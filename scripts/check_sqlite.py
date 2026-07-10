import sys
sys.path.insert(0, "src")

from preventiva.infrastructure.config.settings import PreventivaSettings
from preventiva.infrastructure.persistence.database import create_engine_preventiva, init_database
from cobranzas.infrastructure.persistence.session import get_session_factory
from sqlalchemy import text

cfg = PreventivaSettings()
print(f"DATABASE_URL : {cfg.database_url}")
print(f"AHSALDIA dir : {cfg.prev_origen_ahsaldia}")
print(f"LIS dir      : {cfg.prev_origen_lis}")
print()

engine = create_engine_preventiva(cfg.database_url, echo=False)
init_database(engine)

sf = get_session_factory(engine)
with sf() as session:
    tablas = session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    ).fetchall()
    params = session.execute(
        text("SELECT nombre, valor FROM parametros ORDER BY nombre")
    ).fetchall()
    claves = session.execute(
        text("SELECT clave, descripcion FROM claves ORDER BY clave")
    ).fetchall()
    catalogo = session.execute(
        text("SELECT k.clave, c.valor FROM catalogo c JOIN claves k ON k.id_clave=c.id_clave ORDER BY k.clave, c.valor")
    ).fetchall()

print(f"Tablas en BD : {len(tablas)}")
for (t,) in tablas:
    print(f"  {t}")

print(f"\nParametros ({len(params)}):")
for n, v in params:
    print(f"  {n:<35} = {v}")

print(f"\nClaves ({len(claves)}):")
for c, d in claves:
    print(f"  {c:<30} {d}")

print(f"\nCatalogo ({len(catalogo)}):")
for k, v in catalogo:
    print(f"  [{k}] {v}")

print("\nConexion OK")
