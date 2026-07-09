"""
Inicializa la base de datos SQLite de desarrollo con todas las tablas
y datos semilla necesarios para ejecutar preventiva-svc localmente.

Uso:
    .venv\\Scripts\\python scripts/init_sqlite.py

Crea: data/BD_Cobranza.sqlite
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Agrega src/ al path para que los imports funcionen
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Asegura que el directorio data/ exista
(ROOT / "data").mkdir(exist_ok=True)

DB_PATH = ROOT / "data" / "BD_Cobranza.sqlite"
DATABASE_URL = f"sqlite:///{DB_PATH}"

print(f"Base de datos: {DB_PATH}")

# ── Motor y sesión ──────────────────────────────────────────────────────────
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# ── Importar todos los modelos para que sus metadatos se registren ──────────

# Tablas compartidas (carteramora)
import cobranzas.infrastructure.persistence.models  # noqa: F401
from cobranzas.infrastructure.persistence.base import Base as BaseCobranzas

# Tablas propias de preventiva
import preventiva.infrastructure.persistence.models  # noqa: F401
from preventiva.infrastructure.persistence.base import Base as BasePreventiva

# ── Crear todas las tablas ──────────────────────────────────────────────────
print("Creando tablas de carteramora (claves, catalogo, reglas, asesores…)")
BaseCobranzas.metadata.create_all(bind=engine)

print("Creando tablas de preventiva (parametros, historial, reporte…)")
BasePreventiva.metadata.create_all(bind=engine)

# Tablas que usan raw SQL (no tienen ORM model propio)
print("Creando tablas adicionales (credito_rb, notificaciones, insumos…)")
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS credito_rb (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            id_credito      TEXT    NOT NULL,
            numero_operacion TEXT   NOT NULL,
            identificacion  TEXT    NULL,
            nombre          TEXT    NULL,
            fecha_carga     TEXT    NULL
        )
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS IX_credito_rb_operacion
        ON credito_rb (numero_operacion)
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS notificaciones (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            id_proceso      TEXT NOT NULL,
            estado          TEXT NOT NULL,
            correo_para     TEXT NULL,
            correo_copia    TEXT NULL,
            plantilla_correo TEXT NULL,
            activo          INTEGER NOT NULL DEFAULT 1
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS insumos (
            insumos_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT NOT NULL UNIQUE,
            tabla       TEXT NOT NULL
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS insumo_columnas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            insumos_id  INTEGER NOT NULL REFERENCES insumos(insumos_id),
            nombre_col  TEXT NOT NULL,
            alias       TEXT NULL,
            tipo        TEXT NULL DEFAULT 'TEXT',
            requerida   INTEGER NOT NULL DEFAULT 1
        )
    """))
    conn.commit()

print("Tablas creadas.")

# ── Semillas ────────────────────────────────────────────────────────────────
ahora = datetime.now().isoformat()

with Session() as session:

    # ── 1. dbo.parametros ───────────────────────────────────────────────────
    from preventiva.infrastructure.persistence.models.parametro import Parametro

    parametros_seed = [
        # Scheduler / toggles
        ("ejecucion_corte",           "true",   "true = usa cortes (5,10,15…); false = diario"),
        ("filtro_mora_activo",        "true",   "Activa C1: mora promedio > umbral"),
        ("filtro_pago_tardio_activo", "true",   "Activa C2: pago tardío recurrente"),
        ("filtro_nuevo_activo",       "true",   "Activa C3: crédito nuevo"),
        ("filtro_alivio_activo",      "true",   "Activa C4: alivio financiero vigente"),
        ("excluir_cobertura_total",   "true",   "Excluir clientes con saldo suficiente"),
        # C1
        ("numero_meses",              "6",      "Meses de historial para mora promedio"),
        ("promedio_gestion",          "5",      "Días mínimos mora promedio (C1)"),
        ("dias_retencion_historial",  "190",    "Días máximos en historial_mora_detalle"),
        # C2
        ("dias_retraso_recurrente",   "5",      "Días mora mínimos para contar un mes (C2)"),
        ("meses_consistencia_c2",     "5",      "Meses con mora mínimos para calificar C2"),
        # C3
        ("antiguedad",                "6",      "Meses máximos desde concesión (C3)"),
        # Calendario
        ("dias_antes_gestion",        "2",      "Días hábiles antes del corte para gestionar"),
        # Feriados
        ("clave_feriados",            "feriados_catalogo", "Clave en claves con feriados"),
        # Patrones archivo
        ("CAMOROSICO_LIS",            "camorosico*_of_0.lis",    "Patrón glob CAMOROSICO"),
        ("CADETACACO_LIS",            "cadetacaco_cie*_of_0.lis","Patrón glob CADETACACO"),
        ("AHSALDIA_LIS",              "ahsaldia*_of00255.lis",   "Patrón glob AHSALDIA"),
        # Columna saldo AHSALDIA
        ("col_saldo_ahsaldia",        "SALDO DISPONIBLE",        "Cabecera saldo en ahsaldia"),
        # Recblue
        ("recblue",                   "credito_rb",              "Tabla Recblue"),
    ]

    for nombre, valor, descripcion in parametros_seed:
        existe = session.execute(
            text("SELECT COUNT(*) FROM parametros WHERE nombre = :n"),
            {"n": nombre}
        ).scalar()
        if not existe:
            session.add(Parametro(nombre=nombre, valor=valor,
                                  descripcion=descripcion, activo=True))

    session.flush()

    # ── 2. dbo.claves + dbo.catalogo ────────────────────────────────────────
    from cobranzas.infrastructure.persistence.models.clave import Clave
    from cobranzas.infrastructure.persistence.models.catalogo import Catalogo

    def _get_or_create_clave(session, clave_str, descripcion):
        clave = session.execute(
            text("SELECT id_clave FROM claves WHERE clave = :c"),
            {"c": clave_str}
        ).fetchone()
        if clave:
            return clave[0]
        obj = Clave(clave=clave_str, descripcion=descripcion,
                    fecha_creacion=datetime.now(), vigente=True,
                    fecha_modificacion=datetime.now())
        session.add(obj)
        session.flush()
        return obj.id_clave

    def _insert_catalogo(session, id_clave, valor, descripcion):
        existe = session.execute(
            text("SELECT COUNT(*) FROM catalogo WHERE id_clave=:k AND valor=:v"),
            {"k": id_clave, "v": valor}
        ).scalar()
        if not existe:
            session.add(Catalogo(
                id_clave=id_clave, valor=valor, descripcion=descripcion,
                fecha_creacion=datetime.now(), vigencia=True,
                fecha_modificacion=datetime.now()
            ))

    # Días de corte
    id_cortes = _get_or_create_clave(session, "prev_dias_corte",
                                     "Días de corte para gestión preventiva (GRC-03)")
    for dia in ["5", "10", "15", "17", "20", "24"]:
        _insert_catalogo(session, id_cortes, dia, f"Día de corte {dia}")

    # Tipos de alivio financiero
    id_alivio = _get_or_create_clave(session, "prev_alivio",
                                     "Tipos operación con alivio financiero (GRC-03)")
    for valor, desc in [
        ("NOVA23",     "Novación 2023"),
        ("NOVAMAPOYO", "Novación apoyo"),
        ("NOVAMCONAF", "Novación CONAFIPS"),
        ("NOVASRUEDM", "Novación RUEDM"),
        ("REACT23",    "Reactivación 2023"),
        ("REACTI23",   "Reactivación interna 2023"),
        ("SOLUCION",   "Plan solución"),
        ("REF23",      "Refinanciamiento 2023"),
    ]:
        _insert_catalogo(session, id_alivio, valor, desc)

    # Clave de feriados (vacía — se carga desde Excel con sync-feriados)
    _get_or_create_clave(session, "feriados_catalogo",
                         "Días feriados nacionales")

    # ── 3. dbo.notificaciones ────────────────────────────────────────────────
    notificaciones_seed = [
        ("general", "Error",
         "pgalarza@coop23dejulio.fin.ec;amontero@coop23dejulio.fin.ec",
         "Bot Gestión Preventiva — ERROR en paso: {paso}. Causa: {causa}."),
        ("general", "OK",
         "pgalarza@coop23dejulio.fin.ec;amontero@coop23dejulio.fin.ec",
         "Bot Gestión Preventiva ejecutado correctamente. proceso_cod: {proceso_cod}"),
    ]
    for id_proc, estado, correo_para, plantilla in notificaciones_seed:
        existe = session.execute(
            text("SELECT COUNT(*) FROM notificaciones WHERE id_proceso=:p AND estado=:e"),
            {"p": id_proc, "e": estado}
        ).scalar()
        if not existe:
            session.execute(
                text("INSERT INTO notificaciones "
                     "(id_proceso, estado, correo_para, plantilla_correo, activo) "
                     "VALUES (:p, :e, :cp, :pl, 1)"),
                {"p": id_proc, "e": estado, "cp": correo_para, "pl": plantilla}
            )

    # ── 4. dbo.insumos + columnas ────────────────────────────────────────────
    insumos = [
        ("cadetacaco", "cadetacaco_lis"),
        ("camorosico", "camorosico_lis"),
        ("ahsaldia",   "ahsaldia_lis"),
    ]
    for nombre, tabla in insumos:
        existe = session.execute(
            text("SELECT COUNT(*) FROM insumos WHERE nombre=:n"),
            {"n": nombre}
        ).scalar()
        if not existe:
            session.execute(
                text("INSERT INTO insumos (nombre, tabla) VALUES (:n, :t)"),
                {"n": nombre, "t": tabla}
            )

    session.flush()

    # Columnas clave de CADETACACO
    id_cade = session.execute(
        text("SELECT insumos_id FROM insumos WHERE nombre='cadetacaco'")
    ).scalar()
    columnas_cade = [
        ("OPERACIÓN",        "operacion",       "TEXT", 1),
        ("IDENTIFICACIÓN",   "identificacion",  "TEXT", 1),
        ("NOMBRE SOCIO",     "nombre",          "TEXT", 1),
        ("TIPO DE OPERACIÓN","tipo_operacion",  "TEXT", 1),
        ("DIA DE PAGO",      "dia_pago",        "INT",  1),
        ("VALOR CUOTA",      "valor_cuota",     "FLOAT",1),
        ("DÍAS MORA",        "dias_mora",       "INT",  1),
        ("FECHA CONCESIÓN",  "fecha_concesion", "TEXT", 0),
    ]
    for nombre_col, alias, tipo, requerida in columnas_cade:
        existe = session.execute(
            text("SELECT COUNT(*) FROM insumo_columnas "
                 "WHERE insumos_id=:i AND nombre_col=:n"),
            {"i": id_cade, "n": nombre_col}
        ).scalar()
        if not existe:
            session.execute(
                text("INSERT INTO insumo_columnas "
                     "(insumos_id, nombre_col, alias, tipo, requerida) "
                     "VALUES (:i, :n, :a, :t, :r)"),
                {"i": id_cade, "n": nombre_col,
                 "a": alias, "t": tipo, "r": requerida}
            )

    session.commit()

print()
print("=" * 60)
print(f"SQLite listo: {DB_PATH}")
print()
print("Tablas creadas:")
with engine.connect() as conn:
    tablas = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    ).fetchall()
    for (t,) in tablas:
        count = conn.execute(text(f"SELECT COUNT(*) FROM [{t}]")).scalar()
        print(f"  {t:<40} {count:>5} filas")
print()
print("Para usar SQLite en .env, añade o descomenta:")
print(f"  DATABASE_URL=sqlite:///{DB_PATH}")
