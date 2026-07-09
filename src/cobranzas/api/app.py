import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException

from cobranzas.api.schemas import (
    EjecutarPipelineRequest,
    FinMesRunResponse,
    LisExcelRunResponse,
    PipelineRunResponse,
)
from cobranzas.infrastructure.config.settings import Settings
from cobranzas.jobs.fin_mes_runner import ejecutar_fin_mes
from cobranzas.jobs.lis_excel_runner import ejecutar_lis_a_excel
from cobranzas.jobs.pipeline_runner import ejecutar_pipeline

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Cobranzas — Mora Temprana",
    description=(
        "Ejecuta el pipeline diario (asesores, feriados, limpieza, asignación, BD).\n\n"
        "**Probar en Swagger:** `POST /pipeline` → Try it out → body "
        '`{"fecha": "05052026"}` → Execute.\n\n'
        "**Fin de mes (sin asignación):** `POST /acumulado-fin-mes` con la fecha "
        "del archivo; genera `acumulado_fin_mes_{MMDDYYYY}.xlsx` en destino/{año}/{MM}/ "
        "con columna FECHA DEL PROCESO = día hábil siguiente.\n\n"
        "**Convertir .lis a Excel:** `POST /lis-a-excel` con la fecha del lote; "
        "genera un `.xlsx` por archivo (camorosico y cadetacaco) en "
        "`destino/excel_lis/`.\n\n"
        "La fecha define la carpeta `docsmora/{año}/{MMDDYYYY}/cartera{MMDDYYYY}b/` "
        "(mes-día-año, ej. 05052026)."
    ),
    version="0.1.0",
)


def cargar_settings_para_notificacion() -> Settings:
    """
    Carga Settings solo para enviar correo.

    Tu .env puede seguir con:
        USAR_RUTAS_AUTOMATICAS=true

    Pero para notificar errores desde la API se usan rutas dummy,
    porque si la fecha no tiene carpeta, Settings falla antes de enviar correo.
    """
    return Settings(
        **{
            "USAR_RUTAS_AUTOMATICAS": False,
            "ARCHIVO_MOROSIDAD": Path("notificacion/no_aplica_morosidad.lis"),
            "ARCHIVO_CARTERA": Path("notificacion/no_aplica_cartera.lis"),
            "ARCHIVO_SALIDA_MOROSIDAD": Path("destino/notificacion_detalle_morosidad.lis"),
            "ARCHIVO_SALIDA_MORA": Path("destino/notificacion_reporte_mora.lis"),
            "ARCHIVO_SALIDA_ASIGNACION": Path("destino/notificacion_ASIGNACION.csv"),
        }
    )


def notificar_error_api(
    body: EjecutarPipelineRequest,
    origen: str,
    exc: Exception,
    mensajes_extra: Optional[list[str]] = None,
) -> None:
    """
    Envía correo de error desde la API.

    Sirve para errores que ocurren antes de que el pipeline alcance su propio
    bloque interno de notificación.

    Ejemplo:
    - No existe carpeta de lote.
    - No existe archivo camorosico/cadetacaco.
    - Error de validación antes de ejecutar la cadena completa.
    """
    try:
        from cobranzas.jobs.notificar_error import notificar_error_pipeline

        cfg = cargar_settings_para_notificacion()

        mensajes = []
        mensajes.append(f"Fecha solicitada: {body.fecha}")
        mensajes.append(f"Origen: {origen}")
        mensajes.append(str(exc))

        if mensajes_extra:
            mensajes.extend(mensajes_extra)

        notificar_error_pipeline(
            cfg,
            origen=origen,
            mensajes=mensajes,
            fecha_corte=body.fecha,
            exc=exc,
        )

        logger.info(
            "Notificación de error enviada desde API | origen=%s | fecha=%s",
            origen,
            body.fecha,
        )

    except Exception as notify_exc:
        logger.exception(
            "No se pudo enviar notificación de error desde API | "
            "origen=%s | error_original=%s | error_notificacion=%s",
            origen,
            exc,
            notify_exc,
        )


@app.get("/health", tags=["Sistema"])
def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/pipeline",
    response_model=PipelineRunResponse,
    summary="Ejecutar pipeline diario",
    tags=["Pipeline"],
)
def ejecutar_pipeline_api(body: EjecutarPipelineRequest) -> dict:
    """
    Ejecuta Jobs 0 + 0b + 1 para la fecha de corte indicada.

    Busca archivos en:
    docsmora/{año}/{MMDDYYYY}/cartera{MMDDYYYY}b/
    """
    try:
        resultado = ejecutar_pipeline(
            fecha_corte=body.fecha,
            configurar_logs=True,
            es_fin_de_mes=body.es_fin_de_mes,
        )

    except FileNotFoundError as exc:
        notificar_error_api(
            body=body,
            origen="api /pipeline - archivo o carpeta no encontrada",
            exc=exc,
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except ValueError as exc:
        notificar_error_api(
            body=body,
            origen="api /pipeline - error de validación",
            exc=exc,
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except Exception as exc:
        notificar_error_api(
            body=body,
            origen="api /pipeline - error inesperado",
            exc=exc,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    payload = resultado.to_dict()

    if not resultado.ok:
        notificar_error_api(
            body=body,
            origen="api /pipeline - resultado no exitoso",
            exc=RuntimeError(str(payload)),
            mensajes_extra=resultado.mensajes or [],
        )
        raise HTTPException(status_code=500, detail=payload)

    return payload


@app.post(
    "/lis-a-excel",
    response_model=LisExcelRunResponse,
    summary="Convertir los .lis del lote a Excel",
    tags=["Utilidades"],
)
def convertir_lis_a_excel_api(body: EjecutarPipelineRequest) -> dict:
    """
    Convierte camorosico + cadetacaco del lote indicado a .xlsx.

    Genera un Excel por archivo en destino/excel_lis/.
    """
    try:
        resultado = ejecutar_lis_a_excel(
            fecha=body.fecha,
            configurar_logs=True,
        )

    except FileNotFoundError as exc:
        notificar_error_api(
            body=body,
            origen="api /lis-a-excel - archivo o carpeta no encontrada",
            exc=exc,
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except ValueError as exc:
        notificar_error_api(
            body=body,
            origen="api /lis-a-excel - error de validación",
            exc=exc,
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except Exception as exc:
        notificar_error_api(
            body=body,
            origen="api /lis-a-excel - error inesperado",
            exc=exc,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    payload = resultado.to_dict()

    if not resultado.ok:
        notificar_error_api(
            body=body,
            origen="api /lis-a-excel - resultado no exitoso",
            exc=RuntimeError(str(payload)),
            mensajes_extra=resultado.mensajes or [],
        )
        raise HTTPException(status_code=404, detail=payload)

    return payload


@app.post(
    "/acumulado-fin-mes",
    response_model=FinMesRunResponse,
    summary="Limpieza + merge sin asignación → acumulado fin mes",
    tags=["Fin de mes"],
)
def ejecutar_acumulado_fin_mes_api(body: EjecutarPipelineRequest) -> dict:
    """
    Lee camorosico + cadetacaco (+ Recblue), limpia detalles,
    fusiona y escribe acumulado_fin_mes_{MMDDYYYY}.xlsx sin asignación ni BD.
    """
    try:
        resultado = ejecutar_fin_mes(
            fecha_corte=body.fecha,
            configurar_logs=True,
        )

    except FileNotFoundError as exc:
        notificar_error_api(
            body=body,
            origen="api /acumulado-fin-mes - archivo o carpeta no encontrada",
            exc=exc,
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except ValueError as exc:
        notificar_error_api(
            body=body,
            origen="api /acumulado-fin-mes - error de validación",
            exc=exc,
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except Exception as exc:
        notificar_error_api(
            body=body,
            origen="api /acumulado-fin-mes - error inesperado",
            exc=exc,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    payload = resultado.to_dict()

    if not resultado.ok:
        notificar_error_api(
            body=body,
            origen="api /acumulado-fin-mes - resultado no exitoso",
            exc=RuntimeError(str(payload)),
            mensajes_extra=resultado.mensajes or [],
        )
        raise HTTPException(status_code=500, detail=payload)

    return payload