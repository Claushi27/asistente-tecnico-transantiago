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
        
        # BUSCAMOS EN EL HISTORIAL COMPLETO (df_raw) SIN FILTROS DE FECHA NI GARANTÍA
        detalle_completo = df_raw[df_raw['AMID'].isin(amids_to_search)]
        
        if not detalle_completo.empty:
            # Crear tabla dinámica para que cada "Tipo Salida" sea una columna separada
            resumen_amid = detalle_completo.pivot_table(
                index='AMID', 
                columns='Tipo Salida', 
                aggfunc='size', 
                fill_value=0
            ).reset_index()
            
            # Sumar el total de intervenciones
            cols_numericas = resumen_amid.select_dtypes(include='number').columns
            resumen_amid['Total Intervenciones'] = resumen_amid[cols_numericas].sum(axis=1)
        else:
            resumen_amid = pd.DataFrame(columns=['AMID', 'Garantia', 'Total Intervenciones'])

        # Encontrar los AMIDs ingresados que no están en la base de datos
        amids_encontrados = detalle_completo['AMID'].unique() if not detalle_completo.empty else []
        amids_faltantes = [a for a in amids_to_search if a not in amids_encontrados]
        
        if amids_faltantes:
            # Los que no existen los agregamos con ceros
            df_faltantes = pd.DataFrame([{'AMID': a, 'Total Intervenciones': 0} for a in amids_faltantes])
            resumen_amid = pd.concat([resumen_amid, df_faltantes], ignore_index=True)
            
        if not resumen_amid.empty:
            # Rellenar nulos con 0 por la concatenación y convertir a enteros
            resumen_amid = resumen_amid.fillna(0)
            cols_num = resumen_amid.columns.drop('AMID')
            resumen_amid[cols_num] = resumen_amid[cols_num].astype(int)
            
            # Intentar ordenar por Garantía si existe esa columna, sino por el Total
            sort_cols = ['Garantia', 'Total Intervenciones'] if 'Garantia' in resumen_amid.columns else ['Total Intervenciones']
            resumen_amid = resumen_amid.sort_values(by=sort_cols, ascending=False)
            
            st.dataframe(resumen_amid, use_container_width=True)
            
        if not detalle_completo.empty:
            # Mostrar detalle cronológico de esos equipos
            st.markdown("**Historial Completo para los AMID buscados (Todas las fechas):**")
            detalle = detalle_completo[['AMID', 'Fecha Revision', 'TIPO', 'Tipo Salida', 'Diagnostico', 'Tecnico resp.']]
            
            # Ordenar para agrupar el mismo AMID y ver la historia cronológicamente
            detalle = detalle.sort_values(by=['AMID', 'Fecha Revision'], ascending=[True, False])
            
            # Le damos altura para que se vean más filas sin tener que hacer tanto scroll
            st.dataframe(detalle, use_container_width=True, height=500)

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
