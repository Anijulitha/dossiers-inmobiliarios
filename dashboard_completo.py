import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta

# ===================== CONFIGURACIÓN =====================
st.set_page_config(
    page_title="Dossiers Inmobiliarios PRO",
    page_icon="house",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== FUNCIÓN EXTRAER NÚMERO =====================
def extraer_numero(texto):
    """Extrae número de cualquier texto (1.234 €, 3 hab, 85 m², etc.)"""
    if pd.isna(texto):
        return 0
    texto = str(texto).replace('€', '').replace('hab', '').replace('m²', '').replace('m2', '')
    texto = texto.replace('.', '').replace(',', '.').strip()
    try:
        return float(texto) if texto else 0
    except:
        return 0

# ===================== OBTENER DATOS (BLINDADO) =====================
@st.cache_data(ttl=300)  # Se actualiza cada 5 minutos
def obtener_datos_db():
    try:
        conn = sqlite3.connect('dossiers_inmobiliarios.db')
        query = "SELECT * FROM propiedades WHERE activo = 1 ORDER BY fecha_analisis DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()

        # RENOMBRADO AUTOMÁTICO DE COLUMNAS (nunca más KeyError)
        rename_dict = {
            'habitacione': 'habitaciones', 'habitación': 'habitaciones',
            'hab': 'habitaciones', 'dormitorios': 'habitaciones',
            'metro': 'metros', 'm2': 'metros', 'm²': 'metros', 'superficie': 'metros'
        }
        df.rename(columns=rename_dict, inplace=True)
        
        # Convertir fecha
        if 'fecha_analisis' in df.columns:
            df['fecha_analisis'] = pd.to_datetime(df['fecha_analisis'], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        return pd.DataFrame()

# ===================== CARGAR DATOS =====================
df = obtener_datos_db()

if df.empty:
    st.warning("No hay datos en la base de datos.")
    st.info("Ejecuta primero: ⁠ python extractor_dossiers.py ⁠")
    st.stop()

# ===================== SIDEBAR FILTROS =====================
st.sidebar.title("Filtros Avanzados")

# Fecha
fecha_min = st.sidebar.date_input("Desde", datetime.now() - timedelta(days=90))
fecha_max = st.sidebar.date_input("Hasta", datetime.now())

# Aplicar filtro fecha
mask_fecha = (df['fecha_analisis'].dt.date >= fecha_min) & (df['fecha_analisis'].dt.date <= fecha_max)
df = df[mask_fecha]

# ===================== TÍTULO =====================
st.title("Dossiers Inmobiliarios - Dashboard PRO")
st.markdown(f"*Total propiedades:* {len(df)} | *Período:* {fecha_min} → {fecha_max}")

# ===================== KPIs =====================
col1, col2, col3, col4 = st.columns(4)

precios = [extraer_numero(p) for p in df['precio'] if extraer_numero(p) > 0]
hab = [extraer_numero(h) for h in df['habitaciones'] if extraer_numero(h) > 0]
metros = [extraer_numero(m) for m in df['metros'] if extraer_numero(m) > 0]

with col1:
    st.metric("Propiedades", len(df))
with col2:
    st.metric("Precio medio", f"€ {sum(precios)/len(precios):,.0f}".replace(",", ".") if precios else "N/A")
with col3:
    st.metric("Hab. media", f"{sum(hab)/len(hab):.1f}" if hab else "N/A")
with col4:
    st.metric("Metros medios", f"{sum(metros)/len(metros):.0f} m²" if metros else "N/A")

st.markdown("---")

# ===================== PESTAÑAS =====================
tab1, tab2, tab3 = st.tabs(["Listado Completo", "Estadísticas", "Búsqueda PRO"])

with tab1:
    st.dataframe(df, use_container_width=True, height=600)
    
    if st.button("Exportar a Excel", type="primary"):
        df.to_excel("dossiers_exportados.xlsx", index=False)
        st.success("¡Exportado! Descarga: dossiers_exportados.xlsx")

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        if 'estado' in df.columns:
            fig = px.pie(df['estado'].value_counts(), names=df['estado'].value_counts().index, title="Estado")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'zona' in df.columns:
            top_zonas = df['zona'].value_counts().head(10)
            fig = px.bar(x=top_zonas.index, y=top_zonas.values, labels={'x': 'Zona', 'y': 'Propiedades'})
            fig.update_layout(title="Top 10 Zonas")
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Búsqueda Avanzada")
    
    col1, col2 = st.columns(2)
    with col1:
        busqueda = st.text_input("Buscar en cualquier campo")
        precio_min = st.number_input("Precio mínimo (€)", min_value=0, value=0, step=10000)
    with col2:
        hab_min = st.number_input("Habitaciones mínimas", min_value=0, value=0)
        metros_min = st.number_input("Metros mínimos", min_value=0, value=0)

    df_bus = df.copy()
    
    if busqueda:
        mask = df_bus.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
        df_bus = df_bus[mask]
    
    if precio_min > 0 and 'precio' in df_bus.columns:
        df_bus = df_bus[df_bus['precio'].apply(extraer_numero) >= precio_min]
    
    if hab_min > 0:
        col_hab = next((c for c in ['habitaciones', 'habitacione', 'hab', 'dormitorios'] if c in df_bus.columns), None)
        if col_hab:
            df_bus = df_bus[df_bus[col_hab].apply(extraer_numero) >= hab_min]
    
    if metros_min > 0 and 'metros' in df_bus.columns:
        df_bus = df_bus[df_bus['metros'].apply(extraer_numero) >= metros_min]
    
    st.write(f"*{len(df_bus)} propiedades encontradas*")
    st.dataframe(df_bus, use_container_width=True)
