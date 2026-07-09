# Gestión Preventiva — `preventiva-svc`

Módulo Python para la automatización de la gestión preventiva de cobranzas (EPICA GRC-03).  
Identifica clientes con riesgo de mora **antes del vencimiento**, genera el archivo de carga para **Isabel** y produce reportes Excel consolidados.

---

## Qué hace

1. Cada día a la hora configurada, el **scheduler** decide si corresponde ejecutar según los cortes activos.
2. Si corresponde, lanza el **pipeline de 7 pasos** que lee los archivos del core, aplica reglas de negocio y produce los entregables.
3. También puede ejecutarse **manualmente** vía API REST o CLI.

---

## Pipeline — 7 pasos

```
Archivos del día (.lis)
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. ParseLisHandler                                               │
│    Resuelve y lee los archivos CADETACACO y CAMOROSICO del día.  │
│    Los archivos .lis son TSV (tab-separated); se leen y parsean  │
│    directamente en memoria (equivale a la conversión a Excel     │
│    descrita en la HU, sin pasos intermedios innecesarios).       │
│    Las cabeceras de columna son PARAMETRIZABLES desde            │
│    dbo.parametros (col_cade_*) — HU líneas 167-168.              │
│    Si no encuentra los archivos → detiene el proceso.            │
│    VALIDACIÓN DE INTEGRIDAD (HU línea 153):                      │
│      - Verifica existencia de archivos.                          │
│      - Verifica que CADETACACO tiene registros válidos.          │
│      - Si las columnas no coinciden → detiene con mensaje claro. │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. HistorialMoraHandler                                          │
│    Guarda registros de mora en historial_mora_detalle.           │
│    Mantiene ventana deslizante (máx. N días, parametrizable).    │
│    Calcula: promedio días mora (C1) y meses con mora (C2).       │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. SeleccionHandler                                              │
│    Aplica 4 criterios de selección (ver sección Criterios).      │
│    Retiene solo clientes que cumplen al menos uno.               │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. SaldoHandler                                                  │
│    Lee archivo AHSALDIA (saldos de cuentas).                     │
│    Excluye clientes con saldo suficiente para cubrir la cuota.   │
│    Calcula faltante para los de cobertura parcial.               │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. RecblueHandler                                                │
│    Busca el ID de crédito en dbo.credito_rb (tabla compartida).  │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. IsabelHandler                                                 │
│    Genera PREVENTIVA_CORTE_DDMMAAAA_G{n}.txt                     │
│    Formato: teléfono|nombre|ID_crédito_Recblue                   │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ 7. ReporteHandler                                                │
│    Genera reporte Excel de la gestión.                           │
│    En gestión 3: genera reporte consolidado del corte.           │
│    En último corte del mes: genera reporte mensual completo.     │
│    Persiste todo en dbo.reporte_preventiva.                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Criterios de selección (todos parametrizables vía `dbo.parametros`)

Un cliente se incluye si cumple **al menos uno** de los 4 criterios:

| # | Criterio | Descripción | Parámetro | Default |
|---|----------|-------------|-----------|---------|
| C1 | Mora promedio | Promedio de días mora ≥ N en los últimos 6 meses | `promedio_gestion` | 5 días |
| C2 | Pago tardío recurrente | Aparece con mora en ≥ K meses de los 6 evaluados | `meses_consistencia_c2` | 5 meses |
| C3 | Crédito nuevo | Antigüedad desde concesión ≤ M meses | `antiguedad` | 6 meses |
| C4 | Alivio financiero | Tipo de operación en lista configurable (NOVA23, REACT23, SOLUCION, REF23…) | `dbo.catalogo` clave `prev_alivio` | — |

> **Nota sobre C2 — decisión de diseño:**
> La HU describe C2 como clientes que "de forma consistente en los últimos seis meses, realicen sus pagos en fechas posteriores". La implementación traduce ese concepto de _consistencia_ como: el cliente debe aparecer con mora en al menos `meses_consistencia_c2` meses distintos dentro de la ventana de 6 meses. Este umbral es configurable en `dbo.parametros` para que el negocio pueda ajustarlo según su política vigente.

Cada criterio puede activarse o desactivarse individualmente:

| Parámetro BD | Descripción |
|---|---|
| `filtro_mora_activo` | Activa/desactiva C1 |
| `filtro_pago_tardio_activo` | Activa/desactiva C2 |
| `filtro_nuevo_activo` | Activa/desactiva C3 |
| `filtro_alivio_activo` | Activa/desactiva C4 |
| `excluir_cobertura_total` | Excluye clientes con saldo suficiente para cubrir la cuota completa |

---

## Archivos entregables

| Archivo | Formato | Cuándo |
|---------|---------|--------|
| `PREVENTIVA_CORTE_DDMMAAAA_G{n}.txt` | TXT, separador `\|` | Cada ejecución |
| `REPORTE_PREVENTIVA_DDMMAAAA_G{n}.xlsx` | Excel | Cada ejecución |
| `REPORTE_PREVENTIVA_CORTE{dd}_MMAAAA.xlsx` | Excel | Al completar gestión 3 del corte |
| `REPORTE_PREVENTIVA_MMAAAA.xlsx` | Excel | Al último corte del mes (mensual consolidado) |

**Campos del reporte Excel:** Fecha proceso · Nombre · Cédula · Número operación · Días mora · Día pago · Teléfono · Saldo pendiente · Saldo en cuenta · Número de gestión (1/2/3)

**Campos del TXT para Isabel:** `teléfono|nombre|ID_crédito_Recblue`

---

## Procesos en producción

Se requieren **2 procesos corriendo simultáneamente**:

### Proceso 1 — API REST (`:8001`)

```powershell
preventiva api
```

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/ejecutar-preventiva` | POST | Ejecuta el pipeline manualmente (desde Postman) |
| `/ejecutar-preventiva/{cod}` | GET | Estado de una ejecución |
| `/historial` | GET | Listado de ejecuciones recientes |
| `/historial/{cod}/pasos` | GET | Pasos detallados de una ejecución |
| `/reporte` | GET | Gestiones generadas (con filtros opcionales) |
| `/reporte/mensual` | GET | Datos del reporte mensual consolidado |
| `/cortes` | GET | Días de corte activos en `dbo.catalogo` |
| `/params` | GET | Parámetros del sistema |
| `/params/{nombre}` | PUT | Actualiza un parámetro en caliente |
| `/health` | GET | Verificación de estado |

### Proceso 2 — Scheduler automático

```powershell
preventiva scheduler
```

**Lógica de ejecución (según HU GRC-03):**

- Corre todos los días a `PREV_SCHEDULER_HORA:PREV_SCHEDULER_MINUTO`
- Lee los cortes activos desde `dbo.catalogo` (clave `prev_dias_corte`: 5, 10, 15, 17, 20, 24)
- Por cada corte calcula los días de gestión: **2 días hábiles antes + el día del corte**
- Si el día de corte cae en fin de semana o feriado, se traslada al siguiente día hábil
- Si hoy no corresponde a ningún corte, no hace nada

**Ejemplo:** corte día 5 de mayo (lunes)
```
Gestión 1 → jueves 1 mayo
Gestión 2 → viernes 2 mayo
Gestión 3 → lunes 5 mayo (día del corte)
```

---

## Instalación y primera puesta en producción

```powershell
# 1. Activar entorno virtual
.venv\Scripts\activate

# 2. Instalar dependencias con extras de API
pip install -e ".[api]"

# 3. Configurar .env (ver sección Variables de entorno)

# 4. Poblar historial de los últimos 6 meses (SOLO la primera vez)
preventiva cargar-historico --meses 6

# 5. Levantar los 2 procesos en terminales separadas (o como servicios Windows)
preventiva api
preventiva scheduler
```

---

## Otros comandos CLI

```powershell
# Ejecutar el pipeline manualmente para una fecha y corte específicos
preventiva ejecutar --fecha 05052026 --corte 5

# Ejecutar sin especificar corte (usa la fecha de hoy)
preventiva ejecutar

# Backfill de historial para un rango específico
preventiva cargar-historico --desde 01122025 --hasta 30042026

# Forzar recarga de fechas que ya tienen datos
preventiva cargar-historico --meses 6 --forzar

# Arrancar scheduler con hora personalizada
preventiva scheduler --hora 7 --minuto 0
```

---

## Variables de entorno (`.env`)

```ini
# ── Base de datos ─────────────────────────────────────────────────────
DATABASE_URL=mssql+pyodbc://...    # SQL Server (BD_Cobranza)

# ── Rutas de archivos fuente ──────────────────────────────────────────
PREV_ORIGEN_LIS=\\192.168.101.155\listados_cayambe
PREV_ORIGEN_AHSALDIA=\\192.168.101.148\Listados_Cayambe
PREV_DIRECTORIO_RESULTADOS=\\...\Gestion_preventiva

# ── API ───────────────────────────────────────────────────────────────
PREV_API_HOST=127.0.0.1
PREV_API_PORT=8001

# ── Scheduler ─────────────────────────────────────────────────────────
PREV_SCHEDULER_HORA=6             # Hora de arranque (0-23)
PREV_SCHEDULER_MINUTO=30          # Minuto de arranque (0-59)
PREV_SCHEDULER_TZ=America/Guayaquil

# ── Criterios de selección (fallback si no están en dbo.parametros) ───
PREV_NUMERO_MESES=6               # Meses de historial a evaluar
PREV_PROMEDIO_GESTION=5           # Días mora mínimos para C1
PREV_ANTIGUEDAD=6                 # Meses máximos desde concesión para C3
PREV_DIAS_RETRASO_RECURRENTE=5    # Días mora mínimos para contar un mes en C2
PREV_DIAS_ANTES_GESTION=2         # Días hábiles antes del corte para gestionar

# ── Feriados (clave en dbo.claves, compartida con carteramora) ────────
CLAVE_FERIADOS=feriados_catalogo
```

> Los criterios de selección se leen primero desde `dbo.parametros` en la BD. El `.env` actúa como fallback si el registro no existe.

### Cabeceras de columna del CADETACACO (HU líneas 167-168)

Si COBIS actualiza los nombres de columna, se registran los nuevos en `dbo.parametros` **sin modificar código**:

| Parámetro BD | Columna que sobreescribe | Default |
|---|---|---|
| `col_cade_operacion` | Número de operación | `OPERACIÓN` |
| `col_cade_identificacion` | Cédula / ID socio | `IDENTIFICACIÓN` |
| `col_cade_nombre` | Nombre del socio | `NOMBRE SOCIO` |
| `col_cade_tipo_operacion` | Tipo de operación (C4 alivio) | `TIPO DE OPERACIÓN` |
| `col_cade_dia_pago` | Día de pago habitual | `DIA DE PAGO` |
| `col_cade_valor_cuota` | Valor de la cuota | `VALOR CUOTA` |
| `col_cade_dias_mora` | Días de mora actuales | `DÍAS MORA` |
| `col_cade_fecha_concesion` | Fecha de concesión (C3 crédito nuevo) | `FECHA CONCESIÓN` |

Solo se registran las columnas que cambian; las demás usan el default.

### Patrones de nombre de archivo y extensiones (HU líneas 142-144)

| Parámetro BD | Descripción | Ejemplo |
|---|---|---|
| `CADETACACO_LIS` | Patrón del archivo CADETACACO | `cadetacaco_cie{fecha}of_0.lis` |
| `CAMOROSICO_LIS` | Patrón del archivo CAMOROSICO | `camorosico_{fecha}.of_0.lis` |
| `AHSALDIA_LIS` | Patrón del archivo AHSALDIA | `ahsaldia*_of00255.lis` |

Use `{fecha}` como marcador del MMDDYYYY dentro del patrón. Si el parámetro está vacío, se usan los patrones heredados de `carteramora`.

---

## Tablas de base de datos propias

| Tabla | Descripción |
|-------|-------------|
| `dbo.parametros` | Parámetros configurables del proceso |
| `dbo.historial_proceso` | Registro de cada ejecución del pipeline |
| `dbo.ejecucion_pad` | Pasos detallados de cada ejecución |
| `dbo.logs_cp` | Resumen operacional por ejecución |
| `dbo.historial_mora_detalle` | Histórico de mora por operación (ventana 6 meses) |
| `dbo.promedio_general_mes` | Promedios calculados por corte/mes |
| `dbo.reporte_preventiva` | Registros de clientes gestionados |
| `dbo.insumo` / `dbo.insumo_columna` | Metadatos de archivos procesados |

**Tablas compartidas con `carteramora` (solo lectura):**

| Tabla | Uso |
|-------|-----|
| `dbo.reglas` | Motor de reglas de negocio |
| `dbo.claves` / `dbo.catalogo` | Feriados, días de corte, tipos de alivio |
| `dbo.credito_rb` | ID de crédito Recblue por operación |

El DDL completo está en `docs/schema_base.sql`.

---

## Tests

```powershell
pytest tests/preventiva/ -v
```

| Test | Qué verifica |
|------|-------------|
| `test_seleccion_preventiva_service.py` | Los 4 criterios C1-C4, lógica OR, parametrización |
| `test_validar_saldo_service.py` | Cobertura total, parcial, sin saldo |
| `test_calendario_gestion_service.py` | Cálculo de días hábiles, feriados, traslados |
| `test_scheduler_logica_hu.py` | Regla 2 días antes + día corte, ajuste por feriados |
| `test_historial_mora_handler.py` | Ventana deslizante, purga de registros antiguos |

---

## Cobertura de la Historia de Usuario (HU GRC-03)

Esta sección traza los requisitos de la HU contra la implementación, incluyendo decisiones de diseño donde aplica.

| Requisito HU | Líneas HU | Estado | Decisión de diseño |
|---|---|---|---|
| Generación automática 2 días antes del corte | 28-36 | ✅ Scheduler + CalendarioGestionService | — |
| Fechas de corte parametrizables | 33-36 | ✅ `dbo.catalogo` clave `prev_dias_corte` | — |
| Validar fin de semana / feriado y trasladar | 41-52 | ✅ `_fecha_pago_efectiva` + `_dias_habiles_anteriores` | — |
| C1: mora promedio ≥ 5 días en 6 meses | 60-61 | ✅ `SeleccionPreventivaService` | — |
| C2: pago tardío recurrente y consistente | 63-66 | ✅ Implementado | Ver nota C2 más abajo |
| C3: crédito nuevo ≤ 6 meses | 68-69 | ✅ `SeleccionPreventivaService` | — |
| C4: alivio financiero vigente | 71-77 | ✅ `SeleccionPreventivaService` | — |
| Criterios parametrizables y desactivables | 79-81 | ✅ `dbo.parametros` con flags booleanos | — |
| Validar saldo cuenta (AHSALDIA) | 83-108 | ✅ `SaldoHandler` + `ValidarSaldoService` | — |
| Excluir si saldo cubre cuota completa | 97-99 | ✅ `excluir_cobertura_total` | — |
| Calcular faltante si cobertura parcial | 99-102 | ✅ `valor_faltante` en el reporte | — |
| Rutas de archivos parametrizables | 110-145 | ✅ `.env` + `dbo.parametros` | — |
| Detener y notificar si faltan archivos | 139-140 | ✅ `ParseLisHandler` detiene el proceso | — |
| Lectura y conversión de archivos .lis | 151-153 | ✅ Lectura directa TSV en memoria | Ver nota LIS→Excel más abajo |
| Validación de integridad antes del proceso | 153 | ✅ `ParseLisHandler` valida registros > 0 | — |
| Cabeceras de columna parametrizables | 167-168 | ✅ `col_cade_*` en `dbo.parametros` | — |
| Obtener teléfono del CAMOROSICO | 232 | ✅ `RegistroCamorosico.telefono` | — |
| Generar archivo Isabel `.txt` con `\|` | 236-265 | ✅ `IsabelHandler` + `isabel_writer` | — |
| Nombre archivo `PREVENTIVA_CORTE_DDMMAAAA` | 247 | ✅ Implementado | — |
| Campos mínimos: teléfono, nombre, ID crédito | 257-263 | ✅ ID desde `dbo.credito_rb` (Recblue) | — |
| Reporte por corte con las 3 gestiones | 282-284 | ✅ Al completar gestión 3 | — |
| Reporte mensual consolidado al último corte | 277-284 | ✅ `ReporteHandler` + `escribir_reporte_mensual` | — |
| Formato XLS y estructura completa del reporte | 286-309 | ✅ Todos los campos incluyendo gestión N° | — |

### Nota — Lectura de archivos .lis (HU líneas 151-153)

La HU describe que "los archivos `.lis` se convierten a Excel" refiriéndose al proceso manual que hacían los analistas. En la implementación automatizada, los archivos `.lis` (que son TSV — valores separados por tabulación) se leen y parsean **directamente en memoria** con las mismas columnas, sin generar un Excel intermedio. Esto es funcionalmente equivalente y más eficiente.

### Nota — Criterio C2 (HU líneas 63-66)

La HU describe clientes que "de forma consistente en los últimos seis meses, realicen sus pagos en fechas posteriores". La implementación traduce _consistencia_ como: el cliente debe aparecer con mora en al menos `meses_consistencia_c2` meses distintos (default: 5 de 6). Este umbral es configurable para que el negocio lo ajuste según su criterio.

### Nota — `cargar-historico` (HU líneas 185-188)

La HU indica que el proceso debe revisar "los archivos históricos de los últimos seis meses". Para evitar recorrer diariamente cientos de archivos históricos, el sistema mantiene una tabla `historial_mora_detalle` que se alimenta incrementalmente cada ejecución. El comando `cargar-historico` se usa **solo la primera vez** para poblar esos 6 meses iniciales. Después, cada ejecución diaria agrega el archivo del día automáticamente.

---

## Estructura del módulo

```
src/preventiva/
├── domain/
│   ├── models/          # RegistroCadetacaco, RegistroSeleccion, ProcesoResult
│   ├── ports/           # Interfaces (HistorialMoraPort, ReportePort, ParametrosPort)
│   └── services/        # SeleccionPreventivaService, ValidarSaldoService, CalendarioGestionService
│
├── application/
│   └── chain/           # 7 handlers del pipeline + PreventivaContext
│
├── infrastructure/
│   ├── adapters/        # Lectores .lis, escritor Isabel, escritor Excel
│   ├── config/          # PreventivaSettings, LisResolver
│   └── persistence/     # ORM models, repositorios, engine
│
├── api/
│   ├── app.py           # FastAPI app con todos los endpoints
│   └── schemas.py       # Modelos Pydantic de request/response
│
└── jobs/
    ├── cli.py           # Comandos Click (ejecutar, scheduler, api, cargar-historico)
    ├── scheduler.py     # APScheduler con lógica HU de días de ejecución
    ├── preventiva_runner.py  # Orquestador principal del pipeline
    └── container.py     # Inyección de dependencias
```
