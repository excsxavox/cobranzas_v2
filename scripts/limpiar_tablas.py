import sqlite3
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "BD_Cobranza.sqlite"
conn = sqlite3.connect(str(DB))

tablas = [
    "historial_mora_detalle",
    "historial_proceso",
    "ejecucion_pad",
    "logs_cp",
    "reporte_preventiva",
    "promedio_general_mes",
]

for t in tablas:
    conn.execute(f"DELETE FROM {t}")
    print(f"  {t}: vaciada")

conn.commit()

print("\nVerificacion:")
for t in tablas + ["asesores", "credito_rb"]:
    n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {n} filas")

conn.close()
