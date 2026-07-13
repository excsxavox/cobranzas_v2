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
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, UploadFile
from sqlalchemy import text

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

    # ── Reporte mensual ────────────────────────────────────────────────────

    @app.get(
        "/reporte/mensual",
        tags=["Reporte"],
        summary="Generar reporte mensual consolidado",
        description=(
            "Genera el Excel consolidado con todos los cortes y gestiones "
            "del mes indicado (HU líneas 275-284). "
            "Si `descargar=true` devuelve el archivo; si no, guarda en el "
            "directorio configurado y devuelve la ruta."
        ),
    )
    def reporte_mensual(
        anio: int = Query(..., description="Año (ej. 2026)"),
        mes:  int = Query(..., ge=1, le=12, description="Mes (1-12)"),
    ):
        from preventiva.infrastructure.persistence.repositories.reporte_preventiva_repository import (
            SqlAlchemyReporteRepository,
        )
        from preventiva.infrastructure.adapters.reporte_excel_writer import escribir_reporte_mensual

        repo = SqlAlchemyReporteRepository(sf)
        filas = repo.obtener_por_mes(anio, mes)
        if not filas:
            raise HTTPException(
                status_code=404,
                detail=f"No hay gestiones registradas para {mes:02d}/{anio}.",
            )

        dir_salida = Path(cfg.prev_directorio_resultados)
        ruta = escribir_reporte_mensual(filas, dir_salida, anio, mes)

        return {
            "archivo": ruta.name,
            "ruta": str(ruta),
            "total_registros": len(filas),
            "cortes": sorted({f.dia_corte for f in filas if f.dia_corte}),
        }

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
                        "FROM catalogo c "
                        "JOIN claves k ON k.id_clave = c.id_clave "
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

    # ── Historial CAMOROSICO (backfill) ──────────────────────────────────────

    @app.post(
        "/historico/cargar",
        tags=["Historial"],
        summary="Cargar historial CAMOROSICO de los últimos N meses",
        description=(
            "Recorre los archivos CAMOROSICO en PREV_ORIGEN_LIS y carga "
            "los registros en historial_mora_detalle. Útil para la puesta "
            "en producción inicial o tras una interrupción prolongada."
        ),
    )
    def cargar_historico(
        meses: int = Query(2, ge=1, le=24, description="Meses hacia atrás desde hoy"),
        forzar: bool = Query(False, description="Re-carga fechas que ya tienen datos"),
    ):
        from datetime import timedelta
        from pathlib import Path as _Path
        from preventiva.infrastructure.config.lis_resolver import LisResolver
        from preventiva.infrastructure.persistence.repositories.historial_mora_repository import (
            SqlAlchemyHistorialMoraRepository,
        )
        from preventiva.infrastructure.persistence.repositories.parametros_repository import (
            SqlAlchemyParametrosRepository,
        )
        from preventiva.infrastructure.adapters.lis_camorosico_reader import leer_camorosico

        hoy = date.today()
        ayer = hoy - timedelta(days=1)

        # Mismo cálculo que HistorialMoraHandler
        mes_ini = hoy.month - (meses - 1)
        anio_ini = hoy.year
        while mes_ini < 1:
            mes_ini += 12
            anio_ini -= 1
        fecha_ini = date(anio_ini, mes_ini, hoy.day)
        fecha_fin = ayer

        params_repo = SqlAlchemyParametrosRepository(sf)
        pat_camo = params_repo.obtener("CAMOROSICO_LIS", "")
        lis_resolver = LisResolver(
            base_lis=_Path(cfg.directorio_docsmora),
            patrones_camorosico=[pat_camo] if pat_camo else None,
        )
        mora_repo = SqlAlchemyHistorialMoraRepository(sf)

        cargados = 0
        omitidos = 0
        sin_archivo = 0
        detalle = []

        fecha_actual = fecha_ini
        while fecha_actual <= fecha_fin:
            if not forzar and mora_repo.contar_por_fecha(fecha_actual) > 0:
                omitidos += 1
                fecha_actual += timedelta(days=1)
                continue

            archivos = lis_resolver.camorosico(fecha_actual)
            if not archivos:
                sin_archivo += 1
                fecha_actual += timedelta(days=1)
                continue

            registros = leer_camorosico(archivos[0], fecha_corte=fecha_actual)
            if registros:
                proceso_cod = f"BACKFILL_{fecha_actual.strftime('%Y%m%d')}"
                guardados = mora_repo.guardar_lote(registros, proceso_cod)
                cargados += guardados
                detalle.append({
                    "fecha": fecha_actual.strftime("%d/%m/%Y"),
                    "archivo": archivos[0].name,
                    "registros": guardados,
                })
            else:
                sin_archivo += 1

            fecha_actual += timedelta(days=1)

        return {
            "ventana_desde": fecha_ini.strftime("%d/%m/%Y"),
            "ventana_hasta": fecha_fin.strftime("%d/%m/%Y"),
            "registros_cargados": cargados,
            "dias_omitidos": omitidos,
            "dias_sin_archivo": sin_archivo,
            "detalle": detalle,
        }

    # ── Carga de datos maestros ───────────────────────────────────────────────

    @app.post(
        "/recblue/cargar",
        tags=["Datos Maestros"],
        summary="Cargar archivo CSV de Recblue en credito_rb",
    )
    def cargar_recblue(file: UploadFile):
        import csv
        import io
        from datetime import date as _date

        fecha_hoy = str(_date.today())
        insertados = 0
        actualizados = 0

        contenido = file.file.read()
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                texto = contenido.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(status_code=400, detail="No se pudo decodificar el archivo.")

        reader = csv.DictReader(io.StringIO(texto))
        reader.fieldnames = [c.strip().strip('"').lower() for c in (reader.fieldnames or [])]

        with sf() as session:
            for fila in reader:
                num_op  = (fila.get("numero_operacion") or "").strip()
                id_cred = (fila.get("id_credito") or "").strip()
                if not num_op or not id_cred:
                    continue
                existe = session.execute(
                    text("SELECT COUNT(*) FROM credito_rb WHERE numero_operacion=:op"),
                    {"op": num_op}
                ).scalar()
                if existe:
                    session.execute(
                        text("UPDATE credito_rb SET id_credito=:id, fecha_carga=:f WHERE numero_operacion=:op"),
                        {"id": id_cred, "f": fecha_hoy, "op": num_op}
                    )
                    actualizados += 1
                else:
                    session.execute(
                        text("INSERT INTO credito_rb (id_credito, numero_operacion, fecha_carga) VALUES (:id, :op, :f)"),
                        {"id": id_cred, "op": num_op, "f": fecha_hoy}
                    )
                    insertados += 1
            session.commit()

        with sf() as s2:
            total = s2.execute(text("SELECT COUNT(*) FROM credito_rb")).scalar()

        return {"insertados": insertados, "actualizados": actualizados, "total_en_tabla": total}

    @app.post(
        "/asesores/cargar",
        tags=["Datos Maestros"],
        summary="Cargar archivo CSV de asesores (usuario, perfil_usuario)",
    )
    def cargar_asesores(file: UploadFile):
        import csv
        import io
        from datetime import datetime as _dt

        ahora = str(_dt.now())
        insertados = 0
        actualizados = 0

        contenido = file.file.read()
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                texto = contenido.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(status_code=400, detail="No se pudo decodificar el archivo.")

        reader = csv.DictReader(io.StringIO(texto))
        reader.fieldnames = [c.strip().strip('"').lower() for c in (reader.fieldnames or [])]

        with sf() as session:
            for fila in reader:
                usuario = (fila.get("usuario") or "").strip()
                perfil  = (fila.get("perfil_usuario") or "").strip()
                if not usuario:
                    continue
                existe = session.execute(
                    text("SELECT COUNT(*) FROM asesores WHERE nombre=:n"),
                    {"n": usuario}
                ).scalar()
                if not existe:
                    session.execute(
                        text("INSERT INTO asesores (nombre, perfil, activo, creado_en) VALUES (:n, :p, 1, :f)"),
                        {"n": usuario, "p": perfil, "f": ahora}
                    )
                    insertados += 1
                else:
                    session.execute(
                        text("UPDATE asesores SET perfil=:p WHERE nombre=:n"),
                        {"p": perfil, "n": usuario}
                    )
                    actualizados += 1
            session.commit()

        with sf() as s2:
            total = s2.execute(text("SELECT COUNT(*) FROM asesores")).scalar()

        return {"insertados": insertados, "actualizados": actualizados, "total_en_tabla": total}

    return app


# Instancia global para uvicorn: uvicorn preventiva.api.app:app
# Se crea aquí con manejo de error para no romper el import si falla la BD
try:
    app = create_app()
except Exception as _e:
    import logging as _logging
    _logging.getLogger("preventiva.api").error("Error al crear la app: %s", _e)
    raise
