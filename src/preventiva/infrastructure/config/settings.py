"""Configuración de preventiva-svc mediante variables de entorno / .env."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PreventivaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Base de datos (misma BD_Cobranza que carteramora) ──────────────────
    database_url: str = Field(
        default="sqlite:///data/BD_Cobranza.sqlite",
        alias="DATABASE_URL",
    )
    db_echo: bool = Field(default=False, alias="DB_ECHO")

    # ── API ────────────────────────────────────────────────────────────────
    prev_api_host: str = Field(default="127.0.0.1", alias="PREV_API_HOST")
    prev_api_port: int = Field(default=8001, alias="PREV_API_PORT")

    # ── Rutas de archivos .lis ─────────────────────────────────────────────
    prev_origen_lis: str = Field(
        default=r"\\192.168.101.155\listado_cayambe",
        alias="PREV_ORIGEN_LIS",
    )
    prev_origen_ahsaldia: str = Field(
        default=r"\\192.168.101.148\Listados_Cayambe",
        alias="PREV_ORIGEN_AHSALDIA",
    )
    prev_directorio_resultados: str = Field(
        default=r"\\192.168.101.155\depto_cobranzas\COBRANZAZ_IOI\Gestion_preventiva",
        alias="PREV_DIRECTORIO_RESULTADOS",
    )

    # ── Scheduler ─────────────────────────────────────────────────────────
    prev_ejecucion_corte: bool = Field(
        default=True,
        alias="PREV_EJECUCION_CORTE",
        description="true = usa tabla prev_dias_corte; false = evaluación diaria",
    )
    # Hora de disparo del job diario (0-23)
    prev_scheduler_hora: int = Field(default=6, alias="PREV_SCHEDULER_HORA")
    # Minuto de disparo del job diario (0-59)
    prev_scheduler_minuto: int = Field(default=30, alias="PREV_SCHEDULER_MINUTO")
    # Zona horaria del scheduler (p.ej. America/Guayaquil)
    prev_scheduler_tz: str = Field(default="America/Guayaquil", alias="PREV_SCHEDULER_TZ")
    # Días de la semana en que corre (cron: mon,tue,wed,thu,fri)
    prev_scheduler_dias: str = Field(default="mon,tue,wed,thu,fri", alias="PREV_SCHEDULER_DIAS")

    # ── Criterios de selección (valores base; se leen también de dbo.parametros) ─
    prev_numero_meses: int = Field(default=6, alias="PREV_NUMERO_MESES")
    prev_promedio_gestion: int = Field(default=5, alias="PREV_PROMEDIO_GESTION")
    prev_antiguedad: int = Field(default=6, alias="PREV_ANTIGUEDAD")
    prev_dias_retraso_recurrente: int = Field(default=5, alias="PREV_DIAS_RETRASO_RECURRENTE")
    prev_dias_antes_gestion: int = Field(default=2, alias="PREV_DIAS_ANTES_GESTION")

    # ── Feriados: clave en dbo.claves (tabla compartida con carteramora) ──
    clave_feriados: str = Field(default="feriados_catalogo", alias="CLAVE_FERIADOS")

    # ── SMTP (reutiliza los mismos parámetros de carteramora) ──────────────
    smtp_host: Optional[str] = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, alias="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from: Optional[str] = Field(default=None, alias="SMTP_FROM")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")

    # ── Logging ────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_dir: Path = Field(default=Path("logs"), alias="LOG_DIR")
