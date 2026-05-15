import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_data, filter_by_date

# Configuración de página
st.set_page_config(page_title="Dashboard Validadores Sonda", layout="wide", page_icon="🚍")

# Título Principal
st.title("🚍 Dashboard Consolidado de Validadores Transantiago")
st.markdown("Análisis de reparaciones, reincidencias y rendimiento técnico.")

# Cargar Datos
try:
    with st.spinner('Cargando datos desde Excel...'):
        df_raw = load_data()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# ====================
# BARRA LATERAL (Filtros)
# ====================
st.sidebar.header("⚙️ Filtros")

# Filtro de Tiempo
time_filter = st.sidebar.radio(
    "Seleccionar Rango de Tiempo",
    ("Último Mes", "Últimos 3 Meses", "Últimos 6 Meses", "Todo el histórico"),
    index=1
)

months_map = {
    "Último Mes": 1,
    "Últimos 3 Meses": 3,
    "Últimos 6 Meses": 6,
    "Todo el histórico": None
}

# Aplicar filtro de fecha
df = filter_by_date(df_raw, 'Fecha Revision', months_map[time_filter])

st.sidebar.markdown("---")
st.sidebar.info(f"Registros analizados: {len(df)}")

# ====================
# SECCIÓN 1: KPIs y Rendimiento
# ====================
st.header("1. Resumen General")
col1, col2, col3 = st.columns(3)

total_revisados = len(df)
total_garantia = len(df[df['Tipo Salida'].str.contains('Garantia', case=False, na=False)])
porcentaje_garantia = (total_garantia / total_revisados * 100) if total_revisados > 0 else 0

with col1:
    st.metric("Total Equipos Revisados", f"{total_revisados}")
with col2:
    st.metric("Salidas a Garantía", f"{total_garantia}")
with col3:
    st.metric("% Enviados a Garantía", f"{porcentaje_garantia:.1f}%")

st.markdown("---")

# ====================
# SECCIÓN 2: ALERTA DE REINCIDENCIAS (Prioridad Alta)
# ====================
st.header("🚨 Análisis de Reincidencias (Garantía)")
st.markdown("Equipos (AMID) que han sido enviados a Garantía múltiples veces en el periodo seleccionado.")

# Filtrar solo salidas a Garantía
df_garantia = df[df['Tipo Salida'].str.contains('Garantia', case=False, na=False)]

# Contar por AMID
reincidencias = df_garantia['AMID'].value_counts().reset_index()
reincidencias.columns = ['AMID', 'Cant. Envíos Garantía']
# Filtrar solo los que han ido más de 1 vez, ordenados de mayor a menor
reincidencias_alert = reincidencias[reincidencias['Cant. Envíos Garantía'] > 1]

col_alert1, col_alert2 = st.columns([1, 1])

with col_alert1:
    st.subheader("🔥 Top Reincidentes")
    if not reincidencias_alert.empty:
        st.dataframe(reincidencias_alert, use_container_width=True)
    else:
        st.success("¡Excelente! No hay equipos que hayan ido a Garantía más de 1 vez en este periodo.")

with col_alert2:
    st.subheader("🔍 Buscador de AMID Específico")
    st.markdown("Pega uno o más AMID separados por coma o espacio para revisar su historial de garantías.")
    search_input = st.text_input("Ingresa AMID(s):")
    
    if search_input:
        # Limpiar entrada y buscar
        amids_to_search = [a.strip() for a in search_input.replace(',', ' ').split() if a.strip()]
        result_search = reincidencias[reincidencias['AMID'].isin(amids_to_search)]
        
        if not result_search.empty:
            st.dataframe(result_search, use_container_width=True)
            
            # Mostrar detalle de esos equipos
            st.markdown("**Detalle de Fallas para los AMID buscados:**")
            detalle = df_garantia[df_garantia['AMID'].isin(amids_to_search)][['AMID', 'Fecha Revision', 'TIPO', 'Diagnostico', 'Tecnico resp.']]
            # Ordenar para agrupar el mismo AMID y ver la historia cronológicamente
            detalle = detalle.sort_values(by=['AMID', 'Fecha Revision'], ascending=[True, False])
            st.dataframe(detalle, use_container_width=True)
        else:
            st.info("Los AMID ingresados no registran salidas a Garantía en este periodo.")

st.markdown("---")

# ====================
# SECCIÓN 3: Análisis de Fallas y Productividad
# ====================
st.header("📈 Top Fallas y Productividad")

col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.subheader("Top 10 Diagnósticos (Fallas)")
    top_fallas = df['Diagnostico'].value_counts().head(10).reset_index()
    top_fallas.columns = ['Diagnóstico', 'Cantidad']
    # Filtrar 'No Registrado' si molesta
    top_fallas = top_fallas[top_fallas['Diagnóstico'] != 'No Registrado']
    
    fig_fallas = px.bar(top_fallas, x='Cantidad', y='Diagnóstico', orientation='h', 
                        color='Cantidad', color_continuous_scale='Viridis')
    fig_fallas.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_fallas, use_container_width=True)

with col_graf2:
    st.subheader("Equipos revisados por Técnico")
    productividad = df['Tecnico resp.'].value_counts().reset_index()
    productividad.columns = ['Técnico', 'Equipos']
    
    fig_prod = px.bar(productividad, x='Técnico', y='Equipos', 
                      color='Equipos', color_continuous_scale='Blues')
    st.plotly_chart(fig_prod, use_container_width=True)
