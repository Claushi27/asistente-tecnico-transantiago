import pandas as pd
import os
from dotenv import load_dotenv
import streamlit as st

# Cargar variables de entorno
load_dotenv()

@st.cache_data(ttl=3600)  # Cache de 1 hora para no recargar a cada rato
def load_data():
    """
    Carga y limpia los datos desde el archivo Excel especificado en .env
    """
    file_path = os.getenv("EXCEL_PATH")
    
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo en la ruta: {file_path}. Verifica tu archivo .env")

    # Leer archivo
    df = pd.read_excel(file_path, engine='openpyxl')
    
    # Limpiar nombres de columnas (quitar espacios al final)
    df.columns = df.columns.str.strip()

    # Convertir 'Fecha Revision' a datetime
    if 'Fecha Revision' in df.columns:
        df['Fecha Revision'] = pd.to_datetime(df['Fecha Revision'], dayfirst=True, errors='coerce')
    
    # Asegurar que AMID sea string sin decimales para búsqueda exacta
    if 'AMID' in df.columns:
        df['AMID'] = df['AMID'].astype(str).str.replace(r'\.0$', '', regex=True)

    # Rellenar nulos en columnas de texto importantes
    cols_to_fill = ['Tipo Salida', 'Diagnostico', 'Observaciones', 'Tecnico resp.', 'TIPO']
    for col in cols_to_fill:
        if col in df.columns:
            df[col] = df[col].fillna('No Registrado').astype(str)

    return df

def filter_by_date(df, date_col, months=None):
    """
    Filtra un DataFrame para los últimos X meses usando la columna de fecha.
    """
    if months is None or date_col not in df.columns:
        return df
        
    latest_date = df[date_col].max()
    if pd.isna(latest_date):
        return df
        
    start_date = latest_date - pd.DateOffset(months=months)
    return df[df[date_col] >= start_date]
