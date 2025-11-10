import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import os

# ===================== CONFIG =====================
st.set_page_config(
    page_title="Dossiers Inmobiliarios PRO",
    page_icon="house",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://wa.me/615592892',  # PON AQUÍ TU WHATSAPP
        'Report a bug': 'mailto:anijuli2893@gmail.com',
        'About': 'Dashboard Inmobiliario PRO - Licencia 2.500€'
    }
)

# ===================== FUNCIÓN EXTRAER NÚMERO =====================
def extraer_numero(texto):
    if pd.isna(texto): return 0
    texto = str(texto).replace('€','').replace('hab','').replace('m²','').replace('m2','').replace('.','').replace(',','.').strip()
    try: return float(texto) if texto else 0
    except: return 0

# ===================== CARGAR DATOS =====================
@st.cache_data(ttl=180)  # 3 minutos
def cargar_datos():
    try:
        conn = sqlite3.connect('dossiers_inmobiliarios.db')
        query = "SELECT * FROM propiedades WHERE activo = 1 ORDER BY fecha_analisis DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Normalizar nombres de columnas
        rename = {
            'habitacione': 'habitaciones', 'habitación': 'habitaciones', 'hab': 'habitaciones', 'dormitorios': 'habitaciones',
            'metro': 'metros', 'm2': 'metros', 'm²': 'metros', 'superficie': 'metros'
        }
        df.rename(columns=rename, inplace=True)
        df['fecha_analisis'] = pd.to_datetime(df['fecha_analisis'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error BD: {e}")
        return pd.DataFrame()

df = cargar_datos()
if df.empty:
    st.error("No hay datos. Ejecuta: python extractor_dossiers.py")
    st.stop()

# ===================== SIDEBAR =====================
st.sidebar.image("https://i.imgur.com/8QHZj3J.png", width=200)  # PON TU LOGO AQUÍ
st.sidebar.markdown("## Filtros")

fecha_min = st.sidebar.date_input("Desde", datetime.now() - timedelta(days=90))
fecha_max = st.sidebar.date_input("Hasta", datetime.now())

df = df[(df['fecha_analisis'].dt.date >= fecha_min) & (df['fecha_analisis'].dt.date <= fecha_max)]

# ===================== HEADER =====================
st.title("Dossiers Inmobiliarios PRO")
st.markdown(f"*{len(df)} propiedades* | {fecha_min} → {fecha_max}")

# ===================== KPIs =====================
c1, c2, c3, c4 = st.columns(4)
precios = [extraer_numero(p) for p in df['precio'] if extraer_numero(p)>0]
habs = [extraer_numero(h) for h in df.get('habitaciones', []) if extraer_numero(h)>0]
metros = [extraer_numero(m) for m in df.get('metros', []) if extraer_numero(m)>0]

c1.metric("Propiedades", len(df))
c2.metric("Precio medio", f"€{sum(precios)/len(precios):,.0f}".replace(",",".") if precios else "N/A")
c3.metric("Hab. media", f"{sum(habs)/len(habs):.1f}" if habs else "N/A")
c4.metric("m² medios", f"{sum(metros)/len(metros):.0f}" if metros else "N/A")

# ===================== TABS =====================
tab1, tab2, tab3 = st.tabs(["Listado", "Gráficos", "Búsqueda PRO"])

with tab1:
    st.dataframe(df.drop(columns=['id','activo'], errors='ignore'), use_container_width=True, height=700)
    csv = df.to_csv(index=False).encode()
    st.download_button("Descargar CSV", csv, "dossiers.csv", "text/csv")

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        if 'estado' in df.columns:
            fig = px.pie(df['estado'].value_counts(), names=df['estado'].value_counts().index, title="Estado")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if 'zona' in df.columns:
            top = df['zona'].value_counts().head(10)
            fig = px.bar(x=top.index, y=top.values, labels={'x':'Zona','y':'Nº'}, title="Top 10 Zonas")
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Búsqueda avanzada")
    c1, c2 = st.columns(2)
    with c1:
        texto = st.text_input("Palabra clave")
        pmin = st.number_input("Precio mínimo €", 0, step=10000)
    with c2:
        habmin = st.number_input("Habitaciones mín.", 0)
        mmin = st.number_input("Metros mín.", 0)

    df2 = df.copy()
    if texto:
        df2 = df2[df2.astype(str).apply(lambda x: x.str.contains(texto, case=False, na=False)).any(axis=1)]
    if pmin > 0 and 'precio' in df2.columns:
        df2 = df2[df2['precio'].apply(extraer_numero) >= pmin]
    if habmin > 0:
        col = next((c for c in ['habitaciones','habitacione','hab'] if c in df2.columns), None)
        if col: df2 = df2[df2[col].apply(extraer_numero) >= habmin]
    if mmin > 0 and 'metros' in df2.columns:
        df2 = df2[df2['metros'].apply(extraer_numero) >= mmin]

    st.write(f"*{len(df2)} resultados*")
    st.dataframe(df2, use_container_width=True)

# ===================== FOOTER =====================
st.markdown("---")
st.markdown("""
*Dossiers Inmobiliarios PRO* | Licencia única 2.500€ + IVA  
Contacto: anijuli2893@gmail.com | WhatsApp: +34 615 592 892
""")
