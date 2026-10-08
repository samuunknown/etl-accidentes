"""LOAD: guarda los datos limpios en SQLite."""
import sqlite3

import pandas as pd

from config import DB, TABLA


def load(df: pd.DataFrame) -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as con:
        df.to_sql(TABLA, con, if_exists="replace", index=False)
        if "f_anio" in df.columns:
            con.execute(f"CREATE INDEX IF NOT EXISTS idx_anio ON {TABLA}(f_anio)")
    print(f"[load] {len(df)} filas -> {DB} (tabla '{TABLA}')")
