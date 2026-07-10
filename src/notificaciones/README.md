# Módulo compartido de notificaciones

Servicio hexagonal de correo reutilizable por `cobranzas`, `preventiva` y futuros módulos.

## Responsabilidades

- Leer plantillas desde `dbo.notificaciones` (`id_proceso`, `estado`, destinatarios, cuerpo).
- Renderizar variables `{clave}` en la plantilla.
- Enviar correo SMTP con destinatarios To/Cc y adjuntos opcionales.
- Devolver `ResultadoEnvio` sin tumbar el job llamador.

## Uso desde otro módulo

```python
from pathlib import Path

from notificaciones import build_notificacion_service

svc = build_notificacion_service()

resultado = svc.enviar(
    id_proceso="general",
    estado="OK",
    asunto="[Preventiva] Proceso OK",
    variables={"proceso_cod": "20260709120000", "paso": "isabel", "causa": ""},
    adjuntos=[Path("resultados/PREVENTIVA_CORTE_09072026.txt")],
)

if not resultado.enviado:
    logger.warning("Notificación omitida: %s", resultado.omitido_motivo)
```

Atajo para errores:

```python
svc.notificar_error(
    id_proceso="parse_lis",
    paso="parse_lis",
    causa="No se encontró CADETACACO",
    proceso_cod="20260709120000",
)
```

## CLI

```powershell
pip install -e .
notificaciones test-envio --proceso general --estado OK
notificaciones test-envio --estado Error --adjunto resultados\archivo.txt
```

Requiere `DATABASE_URL` (catálogo) y variables `SMTP_*` en `.env`.

## Configuración SMTP

| Variable | Descripción |
|----------|-------------|
| `SMTP_HOST` | Servidor SMTP |
| `SMTP_PORT` | Puerto (default 587) |
| `SMTP_USER` | Usuario |
| `SMTP_PASSWORD` | Contraseña |
| `SMTP_FROM` | Remitente |
| `SMTP_USE_TLS` | TLS (default true) |
| `SMTP_USE_SSL` | SSL directo (default false) |

## Integración futura

| Módulo | Cambio esperado |
|--------|-----------------|
| `preventiva` | Reemplazar `_notificar` en `preventiva_runner.py` por `NotificacionService` |
| `cobranzas` | Evolucionar `NotificacionErroresService` para delegar aquí o migrar Excel → catálogo BD |

## Estructura

```
src/notificaciones/
├── domain/          # models, ports, NotificacionService
├── infrastructure/  # SMTP, SQL catálogo, settings
└── jobs/            # container, CLI
```
