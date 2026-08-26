package com.shoots.app.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class UserDto(
    val id: String,
    val email: String,
    val name: String = "",
    val picture: String = "",
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
    val blobs: Map<String, String> = emptyMap(),
    @SerialName("experiment_id") val experimentId: String = "",
    @SerialName("capture_session_id") val captureSessionId: String = "",
    @SerialName("kept_at") val keptAt: String? = null,
    @SerialName("drive_review_url") val driveReviewUrl: String = "",
    val error: String = "",
    @SerialName("captured_at") val capturedAt: String? = null,
    @SerialName("ingested_at") val ingestedAt: String = "",
    @SerialName("analyzed_at") val analyzedAt: String? = null,
) {
    val displayTime: String get() = capturedAt ?: exif.capturedAt ?: ingestedAt
}

@Serializable
data class TechniqueEvidenceDto(
    @SerialName("technique_id") val techniqueId: String,
    val confidence: Double = 0.0,
    val cells: List<String> = emptyList(),
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
data class AnalysisDto(
    @SerialName("shot_id") val shotId: String,
    val model: String = "",
    @SerialName("prompt_version") val promptVersion: String = "",
    val techniques: List<TechniqueEvidenceDto> = emptyList(),
    val observations: List<String> = emptyList(),
    val findings: List<FindingDto> = emptyList(),
    val critique: String = "",
    val abstained: String = "",
)

@Serializable
data class ShotViewDto(
    val shot: ShotDto,
    val analysis: AnalysisDto? = null,
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
data class ExperimentDto(
    val id: String,
    @SerialName("technique_id") val techniqueId: String = "",
    val type: String = "reproduce",
    val title: String,
    val brief: String = "",
    @SerialName("why_now") val whyNow: String = "",
    val criteria: CriteriaDto = CriteriaDto(),
    @SerialName("reference_shot_id") val referenceShotId: String = "",
    @SerialName("result_shot_ids") val resultShotIds: List<String> = emptyList(),
    val status: String = "open",
    val verdicts: List<VerdictDto> = emptyList(),
    val change: ChangeDto? = null,
    @SerialName("issued_at") val issuedAt: String = "",
)

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
    @SerialName("last_observed") val lastObserved: String? = null,
)

@Serializable
data class MobileSnapshotDto(
    val user: UserDto,
    @SerialName("drive_connected") val driveConnected: Boolean = false,
    @SerialName("drive_folder_url") val driveFolderUrl: String = "",
    @SerialName("open_experiment") val openExperiment: ExperimentDto? = null,
    @SerialName("latest_capture_session") val latestCaptureSession: CaptureSessionDto? = null,
    @SerialName("latest_run") val latestRun: RunDto? = null,
    @SerialName("recent_shots") val recentShots: List<ShotDto> = emptyList(),
    val journey: List<JourneyUpdateDto> = emptyList(),
    val profile: ProfileDto = ProfileDto(),
    val techniques: List<TechniqueNodeDto> = emptyList(),
    val experiments: List<ExperimentDto> = emptyList(),
)

@Serializable
data class ImportResponse(
    @SerialName("shot_id") val shotId: String,
    val created: Boolean,
    @SerialName("capture_session_id") val captureSessionId: String = "",
)

@Serializable
data class KeeperRequest(val keeper: Boolean)

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

