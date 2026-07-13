import sys
sys.path.insert(0, "src")
from sqlalchemy import create_engine, text

e = create_engine("sqlite:///data/BD_Cobranza.sqlite")
with e.connect() as c:
    rows = c.execute(text(
        "SELECT proceso_cod, estado, descripcion FROM logs_cp ORDER BY fecha_hora DESC LIMIT 10"
    )).fetchall()
    for r in rows:
        print(f"\n[{r[0]}] {r[1]}")
        print(f"  {r[2]}")
