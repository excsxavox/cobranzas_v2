from urllib.parse import quote_plus

from cobranzas.infrastructure.config.settings import Settings


def construir_url_recblue_sql_server(settings: Settings) -> str:
    if not settings.recblue_db_server or not settings.recblue_db_database:
        raise ValueError(
            "RECBLUE_DB_SERVER y RECBLUE_DB_DATABASE son obligatorios "
            "cuando USAR_RECBLUE_SQL=true"
        )

    driver = quote_plus(settings.recblue_db_driver or "ODBC Driver 18 for SQL Server")
    servidor = settings.recblue_db_server.strip()
    database = settings.recblue_db_database.strip()

    parametros = [f"driver={driver}"]

    if settings.recblue_db_encrypt:
        parametros.append(f"Encrypt={settings.recblue_db_encrypt}")

    if settings.recblue_db_trust_server_certificate:
        parametros.append(
            f"TrustServerCertificate={settings.recblue_db_trust_server_certificate}"
        )

    usa_windows = (settings.recblue_db_trusted_connection or "").strip().lower() in (
        "yes",
        "true",
        "1",
    )

    if usa_windows:
        parametros.append("trusted_connection=yes")
        query = "&".join(parametros)
        return f"mssql+pyodbc://@{servidor}/{database}?{query}"

    usuario = quote_plus(settings.recblue_db_user or "")
    password = quote_plus(settings.recblue_db_password or "")

    if not usuario or not password:
        raise ValueError(
            "RECBLUE_DB_USER y RECBLUE_DB_PASSWORD son obligatorios "
            "si no usa RECBLUE_DB_TRUSTED_CONNECTION=yes"
        )

    query = "&".join(parametros)
    return f"mssql+pyodbc://{usuario}:{password}@{servidor}/{database}?{query}"