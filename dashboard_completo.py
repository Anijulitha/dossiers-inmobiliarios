import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="Dossiers PRO", page_icon="house", layout="wide")

def extraer_numero(x):
    if pd.isna(x): return 0
    try:
        return float(str(x).replace('€','').replace('hab','').replace('m²','').replace('.','').replace(',','.').strip())
    except:
        return 0

@st.cache_data(ttl=60)
def cargar_datos():
    try:
        conn = sqlite3.connect('dossiers_inmobiliarios.db')
        df = pd.read_sql("SELECT * FROM propiedades WHERE activo = 1 ORDER BY fecha_analisis DESC", conn)
        conn.close()
        
        # FORZAR nombre correcto aunque venga mal
        if 'habitacione' in df.columns:
            df = df.rename(columns={'habitacione': 'habitaciones'})
        if 'metro' in df.columns:
            df = df.rename(columns={'metro': 'metros'})
            
        df['fecha_analisis'] = pd.to_datetime(df['fecha_analisis'], errors='coerce')
        return df
    except:
        return pd.DataFrame()

df = cargar_datos()
if df.empty:
    st.error("No hay datos. Borra la BD y vuelve a analizar PDFs")
    st.stop()

# Filtros fecha
fecha_min = st.sidebar.date_input("Desde", datetime.now() - timedelta(days=90))
fecha_max = st.sidebar.date_input("Hasta", datetime.now())
df = df[(df['fecha_analisis'].dt.date >= fecha_min) & (df['fecha_analisis'].dt.date <= fecha_max)]

st.title("Dossiers Inmobiliarios PRO")
st.metric("Propiedades", len(df))

# KPIs
col1, col2, col3 = st.columns(3)
precios = df['precio'].apply(extraer_numero)
habs = df['habitaciones'].apply(extraer_numero) if 'habitaciones' in df.columns else pd.Series([0])
metros = df['metros'].apply(extraer_numero) if 'metros' in df.columns else pd.Series([0])

col1.metric("Precio medio", f"€{precios[precios>0].mean():,.0f}".replace(",",".") if precios[precios>0].any() else "N/A")
col2.metric("Hab. media", f"{habs[habs>0].mean():.1f}" if habs[habs>0].any() else "N/A")
col3.metric("m² medios", f"{metros[metros>0].mean():.0f}" if metros[metros>0].any() else "N/A")

# Búsqueda
st.subheader("Búsqueda PRO")
c1, c2 = st.columns(2)
with c1:
    texto = st.text_input("Palabra clave")
    pmin = st.number_input("Precio mínimo", 0, step=10000)
with c2:
    habmin = st.number_input("Hab. mín.", 0)
    mmin = st.number_input("m² mín.", 0)

df2 = df.copy()
if texto:
    df2 = df2[df2.astype(str).apply(lambda row: row.str.contains(texto, case=False, na=False).any(), axis=1)]

if pmin > 0:
    df2 = df2[precios >= pmin]
if habmin > 0 and 'habitaciones' in df2.columns:
    df2 = df2[habs >= habmin]
if mmin > 0 and 'metros' in df2.columns:
    df2 = df2[metros >= mmin]

st.write(f"*{len(df2)} resultados*")
st.dataframe(df2, use_container_width=True)

# Exportar
csv = df2.to_csv(index=False).encode()
st.download_button("Descargar CSV", csv, "dossiers_filtrados.csv", "text/csv")
