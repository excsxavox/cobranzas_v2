import sqlite3
conn = sqlite3.connect("data/BD_Cobranza.sqlite")
conn.execute("UPDATE parametros SET valor='2' WHERE nombre='numero_meses'")
conn.execute("UPDATE parametros SET valor='65' WHERE nombre='dias_retencion_historial'")
conn.commit()
rows = conn.execute("SELECT nombre, valor FROM parametros WHERE nombre IN ('numero_meses','dias_retencion_historial')").fetchall()
for r in rows:
    print(r)
conn.close()
