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
from datetime import datetime
import sys
import os

# ── Configuración de la página ────────────────────────────────────────────────
st.set_page_config(
    page_title="Farkim — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
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
    Carga el config.yaml con los usuarios y contraseñas hasheadas.
    Se cachea para no leerlo en cada rerun de Streamlit.
    """
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
    """
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
        from conexion_sheets import autenticar, abrir_spreadsheet, obtener_hoja

        cliente = autenticar()
        spreadsheet = abrir_spreadsheet(cliente)
        hoja = obtener_hoja(spreadsheet, "Pipeline Completo")

        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
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

    # ── Top 5 oportunidades activas ───────────────────────────────────────
    st.subheader("🏆 Top 5 Oportunidades Activas por Monto")
    if "Estado" in df.columns and "Monto USD" in df.columns:
        top5 = (
            df[df["Estado"] == "Activa"]
            .sort_values("Monto USD", ascending=False)
            .head(5)[["Oportunidad", "Cliente", "Vendedor", "Etapa", "Monto USD", "Probabilidad %"]]
            .reset_index(drop=True)
        )
        top5.index += 1
        top5["Monto USD"] = top5["Monto USD"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(top5, use_container_width=True)


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

    # ── Filtros en la barra lateral ───────────────────────────────────────
    with st.sidebar:
        st.subheader("🔍 Filtros")

        estados_disp = ["Todos"] + sorted(df["Estado"].unique().tolist()) if "Estado" in df.columns else ["Todos"]
        estado_sel = st.selectbox("Estado", estados_disp)

        if "Vendedor" in df.columns:
            vendedores_disp = ["Todos"] + sorted(df["Vendedor"].unique().tolist())
            vendedor_sel = st.selectbox("Vendedor", vendedores_disp)
        else:
            vendedor_sel = "Todos"

        if "Monto USD" in df.columns and len(df) > 0:
            monto_min = float(df["Monto USD"].min())
            monto_max = float(df["Monto USD"].max())
            monto_rango = st.slider(
                "Rango de Monto USD",
                min_value=monto_min,
                max_value=monto_max,
                value=(monto_min, monto_max),
                format="$%.0f"
            )
        else:
            monto_rango = (0, 99999999)

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
    Solo visible para rol 'gerente' o 'admin'.
    """
    st.header("👥 Análisis por Vendedor")

    # Control de acceso por rol
    if rol not in ["gerente", "admin"]:
        st.warning("🔒 Esta sección es solo para gerentes y administradores.")
        return

    df = cargar_vendedores()
    if df.empty:
        st.warning("No se pudieron cargar los datos por vendedor.")
        return

    # ── Top vendedores por monto ──────────────────────────────────────────
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader("Ranking por Monto Total")
        if "Monto Total USD" in df.columns and "Vendedor" in df.columns:
            df_rank = df.sort_values("Monto Total USD", ascending=True).tail(10)  # top 10

            fig_rank = px.bar(
                df_rank,
                x="Monto Total USD",
                y="Vendedor",
                orientation="h",
                color="Monto Total USD",
                color_continuous_scale=["#1e1e2e", "#2196F3"],
                text_auto="$.3s",
            )
            fig_rank.update_layout(
                height=400,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                showlegend=False,
                coloraxis_showscale=False,
                yaxis=dict(showgrid=False),
                xaxis=dict(showgrid=True, gridcolor="#333"),
            )
            st.plotly_chart(fig_rank, use_container_width=True)

    with col_der:
        st.subheader("% Inactivas por Vendedor")
        if "% Inactivas" in df.columns and "Vendedor" in df.columns:
            df_inact = df.sort_values("% Inactivas", ascending=False)

            colores_barra = [
                "#F44336" if x >= 30 else "#FF9800" if x >= 15 else "#4CAF50"
                for x in df_inact["% Inactivas"]
            ]

            fig_inact = px.bar(
                df_inact,
                x="Vendedor",
                y="% Inactivas",
                text_auto=".1f",
            )
            fig_inact.update_traces(marker_color=colores_barra)
            fig_inact.update_layout(
                height=400,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                xaxis=dict(showgrid=False, tickangle=-30),
                yaxis=dict(showgrid=True, gridcolor="#333"),
            )
            fig_inact.add_hline(y=20, line_dash="dash", line_color="orange",
                                annotation_text="Umbral 20%", annotation_position="top right")
            st.plotly_chart(fig_inact, use_container_width=True)

    st.divider()

    # ── Tabla completa de vendedores ──────────────────────────────────────
    st.subheader("Detalle Completo por Vendedor")
    df_tabla = df.copy()

    # Formatear columnas de monto
    for col in ["USD Activas", "USD En Riesgo", "USD Inactivas", "Monto Total USD"]:
        if col in df_tabla.columns:
            df_tabla[col] = df_tabla[col].apply(lambda x: f"${x:,.0f}")

    if "% Inactivas" in df_tabla.columns:
        df_tabla["% Inactivas"] = df_tabla["% Inactivas"].apply(lambda x: f"{x:.1f}%")

    df_tabla = df_tabla.sort_values("Monto Total USD", ascending=False).reset_index(drop=True)
    df_tabla.index += 1

    st.dataframe(df_tabla, use_container_width=True)


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

    # Aseguramos orden cronológico
    if "Mes" in df.columns:
        df = df.sort_values("Mes")

    # ── Métricas clave de evolución ───────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    if "Monto Total USD" in df.columns:
        mes_top = df.loc[df["Monto Total USD"].idxmax()]
        with col1:
            st.metric("📅 Mejor Mes", mes_top["Mes"], f"${mes_top['Monto Total USD']:,.0f} USD")

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
            x=df["Mes"],
            y=df["Monto Total USD"],
            name="Monto Mensual",
            marker_color=COLORES["primario"],
            opacity=0.8,
        ))

        if "Monto Acumulado USD" in df.columns:
            fig_linea.add_trace(go.Scatter(
                x=df["Mes"],
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

    df_tabla = df_tabla.sort_values("Mes", ascending=False).reset_index(drop=True)
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
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Resumen",
            "📋 Pipeline",
            "👥 Por Vendedor",
            "📈 Evolución",
            "🔴 Sin Movimiento",
        ])
        with tab1: tab_resumen(rol)
        with tab2: tab_pipeline(rol)
        with tab3: tab_vendedores(rol)
        with tab4: tab_evolucion(rol)
        with tab5: tab_sin_movimiento(rol)
    else:
        # Vista limitada para roles sin acceso completo
        tab1, tab2, tab4 = st.tabs(["📊 Resumen", "📋 Pipeline", "📈 Evolución"])
        with tab1: tab_resumen(rol)
        with tab2: tab_pipeline(rol)
        with tab4: tab_evolucion(rol)


if __name__ == "__main__":
    main()
