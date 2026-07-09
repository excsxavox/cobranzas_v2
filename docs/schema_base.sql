/* =============================================================================
   schema_base.sql — BD_Cobranza · Bot Gestión Preventiva (EPICA GRC-03)
   Cooperativa 23 de Julio · NexTI Business Solutions
   Ejecutar ANTES de stored_procedures.sql.

   TABLAS COMPARTIDAS (ya existen en BD_Cobranza — NO se crean aquí):
     • dbo.reglas          — motor de reglas parametrizables de carteramora
     • dbo.claves          — cabecera de catálogos (incluye feriados_catalogo)
     • dbo.catalogo        — valores del catálogo (feriados almacenados aquí)
     • dbo.credito_rb      — lookup Recblue (confirmar si ya existe; si no, se crea)
   Solo se leen; nunca se escriben desde preventiva-svc.

   Nota: las tablas LIS dinámicas (cadetacaco_lis, camorosico_lis, ahsaldia_lis)
   NO se crean aquí: las genera el parser vía POST /crear-tablas-lis (orden 10).

   proceso_cod = YYYYMMDDHHMMSS (sortable como string)
   ============================================================================= */
USE BD_Cobranza;
GO

/* ─────────────────────────────────────────────────────────────────────────────
   BLOQUE 1 — TRAZABILIDAD DE EJECUCIONES
   Guarda qué se ejecutó, cuándo, cuántos registros y si fue OK o Error.
   ───────────────────────────────────────────────────────────────────────────── */

IF OBJECT_ID('dbo.historial_proceso') IS NULL
CREATE TABLE dbo.historial_proceso (
    proceso_cod      VARCHAR(14)  NOT NULL PRIMARY KEY,  -- YYYYMMDDHHMMSS
    fecha_inicio     DATETIME     NOT NULL DEFAULT GETDATE(),
    fecha_fin        DATETIME     NULL,
    estado           VARCHAR(10)  NOT NULL DEFAULT 'EN_CURSO', -- OK / ERROR / EN_CURSO
    numero_gestion   INT          NULL,                  -- 1 / 2 / 3 (gestión del corte)
    dia_corte        INT          NULL,                  -- día de corte que disparó la ejecución
    modo             VARCHAR(20)  NOT NULL DEFAULT 'corte' -- corte / diario / manual
);
GO

/* Trazabilidad paso a paso dentro de una ejecución */
IF OBJECT_ID('dbo.ejecucion_pad') IS NULL
CREATE TABLE dbo.ejecucion_pad (
    id               BIGINT IDENTITY(1,1) PRIMARY KEY,
    proceso_cod      VARCHAR(14)  NOT NULL,
    paso_ejecucion   VARCHAR(100) NOT NULL,              -- nombre del paso/handler
    estado           VARCHAR(10)  NOT NULL,              -- OK / Error
    descripcion      VARCHAR(4000) NULL,
    total_registros  INT          NULL DEFAULT 0,
    fecha_registro   DATETIME     NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_ejecucion_pad_hp FOREIGN KEY (proceso_cod)
        REFERENCES dbo.historial_proceso (proceso_cod)
);
GO

/* Resumen operacional por proceso (visible para el usuario final) */
IF OBJECT_ID('dbo.logs_cp') IS NULL
CREATE TABLE dbo.logs_cp (
    id               BIGINT IDENTITY(1,1) PRIMARY KEY,
    proceso_cod      VARCHAR(14)  NOT NULL,
    usuario          VARCHAR(100) NOT NULL DEFAULT 'Bot',
    fecha_hora       DATETIME     NOT NULL DEFAULT GETDATE(),
    proceso_ejecutado VARCHAR(100) NOT NULL,
    estado           VARCHAR(10)  NOT NULL,              -- OK / Error
    descripcion      VARCHAR(4000) NULL,
    total_registros  INT          NULL DEFAULT 0,
    tiempo_total     VARCHAR(10)  NULL,                  -- HH:MM:SS
    CONSTRAINT FK_logs_cp_hp FOREIGN KEY (proceso_cod)
        REFERENCES dbo.historial_proceso (proceso_cod)
);
GO

/* ─────────────────────────────────────────────────────────────────────────────
   BLOQUE 2 — CATÁLOGOS PARAMETRIZABLES (propios de preventiva-svc)
   NOTA: dbo.feriados NO se crea aquí. Los feriados ya están en BD_Cobranza
   dentro de dbo.catalogo con clave 'feriados_catalogo' (tabla dbo.claves +
   dbo.catalogo). preventiva-svc los lee directamente desde ahí.
   ───────────────────────────────────────────────────────────────────────────── */

/* Parámetros del sistema — incluye TODOS los valores de la tabla HU (imagen) */
IF OBJECT_ID('dbo.parametros') IS NULL
CREATE TABLE dbo.parametros (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    nombre      VARCHAR(100)  NOT NULL UNIQUE,
    valor       VARCHAR(1000) NULL,
    descripcion VARCHAR(500)  NULL,
    activo      BIT           NOT NULL DEFAULT 1
);
GO

/* Días de corte y alivio financiero → se almacenan en dbo.claves + dbo.catalogo
   (tabla compartida ya existente). No se crean tablas propias.
   Claves usadas:
     • prev_dias_corte      → valores: 5, 10, 15, 17, 20, 24
     • prev_alivio_financiero → valores: NOVA23, REACT23, REF23, etc.
   Ver semillas en el bloque de SEMILLAS más abajo. */

/* Destinatarios y plantillas de correo (HU líneas 147-149) */
IF OBJECT_ID('dbo.notificaciones') IS NULL
CREATE TABLE dbo.notificaciones (
    id               INT IDENTITY(1,1) PRIMARY KEY,
    id_proceso       VARCHAR(100)  NOT NULL,             -- paso o 'general'
    estado           VARCHAR(10)   NOT NULL,             -- Error / OK
    correo_para      VARCHAR(1000) NOT NULL,             -- separado por ;
    correo_copia     VARCHAR(1000) NULL,
    plantilla_correo VARCHAR(4000) NOT NULL,
    activo           BIT           NOT NULL DEFAULT 1
);
GO

/* ─────────────────────────────────────────────────────────────────────────────
   BLOQUE 3 — DICCIONARIO DE INSUMOS .LIS
   Permite cambiar nombres de cabeceras si COBIS los actualiza (HU líneas 155-168).
   ───────────────────────────────────────────────────────────────────────────── */

IF OBJECT_ID('dbo.insumos') IS NULL
CREATE TABLE dbo.insumos (
    insumos_id INT IDENTITY(1,1) PRIMARY KEY,
    nombre     VARCHAR(100) NOT NULL UNIQUE,             -- cadetacaco / camorosico / ahsaldia
    tabla      VARCHAR(128) NOT NULL                     -- tabla LIS destino (dinámica)
);
GO

IF OBJECT_ID('dbo.insumos_columnas') IS NULL
CREATE TABLE dbo.insumos_columnas (
    insumos_columnas_id INT IDENTITY(1,1) PRIMARY KEY,
    insumos_id     INT          NOT NULL REFERENCES dbo.insumos (insumos_id),
    columna_insumo VARCHAR(200) NOT NULL,                -- cabecera original editable (COBIS)
    columna_tabla  VARCHAR(128) NOT NULL,                -- nombre normalizado en BD
    tipo_dato      VARCHAR(20)  NOT NULL,                -- VARCHAR / INT / DECIMAL / DATE
    longitud_campo VARCHAR(20)  NULL,                    -- 255 / 18,2 / etc.
    activo         BIT          NOT NULL DEFAULT 1
);
GO

/* ─────────────────────────────────────────────────────────────────────────────
   BLOQUE 4 — HISTORIAL DE MORA 6 MESES
   Almacena el detalle diario de días de mora por operación leído de los archivos
   camorosico históricos. Permite calcular/recalcular el promedio en cualquier
   momento (HU líneas 185-196).
   ───────────────────────────────────────────────────────────────────────────── */

IF OBJECT_ID('dbo.historial_mora_detalle') IS NULL
CREATE TABLE dbo.historial_mora_detalle (
    id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    operacion       VARCHAR(30)  NOT NULL,               -- número de operación
    identificacion  VARCHAR(20)  NULL,                   -- cédula del socio
    nombre          VARCHAR(200) NULL,
    fecha_corte     DATE         NOT NULL,               -- fecha del archivo camorosico leído
    dias_mora       INT          NOT NULL DEFAULT 0,     -- DIAS ATRASO de ese día
    fuente_archivo  VARCHAR(300) NULL,                   -- nombre/ruta del .lis origen
    proceso_cod     VARCHAR(14)  NOT NULL,
    CONSTRAINT FK_hmd_hp FOREIGN KEY (proceso_cod)
        REFERENCES dbo.historial_proceso (proceso_cod)
);
CREATE INDEX IX_hmd_operacion_fecha ON dbo.historial_mora_detalle (operacion, fecha_corte);
CREATE INDEX IX_hmd_identificacion  ON dbo.historial_mora_detalle (identificacion);
GO

/* ─────────────────────────────────────────────────────────────────────────────
   BLOQUE 5 — RESULTADO DEL CÁLCULO DE SELECCIÓN
   Resultado consolidado por operación: promedio 6 meses, criterios que aplican,
   validación de saldo. Tabla de staging: se trunca en cada ejecución del corte.
   (HU líneas 56-108 — los 4 criterios de selección + validación saldo)
   ───────────────────────────────────────────────────────────────────────────── */

IF OBJECT_ID('dbo.promedio_general_mes') IS NULL
CREATE TABLE dbo.promedio_general_mes (
    id                   BIGINT IDENTITY(1,1) PRIMARY KEY,
    proceso_cod          VARCHAR(14)  NOT NULL,
    -- Identificación
    operacion            VARCHAR(30)  NOT NULL,
    identificacion       VARCHAR(20)  NULL,
    nombre               VARCHAR(200) NULL,
    telefono             VARCHAR(30)  NULL,
    tipo_operacion       VARCHAR(100) NULL,              -- TIPO OPER del cadetacaco
    -- Datos de cuota y pago
    dia_pago             INT          NULL,              -- DIA DE PAGO del cadetacaco
    valor_cuota          DECIMAL(18,2) NULL,             -- VALOR CUOTA del cadetacaco
    dias_mora_actual     INT          NULL,              -- DIAS MORA del día de ejecución
    -- Criterio 1: promedio mora > 5 días (HU línea 60-61)
    promedio_meses       INT          NULL,              -- FLOOR(promedio 6 meses)
    fecha_desde          DATE         NULL,              -- inicio ventana 6 meses
    fecha_hasta          DATE         NULL,              -- fin ventana 6 meses
    criterio_mora        BIT          NULL DEFAULT 0,   -- 1 si promedio_meses >= umbral
    -- Criterio 2: pago tardío recurrente (HU líneas 63-66)
    criterio_pago_tardio BIT          NULL DEFAULT 0,
    -- Criterio 3: crédito nuevo ≤ 6 meses (HU líneas 68-69)
    fecha_concesion      DATE         NULL,              -- fecha entrega crédito
    antiguedad_meses     INT          NULL,
    criterio_nuevo       BIT          NULL DEFAULT 0,
    -- Criterio 4: alivio financiero vigente (HU líneas 71-77)
    criterio_alivio      BIT          NULL DEFAULT 0,
    -- Decisión final (OR de los 4 criterios)
    aplica_gestion       VARCHAR(2)   NULL,              -- SI / NO
    -- Validación de saldo (HU líneas 83-108)
    saldo_cuenta         DECIMAL(18,2) NULL,             -- saldo disponible de ahsaldia
    valor_faltante       DECIMAL(18,2) NULL,             -- valor_cuota - saldo_cuenta (si > 0)
    cobertura            VARCHAR(10)  NULL,              -- TOTAL / PARCIAL / SIN_FONDOS
    -- Trazabilidad del corte (via catalogo: clave prev_dias_corte)
    dia_corte            INT          NULL,              -- día de corte que originó esta ejecución
    fecha_actualiza      DATETIME     NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_pgm_hp FOREIGN KEY (proceso_cod)
        REFERENCES dbo.historial_proceso (proceso_cod)
);
CREATE INDEX IX_pgm_operacion ON dbo.promedio_general_mes (operacion);
CREATE INDEX IX_pgm_proceso   ON dbo.promedio_general_mes (proceso_cod);
GO

/* ─────────────────────────────────────────────────────────────────────────────
   BLOQUE 6 — GESTIONES PREVENTIVAS (PERSISTENCIA DEL REPORTE)
   Almacena cada contacto realizado (gestión 1, 2 o 3) con todos los campos
   del reporte mensual exigido por la HU (líneas 289-308) más el ID Recblue
   necesario para el archivo Isabel (HU línea 262).
   ───────────────────────────────────────────────────────────────────────────── */

IF OBJECT_ID('dbo.reporte_preventiva') IS NULL
CREATE TABLE dbo.reporte_preventiva (
    id               BIGINT IDENTITY(1,1) PRIMARY KEY,
    proceso_cod      VARCHAR(14)  NOT NULL,
    -- Campos del reporte mensual (HU líneas 289-308)
    fecha_proceso    DATE         NOT NULL,              -- Fecha de proceso
    nombre           VARCHAR(200) NULL,                  -- Nombre
    cedula           VARCHAR(20)  NULL,                  -- Cédula
    numero_operacion VARCHAR(30)  NULL,                  -- Numero Operación
    dias_mora        INT          NULL,                  -- Dias mora
    dia_pago         INT          NULL,                  -- Día pago
    telefono         VARCHAR(30)  NULL,                  -- Telefono Celular
    saldo_pendiente  DECIMAL(18,2) NULL,                 -- Saldo pendiente de cuota (faltante)
    saldo_cuenta     DECIMAL(18,2) NULL,                 -- Saldo en cuenta
    numero_gestion   INT          NOT NULL,              -- Número de gestión (1 / 2 / 3)
    -- Campo para archivo Isabel (HU línea 262)
    id_credito_rb    VARCHAR(30)  NULL,                  -- ID crédito Recblue
    -- Trazabilidad del corte (via catalogo: clave prev_dias_corte)
    dia_corte        INT          NULL,                  -- día de corte (5, 10, 15...)
    CONSTRAINT FK_rp_hp FOREIGN KEY (proceso_cod)
        REFERENCES dbo.historial_proceso (proceso_cod)
);
CREATE INDEX IX_rp_fecha_gestion ON dbo.reporte_preventiva (fecha_proceso, numero_gestion);
CREATE INDEX IX_rp_cedula        ON dbo.reporte_preventiva (cedula);
CREATE INDEX IX_rp_operacion     ON dbo.reporte_preventiva (numero_operacion);
GO

/* ─────────────────────────────────────────────────────────────────────────────
   BLOQUE 7 — RECBLUE
   Resolver numero_operacion → id_credito para el archivo Isabel (HU línea 262).
   Si dbo.credito_rb ya existe en BD_Cobranza (creada por carteramora u otro
   proceso), esta sentencia no la recrea. Solo se agrega el índice si falta.
   ───────────────────────────────────────────────────────────────────────────── */

IF OBJECT_ID('dbo.credito_rb') IS NULL
CREATE TABLE dbo.credito_rb (
    id               BIGINT IDENTITY(1,1) PRIMARY KEY,
    id_credito       VARCHAR(30)  NOT NULL,
    identificacion   VARCHAR(20)  NULL,
    socio            VARCHAR(30)  NULL,
    numero_operacion VARCHAR(30)  NOT NULL,
    fecha_carga      DATETIME     NOT NULL DEFAULT GETDATE(),
    proceso_cod      VARCHAR(14)  NULL
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_credito_rb_operacion')
    CREATE INDEX IX_credito_rb_operacion ON dbo.credito_rb (numero_operacion);
GO

/* =============================================================================
   SEMILLAS — catálogos y parámetros base
   Todo via MERGE para que el script sea idempotente (re-ejecutable).
   ============================================================================= */

/* ── Parámetros del sistema ──────────────────────────────────────────────── */
/* Todos los valores corresponden a la tabla de criterios de la HU (imagen). */
MERGE dbo.parametros AS t USING (VALUES

  /* ── SCHEDULER ─────────────────────────────────────────────────────────── */
  ('ejecucion_corte',          'true',
   'true = usa fecha_cortes (5,10,15,17,20,24); false = evaluación diaria'),

  /* ── CRITERIO 1: mora promedio 6 meses (HU imagen — tabla parámetros) ── */
  ('numero_meses',             '6',
   'Número de meses a considerar para cálculo de mora promedio'),
  ('promedio_gestion',         '5',
   'Días mínimos de mora promedio por mes para incluir cliente'),

  /* ── CRITERIO 2: pago tardío recurrente ─────────────────────────────── */
  ('dias_retraso_recurrente',  '5',
   'Días de retraso recurrente para considerar pago tardío consistente'),

  /* ── CRITERIO 3: crédito nuevo (HU imagen — tabla parámetros) ───────── */
  ('antiguedad',               '6',
   'Meses máximos para considerar desde la nueva operación'),
  -- Criterio 3 se incluye SIN validar mora promedio (HU imagen, nota explícita)

  /* ── CRITERIO 4: alivio financiero (HU imagen — tabla parámetros) ───── */
  ('considerar_novacion',      'Si',
   'Considerar clientes con novación vigente'),
  ('considerar_refinanciado',  'Si',
   'Considerar clientes refinanciados'),
  ('considerar_reestructurado','Si',
   'Considerar clientes reestructurados'),
  -- Criterio 4 se incluye SIN validar mora promedio (HU imagen, nota explícita)

  /* ── CALENDARIO DE GESTIONES (HU imagen — tabla parámetros) ─────────── */
  ('dias_antes_gestion',       '2',
   'Días antes del vencimiento para ejecutar gestión preventiva'),
  ('modo_calendario',          'mrk_cp',
   'mrk_cp = +N días hábiles antes del vencimiento / hu = por calendario exacto'),

  /* ── FERIADOS: clave en dbo.catalogo/dbo.claves (tabla compartida) ───── */
  ('clave_feriados',           'feriados_catalogo',
   'Clave en dbo.claves que contiene el catálogo de feriados de carteramora'),

  /* ── FUENTES DE DATOS (HU líneas 124-145) ──────────────────────────── */
  ('separador_decimal',        '.',
   'Separador decimal en archivos .lis'),
  ('origen_lis',
   '\\\\192.168.101.155\\listado_cayambe\\',
   'Ruta base carpetas CAMOROSICO y CADETACACO'),
  ('origen_ahsaldia',
   '\\\\192.168.101.148\\Listados_Cayambe\\',
   'Ruta base carpeta ahsaldia'),

  /* ── PATRONES DE ARCHIVO (HU líneas 135-137) ─────────────────────── */
  ('CARTERA_PREF_LIS',         'cartera',
   'Prefijo subcarpeta cartera'),
  ('CARTERA_FIN_LIS',          'b',
   'Sufijo subcarpeta cartera'),
  ('CAMOROSICO_LIS',           'camorosico*_of_0.lis',
   'Patrón glob archivo CAMOROSICO'),
  ('CADETACACO_LIS',           'cadetacaco_cie*_of_0.lis',
   'Patrón glob archivo CADETACACO'),
  ('AHSALDIA_PREF_LIS',        'saldo',
   'Prefijo subcarpeta ahsaldia'),
  ('AHSALDIA_FIN_LIS',         'b',
   'Sufijo subcarpeta ahsaldia'),
  ('AHSALDIA_LIS',             'ahsaldia*_of00255.lis',
   'Patrón glob archivo ahsaldia'),
  ('col_saldo_ahsaldia',       'SALDO DISPONIBLE',
   'Cabecera columna saldo disponible en ahsaldia — CONFIRMAR CON NEGOCIO'),

  /* ── SALIDAS (HU líneas 247-250) ────────────────────────────────────── */
  ('resultados',
   '\\\\192.168.101.155\\depto_cobranzas\\COBRANZAZ_IOI\\Gestion_preventiva\\[yyyy]\\[mmyyyy]',
   'Ruta base para PREVENTIVA_CORTE_*.txt y REPORTE_PREVENTIVA_*.xls'),

  /* ── RECBLUE (HU líneas 267-273) ────────────────────────────────────── */
  ('recblue',                  'dbo.credito_rb',
   'Tabla Recblue compartida en BD_Cobranza'),
  ('col_id_credito',           'dbo.credito_rb.id_credito',
   'Columna ID crédito Recblue'),
  ('col_operacion',            'dbo.credito_rb.numero_operacion',
   'Columna número operación Recblue'),

  /* ── BASE DE DATOS ──────────────────────────────────────────────────── */
  ('base',                     'BD_Cobranza',
   'Base de datos activa'),

  /* ── SMTP (HU línea 147) ─────────────────────────────────────────────── */
  ('smtp_correo',              'smtp.gmail.com',  'Servidor SMTP'),
  ('smtp_usuario',             'test@gmail.com',  'Usuario SMTP'),
  ('smtp_pass',                '',
   'Contraseña SMTP — NO dejar en texto plano en PROD, cargar desde vault'),
  ('smtp_puerto',              '587',             'Puerto SMTP'),
  ('smtp_tls',                 'True',            'Usar TLS')

) AS s (nombre, valor, descripcion) ON t.nombre = s.nombre
WHEN NOT MATCHED THEN INSERT (nombre, valor, descripcion, activo)
     VALUES (s.nombre, s.valor, s.descripcion, 1);
GO

/* ── Días de corte → dbo.claves + dbo.catalogo (HU línea 33) ─────────────── */
/* Clave: prev_dias_corte  |  valores: 5,10,15,17,20,24                       */
IF NOT EXISTS (SELECT 1 FROM dbo.claves WHERE clave = 'prev_dias_corte')
    INSERT INTO dbo.claves (clave, descripcion, fecha_creacion, vigente, fecha_modificacion)
    VALUES ('prev_dias_corte',
            'Días de corte para gestión preventiva (GRC-03)',
            GETDATE(), 1, GETDATE());

DECLARE @id_corte INT = (SELECT id_clave FROM dbo.claves WHERE clave = 'prev_dias_corte');
MERGE dbo.catalogo AS t
USING (VALUES ('5'),('10'),('15'),('17'),('20'),('24')) AS s (valor)
ON t.id_clave = @id_corte AND t.valor = s.valor
WHEN NOT MATCHED THEN
    INSERT (id_clave, valor, descripcion, fecha_creacion, vigencia, fecha_modificacion)
    VALUES (@id_corte, s.valor, 'Día de corte preventiva', GETDATE(), 1, GETDATE());
GO

/* ── Tipos de alivio financiero → dbo.claves + dbo.catalogo (HU líneas 211-227) */
/* Clave: prev_alivio_financiero  |  valores: NOVA23, REACT23, REF23, etc.     */
IF NOT EXISTS (SELECT 1 FROM dbo.claves WHERE clave = 'prev_alivio')
    INSERT INTO dbo.claves (clave, descripcion, fecha_creacion, vigente, fecha_modificacion)
    VALUES ('prev_alivio',
            'Tipos de operación con alivio financiero vigente (GRC-03)',
            GETDATE(), 1, GETDATE());

DECLARE @id_alivio INT = (SELECT id_clave FROM dbo.claves WHERE clave = 'prev_alivio');
MERGE dbo.catalogo AS t
USING (VALUES
    ('NOVA23',     'Novación 2023'),
    ('NOVAMAPOYO', 'Novación apoyo'),
    ('NOVAMCONAF', 'Novación CONAFIPS'),
    ('NOVASRUEDM', 'Novación RUEDM'),
    ('REACT23',    'Reactivación 2023'),
    ('REACTI23',   'Reactivación interna 2023'),
    ('SOLUCION',   'Plan solución'),
    ('REF23',      'Refinanciamiento 2023'))
AS s (valor, descripcion)
ON t.id_clave = @id_alivio AND t.valor = s.valor
WHEN NOT MATCHED THEN
    INSERT (id_clave, valor, descripcion, fecha_creacion, vigencia, fecha_modificacion)
    VALUES (@id_alivio, s.valor, s.descripcion, GETDATE(), 1, GETDATE());
GO

/* ── Notificaciones (HU líneas 147-149) ─────────────────────────────────── */
MERGE dbo.notificaciones AS t
USING (VALUES
  ('general', 'Error',
   'pgalarza@coop23dejulio.fin.ec;amontero@coop23dejulio.fin.ec', NULL,
   'Estimados, el bot de Gestión Preventiva reporta un ERROR.' + CHAR(13) +
   'Paso: {paso}' + CHAR(13) + 'Causa: {causa}' + CHAR(13) + 'proceso_cod: {proceso_cod}'),
  ('general', 'OK',
   'pgalarza@coop23dejulio.fin.ec;amontero@coop23dejulio.fin.ec', NULL,
   'Proceso ejecutado correctamente. proceso_cod: {proceso_cod}'),
  ('proceso_completo', 'OK',
   'pgalarza@coop23dejulio.fin.ec;amontero@coop23dejulio.fin.ec', NULL,
   'Estimados, la Gestión Preventiva del {fecha} finalizó correctamente.' + CHAR(13) +
   'Gestión número: {numero_gestion}. Se adjuntan los archivos generados.' + CHAR(13) +
   'proceso_cod: {proceso_cod}'))
AS s (id_proceso, estado, correo_para, correo_copia, plantilla_correo)
ON t.id_proceso = s.id_proceso AND t.estado = s.estado
WHEN NOT MATCHED THEN INSERT (id_proceso, estado, correo_para, correo_copia, plantilla_correo, activo)
     VALUES (s.id_proceso, s.estado, s.correo_para, s.correo_copia, s.plantilla_correo, 1);
GO

/* ── Insumos LIS y mapeo de columnas (HU líneas 155-168) ────────────────── */
MERGE dbo.insumos AS t USING (VALUES
    ('cadetacaco', 'dbo.cadetacaco_lis'),
    ('camorosico', 'dbo.camorosico_lis'),
    ('ahsaldia',   'dbo.ahsaldia_lis'))
AS s (nombre, tabla) ON t.nombre = s.nombre
WHEN NOT MATCHED THEN INSERT (nombre, tabla) VALUES (s.nombre, s.tabla);
GO

-- Columnas clave de cadetacaco (cabeceras originales parametrizables)
DECLARE @id_cadetacaco INT = (SELECT insumos_id FROM dbo.insumos WHERE nombre = 'cadetacaco');
DECLARE @id_camorosico INT = (SELECT insumos_id FROM dbo.insumos WHERE nombre = 'camorosico');
DECLARE @id_ahsaldia   INT = (SELECT insumos_id FROM dbo.insumos WHERE nombre = 'ahsaldia');

MERGE dbo.insumos_columnas AS t
USING (VALUES
    -- cadetacaco (HU líneas 155-165): cabeceras críticas
    (@id_cadetacaco, 'OPERACIÓN',       'operacion',       'VARCHAR', '30'),
    (@id_cadetacaco, 'DÍAS MORA',       'dias_mora',       'INT',     NULL),
    (@id_cadetacaco, 'DIA DE PAGO',     'dia_pago',        'INT',     NULL),
    (@id_cadetacaco, 'TIPO DE OPERACIÓN','tipo_operacion', 'VARCHAR', '100'),
    (@id_cadetacaco, 'VALOR CUOTA',     'valor_cuota',     'DECIMAL', '18,2'),
    (@id_cadetacaco, 'NOMBRE SOCIO',    'nombre',          'VARCHAR', '200'),
    (@id_cadetacaco, 'IDENTIFICACIÓN',  'identificacion',  'VARCHAR', '20'),
    (@id_cadetacaco, 'FECHA CONCESIÓN', 'fecha_concesion', 'DATE',    NULL),
    -- camorosico: teléfono requerido para archivo Isabel (HU línea 232)
    (@id_camorosico, 'OPERACIÓN',       'operacion',       'VARCHAR', '30'),
    (@id_camorosico, 'DÍAS ATRASO',     'dias_mora',       'INT',     NULL),
    (@id_camorosico, 'IDENTIFICACIÓN',  'identificacion',  'VARCHAR', '20'),
    (@id_camorosico, 'NOMBRE SOCIO',    'nombre',          'VARCHAR', '200'),
    (@id_camorosico, 'TELÉFONO',        'telefono',        'VARCHAR', '30'),
    -- ahsaldia: columna de saldo (HU línea 122 — nombre a confirmar con negocio)
    (@id_ahsaldia,   'SALDO DISPONIBLE','saldo_disponible','DECIMAL', '18,2'),
    (@id_ahsaldia,   'IDENTIFICACIÓN',  'identificacion',  'VARCHAR', '20')
) AS s (insumos_id, columna_insumo, columna_tabla, tipo_dato, longitud_campo)
ON t.insumos_id = s.insumos_id AND t.columna_insumo = s.columna_insumo
WHEN NOT MATCHED THEN INSERT (insumos_id, columna_insumo, columna_tabla, tipo_dato, longitud_campo, activo)
     VALUES (s.insumos_id, s.columna_insumo, s.columna_tabla, s.tipo_dato, s.longitud_campo, 1);
GO

PRINT 'schema_base.sql aplicado correctamente.';
GO
