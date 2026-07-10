import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Limpiar cualquier cache en memoria
import importlib, pkgutil

from sqlalchemy import create_engine, event, text
from sqlalchemy.schema import CreateTable

engine = create_engine("sqlite:///:memory:", echo=False)

import preventiva.infrastructure.persistence.models as m
from preventiva.infrastructure.persistence.base import Base

# Mostrar DDL que generaria SQLAlchemy
from preventiva.infrastructure.persistence.models.historial_mora_detalle import HistorialMoraDetalle
ddl = str(CreateTable(HistorialMoraDetalle.__table__).compile(engine))
print("DDL generado por SQLAlchemy:")
print(ddl)

# Crear tabla y revisar PRAGMA
Base.metadata.create_all(engine)
with engine.connect() as conn:
    rows = conn.execute(text("PRAGMA table_info(historial_mora_detalle)")).fetchall()
    print("\nPRAGMA real en SQLite:")
    for r in rows:
        print(r)
