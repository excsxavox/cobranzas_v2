from sqlalchemy import create_engine, text
engine = create_engine("sqlite:///data/BD_Cobranza.sqlite", future=True)
with engine.connect() as conn:
    for nombre, valor in [
        ("numero_meses",            "2"),
        ("dias_retencion_historial","65"),
        ("meses_consistencia_c2",   "1"),
    ]:
        conn.execute(text("UPDATE parametros SET valor=:v WHERE nombre=:n"), {"v": valor, "n": nombre})
        print(f"  {nombre:<35} = {valor}")
    conn.commit()
print("Parametros de prueba aplicados.")
