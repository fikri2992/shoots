package com.shoots.app

import androidx.test.ext.junit.runners.AndroidJUnit4
import com.shoots.app.data.MobileSnapshotDto
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

    @Test
    fun cachedSnapshotDecodesTheTypedShootReceiptAndScoutRoute() {
        val snapshot = json.decodeFromString<MobileSnapshotDto>(
            """
            {
              "user": {"id": "user-1", "email": "photographer@example.test"},
              "latest_shoot": {
                "id": "shoot-1",
                "status": "settled",
                "revision": 2,
                "current_record_revision": 2,
                "ordered_scene_ids": ["scene-1"],
                "ordered_shot_ids": ["shot-1", "shot-2"]
              },
              "latest_shoot_record": {
                "shoot_id": "shoot-1",
                "revision": 2,
                "scene_ids": ["scene-1"],
                "shot_ids": ["shot-1", "shot-2"],
                "receipt": {
                  "shot_count": 2,
                  "scene_count": 1,
                  "repeated": ["2 of 2 Shots used portrait orientation (measured)."]
                },
                "scout": {
                  "route": "recommend",
                  "policy_version": "shoot-scout-1",
                  "recommendation": {
                    "id": "recommendation-1",
                    "primary_option_id": "explore_backlight",
                    "options": [
                      {
                        "id": "explore_backlight",
                        "technique_id": "backlight",
                        "technique_name": "Backlight",
                        "experiment_type": "explore",
                        "title": "Try Backlight on purpose",
                        "why_now": "It appeared clearly in both Shots.",
                        "warrant_shot_ids": ["shot-1", "shot-2"]
                      }
                    ]
                  }
                }
              }
            }
            """.trimIndent()
        )

        assertEquals("shoot-1", snapshot.latestShoot?.id)
        assertEquals(2, snapshot.latestShootRecord?.receipt?.shotCount)
        assertEquals("recommend", snapshot.latestShootRecord?.scout?.route)
        assertEquals(
            "Try Backlight on purpose",
            snapshot.latestShootRecord?.scout?.recommendation?.options?.first()?.title,
        )
    }
}
