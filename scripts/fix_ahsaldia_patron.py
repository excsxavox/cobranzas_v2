from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///data/BD_Cobranza.sqlite", future=True)
with engine.connect() as conn:
    nuevo_patron = "_{fecha}_*_of00255*"
    conn.execute(
        text("UPDATE parametros SET valor=:v WHERE nombre='AHSALDIA_LIS'"),
        {"v": nuevo_patron}
    )
    fila = conn.execute(
        text("SELECT valor FROM parametros WHERE nombre='AHSALDIA_LIS'")
    ).fetchone()
    print(f"AHSALDIA_LIS = {fila[0]}")
    conn.commit()
print("Listo.")
