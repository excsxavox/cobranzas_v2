from datetime import datetime, date, timedelta
import pandas as pd
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

RUTA_FERIADOS = r"C:\Project\carteramora\data\catalogo\dias_feriados.xlsx"


def cargar_feriados(ruta_excel: str) -> set:
    """
    Carga feriados desde Excel.
    Formato esperado: MM/DD/YYYY o M/D/YYYY
    """
    try:
        # Verificar si el archivo existe
        if not os.path.exists(ruta_excel):
            return set()
        
        # Leer todas las columnas primero para inspección
        df_full = pd.read_excel(ruta_excel, engine="openpyxl")
        
        # Buscar columnas que contengan "inicio" o "fin"
        columnas_inicio = [col for col in df_full.columns if "inicio" in str(col).lower()]
        columnas_fin = [col for col in df_full.columns if "fin" in str(col).lower()]
        
        # Seleccionar la primera columna de inicio y fin encontrada
        col_inicio = columnas_inicio[0] if columnas_inicio else None
        col_fin = columnas_fin[0] if columnas_fin else None
        
        if col_inicio is None:
            return set()
        
        # Crear DataFrame con solo las columnas necesarias
        if col_fin:
            df = df_full[[col_inicio, col_fin]].copy()
        else:
            df = df_full[[col_inicio]].copy()
        
        # Función para convertir fechas en múltiples formatos
        def convertir_fecha(valor):
            if pd.isna(valor):
                return pd.NaT
            
            # Si ya es datetime, retornar
            if isinstance(valor, (datetime, pd.Timestamp)):
                return pd.to_datetime(valor)
            
            # Convertir a string y limpiar
            valor_str = str(valor).strip()
            
            # Intentar con formato MM/DD/YYYY (con ceros)
            try:
                return pd.to_datetime(valor_str, format="%m/%d/%Y", errors="coerce")
            except:
                pass
            
            # Intentar con formato M/D/YYYY (sin ceros)
            try:
                partes = valor_str.split('/')
                if len(partes) == 3:
                    mes = int(partes[0])
                    dia = int(partes[1])
                    anio = int(partes[2])
                    fecha_formateada = f"{mes:02d}/{dia:02d}/{anio:04d}"
                    return pd.to_datetime(fecha_formateada, format="%m/%d/%Y", errors="coerce")
            except:
                pass
            
            # Intentar con pandas para otros formatos
            try:
                return pd.to_datetime(valor_str, errors="coerce")
            except:
                return pd.NaT
        
        # Aplicar conversión de fechas
        df[col_inicio] = df[col_inicio].apply(convertir_fecha)
        
        if col_fin:
            df[col_fin] = df[col_fin].apply(convertir_fecha)
        
        # Eliminar filas con fecha inicio inválida
        df = df.dropna(subset=[col_inicio])
        
        if df.empty:
            return set()
        
        # Procesar feriados
        feriados = set()
        
        for _, row in df.iterrows():
            inicio = row[col_inicio].date()
            
            if col_fin and pd.notna(row[col_fin]):
                fin = row[col_fin].date()
                
                if fin < inicio:
                    continue
                
                # Agregar todos los días del rango
                for i in range((fin - inicio).days + 1):
                    feriados.add(inicio + timedelta(days=i))
            else:
                feriados.add(inicio)
        
        return feriados

    except Exception as e:
        return set()

def es_dia_habil(fecha: date, feriados: set) -> bool:
    return fecha.weekday() < 5 and fecha not in feriados


def primer_dia_habil_mes(anio: int, mes: int, feriados: set) -> date:
    dia = date(anio, mes, 1)
    while not es_dia_habil(dia, feriados):
        dia += timedelta(days=1)
    return dia


def ultimo_dia_habil_mes(anio: int, mes: int, feriados: set) -> date:
    if mes == 12:
        dia = date(anio + 1, 1, 1) - timedelta(days=1)
    else:
        dia = date(anio, mes + 1, 1) - timedelta(days=1)
    while not es_dia_habil(dia, feriados):
        dia -= timedelta(days=1)
    return dia


def dia_anterior_habil(fecha: date, feriados: set) -> date:
    dia = fecha
    while True:
        dia -= timedelta(days=1)
        if es_dia_habil(dia, feriados):
            return dia


def formatear_fecha(fecha: date) -> str:
    return fecha.strftime("%m%d%Y")


def obtener_fecha_desde_env() -> date:
    manual = os.getenv("FECHA_MANUAL", "NO").strip().upper()
    if manual == "SI":
        fecha_str = os.getenv("FECHAPROCESO")
        if not fecha_str:
            raise ValueError("FECHA_MANUAL=SI pero no se definió FECHAPROCESO en .env")
        fecha_str = fecha_str.strip()
        if len(fecha_str) != 8 or not fecha_str.isdigit():
            raise ValueError(f"FECHAPROCESO debe tener 8 dígitos (MMDDYYYY), pero se recibió: '{fecha_str}'")
        try:
            return datetime.strptime(fecha_str, "%m%d%Y").date()
        except ValueError:
            raise ValueError(f"FECHAPROCESO con formato inválido: {fecha_str}. Debe ser MMDDYYYY.")
    else:
        return date.today()


def procesar_fecha(fecha: date) -> str:
    feriados = cargar_feriados(RUTA_FERIADOS)
    
    if not es_dia_habil(fecha, feriados):
        anterior = dia_anterior_habil(fecha, feriados)
        return f"{formatear_fecha(anterior)}|false"

    primer_dia = primer_dia_habil_mes(fecha.year, fecha.month, feriados)

    if fecha == primer_dia:
        if fecha.month == 1:
            anio_anterior = fecha.year - 1
            mes_anterior = 12
        else:
            anio_anterior = fecha.year
            mes_anterior = fecha.month - 1

        fin_mes = ultimo_dia_habil_mes(anio_anterior, mes_anterior, feriados)
        return f"{formatear_fecha(fin_mes)}|true"
    else:
        anterior = dia_anterior_habil(fecha, feriados)
        return f"{formatear_fecha(anterior)}|false"


if __name__ == "__main__":
    fecha_proceso = obtener_fecha_desde_env()
    resultado = procesar_fecha(fecha_proceso)
    print(resultado)