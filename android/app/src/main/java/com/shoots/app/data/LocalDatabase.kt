package com.shoots.app.data

import android.content.Context
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Index
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.room.Transaction
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "source_state")
data class SourceStateEntity(
    @androidx.room.PrimaryKey val id: Int = 1,
    val enabled: Boolean = false,
    val lastDateAdded: Long = 0,
    val lastMediaId: Long = 0,
    val lastSuccessfulSyncAt: String = "",
    val lastError: String = "",
)

@Entity(
    tableName = "imports",
    indices = [Index("captureSessionId"), Index("state")],
)
data class ImportEntity(
    @androidx.room.PrimaryKey val sourceId: String,
    val uri: String,
    val mediaId: Long,
    val dateAdded: Long,
    val size: Long,
    val displayName: String,
    val mimeType: String,
    val sourceRole: String = "mine",
    val captureSessionId: String = "",
    val experimentId: String = "",
    val manifestOrder: Int = -1,
    val state: String = ImportState.DISCOVERED,
    val shotId: String = "",
    val error: String = "",
    val attemptCount: Int = 0,
)

object ImportState {
    const val DISCOVERED = "discovered"
    const val MANIFEST_PENDING = "manifest_pending"
    const val READY = "ready"
    const val UPLOADING = "uploading"
    const val UPLOADED = "uploaded"
    const val AUTH_REQUIRED = "auth_required"
    const val SESSION_CONFLICT = "session_conflict"
    const val UNSUPPORTED = "unsupported"
    const val MISSING = "missing"
}

@Entity(tableName = "local_capture_sessions")
data class LocalCaptureSessionEntity(
    @androidx.room.PrimaryKey val id: String,
    val experimentId: String,
    val state: String,
    val baselineDateAdded: Long,
    val baselineMediaId: Long,
    val reservedAt: String,
    val expiresAt: String,
    val error: String = "",
)

object LocalCaptureState {
    const val RESERVED = "reserved"
    const val AWAITING_SELECTION = "awaiting_selection"
    const val MANIFEST_PENDING = "manifest_pending"
    const val COMMITTED = "committed"
    const val PROCESSING = "processing"
    const val SETTLED = "settled"
    const val CANCELLED = "cancelled"
    const val EXPIRED = "expired"
    const val CONFLICT = "conflict"
}

@Entity(tableName = "cached_resources")
data class CachedResourceEntity(
    @androidx.room.PrimaryKey val key: String,
    val payload: String,
    val etag: String = "",
    val updatedAt: String,
)

@Entity(tableName = "cached_shots", indices = [Index("sortTime")])
data class CachedShotEntity(
    @androidx.room.PrimaryKey val id: String,
    val payload: String,
    val sortTime: String,
    val status: String,
    val kept: Boolean,
    val thumbPath: String,
    val updatedAt: String,
)

@Dao
abstract class ShootsDao {
    @Query("SELECT * FROM source_state WHERE id = 1")
    abstract suspend fun sourceState(): SourceStateEntity?

    @Query("SELECT * FROM source_state WHERE id = 1")
    abstract fun observeSourceState(): Flow<SourceStateEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    abstract suspend fun putSourceState(state: SourceStateEntity)

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    protected abstract suspend fun insertImport(item: ImportEntity): Long

    @Query("SELECT MAX(manifestOrder) FROM imports WHERE captureSessionId = :sessionId")
    protected abstract suspend fun highestManifestOrder(sessionId: String): Int?

    @Transaction
    open suspend fun discoverAndAdvance(
        items: List<ImportEntity>,
        state: SourceStateEntity,
        captureSessionId: String,
        experimentId: String,
    ): Int {
        var nextOrder = if (captureSessionId.isBlank()) -1 else
            (highestManifestOrder(captureSessionId) ?: -1) + 1
        var inserted = 0
        for (candidate in items) {
            val assigned = if (captureSessionId.isBlank()) {
                candidate
            } else {
                candidate.copy(
                    captureSessionId = captureSessionId,
                    experimentId = experimentId,
                    manifestOrder = nextOrder,
                    state = ImportState.MANIFEST_PENDING,
                )
            }
            if (insertImport(assigned) != -1L) {
                inserted += 1
                if (captureSessionId.isNotBlank()) nextOrder += 1
            }
        }
        putSourceState(state)
        return inserted
    }

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    abstract suspend fun insertSelectedImport(item: ImportEntity): Long

    @Transaction
    open suspend fun insertSelectedImports(
        items: List<ImportEntity>,
        captureSessionId: String,
        experimentId: String,
    ): Int {
        var nextOrder = if (captureSessionId.isBlank()) -1 else
            (highestManifestOrder(captureSessionId) ?: -1) + 1
        var inserted = 0
        for (candidate in items) {
            val assigned = if (captureSessionId.isBlank()) candidate else candidate.copy(
                captureSessionId = captureSessionId,
                experimentId = experimentId,
                manifestOrder = nextOrder,
                state = ImportState.MANIFEST_PENDING,
            )
            if (insertSelectedImport(assigned) != -1L) {
                inserted += 1
                if (captureSessionId.isNotBlank()) nextOrder += 1
            }
        }
        return inserted
    }

    @Query("SELECT * FROM imports WHERE state IN (:states) ORDER BY dateAdded, mediaId")
    abstract suspend fun importsInStates(states: List<String>): List<ImportEntity>

    @Query("SELECT * FROM imports WHERE captureSessionId = :sessionId ORDER BY manifestOrder")
    abstract suspend fun sessionImports(sessionId: String): List<ImportEntity>

    @Query("SELECT * FROM imports WHERE sourceId = :sourceId")
    abstract suspend fun importBySource(sourceId: String): ImportEntity?

    @Query("SELECT * FROM imports WHERE state != 'uploaded' ORDER BY dateAdded DESC, mediaId DESC")
    abstract fun observePendingImports(): Flow<List<ImportEntity>>

    @Update
    abstract suspend fun updateImport(item: ImportEntity)

    @Query("UPDATE imports SET state = :state, error = :error WHERE captureSessionId = :sessionId AND state != 'uploaded'")
    abstract suspend fun setSessionImportState(sessionId: String, state: String, error: String = "")

    @Query("UPDATE imports SET captureSessionId = '', experimentId = '', manifestOrder = -1, state = 'discovered', error = '' WHERE captureSessionId = :sessionId AND state != 'uploaded'")
    abstract suspend fun detachSessionImports(sessionId: String)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    abstract suspend fun putCaptureSession(session: LocalCaptureSessionEntity)

    @Query("SELECT * FROM local_capture_sessions WHERE id = :id")
    abstract suspend fun captureSession(id: String): LocalCaptureSessionEntity?

    @Query("SELECT * FROM local_capture_sessions WHERE state IN ('reserved', 'awaiting_selection', 'manifest_pending', 'committed', 'processing', 'conflict') ORDER BY reservedAt DESC LIMIT 1")
    abstract suspend fun activeCaptureSession(): LocalCaptureSessionEntity?

    @Query("SELECT * FROM local_capture_sessions ORDER BY reservedAt DESC LIMIT 1")
    abstract fun observeLatestCaptureSession(): Flow<LocalCaptureSessionEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    abstract suspend fun putResource(resource: CachedResourceEntity)

    @Query("SELECT * FROM cached_resources WHERE `key` = :key")
    abstract suspend fun resource(key: String): CachedResourceEntity?

    @Query("SELECT * FROM cached_resources WHERE `key` = :key")
    abstract fun observeResource(key: String): Flow<CachedResourceEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    abstract suspend fun putShots(shots: List<CachedShotEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    abstract suspend fun putShot(shot: CachedShotEntity)

    @Query("SELECT * FROM cached_shots ORDER BY sortTime DESC")
    abstract fun observeShots(): Flow<List<CachedShotEntity>>

    @Query("SELECT * FROM cached_shots WHERE id = :id")
    abstract fun observeShot(id: String): Flow<CachedShotEntity?>

    @Query("DELETE FROM cached_shots WHERE id = :id")
    abstract suspend fun deleteShot(id: String)

    @Transaction
    open suspend fun cacheSnapshot(
        resource: CachedResourceEntity,
        shots: List<CachedShotEntity>,
        source: SourceStateEntity,
    ) {
        putResource(resource)
        putShots(shots)
        putSourceState(source)
    }
}

@Database(
    entities = [
        SourceStateEntity::class,
        ImportEntity::class,
        LocalCaptureSessionEntity::class,
        CachedResourceEntity::class,
        CachedShotEntity::class,
    ],
    version = 2,
    // Version 1 is checked in under app/schemas. Room 2.8.4 cannot re-read its
    // own exported JSON with its current serialization ABI; re-enable export
    // when the upstream compiler fix lands, before introducing version 2.
    exportSchema = false,
)
abstract class ShootsDatabase : RoomDatabase() {
    abstract fun dao(): ShootsDao

    companion object {
        fun build(context: Context): ShootsDatabase = Room.databaseBuilder(
            context.applicationContext,
            ShootsDatabase::class.java,
            "shoots.db",
        ).addMigrations(MIGRATION_1_2)
            .setJournalMode(JournalMode.WRITE_AHEAD_LOGGING)
            .build()

        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE imports ADD COLUMN sourceRole TEXT NOT NULL DEFAULT 'mine'")
            }
        }
    }
}
