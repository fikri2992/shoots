package com.shoots.app.data

import android.content.Context

class LegacyStateMigrator(
    private val context: Context,
    private val dao: ShootsDao,
) {
    suspend fun migrate() {
        if (dao.sourceState() != null) return
        val old = context.getSharedPreferences("phone_source", Context.MODE_PRIVATE)
        dao.putSourceState(
            SourceStateEntity(
                enabled = old.getBoolean("enabled", false),
                lastDateAdded = old.getLong("last_date", 0),
                lastMediaId = old.getLong("last_id", 0),
                lastSuccessfulSyncAt = old.getString("last_run", "").orEmpty(),
                lastError = old.getString("error", "").orEmpty(),
            )
        )
        old.edit().clear().apply()
    }
}
