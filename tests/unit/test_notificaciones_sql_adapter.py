"""Integración del adapter SQL con SQLite en memoria."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from notificaciones.infrastructure.adapters.sql_catalogo_notificaciones_adapter import (
    SqlCatalogoNotificacionesAdapter,
)
from notificaciones.infrastructure.persistence.database import init_database


def test_sql_catalogo_lee_plantilla_sqlite():
    engine = create_engine("sqlite:///:memory:")
    init_database(engine)
    sf = sessionmaker(bind=engine)

    with sf() as session:
        session.execute(
            text(
                """
                INSERT INTO notificaciones
                    (id_proceso, estado, correo_para, correo_copia, plantilla_correo, activo)
                VALUES
                    ('general', 'OK', 'a@x.com;b@y.com', 'c@z.com', 'Codigo: {proceso_cod}', 1)
                """
            )
        )
        session.commit()

    adapter = SqlCatalogoNotificacionesAdapter(sf)
    plantilla = adapter.obtener("general", "OK")

    assert plantilla is not None
    assert plantilla.correo_para == "a@x.com;b@y.com"
    assert plantilla.correo_copia == "c@z.com"
    assert "{proceso_cod}" in plantilla.plantilla_correo


def test_sql_catalogo_retorna_none_si_no_existe():
    engine = create_engine("sqlite:///:memory:")
    init_database(engine)
    sf = sessionmaker(bind=engine)

    adapter = SqlCatalogoNotificacionesAdapter(sf)
    assert adapter.obtener("inexistente", "OK") is None
