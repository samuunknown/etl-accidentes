"""TRANSFORM: limpia y enriquece los datos crudos."""
import re
import unicodedata

import pandas as pd

from config import PROCESSED, RAW

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
# Caja aproximada de Medellín/Valle de Aburrá para descartar coordenadas erróneas
LAT_RANGO = (6.0, 6.5)
LON_RANGO = (-75.8, -75.3)


def normalizar_nombre(col: str) -> str:
    """'AÑO' -> 'ano', 'Clase Accidente' -> 'clase_accidente'."""
    col = unicodedata.normalize("NFKD", str(col)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", col.strip().lower()).strip("_")


def leer_raw() -> pd.DataFrame:
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(RAW, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise RuntimeError("No se pudo leer el CSV con utf-8 ni latin-1")


def parsear_fecha(serie: pd.Series) -> pd.Series:
    # Formato del dataset: dd/mm/aaaa hh:mm:ss
    return pd.to_datetime(serie, errors="coerce", dayfirst=True)


def buscar_columna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    for c in df.columns:
        if any(k == c or k in c for k in candidatos):
            return c
    return None


def transform(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)
    df = df.rename(columns=normalizar_nombre)

    # Texto: quitar espacios, unificar vacíos como nulos
    for c in [c for c in df.columns if df[c].dtype == "object" or pd.api.types.is_string_dtype(df[c])]:
        df[c] = (
            df[c].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
        )
        df[c] = df[c].replace({"": pd.NA, "NA": pd.NA, "N/A": pd.NA, "NULL": pd.NA})

    df = df.drop_duplicates()

    # Fecha estándar -> columna 'fecha' + derivadas
    # fecha_accidente = hora local; fecha_accidentes viene en UTC (+5h), se descarta
    col_fecha = "fecha_accidente" if "fecha_accidente" in df.columns else buscar_columna(df, ["fecha"])
    if col_fecha:
        df["fecha"] = parsear_fecha(df[col_fecha])
        df = df.dropna(subset=["fecha"])
        df["f_anio"] = df["fecha"].dt.year
        df["f_mes"] = df["fecha"].dt.month
        df["f_dia_semana"] = df["fecha"].dt.dayofweek.map(dict(enumerate(DIAS)))
        if (df["fecha"].dt.hour != 0).any():
            df["f_hora"] = df["fecha"].dt.hour
    else:
        print("[transform] AVISO: no se encontró columna de fecha")

    # Coordenadas: 'location' viene como texto "[lon, lat]"
    if "location" in df.columns:
        xy = df["location"].astype("string").str.extract(
            r"\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]"
        )
        df["lon"] = pd.to_numeric(xy[0], errors="coerce")
        df["lat"] = pd.to_numeric(xy[1], errors="coerce")
    else:
        col_lat = buscar_columna(df, ["latitud", "lat"])
        col_lon = buscar_columna(df, ["longitud", "lon", "lng"])
        if col_lat and col_lon:
            df["lat"] = pd.to_numeric(df[col_lat], errors="coerce")
            df["lon"] = pd.to_numeric(df[col_lon], errors="coerce")
    if {"lat", "lon"} <= set(df.columns):
        mal = ~df["lat"].between(*LAT_RANGO) | ~df["lon"].between(*LON_RANGO)
        df.loc[mal, ["lat", "lon"]] = pd.NA

    # Columnas redundantes
    df = df.drop(
        columns=["fecha_accidentes", "fecha_accidente", "ano", "mes", "location", "x", "y"],
        errors="ignore",
    )

    print(f"[transform] {n0} -> {len(df)} filas | {len(df.columns)} columnas")
    return df.reset_index(drop=True)


def run() -> pd.DataFrame:
    df = transform(leer_raw())
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED, index=False)
    print(f"[transform] Guardado en {PROCESSED}")
    return df


if __name__ == "__main__":
    run()
