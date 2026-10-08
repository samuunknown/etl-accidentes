from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# CSV oficial de MEData: incidentes viales de Medellín
URL = "http://medata.gov.co/sites/default/files/distribution/1-023-25-000094/incidentes_viales.csv"

RAW = BASE / "data" / "raw" / "incidentes_viales.csv"
PROCESSED = BASE / "data" / "processed" / "incidentes_viales_limpio.csv"
DB = BASE / "data" / "incidentes.db"
TABLA = "incidentes"
