# Módulo compartido de notificaciones

Servicio hexagonal de correo reutilizable por `cobranzas`, `preventiva` y futuros módulos.

## Responsabilidades

- Leer plantillas desde `dbo.notificaciones` (`id_proceso`, `estado`, destinatarios, cuerpo).
- Renderizar variables `{clave}` en la plantilla.
- Enviar correo SMTP con destinatarios To/Cc y adjuntos opcionales.
- Exponer API REST (`:8002`) para consumo HTTP desde otros módulos.
- Devolver `ResultadoEnvio` sin tumbar el job llamador.

## API REST (`:8002`)

```powershell
pip install -e ".[api]"
notificaciones api
```

| Endpoint | Descripción |
|----------|-------------|
| `GET /health` | Liveness + `smtp_configurado` |
| `POST /enviar` | Envío según catálogo |
| `POST /notificar-error` | Atajo para plantillas `Error` |

### Contrato `POST /enviar`

```json
{
  "id_proceso": "proceso_completo",
  "estado": "OK",
  "asunto": "[BOT COBRANZA PREVENTIVA] Proceso 09/07/2026 finalizado OK",
  "variables": {
    "fecha": "09/07/2026",
    "numero_gestion": "1",
    "proceso_cod": "20260709120000"
  },
  "adjuntos": ["D:/resultados/PREVENTIVA_CORTE_09072026.txt"]
}
```

Placeholders en plantillas: `{paso}`, `{causa}`, `{proceso_cod}`, `{fecha}`, `{numero_gestion}`.

### Contrato `POST /notificar-error`

```json
{
  "id_proceso": "general",
  "paso": "parse_lis",
  "causa": "No se encontró CADETACACO",
  "proceso_cod": "20260709120000",
  "asunto_prefix": "[BOT COBRANZA PREVENTIVA]"
}
```

## Consumo desde otro módulo (HTTP)

```python
from notificaciones import build_notificaciones_api_client

client = build_notificaciones_api_client()

resultado = client.enviar(
    id_proceso="proceso_completo",
    estado="OK",
    asunto="[Preventiva] Proceso OK",
    variables={"proceso_cod": "20260709120000", "fecha": "09/07/2026"},
    adjuntos=["resultados/PREVENTIVA_CORTE_09072026.txt"],
)
```

Atajo para errores:

```python
client.notificar_error(
    id_proceso="cartera_mora",
    paso="pipeline",
    causa="Detalle del error",
    asunto_prefix="[Cartera Mora]",
)
```

Configurar en `.env`:

| Variable | Default |
|----------|---------|
| `NOTIFICACIONES_API_URL` | `http://127.0.0.1:8002` |
| `NOTIFICACIONES_API_TIMEOUT` | `30` |

## Uso in-process (servidor / tests)

```python
from notificaciones import build_notificacion_service

svc = build_notificacion_service()
resultado = svc.enviar(...)
```

## CLI

```powershell
notificaciones api                    # API REST :8002
notificaciones test-envio --estado OK # Prueba SMTP + catálogo
```

Requiere `DATABASE_URL` (catálogo) y `SMTP_*` en el servicio de notificaciones.

## Configuración SMTP (servicio)

| Variable | Descripción |
|----------|-------------|
| `SMTP_HOST` | Servidor SMTP |
| `SMTP_PORT` | Puerto (default 587) |
| `SMTP_USER` | Usuario |
| `SMTP_PASSWORD` | Contraseña |
| `SMTP_FROM` | Remitente |
| `SMTP_USE_TLS` | TLS (default true) |
| `SMTP_USE_SSL` | SSL directo (default false) |

## Integración

| Módulo | Consumo |
|--------|---------|
| `preventiva` | `preventiva_runner._notificar` → API (`proceso_completo` OK + adjuntos) |
| `cobranzas` | `notificar_error_pipeline` → API (`cartera_mora` Error) |

## Estructura

```
src/notificaciones/
├── api/             # FastAPI (:8002)
├── domain/          # models, ports, NotificacionService
├── infrastructure/  # SMTP, SQL catálogo, HTTP client, settings
└── jobs/            # container, CLI
```
