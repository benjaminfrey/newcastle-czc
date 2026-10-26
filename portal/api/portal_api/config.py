from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from PORTAL_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="PORTAL_")

    database_url: str = "postgresql+psycopg://portal:portal@localhost:5433/portal"
    # Where applicants open the web app; sign-in links point here.
    public_base_url: str = "http://localhost:5173"
    # False only in local development over plain http.
    cookie_secure: bool = True
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "Town of Newcastle Permits <permits@localhost>"
    signin_link_minutes: int = 15
    session_days: int = 14
    # Sign-in link requests allowed per hour. Per email *and* address, so a stranger
    # asking for links to someone else's email cannot lock that person out; the
    # per-email ceiling still bounds mail to one inbox. IPv6 counts per /64.
    signin_limit_per_email_ip: int = 5
    signin_limit_per_email: int = 20
    signin_limit_per_ip: int = 20
    signin_limit_global: int = 500
    # Parcel data older than this is refused (lookup falls back to manual entry).
    # Only the dev VM sets allow_stale_parcels, so old lot lines never reach applicants.
    allow_stale_parcels: bool = False
    parcel_max_age_days: int = 1095
    # The screener's rules start as drafts the chair approves one by one. Production
    # refuses answers that rest on a draft; only development sets this.
    allow_draft_rules: bool = False
    # A stand-in for the staff lock (Milestone 6 builds the staff side), for tests and the
    # journeys only: an applicant may lock their own sent project. Never set in production.
    allow_test_lock: bool = False
    # Public property lookups per address per minute (spec §6). The map asks for many
    # tiles at once, so tiles have their own, larger allowance.
    lookup_limit_per_minute: int = 60
    tile_limit_per_minute: int = 1200
    # Uploads (spec §6): any S3-compatible store, reached only by the API, and clamd.
    # There is deliberately no setting that turns scanning off.
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "portal-uploads"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    clamd_host: str = "localhost"
    clamd_port: int = 3310
    upload_max_bytes: int = 26_214_400
    upload_limit_per_hour: int = 60
