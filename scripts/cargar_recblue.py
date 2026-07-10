# Carga el archivo CSV de Recblue en la tabla credito_rb.
# Formato CSV esperado (coma separador, primera fila cabecera):
#   numero_operacion,id_credito,estado_credito_cr,estado_operacion_cr
#
# Uso:
#   .venv\Scripts\python scripts/cargar_recblue.py "ruta/al/archivo.csv"

import sys
import csv
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DB_PATH = Path(__file__).parent.parent / "data" / "BD_Cobranza.sqlite"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/cargar_recblue.py <ruta_archivo.csv>")
        sys.exit(1)

    archivo = Path(sys.argv[1])
    if not archivo.exists():
        print(f"Archivo no encontrado: {archivo}")
        sys.exit(1)

    fecha_hoy = str(date.today())
    insertados = 0
    omitidos = 0

    with Session() as session:
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                with archivo.open(encoding=encoding, newline="") as f:
                    reader = csv.DictReader(f)
                    # Normalizar cabeceras (quitar comillas y espacios)
                    reader.fieldnames = [c.strip().strip('"').lower() for c in reader.fieldnames]

                    for fila in reader:
                        num_op = (fila.get("numero_operacion") or "").strip()
                        id_cred = (fila.get("id_credito") or "").strip()
                        if not num_op or not id_cred:
                            omitidos += 1
                            continue

                        # Evitar duplicados por numero_operacion
                        existe = session.execute(
                            text("SELECT COUNT(*) FROM credito_rb WHERE numero_operacion = :op"),
                            {"op": num_op}
                        ).scalar()

                        if existe:
                            # Actualizar id_credito si cambió
                            session.execute(
                                text("UPDATE credito_rb SET id_credito=:id, fecha_carga=:f WHERE numero_operacion=:op"),
                                {"id": id_cred, "f": fecha_hoy, "op": num_op}
                            )
                        else:
                            session.execute(
                                text("INSERT INTO credito_rb (id_credito, numero_operacion, fecha_carga) VALUES (:id, :op, :f)"),
                                {"id": id_cred, "op": num_op, "f": fecha_hoy}
                            )
                            insertados += 1

                session.commit()
                break
            except UnicodeDecodeError:
                continue

    total = session.execute(text("SELECT COUNT(*) FROM credito_rb")).scalar() if False else \
            engine.connect().execute(text("SELECT COUNT(*) FROM credito_rb")).scalar()

    print(f"\nCarga completada:")
    print(f"  Insertados/actualizados: {insertados}")
    print(f"  Omitidos (sin datos):    {omitidos}")
    print(f"  Total en tabla:          {total}")


if __name__ == "__main__":
    main()
