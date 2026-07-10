# Corrige columnas id con BIGINT -> INTEGER en SQLite para que autoincrement funcione.
import sqlite3
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "BD_Cobranza.sqlite"

TABLAS = {
    "historial_mora_detalle": (
        """CREATE TABLE historial_mora_detalle_new (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            proceso_cod     VARCHAR(14)   NOT NULL REFERENCES historial_proceso(proceso_cod),
            operacion       VARCHAR(30)   NOT NULL,
            identificacion  VARCHAR(20)   NULL,
            nombre          VARCHAR(200)  NULL,
            fecha_corte     DATE          NOT NULL,
            dias_mora       INTEGER       NOT NULL DEFAULT 0,
            fuente_archivo  VARCHAR(300)  NULL
        )""",
        ["id","proceso_cod","operacion","identificacion","nombre","fecha_corte","dias_mora","fuente_archivo"],
    ),
    "ejecucion_pad": (
        """CREATE TABLE ejecucion_pad_new (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            proceso_cod     VARCHAR(14)   NOT NULL REFERENCES historial_proceso(proceso_cod),
            paso_ejecucion  VARCHAR(100)  NOT NULL,
            estado          VARCHAR(10)   NOT NULL,
            descripcion     VARCHAR(4000) NULL,
            total_registros INTEGER       NULL DEFAULT 0,
            fecha_registro  DATETIME      NOT NULL
        )""",
        ["id","proceso_cod","paso_ejecucion","estado","descripcion","total_registros","fecha_registro"],
    ),
    "promedio_general_mes": (
        """CREATE TABLE promedio_general_mes_new (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            proceso_cod          VARCHAR(14)   NOT NULL REFERENCES historial_proceso(proceso_cod),
            dia_corte            INTEGER       NULL,
            operacion            VARCHAR(30)   NOT NULL,
            identificacion       VARCHAR(20)   NULL,
            nombre               VARCHAR(200)  NULL,
            telefono             VARCHAR(30)   NULL,
            tipo_operacion       VARCHAR(100)  NULL,
            dia_pago             INTEGER       NULL,
            valor_cuota          NUMERIC(18,2) NULL,
            dias_mora_actual     INTEGER       NULL,
            promedio_meses       INTEGER       NULL,
            fecha_desde          DATE          NULL,
            fecha_hasta          DATE          NULL,
            criterio_mora        BOOLEAN       NULL DEFAULT 0,
            criterio_pago_tardio BOOLEAN       NULL DEFAULT 0,
            fecha_concesion      DATE          NULL,
            antiguedad_meses     INTEGER       NULL,
            criterio_nuevo       BOOLEAN       NULL DEFAULT 0,
            criterio_alivio      BOOLEAN       NULL DEFAULT 0,
            aplica_gestion       VARCHAR(2)    NULL,
            saldo_cuenta         NUMERIC(18,2) NULL,
            valor_faltante       NUMERIC(18,2) NULL,
            cobertura            VARCHAR(10)   NULL,
            fecha_actualiza      DATETIME      NOT NULL
        )""",
        ["id","proceso_cod","dia_corte","operacion","identificacion","nombre","telefono",
         "tipo_operacion","dia_pago","valor_cuota","dias_mora_actual","promedio_meses",
         "fecha_desde","fecha_hasta","criterio_mora","criterio_pago_tardio","fecha_concesion",
         "antiguedad_meses","criterio_nuevo","criterio_alivio","aplica_gestion",
         "saldo_cuenta","valor_faltante","cobertura","fecha_actualiza"],
    ),
    "reporte_preventiva": (
        """CREATE TABLE reporte_preventiva_new (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            proceso_cod      VARCHAR(14)   NOT NULL REFERENCES historial_proceso(proceso_cod),
            fecha_proceso    DATE          NOT NULL,
            nombre           VARCHAR(200)  NULL,
            cedula           VARCHAR(20)   NULL,
            numero_operacion VARCHAR(30)   NULL,
            dias_mora        INTEGER       NULL,
            dia_pago         INTEGER       NULL,
            telefono         VARCHAR(30)   NULL,
            saldo_pendiente  NUMERIC(18,2) NULL,
            saldo_cuenta     NUMERIC(18,2) NULL,
            numero_gestion   INTEGER       NOT NULL,
            id_credito_rb    VARCHAR(30)   NULL,
            dia_corte        INTEGER       NULL
        )""",
        ["id","proceso_cod","fecha_proceso","nombre","cedula","numero_operacion",
         "dias_mora","dia_pago","telefono","saldo_pendiente","saldo_cuenta",
         "numero_gestion","id_credito_rb","dia_corte"],
    ),
    "logs_cp": (
        """CREATE TABLE logs_cp_new (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            proceso_cod       VARCHAR(14)   NOT NULL REFERENCES historial_proceso(proceso_cod),
            usuario           VARCHAR(100)  NOT NULL DEFAULT 'Bot',
            fecha_hora        DATETIME      NOT NULL,
            proceso_ejecutado VARCHAR(100)  NOT NULL,
            estado            VARCHAR(10)   NOT NULL,
            descripcion       VARCHAR(4000) NULL,
            total_registros   INTEGER       NULL DEFAULT 0,
            tiempo_total      VARCHAR(10)   NULL
        )""",
        ["id","proceso_cod","usuario","fecha_hora","proceso_ejecutado","estado",
         "descripcion","total_registros","tiempo_total"],
    ),
}

conn = sqlite3.connect(str(DB))
conn.execute("PRAGMA foreign_keys = OFF")

for tabla, (ddl_new, cols) in TABLAS.items():
    info = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
    id_col = next((r for r in info if r[1] == "id"), None)
    if id_col and id_col[2].upper() == "INTEGER":
        print(f"{tabla}: ya es INTEGER, sin cambios.")
        continue

    print(f"{tabla}: {id_col[2] if id_col else '?'} -> INTEGER...")
    tabla_new = f"{tabla}_new"
    # Eliminar _new si quedó de intento anterior
    conn.execute(f"DROP TABLE IF EXISTS {tabla_new}")
    conn.execute(ddl_new)
    cols_str = ", ".join(cols)
    # Solo migrar columnas que existen realmente en la tabla
    real_cols = [r[1] for r in info]
    migrar = [c for c in cols if c in real_cols]
    migrar_str = ", ".join(migrar)
    conn.execute(f"INSERT INTO {tabla_new} ({migrar_str}) SELECT {migrar_str} FROM {tabla}")
    conn.execute(f"DROP TABLE {tabla}")
    conn.execute(f"ALTER TABLE {tabla_new} RENAME TO {tabla}")
    print(f"  -> OK")

conn.execute("PRAGMA foreign_keys = ON")
conn.commit()
conn.close()

conn2 = sqlite3.connect(str(DB))
print("\nVerificacion final:")
for tabla in TABLAS:
    info = conn2.execute(f"PRAGMA table_info({tabla})").fetchall()
    id_col = next((r for r in info if r[1] == "id"), None)
    estado = id_col[2] if id_col else "NO EXISTE"
    print(f"  {tabla}.id = {estado}")
conn2.close()
