# ==============================================
# Nombre:      app.py
# Descripción: Dashboard principal de Farkim.
#              Login con streamlit-authenticator,
#              5 pestañas con datos en tiempo real
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

# ── Nombres de meses en español ─────────────────────────────────────────────
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

# ── Configuración de la página ────────────────────────────────────────────────
st.set_page_config(
    page_title="Farkim — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Estilos personalizados ────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Ocultar menú y footer de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Tarjetas de métricas más grandes */
    [data-testid="metric-container"] {
        background-color: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 10px;
        padding: 15px;
    }

    /* Color del valor principal de métricas */
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700;
    }

    /* Separador de pestañas */
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


# ── Carga del archivo de configuración de usuarios ───────────────────────────
@st.cache_resource
def cargar_config():
    """
    Carga la configuración de autenticación.
    En Streamlit Cloud: lee de st.secrets["auth"]
    En local: lee del archivo config.yaml
    """
    # ── Intento 1: Streamlit Cloud (st.secrets) ─────────────────
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

    # ── Intento 2: archivo local config.yaml ────────────────────
    try:
        with open("config.yaml") as f:
            config = yaml.load(f, Loader=SafeLoader)
        return config
    except FileNotFoundError:
        st.error("❌ Archivo config.yaml no encontrado. Ejecutá crear_config_auth.py primero.")
        st.stop()


# ── Funciones de carga de datos desde Google Sheets ──────────────────────────
@st.cache_data(ttl=300)   # 300 segundos = 5 minutos de caché
def cargar_pipeline():
    """
    Carga la hoja 'Pipeline Completo' desde Google Sheets.
    ttl=300 significa que se actualiza automáticamente cada 5 minutos.

    Excluye automáticamente las oportunidades GANADAS:
    - Odoo asigna Probabilidad 100% cuando se marca como Ganada
    - O la etapa contiene "GANAD" (ej: "Ganada", "GANADO")
    Estas ya son ventas cerradas — no corresponde trackearlas en el pipeline.
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
        # Condición 1: Probabilidad 100% → Odoo la marca así cuando está ganada
        # Condición 2: Nombre de etapa contiene "GANAD" por si acaso
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


# =============================================================================
# ODOO — Ventas Cerradas (activo — usado en pestana Por Vendedor)
# =============================================================================
@st.cache_data(ttl=300)
def cargar_ventas_cerradas():
    """Carga la hoja 'Ventas Cerradas' desde Google Sheets (Odoo)."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja
        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Ventas Cerradas")
        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        return pd.DataFrame()
# =============================================================================


# =============================================================================
# ALTO CERRO — CARGA SEMANAL MANUAL (ACTIVO)
# =============================================================================

@st.cache_data(ttl=120)
def cargar_ac_ventas_detalle():
    """Carga 'AC Ventas Detalle' — fuente principal de ventas (Alto Cerro)."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja
        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "AC Ventas Detalle")
        if hoja is None:
            return pd.DataFrame()
        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def cargar_ac_ventas_mensual():
    """Carga 'AC Ventas Mensual' — resumen mensual calculado desde Alto Cerro."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja
        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "AC Ventas Mensual")
        if hoja is None:
            return pd.DataFrame()
        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=120)
def cargar_ac_resumen():
    """Carga 'AC Resumen Mensual' — tabla por categoria extraida de Hoja1 del Excel."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja
        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        if spreadsheet is None:
            return pd.DataFrame()
        hoja = obtener_hoja(spreadsheet, "AC Resumen Mensual")
        if hoja is None:
            return pd.DataFrame()
        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception:
        return pd.DataFrame()

# =============================================================================
# FIN BLOQUE ALTO CERRO
# =============================================================================
@st.cache_data(ttl=60)
def cargar_objetivos():
    """Carga la hoja 'Objetivos Mensuales' desde Google Sheets. TTL corto porque se edita."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja
        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        if spreadsheet is None:
            return pd.DataFrame()
        hoja = obtener_hoja(spreadsheet, "Objetivos Mensuales")
        if hoja is None:
            return pd.DataFrame()
        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def cargar_historial_cierres():
    """Carga la hoja 'Historial Cierres' desde Google Sheets."""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja
        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        if spreadsheet is None:
            return pd.DataFrame()
        hoja = obtener_hoja(spreadsheet, "Historial Cierres")
        if hoja is None:
            return pd.DataFrame()
        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception:
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
                fila_idx = i + 2  # +1 por encabezado, +1 por índice 1-based
                estado = "✅ Superado" if facturado >= objetivo else "❌ No superado"
                hoja.update(f"A{fila_idx}:F{fila_idx}", [[
                    mes_es, objetivo, round(facturado, 2), estado,
                    datetime.now().strftime("%Y-%m-%d %H:%M"), usuario
                ]])
                cargar_historial_cierres.clear()
                return True

        # Si no existe, agregar nueva fila
        estado = "✅ Superado" if facturado >= objetivo else "❌ No superado"
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

        # Limpiar caché para que se vea el cambio
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
        if spreadsheet is None:
            return pd.DataFrame()
        hoja = obtener_hoja(spreadsheet, "Historico Mensual USD")
        if hoja is None:
            return pd.DataFrame()
        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except Exception:
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


# ── Paleta de colores de Farkim ───────────────────────────────────────────────
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


# ══════════════════════════════════════════════════════════════════════════════
# TABS DEL DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def tab_resumen(rol):
    """
    Pestaña de resumen ejecutivo.
    Muestra los KPIs principales del pipeline en tarjetas grandes.
    """
    st.header("📊 Resumen Ejecutivo")
    st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')} hs  •  Se refresca cada 5 minutos")

    df = cargar_pipeline()
    if df.empty:
        st.warning("No se pudieron cargar los datos del pipeline.")
        return

    # ── KPIs principales ──────────────────────────────────────────────────
    st.subheader("📋 Oportunidades en Pipeline")
    col1, col2, col3, col4 = st.columns(4)

    total_opps = len(df)
    total_usd  = df["Monto USD"].sum() if "Monto USD" in df.columns else 0

    activas    = len(df[df["Estado"] == "Activa"])    if "Estado" in df.columns else 0
    en_riesgo  = len(df[df["Estado"] == "En riesgo"]) if "Estado" in df.columns else 0
    inactivas  = len(df[df["Estado"] == "Inactiva"])  if "Estado" in df.columns else 0

    monto_activas   = df.loc[df["Estado"] == "Activa",    "Monto USD"].sum() if "Estado" in df.columns else 0
    monto_en_riesgo = df.loc[df["Estado"] == "En riesgo", "Monto USD"].sum() if "Estado" in df.columns else 0

    with col1:
        st.metric("💰 Pipeline Total", f"${total_usd:,.0f} USD", f"{total_opps} oportunidades")
    with col2:
        st.metric("✅ Activas", f"{activas}", f"${monto_activas:,.0f} USD")
    with col3:
        st.metric("⚠️ En Riesgo", f"{en_riesgo}", f"${monto_en_riesgo:,.0f} USD")
    with col4:
        porc_inactivas = round((inactivas / total_opps * 100), 1) if total_opps > 0 else 0
        st.metric("🔴 Inactivas", f"{inactivas}", f"{porc_inactivas}% del total")

    st.divider()

    # ── Gráficos fila 1 ───────────────────────────────────────────────────
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("Distribución del Pipeline")
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
            fig_pie.update_traces(
                textposition="inside",
                textinfo="percent+label",
                textfont=dict(color="black", size=13),
            )
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
            for trace in fig_bar.data:
                color_texto = "white" if trace.name == "Inactiva" else "black"
                trace.update(textfont=dict(color=color_texto, size=13))
            st.plotly_chart(fig_bar, use_container_width=True)

    # ── Top 20 oportunidades activas ──────────────────────────────────────
    st.subheader("🏆 Top 20 Oportunidades Activas por Monto")
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
    Pestaña con el pipeline completo filtrable.
    Permite filtrar por estado, vendedor y rango de monto.
    """
    st.header("📋 Pipeline Completo")

    df = cargar_pipeline()
    if df.empty:
        st.warning("No se pudieron cargar los datos del pipeline.")
        return

    # ── Filtros horizontales dentro de la pestaña ────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        estados_disp = ["Todos"] + sorted(df["Estado"].unique().tolist()) if "Estado" in df.columns else ["Todos"]
        estado_sel = st.selectbox("🔍 Estado", estados_disp, key="filtro_estado_pipeline")

    with col_f2:
        if "Vendedor" in df.columns:
            vendedores_disp = ["Todos"] + sorted(df["Vendedor"].unique().tolist())
            vendedor_sel = st.selectbox("👤 Vendedor", vendedores_disp, key="filtro_vendedor_pipeline")
        else:
            vendedor_sel = "Todos"

    with col_f3:
        if "Monto USD" in df.columns and len(df) > 0:
            monto_min = float(df["Monto USD"].min())
            monto_max = float(df["Monto USD"].max())
            monto_rango = st.slider(
                "💰 Rango de Monto USD",
                min_value=monto_min,
                max_value=monto_max,
                value=(monto_min, monto_max),
                format="$%.0f",
                key="filtro_monto_pipeline"
            )
        else:
            monto_rango = (0, 99999999)

    st.divider()

    # ── Aplicar filtros ───────────────────────────────────────────────────
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

    # ── Métricas del filtro ───────────────────────────────────────────────
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

    # ── Tabla filtrable ───────────────────────────────────────────────────
    columnas_mostrar = [c for c in ["Oportunidad", "Cliente", "Vendedor", "Etapa", "Estado",
                                     "Monto USD", "Probabilidad %", "Días Sin Actividad",
                                     "Fecha Creación", "Última Actividad"] if c in df_filtrado.columns]

    df_mostrar = df_filtrado[columnas_mostrar].sort_values("Monto USD", ascending=False).reset_index(drop=True)
    df_mostrar.index += 1

    # Formatear monto para visualización
    if "Monto USD" in df_mostrar.columns:
        df_mostrar["Monto USD"] = df_mostrar["Monto USD"].apply(lambda x: f"${x:,.0f}")

    st.dataframe(df_mostrar, use_container_width=True, height=500)
    st.caption(f"Mostrando {len(df_filtrado)} de {len(df)} oportunidades")


def tab_vendedores(rol):
    """
    Pestaña de análisis por vendedor.
    Muestra ranking mensual de facturación (ventas cerradas del mes actual).
    Solo visible para rol 'gerente' o 'admin'.
    """
    # Control de acceso por rol
    if rol not in ["gerente", "admin"]:
        st.warning("🔒 Esta sección es solo para gerentes y administradores.")
        return

    hoy = date.today()
    mes_actual_es = f"{MESES_ES[hoy.month]} {hoy.year}"

    st.header(f"👥 Ranking de Vendedores — {mes_actual_es}")
    st.caption("📡 Fuente: Odoo CRM — Oportunidades marcadas como Ganadas en el mes actual")

    # Cargar ventas cerradas desde Odoo (hoja Ventas Cerradas)
    df_ventas = cargar_ventas_cerradas()

    if df_ventas.empty or "Vendedor" not in df_ventas.columns:
        st.warning("No se pudieron cargar las ventas cerradas.")
        return

    # ── Filtrar solo el mes actual ───────────────────────────────────────
    if "Mes Cierre" in df_ventas.columns:
        df_mes = df_ventas[df_ventas["Mes Cierre"] == mes_actual_es].copy()
    else:
        df_mes = df_ventas.copy()

    # Asegurar que Monto USD sea numérico
    if "Monto USD" in df_mes.columns:
        df_mes["Monto USD"] = pd.to_numeric(df_mes["Monto USD"], errors="coerce").fillna(0)

    # ── Resumen por vendedor ─────────────────────────────────────────────
    if df_mes.empty:
        st.info(f"No hay ventas cerradas en {mes_actual_es} todavía.")
        return

    df_ranking = df_mes.groupby("Vendedor").agg(
        Facturado=("Monto USD", "sum"),
        Operaciones=("Monto USD", "count"),
        Ticket_Promedio=("Monto USD", "mean")
    ).reset_index().sort_values("Facturado", ascending=False)

    total_facturado = df_ranking["Facturado"].sum()
    total_ops = int(df_ranking["Operaciones"].sum())

    # ── Métricas generales ───────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Total Oportunidades Ganadas", f"${total_facturado:,.0f} USD")
    with col2:
        st.metric("🏆 Cierres Registrados en Odoo", total_ops)
    with col3:
        st.metric("👥 Vendedores con Cierres", len(df_ranking))

    st.divider()

    # ── Gráficos ─────────────────────────────────────────────────────────
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader(f"🏆 Oportunidades Ganadas — {mes_actual_es}")
        df_chart = df_ranking.sort_values("Facturado", ascending=True)

        fig_rank = px.bar(
            df_chart,
            x="Facturado",
            y="Vendedor",
            orientation="h",
            text=df_chart["Facturado"].apply(lambda x: f"${x:,.0f}"),
            color_discrete_sequence=[COLORES["activa"]],
        )
        fig_rank.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            showlegend=False,
            yaxis=dict(showgrid=False),
            xaxis=dict(showgrid=True, gridcolor="#333", title="USD — Oportunidades Ganadas (Odoo)"),
        )
        st.plotly_chart(fig_rank, use_container_width=True)

    with col_der:
        st.subheader("📊 Participación en Cierres")
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

    # ── Tabla detalle por vendedor ────────────────────────────────────────
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

    # ── Detalle de operaciones del mes ────────────────────────────────────
    st.subheader(f"📋 Operaciones Cerradas — {mes_actual_es}")
    cols_detalle = [c for c in ["Oportunidad", "Cliente", "Vendedor", "Monto USD", "Fecha Cierre"] if c in df_mes.columns]
    df_detalle = df_mes[cols_detalle].sort_values("Monto USD", ascending=False).reset_index(drop=True)
    df_detalle.index += 1
    if "Monto USD" in df_detalle.columns:
        df_detalle["Monto USD"] = df_detalle["Monto USD"].apply(lambda x: f"${x:,.0f}")
    st.dataframe(df_detalle, use_container_width=True)


def tab_evolucion(rol):
    """
    Pestaña de evolución temporal de ventas.
    Muestra la tendencia por mes con monto acumulado.
    """
    st.header("📈 Evolución de Ventas en el Tiempo")

    df = cargar_ventas_mes()
    if df.empty:
        st.warning("No se pudieron cargar los datos temporales.")
        return

    # Aseguramos orden cronológico y convertimos a español
    if "Mes" in df.columns:
        df = df.sort_values("Mes")
        df["Mes Display"] = df["Mes"].apply(formato_mes_es)

    # ── Métricas clave de evolución ───────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    if "Monto Total USD" in df.columns:
        mes_top = df.loc[df["Monto Total USD"].idxmax()]
        with col1:
            st.metric("📅 Mejor Mes", formato_mes_es(mes_top["Mes"]), f"${mes_top['Monto Total USD']:,.0f} USD")

    if "Monto Acumulado USD" in df.columns and len(df) > 0:
        acumulado = df["Monto Acumulado USD"].iloc[-1]
        with col2:
            st.metric("💰 Pipeline Acumulado", f"${acumulado:,.0f} USD")

    if "Oportunidades Creadas" in df.columns:
        total_opps_hist = df["Oportunidades Creadas"].sum()
        with col3:
            st.metric("📊 Oportunidades Históricas", f"{total_opps_hist}")

    st.divider()

    # ── Gráfico de líneas: monto por mes ──────────────────────────────────
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

    # ── Tabla de meses ────────────────────────────────────────────────────
    st.subheader("Detalle por Mes")
    df_tabla = df.copy()

    for col in ["Monto Total USD", "Ticket Promedio USD", "Monto Acumulado USD"]:
        if col in df_tabla.columns:
            df_tabla[col] = df_tabla[col].apply(lambda x: f"${x:,.0f}")

    # Reemplazar columna Mes con la versión en español
    if "Mes Display" in df_tabla.columns:
        df_tabla["Mes"] = df_tabla["Mes Display"]
        df_tabla = df_tabla.drop(columns=["Mes Display"])
    df_tabla = df_tabla.sort_values("Mes", ascending=False).reset_index(drop=True)
    df_tabla.index += 1
    st.dataframe(df_tabla, use_container_width=True)


def tab_historico(rol):
    """
    Pestaña de facturación histórica.
    Hasta 2025: datos del Excel histórico (Historico Mensual/Anual USD).
    Desde 2026: datos de AC Resumen Mensual (Hoja1 del Excel semanal).
    Muestra los últimos 10 años en el gráfico anual.
    """
    st.header("📜 Facturación Histórica")
    st.caption("Hasta 2025: Excel histórico  •  2026 en adelante: Excel semanal de Alto Cerro")

    df_mensual_hist = cargar_historico_mensual()
    df_anual_hist   = cargar_historico_anual()
    df_resumen      = cargar_ac_resumen()

    meses_inv = {v: k for k, v in MESES_ES.items()}

    # ── Tabla mensual combinada ──────────────────────────────────────────
    # Periodo se calcula desde "Mes" (ej: "Enero 2020" → 202001) para evitar
    # depender del formato del campo Periodo del sheet (viene como "2020-01", no número).
    def _periodo_desde_mes(mes_str):
        partes = str(mes_str).strip().title().split(" ")
        if len(partes) == 2:
            try:
                return int(partes[1]) * 100 + meses_inv.get(partes[0], 0)
            except ValueError:
                pass
        return 0

    # Parte 1: histórico ≤ 2025 (excluir 2026 del sheet, tiene datos incorrectos)
    filas_mens = []
    if not df_mensual_hist.empty:
        df_h = df_mensual_hist.copy()
        df_h["Facturacion USD"] = pd.to_numeric(df_h.get("Facturacion USD", 0), errors="coerce").fillna(0)
        df_h["_periodo"] = df_h["Mes"].apply(_periodo_desde_mes)
        df_h = df_h[(df_h["_periodo"] > 0) & (df_h["_periodo"] < 202600)]
        for _, row in df_h.iterrows():
            filas_mens.append({
                "Mes":            str(row.get("Mes", "")),
                "Periodo":        int(row["_periodo"]),
                "Facturacion USD": float(row["Facturacion USD"]),
            })

    # Parte 2: AC Resumen Mensual ≥ 2026
    if not df_resumen.empty and "Mes" in df_resumen.columns:
        df_res = df_resumen.copy()
        df_res["Ventas USD"] = pd.to_numeric(df_res.get("Ventas USD", 0), errors="coerce").fillna(0)
        for _, row in df_res[df_res["Categoria"] == "TOTALES"].iterrows():
            mes_str = str(row.get("Mes", "")).strip().title()
            partes  = mes_str.split(" ")
            if len(partes) == 2:
                try:
                    anio    = int(partes[1])
                    mes_num = meses_inv.get(partes[0], 0)
                    if anio >= 2026 and mes_num > 0:
                        filas_mens.append({
                            "Mes":            mes_str,
                            "Periodo":        anio * 100 + mes_num,
                            "Facturacion USD": float(row["Ventas USD"]),
                        })
                except ValueError:
                    pass

    df_mensual_combined = (
        pd.DataFrame(filas_mens)
        .drop_duplicates(subset=["Periodo"])
        .sort_values("Periodo")
        .reset_index(drop=True)
    )

    # ── Tabla anual combinada ────────────────────────────────────────────
    # Parte 1: histórico ≤ 2025
    filas_anual = []
    if not df_anual_hist.empty:
        df_a = df_anual_hist.copy()
        df_a["Facturacion USD"]    = pd.to_numeric(df_a.get("Facturacion USD",    0), errors="coerce").fillna(0)
        df_a["Operaciones"]        = pd.to_numeric(df_a.get("Operaciones",        0), errors="coerce").fillna(0)
        df_a["Ticket Promedio USD"] = pd.to_numeric(df_a.get("Ticket Promedio USD", 0), errors="coerce").fillna(0)
        df_a["Anio"]               = pd.to_numeric(df_a.get("Anio", 0), errors="coerce").fillna(0)
        df_a = df_a[df_a["Anio"] <= 2025]
        for _, row in df_a.iterrows():
            filas_anual.append({
                "Anio":              int(row["Anio"]),
                "Facturacion USD":   float(row["Facturacion USD"]),
                "Operaciones":       int(row["Operaciones"]),
                "Ticket Promedio USD": float(row["Ticket Promedio USD"]),
            })

    # Parte 2: ≥ 2026 — se suma desde df_mensual_combined (ya construido y correcto)
    # Más robusto que depender de df_resumen nuevamente.
    if not df_mensual_combined.empty:
        df_2026plus = df_mensual_combined[df_mensual_combined["Periodo"] >= 202600].copy()
        df_2026plus["_anio"] = df_2026plus["Periodo"] // 100
        por_anio = df_2026plus.groupby("_anio")["Facturacion USD"].sum().reset_index()
        for _, row in por_anio.iterrows():
            anio = int(row["_anio"])
            if anio > 0 and not any(f["Anio"] == anio for f in filas_anual):
                filas_anual.append({
                    "Anio":              anio,
                    "Facturacion USD":   float(row["Facturacion USD"]),
                    "Operaciones":       0,
                    "Ticket Promedio USD": 0,
                })

    df_anual_combined = (
        pd.DataFrame(filas_anual)
        .drop_duplicates(subset=["Anio"])
        .sort_values("Anio")
        .reset_index(drop=True)
    )
    # Últimos 10 años
    df_anual_combined = df_anual_combined.tail(10).copy()

    if df_mensual_combined.empty:
        st.warning("No se pudieron cargar los datos históricos.")
        return

    # ── KPIs principales ────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    total_usd      = df_anual_combined["Facturacion USD"].sum()
    total_ops      = df_anual_combined["Operaciones"].sum()
    n_anios        = len(df_anual_combined)
    promedio_anual = total_usd / n_anios if n_anios > 0 else 0

    with col1:
        st.metric("💰 Facturación Total", f"${total_usd:,.0f} USD", f"{n_anios} años")
    with col2:
        st.metric("📊 Operaciones", f"{total_ops:,.0f}", f"{n_anios} años")
    with col3:
        st.metric("📅 Promedio Anual", f"${promedio_anual:,.0f} USD")
    with col4:
        if not df_anual_combined.empty:
            mejor = df_anual_combined.loc[df_anual_combined["Facturacion USD"].idxmax()]
            st.metric("🏆 Mejor Año", f"{int(mejor['Anio'])}", f"${mejor['Facturacion USD']:,.0f} USD")

    st.divider()

    # ── Gráfico barras: facturación anual (últimos 10 años) ──────────────
    st.subheader("Facturación Anual en USD — Últimos 10 años")

    if not df_anual_combined.empty:
        anio_actual = str(date.today().year)
        df_ap = df_anual_combined.copy()
        df_ap["Anio"] = df_ap["Anio"].astype(str)
        colores_anual = [COLORES["primario"] if a != anio_actual else "#FF9800" for a in df_ap["Anio"]]

        fig_anual = go.Figure()
        fig_anual.add_trace(go.Bar(
            x=df_ap["Anio"],
            y=df_ap["Facturacion USD"],
            marker_color=colores_anual,
            text=[f"${v:,.0f}" for v in df_ap["Facturacion USD"]],
            textposition="outside",
            textfont=dict(color="white", size=12),
        ))
        annotations = []
        if anio_actual in df_ap["Anio"].values:
            val_actual = df_ap[df_ap["Anio"] == anio_actual]["Facturacion USD"].values[0]
            annotations = [dict(
                x=anio_actual, y=val_actual,
                text="En curso", showarrow=True, arrowhead=2,
                font=dict(color="#FF9800"), ax=0, ay=-40,
            )]
        fig_anual.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            xaxis=dict(showgrid=False, title="Año"),
            yaxis=dict(showgrid=True, gridcolor="#333", title="USD"),
            showlegend=False,
            annotations=annotations,
        )
        st.plotly_chart(fig_anual, use_container_width=True)

    st.divider()

    # ── Gráfico líneas: evolución mensual ───────────────────────────────
    st.subheader("Evolución Mensual en USD")

    if not df_mensual_combined.empty:
        df_plot = df_mensual_combined.copy()
        df_plot["Facturacion USD"] = pd.to_numeric(df_plot["Facturacion USD"], errors="coerce").fillna(0)

        fig_mensual = go.Figure()
        fig_mensual.add_trace(go.Bar(
            x=df_plot["Mes"],
            y=df_plot["Facturacion USD"],
            name="Facturación Mensual",
            marker_color=COLORES["primario"],
            opacity=0.6,
        ))
        if len(df_plot) > 6:
            df_plot["media_movil"] = df_plot["Facturacion USD"].rolling(window=6, min_periods=1).mean()
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

    # ── Tabla resumen anual ─────────────────────────────────────────────
    st.subheader("Resumen por Año")

    if not df_anual_combined.empty:
        df_tabla = df_anual_combined.copy()
        df_tabla = df_tabla.rename(columns={
            "Anio":              "Año",
            "Facturacion USD":   "Facturación USD",
            "Ticket Promedio USD": "Ticket Prom. USD",
        })
        for col in ["Facturación USD", "Ticket Prom. USD"]:
            if col in df_tabla.columns:
                df_tabla[col] = df_tabla[col].apply(lambda x: f"${x:,.0f}" if x > 0 else "—")
        if "Operaciones" in df_tabla.columns:
            df_tabla["Operaciones"] = df_tabla["Operaciones"].apply(lambda x: x if x > 0 else "—")
        df_tabla = df_tabla.sort_values("Año", ascending=False).reset_index(drop=True)
        df_tabla.index += 1
        st.dataframe(df_tabla, use_container_width=True)


def tab_sin_movimiento(rol):
    """
    Pestaña de oportunidades sin movimiento (+60 días).
    Solo visible para rol 'gerente' o 'admin'.
    Ordenadas por urgencia.
    """
    st.header("🔴 Oportunidades Sin Movimiento")

    if rol not in ["gerente", "admin"]:
        st.warning("🔒 Esta sección es solo para gerentes y administradores.")
        return

    df = cargar_sin_movimiento()
    if df.empty:
        st.warning("No se pudieron cargar los datos de oportunidades inactivas.")
        return

    # ── Métricas de urgencia ──────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    total = len(df)
    criticas = len(df[df["Urgencia"].str.startswith("CRITICA")]) if "Urgencia" in df.columns else 0
    altas    = len(df[df["Urgencia"].str.startswith("ALTA")])    if "Urgencia" in df.columns else 0
    medias   = len(df[df["Urgencia"].str.startswith("MEDIA")])   if "Urgencia" in df.columns else 0
    monto_riesgo = df["Monto USD"].sum() if "Monto USD" in df.columns else 0

    with col1:
        st.metric("Total inactivas", total, f"${monto_riesgo:,.0f} USD en riesgo")
    with col2:
        st.metric("🔴 CRÍTICAS (+6 meses)", criticas, delta_color="inverse")
    with col3:
        st.metric("🟠 ALTAS (+3 meses)", altas, delta_color="inverse")
    with col4:
        st.metric("🟡 MEDIAS (+2 meses)", medias, delta_color="inverse")

    st.divider()

    # ── Gráfico por vendedor ──────────────────────────────────────────────
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
        st.subheader("Distribución por Urgencia")
        if "Urgencia" in df.columns:
            por_urgencia = df["Urgencia"].value_counts().reset_index()
            por_urgencia.columns = ["Urgencia", "Cantidad"]

            colores_urg = {
                "CRITICA — +6 meses sin contacto": "#F44336",
                "ALTA — +3 meses sin contacto":    "#FF9800",
                "MEDIA — +2 meses sin contacto":   "#FFEB3B",
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

    # ── Tabla de inactivas con filtro de urgencia ─────────────────────────
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
    Pestaña de ventas del mes — fuente: Alto Cerro (Excel semanal).
    Estructura:
      0. Alerta semanal
      1. Uploader Excel
      2. KPIs + tabla por categoria
      3. Graficos: semana actual | ultimos 6 meses
      4. Historial mensual
      5. Edicion de objetivo
      6. Cierre del mes
    """
    import calendar as _cal

    st.header("💰 Ventas del Mes")

    if rol not in ["gerente", "admin"]:
        st.warning("🔒 Esta sección es solo para gerentes y administradores.")
        return

    hoy = date.today()
    mes_actual_es = f"{MESES_ES[hoy.month]} {hoy.year}"

    # ════════════════════════════════════════════════════════════════════
    # CARGA DE DATOS
    # ════════════════════════════════════════════════════════════════════
    df_detalle  = cargar_ac_ventas_detalle()
    df_mensual  = cargar_ac_ventas_mensual()
    df_resumen  = cargar_ac_resumen()
    df_obj      = cargar_objetivos()

    # ════════════════════════════════════════════════════════════════════
    # ALERTA SEMANAL — mostrar ANTES del uploader
    # ════════════════════════════════════════════════════════════════════
    if not df_detalle.empty and "Cargado el" in df_detalle.columns:
        try:
            ultima_carga = pd.to_datetime(df_detalle["Cargado el"], errors="coerce").max()
            if pd.notna(ultima_carga):
                dias_sin_carga = (datetime.now() - ultima_carga).days
                if dias_sin_carga >= 7:
                    st.warning(
                        f"⚠️ **Atención:** Hace **{dias_sin_carga} días** que no se carga el Excel semanal. "
                        f"Última carga: {ultima_carga.strftime('%d/%m/%Y')}. Recordá cargarlo todos los viernes."
                    )
        except Exception:
            pass
    elif df_detalle.empty:
        st.warning("⚠️ No hay datos cargados todavía. Cargá el Excel semanal usando el botón de abajo.")

    # ════════════════════════════════════════════════════════════════════
    # SECCIÓN 1 — UPLOADER
    # ════════════════════════════════════════════════════════════════════
    with st.expander("📂 Cargar Excel semanal de Alto Cerro", expanded=False):
        st.caption("Cargá el archivo todos los viernes. Formatos aceptados: .xls · .xlsx · .csv")

        # Estado persistente del uploader
        if "upload_estado" not in st.session_state:
            st.session_state.upload_estado = None  # None | "listo" | "exito" | "error"
        if "upload_resultado" not in st.session_state:
            st.session_state.upload_resultado = None

        # Mostrar resultado de carga anterior (persiste entre reruns)
        if st.session_state.upload_estado == "exito":
            r = st.session_state.upload_resultado
            st.success(
                f"✅ Última carga exitosa: {r['filas']} registros "
                f"({r['fecha_min']} al {r['fecha_max']}) "
                f"— Total: ${r['total_usd']:,.0f} USD"
            )
        elif st.session_state.upload_estado == "error":
            st.error(f"⚠️ Error en última carga: {st.session_state.upload_resultado}")

        archivo = st.file_uploader(
            "Seleccioná el archivo semanal exportado desde Alto Cerro",
            type=["xls", "xlsx", "csv"],
            key="upload_ac_excel",
        )

        if archivo is not None:
            # Paso 1: Mostrar preview del archivo seleccionado
            st.info(f"📄 Archivo seleccionado: **{archivo.name}** ({archivo.size / 1024:.0f} KB)")

            # Paso 2: Botón para confirmar la carga
            if st.button("📤 Procesar y cargar datos", type="primary", key="btn_procesar_excel"):
                with st.status("Procesando Excel...", expanded=True) as status:
                    try:
                        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
                        from carga_semanal_ac import leer_archivo, procesar_y_guardar

                        # Paso 2a: Leer archivo
                        st.write("📖 Leyendo archivo...")
                        contenido = archivo.read()
                        df_raw = leer_archivo(contenido, archivo.name)
                        if df_raw is None:
                            status.update(label="❌ Error al leer el archivo", state="error")
                            st.session_state.upload_estado = "error"
                            st.session_state.upload_resultado = "No se pudo leer. Verificá el formato."
                            st.stop()

                        st.write(f"✅ Archivo leído: {len(df_raw)} filas encontradas")

                        # Paso 2b: Procesar y guardar en Google Sheets
                        st.write("☁️ Enviando datos a Google Sheets...")
                        usuario_actual = st.session_state.get("name", "sistemas")
                        resultado = procesar_y_guardar(
                            df_raw,
                            cargado_por=usuario_actual,
                            archivo_bytes=contenido,
                            nombre_archivo=archivo.name,
                        )

                        if resultado["exito"]:
                            st.write(
                                f"✅ **{resultado['filas']} registros** guardados "
                                f"({resultado['fecha_min']} al {resultado['fecha_max']})"
                            )
                            st.write(f"💰 Total: **${resultado['total_usd']:,.0f} USD**")
                            st.write(f"📅 Meses: {', '.join(resultado['meses'])}")

                            # Guardar estado y limpiar caché
                            st.session_state.upload_estado = "exito"
                            st.session_state.upload_resultado = resultado
                            st.cache_data.clear()

                            status.update(label="✅ Carga completada", state="complete")

                            st.write("🔄 Refrescando dashboard en 3 segundos...")
                            import time
                            time.sleep(3)
                            st.rerun()
                        else:
                            status.update(label="❌ Error en el procesamiento", state="error")
                            st.session_state.upload_estado = "error"
                            st.session_state.upload_resultado = resultado["error"]
                            st.error(f"⚠️ {resultado['error']}")

                    except Exception as e:
                        status.update(label="❌ Error crítico", state="error")
                        st.session_state.upload_estado = "error"
                        st.session_state.upload_resultado = str(e)
                        st.error(f"Error crítico: {str(e)}")

    # ════════════════════════════════════════════════════════════════════
    # EXTRAER VALORES DESDE EL RESUMEN (Hoja1 del Excel → AC Resumen Mensual)
    # Fuente de verdad para ventas totales y objetivo por categoria.
    # ════════════════════════════════════════════════════════════════════
    ventas_mes      = 0.0
    objetivo_excel  = 0.0
    df_cats_mes     = pd.DataFrame()

    try:
        if not df_resumen.empty and "Mes" in df_resumen.columns:
            df_resumen["Ventas USD"]   = pd.to_numeric(df_resumen.get("Ventas USD",   0), errors="coerce").fillna(0)
            df_resumen["Objetivo USD"] = pd.to_numeric(df_resumen.get("Objetivo USD", 0), errors="coerce").fillna(0)
            df_res_mes = df_resumen[df_resumen["Mes"] == mes_actual_es]
            if not df_res_mes.empty:
                fila_total = df_res_mes[df_res_mes["Categoria"] == "TOTALES"]
                if not fila_total.empty:
                    ventas_mes     = float(fila_total.iloc[0]["Ventas USD"])
                    objetivo_excel = float(fila_total.iloc[0]["Objetivo USD"])
                df_cats_mes = df_res_mes[df_res_mes["Categoria"] != "TOTALES"].copy()
    except Exception:
        pass

    # Objetivo editable del dashboard (sobreescribe al del Excel si está definido)
    objetivo = objetivo_excel
    try:
        if not df_obj.empty and "Mes" in df_obj.columns and "Objetivo USD" in df_obj.columns:
            fila_obj = df_obj[df_obj["Mes"] == mes_actual_es]
            if not fila_obj.empty:
                val = pd.to_numeric(fila_obj.iloc[0]["Objetivo USD"], errors="coerce")
                if pd.notna(val) and val > 0:
                    objetivo = float(val)
    except Exception:
        pass

    # Registros y ticket promedio desde detalle (para el subtitulo de KPI)
    registros       = 0
    ticket_promedio = 0.0
    try:
        if not df_detalle.empty and "Fecha" in df_detalle.columns:
            df_detalle["Fecha"]     = pd.to_datetime(df_detalle["Fecha"], errors="coerce")
            df_detalle["Monto USD"] = pd.to_numeric(df_detalle["Monto USD"], errors="coerce").fillna(0)
            df_mes_det = df_detalle[
                (df_detalle["Fecha"].dt.year  == hoy.year) &
                (df_detalle["Fecha"].dt.month == hoy.month)
            ]
            registros = len(df_mes_det)
            if registros > 0 and ventas_mes > 0:
                ticket_promedio = round(ventas_mes / registros, 0)
    except Exception:
        pass

    porcentaje = round((ventas_mes / objetivo * 100), 1) if objetivo > 0 else 0.0

    # ════════════════════════════════════════════════════════════════════
    # SECCIÓN 2 — KPIs + tabla por categoría
    # ════════════════════════════════════════════════════════════════════

    # Estado para edición inline del objetivo
    if "editando_objetivo" not in st.session_state:
        st.session_state.editando_objetivo = False
    if "objetivo_guardado" not in st.session_state:
        st.session_state.objetivo_guardado = False

    if st.session_state.objetivo_guardado:
        st.success("✅ Objetivo guardado correctamente.")
        st.session_state.objetivo_guardado = False

    col1, col2, col3, col4 = st.columns(4)

    if objetivo > 0:
        delta_ventas = f"${ventas_mes:,.0f} de ${objetivo:,.0f} ({porcentaje}%)"
    elif registros > 0:
        delta_ventas = f"{registros} registros cargados"
    else:
        delta_ventas = "Sin datos"
    estado_kpi   = "En camino" if porcentaje >= 70 else "Atención"
    color_kpi    = "normal"    if porcentaje >= 80 else "inverse"

    with col1:
        st.metric("💰 Ventas del Mes", f"${ventas_mes:,.0f} USD", delta_ventas)
    with col2:
        if not st.session_state.editando_objetivo:
            st.metric("🎯 Objetivo", f"${objetivo:,.0f} USD", mes_actual_es)
            if st.button("✏️ Editar", key="btn_editar_obj"):
                st.session_state.editando_objetivo = True
                st.rerun()
        else:
            st.markdown("**🎯 Objetivo**")
            nuevo_objetivo = st.number_input(
                "Monto USD",
                min_value=0,
                max_value=10_000_000,
                value=int(objetivo) if objetivo > 0 else 500_000,
                step=10_000,
                format="%d",
                key="input_obj_usd",
                label_visibility="collapsed",
            )
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("💾 Guardar", type="primary", key="btn_guardar_obj", use_container_width=True):
                    usuario_actual = st.session_state.get("name", "Desconocido")
                    if guardar_objetivo(mes_actual_es, nuevo_objetivo, usuario_actual):
                        st.session_state.editando_objetivo = False
                        st.session_state.objetivo_guardado = True
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("No se pudo guardar.")
            with col_cancel:
                if st.button("Cancelar", key="btn_cancelar_obj", use_container_width=True):
                    st.session_state.editando_objetivo = False
                    st.rerun()
    with col3:
        st.metric("📊 Cumplimiento", f"{porcentaje}%", estado_kpi, delta_color=color_kpi)
    with col4:
        st.metric("🧾 Ticket Promedio", f"${ticket_promedio:,.0f} USD")

    st.divider()

    # ════════════════════════════════════════════════════════════════════
    # SECCIÓN 2b — VENTAS POR CATEGORÍA (tabla + gráfico agrupado)
    # ════════════════════════════════════════════════════════════════════
    if not df_cats_mes.empty:
        st.subheader(f"Ventas por Categoría — {mes_actual_es}")

        df_cats = df_cats_mes.copy()
        df_cats["Ventas USD"]   = pd.to_numeric(df_cats.get("Ventas USD",   0), errors="coerce").fillna(0)
        df_cats["Objetivo USD"] = pd.to_numeric(df_cats.get("Objetivo USD", 0), errors="coerce").fillna(0)
        df_cats["Pct"]          = df_cats.apply(
            lambda r: round(r["Ventas USD"] / r["Objetivo USD"] * 100, 1) if r["Objetivo USD"] > 0 else 0.0,
            axis=1,
        )

        col_tabla, col_grafico = st.columns([1, 1])

        # ── Tabla con barras de progreso ──
        with col_tabla:
            filas_html = ""
            for _, row in df_cats.iterrows():
                cat   = str(row.get("Categoria", ""))
                vtas  = float(row["Ventas USD"])
                obj   = float(row["Objetivo USD"])
                pct   = float(row["Pct"])
                ancho = min(pct, 100)
                color = "#4CAF50" if pct >= 80 else "#FF9800" if pct >= 50 else "#F44336"
                filas_html += f"""
                <tr>
                  <td style="padding:6px 10px;color:#ccc;font-size:13px;">{cat}</td>
                  <td style="padding:6px 10px;text-align:right;color:white;font-size:13px;">${vtas:,.0f}</td>
                  <td style="padding:6px 10px;text-align:right;color:#888;font-size:12px;">${obj:,.0f}</td>
                  <td style="padding:6px 18px;width:130px;">
                    <div style="background:#2a2a3a;border-radius:6px;height:16px;width:100%;">
                      <div style="background:{color};width:{ancho}%;height:16px;border-radius:6px;"></div>
                    </div>
                    <div style="color:{color};font-size:11px;text-align:right;margin-top:2px;">{pct}%</div>
                  </td>
                </tr>"""

            st.markdown(f"""
            <table style="width:100%;border-collapse:collapse;">
              <thead>
                <tr style="border-bottom:1px solid #333;">
                  <th style="padding:6px 10px;text-align:left;color:#888;font-size:12px;">Categoría</th>
                  <th style="padding:6px 10px;text-align:right;color:#888;font-size:12px;">Ventas</th>
                  <th style="padding:6px 10px;text-align:right;color:#888;font-size:12px;">Objetivo</th>
                  <th style="padding:6px 18px;text-align:left;color:#888;font-size:12px;">Progreso</th>
                </tr>
              </thead>
              <tbody>{filas_html}</tbody>
            </table>
            """, unsafe_allow_html=True)

        # ── Gráfico agrupado OBJ vs Ventas ──
        with col_grafico:
            cats_labels = df_cats["Categoria"].tolist()
            fig_cats = go.Figure()
            fig_cats.add_trace(go.Bar(
                name="Objetivo",
                x=cats_labels,
                y=df_cats["Objetivo USD"],
                marker_color="#555577",
                opacity=0.7,
            ))
            fig_cats.add_trace(go.Bar(
                name="Ventas",
                x=cats_labels,
                y=df_cats["Ventas USD"],
                marker_color=[
                    "#4CAF50" if p >= 80 else "#FF9800" if p >= 50 else "#F44336"
                    for p in df_cats["Pct"]
                ],
            ))
            fig_cats.update_layout(
                height=320,
                barmode="group",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis=dict(showgrid=False, tickangle=-20),
                yaxis=dict(showgrid=True, gridcolor="#333"),
                margin=dict(t=40, b=10),
            )
            st.plotly_chart(fig_cats, use_container_width=True)

        st.divider()

    # ════════════════════════════════════════════════════════════════════
    # SECCIÓN 3 — VENTAS POR SEMANA: MES ANTERIOR vs MES ACTUAL
    # ════════════════════════════════════════════════════════════════════

    # Calcular mes anterior
    mes_ant_num  = hoy.month - 1 if hoy.month > 1 else 12
    anio_ant     = hoy.year if hoy.month > 1 else hoy.year - 1
    mes_ant_es   = f"{MESES_ES[mes_ant_num]} {anio_ant}"

    # Preparar datos de detalle (una sola vez para ambos gráficos)
    if not df_detalle.empty and "Fecha" in df_detalle.columns and "Semana" in df_detalle.columns:
        df_detalle["Fecha"]     = pd.to_datetime(df_detalle["Fecha"], errors="coerce")
        df_detalle["Monto USD"] = pd.to_numeric(df_detalle["Monto USD"], errors="coerce").fillna(0)

    def _grafico_semana(df_src, anio, mes, titulo, obj_mensual):
        """Genera gráfico de barras por semana para un mes dado."""
        try:
            if df_src.empty or "Fecha" not in df_src.columns:
                st.info(f"Sin datos para {titulo}.")
                return
            df_mes = df_src[
                (df_src["Fecha"].dt.year == anio) &
                (df_src["Fecha"].dt.month == mes)
            ].copy()
            if df_mes.empty:
                st.info(f"Sin datos semanales para {titulo}.")
                return
            por_semana = df_mes.groupby("Semana")["Monto USD"].sum().reset_index()
            por_semana["_orden"] = por_semana["Semana"].str.extract(r"(\d+)").astype(int)
            por_semana = por_semana.sort_values("_orden").drop(columns=["_orden"])

            fig = px.bar(
                por_semana, x="Semana", y="Monto USD",
                text_auto="$.3s",
                color_discrete_sequence=[COLORES["activa"]],
            )
            fig.update_layout(
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                showlegend=False,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#333"),
            )
            if obj_mensual > 0:
                fig.add_hline(
                    y=obj_mensual / 4, line_dash="dash", line_color="orange",
                    annotation_text="Obj. semanal", annotation_position="top right",
                )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info(f"No se pudo generar el gráfico de {titulo}.")

    # Buscar objetivo del mes anterior
    obj_ant = 0.0
    if not df_obj.empty and "Mes" in df_obj.columns:
        fila_obj_ant = df_obj[df_obj["Mes"].str.strip().str.title() == mes_ant_es]
        if not fila_obj_ant.empty:
            obj_ant = float(pd.to_numeric(fila_obj_ant.iloc[0].get("Objetivo USD", 0), errors="coerce") or 0)

    col_ant, col_act = st.columns(2)
    with col_ant:
        st.subheader(f"📅 {mes_ant_es}")
        _grafico_semana(df_detalle, anio_ant, mes_ant_num, mes_ant_es, obj_ant)
    with col_act:
        st.subheader(f"📅 {mes_actual_es}")
        _grafico_semana(df_detalle, hoy.year, hoy.month, mes_actual_es, objetivo)

    st.divider()

    # ════════════════════════════════════════════════════════════════════
    # SECCIÓN 3b — COMPARACIÓN ÚLTIMOS 6 MESES
    # ════════════════════════════════════════════════════════════════════
    st.subheader("Comparación Últimos 6 Meses")
    try:
        meses_inv = {v: k for k, v in MESES_ES.items()}

        def _orden_mes(m):
            partes = str(m).strip().split(" ")
            if len(partes) == 2:
                return int(partes[1]) * 100 + meses_inv.get(partes[0].capitalize(), 0)
            return 0

        # ── Fuente 1: AC Resumen Mensual (TOTALES) — fuente de verdad ──
        # Normalizamos Mes a Title Case para comparaciones seguras.
        df_comp_base = pd.DataFrame()
        if not df_resumen.empty and "Mes" in df_resumen.columns:
            df_r = df_resumen.copy()
            df_r["Mes"] = df_r["Mes"].str.strip().str.title()
            df_r["Ventas USD"]   = pd.to_numeric(df_r["Ventas USD"],   errors="coerce").fillna(0)
            df_r["Objetivo USD"] = pd.to_numeric(df_r["Objetivo USD"], errors="coerce").fillna(0)
            df_tot = df_r[df_r["Categoria"] == "TOTALES"][["Mes", "Ventas USD", "Objetivo USD"]].copy()
            df_comp_base = df_tot.rename(columns={"Ventas USD": "Facturacion USD"})

        # ── Fuente 2: Histórico Mensual USD — solo para meses sin Excel ──
        # Excluimos explícitamente los meses que ya están en AC Resumen.
        df_hist_men = cargar_historico_mensual()
        if not df_hist_men.empty and "Mes" in df_hist_men.columns and "Facturacion USD" in df_hist_men.columns:
            df_hist_men = df_hist_men.copy()
            df_hist_men["Mes"] = df_hist_men["Mes"].str.strip().str.title()
            df_hist_men["Facturacion USD"] = pd.to_numeric(df_hist_men["Facturacion USD"], errors="coerce").fillna(0)
            meses_en_resumen = set(df_comp_base["Mes"]) if not df_comp_base.empty else set()
            df_hist_filtrado = df_hist_men[
                ~df_hist_men["Mes"].isin(meses_en_resumen)
            ][["Mes", "Facturacion USD"]].copy()
            df_comp_base = pd.concat([df_comp_base, df_hist_filtrado], ignore_index=True)

        if not df_comp_base.empty:
            df_comp_base["_orden"] = df_comp_base["Mes"].apply(_orden_mes)
            df_comp = df_comp_base.sort_values("_orden").tail(6).copy()

            # Objetivo: Objetivos Mensuales (gerente) es la fuente de verdad.
            # Solo usa el valor del Excel si el gerente no definió objetivo para ese mes.
            if "Objetivo USD" not in df_comp.columns:
                df_comp["Objetivo USD"] = 0.0
            if not df_obj.empty and "Mes" in df_obj.columns:
                obj_dict = {
                    str(k).strip().title(): float(v)
                    for k, v in zip(df_obj["Mes"], pd.to_numeric(df_obj["Objetivo USD"], errors="coerce").fillna(0))
                }
                df_comp["Objetivo USD"] = df_comp["Mes"].map(obj_dict).fillna(df_comp["Objetivo USD"])

            meses_ordenados = df_comp["Mes"].tolist()
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Bar(
                x=df_comp["Mes"], y=df_comp["Facturacion USD"],
                name="Ventas", marker_color=COLORES["activa"],
                text=df_comp["Facturacion USD"].apply(lambda x: f"${x:,.0f}"),
                textposition="outside",
            ))
            if df_comp["Objetivo USD"].sum() > 0:
                fig_comp.add_trace(go.Scatter(
                    x=df_comp["Mes"], y=df_comp["Objetivo USD"],
                    name="Objetivo", mode="lines+markers",
                    line=dict(color="#FF9800", width=3, dash="dash"),
                ))
            fig_comp.update_layout(
                height=500,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis=dict(showgrid=False, categoryorder="array", categoryarray=meses_ordenados),
                yaxis=dict(showgrid=True, gridcolor="#333"),
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.info("No hay datos históricos disponibles todavía.")
    except Exception:
        st.info("No se pudo generar el gráfico de comparación.")

    st.divider()

    # ════════════════════════════════════════════════════════════════════
    # SECCIÓN 4 — HISTORIAL MENSUAL
    # ════════════════════════════════════════════════════════════════════
    st.subheader("📅 Historial Mensual")

    try:
        df_cierres = cargar_historial_cierres()
        filas_hist = []

        meses_inv_h = {v: k for k, v in MESES_ES.items()}
        def _orden_h(mes):
            partes = str(mes).strip().split(" ")
            if len(partes) == 2:
                return int(partes[1]) * 100 + meses_inv_h.get(partes[0].capitalize(), 0)
            return 0

        if not df_cierres.empty:
            for _, row in df_cierres.iterrows():
                mes_raw = str(row.get("Mes", ""))
                try:
                    facturado_val = float(str(row.get("Facturado USD", 0)).replace(",", "").replace("$", "") or 0)
                    objetivo_val  = float(str(row.get("Objetivo USD",  0)).replace(",", "").replace("$", "") or 0)
                except ValueError:
                    facturado_val, objetivo_val = 0.0, 0.0
                estado_raw = str(row.get("Estado", ""))
                estado = "✅ Cumplido" if "Superado" in estado_raw else "❌ No cumplido"
                filas_hist.append({
                    "Mes":           mes_raw,
                    "Facturado USD": f"${facturado_val:,.0f}",
                    "Objetivo USD":  f"${objetivo_val:,.0f}",
                    "Estado":        estado,
                })

        # Meses con datos en AC Resumen pero sin cierre registrado — mostrar como "Sin cerrar"
        meses_ya_en_hist = {f["Mes"].strip().title() for f in filas_hist}
        if not df_resumen.empty and "Mes" in df_resumen.columns:
            df_r_tot = df_resumen[df_resumen.get("Categoria", pd.Series(dtype=str)).str.strip().str.upper() == "TOTALES"] if "Categoria" in df_resumen.columns else pd.DataFrame()
            for _, row in df_r_tot.iterrows():
                mes_r = str(row.get("Mes", "")).strip().title()
                if mes_r and mes_r != mes_actual_es.strip().title() and mes_r not in meses_ya_en_hist:
                    fac = pd.to_numeric(row.get("Ventas USD", 0), errors="coerce") or 0
                    obj_r = pd.to_numeric(row.get("Objetivo USD", 0), errors="coerce") or 0
                    # Tomar objetivo de Objetivos Mensuales si existe
                    if not df_obj.empty and "Mes" in df_obj.columns:
                        obj_dict_h = {str(k).strip().title(): float(v) for k, v in zip(df_obj["Mes"], pd.to_numeric(df_obj["Objetivo USD"], errors="coerce").fillna(0))}
                        obj_r = obj_dict_h.get(mes_r, obj_r)
                    filas_hist.append({
                        "Mes":           mes_r,
                        "Facturado USD": f"${fac:,.0f}",
                        "Objetivo USD":  f"${obj_r:,.0f}" if obj_r > 0 else "Sin definir",
                        "Estado":        "⚠️ Sin cerrar",
                    })
                    meses_ya_en_hist.add(mes_r)

        # Mes actual — siempre "En curso"
        meses_cerrados = [f["Mes"].strip().title() for f in filas_hist]
        if mes_actual_es.strip().title() not in meses_cerrados:
            filas_hist.append({
                "Mes":           mes_actual_es,
                "Facturado USD": f"${ventas_mes:,.0f}",
                "Objetivo USD":  f"${objetivo:,.0f}" if objetivo > 0 else "Sin definir",
                "Estado":        "🟡 En curso",
            })

        # Ordenar y limitar a los últimos 6 meses
        filas_hist.sort(key=lambda r: _orden_h(r["Mes"]))
        filas_hist = filas_hist[-6:]

        df_hist_tabla = pd.DataFrame(filas_hist)

        def _color_hist(val):
            s = str(val)
            if "Cumplido" in s and "No" not in s:
                return "background-color:#1a3a1a;color:#4CAF50;font-weight:bold"
            if "No cumplido" in s:
                return "background-color:#3a1a1a;color:#F44336;font-weight:bold"
            if "En curso" in s:
                return "background-color:#2a2a10;color:#FFC107;font-weight:bold"
            if "Sin cerrar" in s:
                return "background-color:#1a1a3a;color:#90CAF9;font-weight:bold"
            return ""

        st.dataframe(
            df_hist_tabla.style.applymap(_color_hist, subset=["Estado"]),
            use_container_width=True,
            hide_index=True,
        )
    except Exception:
        st.info("No se pudo cargar el historial de meses.")

    # ════════════════════════════════════════════════════════════════════
    # SECCIÓN 5 — CIERRE DEL MES
    # ════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("🔒 Cierre del Mes")

    if "confirmar_cierre" not in st.session_state:
        st.session_state.confirmar_cierre = False

    # Armar lista de meses que se pueden cerrar:
    # - Mes actual (siempre disponible)
    # - Meses pasados con datos en AC Resumen que no fueron cerrados
    meses_cerrables = {}  # {mes_label: {facturado, objetivo}}

    # Mes actual
    meses_cerrables[mes_actual_es] = {"facturado": ventas_mes, "objetivo": objetivo}

    # Meses pasados sin cerrar (datos en AC Resumen pero no en Historial Cierres)
    meses_cerrados_set = set()
    df_cierres_check = cargar_historial_cierres()
    if not df_cierres_check.empty and "Mes" in df_cierres_check.columns:
        meses_cerrados_set = {str(m).strip().title() for m in df_cierres_check["Mes"]}

    if not df_resumen.empty and "Mes" in df_resumen.columns and "Categoria" in df_resumen.columns:
        df_r_tot_cierre = df_resumen[df_resumen["Categoria"].str.strip().str.upper() == "TOTALES"]
        for _, row in df_r_tot_cierre.iterrows():
            mes_r = str(row.get("Mes", "")).strip().title()
            if mes_r and mes_r not in meses_cerrados_set and mes_r != mes_actual_es:
                fac_r = float(pd.to_numeric(row.get("Ventas USD", 0), errors="coerce") or 0)
                obj_r = 0.0
                if not df_obj.empty and "Mes" in df_obj.columns:
                    obj_lookup = {str(k).strip().title(): float(v) for k, v in
                                  zip(df_obj["Mes"], pd.to_numeric(df_obj["Objetivo USD"], errors="coerce").fillna(0))}
                    obj_r = obj_lookup.get(mes_r, 0.0)
                meses_cerrables[mes_r] = {"facturado": fac_r, "objetivo": obj_r}

    # Mostrar selector si hay meses sin cerrar aparte del actual
    meses_sin_cerrar = [m for m in meses_cerrables if m != mes_actual_es]
    if meses_sin_cerrar:
        st.warning(f"⚠️ Hay **{len(meses_sin_cerrar)} mes(es)** sin cerrar: {', '.join(meses_sin_cerrar)}")

    col_cierre1, col_cierre2, _ = st.columns([2, 2, 2])
    with col_cierre1:
        opciones_cierre = list(meses_cerrables.keys())
        mes_a_cerrar = st.selectbox("Mes a cerrar", opciones_cierre, key="sel_mes_cierre")
    with col_cierre2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔒 Cerrar Mes", type="primary", key="btn_cierre_mes"):
            datos_cierre = meses_cerrables[mes_a_cerrar]
            if datos_cierre["objetivo"] <= 0:
                st.error("⚠️ No podés cerrar el mes sin un objetivo definido. Definilo arriba primero.")
            else:
                st.session_state.confirmar_cierre = True
                st.session_state.mes_a_cerrar = mes_a_cerrar

    if st.session_state.get("confirmar_cierre", False):
        mes_cierre = st.session_state.get("mes_a_cerrar", mes_actual_es)
        datos_cierre = meses_cerrables.get(mes_cierre, {"facturado": 0, "objetivo": 0})
        fac_cierre = datos_cierre["facturado"]
        obj_cierre = datos_cierre["objetivo"]
        pct_cierre = round(fac_cierre / obj_cierre * 100, 1) if obj_cierre > 0 else 0

        with st.container():
            st.markdown("---")
            if mes_cierre == mes_actual_es:
                ultimo_dia_mes = _cal.monthrange(hoy.year, hoy.month)[1]
                dias_restantes = ultimo_dia_mes - hoy.day
                if dias_restantes > 0:
                    st.warning(
                        f"⚠️ **Atención:** Todavía faltan **{dias_restantes} días** para que termine "
                        f"{mes_cierre}. ¿Estás seguro que querés cerrar el mes ahora?"
                    )
            else:
                st.info(f"📅 Estás cerrando un mes pasado: **{mes_cierre}**")

            cumplido_txt = "✅ **Objetivo SUPERADO**" if fac_cierre >= obj_cierre else "❌ **Objetivo NO alcanzado**"
            st.markdown(f"""
**Resumen del cierre:**
- 📅 Mes: **{mes_cierre}**
- 🎯 Objetivo: **${obj_cierre:,.0f} USD**
- 💰 Facturado: **${fac_cierre:,.0f} USD**
- 📊 Cumplimiento: **{pct_cierre}%**
- {cumplido_txt}
            """)

            col_conf1, col_conf2 = st.columns([1, 1])
            with col_conf1:
                if st.button("✅ Confirmar Cierre", type="primary", key="btn_confirmar_cierre"):
                    usuario_actual = st.session_state.get("name", "Desconocido")
                    if guardar_cierre_mes(mes_cierre, obj_cierre, fac_cierre, usuario_actual):
                        st.session_state.confirmar_cierre = False
                        st.session_state.mes_a_cerrar = None
                        st.cache_data.clear()
                        st.success(f"✅ Mes {mes_cierre} cerrado correctamente.")
                        st.rerun()
            with col_conf2:
                if st.button("Cancelar", key="btn_cancelar_cierre"):
                    st.session_state.confirmar_cierre = False
                    st.session_state.mes_a_cerrar = None
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# APLICACIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """
    Función principal de la aplicación Streamlit.
    Maneja el login y renderiza las pestañas según el rol del usuario.
    """

    # ── Carga de configuración de autenticación ───────────────────────────
    config = cargar_config()

    # ── Configuración del autenticador ────────────────────────────────────
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )

    # ── Pantalla de login ─────────────────────────────────────────────────
    # Si el usuario no está logueado, muestra el formulario de login
    if not st.session_state.get("authentication_status"):
        col_login1, col_login2, col_login3 = st.columns([1, 2, 1])
        with col_login2:
            st.markdown("## 📊 Farkim — Dashboard")
            st.markdown("**Sistema de Business Intelligence**")
            st.markdown("---")

        authenticator.login(location="main")

        status = st.session_state.get("authentication_status")

        if status is False:
            st.error("❌ Usuario o contraseña incorrectos.")
        elif status is None:
            st.info("🔐 Ingresá tus credenciales para acceder al dashboard.")

        return   # Detenemos la ejecución hasta que haya login

    # ── Dashboard (usuario autenticado) ───────────────────────────────────
    usuario = st.session_state.get("name", "")
    username = st.session_state.get("username", "")

    # Obtenemos el rol del usuario desde el config
    rol = "viewer"
    if username in config["credentials"]["usernames"]:
        roles = config["credentials"]["usernames"][username].get("roles", [])
        if roles:
            rol = roles[0]

    # ── Sidebar con info del usuario ──────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### 👤 {usuario}")
        st.markdown(f"**Rol:** `{rol}`")
        st.markdown(f"**{datetime.now().strftime('%d/%m/%Y %H:%M')} hs**")
        st.divider()

        # Botón de logout
        authenticator.logout("Cerrar sesión", location="sidebar")

        st.divider()
        st.markdown("**Farkim Sistemas**")
        st.caption("Dashboard v1.0 — 2026")

    # ── Header del dashboard ──────────────────────────────────────────────
    st.title("📊 Farkim — Dashboard Comercial")
    st.caption("Datos en tiempo real desde Odoo CRM → Google Sheets")

    # ── Pestañas principales ──────────────────────────────────────────────
    if rol in ["gerente", "admin"]:
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Resumen",
            "📋 Pipeline",
            "💰 Ventas del Mes",
            "👥 Por Vendedor",
            "📜 Histórico",
            "🔴 Sin Movimiento",
        ])
        with tab1: tab_resumen(rol)
        with tab2: tab_pipeline(rol)
        with tab3: tab_ventas_del_mes(rol)
        with tab4: tab_vendedores(rol)
        with tab5: tab_historico(rol)
        with tab6: tab_sin_movimiento(rol)
    else:
        # Vista limitada para roles sin acceso completo
        tab1, tab2 = st.tabs(["📊 Resumen", "📋 Pipeline"])
        with tab1: tab_resumen(rol)
        with tab2: tab_pipeline(rol)


if __name__ == "__main__":
    main()
