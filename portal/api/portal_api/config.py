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
