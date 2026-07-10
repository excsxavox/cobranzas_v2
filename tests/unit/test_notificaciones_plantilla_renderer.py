from notificaciones.domain.services.plantilla_renderer import parse_emails, render


def test_render_reemplaza_variables():
    plantilla = "Hola {nombre}, codigo: {proceso_cod}"
    resultado = render(plantilla, {"nombre": "Ana", "proceso_cod": "123"})
    assert resultado == "Hola Ana, codigo: 123"


def test_render_sin_variables_devuelve_plantilla():
    assert render("Texto fijo", None) == "Texto fijo"


def test_parse_emails_separados_por_punto_y_coma():
    assert parse_emails("a@x.com; b@y.com ;") == ["a@x.com", "b@y.com"]


def test_parse_emails_vacio():
    assert parse_emails(None) == []
    assert parse_emails("") == []
