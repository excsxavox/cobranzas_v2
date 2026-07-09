"""
FastAPI app de gestión preventiva — puerto :8001.

Endpoints:
  POST /ejecutar-preventiva            Ejecuta el pipeline manualmente
  GET  /ejecutar-preventiva/{cod}      Estado de una ejecución
  GET  /historial                      Listado de ejecuciones recientes
  GET  /historial/{cod}/pasos          Pasos detallados (ejecucion_pad)
  GET  /historial/{cod}/logs           Resumen operacional (logs_cp)
  GET  /reporte                        Gestiones generadas (filtros opcionales)
  GET  /cortes                         Días de corte activos (dbo.catalogo)
  GET  /params                         Parámetros del sistema
  PUT  /params/{nombre}                Actualiza un parámetro
  GET  /health                         Liveness check
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import select, text

from preventiva.api.schemas import (
    DiaCorteResponse,
    EjecutarPreventivaRequest,
    EjecutarPreventivaResponse,
    HistorialProcesoResponse,
    LogCpResponse,
    PasoEjecucionResponse,
    ParametroResponse,
    ParametroUpdateRequest,
    ReporteGestionResponse,
)
from preventiva.infrastructure.config.settings import PreventivaSettings
from preventiva.infrastructure.persistence.database import create_engine_preventiva, init_database
from preventiva.infrastructure.persistence.models.historial_proceso import HistorialProceso
from preventiva.infrastructure.persistence.models.ejecucion_pad import EjecucionPad
from preventiva.infrastructure.persistence.models.logs_cp import LogCp
from preventiva.infrastructure.persistence.models.parametro import Parametro
from preventiva.infrastructure.persistence.models.reporte_preventiva import ReportePreventiva
from cobranzas.infrastructure.persistence.session import get_session_factory

log = logging.getLogger("preventiva.api")


def create_app(settings: Optional[PreventivaSettings] = None) -> FastAPI:
    cfg = settings or PreventivaSettings()

    app = FastAPI(
        title="Gestión Preventiva API",
        description=(
            "EPICA GRC-03 — Cooperativa 23 de Julio\n\n"
            "Permite ejecutar, monitorear y parametrizar el bot de gestión preventiva."
        ),
        version="1.0.0",
    )

    engine = create_engine_preventiva(cfg.database_url, echo=cfg.db_echo)
    init_database(engine)
    sf = get_session_factory(engine)

    # ── Health ─────────────────────────────────────────────────────────────

    @app.get("/health", tags=["Sistema"])
    def health():
        return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

    # ── Ejecución manual ───────────────────────────────────────────────────

    @app.post(
        "/ejecutar-preventiva",
        response_model=EjecutarPreventivaResponse,
        tags=["Ejecución"],
        summary="Ejecutar gestión preventiva manualmente",
    )
    def ejecutar_preventiva(body: EjecutarPreventivaRequest):
        """
        Ejecuta el pipeline completo de gestión preventiva.

        - **fecha**: `DDMMAAAA` (vacío = hoy)
        - **corte**: día de pago que dispara la gestión (ej. `15`)
        - **modo**: `manual` para ejecución ad-hoc, `corte` para scheduler, `diario` para revisión diaria
        """
        from preventiva.jobs.preventiva_runner import ejecutar_preventiva as run

        fecha_dt = None
        if body.fecha:
            try:
                fecha_dt = datetime.strptime(body.fecha, "%d%m%Y").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Fecha inválida. Usa DDMMAAAA (ej. 15072026).")

        ctx = run(
            fecha_ejecucion=fecha_dt,
            dia_corte=body.corte,
            modo=body.modo,
            settings=cfg,
        )
        return EjecutarPreventivaResponse(
            proceso_cod=ctx.proceso_cod,
            estado="OK" if ctx.ok else "ERROR",
            fecha_ejecucion=ctx.fecha_ejecucion.strftime("%d/%m/%Y"),
            ventana_historico_desde=(
                ctx.ventana_desde.strftime("%d/%m/%Y") if ctx.ventana_desde else None
            ),
            ventana_historico_hasta=(
                ctx.ventana_hasta.strftime("%d/%m/%Y") if ctx.ventana_hasta else None
            ),
            seleccionados=len(ctx.seleccionados),
            archivo_isabel=str(ctx.ruta_isabel) if ctx.ruta_isabel else None,
            archivo_reporte=str(ctx.ruta_reporte) if ctx.ruta_reporte else None,
            mensaje_error=ctx.mensaje_error or None,
        )

    @app.get(
        "/ejecutar-preventiva/{proceso_cod}",
        response_model=HistorialProcesoResponse,
        tags=["Ejecución"],
        summary="Estado de una ejecución específica",
    )
    def estado_ejecucion(proceso_cod: str):
        with sf() as session:
            hp = session.get(HistorialProceso, proceso_cod)
        if hp is None:
            raise HTTPException(status_code=404, detail="proceso_cod no encontrado")
        return HistorialProcesoResponse(
            proceso_cod=hp.proceso_cod,
            fecha_inicio=hp.fecha_inicio,
            fecha_fin=hp.fecha_fin,
            estado=hp.estado,
            numero_gestion=hp.numero_gestion,
            dia_corte=hp.dia_corte,
            modo=hp.modo,
        )

    # ── Historial ──────────────────────────────────────────────────────────

    @app.get(
        "/historial",
        response_model=List[HistorialProcesoResponse],
        tags=["Historial"],
        summary="Listado de ejecuciones recientes",
    )
    def listar_historial(
        limit: int = Query(20, ge=1, le=200, description="Máximo de registros"),
        estado: Optional[str] = Query(None, description="OK | ERROR | EN_CURSO"),
    ):
        with sf() as session:
            q = select(HistorialProceso).order_by(HistorialProceso.fecha_inicio.desc()).limit(limit)
            if estado:
                q = q.where(HistorialProceso.estado == estado.upper())
            filas = session.scalars(q).all()
        return [
            HistorialProcesoResponse(
                proceso_cod=h.proceso_cod,
                fecha_inicio=h.fecha_inicio,
                fecha_fin=h.fecha_fin,
                estado=h.estado,
                numero_gestion=h.numero_gestion,
                dia_corte=h.dia_corte,
                modo=h.modo,
            )
            for h in filas
        ]

    @app.get(
        "/historial/{proceso_cod}/pasos",
        response_model=List[PasoEjecucionResponse],
        tags=["Historial"],
        summary="Pasos detallados de una ejecución",
    )
    def pasos_ejecucion(proceso_cod: str):
        with sf() as session:
            filas = session.scalars(
                select(EjecucionPad)
                .where(EjecucionPad.proceso_cod == proceso_cod)
                .order_by(EjecucionPad.fecha_registro)
            ).all()
        if not filas:
            raise HTTPException(status_code=404, detail="Sin pasos para ese proceso_cod")
        return [
            PasoEjecucionResponse(
                id=p.id,
                paso_ejecucion=p.paso_ejecucion,
                estado=p.estado,
                descripcion=p.descripcion,
                total_registros=p.total_registros,
                fecha_registro=p.fecha_registro,
            )
            for p in filas
        ]

    @app.get(
        "/historial/{proceso_cod}/logs",
        response_model=List[LogCpResponse],
        tags=["Historial"],
        summary="Resumen operacional de una ejecución",
    )
    def logs_ejecucion(proceso_cod: str):
        with sf() as session:
            filas = session.scalars(
                select(LogCp)
                .where(LogCp.proceso_cod == proceso_cod)
                .order_by(LogCp.fecha_hora)
            ).all()
        return [
            LogCpResponse(
                id=l.id,
                proceso_ejecutado=l.proceso_ejecutado,
                estado=l.estado,
                descripcion=l.descripcion,
                total_registros=l.total_registros,
                tiempo_total=l.tiempo_total,
                fecha_hora=l.fecha_hora,
            )
            for l in filas
        ]

    # ── Reporte de gestiones ───────────────────────────────────────────────

    @app.get(
        "/reporte",
        response_model=List[ReporteGestionResponse],
        tags=["Reporte"],
        summary="Gestiones preventivas generadas",
    )
    def listar_reporte(
        cedula:          Optional[str] = Query(None, description="Filtrar por cédula"),
        numero_gestion:  Optional[int] = Query(None, description="1 | 2 | 3"),
        dia_corte:       Optional[int] = Query(None, description="Día de corte (ej. 15)"),
        limit:           int           = Query(100,  ge=1, le=1000),
    ):
        with sf() as session:
            q = (
                select(ReportePreventiva)
                .order_by(ReportePreventiva.fecha_proceso.desc(), ReportePreventiva.numero_gestion)
                .limit(limit)
            )
            if cedula:
                q = q.where(ReportePreventiva.cedula == cedula)
            if numero_gestion:
                q = q.where(ReportePreventiva.numero_gestion == numero_gestion)
            if dia_corte:
                q = q.where(ReportePreventiva.dia_corte == dia_corte)
            filas = session.scalars(q).all()
        return [
            ReporteGestionResponse(
                numero_operacion=r.numero_operacion,
                nombre=r.nombre,
                cedula=r.cedula,
                telefono=r.telefono,
                dia_pago=r.dia_pago,
                dias_mora=r.dias_mora,
                saldo_cuenta=float(r.saldo_cuenta) if r.saldo_cuenta is not None else None,
                saldo_pendiente=float(r.saldo_pendiente) if r.saldo_pendiente is not None else None,
                numero_gestion=r.numero_gestion,
                dia_corte=r.dia_corte,
                fecha_proceso=r.fecha_proceso.strftime("%d/%m/%Y"),
            )
            for r in filas
        ]

    # ── Días de corte (desde dbo.catalogo — tabla compartida) ─────────────

    @app.get(
        "/cortes",
        response_model=List[DiaCorteResponse],
        tags=["Configuración"],
        summary="Días de corte activos (prev_dias_corte en catalogo)",
    )
    def listar_cortes():
        try:
            with sf() as session:
                filas = session.execute(
                    text(
                        "SELECT c.valor, c.vigencia "
                        "FROM dbo.catalogo c "
                        "JOIN dbo.claves k ON k.id_clave = c.id_clave "
                        "WHERE k.clave = 'prev_dias_corte' "
                        "ORDER BY CAST(c.valor AS INT)"
                    )
                ).fetchall()
            return [DiaCorteResponse(valor=f[0], vigencia=bool(f[1])) for f in filas]
        except Exception as exc:
            log.warning("No se pudieron leer los cortes desde catalogo: %s", exc)
            return []

    # ── Parámetros ─────────────────────────────────────────────────────────

    @app.get(
        "/params",
        response_model=List[ParametroResponse],
        tags=["Configuración"],
        summary="Parámetros del sistema",
    )
    def listar_params():
        with sf() as session:
            filas = session.scalars(
                select(Parametro).where(Parametro.activo == True).order_by(Parametro.nombre)  # noqa: E712
            ).all()
        return [
            ParametroResponse(
                nombre=p.nombre,
                valor=p.valor,
                descripcion=p.descripcion,
                activo=p.activo,
            )
            for p in filas
        ]

    @app.put(
        "/params/{nombre}",
        response_model=ParametroResponse,
        tags=["Configuración"],
        summary="Actualizar valor de un parámetro",
    )
    def actualizar_param(nombre: str, body: ParametroUpdateRequest):
        with sf() as session:
            param = session.scalar(
                select(Parametro).where(Parametro.nombre == nombre).limit(1)
            )
            if param is None:
                raise HTTPException(status_code=404, detail=f"Parámetro '{nombre}' no encontrado")
            param.valor = body.valor
            session.commit()
            session.refresh(param)
            return ParametroResponse(
                nombre=param.nombre,
                valor=param.valor,
                descripcion=param.descripcion,
                activo=param.activo,
            )

    return app
