from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from notificaciones.api.app import create_app
from notificaciones.domain.models.resultado_envio import ResultadoEnvio
from notificaciones.infrastructure.config.settings import NotificacionesSettings


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.enviar.return_value = ResultadoEnvio(
        enviado=True,
        destinatarios=["test@example.com"],
    )
    svc.notificar_error.return_value = ResultadoEnvio(
        enviado=True,
        destinatarios=["test@example.com"],
    )
    return svc


@pytest.fixture
def client(mock_service):
    cfg = NotificacionesSettings(
        SMTP_HOST="smtp.test.com",
        NOTIFICACIONES_API_URL="http://127.0.0.1:8002",
    )
    with patch("notificaciones.api.app.build_notificacion_service", return_value=mock_service):
        app = create_app(cfg)
        yield TestClient(app), mock_service


def test_health(client):
    test_client, _ = client
    resp = test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["smtp_configurado"] is True


def test_enviar_ok(client):
    test_client, mock_svc = client
    resp = test_client.post(
        "/enviar",
        json={
            "id_proceso": "proceso_completo",
            "estado": "OK",
            "asunto": "[BOT] OK",
            "variables": {"fecha": "09/07/2026", "proceso_cod": "123"},
            "adjuntos": ["/tmp/archivo.txt"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["enviado"] is True
    assert data["destinatarios"] == ["test@example.com"]
    mock_svc.enviar.assert_called_once()


def test_notificar_error(client):
    test_client, mock_svc = client
    resp = test_client.post(
        "/notificar-error",
        json={
            "id_proceso": "general",
            "paso": "parse_lis",
            "causa": "Falta CADETACACO",
            "proceso_cod": "999",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["enviado"] is True
    mock_svc.notificar_error.assert_called_once_with(
        id_proceso="general",
        paso="parse_lis",
        causa="Falta CADETACACO",
        proceso_cod="999",
        asunto_prefix="[BOT COBRANZA]",
    )


def test_enviar_estado_invalido(client):
    test_client, _ = client
    resp = test_client.post(
        "/enviar",
        json={
            "id_proceso": "general",
            "estado": "INVALIDO",
            "asunto": "Test",
        },
    )
    assert resp.status_code == 422


def test_enviar_respuesta_omitida(client, mock_service):
    mock_service.enviar.return_value = ResultadoEnvio(
        omitido_motivo="SMTP no configurado",
    )
    cfg = NotificacionesSettings(NOTIFICACIONES_API_URL="http://127.0.0.1:8002")
    with patch("notificaciones.api.app.build_notificacion_service", return_value=mock_service):
        app = create_app(cfg)
        test_client = TestClient(app)
        resp = test_client.post(
            "/enviar",
            json={"id_proceso": "general", "estado": "OK", "asunto": "Test"},
        )
    assert resp.status_code == 200
    assert resp.json()["enviado"] is False
    assert "SMTP" in resp.json()["omitido_motivo"]
