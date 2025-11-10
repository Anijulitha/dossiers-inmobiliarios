import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import os

def main():
    st.set_page_config(
        page_title="Dossiers Inmobiliarios - Histórico",
        page_icon="🏠",
        layout="wide"
    )
    
    st.title("🏠 Dossiers Inmobiliarios - Base de Datos Completa")
    st.markdown("---")
    
    # Obtener datos
    df = obtener_datos_db()
    
    if df.empty:
        st.warning("📭 No hay datos en la base de datos. Ejecuta primero: ⁠ python extractor_dossiers.py ⁠")
        st.info("💡 El sistema funciona, pero necesitas analizar algunos PDFs primero.")
        return
    
    # Sidebar
    st.sidebar.title("🔍 Filtros Avanzados")
    
    # Filtro de fecha
    st.sidebar.subheader("Rango de Fechas")
    fecha_min = st.sidebar.date_input("Desde:", datetime.now() - timedelta(days=30))
    fecha_max = st.sidebar.date_input("Hasta:", datetime.now())
    
    # Aplicar filtros de fecha
    df['fecha_analisis'] = pd.to_datetime(df['fecha_analisis'])
    mask = (df['fecha_analisis'].dt.date >= fecha_min) & (df['fecha_analisis'].dt.date <= fecha_max)
    df_filtrado = df[mask]
    
    if df_filtrado.empty:
        st.warning("No hay propiedades en el rango de fechas seleccionado.")
        df_filtrado = df
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Histórico", len(df))
        st.metric("📈 En Periodo", len(df_filtrado))
    
    with col2:
        precio_prom = calcular_promedio_streamlit(df_filtrado, 'precio')
        st.metric("💰 Precio Promedio", precio_prom)
    
    with col3:
        hab_prom = calcular_promedio_streamlit(df_filtrado, 'habitaciones')
        st.metric("🛏️ Hab. Promedio", hab_prom)
    
    with col4:
        metros_prom = calcular_promedio_streamlit(df_filtrado, 'metros')
        st.metric("📏 Metros Promedio", metros_prom)
    
    st.markdown("---")
    
    # Pestañas
    tab1, tab2, tab3 = st.tabs(["📋 Propiedades", "📈 Estadísticas", "🔍 Búsqueda"])
    
    with tab1:
        st.subheader("Listado Completo de Propiedades")
        st.dataframe(df_filtrado, use_container_width=True)
        
        # Exportar datos
        if st.button("📥 Exportar a Excel"):
            df_filtrado.to_excel("export_propiedades.xlsx", index=False)
            st.success("✅ Datos exportados a export_propiedades.xlsx")
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Distribución por Estado")
            if 'estado' in df_filtrado.columns and not df_filtrado.empty:
                fig = px.pie(df_filtrado, names='estado', title='')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de estado para mostrar")
        
        with col2:
            st.subheader("Propiedades por Zona")
            if 'zona' in df_filtrado.columns and not df_filtrado.empty:
                fig = px.bar(df_filtrado['zona'].value_counts().head(10), 
                            title='Top 10 Zonas',
                            labels={'value': 'Número', 'index': 'Zona'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de zona para mostrar")
    
    with tab3:
        st.subheader("Búsqueda Avanzada")
        
        col1, col2 = st.columns(2)
        
        with col1:
            termino_busqueda = st.text_input("🔍 Buscar en todos los campos:")
            precio_min = st.number_input("Precio mínimo:", min_value=0, value=0)
        
        with col2:
            habitaciones_min = st.number_input("Habitaciones mínimas:", min_value=0, value=0)
            metros_min = st.number_input("Metros mínimos:", min_value=0, value=0)
        
        # Aplicar búsqueda
        if termino_busqueda and not df_filtrado.empty:
            mask = df_filtrado.astype(str).apply(lambda x: x.str.contains(termino_busqueda, case=False).any(), axis=1)
            df_busqueda = df_filtrado[mask]
        else:
            df_busqueda = df_filtrado
        
        # Aplicar filtros numéricos SOLO si existen las columnas
        if not df_busqueda.empty:
            if 'habitaciones' in df_busqueda.columns:
                df_busqueda = df_busqueda[df_busqueda['habitaciones'].apply(lambda x: extraer_numero(x) >= habitaciones_min)]
            if 'metros' in df_busqueda.columns:
                df_busqueda = df_busqueda[df_busqueda['metros'].apply(lambda x: extraer_numero(x) >= metros_min)]
            if 'precio' in df_busqueda.columns:
                df_busqueda = df_busqueda[df_busqueda['precio'].apply(lambda x: extraer_numero(x) >= precio_min)]
        
        st.write(f"Resultados: {len(df_busqueda)} propiedades")
        if not df_busqueda.empty:
            st.dataframe(df_busqueda, use_container_width=True)
        else:
            st.info("No se encontraron propiedades con los filtros aplicados")

def obtener_datos_db():
    """Obtener datos de la base de datos SQLite"""
    try:
        conn = sqlite3.connect('dossiers_inmobiliarios.db')
        query = "SELECT archivo, precio, habitaciones, metros, zona, estado, fecha_analisis FROM propiedades WHERE activo = 1 ORDER BY fecha_analisis DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

def calcular_promedio_streamlit(df, campo):
    """Calcula promedios para Streamlit"""
    try:
        valores = []
        for valor in df[campo]:
            if valor != 'No encontrado':
                num = extraer_numero(valor)
                if num > 0:
                    valores.append(num)
        
        if valores:
            promedio = sum(valores) / len(valores)
            if campo == 'precio':
                return f"€ {promedio:,.0f}".replace(',', '.')
            elif campo == 'habitaciones':
                return f"{promedio:.1f}"
            elif campo == 'metros':
                return f"{promedio:.0f} m²"
    except:
        pass
    return "N/A"

def extraer_numero(texto):
    """Extrae número de texto formateado"""
    try:
        if isinstance(texto, str):
            # Limpiar texto
            limpio = texto.replace('€', '').replace('hab', '').replace('m²', '')
            limpio = limpio.replace('.', '').replace(',', '.').strip()
            return float(limpio) if limpio else 0
        return 0
    except:
        return 0

if __name__ == "__main__":
    main()
