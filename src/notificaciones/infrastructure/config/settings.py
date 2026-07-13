from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NotificacionesSettings(BaseSettings):
    """Configuración SMTP y API del módulo compartido de notificaciones."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    smtp_host: Optional[str] = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, alias="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from: Optional[str] = Field(default=None, alias="SMTP_FROM")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")

    notificaciones_api_host: str = Field(default="127.0.0.1", alias="NOTIFICACIONES_API_HOST")
    notificaciones_api_port: int = Field(default=8002, alias="NOTIFICACIONES_API_PORT")
    notificaciones_api_url: Optional[str] = Field(default=None, alias="NOTIFICACIONES_API_URL")
    notificaciones_api_timeout: float = Field(default=30.0, alias="NOTIFICACIONES_API_TIMEOUT")

    @model_validator(mode="after")
    def _resolver_api_url(self) -> "NotificacionesSettings":
        if not self.notificaciones_api_url:
            self.notificaciones_api_url = (
                f"http://{self.notificaciones_api_host}:{self.notificaciones_api_port}"
            )
        return self

    def smtp_habilitado(self) -> bool:
        return bool((self.smtp_host or "").strip())

    def api_base_url(self) -> str:
        return (self.notificaciones_api_url or "").rstrip("/")
