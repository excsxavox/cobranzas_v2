"""
Deja en historial_mora_detalle SOLO los registros de junio 2026
para acelerar las pruebas con SQLite.
"""
import sys
sys.path.insert(0, "src")
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///data/BD_Cobranza.sqlite")
with engine.connect() as c:
    antes = c.execute(text("SELECT COUNT(*) FROM historial_mora_detalle")).scalar()
    c.execute(text(
        "DELETE FROM historial_mora_detalle WHERE fecha_corte < '2026-06-01'"
    ))
    c.execute(text("COMMIT"))
    despues = c.execute(text("SELECT COUNT(*) FROM historial_mora_detalle")).scalar()
    print(f"Antes  : {antes:,} registros")
    print(f"Despues: {despues:,} registros")
    print(f"Borrados: {antes - despues:,}")
