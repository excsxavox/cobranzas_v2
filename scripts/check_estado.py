"""Verifica el estado actual de las tablas clave en SQLite."""
import sys
sys.path.insert(0, "src")
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///data/BD_Cobranza.sqlite")
tablas = ["asesores", "credito_rb", "historial_mora_detalle", "parametros", "logs_cp"]
with engine.connect() as c:
    for tabla in tablas:
        try:
            n = c.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
            print(f"  {tabla:<30} {n:>8} registros")
        except Exception as e:
            print(f"  {tabla:<30} ERROR: {e}")

# Archivos disponibles en New folder
from pathlib import Path
carpeta = Path(r"C:\Users\edison.cuichan\Desktop\New folder")
if carpeta.exists():
    archivos = sorted(carpeta.glob("*.lis"))
    print(f"\nArchivos .lis en '{carpeta}': {len(archivos)}")
    for a in archivos:
        print(f"  {a.name}")
else:
    print(f"\nCarpeta no encontrada: {carpeta}")
