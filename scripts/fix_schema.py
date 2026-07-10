"""
Verifica y corrige el schema de logs_cp en SQLite,
y muestra las cabeceras reales del archivo CADETACACO encontrado.
"""
import sys
from pathlib import Path
sys.path.insert(0, "src")

from sqlalchemy import create_engine, text
engine = create_engine("sqlite:///data/BD_Cobranza.sqlite", future=True)

with engine.connect() as conn:
    # Ver definicion real de logs_cp
    schema = conn.execute(
        text("SELECT sql FROM sqlite_master WHERE name='logs_cp'")
    ).scalar()
    print("Schema actual logs_cp:")
    print(schema)
    print()

    # Verificar si id es autoincrement real en SQLite
    pragma = conn.execute(text("PRAGMA table_info(logs_cp)")).fetchall()
    print("Columnas logs_cp:")
    for col in pragma:
        print(f"  {col}")
    print()

    # Probar insertar una fila de prueba
    try:
        conn.execute(text(
            "INSERT INTO logs_cp (proceso_cod, usuario, fecha_hora, proceso_ejecutado, estado, descripcion, total_registros)"
            " VALUES ('TEST001', 'Bot', datetime('now'), 'test', 'OK', 'test', 0)"
        ))
        last = conn.execute(text("SELECT last_insert_rowid()")).scalar()
        print(f"INSERT OK — id generado: {last}")
        conn.rollback()
    except Exception as e:
        print(f"INSERT FALLO: {e}")
        conn.rollback()

# Mostrar cabeceras del CADETACACO encontrado
import glob
base = Path(r"C:\Users\edison.cuichan\Desktop\New folder")
archivos = list(base.glob("**/cadetacaco*"))
print(f"\nArchivos CADETACACO encontrados: {len(archivos)}")
for a in archivos[:3]:
    print(f"  {a.name}")
    try:
        lineas = a.read_text(encoding="latin-1", errors="replace").splitlines()
        for i, l in enumerate(lineas[:10]):
            if "\t" in l:
                print(f"    Cabecera (línea {i}): {l[:200]}")
                break
    except Exception as e:
        print(f"    Error leyendo: {e}")
