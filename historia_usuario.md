FOR-GDE-PMO-05-11

PMO-PE-001-2026

Inteligencia Operacional e Integridad (IOI)

EPICA N° GRC-03

"Automatización de Gestión Preventiva"

HISTÓRICO DE CAMBIOS

EPICA N° 3: Creación de Base Preventiva

Como supervisor de cobranzas, quiero que el proveedor genere la cartera
de gestión Preventiva

HU N° 1.1: Creación de Base Preventiva

Como supervisor de cobranzas, Quiero que se genere de forma automática
la cartera preventiva, para anticipar riesgos de mora y gestionar
clientes antes del vencimiento.

Criterios de aceptación

GESTIÓN PREVENTIVA:

El sistema deberá generar de forma automática y programada el archivo de
gestión preventiva con dos (2) días de anticipación a la fecha de pago
del socio.

La generación se realizará considerando las fechas de pago con mayor
volumen de socios (cortes), inicialmente definidas como: 5, 10, 15, 17,
20 y 24, las cuales deberán ser parametrizables y modificables por el
usuario autorizado, en el caso de requerir ejecutar el proceso de forma
diaria, también se debe permitir.

Ejemplo: Para una fecha de pago correspondiente al 5 de mayo, el archivo
de gestión preventiva deberá generarse automáticamente el 3 de mayo.

El sistema deberá validar si la fecpago del cliente corresponde a un
sábado, domingo o feriado. ha de

En caso de presentarse esta condición, la fecha efectiva de pago se
traslada al siguiente día laborable.

Ejemplo:

Si la fecha de pago del cliente corresponde al lunes debido a que el
vencimiento original cae en sábado, domingo o feriado, el sistema deberá
realizar la gestión preventiva el día jueves, viernes y nuevamente el
día lunes.

Criterios de selección de clientes

El sistema deberá identificar y seleccionar automáticamente a los
clientes que serán incluidos en la gestión de cobranza preventiva,
considerando las siguientes condiciones:

Clientes que, durante los últimos seis (6) meses, presenten una mora
promedio superior a cinco (5) días.

Clientes con una fecha de pago recurrente definida (ejemplo fecha de
pago: día 10) que, de forma consistente en los últimos seis (6) meses,
realicen sus pagos en fechas posteriores (ejemplo real de pago: día 16).
Es decir se demoran 5 días en pagar.

Clientes con una antigüedad igual o menor a seis (6) meses desde la
entrega del crédito.

Clientes con alivio financiero vigente:

Novación

Refinanciamiento

Reestructuración

Todos estos criterios deberán ser evaluados de forma automatizada y
parametrizable, permitiendo su ajuste según políticas vigentes del
negocio.

Criterios de validación de saldos

El sistema deberá validar automáticamente los saldos disponibles en las
cuentas de ahorro del socio, con el fin de estimar su capacidad de pago
al momento de la gestión preventiva.

Esta validación deberá:

Consultar el saldo disponible actualizado con la última información
disponible. (Insumo: archivo ahsaldia)

Determinar si el cliente cuenta con fondos suficientes o si le falta
para cubrir la próxima cuota a vencer.

Cuando el cliente disponga del saldo necesario para cubrir el valor
total de la cuota, no deberá ser considerado dentro de la gestión
preventiva. En caso de que el cliente cuente con fondos parciales, el
sistema deberá calcular el faltante e informar el valor pendiente por
cubrir, considerando la diferencia entre el valor de la cuota próxima a
vencer y el saldo disponible en la cuenta.

Ejemplo:

Si la cuota a vencer es de USD 100 y el cliente dispone de USD 70 en su
cuenta de ahorro, el sistema deberá registrar que existe una cobertura
parcial y que el saldo pendiente por cubrir es de USD 30.

Ruta de archivo de saldos disponibles:

\\192.168.101.148`\Listados`{=tex}\_Cayambe\\2026\

Carpeta año en curso

Subcarpeta

Subcarpeta

Archivo de saldo disponible en la cuenta.

Columna a identificar el saldo disponible:

Proceso actual

Se accede a la ruta compartida:

\\192.168.101.148`\Listados`{=tex}\_Cayambe\\2026\

Se ingresa a la carpeta del año vigente y subcarpeta diaria
correspondiente

Se descargan los archivos:

cadetacaco_cieXXXXof_0.lis

camorosico_XXXX.of_0.lis

Nota: En el caso de no encontrar los archivos en las rutas definidas, se
notificará al usuario y se detendrá el proceso.

Debe existir una parametrización para que se pueda cambiar la ruta de
los archivos o incluso las extensiones de los archivos. Una vez que se
regularice los archivos en las rutas, se debe ejecutar de forma manual
el bot.

Se debe notificar a (pgalarza@coop23dejulio.fin.ec y
amontero@coop23dejulio.fin.ec), además debe permitir aumentar, modificar
o eliminar los correos, en el caso de cambio.

Los archivos .lis se convierten a Excel:

Se valida integridad de la información antes del procesamiento

Se identifican columnas clave "CADETACACO":

(OPERACIÓN)

(DÍAS MORA)

(DIA DE PAGO)

(TIPO DE OPERACIÓN)

(VALOR CUOTA)

Estas cabeceras deben ser parametrizables en el caso que cobis realice
una actualización de cabeceras, se podrá modificar con el nuevo nombre.

Ejemplos:

Criterios de inclusión en gestión preventiva:

Se priorizan las siguientes operaciones:

El sistema deberá identificar los clientes que en los últimos 6 meses
han presentado mora mayor o igual a 5 días en promedio (el resultado
generado del promedio se elimina el decimal, por ejemplo 4.99 solo toma
el 4 y no aplica gestión). Para esto se debe identificar los últimos
seis meses, cuantos días se ha demorado en pagar, después del
vencimiento de su cuota.

Ejemplo:

El sistema deberá realizar una revisión diaria de los archivos
históricos de cartera (camorosi), considerando el archivo actual y los
archivos correspondientes a los seis (6) meses anteriores, con el fin de
calcular los días de retraso registrados por cada cliente.

Ejemplo: Si la ejecución del proceso se realiza el 5 de mayo de 2026, el
sistema deberá considerar la información comprendida entre el 5 de
diciembre de 2025 y el 4 de mayo de 2026.

La cantidad de días de mora y el periodo de evaluación deberán ser
parametrizables, permitiendo su ajuste conforme a las políticas vigentes
del negocio.

Operaciones nuevas

CADETACACO

Cuentas que mantienen alivio financiero

Para identificar operaciones con alivio financiero se tiene la cabecera
TIPO OPER.

CADETACACO

TIPO OPER.

Debe ser Parametrizable según el producto:

NOVA23

NOVAMAPOYO

NOVAMCONAF

NOVASRUEDM

REACT23

REACTI23

SOLUCION

REF23\|

La gestión se efectúa 2 días antes de la fecha de pago del socio,
incluyendo el día de pago.

Obtener numero telefonico del camorosico

Generación de Archivo para Gestión Preventiva

Una vez identificada y validada la información de los clientes que serán
gestionados en el día, el sistema deberá generar automáticamente el
archivo base para carga en herramienta: Isabel.

El archivo deberá contener únicamente los registros correspondientes a
clientes incluidos en la gestión preventiva diaria y deberá consolidar
la información en un formato concatenado y estructurado para su
procesamiento.

Estructura y formato del archivo

Nombre del archivo: PREVENTIVA_CORTE_DDMMAAAA

Ruta: Servidor Cooperativa 23 de Julio / Carpeta por crearse para
campañas cobranza preventiva

Formato de salida: .txt

El separador del archivo debe ser \|

Campos mínimos requeridos

Número de teléfono

Nombre del cliente

ID de crédito de acuedo al reporte RECBLUE

El sistema deberá garantizar que el archivo sea generado con el formato
y estructura compatibles para su carga automática en Isabel.

Obtención del ID de crédito (Recblue):

"Gestionar" → "Consulta créditos"

Seleccionar "ID CREDITO-IDENTIFICACION-SOCIO-NUMERO DE OPERACION"

Click sobre el icono de Excel, se Descarga archivo

Generación de Reporte mensual

Se debe generar un reporte mensual, el ultimo día de corte con toda la
información generada del mes.

Nombre del archivo (REPORTE PREVENTIVA DDMMAAA)

Este reporte se debe generar cada corte con las 3 gestiones realizadas
previamente y se debe tener al final del mes el reporte mensual
consolidado con todos los cortes.

El formato del archivo es xls.

La estructura que debe generar es la siguiente:

Fecha de proceso

Nombre

Cédula

Numero Operación

Dias mora

Día pago

Telefono Celular

Saldo pendiente de cuota

Saldo en cuenta

Número de gestión (1-2-3)
