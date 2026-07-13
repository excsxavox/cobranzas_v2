"""Inicialización de base de datos para preventiva-svc.

Al arrancar la aplicación:
  1. Crea todas las tablas del Esquema B (solo si no existen).
  2. Siembra datos base en parametros, notificaciones, insumos e
     insumos_columnas si las tablas están vacías.
  3. Inserta las claves prev_dias_corte y prev_alivio en las tablas
     compartidas (claves / catalogo) si aún no existen.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from cobranzas.infrastructure.persistence.session import get_engine
from preventiva.infrastructure.persistence.base import Base

log = logging.getLogger("preventiva.database")


def create_engine_preventiva(database_url: str, echo: bool = False) -> Engine:
    return get_engine(database_url, echo=echo)


def init_database(engine: Engine) -> None:
    """Crea tablas del Esquema B y siembra datos base (idempotente)."""
    import preventiva.infrastructure.persistence.models  # noqa: F401  registra los modelos

    Base.metadata.create_all(bind=engine, checkfirst=True)
    log.info("Tablas preventiva verificadas / creadas.")

    with engine.begin() as conn:
        _seed_parametros(conn)
        _seed_notificaciones(conn)
        _seed_insumos(conn)
        _seed_claves_catalogo(conn)

    log.info("Semillas de base de datos aplicadas.")


# ──────────────────────────────────────────────────────────────────────────────
# SEMILLAS
# ──────────────────────────────────────────────────────────────────────────────

def _seed_parametros(conn) -> None:
    """Inserta parámetros base solo si la tabla está vacía."""
    total = conn.execute(text("SELECT COUNT(*) FROM parametros")).scalar()
    if total and total > 0:
        return

    parametros = [
        # Scheduler
        ("ejecucion_corte", "true",
         "true = usa fechas de corte (5,10,15,17,20,24); false = evaluación diaria"),
        # Toggles de filtros
        ("filtro_mora_activo", "true",
         "Activa Criterio 1: mora promedio >= umbral en los últimos N meses"),
        ("filtro_pago_tardio_activo", "true",
         "Activa Criterio 2: pago tardío recurrente"),
        ("filtro_nuevo_activo", "true",
         "Activa Criterio 3: crédito nuevo (antigüedad <= N meses)"),
        ("filtro_alivio_activo", "true",
         "Activa Criterio 4: alivio financiero vigente"),
        ("excluir_cobertura_total", "true",
         "Si true, excluye clientes con saldo suficiente para cubrir toda la cuota"),
        # Criterio 1
        ("numero_meses", "6",
         "Número de meses a considerar para cálculo de mora promedio"),
        ("promedio_gestion", "5",
         "Días mínimos de mora promedio por mes para incluir cliente"),
        ("dias_retencion_historial", "190",
         "Días máximos a conservar en historial_mora_detalle (~6 meses)"),
        # Criterio 2
        ("dias_retraso_recurrente", "5",
         "Días de mora mínimos para que un mes cuente como mes con mora (umbral C2)"),
        ("meses_consistencia_c2", "5",
         "Cantidad mínima de meses con mora en la ventana para calificar C2"),
        # Criterio 3
        ("antiguedad", "6",
         "Meses máximos para considerar desde la nueva operación"),
        # Criterio 4
        ("considerar_novacion", "Si",
         "Considerar clientes con novación vigente"),
        ("considerar_refinanciado", "Si",
         "Considerar clientes refinanciados"),
        ("considerar_reestructurado", "Si",
         "Considerar clientes reestructurados"),
        # Calendario de gestiones
        ("dias_antes_gestion", "2",
         "Días antes del vencimiento para ejecutar gestión preventiva"),
        ("modo_calendario", "mrk_cp",
         "mrk_cp = +N días hábiles antes del vencimiento"),
        # Feriados
        ("clave_feriados", "feriados_catalogo",
         "Clave en claves que contiene el catálogo de feriados"),
        # Fuentes de datos
        ("separador_decimal", ".",
         "Separador decimal en archivos .lis"),
        ("origen_lis", r"\\192.168.101.155\listado_cayambe\\",
         "Ruta base carpetas CAMOROSICO y CADETACACO"),
        ("origen_ahsaldia", r"\\192.168.101.148\Listados_Cayambe\\",
         "Ruta base carpeta ahsaldia"),
        # Patrones de archivo
        ("CARTERA_PREF_LIS", "cartera", "Prefijo subcarpeta cartera"),
        ("CARTERA_FIN_LIS", "b", "Sufijo subcarpeta cartera"),
        ("CAMOROSICO_LIS", "camorosico*_of_0.lis", "Patrón glob CAMOROSICO"),
        ("CADETACACO_LIS", "cadetacaco_cie*_of_0.lis", "Patrón glob CADETACACO"),
        ("AHSALDIA_PREF_LIS", "ahorros", "Prefijo subcarpeta ahsaldia"),
        ("AHSALDIA_FIN_LIS", "b", "Sufijo subcarpeta ahsaldia"),
        ("AHSALDIA_LIS", "_{fecha}_*_of00255*", "Patrón glob archivo ahsaldia"),
        ("col_saldo_ahsaldia", "SALDO DISPONIBLE",
         "Cabecera columna saldo disponible en ahsaldia"),
        # Salidas
        ("resultados",
         r"\\192.168.101.155\depto_cobranzas\COBRANZAZ_IOI\Gestion_preventiva\[yyyy]\[mmyyyy]",
         "Ruta base para PREVENTIVA_CORTE_*.txt y REPORTE_PREVENTIVA_*.xls"),
        # Recblue
        ("recblue", "credito_rb", "Tabla Recblue compartida en BD_Cobranza"),
        ("col_id_credito", "id_credito", "Columna ID crédito Recblue"),
        ("col_operacion", "numero_operacion", "Columna número operación Recblue"),
        # Base de datos
        ("base", "BD_Cobranza", "Base de datos activa"),
        # SMTP
        ("smtp_correo", "smtp.gmail.com", "Servidor SMTP"),
        ("smtp_usuario", "test@gmail.com", "Usuario SMTP"),
        ("smtp_pass", "", "Contraseña SMTP"),
        ("smtp_puerto", "587", "Puerto SMTP"),
        ("smtp_tls", "True", "Usar TLS"),
    ]

    for nombre, valor, descripcion in parametros:
        conn.execute(
            text(
                "INSERT INTO parametros (nombre, valor, descripcion, activo) "
                "VALUES (:n, :v, :d, 1)"
            ),
            {"n": nombre, "v": valor, "d": descripcion},
        )
    log.info("Semilla parametros: %d registros insertados.", len(parametros))


def _seed_notificaciones(conn) -> None:
    """Inserta notificaciones base solo si la tabla está vacía."""
    total = conn.execute(text("SELECT COUNT(*) FROM notificaciones")).scalar()
    if total and total > 0:
        return

    notificaciones = [
        ("general", "Error",
         "pgalarza@coop23dejulio.fin.ec;amontero@coop23dejulio.fin.ec",
         None,
         "Estimados, el bot de Gestión Preventiva reporta un ERROR.\n"
         "Paso: {paso}\nCausa: {causa}\nproceso_cod: {proceso_cod}"),
        ("general", "OK",
         "pgalarza@coop23dejulio.fin.ec;amontero@coop23dejulio.fin.ec",
         None,
         "Proceso ejecutado correctamente. proceso_cod: {proceso_cod}"),
        ("proceso_completo", "OK",
         "pgalarza@coop23dejulio.fin.ec;amontero@coop23dejulio.fin.ec",
         None,
         "Estimados, la Gestión Preventiva del {fecha} finalizó correctamente.\n"
         "Gestión número: {numero_gestion}. Se adjuntan los archivos generados.\n"
         "proceso_cod: {proceso_cod}"),
        ("cartera_mora", "Error",
         "pgalarza@coop23dejulio.fin.ec;amontero@coop23dejulio.fin.ec",
         None,
         "Se detectó un error en el procesamiento de cartera en mora.\n"
         "Origen: {paso}\nDetalle:\n{causa}"),
    ]

    for id_proceso, estado, correo_para, correo_copia, plantilla in notificaciones:
        conn.execute(
            text(
                "INSERT INTO notificaciones "
                "(id_proceso, estado, correo_para, correo_copia, plantilla_correo, activo) "
                "VALUES (:ip, :e, :cp, :cc, :pl, 1)"
            ),
            {"ip": id_proceso, "e": estado, "cp": correo_para,
             "cc": correo_copia, "pl": plantilla},
        )
    log.info("Semilla notificaciones: %d registros insertados.", len(notificaciones))


def _seed_insumos(conn) -> None:
    """Inserta insumos y sus columnas solo si la tabla está vacía."""
    total = conn.execute(text("SELECT COUNT(*) FROM insumos")).scalar()
    if total and total > 0:
        return

    conn.execute(
        text("INSERT INTO insumos (nombre, tabla) VALUES (:n, :t)"),
        [
            {"n": "cadetacaco", "t": "cadetacaco_lis"},
            {"n": "camorosico", "t": "camorosico_lis"},
            {"n": "ahsaldia",   "t": "ahsaldia_lis"},
        ],
    )

    id_cade = conn.execute(
        text("SELECT insumos_id FROM insumos WHERE nombre='cadetacaco'")
    ).scalar()
    id_camo = conn.execute(
        text("SELECT insumos_id FROM insumos WHERE nombre='camorosico'")
    ).scalar()
    id_ahs = conn.execute(
        text("SELECT insumos_id FROM insumos WHERE nombre='ahsaldia'")
    ).scalar()

    columnas = [
        # cadetacaco
        (id_cade, "OPERACIÓN",        "operacion",       "VARCHAR",  "30"),
        (id_cade, "DÍAS MORA",        "dias_mora",        "INT",      None),
        (id_cade, "DIA DE PAGO",      "dia_pago",         "INT",      None),
        (id_cade, "TIPO DE OPERACIÓN","tipo_operacion",   "VARCHAR",  "100"),
        (id_cade, "VALOR CUOTA",      "valor_cuota",      "DECIMAL",  "18,2"),
        (id_cade, "NOMBRE SOCIO",     "nombre",           "VARCHAR",  "200"),
        (id_cade, "IDENTIFICACIÓN",   "identificacion",   "VARCHAR",  "20"),
        (id_cade, "FECHA CONCESIÓN",  "fecha_concesion",  "DATE",     None),
        # camorosico
        (id_camo, "OPERACIÓN",        "operacion",        "VARCHAR",  "30"),
        (id_camo, "DÍAS ATRASO",      "dias_mora",        "INT",      None),
        (id_camo, "IDENTIFICACIÓN",   "identificacion",   "VARCHAR",  "20"),
        (id_camo, "NOMBRE SOCIO",     "nombre",           "VARCHAR",  "200"),
        (id_camo, "TELÉFONO",         "telefono",         "VARCHAR",  "30"),
        # ahsaldia
        (id_ahs,  "SALDO DISPONIBLE", "saldo_disponible", "DECIMAL",  "18,2"),
        (id_ahs,  "IDENTIFICACIÓN",   "identificacion",   "VARCHAR",  "20"),
    ]

    for insumos_id, col_insumo, col_tabla, tipo, longitud in columnas:
        conn.execute(
            text(
                "INSERT INTO insumos_columnas "
                "(insumos_id, columna_insumo, columna_tabla, tipo_dato, longitud_campo, activo) "
                "VALUES (:iid, :ci, :ct, :td, :lc, 1)"
            ),
            {"iid": insumos_id, "ci": col_insumo, "ct": col_tabla,
             "td": tipo, "lc": longitud},
        )
    log.info("Semilla insumos: 3 insumos y %d columnas insertadas.", len(columnas))


def _seed_claves_catalogo(conn) -> None:
    """Inserta prev_dias_corte y prev_alivio en las tablas compartidas.

    Se ejecuta con manejo de errores para no interrumpir el arranque si las
    tablas compartidas (claves / catalogo) no existen todavía en la BD.
    """
    try:
        # ── prev_dias_corte ───────────────────────────────────────────────
        existe_clave = conn.execute(
            text("SELECT COUNT(*) FROM claves WHERE clave = 'prev_dias_corte'")
        ).scalar()
        if not existe_clave:
            conn.execute(
                text(
                    "INSERT INTO claves (clave, descripcion, fecha_creacion, vigente, fecha_modificacion) "
                    "VALUES ('prev_dias_corte', 'Días de corte para gestión preventiva (GRC-03)', "
                    "CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)"
                )
            )

        id_corte = conn.execute(
            text("SELECT id_clave FROM claves WHERE clave = 'prev_dias_corte'")
        ).scalar()

        for dia in ("5", "10", "15", "17", "20", "24"):
            existe_val = conn.execute(
                text("SELECT COUNT(*) FROM catalogo WHERE id_clave=:k AND valor=:v"),
                {"k": id_corte, "v": dia},
            ).scalar()
            if not existe_val:
                conn.execute(
                    text(
                        "INSERT INTO catalogo "
                        "(id_clave, valor, descripcion, fecha_creacion, vigencia, fecha_modificacion) "
                        "VALUES (:k, :v, 'Día de corte preventiva', CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)"
                    ),
                    {"k": id_corte, "v": dia},
                )

        # ── prev_alivio ───────────────────────────────────────────────────
        existe_alivio = conn.execute(
            text("SELECT COUNT(*) FROM claves WHERE clave = 'prev_alivio'")
        ).scalar()
        if not existe_alivio:
            conn.execute(
                text(
                    "INSERT INTO claves (clave, descripcion, fecha_creacion, vigente, fecha_modificacion) "
                    "VALUES ('prev_alivio', 'Tipos de operación con alivio financiero (GRC-03)', "
                    "CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)"
                )
            )

        id_alivio = conn.execute(
            text("SELECT id_clave FROM claves WHERE clave = 'prev_alivio'")
        ).scalar()

        tipos_alivio = [
            ("NOVA23",      "Novación 2023"),
            ("NOVAMAPOYO",  "Novación apoyo"),
            ("NOVAMCONAF",  "Novación CONAFIPS"),
            ("NOVASRUEDM",  "Novación RUEDM"),
            ("REACT23",     "Reactivación 2023"),
            ("REACTI23",    "Reactivación interna 2023"),
            ("SOLUCION",    "Plan solución"),
            ("REF23",       "Refinanciamiento 2023"),
        ]
        for valor, desc in tipos_alivio:
            existe_val = conn.execute(
                text("SELECT COUNT(*) FROM catalogo WHERE id_clave=:k AND valor=:v"),
                {"k": id_alivio, "v": valor},
            ).scalar()
            if not existe_val:
                conn.execute(
                    text(
                        "INSERT INTO catalogo "
                        "(id_clave, valor, descripcion, fecha_creacion, vigencia, fecha_modificacion) "
                        "VALUES (:k, :v, :d, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)"
                    ),
                    {"k": id_alivio, "v": valor, "d": desc},
                )

        log.info("Semilla claves/catalogo (prev_dias_corte, prev_alivio) aplicada.")

    except Exception as exc:
        log.warning(
            "No se pudieron sembrar claves/catalogo (tablas compartidas aún no disponibles): %s",
            exc,
        )
