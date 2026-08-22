"""Single source of truth for models, caps, topics and environment config.

AGENTS.md golden rule: no scattered literals. Every cap, model ID and topic
name lives here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Models -----------------------------------------------------------
    # Hackathon rule: "Gemini 3.5 or newer". All ids verified 2026-08-22 against
    # the Vertex publisher model list for project your-gcp-project.
    #
    #   gemini-3.7-flash     Analyst, Scout, Judge. Every image/contact sheet.
    #   veo-3.1-fast         One 5s reference clip per quest (bonus: Veo).
    #   lyria-3-clip         Optional temp track for video-edit quests (bonus: Lyria).
    #   gemini-live-2.5      Voice review of a shot from the phone (Multimodal UX).
    model_flash: str = "gemini-3.7-flash"
    model_video: str = "veo-3.1-fast-generate-001"
    model_music: str = "lyria-3-clip-preview"
    model_live: str = "gemini-live-2.5-flash-native-audio"

    # Veo/Lyria are long-running operations; these bound the polling loop.
    generate_poll_seconds: float = 5.0
    generate_timeout_seconds: float = 600.0

    #: How long a voice session token stays mintable/usable, in minutes.
    voice_token_minutes: int = 10

    # --- Pipeline caps (docs/domain-model.md) -----------------------------
    #: Long edge the Analyst sees. Composition judgement does not need more.
    analyst_max_edge: int = 1536
    #: Frames sampled from a video, by scene change, before tiling.
    video_max_frames: int = 12
    contact_sheet_cols: int = 4
    #: Below this the Judge will not count a vision tag as evidence.
    judge_min_confidence: float = 0.6
    #: Quests issued per user per daily tick.
    quests_per_day: int = 1
    #: A quest nobody shoots for expires after this many days.
    quest_ttl_days: int = 3
    #: Skills decay toward "rusty" after this many days without practice.
    skill_decay_days: int = 21

    # --- Model call resilience --------------------------------------------
    max_model_retries: int = 4
    model_retry_base_seconds: float = 2.0
    model_retry_max_seconds: float = 30.0

    # --- Google Cloud -----------------------------------------------------
    google_api_key: str = ""
    gcp_project: str = ""
    #: Where the app runs: Cloud Run, Firestore, Pub/Sub, GCS.
    gcp_location: str = "asia-southeast2"
    #: Gemini 3.x is served from the global endpoint only.
    vertex_location: str = "global"
    #: Veo and Lyria are us-central1 only.
    media_location: str = "us-central1"
    gcs_bucket: str = ""
    firestore_database: str = "(default)"
    use_vertex_ai: bool = False
    #: Firestore + Secret Manager instead of the in-memory store and local token
    #: files. Separate from ``gcp_project`` so local dev can use Vertex (needs the
    #: project) while keeping state on disk.
    cloud_state: bool = False

    # --- Pub/Sub (infra/topics.sh creates these) ---------------------------
    topic_media_new: str = "shoots.media.new"
    topic_media_ingested: str = "shoots.media.ingested"
    topic_media_analyzed: str = "shoots.media.analyzed"
    topic_quest_closed: str = "shoots.quest.closed"
    #: Empty = run stages in-process (local dev). Set to the public base URL of
    #: this service on Cloud Run so push subscriptions can reach /pubsub/*.
    pubsub_push_base_url: str = ""
    #: Pub/Sub push requests carry an OIDC token for this service account.
    pubsub_push_audience: str = ""

    # --- Google Drive -----------------------------------------------------
    #: Name of the folder the app creates in the user's Drive on Connect.
    drive_folder_name: str = "Shoots"
    #: Set to a directory to use it as the Drive folder instead of Google.
    #: Local dev and tests: the whole pipeline runs with no Google at all.
    drive_local_folder: str = ""
    #: Where LocalBlobStore keeps files.
    blob_root: str = "./.blobs"
    #: Webhook Drive calls when the watched folder changes.
    drive_webhook_url: str = "http://localhost:8000/drive/notify"
    #: Watch channels expire; the Scheduler renews them this often (hours).
    drive_channel_hours: int = 24

    # --- Auth -------------------------------------------------------------
    google_client_id: str = ""
    google_client_secret: str = ""
    session_secret: str = "dev-only-insecure-secret"
    oauth_redirect_uri: str = "http://localhost:8000/auth/callback"
    frontend_origin: str = "http://localhost:5173"
    #: Sign-in scopes. drive.file is non-sensitive, so the shared consent screen
    #: stays in production untouched. The app creates the user's Shoots folder
    #: with it and shares that folder with ``drive_service_account``, which then
    #: watches and downloads everything dropped there (domain-model decision 11).
    oauth_scopes: str = "openid email profile https://www.googleapis.com/auth/drive.file"
    #: The identity that reads the Drive folder and runs the pipeline on Cloud Run.
    #: Locally, ADC impersonates it (``gcloud auth application-default login
    #: --impersonate-service-account``).
    drive_service_account: str = "shoots-ingest@your-gcp-project.iam.gserviceaccount.com"
    allow_dev_login: bool = False

    @property
    def dev_login_allowed(self) -> bool:
        return self.allow_dev_login and not self.cloud_state and not self.gcs_bucket

    @property
    def in_process_pipeline(self) -> bool:
        """No Pub/Sub configured: stages chain directly. Same code, no bus."""
        return not self.pubsub_push_base_url


settings = Settings()


def export_genai_environment(target: dict[str, str] | None = None) -> dict[str, str]:
    """Publish our settings as the environment variables google-genai reads."""
    import os

    target = os.environ if target is None else target

    wanted: dict[str, str] = {}
    if settings.use_vertex_ai:
        wanted["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        if settings.gcp_project:
            wanted["GOOGLE_CLOUD_PROJECT"] = settings.gcp_project
        if settings.vertex_location:
            wanted["GOOGLE_CLOUD_LOCATION"] = settings.vertex_location
        # User ADC has no quota project by default and Vertex refuses such calls
        # with a 403; google-auth honours this variable, so set it here rather
        # than depending on every dev machine having run set-quota-project.
        if settings.gcp_project:
            wanted["GOOGLE_CLOUD_QUOTA_PROJECT"] = settings.gcp_project
    elif settings.google_api_key:
        wanted["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
        wanted["GOOGLE_API_KEY"] = settings.google_api_key

    applied = {key: value for key, value in wanted.items() if not target.get(key)}
    target.update(applied)
    return applied


export_genai_environment()
