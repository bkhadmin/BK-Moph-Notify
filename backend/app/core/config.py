from pathlib import Path
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BK-Moph Notify"
    app_env: str = "production"
    app_debug: bool = False
    app_secret_key: str = "change-me"
    app_url: str = "http://127.0.0.1:8012"

    allowed_origins: str = "http://127.0.0.1:8012"
    trusted_hosts: str = "127.0.0.1,localhost,app,app:8000,nginx,bk_app"

    session_cookie_name: str = "bk_notify_session"
    session_expire_hours: int = 12
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"

    csrf_enabled: bool = True
    csrf_cookie_name: str = "bk_notify_csrf"
    csrf_header_name: str = "x-csrf-token"

    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_database: str = "bk_moph_notify"
    mysql_user: str = "bknotify"
    mysql_password: str = "change-me"

    redis_url: str = "redis://redis:6379/0"

    internal_superadmin_username: str = "superadmin"
    internal_superadmin_password: str = "change-me"

    upload_dir: str = "/app/storage/uploads"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def allowed_origins_list(self):
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def sqlalchemy_database_uri(self) -> str:
        pwd = quote_plus(self.mysql_password)
        return f"mysql+pymysql://{self.mysql_user}:{pwd}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"


settings = Settings()
