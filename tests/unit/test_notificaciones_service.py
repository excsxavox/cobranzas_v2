from pathlib import Path
from typing import Dict, List, Optional, Tuple

from notificaciones.domain.models.mensaje_correo import MensajeCorreo
from notificaciones.domain.models.plantilla_notificacion import PlantillaNotificacion
from notificaciones.domain.services.notificacion_service import NotificacionService


class FakeCatalogo:
    def __init__(self, plantillas: Dict[Tuple[str, str], PlantillaNotificacion]) -> None:
        self._plantillas = plantillas

    def obtener(self, id_proceso: str, estado: str) -> Optional[PlantillaNotificacion]:
        return self._plantillas.get((id_proceso, estado))


class FakeCorreo:
    def __init__(self) -> None:
        self.mensajes: List[MensajeCorreo] = []
        self.debe_fallar = False

    def enviar(self, mensaje: MensajeCorreo) -> None:
        if self.debe_fallar:
            raise RuntimeError("SMTP caído")
        self.mensajes.append(mensaje)


def _plantilla(
    id_proceso: str = "general",
    estado: str = "OK",
    para: str = "test@example.com",
    copia: Optional[str] = None,
    cuerpo: str = "Proceso {proceso_cod} OK",
) -> PlantillaNotificacion:
    return PlantillaNotificacion(
        id_proceso=id_proceso,
        estado=estado,
        correo_para=para,
        correo_copia=copia,
        plantilla_correo=cuerpo,
    )


def test_enviar_ok_con_plantilla_y_smtp():
    catalogo = FakeCatalogo({("general", "OK"): _plantilla()})
    correo = FakeCorreo()
    svc = NotificacionService(catalogo, correo, smtp_configurado=True)

    resultado = svc.enviar(
        id_proceso="general",
        estado="OK",
        asunto="Prueba",
        variables={"proceso_cod": "ABC"},
    )

    assert resultado.enviado is True
    assert resultado.destinatarios == ["test@example.com"]
    assert len(correo.mensajes) == 1
    assert correo.mensajes[0].cuerpo == "Proceso ABC OK"


def test_fallback_a_general_si_no_hay_plantilla_especifica():
    catalogo = FakeCatalogo({("general", "Error"): _plantilla(estado="Error", cuerpo="Error: {causa}")})
    correo = FakeCorreo()
    svc = NotificacionService(catalogo, correo, smtp_configurado=True)

    resultado = svc.notificar_error("parse_lis", paso="parse_lis", causa="archivo ausente")

    assert resultado.enviado is True
    assert correo.mensajes[0].cuerpo == "Error: archivo ausente"


def test_omite_si_smtp_no_configurado():
    catalogo = FakeCatalogo({("general", "OK"): _plantilla()})
    svc = NotificacionService(catalogo, None, smtp_configurado=False)

    resultado = svc.enviar("general", "OK", "Asunto")

    assert resultado.enviado is False
    assert "SMTP" in resultado.omitido_motivo


def test_omite_si_no_hay_plantilla():
    svc = NotificacionService(FakeCatalogo({}), FakeCorreo(), smtp_configurado=True)

    resultado = svc.enviar("inexistente", "OK", "Asunto")

    assert resultado.enviado is False
    assert "Sin plantilla" in resultado.omitido_motivo


def test_adjunto_inexistente_se_ignora(tmp_path: Path):
    catalogo = FakeCatalogo({("general", "OK"): _plantilla()})
    correo = FakeCorreo()
    svc = NotificacionService(catalogo, correo, smtp_configurado=True)

    adjunto_real = tmp_path / "dato.txt"
    adjunto_real.write_text("contenido", encoding="utf-8")

    resultado = svc.enviar(
        id_proceso="general",
        estado="OK",
        asunto="Con adjuntos",
        adjuntos=[tmp_path / "no_existe.txt", adjunto_real],
    )

    assert resultado.enviado is True
    assert len(correo.mensajes[0].adjuntos) == 1
    assert correo.mensajes[0].adjuntos[0].name == "dato.txt"


def test_error_smtp_no_propaga_excepcion():
    catalogo = FakeCatalogo({("general", "OK"): _plantilla()})
    correo = FakeCorreo()
    correo.debe_fallar = True
    svc = NotificacionService(catalogo, correo, smtp_configurado=True)

    resultado = svc.enviar("general", "OK", "Asunto")

    assert resultado.enviado is False
    assert resultado.errores


def test_incluye_cc_en_destinatarios():
    catalogo = FakeCatalogo(
        {("general", "OK"): _plantilla(para="a@x.com", copia="b@y.com;c@z.com")}
    )
    correo = FakeCorreo()
    svc = NotificacionService(catalogo, correo, smtp_configurado=True)

    resultado = svc.enviar("general", "OK", "Asunto")

    assert resultado.enviado is True
    assert set(resultado.destinatarios) == {"a@x.com", "b@y.com", "c@z.com"}
    assert list(correo.mensajes[0].cc) == ["b@y.com", "c@z.com"]
