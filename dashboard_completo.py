import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database_manager import DatabaseManager

def main():
    st.set_page_config(
        page_title="Dossiers Inmobiliarios - Histórico",
        page_icon="🏠",
        layout="wide"
    )
    
    st.title("🏠 Dossiers Inmobiliarios - Base de Datos Completa")
    st.markdown("---")
    
    # Inicializar base de datos
    db = DatabaseManager()
    
    # Sidebar
    st.sidebar.title("🔍 Filtros Avanzados")
    
    # Filtro de fecha
    st.sidebar.subheader("Rango de Fechas")
    fecha_min = st.sidebar.date_input("Desde:", datetime.now() - timedelta(days=30))
    fecha_max = st.sidebar.date_input("Hasta:", datetime.now())
    
    # Obtener datos
    df = db.obtener_todas_propiedades()
    df['fecha_analisis'] = pd.to_datetime(df['fecha_analisis'])
    
    # Aplicar filtros de fecha
    mask = (df['fecha_analisis'].dt.date >= fecha_min) & (df['fecha_analisis'].dt.date <= fecha_max)
    df_filtrado = df[mask]
    
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
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Propiedades", "📈 Estadísticas", "📊 Evolución", "🔍 Búsqueda"])
    
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
            if 'estado' in df_filtrado.columns:
                fig = px.pie(df_filtrado, names='estado', title='')
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Propiedades por Zona")
            if 'zona' in df_filtrado.columns:
                fig = px.bar(df_filtrado['zona'].value_counts().head(10), 
                            title='Top 10 Zonas',
                            labels={'value': 'Número', 'index': 'Zona'})
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Evolución Temporal")
        
        # Estadísticas históricas
        stats_df = db.obtener_estadisticas_historicas()
        if not stats_df.empty:
            stats_df['fecha'] = pd.to_datetime(stats_df['fecha'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=stats_df['fecha'], y=stats_df['precio_promedio'],
                                    mode='lines+markers', name='Precio Promedio'))
            fig.add_trace(go.Scatter(x=stats_df['fecha'], y=stats_df['total_propiedades'],
                                    mode='lines+markers', name='Total Propiedades'))
            
            fig.update_layout(title="Evolución Histórica")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay suficientes datos históricos para mostrar evolución")
    
    with tab4:
        st.subheader("Búsqueda Avanzada")
        
        col1, col2 = st.columns(2)
        
        with col1:
            termino_busqueda = st.text_input("🔍 Buscar en todos los campos:")
            precio_min = st.number_input("Precio mínimo:", min_value=0, value=0)
        
        with col2:
            habitaciones_min = st.number_input("Habitaciones mínimas:", min_value=0, value=0)
            metros_min = st.number_input("Metros mínimos:", min_value=0, value=0)
        
        # Aplicar búsqueda
        if termino_busqueda:
            mask = df_filtrado.astype(str).apply(lambda x: x.str.contains(termino_busqueda, case=False).any(), axis=1)
            df_busqueda = df_filtrado[mask]
        else:
            df_busqueda = df_filtrado
        
        # Aplicar filtros numéricos
        df_busqueda = df_busqueda[df_busqueda['precio'].apply(lambda x: extraer_numero(x) >= precio_min)]
        df_busqueda = df_busqueda[df_busqueda['habitaciones'].apply(lambda x: extraer_numero(x) >= habitaciones_min)]
        df_busqueda = df_busqueda[df_busqueda['metros'].apply(lambda x: extraer_numero(x) >= metros_min)]
        
        st.write(f"Resultados: {len(df_busqueda)} propiedades")
        st.dataframe(df_busqueda, use_container_width=True)

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