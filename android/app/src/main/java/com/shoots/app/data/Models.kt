package com.shoots.app.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import java.time.Instant

@Serializable
data class UserDto(
    val id: String,
    val email: String,
    val name: String = "",
    val picture: String = "",
    @SerialName("record_mode") val recordMode: String = "real",
)

@Serializable
data class AndroidSessionRequest(
    @SerialName("id_token") val idToken: String,
    val nonce: String,
    val device: String,
)

@Serializable
data class AndroidSessionResponse(
    val token: String,
    @SerialName("expires_at") val expiresAt: String,
    val user: UserDto,
)

@Serializable
data class ExifDto(
    val make: String = "",
    val model: String = "",
    @SerialName("exposure_time_s") val exposureTimeSeconds: Double? = null,
    @SerialName("f_number") val aperture: Double? = null,
    val iso: Int? = null,
    @SerialName("focal_length_mm") val focalLengthMillimetres: Double? = null,
    @SerialName("captured_at") val capturedAt: String? = null,
    @SerialName("capture_utc_offset_minutes") val captureUtcOffsetMinutes: Int? = null,
    @SerialName("capture_time_authority") val captureTimeAuthority: String = "unknown",
)

@Serializable
data class GridSpecDto(
    val cols: Int,
    val rows: Int,
    val width: Int,
    val height: Int,
)

@Serializable
data class ShotDto(
    val id: String,
    @SerialName("user_id") val userId: String = "",
    val kind: String = "photo",
    val source: String = "android",
    @SerialName("source_id") val sourceId: String = "",
    val filename: String = "Shot",
    @SerialName("mime_type") val mimeType: String = "image/jpeg",
    val status: String = "new",
    val exif: ExifDto = ExifDto(),
    val grid: GridSpecDto? = null,
    val blobs: Map<String, String> = emptyMap(),
    @SerialName("experiment_id") val experimentId: String = "",
    @SerialName("variation_id") val variationId: String = "",
    @SerialName("capture_session_id") val captureSessionId: String = "",
    @SerialName("kept_at") val keptAt: String? = null,
    @SerialName("drive_review_url") val driveReviewUrl: String = "",
    val error: String = "",
    @SerialName("captured_at") val capturedAt: String? = null,
    @SerialName("ingested_at") val ingestedAt: String = "",
    @SerialName("analyzed_at") val analyzedAt: String? = null,
) {
    val displayTime: String
        get() = mediaStoreCapturedAt ?: capturedAt ?: exif.capturedAt ?: ingestedAt

    private val mediaStoreCapturedAt: String?
        get() {
            val sourceTail = sourceId.substringAfter(":external:", "")
            val dateAdded = sourceTail
                .split(':')
                .getOrNull(1)
                ?.toLongOrNull()
                ?.takeIf { it in 946684800L..4102444800L }
                ?: return null
            return Instant.ofEpochSecond(dateAdded).toString()
        }
}

@Serializable
data class InspirationDto(
    val id: String,
    @SerialName("user_id") val userId: String = "",
    val source: String = "android",
    @SerialName("source_id") val sourceId: String = "",
    val filename: String = "Inspiration",
    @SerialName("mime_type") val mimeType: String = "image/jpeg",
    val blobs: Map<String, String> = emptyMap(),
    @SerialName("source_shot_id") val sourceShotId: String = "",
    @SerialName("created_at") val createdAt: String = "",
)

@Serializable
data class PhotographerSignalDto(
    val id: String,
    val scope: String = "photographer",
    @SerialName("scope_id") val scopeId: String = "",
    val kind: String,
    val value: String,
    val source: String,
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("expires_at") val expiresAt: String? = null,
)

@Serializable
data class VisualPathDto(
    val points: List<String> = emptyList(),
    @SerialName("leads_to") val leadsTo: List<String> = emptyList(),
    val role: String = "other",
)

@Serializable
data class VisualRegionDto(
    val cells: List<String> = emptyList(),
    val role: String = "other",
    val order: Int = 0,
)

@Serializable
data class VisualEvidenceArtifactDto(
    val kind: String,
    val authority: String,
    val status: String = "rendered",
    val verification: String = "not_run",
    @SerialName("refinement_count") val refinementCount: Int = 0,
    @SerialName("blob_path") val blobPath: String = "",
    val label: String = "",
    val legend: String = "",
    val metrics: Map<String, JsonElement> = emptyMap(),
    @SerialName("source_digest") val sourceDigest: String = "",
    @SerialName("renderer_version") val rendererVersion: String = "",
    @SerialName("fallback_reason") val fallbackReason: String = "",
)

@Serializable
data class TechniqueEvidenceDto(
    @SerialName("technique_id") val techniqueId: String,
    val name: String = "",
    val confidence: Double = 0.0,
    val cells: List<String> = emptyList(),
    val paths: List<VisualPathDto> = emptyList(),
    val regions: List<VisualRegionDto> = emptyList(),
    @SerialName("visual_artifact") val visualArtifact: VisualEvidenceArtifactDto? = null,
    val note: String = "",
    val agreement: Int = 1,
    val lenses: List<String> = emptyList(),
)

@Serializable
data class FindingDto(
    @SerialName("finding_id") val findingId: String,
    val what: String,
    val why: String,
    val cells: List<String> = emptyList(),
)

@Serializable
data class MoveDto(
    val what: String,
    val kind: String = "move",
    @SerialName("from_cells") val fromCells: List<String> = emptyList(),
    @SerialName("to_cells") val toCells: List<String> = emptyList(),
    val reason: String = "",
    val warrant: String = "unspecified",
    @SerialName("challenges_technique_ids") val challengesTechniqueIds: List<String> = emptyList(),
)

@Serializable
data class CompositionDto(
    @SerialName("subject_cells") val subjectCells: List<String> = emptyList(),
    @SerialName("subject_x") val subjectX: Double? = null,
    @SerialName("subject_y") val subjectY: Double? = null,
    val guide: String = "",
    @SerialName("horizon_row") val horizonRow: Int? = null,
    @SerialName("suggested_crop_cells") val suggestedCropCells: List<String> = emptyList(),
    @SerialName("crop_tested") val cropTested: Boolean = false,
    @SerialName("crop_reason") val cropReason: String = "",
    val moves: List<MoveDto> = emptyList(),
)

@Serializable
data class AnalysisDto(
    @SerialName("shot_id") val shotId: String,
    val model: String = "",
    @SerialName("prompt_version") val promptVersion: String = "",
    val techniques: List<TechniqueEvidenceDto> = emptyList(),
    val composition: CompositionDto = CompositionDto(),
    val observations: List<String> = emptyList(),
    val findings: List<FindingDto> = emptyList(),
    val critique: String = "",
    val abstained: String = "",
)

@Serializable
data class ShotTechniqueContextDto(
    @SerialName("technique_id") val techniqueId: String,
    val status: String,
    @SerialName("corroborated_shots") val corroboratedShots: Int = 0,
    @SerialName("distinct_scenes") val distinctScenes: Int = 0,
    @SerialName("distinct_shoots") val distinctShoots: Int = 0,
    @SerialName("reproduce_sessions") val reproduceSessions: Int = 0,
    @SerialName("evaluable_reproduce_sessions") val evaluableReproduceSessions: Int = 0,
    @SerialName("criteria_met_sessions") val criteriaMetSessions: Int = 0,
    @SerialName("positive_keeper_shots") val positiveKeeperShots: Int = 0,
)

@Serializable
data class ShotViewDto(
    val shot: ShotDto,
    val analysis: AnalysisDto? = null,
    val run: RunDto? = null,
    val teaching: ShotTeachingReceiptDto? = null,
    @SerialName("technique_context")
    val techniqueContext: Map<String, ShotTechniqueContextDto> = emptyMap(),
)

@Serializable
data class VisualMarkDto(
    val kind: String = "none",
    val cells: List<String> = emptyList(),
    @SerialName("to_cells") val toCells: List<String> = emptyList(),
    val paths: List<VisualPathDto> = emptyList(),
    val regions: List<VisualRegionDto> = emptyList(),
    @SerialName("visual_artifact") val visualArtifact: VisualEvidenceArtifactDto? = null,
    @SerialName("technique_id") val techniqueId: String = "",
    @SerialName("finding_id") val findingId: String = "",
)

@Serializable
data class ShotTeachingReceiptDto(
    @SerialName("keep_title") val keepTitle: String = "",
    @SerialName("keep_proof") val keepProof: String = "",
    @SerialName("keep_technique_id") val keepTechniqueId: String = "",
    @SerialName("keep_authority") val keepAuthority: String? = null,
    @SerialName("keep_cells") val keepCells: List<String> = emptyList(),
    @SerialName("keep_mark") val keepMark: VisualMarkDto = VisualMarkDto(),
    @SerialName("notice_title") val noticeTitle: String = "",
    @SerialName("notice_proof") val noticeProof: String = "",
    @SerialName("notice_finding_id") val noticeFindingId: String = "",
    @SerialName("notice_authority") val noticeAuthority: String? = null,
    @SerialName("notice_cells") val noticeCells: List<String> = emptyList(),
    @SerialName("notice_mark") val noticeMark: VisualMarkDto = VisualMarkDto(),
    @SerialName("try_text") val tryText: String = "",
    @SerialName("try_reason") val tryReason: String = "",
    @SerialName("try_kind") val tryKind: String? = null,
    @SerialName("try_from_cells") val tryFromCells: List<String> = emptyList(),
    @SerialName("try_to_cells") val tryToCells: List<String> = emptyList(),
    @SerialName("try_mark") val tryMark: VisualMarkDto = VisualMarkDto(),
    @SerialName("visible_check") val visibleCheck: String = "",
    @SerialName("check_mark") val checkMark: VisualMarkDto = VisualMarkDto(),
    @SerialName("primary_layer") val primaryLayer: String = "clean",
    val guide: String = "",
)

@Serializable
data class CriteriaDto(
    val text: List<String> = emptyList(),
    val vision: List<String> = emptyList(),
)

@Serializable
data class VerdictDto(
    @SerialName("shot_id") val shotId: String,
    @SerialName("criteria_met") val criteriaMet: Boolean,
    val feedback: String = "",
    @SerialName("compared_with") val comparedWith: String = "",
)

@Serializable
data class ChangeDto(
    val state: String,
    val comparability: String = "comparable",
    val outcome: String = "",
    val added: Int = 0,
)

@Serializable
data class VariationDto(
    val id: String,
    val title: String,
    val instruction: String,
    val inversion: Boolean = false,
)

@Serializable
data class VariationObservationDto(
    @SerialName("variation_id") val variationId: String,
    @SerialName("shot_id") val shotId: String,
    @SerialName("technique_ids") val techniqueIds: List<String> = emptyList(),
    @SerialName("corroborated_technique_ids") val corroboratedTechniqueIds: List<String> = emptyList(),
    val guide: String = "",
    @SerialName("finding_ids") val findingIds: List<String> = emptyList(),
    val abstained: String = "",
)

@Serializable
data class ExperimentDto(
    val id: String,
    @SerialName("technique_id") val techniqueId: String = "",
    val type: String = "reproduce",
    val title: String,
    val brief: String = "",
    @SerialName("why_now") val whyNow: String = "",
    val criteria: CriteriaDto = CriteriaDto(),
    val variations: List<VariationDto> = emptyList(),
    @SerialName("variation_observations") val variationObservations: List<VariationObservationDto> = emptyList(),
    @SerialName("reference_shot_id") val referenceShotId: String = "",
    @SerialName("result_shot_ids") val resultShotIds: List<String> = emptyList(),
    val status: String = "open",
    val verdicts: List<VerdictDto> = emptyList(),
    val change: ChangeDto? = null,
    @SerialName("issued_at") val issuedAt: String = "",
)

@Serializable
data class ExperimentDirectionDto(
    val id: String,
    @SerialName("source_shot_id") val sourceShotId: String,
    @SerialName("technique_id") val techniqueId: String,
    @SerialName("technique_name") val techniqueName: String,
    val question: String,
    @SerialName("warrant_shot_ids") val warrantShotIds: List<String> = emptyList(),
    @SerialName("reference_shot_id") val referenceShotId: String = "",
    @SerialName("corroborated_shots") val corroboratedShots: Int = 0,
    @SerialName("distinct_shoots") val distinctShoots: Int = 0,
    val state: String = "saved",
    @SerialName("started_experiment_id") val startedExperimentId: String = "",
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("updated_at") val updatedAt: String = "",
)

@Serializable
data class ExperimentDirectionChoiceRequest(
    @SerialName("source_shot_id") val sourceShotId: String,
    @SerialName("technique_id") val techniqueId: String,
    val state: String,
)

val ExperimentDto.canStartReproduce: Boolean
    get() = type == "reproduce" && referenceShotId.isNotBlank() && criteria.text.isNotEmpty()

val ExperimentDto.canStartExplore: Boolean
    get() = type == "explore" && variations.size in 2..4 && criteria.text.isEmpty()

@Serializable
data class CaptureSessionMemberDto(
    @SerialName("source_id") val sourceId: String,
    val order: Int,
    @SerialName("shot_id") val shotId: String = "",
    val outcome: String = "pending",
)

@Serializable
data class CaptureSessionDto(
    val id: String,
    @SerialName("experiment_id") val experimentId: String,
    @SerialName("variation_id") val variationId: String = "",
    val status: String,
    val members: List<CaptureSessionMemberDto> = emptyList(),
    @SerialName("representative_result_shot_id") val representativeResultShotId: String = "",
    val summary: Map<String, Int> = emptyMap(),
    @SerialName("reserved_at") val reservedAt: String = "",
    @SerialName("expires_at") val expiresAt: String = "",
    @SerialName("settled_at") val settledAt: String? = null,
)

@Serializable
data class CaptureSessionReserveRequest(
    @SerialName("experiment_id") val experimentId: String,
    @SerialName("variation_id") val variationId: String = "",
)

@Serializable
data class CaptureManifestMember(
    @SerialName("source_id") val sourceId: String,
    val order: Int,
)

@Serializable
data class CaptureManifestRequest(val members: List<CaptureManifestMember>)

@Serializable
data class RunStepDto(
    val state: String = "pending",
    val outcome: String = "",
    val detail: Map<String, JsonElement> = emptyMap(),
)

@Serializable
data class RunDto(
    val id: String,
    @SerialName("shot_id") val shotId: String,
    @SerialName("experiment_id") val experimentId: String = "",
    @SerialName("capture_session_id") val captureSessionId: String = "",
    val status: String = "running",
    val steps: Map<String, RunStepDto> = emptyMap(),
    @SerialName("updated_at") val updatedAt: String = "",
)

@Serializable
data class ShootDto(
    val id: String,
    @SerialName("user_id") val userId: String = "",
    val status: String = "open",
    val revision: Int = 1,
    @SerialName("current_record_revision") val currentRecordRevision: Int = 0,
    @SerialName("ordered_scene_ids") val orderedSceneIds: List<String> = emptyList(),
    @SerialName("ordered_shot_ids") val orderedShotIds: List<String> = emptyList(),
    @SerialName("started_at") val startedAt: String? = null,
    @SerialName("last_capture_at") val lastCaptureAt: String? = null,
    @SerialName("closed_at") val closedAt: String? = null,
)

@Serializable
data class ShootDimensionFigureDto(
    @SerialName("dimension_id") val dimensionId: String,
    val label: String,
    val authority: String,
    val counts: Map<String, Int> = emptyMap(),
    @SerialName("readable_shots") val readableShots: Int = 0,
    @SerialName("unreadable_shots") val unreadableShots: Int = 0,
    val dominant: String = "",
    @SerialName("dominant_count") val dominantCount: Int = 0,
    val exploration: Double = 0.0,
    @SerialName("blind_spot") val blindSpot: String = "",
)

@Serializable
data class ShootTechniqueFigureDto(
    @SerialName("technique_id") val techniqueId: String,
    val name: String,
    val authority: String = "model_read",
    @SerialName("observed_shot_ids") val observedShotIds: List<String> = emptyList(),
    @SerialName("corroborated_shot_ids") val corroboratedShotIds: List<String> = emptyList(),
)

@Serializable
data class ShootReceiptDto(
    @SerialName("calc_version") val calcVersion: String = "",
    val summary: String = "",
    @SerialName("shot_count") val shotCount: Int = 0,
    @SerialName("scene_count") val sceneCount: Int = 0,
    @SerialName("shots_per_scene") val shotsPerScene: List<Int> = emptyList(),
    @SerialName("readable_shot_count") val readableShotCount: Int = 0,
    @SerialName("unreadable_shot_ids") val unreadableShotIds: List<String> = emptyList(),
    @SerialName("keeper_shot_ids") val keeperShotIds: List<String> = emptyList(),
    val repeated: List<String> = emptyList(),
    val varied: List<String> = emptyList(),
    @SerialName("blind_spots") val blindSpots: List<String> = emptyList(),
    val dimensions: List<ShootDimensionFigureDto> = emptyList(),
    val techniques: List<ShootTechniqueFigureDto> = emptyList(),
)

@Serializable
data class ScoutWarrantDto(
    val kind: String,
    @SerialName("shoot_id") val shootId: String,
    @SerialName("shoot_revision") val shootRevision: Int,
    @SerialName("shot_ids") val shotIds: List<String> = emptyList(),
    @SerialName("technique_id") val techniqueId: String = "",
    @SerialName("reference_shot_id") val referenceShotId: String = "",
    val detail: String = "",
)

@Serializable
data class ScoutRejectedRouteDto(
    val route: String,
    val reason: String,
)

@Serializable
data class ScoutQuestionOptionDto(
    val id: String,
    val label: String,
    @SerialName("technique_id") val techniqueId: String = "",
)

@Serializable
data class ScoutQuestionDto(
    val id: String = "",
    val prompt: String = "",
    val options: List<ScoutQuestionOptionDto> = emptyList(),
)

@Serializable
data class ScoutDecisionDto(
    val route: String = "silence",
    val reason: String = "",
    val warrant: List<ScoutWarrantDto> = emptyList(),
    @SerialName("rejected_routes") val rejectedRoutes: List<ScoutRejectedRouteDto> = emptyList(),
    @SerialName("input_shot_ids") val inputShotIds: List<String> = emptyList(),
    @SerialName("projection_versions") val projectionVersions: Map<String, String> = emptyMap(),
    @SerialName("policy_version") val policyVersion: String = "",
    @SerialName("experiment_id") val experimentId: String = "",
    @SerialName("execution_state") val executionState: String = "completed",
    @SerialName("execution_detail") val executionDetail: String = "",
    @SerialName("attempt_state") val attemptState: String = "not_applicable",
    @SerialName("observable_outcome") val observableOutcome: String = "not_applicable",
    val question: ScoutQuestionDto = ScoutQuestionDto(),
)

@Serializable
data class ScoutAnswerDto(
    val id: String,
    @SerialName("question_id") val questionId: String,
    @SerialName("shoot_id") val shootId: String,
    @SerialName("shoot_revision") val shootRevision: Int,
    @SerialName("option_id") val optionId: String,
    @SerialName("technique_id") val techniqueId: String = "",
    @SerialName("intent_signal_id") val intentSignalId: String = "",
    @SerialName("experiment_id") val experimentId: String = "",
    val state: String = "pending",
    val detail: String = "",
)

@Serializable
data class ScoutAnswerRequest(
    val revision: Int,
    @SerialName("option_id") val optionId: String,
)

@Serializable
data class InterventionRecordDto(
    val id: String,
    @SerialName("shoot_id") val shootId: String,
    @SerialName("shoot_revision") val shootRevision: Int,
    val route: String,
    @SerialName("technique_id") val techniqueId: String = "",
    @SerialName("question_id") val questionId: String = "",
    @SerialName("experiment_id") val experimentId: String = "",
    @SerialName("warrant_shot_ids") val warrantShotIds: List<String> = emptyList(),
    @SerialName("attempt_state") val attemptState: String = "not_applicable",
    @SerialName("observable_outcome") val observableOutcome: String = "not_applicable",
    @SerialName("result_shot_ids") val resultShotIds: List<String> = emptyList(),
    @SerialName("criteria_met_results") val criteriaMetResults: Int = 0,
    val abstentions: Int = 0,
    @SerialName("variation_ids") val variationIds: List<String> = emptyList(),
    @SerialName("change_state") val changeState: String = "",
    val comparability: String = "",
    @SerialName("outcome_reason") val outcomeReason: String = "",
)

@Serializable
data class ShootRecordDto(
    @SerialName("shoot_id") val shootId: String,
    val revision: Int = 1,
    @SerialName("scene_ids") val sceneIds: List<String> = emptyList(),
    @SerialName("shot_ids") val shotIds: List<String> = emptyList(),
    @SerialName("run_outcomes") val runOutcomes: Map<String, String> = emptyMap(),
    @SerialName("unreadable_shot_ids") val unreadableShotIds: List<String> = emptyList(),
    val receipt: ShootReceiptDto = ShootReceiptDto(),
    val scout: ScoutDecisionDto = ScoutDecisionDto(),
    @SerialName("settled_at") val settledAt: String = "",
)

@Serializable
data class DeconstructionPageDto(
    val kind: String,
    val title: String,
    val claim: String,
    @SerialName("shot_ids") val shotIds: List<String> = emptyList(),
    @SerialName("evidence_refs") val evidenceRefs: List<String> = emptyList(),
    @SerialName("visual_layer") val visualLayer: String = "original",
    @SerialName("blob_path") val blobPath: String = "",
)

@Serializable
data class DeconstructionDto(
    val id: String,
    @SerialName("source_type") val sourceType: String,
    @SerialName("source_id") val sourceId: String,
    @SerialName("source_revision") val sourceRevision: Int = 0,
    val status: String = "needs_cover",
    @SerialName("candidate_cover_shot_ids") val candidateCoverShotIds: List<String> = emptyList(),
    @SerialName("cover_shot_id") val coverShotId: String = "",
    val pages: List<DeconstructionPageDto> = emptyList(),
    @SerialName("suggested_caption") val suggestedCaption: String = "",
)

@Serializable
data class DeconstructionPrepareRequest(
    @SerialName("source_type") val sourceType: String,
    @SerialName("source_id") val sourceId: String,
    @SerialName("source_revision") val sourceRevision: Int = 0,
    @SerialName("cover_shot_id") val coverShotId: String = "",
)

@Serializable
data class JourneyUpdateDto(
    val id: String,
    val body: String,
    val evidence: List<String> = emptyList(),
    val widened: List<String> = emptyList(),
    @SerialName("became_recurring") val becameRecurring: List<String> = emptyList(),
    val shots: Int = 0,
    @SerialName("taste_is_known") val tasteIsKnown: Boolean = false,
    @SerialName("created_at") val createdAt: String = "",
)

@Serializable
data class ProfileBucketDto(
    val bucket: String,
    val count: Int,
    val keepers: Int = 0,
)

@Serializable
data class ProfileDimensionDto(
    val id: String,
    val label: String,
    val buckets: List<ProfileBucketDto> = emptyList(),
    val unreadable: Int = 0,
    val readable: Boolean = false,
    val narrow: Boolean = false,
    val dominant: String = "",
    val never: List<String> = emptyList(),
    val source: String = "",
)

@Serializable
data class ProfileDto(
    val shots: Int = 0,
    val keepers: Int = 0,
    @SerialName("taste_is_known") val tasteIsKnown: Boolean = false,
    val dimensions: List<ProfileDimensionDto> = emptyList(),
    val scenes: Int = 0,
    @SerialName("shots_per_scene") val shotsPerScene: Double = 0.0,
    @SerialName("blind_spots") val blindSpots: List<String> = emptyList(),
)

@Serializable
data class TechniqueNodeDto(
    @SerialName("technique_id") val techniqueId: String,
    val name: String,
    val family: String,
    val status: String,
    val attempts: Int,
    val corroborated: Int,
    val sightings: Int = attempts,
    @SerialName("corroborated_shots") val corroboratedShots: Int = corroborated,
    @SerialName("distinct_scenes") val distinctScenes: Int = 0,
    @SerialName("distinct_shoots") val distinctShoots: Int = 0,
    @SerialName("reproduce_attempts") val reproduceAttempts: Int = 0,
    @SerialName("criteria_met_results") val criteriaMetResults: Int = 0,
    @SerialName("reproduce_sessions") val reproduceSessions: Int = 0,
    @SerialName("evaluable_reproduce_sessions") val evaluableReproduceSessions: Int = 0,
    @SerialName("criteria_met_sessions") val criteriaMetSessions: Int = 0,
    val abstentions: Int = 0,
    @SerialName("positive_keeper_shots") val positiveKeeperShots: Int = 0,
    @SerialName("supported_condition_coverage") val supportedConditionCoverage: Map<String, Int> = emptyMap(),
    @SerialName("projection_version") val projectionVersion: String = "",
    @SerialName("input_digest") val inputDigest: String = "",
    @SerialName("last_observed") val lastObserved: String? = null,
)

@Serializable
data class TechniqueChoiceDto(
    @SerialName("technique_id") val techniqueId: String,
    val name: String,
    val family: String,
    val description: String,
    val observed: Boolean = false,
    val recurring: Boolean = false,
    @SerialName("corroborated_shots") val corroboratedShots: Int = 0,
)

@Serializable
data class MobileSnapshotDto(
    val user: UserDto,
    @SerialName("drive_connected") val driveConnected: Boolean = false,
    @SerialName("drive_folder_url") val driveFolderUrl: String = "",
    @SerialName("open_experiment") val openExperiment: ExperimentDto? = null,
    @SerialName("latest_capture_session") val latestCaptureSession: CaptureSessionDto? = null,
    @SerialName("latest_run") val latestRun: RunDto? = null,
    @SerialName("latest_shoot") val latestShoot: ShootDto? = null,
    @SerialName("latest_shoot_record") val latestShootRecord: ShootRecordDto? = null,
    @SerialName("latest_shot") val latestShot: ShotViewDto? = null,
    @SerialName("recent_shots") val recentShots: List<ShotDto> = emptyList(),
    @SerialName("recent_inspirations") val recentInspirations: List<InspirationDto> = emptyList(),
    @SerialName("photographer_signals") val photographerSignals: List<PhotographerSignalDto> = emptyList(),
    val journey: List<JourneyUpdateDto> = emptyList(),
    val profile: ProfileDto = ProfileDto(),
    val techniques: List<TechniqueNodeDto> = emptyList(),
    @SerialName("technique_catalogue") val techniqueCatalogue: List<TechniqueChoiceDto> = emptyList(),
    val experiments: List<ExperimentDto> = emptyList(),
    @SerialName("experiment_directions")
    val experimentDirections: List<ExperimentDirectionDto> = emptyList(),
    @SerialName("latest_deconstruction") val latestDeconstruction: DeconstructionDto? = null,
    @SerialName("recent_scout_answers") val recentScoutAnswers: List<ScoutAnswerDto> = emptyList(),
    @SerialName("recent_interventions") val recentInterventions: List<InterventionRecordDto> = emptyList(),
)

@Serializable
data class ImportResponse(
    @SerialName("shot_id") val shotId: String = "",
    @SerialName("inspiration_id") val inspirationId: String = "",
    @SerialName("source_role") val sourceRole: String = "mine",
    val created: Boolean,
    @SerialName("capture_session_id") val captureSessionId: String = "",
)

@Serializable
data class KeeperRequest(val keeper: Boolean)

@Serializable
data class SourceRoleRequest(@SerialName("source_role") val sourceRole: String)

@Serializable
data class SourceRoleResult(
    @SerialName("source_role") val sourceRole: String,
    @SerialName("shot_id") val shotId: String = "",
    @SerialName("inspiration_id") val inspirationId: String = "",
)

@Serializable
data class NotificationTargetRequest(val target: String)

@Serializable
data class DriveAuthorizationRequest(val code: String)

@Serializable
data class DriveConnectResponse(
    @SerialName("folder_id") val folderId: String = "",
    @SerialName("folder_url") val folderUrl: String = "",
)

@Serializable
data class DeletionResponse(val id: String, val status: String)
