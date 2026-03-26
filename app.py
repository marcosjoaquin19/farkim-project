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
    Pestaña de facturación histórica (2020-2026) con datos de Alto Cerró.
    Muestra evolución mensual y anual en USD usando el dólar real de cada venta.
    """
    st.header("📜 Facturación Histórica (2020-2026)")
    st.caption("Fuente: Alto Cerró  •  Montos convertidos a USD con el dólar oficial del día de cada venta")

    df_mensual = cargar_historico_mensual()
    df_anual = cargar_historico_anual()

    if df_mensual.empty:
        st.warning("No se pudieron cargar los datos históricos.")
        return

    # ── KPIs principales ────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    total_usd = df_anual["Facturacion USD"].sum() if not df_anual.empty else 0
    total_ops = df_anual["Operaciones"].sum() if not df_anual.empty else 0
    anios = len(df_anual) if not df_anual.empty else 0
    promedio_anual = total_usd / anios if anios > 0 else 0

    with col1:
        st.metric("💰 Facturación Total", f"${total_usd:,.0f} USD", f"6 años de historia")
    with col2:
        st.metric("📊 Operaciones", f"{total_ops:,.0f}", f"{anios} años")
    with col3:
        st.metric("📅 Promedio Anual", f"${promedio_anual:,.0f} USD")
    with col4:
        if not df_anual.empty:
            mejor_anio = df_anual.loc[df_anual["Facturacion USD"].idxmax()]
            st.metric("🏆 Mejor Año", f"{int(mejor_anio['Anio'])}", f"${mejor_anio['Facturacion USD']:,.0f} USD")

    st.divider()

    # ── Gráfico barras: facturación anual ───────────────────────────────
    st.subheader("Facturación Anual en USD")

    if not df_anual.empty:
        df_anual_plot = df_anual.copy()
        df_anual_plot['Anio'] = df_anual_plot['Anio'].astype(str)

        # Color especial para 2026 (año incompleto)
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
            xaxis=dict(showgrid=False, title="Año"),
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

    # ── Gráfico líneas: evolución mensual ───────────────────────────────
    st.subheader("Evolución Mensual en USD")

    if "Periodo" in df_mensual.columns and "Facturacion USD" in df_mensual.columns:
        df_plot = df_mensual.sort_values("Periodo").copy()

        fig_mensual = go.Figure()

        # Barras de facturación mensual
        fig_mensual.add_trace(go.Bar(
            x=df_plot["Mes"],
            y=df_plot["Facturacion USD"],
            name="Facturación Mensual",
            marker_color=COLORES["primario"],
            opacity=0.6,
        ))

        # Línea de tendencia (media móvil 6 meses)
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

    # ── Tabla resumen anual ─────────────────────────────────────────────
    st.subheader("Resumen por Año")

    if not df_anual.empty:
        df_tabla = df_anual.copy()
        df_tabla = df_tabla.rename(columns={
            "Anio": "Año",
            "Facturacion USD": "Facturación USD",
            "Ticket Promedio USD": "Ticket Prom. USD",
            "Clientes Unicos": "Clientes",
            "Productos Unicos": "Productos",
            "Dolar Promedio": "Dólar Prom.",
        })

        for col in ["Facturación USD", "Ticket Prom. USD"]:
            if col in df_tabla.columns:
                df_tabla[col] = df_tabla[col].apply(lambda x: f"${x:,.0f}")

        if "Dólar Prom." in df_tabla.columns:
            df_tabla["Dólar Prom."] = df_tabla["Dólar Prom."].apply(lambda x: f"${x:,.0f}")

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
    Pestaña de ventas cerradas del mes con seguimiento de objetivo.
    Muestra progreso semanal, comparación con meses anteriores,
    y permite al gerente editar el objetivo mensual.
    """
    st.header("💰 Ventas del Mes")

    if rol not in ["gerente", "admin"]:
        st.warning("🔒 Esta sección es solo para gerentes y administradores.")
        return

    df = cargar_ventas_cerradas()
    df_obj = cargar_objetivos()

    # ── Mes actual en formato español ───────────────────────────────────
    hoy = date.today()
    mes_actual_es = f"{MESES_ES[hoy.month]} {hoy.year}"
    mes_actual_num = f"{hoy.year}-{hoy.month:02d}"

    # ── Filtrar ventas del mes actual ───────────────────────────────────
    df_mes = pd.DataFrame()
    if not df.empty and "Fecha Cierre" in df.columns:
        df["Fecha Cierre"] = df["Fecha Cierre"].astype(str)
        df_mes = df[df["Fecha Cierre"].str.startswith(mes_actual_num)]

    ventas_mes = df_mes["Monto USD"].sum() if not df_mes.empty and "Monto USD" in df_mes.columns else 0

    # ── Obtener objetivo del mes actual ─────────────────────────────────
    objetivo = 0
    if not df_obj.empty and "Mes" in df_obj.columns:
        fila_obj = df_obj[df_obj["Mes"] == mes_actual_es]
        if not fila_obj.empty and "Objetivo USD" in df_obj.columns:
            objetivo = float(fila_obj.iloc[0]["Objetivo USD"])

    # ── KPIs principales ────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    porcentaje = round((ventas_mes / objetivo * 100), 1) if objetivo > 0 else 0
    ops_cerradas = len(df_mes)
    ticket_promedio = round(ventas_mes / ops_cerradas, 0) if ops_cerradas > 0 else 0

    with col1:
        st.metric("💰 Ventas del Mes", f"${ventas_mes:,.0f} USD", f"{ops_cerradas} operaciones cerradas")
    with col2:
        st.metric("🎯 Objetivo", f"${objetivo:,.0f} USD", mes_actual_es)
    with col3:
        delta_color = "normal" if porcentaje >= 80 else "inverse"
        st.metric("📊 Cumplimiento", f"{porcentaje}%", f"{'En camino' if porcentaje >= 70 else 'Atención'}", delta_color=delta_color)
    with col4:
        st.metric("🧾 Ticket Promedio", f"${ticket_promedio:,.0f} USD")

    # ── Barra de progreso visual ────────────────────────────────────────
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
        st.info(f"No hay objetivo definido para {mes_actual_es}. Usá el botón de abajo para cargarlo.")

    st.divider()

    # ── Ventas por semana del mes actual ────────────────────────────────
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.subheader(f"Ventas por Semana — {mes_actual_es}")
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
            st.info(f"No hay ventas cerradas en {mes_actual_es} todavía.")

    # ── Comparación últimos 6 meses ─────────────────────────────────────
    with col_der:
        st.subheader("Comparación Últimos 6 Meses")
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
            st.info("No hay datos históricos de ventas cerradas.")

    st.divider()

    # ── Detalle de ventas del mes ───────────────────────────────────────
    if not df_mes.empty:
        st.subheader(f"Detalle de Ventas Cerradas — {mes_actual_es}")
        cols_mostrar = [c for c in ["Oportunidad", "Cliente", "Vendedor", "Monto USD",
                                     "Semana", "Fecha Cierre"] if c in df_mes.columns]
        df_detalle = df_mes[cols_mostrar].sort_values("Monto USD", ascending=False).reset_index(drop=True)
        df_detalle.index += 1
        if "Monto USD" in df_detalle.columns:
            df_detalle["Monto USD"] = df_detalle["Monto USD"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(df_detalle, use_container_width=True)

    # ── Objetivo mensual: mostrar actual + botón editar ─────────────────
    st.divider()

    # Inicializar estado del editor
    if "editando_objetivo" not in st.session_state:
        st.session_state.editando_objetivo = False
    if "objetivo_guardado" not in st.session_state:
        st.session_state.objetivo_guardado = False

    # Mostrar mensaje de éxito si se acaba de guardar
    if st.session_state.objetivo_guardado:
        st.success("Objetivo guardado correctamente.")
        st.session_state.objetivo_guardado = False

    col_obj1, col_obj2 = st.columns([4, 1])

    with col_obj1:
        if objetivo > 0:
            st.subheader(f"🎯 Objetivo {mes_actual_es}: ${objetivo:,.0f} USD — {porcentaje}% cumplido")
        else:
            st.subheader(f"🎯 Objetivo {mes_actual_es}: Sin definir")

    with col_obj2:
        if st.button("✏️ Editar", key="btn_editar_obj"):
            st.session_state.editando_objetivo = not st.session_state.editando_objetivo
            st.rerun()

    # ── Editor de objetivo (visible al hacer clic en Editar) ──────────
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
            if st.button("💾 Guardar", type="primary", key="btn_guardar_obj"):
                usuario_actual = st.session_state.get("name", "Desconocido")
                exito = guardar_objetivo(mes_seleccionado, nuevo_objetivo, usuario_actual)
                if exito:
                    st.session_state.editando_objetivo = False
                    st.session_state.objetivo_guardado = True
                    st.rerun()
                else:
                    st.error("No se pudo guardar. Revisá la conexión.")
        with col_btn2:
            if st.button("Cancelar", key="btn_cancelar_obj"):
                st.session_state.editando_objetivo = False
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
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📊 Resumen",
            "📋 Pipeline",
            "💰 Ventas del Mes",
            "👥 Por Vendedor",
            "📈 Evolución",
            "📜 Histórico",
            "🔴 Sin Movimiento",
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
        tab1, tab2, tab4 = st.tabs(["📊 Resumen", "📋 Pipeline", "📈 Evolución"])
        with tab1: tab_resumen(rol)
        with tab2: tab_pipeline(rol)
        with tab4: tab_evolucion(rol)


if __name__ == "__main__":
    main()
