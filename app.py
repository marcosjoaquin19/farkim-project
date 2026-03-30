# ==============================================
# Nombre:      app.py
# Descripci├│n: Dashboard principal de Farkim.
#              Login con streamlit-authenticator,
#              5 pesta├▒as con datos en tiempo real
#              desde Google Sheets.
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-19
# ==============================================

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import sys
import os

# ÔöÇÔöÇ Nombres de meses en espa├▒ol ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def formato_mes_es(fecha_str):
    """Convierte '2026-04' o '2026-04-15' a 'Abril 2026'."""
    try:
        partes = str(fecha_str)[:7].split("-")
        return f"{MESES_ES[int(partes[1])]} {partes[0]}"
    except Exception:
        return str(fecha_str)

# ÔöÇÔöÇ Configuraci├│n de la p├ígina ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
st.set_page_config(
    page_title="Farkim ÔÇö Dashboard",
    page_icon="­ƒôè",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ÔöÇÔöÇ Estilos personalizados ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
st.markdown("""
<style>
    /* Ocultar men├║ y footer de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Tarjetas de m├®tricas m├ís grandes */
    [data-testid="metric-container"] {
        background-color: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 10px;
        padding: 15px;
    }

    /* Color del valor principal de m├®tricas */
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700;
    }

    /* Separador de pesta├▒as */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e1e2e;
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ÔöÇÔöÇ Carga del archivo de configuraci├│n de usuarios ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
@st.cache_resource
def cargar_config():
    """
    Carga la configuraci├│n de autenticaci├│n.
    En Streamlit Cloud: lee de st.secrets["auth"]
    En local: lee del archivo config.yaml
    """
    # ÔöÇÔöÇ Intento 1: Streamlit Cloud (st.secrets) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    try:
        if "auth" in st.secrets:
            config = dict(st.secrets["auth"])
            # Convertir secciones anidadas de secrets a dicts normales
            config["credentials"] = dict(config["credentials"])
            config["credentials"]["usernames"] = {
                k: dict(v) for k, v in dict(config["credentials"]["usernames"]).items()
            }
            config["cookie"] = dict(config["cookie"])
            return config
    except Exception:
        pass

    # ÔöÇÔöÇ Intento 2: archivo local config.yaml ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    try:
        with open("config.yaml") as f:
            config = yaml.load(f, Loader=SafeLoader)
        return config
    except FileNotFoundError:
        st.error("ÔØî Archivo config.yaml no encontrado. Ejecut├í crear_config_auth.py primero.")
        st.stop()


# ÔöÇÔöÇ Funciones de carga de datos desde Google Sheets ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
@st.cache_data(ttl=300)   # 300 segundos = 5 minutos de cach├®
def cargar_pipeline():
    """
    Carga la hoja 'Pipeline Completo' desde Google Sheets.
    ttl=300 significa que se actualiza autom├íticamente cada 5 minutos.

    Excluye autom├íticamente las oportunidades GANADAS:
    - Odoo asigna Probabilidad 100% cuando se marca como Ganada
    - O la etapa contiene "GANAD" (ej: "Ganada", "GANADO")
    Estas ya son ventas cerradas ÔÇö no corresponde trackearlas en el pipeline.
    """
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja

        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Pipeline Completo")

        datos = hoja.get_all_records()
        df = pd.DataFrame(datos)

        if df.empty:
            return df

        total_antes = len(df)

        # Excluir oportunidades ganadas:
        # Condici├│n 1: Probabilidad 100% ÔåÆ Odoo la marca as├¡ cuando est├í ganada
        # Condici├│n 2: Nombre de etapa contiene "GANAD" por si acaso
        mask_ganadas = pd.Series([False] * len(df), index=df.index)

        if "Probabilidad %" in df.columns:
            mask_ganadas = mask_ganadas | (pd.to_numeric(df["Probabilidad %"], errors="coerce") == 100)

        if "Etapa" in df.columns:
            mask_ganadas = mask_ganadas | df["Etapa"].str.upper().str.contains("GANAD", na=False)

        df = df[~mask_ganadas]

        ganadas_excluidas = total_antes - len(df)
        if ganadas_excluidas > 0:
            print(f"Pipeline: {ganadas_excluidas} oportunidades ganadas excluidas del dashboard.")

        return df
    except Exception as e:
        st.error(f"Error cargando Pipeline Completo: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def cargar_vendedores():
    """Carga la hoja 'Por Vendedor' desde Google Sheets."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja

        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Por Vendedor")

        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        st.error(f"Error cargando Por Vendedor: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def cargar_ventas_mes():
    """Carga la hoja 'Ventas por Mes USD' desde Google Sheets."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja

        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Ventas por Mes USD")

        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        st.error(f"Error cargando Ventas por Mes USD: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def cargar_ventas_cerradas():
    """Carga la hoja 'Ventas Cerradas' desde Google Sheets."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja

        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Ventas Cerradas")

        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        st.error(f"Error cargando Ventas Cerradas: {e}")
        return pd.DataFrame()


# =============================================================================
# ALTO CERRÓ — CARGA SEMANAL MANUAL (COMENTADO — PENDIENTE CONFIRMACIÓN)
# -----------------------------------------------------------------------------
# Activar cuando Alto Cerró confirme el envío semanal del CSV.
# Pasos para activar:
#   1. Descomentar las 2 funciones de abajo
#   2. En tab_ventas_del_mes(): reemplazar cargar_ventas_cerradas() por
#      cargar_ac_ventas_detalle() y cargar_ac_ventas_mensual()
#   3. Eliminar el bloque que usa "Ventas Cerradas" (Odoo)
# =============================================================================
#
# @st.cache_data(ttl=120)
# def cargar_ac_ventas_detalle():
#     """Carga 'AC Ventas Detalle' — filas individuales cargadas semana a semana."""
#     try:
#         sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
#         from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja
#         cliente = autenticar()
#         spreadsheet = abrir_spreadsheet(cliente)
#         hoja = obtener_hoja(spreadsheet, "AC Ventas Detalle")
#         datos = hoja.get_all_records()
#         return pd.DataFrame(datos)
#     except Exception as e:
#         st.error(f"Error cargando AC Ventas Detalle: {e}")
#         return pd.DataFrame()
#
# @st.cache_data(ttl=120)
# def cargar_ac_ventas_mensual():
#     """Carga 'AC Ventas Mensual' — resumen mensual calculado desde Alto Cerró."""
#     try:
#         sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
#         from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja
#         cliente = autenticar()
#         spreadsheet = abrir_spreadsheet(cliente)
#         hoja = obtener_hoja(spreadsheet, "AC Ventas Mensual")
#         datos = hoja.get_all_records()
#         return pd.DataFrame(datos)
#     except Exception as e:
#         st.error(f"Error cargando AC Ventas Mensual: {e}")
#         return pd.DataFrame()
#
# =============================================================================
# FIN BLOQUE ALTO CERRÓ — NO MODIFICAR HASTA CONFIRMAR CON ALTO CERRÓ
# =============================================================================


@st.cache_data(ttl=60)
def cargar_objetivos():
    """Carga la hoja 'Objetivos Mensuales' desde Google Sheets. TTL corto porque se edita."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja

        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Objetivos Mensuales")

        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        st.error(f"Error cargando Objetivos Mensuales: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def cargar_historial_cierres():
    """Carga la hoja 'Historial Cierres' desde Google Sheets."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja
        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Historial Cierres")
        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        st.error(f"Error cargando Historial Cierres: {e}")
        return pd.DataFrame()


def guardar_cierre_mes(mes_es, objetivo, facturado, usuario):
    """Guarda el cierre del mes en la hoja 'Historial Cierres'."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja
        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Historial Cierres")

        # Verificar si ya existe un cierre para ese mes
        datos = hoja.get_all_records()
        for i, fila in enumerate(datos):
            if fila.get("Mes") == mes_es:
                # Actualizar fila existente
                fila_idx = i + 2  # +1 por encabezado, +1 por ├¡ndice 1-based
                estado = "Ô£à Superado" if facturado >= objetivo else "ÔØî No superado"
                hoja.update(f"A{fila_idx}:F{fila_idx}", [[
                    mes_es, objetivo, round(facturado, 2), estado,
                    datetime.now().strftime("%Y-%m-%d %H:%M"), usuario
                ]])
                cargar_historial_cierres.clear()
                return True

        # Si no existe, agregar nueva fila
        estado = "Ô£à Superado" if facturado >= objetivo else "ÔØî No superado"
        hoja.append_row([
            mes_es, objetivo, round(facturado, 2), estado,
            datetime.now().strftime("%Y-%m-%d %H:%M"), usuario
        ])
        cargar_historial_cierres.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar cierre: {e}")
        return False


def guardar_objetivo(mes_es, monto, usuario):
    """Guarda o actualiza el objetivo mensual en Google Sheets."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja

        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Objetivos Mensuales")

        fecha_edicion = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Buscar si ya existe una fila para este mes
        datos = hoja.get_all_values()
        fila_encontrada = None
        for i, fila in enumerate(datos):
            if i == 0:
                continue  # Saltar encabezado
            if len(fila) > 0 and fila[0] == mes_es:
                fila_encontrada = i + 1  # gspread usa base 1
                break

        if fila_encontrada:
            # Actualizar fila existente
            hoja.update(f"A{fila_encontrada}:D{fila_encontrada}",
                        [[mes_es, monto, usuario, fecha_edicion]])
        else:
            # Agregar fila nueva
            hoja.append_row([mes_es, monto, usuario, fecha_edicion])

        # Limpiar cach├® para que se vea el cambio
        cargar_objetivos.clear()
        return True
    except Exception as e:
        st.error(f"Error guardando objetivo: {e}")
        return False


@st.cache_data(ttl=300)
def cargar_sin_movimiento():
    """Carga la hoja 'Sin Movimiento' desde Google Sheets."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja

        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Sin Movimiento")

        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        st.error(f"Error cargando Sin Movimiento: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def cargar_historico_mensual():
    """Carga la hoja 'Historico Mensual USD' desde Google Sheets."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja

        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Historico Mensual USD")

        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        st.error(f"Error cargando Historico Mensual USD: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def cargar_historico_anual():
    """Carga la hoja 'Historico Anual USD' desde Google Sheets."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja

        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Historico Anual USD")

        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        st.error(f"Error cargando Historico Anual USD: {e}")
        return pd.DataFrame()


# ÔöÇÔöÇ Paleta de colores de Farkim ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
COLORES = {
    "activa":    "#4CAF50",   # Verde
    "en_riesgo": "#FF9800",   # Naranja
    "inactiva":  "#F44336",   # Rojo
    "primario":  "#2196F3",   # Azul
    "fondo":     "#1e1e2e",   # Fondo oscuro
}

COLOR_ESTADOS = {
    "Activa":    COLORES["activa"],
    "En riesgo": COLORES["en_riesgo"],
    "Inactiva":  COLORES["inactiva"],
}


# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
# TABS DEL DASHBOARD
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ

def tab_resumen(rol):
    """
    Pesta├▒a de resumen ejecutivo.
    Muestra los KPIs principales del pipeline en tarjetas grandes.
    """
    st.header("­ƒôè Resumen Ejecutivo")
    st.caption(f"├Ültima actualizaci├│n: {datetime.now().strftime('%d/%m/%Y %H:%M')} hs  ÔÇó  Se refresca cada 5 minutos")

    df = cargar_pipeline()
    if df.empty:
        st.warning("No se pudieron cargar los datos del pipeline.")
        return

    # ÔöÇÔöÇ KPIs principales ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col1, col2, col3, col4 = st.columns(4)

    total_opps = len(df)
    total_usd  = df["Monto USD"].sum() if "Monto USD" in df.columns else 0

    activas    = len(df[df["Estado"] == "Activa"])    if "Estado" in df.columns else 0
    en_riesgo  = len(df[df["Estado"] == "En riesgo"]) if "Estado" in df.columns else 0
    inactivas  = len(df[df["Estado"] == "Inactiva"])  if "Estado" in df.columns else 0

    monto_activas   = df.loc[df["Estado"] == "Activa",    "Monto USD"].sum() if "Estado" in df.columns else 0
    monto_en_riesgo = df.loc[df["Estado"] == "En riesgo", "Monto USD"].sum() if "Estado" in df.columns else 0

    with col1:
        st.metric("­ƒÆ░ Pipeline Total", f"${total_usd:,.0f} USD", f"{total_opps} oportunidades")
    with col2:
        st.metric("Ô£à Activas", f"{activas}", f"${monto_activas:,.0f} USD")
    with col3:
        st.metric("ÔÜá´©Å En Riesgo", f"{en_riesgo}", f"${monto_en_riesgo:,.0f} USD")
    with col4:
        porc_inactivas = round((inactivas / total_opps * 100), 1) if total_opps > 0 else 0
        st.metric("­ƒö┤ Inactivas", f"{inactivas}", f"{porc_inactivas}% del total")

    st.divider()

    # ÔöÇÔöÇ Gr├íficos fila 1 ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("Distribuci├│n del Pipeline")
        if "Estado" in df.columns:
            conteo = df["Estado"].value_counts().reset_index()
            conteo.columns = ["Estado", "Cantidad"]

            fig_pie = px.pie(
                conteo,
                values="Cantidad",
                names="Estado",
                color="Estado",
                color_discrete_map=COLOR_ESTADOS,
                hole=0.45,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(
                showlegend=True,
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_der:
        st.subheader("Monto USD por Estado")
        if "Estado" in df.columns and "Monto USD" in df.columns:
            montos = df.groupby("Estado")["Monto USD"].sum().reset_index()
            montos.columns = ["Estado", "Monto USD"]

            fig_bar = px.bar(
                montos,
                x="Estado",
                y="Monto USD",
                color="Estado",
                color_discrete_map=COLOR_ESTADOS,
                text_auto="$.3s",
            )
            fig_bar.update_layout(
                showlegend=False,
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#333"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # ÔöÇÔöÇ Top 20 oportunidades activas ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.subheader("­ƒÅå Top 20 Oportunidades Activas por Monto")
    if "Estado" in df.columns and "Monto USD" in df.columns:
        top20 = (
            df[df["Estado"] == "Activa"]
            .sort_values("Monto USD", ascending=False)
            .head(20)[["Oportunidad", "Cliente", "Vendedor", "Etapa", "Monto USD", "Probabilidad %"]]
            .reset_index(drop=True)
        )
        top20.index += 1
        top20["Monto USD"] = top20["Monto USD"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(top20, use_container_width=True, height=700)


def tab_pipeline(rol):
    """
    Pesta├▒a con el pipeline completo filtrable.
    Permite filtrar por estado, vendedor y rango de monto.
    """
    st.header("­ƒôï Pipeline Completo")

    df = cargar_pipeline()
    if df.empty:
        st.warning("No se pudieron cargar los datos del pipeline.")
        return

    # ÔöÇÔöÇ Filtros horizontales dentro de la pesta├▒a ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        estados_disp = ["Todos"] + sorted(df["Estado"].unique().tolist()) if "Estado" in df.columns else ["Todos"]
        estado_sel = st.selectbox("­ƒöì Estado", estados_disp, key="filtro_estado_pipeline")

    with col_f2:
        if "Vendedor" in df.columns:
            vendedores_disp = ["Todos"] + sorted(df["Vendedor"].unique().tolist())
            vendedor_sel = st.selectbox("­ƒæñ Vendedor", vendedores_disp, key="filtro_vendedor_pipeline")
        else:
            vendedor_sel = "Todos"

    with col_f3:
        if "Monto USD" in df.columns and len(df) > 0:
            monto_min = float(df["Monto USD"].min())
            monto_max = float(df["Monto USD"].max())
            monto_rango = st.slider(
                "­ƒÆ░ Rango de Monto USD",
                min_value=monto_min,
                max_value=monto_max,
                value=(monto_min, monto_max),
                format="$%.0f",
                key="filtro_monto_pipeline"
            )
        else:
            monto_rango = (0, 99999999)

    st.divider()

    # ÔöÇÔöÇ Aplicar filtros ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    df_filtrado = df.copy()

    if estado_sel != "Todos" and "Estado" in df.columns:
        df_filtrado = df_filtrado[df_filtrado["Estado"] == estado_sel]

    if vendedor_sel != "Todos" and "Vendedor" in df.columns:
        df_filtrado = df_filtrado[df_filtrado["Vendedor"] == vendedor_sel]

    if "Monto USD" in df.columns:
        df_filtrado = df_filtrado[
            (df_filtrado["Monto USD"] >= monto_rango[0]) &
            (df_filtrado["Monto USD"] <= monto_rango[1])
        ]

    # ÔöÇÔöÇ M├®tricas del filtro ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Oportunidades filtradas", len(df_filtrado))
    with col2:
        monto_total = df_filtrado["Monto USD"].sum() if "Monto USD" in df_filtrado.columns else 0
        st.metric("Monto filtrado", f"${monto_total:,.0f} USD")
    with col3:
        porc = round(len(df_filtrado) / len(df) * 100, 1) if len(df) > 0 else 0
        st.metric("% del pipeline total", f"{porc}%")

    st.divider()

    # ÔöÇÔöÇ Tabla filtrable ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    columnas_mostrar = [c for c in ["Oportunidad", "Cliente", "Vendedor", "Etapa", "Estado",
                                     "Monto USD", "Probabilidad %", "D├¡as Sin Actividad",
                                     "Fecha Creaci├│n", "├Ültima Actividad"] if c in df_filtrado.columns]

    df_mostrar = df_filtrado[columnas_mostrar].sort_values("Monto USD", ascending=False).reset_index(drop=True)
    df_mostrar.index += 1

    # Formatear monto para visualizaci├│n
    if "Monto USD" in df_mostrar.columns:
        df_mostrar["Monto USD"] = df_mostrar["Monto USD"].apply(lambda x: f"${x:,.0f}")

    st.dataframe(df_mostrar, use_container_width=True, height=500)
    st.caption(f"Mostrando {len(df_filtrado)} de {len(df)} oportunidades")


def tab_vendedores(rol):
    """
    Pesta├▒a de an├ílisis por vendedor.
    Muestra ranking mensual de facturaci├│n (ventas cerradas del mes actual).
    Solo visible para rol 'gerente' o 'admin'.
    """
    # Control de acceso por rol
    if rol not in ["gerente", "admin"]:
        st.warning("­ƒöÆ Esta secci├│n es solo para gerentes y administradores.")
        return

    hoy = date.today()
    mes_actual_es = f"{MESES_ES[hoy.month]} {hoy.year}"

    st.header(f"­ƒæÑ Ranking de Vendedores ÔÇö {mes_actual_es}")
    st.caption("Basado en ventas cerradas (oportunidades ganadas) del mes actual")

    # Cargar ventas cerradas
    df_ventas = cargar_ventas_cerradas()

    if df_ventas.empty or "Vendedor" not in df_ventas.columns:
        st.warning("No se pudieron cargar las ventas cerradas.")
        return

    # ÔöÇÔöÇ Filtrar solo el mes actual ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    if "Mes Cierre" in df_ventas.columns:
        df_mes = df_ventas[df_ventas["Mes Cierre"] == mes_actual_es].copy()
    else:
        df_mes = df_ventas.copy()

    # Asegurar que Monto USD sea num├®rico
    if "Monto USD" in df_mes.columns:
        df_mes["Monto USD"] = pd.to_numeric(df_mes["Monto USD"], errors="coerce").fillna(0)

    # ÔöÇÔöÇ Resumen por vendedor ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    if df_mes.empty:
        st.info(f"No hay ventas cerradas en {mes_actual_es} todav├¡a.")
        return

    df_ranking = df_mes.groupby("Vendedor").agg(
        Facturado=("Monto USD", "sum"),
        Operaciones=("Monto USD", "count"),
        Ticket_Promedio=("Monto USD", "mean")
    ).reset_index().sort_values("Facturado", ascending=False)

    total_facturado = df_ranking["Facturado"].sum()
    total_ops = int(df_ranking["Operaciones"].sum())

    # ÔöÇÔöÇ M├®tricas generales ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("­ƒÆ░ Facturado Total del Mes", f"${total_facturado:,.0f} USD")
    with col2:
        st.metric("­ƒôï Operaciones Cerradas", total_ops)
    with col3:
        st.metric("­ƒæÑ Vendedores Activos", len(df_ranking))

    st.divider()

    # ÔöÇÔöÇ Gr├íficos ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader(f"­ƒÅå Ranking Facturaci├│n {mes_actual_es}")
        df_chart = df_ranking.sort_values("Facturado", ascending=True)

        fig_rank = px.bar(
            df_chart,
            x="Facturado",
            y="Vendedor",
            orientation="h",
            color="Facturado",
            color_continuous_scale=["#1e1e2e", "#2196F3"],
            text=df_chart["Facturado"].apply(lambda x: f"${x:,.0f}"),
        )
        fig_rank.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            showlegend=False,
            coloraxis_showscale=False,
            yaxis=dict(showgrid=False),
            xaxis=dict(showgrid=True, gridcolor="#333", title="USD Facturado"),
        )
        st.plotly_chart(fig_rank, use_container_width=True)

    with col_der:
        st.subheader("­ƒôè Participaci├│n en Facturaci├│n")
        fig_pie = px.pie(
            df_ranking,
            values="Facturado",
            names="Vendedor",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_pie.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # ÔöÇÔöÇ Tabla detalle por vendedor ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.subheader("Detalle por Vendedor")
    df_tabla = df_ranking.copy()
    df_tabla["% del Total"] = (df_tabla["Facturado"] / total_facturado * 100).round(1)
    df_tabla = df_tabla.rename(columns={
        "Facturado": "Facturado USD",
        "Ticket_Promedio": "Ticket Promedio USD"
    })
    df_tabla["Facturado USD"] = df_tabla["Facturado USD"].apply(lambda x: f"${x:,.0f}")
    df_tabla["Ticket Promedio USD"] = df_tabla["Ticket Promedio USD"].apply(lambda x: f"${x:,.0f}")
    df_tabla["% del Total"] = df_tabla["% del Total"].apply(lambda x: f"{x}%")
    df_tabla = df_tabla.reset_index(drop=True)
    df_tabla.index += 1

    st.dataframe(df_tabla, use_container_width=True)

    st.divider()

    # ÔöÇÔöÇ Detalle de operaciones del mes ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.subheader(f"­ƒôï Operaciones Cerradas ÔÇö {mes_actual_es}")
    cols_detalle = [c for c in ["Oportunidad", "Cliente", "Vendedor", "Monto USD", "Fecha Cierre"] if c in df_mes.columns]
    df_detalle = df_mes[cols_detalle].sort_values("Monto USD", ascending=False).reset_index(drop=True)
    df_detalle.index += 1
    if "Monto USD" in df_detalle.columns:
        df_detalle["Monto USD"] = df_detalle["Monto USD"].apply(lambda x: f"${x:,.0f}")
    st.dataframe(df_detalle, use_container_width=True)


def tab_evolucion(rol):
    """
    Pesta├▒a de evoluci├│n temporal de ventas.
    Muestra la tendencia por mes con monto acumulado.
    """
    st.header("­ƒôê Evoluci├│n de Ventas en el Tiempo")

    df = cargar_ventas_mes()
    if df.empty:
        st.warning("No se pudieron cargar los datos temporales.")
        return

    # Aseguramos orden cronol├│gico y convertimos a espa├▒ol
    if "Mes" in df.columns:
        df = df.sort_values("Mes")
        df["Mes Display"] = df["Mes"].apply(formato_mes_es)

    # ÔöÇÔöÇ M├®tricas clave de evoluci├│n ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col1, col2, col3 = st.columns(3)

    if "Monto Total USD" in df.columns:
        mes_top = df.loc[df["Monto Total USD"].idxmax()]
        with col1:
            st.metric("­ƒôà Mejor Mes", formato_mes_es(mes_top["Mes"]), f"${mes_top['Monto Total USD']:,.0f} USD")

    if "Monto Acumulado USD" in df.columns and len(df) > 0:
        acumulado = df["Monto Acumulado USD"].iloc[-1]
        with col2:
            st.metric("­ƒÆ░ Pipeline Acumulado", f"${acumulado:,.0f} USD")

    if "Oportunidades Creadas" in df.columns:
        total_opps_hist = df["Oportunidades Creadas"].sum()
        with col3:
            st.metric("­ƒôè Oportunidades Hist├│ricas", f"{total_opps_hist}")

    st.divider()

    # ÔöÇÔöÇ Gr├ífico de l├¡neas: monto por mes ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.subheader("Monto USD por Mes")
    if "Mes" in df.columns and "Monto Total USD" in df.columns:
        fig_linea = go.Figure()

        fig_linea.add_trace(go.Bar(
            x=df["Mes Display"],
            y=df["Monto Total USD"],
            name="Monto Mensual",
            marker_color=COLORES["primario"],
            opacity=0.8,
        ))

        if "Monto Acumulado USD" in df.columns:
            fig_linea.add_trace(go.Scatter(
                x=df["Mes Display"],
                y=df["Monto Acumulado USD"],
                name="Acumulado",
                mode="lines+markers",
                line=dict(color="#FF9800", width=3),
                yaxis="y2",
            ))

        fig_linea.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#333", title="Monto Mensual USD"),
            yaxis2=dict(
                overlaying="y",
                side="right",
                title="Monto Acumulado USD",
                showgrid=False,
            ),
            barmode="group",
        )
        st.plotly_chart(fig_linea, use_container_width=True)

    # ÔöÇÔöÇ Tabla de meses ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.subheader("Detalle por Mes")
    df_tabla = df.copy()

    for col in ["Monto Total USD", "Ticket Promedio USD", "Monto Acumulado USD"]:
        if col in df_tabla.columns:
            df_tabla[col] = df_tabla[col].apply(lambda x: f"${x:,.0f}")

    # Reemplazar columna Mes con la versi├│n en espa├▒ol
    if "Mes Display" in df_tabla.columns:
        df_tabla["Mes"] = df_tabla["Mes Display"]
        df_tabla = df_tabla.drop(columns=["Mes Display"])
    df_tabla = df_tabla.sort_values("Mes", ascending=False).reset_index(drop=True)
    df_tabla.index += 1
    st.dataframe(df_tabla, use_container_width=True)


def tab_historico(rol):
    """
    Pesta├▒a de facturaci├│n hist├│rica (2020-2026) con datos de Alto Cerr├│.
    Muestra evoluci├│n mensual y anual en USD usando el d├│lar real de cada venta.
    """
    st.header("­ƒô£ Facturaci├│n Hist├│rica (2020-2026)")
    st.caption("Fuente: Alto Cerr├│  ÔÇó  Montos convertidos a USD con el d├│lar oficial del d├¡a de cada venta")

    df_mensual = cargar_historico_mensual()
    df_anual = cargar_historico_anual()

    if df_mensual.empty:
        st.warning("No se pudieron cargar los datos hist├│ricos.")
        return

    # ÔöÇÔöÇ KPIs principales ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col1, col2, col3, col4 = st.columns(4)

    total_usd = df_anual["Facturacion USD"].sum() if not df_anual.empty else 0
    total_ops = df_anual["Operaciones"].sum() if not df_anual.empty else 0
    anios = len(df_anual) if not df_anual.empty else 0
    promedio_anual = total_usd / anios if anios > 0 else 0

    with col1:
        st.metric("­ƒÆ░ Facturaci├│n Total", f"${total_usd:,.0f} USD", f"6 a├▒os de historia")
    with col2:
        st.metric("­ƒôè Operaciones", f"{total_ops:,.0f}", f"{anios} a├▒os")
    with col3:
        st.metric("­ƒôà Promedio Anual", f"${promedio_anual:,.0f} USD")
    with col4:
        if not df_anual.empty:
            mejor_anio = df_anual.loc[df_anual["Facturacion USD"].idxmax()]
            st.metric("­ƒÅå Mejor A├▒o", f"{int(mejor_anio['Anio'])}", f"${mejor_anio['Facturacion USD']:,.0f} USD")

    st.divider()

    # ÔöÇÔöÇ Gr├ífico barras: facturaci├│n anual ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.subheader("Facturaci├│n Anual en USD")

    if not df_anual.empty:
        df_anual_plot = df_anual.copy()
        df_anual_plot['Anio'] = df_anual_plot['Anio'].astype(str)

        # Color especial para 2026 (a├▒o incompleto)
        colores_anual = [COLORES["primario"] if a != "2026" else "#FF9800" for a in df_anual_plot['Anio']]

        fig_anual = go.Figure()
        fig_anual.add_trace(go.Bar(
            x=df_anual_plot["Anio"],
            y=df_anual_plot["Facturacion USD"],
            marker_color=colores_anual,
            text=[f"${v:,.0f}" for v in df_anual_plot["Facturacion USD"]],
            textposition="outside",
            textfont=dict(color="white", size=12),
        ))

        fig_anual.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis=dict(showgrid=False, title="A├▒o"),
            yaxis=dict(showgrid=True, gridcolor="#333", title="USD"),
            showlegend=False,
            annotations=[dict(
                x="2026", y=df_anual_plot[df_anual_plot["Anio"] == "2026"]["Facturacion USD"].values[0] if "2026" in df_anual_plot["Anio"].values else 0,
                text="En curso", showarrow=True, arrowhead=2, font=dict(color="#FF9800"),
                ax=0, ay=-40,
            )] if "2026" in df_anual_plot["Anio"].values else [],
        )
        st.plotly_chart(fig_anual, use_container_width=True)

    st.divider()

    # ÔöÇÔöÇ Gr├ífico l├¡neas: evoluci├│n mensual ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.subheader("Evoluci├│n Mensual en USD")

    if "Periodo" in df_mensual.columns and "Facturacion USD" in df_mensual.columns:
        df_plot = df_mensual.sort_values("Periodo").copy()

        fig_mensual = go.Figure()

        # Barras de facturaci├│n mensual
        fig_mensual.add_trace(go.Bar(
            x=df_plot["Mes"],
            y=df_plot["Facturacion USD"],
            name="Facturaci├│n Mensual",
            marker_color=COLORES["primario"],
            opacity=0.6,
        ))

        # L├¡nea de tendencia (media m├│vil 6 meses)
        if len(df_plot) > 6:
            df_plot['media_movil'] = df_plot['Facturacion USD'].rolling(window=6, min_periods=1).mean()
            fig_mensual.add_trace(go.Scatter(
                x=df_plot["Mes"],
                y=df_plot["media_movil"],
                name="Tendencia (6 meses)",
                mode="lines",
                line=dict(color="#FF9800", width=3),
            ))

        fig_mensual.update_layout(
            height=450,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            xaxis=dict(showgrid=False, title="Mes", tickangle=-45, dtick=3),
            yaxis=dict(showgrid=True, gridcolor="#333", title="USD"),
        )
        st.plotly_chart(fig_mensual, use_container_width=True)

    st.divider()

    # ÔöÇÔöÇ Tabla resumen anual ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.subheader("Resumen por A├▒o")

    if not df_anual.empty:
        df_tabla = df_anual.copy()
        df_tabla = df_tabla.rename(columns={
            "Anio": "A├▒o",
            "Facturacion USD": "Facturaci├│n USD",
            "Ticket Promedio USD": "Ticket Prom. USD",
            "Clientes Unicos": "Clientes",
            "Productos Unicos": "Productos",
            "Dolar Promedio": "D├│lar Prom.",
        })

        for col in ["Facturaci├│n USD", "Ticket Prom. USD"]:
            if col in df_tabla.columns:
                df_tabla[col] = df_tabla[col].apply(lambda x: f"${x:,.0f}")

        if "D├│lar Prom." in df_tabla.columns:
            df_tabla["D├│lar Prom."] = df_tabla["D├│lar Prom."].apply(lambda x: f"${x:,.0f}")

        df_tabla = df_tabla.sort_values("A├▒o", ascending=False).reset_index(drop=True)
        df_tabla.index += 1
        st.dataframe(df_tabla, use_container_width=True)


def tab_sin_movimiento(rol):
    """
    Pesta├▒a de oportunidades sin movimiento (+60 d├¡as).
    Solo visible para rol 'gerente' o 'admin'.
    Ordenadas por urgencia.
    """
    st.header("­ƒö┤ Oportunidades Sin Movimiento")

    if rol not in ["gerente", "admin"]:
        st.warning("­ƒöÆ Esta secci├│n es solo para gerentes y administradores.")
        return

    df = cargar_sin_movimiento()
    if df.empty:
        st.warning("No se pudieron cargar los datos de oportunidades inactivas.")
        return

    # ÔöÇÔöÇ M├®tricas de urgencia ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col1, col2, col3, col4 = st.columns(4)

    total = len(df)
    criticas = len(df[df["Urgencia"].str.startswith("CRITICA")]) if "Urgencia" in df.columns else 0
    altas    = len(df[df["Urgencia"].str.startswith("ALTA")])    if "Urgencia" in df.columns else 0
    medias   = len(df[df["Urgencia"].str.startswith("MEDIA")])   if "Urgencia" in df.columns else 0
    monto_riesgo = df["Monto USD"].sum() if "Monto USD" in df.columns else 0

    with col1:
        st.metric("Total inactivas", total, f"${monto_riesgo:,.0f} USD en riesgo")
    with col2:
        st.metric("­ƒö┤ CR├ìTICAS (+6 meses)", criticas, delta_color="inverse")
    with col3:
        st.metric("­ƒƒá ALTAS (+3 meses)", altas, delta_color="inverse")
    with col4:
        st.metric("­ƒƒí MEDIAS (+2 meses)", medias, delta_color="inverse")

    st.divider()

    # ÔöÇÔöÇ Gr├ífico por vendedor ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("Inactivas por Vendedor")
        if "Vendedor" in df.columns:
            por_vendedor = df["Vendedor"].value_counts().reset_index()
            por_vendedor.columns = ["Vendedor", "Cantidad"]

            fig_vend = px.bar(
                por_vendedor.sort_values("Cantidad"),
                x="Cantidad",
                y="Vendedor",
                orientation="h",
                color="Cantidad",
                color_continuous_scale=["#FF9800", "#F44336"],
                text_auto=True,
            )
            fig_vend.update_layout(
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                showlegend=False,
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_vend, use_container_width=True)

    with col_der:
        st.subheader("Distribuci├│n por Urgencia")
        if "Urgencia" in df.columns:
            por_urgencia = df["Urgencia"].value_counts().reset_index()
            por_urgencia.columns = ["Urgencia", "Cantidad"]

            colores_urg = {
                "CRITICA ÔÇö +6 meses sin contacto": "#F44336",
                "ALTA ÔÇö +3 meses sin contacto":    "#FF9800",
                "MEDIA ÔÇö +2 meses sin contacto":   "#FFEB3B",
            }

            fig_urg = px.pie(
                por_urgencia,
                values="Cantidad",
                names="Urgencia",
                color="Urgencia",
                color_discrete_map=colores_urg,
                hole=0.4,
            )
            fig_urg.update_traces(textposition="inside", textinfo="percent+value")
            fig_urg.update_layout(
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
            )
            st.plotly_chart(fig_urg, use_container_width=True)

    st.divider()

    # ÔöÇÔöÇ Tabla de inactivas con filtro de urgencia ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.subheader("Listado de Oportunidades Sin Movimiento")

    urgencia_sel = st.radio(
        "Filtrar por urgencia:",
        ["Todas", "CRITICA", "ALTA", "MEDIA"],
        horizontal=True
    )

    df_filtrado = df.copy()
    if urgencia_sel != "Todas" and "Urgencia" in df.columns:
        df_filtrado = df_filtrado[df_filtrado["Urgencia"].str.startswith(urgencia_sel)]

    # Formatear monto
    df_mostrar = df_filtrado.copy()
    if "Monto USD" in df_mostrar.columns:
        df_mostrar["Monto USD"] = df_mostrar["Monto USD"].apply(lambda x: f"${x:,.0f}")

    df_mostrar = df_mostrar.reset_index(drop=True)
    df_mostrar.index += 1

    st.dataframe(df_mostrar, use_container_width=True, height=400)
    st.caption(f"Mostrando {len(df_filtrado)} oportunidades inactivas")


def tab_ventas_del_mes(rol):
    """
    Pesta├▒a de ventas cerradas del mes con seguimiento de objetivo.
    Muestra progreso semanal, comparaci├│n con meses anteriores,
    y permite al gerente editar el objetivo mensual.
    """
    st.header("­ƒÆ░ Ventas del Mes")

    if rol not in ["gerente", "admin"]:
        st.warning("­ƒöÆ Esta secci├│n es solo para gerentes y administradores.")
        return

    df = cargar_ventas_cerradas()
    df_obj = cargar_objetivos()

    # ÔöÇÔöÇ Mes actual en formato espa├▒ol ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    hoy = date.today()
    mes_actual_es = f"{MESES_ES[hoy.month]} {hoy.year}"
    mes_actual_num = f"{hoy.year}-{hoy.month:02d}"

    # ÔöÇÔöÇ Filtrar ventas del mes actual ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    df_mes = pd.DataFrame()
    if not df.empty and "Fecha Cierre" in df.columns:
        df["Fecha Cierre"] = df["Fecha Cierre"].astype(str)
        df_mes = df[df["Fecha Cierre"].str.startswith(mes_actual_num)]

    ventas_mes = df_mes["Monto USD"].sum() if not df_mes.empty and "Monto USD" in df_mes.columns else 0

    # ÔöÇÔöÇ Obtener objetivo del mes actual ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    objetivo = 0
    if not df_obj.empty and "Mes" in df_obj.columns:
        fila_obj = df_obj[df_obj["Mes"] == mes_actual_es]
        if not fila_obj.empty and "Objetivo USD" in df_obj.columns:
            objetivo = float(fila_obj.iloc[0]["Objetivo USD"])

    # ÔöÇÔöÇ KPIs principales ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col1, col2, col3, col4 = st.columns(4)

    porcentaje = round((ventas_mes / objetivo * 100), 1) if objetivo > 0 else 0
    ops_cerradas = len(df_mes)
    ticket_promedio = round(ventas_mes / ops_cerradas, 0) if ops_cerradas > 0 else 0

    with col1:
        st.metric("­ƒÆ░ Ventas del Mes", f"${ventas_mes:,.0f} USD", f"{ops_cerradas} operaciones cerradas")
    with col2:
        st.metric("­ƒÄ» Objetivo", f"${objetivo:,.0f} USD", mes_actual_es)
    with col3:
        delta_color = "normal" if porcentaje >= 80 else "inverse"
        st.metric("­ƒôè Cumplimiento", f"{porcentaje}%", f"{'En camino' if porcentaje >= 70 else 'Atenci├│n'}", delta_color=delta_color)
    with col4:
        st.metric("­ƒº¥ Ticket Promedio", f"${ticket_promedio:,.0f} USD")

    # ÔöÇÔöÇ Barra de progreso visual ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    if objetivo > 0:
        progreso = min(ventas_mes / objetivo, 1.0)
        color_barra = "#4CAF50" if progreso >= 0.8 else "#FF9800" if progreso >= 0.5 else "#F44336"
        st.markdown(f"""
        <div style="background-color: #1e1e2e; border-radius: 10px; padding: 3px; border: 1px solid #313244;">
            <div style="background-color: {color_barra}; width: {progreso*100:.1f}%; height: 30px;
                        border-radius: 8px; display: flex; align-items: center; justify-content: center;
                        font-weight: bold; color: white; font-size: 14px;">
                ${ventas_mes:,.0f} / ${objetivo:,.0f} ({porcentaje}%)
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info(f"No hay objetivo definido para {mes_actual_es}. Us├í el bot├│n de abajo para cargarlo.")

    st.divider()

    # ÔöÇÔöÇ Ventas por semana del mes actual ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader(f"Ventas por Semana ÔÇö {mes_actual_es}")
        if not df_mes.empty and "Semana" in df_mes.columns and "Monto USD" in df_mes.columns:
            por_semana = df_mes.groupby("Semana")["Monto USD"].agg(["sum", "count"]).reset_index()
            por_semana.columns = ["Semana", "Monto USD", "Operaciones"]
            por_semana = por_semana.sort_values("Semana")

            fig_sem = px.bar(
                por_semana,
                x="Semana",
                y="Monto USD",
                text_auto="$.3s",
                color_discrete_sequence=[COLORES["primario"]],
            )
            fig_sem.update_layout(
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                showlegend=False,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#333"),
            )
            if objetivo > 0:
                fig_sem.add_hline(
                    y=objetivo / 4, line_dash="dash", line_color="orange",
                    annotation_text="Obj. semanal", annotation_position="top right"
                )
            st.plotly_chart(fig_sem, use_container_width=True)
        else:
            st.info(f"No hay ventas cerradas en {mes_actual_es} todav├¡a.")

    # ÔöÇÔöÇ Comparaci├│n ├║ltimos 6 meses ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    with col_der:
        st.subheader("Comparaci├│n ├Ültimos 6 Meses")
        if not df.empty and "Fecha Cierre" in df.columns and "Monto USD" in df.columns:
            # Crear columna de mes para agrupar
            df["_mes_num"] = df["Fecha Cierre"].str[:7]
            df_por_mes = df.groupby("_mes_num")["Monto USD"].sum().reset_index()
            df_por_mes.columns = ["Mes Num", "Ventas USD"]
            df_por_mes = df_por_mes.sort_values("Mes Num").tail(6)
            df_por_mes["Mes"] = df_por_mes["Mes Num"].apply(formato_mes_es)

            # Agregar objetivos si existen
            if not df_obj.empty:
                obj_dict = dict(zip(df_obj["Mes"], df_obj["Objetivo USD"])) if "Mes" in df_obj.columns else {}
                df_por_mes["Objetivo USD"] = df_por_mes["Mes"].map(obj_dict).fillna(0).astype(float)

            fig_comp = go.Figure()
            fig_comp.add_trace(go.Bar(
                x=df_por_mes["Mes"], y=df_por_mes["Ventas USD"],
                name="Ventas", marker_color=COLORES["activa"], text=df_por_mes["Ventas USD"].apply(lambda x: f"${x:,.0f}"),
                textposition="outside",
            ))

            if not df_obj.empty and "Objetivo USD" in df_por_mes.columns:
                obj_vals = df_por_mes["Objetivo USD"]
                if obj_vals.sum() > 0:
                    fig_comp.add_trace(go.Scatter(
                        x=df_por_mes["Mes"], y=obj_vals,
                        name="Objetivo", mode="lines+markers",
                        line=dict(color="#FF9800", width=3, dash="dash"),
                    ))

            fig_comp.update_layout(
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#333"),
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.info("No hay datos hist├│ricos de ventas cerradas.")

    st.divider()

    # ÔöÇÔöÇ Historial mensual de ventas vs objetivo ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.subheader("­ƒôà Historial Mensual")

    df_historial_prev = cargar_historial_cierres()

    # Armar filas desde historial de cierres confirmados
    filas_hist = []
    if not df_historial_prev.empty:
        for _, row in df_historial_prev.iterrows():
            mes_raw = str(row.get("Mes", ""))
            partes = mes_raw.split(" ")
            mes_corto = f"{partes[0][:3]} {partes[1]}" if len(partes) == 2 else mes_raw
            facturado_val = float(str(row.get("Facturado USD", 0)).replace(",", "").replace("$", "") or 0)
            objetivo_val  = float(str(row.get("Objetivo USD",  0)).replace(",", "").replace("$", "") or 0)
            estado_raw = str(row.get("Estado", ""))
            estado = "Ô£à Cumplido" if "Superado" in estado_raw else "ÔØî No cumplido"
            filas_hist.append({
                "Mes":              mes_corto,
                "Facturado USD":    f"${facturado_val:,.0f}",
                "Objetivo USD":     f"${objetivo_val:,.0f}",
                "Estado Objetivo":  estado,
            })

    # Agregar mes actual (en curso, sin cierre todav├¡a)
    # Solo si no est├í ya en el historial
    meses_cerrados = [f["Mes"] for f in filas_hist]
    mes_actual_corto = f"{MESES_ES[hoy.month][:3]} {hoy.year}"
    if mes_actual_corto not in meses_cerrados:
        estado_actual = "­ƒƒí En curso"
        if objetivo > 0:
            estado_actual = "Ô£à Cumplido" if ventas_mes >= objetivo else "­ƒƒí En curso"
        filas_hist.append({
            "Mes":             mes_actual_corto,
            "Facturado USD":   f"${ventas_mes:,.0f}",
            "Objetivo USD":    f"${objetivo:,.0f}" if objetivo > 0 else "Sin definir",
            "Estado Objetivo": estado_actual,
        })

    df_tabla_hist = pd.DataFrame(filas_hist)

    def color_estado_hist(val):
        if "Cumplido" in str(val) and "No" not in str(val):
            return "background-color: #1a3a1a; color: #4CAF50; font-weight: bold"
        elif "No cumplido" in str(val):
            return "background-color: #3a1a1a; color: #F44336; font-weight: bold"
        elif "En curso" in str(val):
            return "background-color: #2a2a10; color: #FFC107; font-weight: bold"
        return ""

    st.dataframe(
        df_tabla_hist.style.applymap(color_estado_hist, subset=["Estado Objetivo"]),
        use_container_width=True,
        hide_index=True
    )

    # ÔöÇÔöÇ Objetivo mensual: mostrar actual + bot├│n editar ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.divider()

    # Inicializar estado del editor
    if "editando_objetivo" not in st.session_state:
        st.session_state.editando_objetivo = False
    if "objetivo_guardado" not in st.session_state:
        st.session_state.objetivo_guardado = False

    # Mostrar mensaje de ├®xito si se acaba de guardar
    if st.session_state.objetivo_guardado:
        st.success("Objetivo guardado correctamente.")
        st.session_state.objetivo_guardado = False

    col_obj1, col_obj2 = st.columns([4, 1])

    with col_obj1:
        if objetivo > 0:
            st.subheader(f"­ƒÄ» Objetivo {mes_actual_es}: ${objetivo:,.0f} USD ÔÇö {porcentaje}% cumplido")
        else:
            st.subheader(f"­ƒÄ» Objetivo {mes_actual_es}: Sin definir")

    with col_obj2:
        if st.button("Ô£Å´©Å Editar", key="btn_editar_obj"):
            st.session_state.editando_objetivo = not st.session_state.editando_objetivo
            st.rerun()

    # ÔöÇÔöÇ Editor de objetivo (visible al hacer clic en Editar) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    if st.session_state.editando_objetivo:
        st.markdown("---")
        st.markdown("**Configurar Objetivo Mensual**")

        col_form1, col_form2 = st.columns(2)

        with col_form1:
            meses_opciones = []
            for delta in range(0, 3):
                m = hoy.month + delta
                a = hoy.year
                if m > 12:
                    m -= 12
                    a += 1
                meses_opciones.append(f"{MESES_ES[m]} {a}")
            mes_seleccionado = st.selectbox("Mes", meses_opciones, key="sel_mes_obj")

        with col_form2:
            nuevo_objetivo = st.number_input(
                "Objetivo USD",
                min_value=0,
                max_value=10000000,
                value=int(objetivo) if objetivo > 0 else 500000,
                step=10000,
                format="%d",
                key="input_obj_usd"
            )

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
        with col_btn1:
            if st.button("­ƒÆ¥ Guardar", type="primary", key="btn_guardar_obj"):
                usuario_actual = st.session_state.get("name", "Desconocido")
                exito = guardar_objetivo(mes_seleccionado, nuevo_objetivo, usuario_actual)
                if exito:
                    st.session_state.editando_objetivo = False
                    st.session_state.objetivo_guardado = True
                    st.rerun()
                else:
                    st.error("No se pudo guardar. Revis├í la conexi├│n.")
        with col_btn2:
            if st.button("Cancelar", key="btn_cancelar_obj"):
                st.session_state.editando_objetivo = False
                st.rerun()

    # ÔöÇÔöÇ Cierre del Mes ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.divider()
    st.subheader("­ƒöÆ Cierre del Mes")

    # Inicializar estado de confirmaci├│n
    if "confirmar_cierre" not in st.session_state:
        st.session_state.confirmar_cierre = False

    # Historial de cierres anteriores
    df_historial = cargar_historial_cierres()
    if not df_historial.empty:
        st.markdown("**­ƒôï Historial de Cierres**")

        def color_estado(val):
            if "Superado" in str(val):
                return "background-color: #1a3a1a; color: #4CAF50; font-weight: bold"
            elif "No superado" in str(val):
                return "background-color: #3a1a1a; color: #F44336; font-weight: bold"
            return ""

        df_hist_mostrar = df_historial.copy()
        if "Objetivo USD" in df_hist_mostrar.columns:
            df_hist_mostrar["Objetivo USD"] = pd.to_numeric(df_hist_mostrar["Objetivo USD"], errors="coerce")
            df_hist_mostrar["Objetivo USD"] = df_hist_mostrar["Objetivo USD"].apply(lambda x: f"${x:,.0f}")
        if "Facturado USD" in df_hist_mostrar.columns:
            df_hist_mostrar["Facturado USD"] = pd.to_numeric(df_hist_mostrar["Facturado USD"], errors="coerce")
            df_hist_mostrar["Facturado USD"] = df_hist_mostrar["Facturado USD"].apply(lambda x: f"${x:,.0f}")

        st.dataframe(
            df_hist_mostrar.style.applymap(color_estado, subset=["Estado"]),
            use_container_width=True,
            hide_index=True
        )
        st.divider()

    # Bot├│n de cierre del mes
    col_cierre1, col_cierre2 = st.columns([2, 4])
    with col_cierre1:
        if st.button("­ƒöÆ Cerrar Mes", type="primary", key="btn_cierre_mes"):
            # Validaci├│n 1: objetivo definido
            if objetivo <= 0:
                st.error("ÔÜá´©Å No pod├®s cerrar el mes sin un objetivo definido. Carg├í el objetivo primero.")
            else:
                st.session_state.confirmar_cierre = True

    # Panel de confirmaci├│n
    if st.session_state.get("confirmar_cierre", False):
        ultimo_dia = (date(hoy.year, hoy.month % 12 + 1, 1) - pd.Timedelta(days=1)).day if hoy.month < 12 else 31
        dias_restantes = ultimo_dia - hoy.day

        with st.container():
            st.markdown("---")
            if dias_restantes > 0:
                st.warning(f"ÔÜá´©Å **Atenci├│n:** Todav├¡a faltan {dias_restantes} d├¡as para que termine {mes_actual_es}. ┬┐Est├ís seguro que quer├®s cerrar el mes ahora?")

            st.markdown(f"""
            **Resumen del cierre:**
            - ­ƒôà Mes: **{mes_actual_es}**
            - ­ƒÄ» Objetivo: **${objetivo:,.0f} USD**
            - ­ƒÆ░ Facturado: **${ventas_mes:,.0f} USD**
            - ­ƒôè Cumplimiento: **{porcentaje}%**
            - {"Ô£à **Objetivo SUPERADO**" if ventas_mes >= objetivo else "ÔØî **Objetivo NO alcanzado**"}
            """)

            col_conf1, col_conf2 = st.columns([1, 1])
            with col_conf1:
                if st.button("Ô£à Confirmar Cierre", type="primary", key="btn_confirmar_cierre"):
                    usuario_actual = st.session_state.get("name", "Desconocido")
                    exito = guardar_cierre_mes(mes_actual_es, objetivo, ventas_mes, usuario_actual)
                    if exito:
                        st.session_state.confirmar_cierre = False
                        st.success(f"Ô£à Mes {mes_actual_es} cerrado correctamente.")
                        st.rerun()
            with col_conf2:
                if st.button("Cancelar", key="btn_cancelar_cierre"):
                    st.session_state.confirmar_cierre = False
                    st.rerun()


# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ
# APLICACI├ôN PRINCIPAL
# ÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉÔòÉ

def main():
    """
    Funci├│n principal de la aplicaci├│n Streamlit.
    Maneja el login y renderiza las pesta├▒as seg├║n el rol del usuario.
    """

    # ÔöÇÔöÇ Carga de configuraci├│n de autenticaci├│n ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    config = cargar_config()

    # ÔöÇÔöÇ Configuraci├│n del autenticador ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )

    # ÔöÇÔöÇ Pantalla de login ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    # Si el usuario no est├í logueado, muestra el formulario de login
    if not st.session_state.get("authentication_status"):
        col_login1, col_login2, col_login3 = st.columns([1, 2, 1])
        with col_login2:
            st.markdown("## ­ƒôè Farkim ÔÇö Dashboard")
            st.markdown("**Sistema de Business Intelligence**")
            st.markdown("---")

        authenticator.login(location="main")

        status = st.session_state.get("authentication_status")

        if status is False:
            st.error("ÔØî Usuario o contrase├▒a incorrectos.")
        elif status is None:
            st.info("­ƒöÉ Ingres├í tus credenciales para acceder al dashboard.")

        return   # Detenemos la ejecuci├│n hasta que haya login

    # ÔöÇÔöÇ Dashboard (usuario autenticado) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    usuario = st.session_state.get("name", "")
    username = st.session_state.get("username", "")

    # Obtenemos el rol del usuario desde el config
    rol = "viewer"
    if username in config["credentials"]["usernames"]:
        roles = config["credentials"]["usernames"][username].get("roles", [])
        if roles:
            rol = roles[0]

    # ÔöÇÔöÇ Sidebar con info del usuario ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    with st.sidebar:
        st.markdown(f"### ­ƒæñ {usuario}")
        st.markdown(f"**Rol:** `{rol}`")
        st.markdown(f"**{datetime.now().strftime('%d/%m/%Y %H:%M')} hs**")
        st.divider()

        # Bot├│n de logout
        authenticator.logout("Cerrar sesi├│n", location="sidebar")

        st.divider()
        st.markdown("**Farkim Sistemas**")
        st.caption("Dashboard v1.0 ÔÇö 2026")

    # ÔöÇÔöÇ Header del dashboard ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    st.title("­ƒôè Farkim ÔÇö Dashboard Comercial")
    st.caption("Datos en tiempo real desde Odoo CRM ÔåÆ Google Sheets")

    # ÔöÇÔöÇ Pesta├▒as principales ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇ
    if rol in ["gerente", "admin"]:
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "­ƒôè Resumen",
            "­ƒôï Pipeline",
            "­ƒÆ░ Ventas del Mes",
            "­ƒæÑ Por Vendedor",
            "­ƒôê Evoluci├│n",
            "­ƒô£ Hist├│rico",
            "­ƒö┤ Sin Movimiento",
        ])
        with tab1: tab_resumen(rol)
        with tab2: tab_pipeline(rol)
        with tab3: tab_ventas_del_mes(rol)
        with tab4: tab_vendedores(rol)
        with tab5: tab_evolucion(rol)
        with tab6: tab_historico(rol)
        with tab7: tab_sin_movimiento(rol)
    else:
        # Vista limitada para roles sin acceso completo
        tab1, tab2, tab4 = st.tabs(["­ƒôè Resumen", "­ƒôï Pipeline", "­ƒôê Evoluci├│n"])
        with tab1: tab_resumen(rol)
        with tab2: tab_pipeline(rol)
        with tab4: tab_evolucion(rol)


if __name__ == "__main__":
    main()
