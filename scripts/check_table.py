import sqlite3
conn = sqlite3.connect("data/BD_Cobranza.sqlite")
rows = conn.execute("PRAGMA table_info(historial_mora_detalle)").fetchall()
print("historial_mora_detalle schema:")
for r in rows:
    print(r)
conn.close()
