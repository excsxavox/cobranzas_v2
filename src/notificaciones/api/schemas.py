"""Schemas Pydantic para la API REST de notificaciones."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class EnviarNotificacionRequest(BaseModel):
    id_proceso: str = Field(..., description="Clave del catálogo dbo.notificaciones")
    estado: str = Field(..., description="OK o Error")
    asunto: str = Field(..., min_length=1)
    variables: Dict[str, str] = Field(default_factory=dict)
    adjuntos: List[str] = Field(default_factory=list)

    @field_validator("estado")
    @classmethod
    def normalizar_estado(cls, v: str) -> str:
        normalizado = v.strip()
        if normalizado.upper() == "OK":
            return "OK"
        if normalizado.lower() == "error":
            return "Error"
        raise ValueError("estado debe ser 'OK' o 'Error'")


class NotificarErrorRequest(BaseModel):
    id_proceso: str = Field(default="general")
    paso: str = Field(..., min_length=1)
    causa: str = Field(..., min_length=1)
    proceso_cod: str = Field(default="")
    asunto_prefix: str = Field(default="[BOT COBRANZA]")


class ResultadoEnvioResponse(BaseModel):
    enviado: bool
    destinatarios: List[str] = Field(default_factory=list)
    omitido_motivo: str = ""
    errores: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    smtp_configurado: bool
