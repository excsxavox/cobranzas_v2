from sqlalchemy.engine import Engine

from notificaciones.infrastructure.persistence.base import Base


def init_database(engine: Engine) -> None:
    """Crea la tabla notificaciones si no existe (SQLite / dev)."""
    import notificaciones.infrastructure.persistence.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
