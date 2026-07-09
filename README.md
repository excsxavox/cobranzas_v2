# BD Cobranza — Plataforma de Gestión de Cartera

Sistema Python (arquitectura hexagonal + cadena de responsabilidad) para gestión de cartera en mora y gestión preventiva, compuesto por dos módulos independientes que comparten la misma base de datos SQL Server (`BD_Cobranza`).

---

## Módulos del sistema

| Módulo | Paquete | Puerto | Propósito |
|--------|---------|--------|-----------|
| **Cartera Mora** | `cobranzas` | — | Procesa cartera vencida desde archivos `.lis` del core y genera asignaciones diarias |
| **Gestión Preventiva** | `preventiva` | `:8001` | Identifica clientes en riesgo antes del vencimiento y genera base para Isabel |

---

## Estructura del proyecto

```
carteramora/
├── .env                          # Variables de entorno (no subir a git)
├── pyproject.toml                # Dependencias y scripts de entrada
├── main.py                       # Comando de entrada de carteramora
│
├── src/
│   ├── cobranzas/                # Módulo Cartera Mora
│   │   ├── domain/               #   Modelos y servicios de dominio
│   │   ├── application/chain/    #   Pipeline (cadena de responsabilidad)
│   │   └── infrastructure/       #   BD, adaptadores, configuración
│   │
│   └── preventiva/               # Módulo Gestión Preventiva (EPICA GRC-03)
│       ├── domain/               #   Modelos, puertos y servicios
│       ├── application/chain/    #   Pipeline de 7 pasos
│       ├── infrastructure/       #   BD, adaptadores, configuración
│       ├── api/                  #   API REST FastAPI (:8001)
│       └── jobs/                 #   Scheduler, runner, CLI, container DI
│
├── docs/
│   ├── schema_base.sql           # DDL completo (carteramora + preventiva)
│   ├── BD_Cobranza.mmd           # Diagrama ER (Mermaid)
│   └── preventiva_arquitectura.mmd
│
├── tests/
│   └── preventiva/               # Tests unitarios del módulo preventiva
│
└── Batch_Cobranzas/              # Scripts .bat para inicio/parada en Windows
```

---

## Módulo 1 — Cartera Mora (`cobranzas`)

Procesa diariamente los archivos `.lis` generados por el core bancario para identificar clientes en mora y generar el archivo de asignación de gestión.

### Flujo del pipeline

```
asesores.xlsx      → [sync]           → tabla dbo.asesores
*feriados*.xlsx    → [sync-feriados]  → dbo.claves + dbo.catalogo
docsmora/*.lis     → [limpieza]       → destino/*.lis + ASIGNACION.csv + BD
destino/*.lis      → [staging]        → tablas tmp_stg_*
```

### Comandos

```powershell
# Activar entorno
.venv\Scripts\activate

# Instalar dependencias
pip install -e .

# Flujo completo diario
python main.py

# Comandos individuales
python main.py sync               # Sincronizar asesores desde Excel
python main.py sync-feriados      # Sincronizar feriados desde Excel
python main.py limpieza           # Solo limpieza de archivos .lis
python main.py staging            # Cargar .lis limpios a tablas tmp_*
python main.py init-db            # Crear tablas en BD
python main.py plantilla          # Generar plantilla asesores.xlsx
```

### Variables de entorno relevantes (`.env`)

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | Cadena de conexión SQL Server / SQLite |
| `DOCSMORA_DIR` | Carpeta raíz de archivos `.lis` del core |
| `DESTINO_DIR` | Carpeta de salida de archivos procesados |
| `USAR_MORA_TEMPRANA` | Activa filtro de mora temprana (1-30 días) |
| `MORA_TEMPRANA_DIAS_MIN/MAX` | Rango de días para mora temprana |
| `ESTADOS_EXCLUIDOS` | Estados de operación a excluir (CASTIGADO, JUDICIAL…) |
| `TIPOS_OPER_EXCLUIDOS` | Tipos de operación a excluir |
| `USAR_RECBLUE_SQL` | Lee créditos Recblue desde SQL Server externo |
| `PERSISTIR_EN_BD` | Guarda resultados en BD (`true`/`false`) |

---

## Módulo 2 — Gestión Preventiva (`preventiva`) — EPICA GRC-03

Identifica clientes con riesgo de mora antes del vencimiento de su cuota, genera el archivo de carga para la herramienta **Isabel** y produce reportes consolidados mensuales.

### Cómo funciona

El proceso aplica un pipeline de **7 pasos encadenados** sobre los archivos del día:

```
[1] ParseLisHandler        Lee CADETACACO y CAMOROSICO del día
        ↓
[2] HistorialMoraHandler   Guarda mora en historial (ventana 6 meses)
                           Calcula promedio (C1) y meses con mora (C2)
        ↓
[3] SeleccionHandler       Aplica 4 criterios de selección
        ↓
[4] SaldoHandler           Valida saldo disponible (AHSALDIA)
                           Excluye si cubre cuota total
        ↓
[5] RecblueHandler         Busca ID de crédito en dbo.credito_rb
        ↓
[6] IsabelHandler          Genera PREVENTIVA_CORTE_DDMMAAAA_G{n}.txt
        ↓
[7] ReporteHandler         Genera reporte Excel + persiste en BD
                           Al gestión 3: reporte consolidado del corte
                           Al último corte del mes: reporte mensual
```

### Criterios de selección de clientes (todos parametrizables)

| Criterio | Descripción | Parámetro BD |
|----------|-------------|--------------|
| **C1** — Mora promedio | Mora promedio ≥ N días en los últimos 6 meses | `promedio_gestion` (def. 5) |
| **C2** — Pago tardío recurrente | Aparece con mora en ≥ K de los 6 meses (consistencia) | `meses_consistencia_c2` (def. 5) |
| **C3** — Crédito nuevo | Antigüedad ≤ M meses desde la concesión | `antiguedad` (def. 6) |
| **C4** — Alivio financiero | Tipo de operación en lista configurable (NOVA23, REACT23…) | `dbo.catalogo` clave `prev_alivio` |

Cada criterio puede **activarse o desactivarse** individualmente con los parámetros `filtro_mora_activo`, `filtro_pago_tardio_activo`, `filtro_nuevo_activo`, `filtro_alivio_activo` en `dbo.parametros`.

### Archivos entregables generados

| Archivo | Formato | Cuándo se genera |
|---------|---------|-----------------|
| `PREVENTIVA_CORTE_DDMMAAAA_G{n}.txt` | TXT, separador `\|` | Cada ejecución del pipeline |
| `REPORTE_PREVENTIVA_DDMMAAAA_G{n}.xlsx` | Excel | Cada ejecución del pipeline |
| `REPORTE_PREVENTIVA_CORTE{dd}_MMAAAA.xlsx` | Excel | Al completar la gestión 3 del corte |
| `REPORTE_PREVENTIVA_MMAAAA.xlsx` | Excel | Al último corte del mes (consolidado mensual) |

El archivo TXT contiene únicamente: **teléfono | nombre | ID crédito Recblue**

El reporte Excel incluye: fecha proceso, nombre, cédula, número de operación, días mora, día de pago, teléfono, saldo pendiente, saldo en cuenta, número de gestión (1/2/3).

### Procesos en producción

Se deben mantener **2 procesos corriendo simultáneamente**:

#### Proceso 1 — API REST

```powershell
preventiva api
# Levanta en http://127.0.0.1:8001
```

| Endpoint | Descripción |
|----------|-------------|
| `POST /ejecutar-preventiva` | Ejecuta el pipeline manualmente (Postman) |
| `GET  /historial` | Lista ejecuciones recientes |
| `GET  /reporte` | Gestiones generadas (con filtros) |
| `GET  /cortes` | Días de corte activos |
| `GET  /params` | Parámetros del sistema |
| `PUT  /params/{nombre}` | Actualiza un parámetro en caliente |
| `GET  /health` | Verificación de estado |

#### Proceso 2 — Scheduler automático

```powershell
preventiva scheduler
```

Corre todos los días a la hora configurada (`PREV_SCHEDULER_HORA=6`, `PREV_SCHEDULER_MINUTO=30`). Internamente decide si ejecutar según los **cortes activos** en `dbo.catalogo` (clave `prev_dias_corte`):

- Ejecuta **2 días hábiles antes** del corte → gestión 1 y 2
- Ejecuta **el día del corte** → gestión 3
- Si el día de corte cae en fin de semana o feriado, ajusta al siguiente hábil
- Si hoy no corresponde a ningún corte, no hace nada

### Primera puesta en producción

```powershell
# 1. Instalar
.venv\Scripts\activate
pip install -e ".[api]"

# 2. Poblar historial de los últimos 6 meses (solo la primera vez)
preventiva cargar-historico --meses 6

# 3. Levantar los 2 procesos (en terminales separadas o como servicios)
preventiva api
preventiva scheduler
```

### Variables de entorno relevantes (`.env`)

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `DATABASE_URL` | Cadena de conexión SQL Server | — |
| `PREV_ORIGEN_LIS` | Carpeta raíz de archivos CADETACACO y CAMOROSICO | `\\192.168.101.155\listados_cayambe` |
| `PREV_ORIGEN_AHSALDIA` | Carpeta raíz del archivo AHSALDIA | `\\192.168.101.148\Listados_Cayambe` |
| `PREV_DIRECTORIO_RESULTADOS` | Carpeta de salida (Isabel + reportes) | `\\...\Gestion_preventiva` |
| `PREV_API_PORT` | Puerto de la API REST | `8001` |
| `PREV_SCHEDULER_HORA` | Hora de arranque del job diario (0-23) | `6` |
| `PREV_SCHEDULER_MINUTO` | Minuto de arranque (0-59) | `30` |
| `PREV_SCHEDULER_TZ` | Zona horaria | `America/Guayaquil` |
| `PREV_NUMERO_MESES` | Meses de historial a evaluar | `6` |
| `PREV_PROMEDIO_GESTION` | Días mora mínimos para C1 | `5` |
| `PREV_ANTIGUEDAD` | Meses máximos para C3 (crédito nuevo) | `6` |
| `PREV_DIAS_RETRASO_RECURRENTE` | Días mora mínimos para contar un mes en C2 | `5` |
| `PREV_DIAS_ANTES_GESTION` | Días hábiles antes del corte para gestionar | `2` |
| `CLAVE_FERIADOS` | Clave en `dbo.claves` con fechas de feriados | `feriados_catalogo` |

Los valores de la sección **Criterios de selección** se leen primero desde `dbo.parametros` en BD; las variables `.env` actúan como fallback.

---

## Base de datos compartida (`BD_Cobranza`)

Ambos módulos usan la misma base SQL Server. Las tablas están organizadas en dos grupos:

| Grupo | Tablas | Usado por |
|-------|--------|-----------|
| **Compartidas** | `dbo.reglas`, `dbo.claves`, `dbo.catalogo`, `dbo.credito_rb` | Ambos módulos |
| **Cartera mora** | `dbo.asesores`, `dbo.tmp_stg_*`, `dbo.detalle_mora`, etc. | Solo `cobranzas` |
| **Preventiva** | `dbo.parametros`, `dbo.historial_proceso`, `dbo.historial_mora_detalle`, `dbo.reporte_preventiva`, etc. | Solo `preventiva` |

El DDL completo está en `docs/schema_base.sql`. El diagrama ER en `docs/BD_Cobranza.mmd`.

---

## Tests

```powershell
# Todos los tests
pytest

# Solo módulo preventiva
pytest tests/preventiva/ -v
```

Cobertura actual: criterios de selección C1-C4, validación de saldos, calendario de gestión, lógica del scheduler (días hábiles, feriados, traslados), handler de historial mora.

---

## Documentación adicional

| Archivo | Contenido |
|---------|-----------|
| `docs/schema_base.sql` | DDL completo con seeds de parámetros |
| `docs/BD_Cobranza.mmd` | Diagrama ER de toda la base de datos |
| `docs/preventiva_arquitectura.mmd` | Diagrama de arquitectura de los dos microservicios |
| `historia_usuario.md` | Historia de usuario EPICA GRC-03 |
