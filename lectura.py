from pathlib import Path
from datetime import datetime


# Carpetas que se deben ignorar
CARPETAS_IGNORADAS = {
    "__pycache__",
    ".env",
    ".venv",
    "venv",
    "env",
    "test",
    "tests",
    ".git",
    ".idea",
    ".vscode"
}


def carpeta_debe_ignorarse(ruta: Path) -> bool:
    """
    Verifica si alguna parte del path pertenece a una carpeta ignorada.
    """
    for parte in ruta.parts:
        if parte.lower() in CARPETAS_IGNORADAS:
            return True
    return False


def leer_archivos_python():
    """
    Lee todos los archivos .py desde la ruta donde está este script,
    incluyendo carpetas y subcarpetas.
    """

    # Ruta donde está ubicado este archivo .py
    ruta_base = Path(__file__).resolve().parent

    # Archivo de salida
    fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = ruta_base / f"contenido_archivos_python_{fecha_actual}.txt"

    archivos_encontrados = []

    # Buscar todos los archivos .py recursivamente
    for archivo in ruta_base.rglob("*.py"):

        # Ignorar el mismo script si no quieres que se incluya en el TXT
        if archivo.name == Path(__file__).name:
            continue

        # Ignorar carpetas no deseadas
        if carpeta_debe_ignorarse(archivo.relative_to(ruta_base)):
            continue

        archivos_encontrados.append(archivo)

    with open(archivo_salida, "w", encoding="utf-8") as salida:
        salida.write("EXTRACCIÓN DE ARCHIVOS PYTHON\n")
        salida.write("=" * 80 + "\n")
        salida.write(f"Ruta base: {ruta_base}\n")
        salida.write(f"Total de archivos encontrados: {len(archivos_encontrados)}\n")
        salida.write(f"Fecha de generación: {datetime.now()}\n")
        salida.write("=" * 80 + "\n\n")

        for archivo in archivos_encontrados:
            salida.write("\n")
            salida.write("=" * 100 + "\n")
            salida.write(f"ARCHIVO: {archivo.name}\n")
            salida.write(f"PATH COMPLETO: {archivo}\n")
            salida.write(f"PATH RELATIVO: {archivo.relative_to(ruta_base)}\n")
            salida.write("=" * 100 + "\n\n")

            try:
                contenido = archivo.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                contenido = archivo.read_text(encoding="latin-1")
            except Exception as e:
                contenido = f"No se pudo leer el archivo. Error: {e}"

            salida.write(contenido)
            salida.write("\n\n")

    print("Proceso finalizado correctamente.")
    print(f"Archivo generado: {archivo_salida}")
    print(f"Total de archivos .py procesados: {len(archivos_encontrados)}")


if __name__ == "__main__":
    leer_archivos_python()