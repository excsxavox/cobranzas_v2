from unittest.mock import MagicMock, patch

import httpx

from notificaciones.infrastructure.clients.notificaciones_api_client import (
    NotificacionesApiClient,
)


def test_client_enviar_ok():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "enviado": True,
        "destinatarios": ["a@example.com"],
        "omitido_motivo": "",
        "errores": [],
    }

    mock_http = MagicMock()
    mock_http.post.return_value = mock_response
    mock_http.__enter__ = MagicMock(return_value=mock_http)
    mock_http.__exit__ = MagicMock(return_value=False)

    client = NotificacionesApiClient("http://127.0.0.1:8002")
    with patch("notificaciones.infrastructure.clients.notificaciones_api_client.httpx.Client", return_value=mock_http):
        resultado = client.enviar(
            id_proceso="proceso_completo",
            estado="OK",
            asunto="Test",
            variables={"fecha": "09/07/2026"},
        )

    assert resultado.enviado is True
    assert resultado.destinatarios == ["a@example.com"]
    mock_http.post.assert_called_once()
    url, = mock_http.post.call_args[0]
    assert url == "http://127.0.0.1:8002/enviar"


def test_client_notificar_error_ok():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "enviado": True,
        "destinatarios": ["b@example.com"],
        "omitido_motivo": "",
        "errores": [],
    }

    mock_http = MagicMock()
    mock_http.post.return_value = mock_response
    mock_http.__enter__ = MagicMock(return_value=mock_http)
    mock_http.__exit__ = MagicMock(return_value=False)

    client = NotificacionesApiClient("http://127.0.0.1:8002")
    with patch("notificaciones.infrastructure.clients.notificaciones_api_client.httpx.Client", return_value=mock_http):
        resultado = client.notificar_error(
            id_proceso="cartera_mora",
            paso="pipeline",
            causa="Error de prueba",
        )

    assert resultado.enviado is True
    payload = mock_http.post.call_args[1]["json"]
    assert payload["id_proceso"] == "cartera_mora"
    assert payload["paso"] == "pipeline"


def test_client_error_red_no_propaga():
    mock_http = MagicMock()
    mock_http.post.side_effect = httpx.ConnectError("Connection refused")
    mock_http.__enter__ = MagicMock(return_value=mock_http)
    mock_http.__exit__ = MagicMock(return_value=False)

    client = NotificacionesApiClient("http://127.0.0.1:8002", timeout=1.0)
    with patch("notificaciones.infrastructure.clients.notificaciones_api_client.httpx.Client", return_value=mock_http):
        resultado = client.enviar("general", "OK", "Asunto")

    assert resultado.enviado is False
    assert resultado.errores
