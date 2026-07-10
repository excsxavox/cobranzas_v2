import sqlite3
conn = sqlite3.connect("data/BD_Cobranza.sqlite")
try:
    conn.execute("ALTER TABLE asesores ADD COLUMN perfil VARCHAR(100) NULL")
    conn.commit()
    print("Columna perfil agregada a asesores.")
except Exception as e:
    print(f"Nota: {e}")
conn.close()
