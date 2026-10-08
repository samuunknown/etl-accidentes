import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from config import DB, TABLA  # noqa: E402

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

ETIQUETAS = {
    "f_anio": "Año",
    "f_mes": "Mes",
    "f_dia_semana": "Día de la semana",
    "f_hora": "Hora",
    "fecha": "Fecha",
    "clase_accidente": "Clase de incidente",
    "gravedad_accidente": "Gravedad",
    "diseno": "Diseño de la vía",
    "comuna": "Comuna",
    "barrio": "Barrio",
    "direccion": "Dirección",
    "direccion_encasillada": "Dirección encasillada",
    "numcomuna": "N.º de comuna",
    "nro_radicado": "N.º de radicado",
    "expediente": "Expediente",
    "cbml": "CBML",
    "lat": "Latitud",
    "lon": "Longitud",
}


def etiqueta(c: str) -> str:
    return ETIQUETAS.get(c, c.replace("_", " ").capitalize())


st.set_page_config(page_title="Incidentes viales", page_icon="🚦", layout="wide")


@st.cache_data
def cargar() -> pd.DataFrame:
    with sqlite3.connect(DB) as con:
        df = pd.read_sql(f"SELECT * FROM {TABLA}", con)
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"])
    return df


if not DB.exists():
    st.error("No existe la base de datos. Corre primero: python src/run_pipeline.py")
    st.stop()

df = cargar()
st.title("🚦 Incidentes viales")
st.caption("Pipeline ETL con datos abiertos · Python, pandas, SQLite y Streamlit")

INCOMPLETOS: list[int] = []

# Rango real de los datos (antes de filtrar) y aviso de años incompletos
if "fecha" in df.columns and len(df):
    f_min, f_max = df["fecha"].min(), df["fecha"].max()
    st.caption(
        f"Datos del {f_min.day} de {MESES[f_min.month - 1]} de {f_min.year} "
        f"al {f_max.day} de {MESES[f_max.month - 1]} de {f_max.year}"
    )
    incompletos = []
    if f_min.month != 1:
        incompletos.append(str(f_min.year))
    if f_max.month != 12:
        incompletos.append(str(f_max.year))
    INCOMPLETOS = [int(a) for a in incompletos]
    if incompletos:
        st.info(
            "Los años " + " y ".join(incompletos) + " están incompletos en la fuente, "
            "así que sus totales no son comparables con los años completos."
        )

# ---- Filtros ----
st.sidebar.header("Filtros")
if "f_anio" in df.columns:
    lista_anios = sorted(df["f_anio"].dropna().astype(int).unique())
    rango = st.sidebar.select_slider("Año", options=lista_anios, value=(lista_anios[0], lista_anios[-1]))
    df = df[df["f_anio"].between(*rango)]

def es_texto(c: str) -> bool:
    return df[c].dtype == "object" or pd.api.types.is_string_dtype(df[c])


FILTROS = [c for c in ["gravedad_accidente", "clase_accidente", "comuna"] if c in df.columns]
for c in FILTROS:
    opciones = sorted(df[c].dropna().unique())
    sel = st.sidebar.multiselect(etiqueta(c), opciones)
    if sel:
        df = df[df[c].isin(sel)]

categoricas = [
    c for c in ["clase_accidente", "gravedad_accidente", "comuna", "barrio", "diseno"]
    if c in df.columns
] or [c for c in df.columns if es_texto(c) and 2 <= df[c].nunique() <= 40]

# ---- KPIs ----
k1, k2, k3 = st.columns(3)
k1.metric("Incidentes", f"{len(df):,}")
if "f_anio" in df.columns and len(df):
    incidentes_por_anio = df.groupby("f_anio").size()
    completos = [a for a in incidentes_por_anio.index if a not in INCOMPLETOS]
    if completos:
        incidentes_por_anio = incidentes_por_anio.loc[completos]
    k2.metric(
        "Año con más incidentes",
        int(incidentes_por_anio.idxmax()),
        f"{incidentes_por_anio.max():,}",
    )
if "fecha" in df.columns and len(df):
    meses = df.groupby(df["fecha"].dt.to_period("M")).size()
    k3.metric("Promedio mensual", f"{meses.mean():,.0f}")

st.divider()

# ---- Gráficos ----
if "fecha" in df.columns and len(df):
    serie = df.groupby(df["fecha"].dt.to_period("M").dt.to_timestamp()).size()
    serie = serie.reset_index(name="incidentes")
    serie.columns = ["Mes", "Incidentes"]
    st.subheader("Evolución mensual")
    st.plotly_chart(px.line(serie, x="Mes", y="Incidentes"), width="stretch")

c1, c2 = st.columns(2)
if "f_dia_semana" in df.columns:
    d = df["f_dia_semana"].value_counts().reindex(DIAS).reset_index()
    d.columns = ["Día", "Incidentes"]
    c1.subheader("Por día de la semana")
    c1.plotly_chart(px.bar(d, x="Día", y="Incidentes"), width="stretch")
if "f_hora" in df.columns:
    h = df["f_hora"].value_counts().sort_index().reset_index()
    h.columns = ["Hora", "Incidentes"]
    c2.subheader("Por hora del día")
    c2.plotly_chart(px.bar(h, x="Hora", y="Incidentes"), width="stretch")

if categoricas:
    st.subheader("Desglose por categoría")
    col = st.selectbox("Desglosar por", categoricas, format_func=etiqueta)
    top = df[col].value_counts().head(15).reset_index()
    top.columns = [etiqueta(col), "Incidentes"]
    st.plotly_chart(
        px.bar(top, x="Incidentes", y=etiqueta(col), orientation="h"), width="stretch"
    )

if {"lat", "lon"} <= set(df.columns):
    st.subheader("Mapa")
    pts = df[["lat", "lon"]].dropna()
    if len(pts):
        st.map(pts.sample(min(len(pts), 20000), random_state=1))

with st.expander("Ver datos"):
    st.dataframe(df.head(1000).rename(columns=etiqueta))
