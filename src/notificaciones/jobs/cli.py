"""CLI del módulo compartido de notificaciones."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from notificaciones.jobs.container import build_notificacion_service

log = logging.getLogger("notificaciones.cli")


def _configurar_logging(nivel: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, nivel.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def cmd_test_envio(args: argparse.Namespace) -> int:
    svc = build_notificacion_service()
    variables = {
        "paso": "test-envio",
        "causa": "Prueba manual desde CLI",
        "proceso_cod": "TEST000",
    }
    adjuntos = [Path(p) for p in args.adjunto] if args.adjunto else None

    resultado = svc.enviar(
        id_proceso=args.proceso,
        estado=args.estado,
        asunto=args.asunto,
        variables=variables,
        adjuntos=adjuntos,
    )

    if resultado.enviado:
        log.info("Correo enviado a: %s", ", ".join(resultado.destinatarios))
        return 0

    if resultado.omitido_motivo:
        log.warning("Envío omitido: %s", resultado.omitido_motivo)
    for error in resultado.errores:
        log.error("Error: %s", error)
    return 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="notificaciones",
        description="Módulo compartido de notificaciones por correo",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Nivel de logging (DEBUG, INFO, WARNING, ERROR)",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    test = sub.add_parser(
        "test-envio",
        help="Envía un correo de prueba usando el catálogo dbo.notificaciones",
    )
    test.add_argument("--proceso", default="general", help="id_proceso del catálogo")
    test.add_argument(
        "--estado",
        default="OK",
        choices=["OK", "Error"],
        help="Estado de la plantilla (OK / Error)",
    )
    test.add_argument(
        "--asunto",
        default="[Notificaciones] Prueba de envío",
        help="Asunto del correo",
    )
    test.add_argument(
        "--adjunto",
        action="append",
        default=[],
        help="Ruta de archivo adjunto (repetible)",
    )
    test.set_defaults(handler=cmd_test_envio)

    args = parser.parse_args(argv)
    _configurar_logging(args.log_level)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
