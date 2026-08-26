package com.shoots.app

import androidx.test.ext.junit.runners.AndroidJUnit4
import com.shoots.app.data.ShotDto
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MobileModelIntegrationTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun automaticPhoneShotUsesFrozenMediaStoreInstantInsteadOfNaiveExifClock() {
        val shot = json.decodeFromString<ShotDto>(
            """
            {
              "id": "shot-1",
              "source_id": "device:external:7:1787733541:4096",
              "captured_at": "2026-08-26T15:39:01Z",
              "ingested_at": "2026-08-26T08:39:07Z",
              "exif": {"captured_at": "2026-08-26T15:39:01Z"}
            }
            """.trimIndent()
        )

        assertEquals("2026-08-26T08:39:01Z", shot.displayTime)
    }

    @Test
    fun selectedShotDoesNotBorrowAnAutomaticMediaStoreInstant() {
        val shot = json.decodeFromString<ShotDto>(
            """
            {
              "id": "shot-2",
              "source_id": "device:selected:stable-reference",
              "captured_at": "2026-08-26T08:40:00Z",
              "ingested_at": "2026-08-26T08:40:05Z"
            }
            """.trimIndent()
        )

        assertEquals("2026-08-26T08:40:00Z", shot.displayTime)
    }
}
