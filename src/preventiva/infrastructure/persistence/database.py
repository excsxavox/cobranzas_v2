"""Inicialización de base de datos para preventiva-svc.

Reutiliza get_engine y get_session_factory de carteramora
(mismo motor SQLAlchemy, misma BD_Cobranza).
"""

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# Reutilización directa del motor de carteramora
from cobranzas.infrastructure.persistence.session import get_engine, get_session_factory

from preventiva.infrastructure.persistence.base import Base


def create_engine_preventiva(database_url: str, echo: bool = False) -> Engine:
    return get_engine(database_url, echo=echo)


def init_database(engine: Engine) -> None:
    """Crea solo las tablas del Esquema B (no toca las de carteramora)."""
    import preventiva.infrastructure.persistence.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
