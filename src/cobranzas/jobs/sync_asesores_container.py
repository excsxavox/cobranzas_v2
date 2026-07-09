from typing import Optional

from cobranzas.application.use_cases.sincronizar_asesores import (
    SincronizarAsesoresUseCase,
)
from cobranzas.domain.services.sincronizar_asesores_service import (
    SincronizarAsesoresService,
)
from cobranzas.infrastructure.adapters.sql_usuarios_asesor_reader import (
    SqlUsuariosAsesorReader,
)
from cobranzas.infrastructure.config.recblue_database_url import (
    construir_url_recblue_sql_server,
)
from cobranzas.infrastructure.config.settings import Settings
from cobranzas.infrastructure.persistence.database import (
    create_engine_from_settings,
    init_database,
)
from cobranzas.infrastructure.persistence.repositories.asesor_sync_repository import (
    SqlAlchemyAsesorSyncRepository,
)
from cobranzas.infrastructure.persistence.session import get_session_factory


def build_sincronizar_asesores_use_case(
    settings: Optional[Settings] = None,
) -> SincronizarAsesoresUseCase:
    cfg = settings or Settings()

    # Conexión principal del sistema, donde se guarda la tabla local asesores.
    engine = create_engine_from_settings(cfg)
    init_database(engine)
    session_factory = get_session_factory(engine)

    # Conexión SQL Server de Recblue, ahora también usada para leer asesores.
    recblue_database_url = construir_url_recblue_sql_server(cfg)

    service = SincronizarAsesoresService(
        SqlUsuariosAsesorReader(recblue_database_url),
        SqlAlchemyAsesorSyncRepository(session_factory),
        rechazar_duplicados_excel=cfg.sync_asesores_rechazar_duplicados,
    )

    return SincronizarAsesoresUseCase(service, cfg)