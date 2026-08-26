package com.shoots.app.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.shoots.app.ShootsTheme
import com.shoots.app.data.CriteriaDto
import com.shoots.app.data.ExperimentDto
import com.shoots.app.data.MobileSnapshotDto
import com.shoots.app.data.ShotDto
import com.shoots.app.data.TechniqueChoiceDto
import com.shoots.app.data.UserDto
import com.shoots.app.data.VariationDto
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class ExperimentsScreenIntegrationTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun legacyExploreCannotMasqueradeAsRunnableReproduce() {
        val snapshot = snapshotWith(
            ExperimentDto(
                id = "legacy-explore",
                type = "explore",
                title = "Try a brighter frame",
                criteria = CriteriaDto(text = listOf("Keep the subject readable")),
            )
        )

        compose.setContent { ExperimentsTestContent(snapshot) }

        compose.onNodeWithText("OLDER EXPERIMENT").assertExists()
        compose.onNodeWithText("Find a current Experiment").assertExists()
        compose.onNodeWithText("Try with normal camera").assertDoesNotExist()
        compose.onNodeWithText("REPRODUCE").assertDoesNotExist()
    }

    @Test
    fun keeperBackedReproduceCanOpenTheNormalCameraFlow() {
        val keeper = ShotDto(id = "keeper-1", status = "analyzed", keptAt = "2026-08-26T00:00:00Z")
        val snapshot = snapshotWith(
            experiment = ExperimentDto(
                id = "reproduce-1",
                type = "reproduce",
                title = "Hold the backlight",
                referenceShotId = keeper.id,
                criteria = CriteriaDto(text = listOf("Subject edge remains readable")),
            ),
            shots = listOf(keeper),
        )

        compose.setContent { ExperimentsTestContent(snapshot) }

        compose.onNodeWithText("REPRODUCE").assertExists()
        compose.onNodeWithText("Try with normal camera").assertExists()
        compose.onNodeWithText("OLDER EXPERIMENT").assertDoesNotExist()
    }

    @Test
    fun correctedExploreShowsOptionalVariationsWithoutCriteriaOrVerdict() {
        val snapshot = snapshotWith(
            ExperimentDto(
                id = "explore-1",
                type = "explore",
                title = "Explore negative space",
                variations = listOf(
                    VariationDto("clear", "Make it obvious", "Let empty space lead."),
                    VariationDto("invert", "Try the opposite", "Fill the frame.", true),
                ),
            )
        )

        compose.setContent { ExperimentsTestContent(snapshot) }

        compose.onNodeWithText("EXPLORE").assertExists()
        compose.onNodeWithText("NO VERDICT").assertExists()
        compose.onNodeWithText("Make it obvious").assertExists()
        compose.onNodeWithText("Try the opposite").assertExists()
        compose.onNodeWithText("CRITERIA").assertDoesNotExist()
        compose.onNodeWithText("OLDER EXPERIMENT").assertDoesNotExist()
    }

    @Test
    fun photographerCanExploreAnExplicitNewTechnique() {
        var requested: Pair<Boolean, String>? = null
        val snapshot = snapshotWith(
            experiment = null,
            techniqueCatalogue = listOf(
                TechniqueChoiceDto(
                    techniqueId = "motion_blur",
                    name = "Motion blur",
                    family = "exposure",
                    description = "Keep one anchor sharp while another region streaks.",
                    observed = false,
                )
            ),
        )

        compose.setContent {
            ExperimentsTestContent(snapshot) { force, techniqueId ->
                requested = force to techniqueId
            }
        }

        compose.onNodeWithText("Explore something").performClick()
        compose.onNodeWithText("What do you want to explore?").assertExists()
        compose.onNodeWithText("New to your record").assertExists()
        compose.onNodeWithText("Motion blur").performClick()
        compose.runOnIdle { assertEquals(false to "motion_blur", requested) }
    }

    @androidx.compose.runtime.Composable
    private fun ExperimentsTestContent(
        snapshot: MobileSnapshotDto,
        onRequestExplore: (Boolean, String) -> Unit = { _, _ -> },
    ) {
        ShootsTheme {
            ExperimentsScreen(
                snapshot = snapshot,
                localSession = null,
                busy = false,
                imageUrl = { _ -> "" },
                onRequestExperiment = { _ -> },
                onRequestExplore = onRequestExplore,
                onStartExperiment = { _, _ -> },
                onCompleteExplore = { _ -> },
                onContinueSession = { _ -> },
                onFinishSession = { _ -> },
                onCancelSession = { _ -> },
                onImportSessionAsFree = { _ -> },
                onShot = { _ -> },
            )
        }
    }

    private fun snapshotWith(
        experiment: ExperimentDto?,
        shots: List<ShotDto> = emptyList(),
        techniqueCatalogue: List<TechniqueChoiceDto> = emptyList(),
    ) = MobileSnapshotDto(
        user = UserDto(id = "user-1", email = "photographer@example.com"),
        openExperiment = experiment,
        recentShots = shots,
        experiments = listOfNotNull(experiment),
        techniqueCatalogue = techniqueCatalogue,
    )
}
