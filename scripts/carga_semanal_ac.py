# ==============================================
# Nombre:      carga_semanal_ac.py
# Descripcion: Procesa el Excel semanal de Alto Cerro y lo
#              guarda en Google Sheets hoja "AC Ventas Detalle".
#              Detecta duplicados por rango de fechas.
#              Recalcula el resumen mensual en "AC Ventas Mensual".
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-30
# ==============================================

import pandas as pd
from datetime import datetime
import sys
import os
import io

sys.path.append(os.path.dirname(__file__))

from conexion_sheets import (
    autenticar as autenticar_sheets,
    abrir_spreadsheet,
    obtener_hoja,
    escribir_hoja,
)

# Columnas requeridas en el Excel de Alto Cerro (formato nuevo)
COLUMNAS_REQUERIDAS = [
    "kx_tipfac", "iv_feccte", "neto_us",
    "iv_nombre", "ve_nombre"
]

# Columnas opcionales
COLUMNAS_OPCIONALES = [
    "ar_descrip", "us_dia", "kx_nrofac", "kx_nrocomp",
    "iv_total", "cp_codprov"
]

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


# ── Lectura del archivo ─────────────────────────────────────────────────────────

def leer_archivo(archivo_bytes, nombre_archivo):
    """
    Lee el archivo subido (XLS, XLSX o CSV) y devuelve un DataFrame.
    archivo_bytes: bytes del archivo
    nombre_archivo: nombre del archivo para detectar extension
    """
    nombre = nombre_archivo.lower()
    try:
        if nombre.endswith(".csv"):
            return pd.read_csv(io.BytesIO(archivo_bytes))
        elif nombre.endswith(".xls"):
            return pd.read_excel(io.BytesIO(archivo_bytes), engine="xlrd")
        elif nombre.endswith(".xlsx"):
            return pd.read_excel(io.BytesIO(archivo_bytes), engine="openpyxl")
        else:
            return None, "Formato no soportado. Usa .xls, .xlsx o .csv"
    except Exception as e:
        return None, f"No se pudo leer el archivo: {e}"


# ── Validacion ─────────────────────────────────────────────────────────────────

def validar_csv(df):
    """
    Verifica que el archivo tenga las columnas minimas requeridas.
    Devuelve (True, "") si es valido, (False, mensaje_error) si no.
    """
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        return False, f"Faltan columnas: {', '.join(faltantes)}"
    if len(df) == 0:
        return False, "El archivo esta vacio."
    return True, ""


# ── Procesamiento ──────────────────────────────────────────────────────────────

def procesar_csv(df, cargado_por="sistemas"):
    """
    Limpia y procesa el Excel de Alto Cerro (formato nuevo):
    - Parsea fechas desde iv_feccte
    - Filtra solo facturas validas (F/A, F/B)
    - Excluye montos negativos o cero
    - Agrega columnas de mes, semana y metadatos de carga
    Devuelve DataFrame limpio listo para guardar.
    """
    df = df.copy()

    # Parsear fechas
    df["fecha_dt"] = pd.to_datetime(df["iv_feccte"], errors="coerce")
    df = df.dropna(subset=["fecha_dt"])

    # Filtrar solo facturas de venta
    df = df[df["kx_tipfac"].isin(["F/A", "F/B"])].copy()

    # Filtrar montos validos
    df["neto_us"] = pd.to_numeric(df["neto_us"], errors="coerce").fillna(0)
    df = df[df["neto_us"] > 0].copy()

    if df.empty:
        return df

    # Dolar del dia (opcional)
    if "us_dia" in df.columns:
        df["us_dia"] = pd.to_numeric(df["us_dia"], errors="coerce").fillna(0)
    else:
        df["us_dia"] = 0

    # Columnas de periodo
    df["anio"]       = df["fecha_dt"].dt.year
    df["mes_num"]    = df["fecha_dt"].dt.month
    df["mes_es"]     = df.apply(lambda r: f"{MESES_ES[r['mes_num']]} {r['anio']}", axis=1)
    df["dia"]        = df["fecha_dt"].dt.day
    df["semana_num"] = df["dia"].apply(lambda d: ((d - 1) // 7) + 1)
    df["semana_label"] = df["semana_num"].apply(lambda n: f"Semana {n}")
    df["fecha_str"]  = df["fecha_dt"].dt.strftime("%Y-%m-%d")

    # Metadatos de carga
    df["cargado_el"]  = datetime.now().strftime("%Y-%m-%d %H:%M")
    df["cargado_por"] = cargado_por

    return df


# ── Deduplicacion ──────────────────────────────────────────────────────────────

def obtener_fechas_existentes(hoja):
    """
    Lee las fechas ya cargadas en 'AC Ventas Detalle'.
    Devuelve un set de strings "YYYY-MM-DD".
    """
    try:
        datos = hoja.get_all_records()
        if not datos:
            return set()
        df_existente = pd.DataFrame(datos)
        if "Fecha" not in df_existente.columns:
            return set()
        return set(df_existente["Fecha"].astype(str).tolist())
    except Exception:
        return set()


def filtrar_duplicados(df_nuevo, fechas_existentes):
    """
    Elimina del df_nuevo las filas cuya fecha ya esta en Sheets.
    Devuelve (df_sin_duplicados, n_duplicados).
    """
    if not fechas_existentes:
        return df_nuevo, 0
    mask_nueva = ~df_nuevo["fecha_str"].isin(fechas_existentes)
    duplicados = (~mask_nueva).sum()
    return df_nuevo[mask_nueva].copy(), duplicados


# ── Guardar en Google Sheets ───────────────────────────────────────────────────

def crear_hoja_si_no_existe(spreadsheet, nombre, filas=5000, cols=20):
    hojas = [h.title for h in spreadsheet.worksheets()]
    if nombre not in hojas:
        spreadsheet.add_worksheet(title=nombre, rows=filas, cols=cols)


def guardar_detalle(df, spreadsheet):
    """
    Agrega las filas nuevas a 'AC Ventas Detalle' (no reemplaza).
    """
    crear_hoja_si_no_existe(spreadsheet, "AC Ventas Detalle")
    hoja = obtener_hoja(spreadsheet, "AC Ventas Detalle")

    encabezados = [
        "Fecha", "Mes", "Semana",
        "Producto", "Cliente", "Vendedor",
        "Monto USD", "Dolar",
        "Cargado el", "Cargado por"
    ]

    datos_actuales = hoja.get_all_values()
    if len(datos_actuales) == 0:
        hoja.append_row(encabezados)

    filas_nuevas = []
    for _, r in df.iterrows():
        filas_nuevas.append([
            r["fecha_str"],
            r["mes_es"],
            r["semana_label"],
            str(r.get("ar_descrip", "")),
            str(r.get("iv_nombre", "")),
            str(r.get("ve_nombre", "")),
            round(float(r["neto_us"]), 2),
            round(float(r["us_dia"]), 2) if r["us_dia"] > 0 else "",
            r["cargado_el"],
            r["cargado_por"],
        ])

    if filas_nuevas:
        hoja.append_rows(filas_nuevas, value_input_option="USER_ENTERED")

    return len(filas_nuevas)


def recalcular_mensual(spreadsheet):
    """
    Lee 'AC Ventas Detalle' completo y recalcula 'AC Ventas Mensual'.
    """
    hoja_det = obtener_hoja(spreadsheet, "AC Ventas Detalle")
    if hoja_det is None:
        return False

    datos = hoja_det.get_all_records()
    if not datos:
        return False

    df = pd.DataFrame(datos)
    if "Monto USD" not in df.columns or "Mes" not in df.columns:
        return False

    df["Monto USD"] = pd.to_numeric(df["Monto USD"], errors="coerce").fillna(0)
    df["Dolar"]     = pd.to_numeric(df["Dolar"],     errors="coerce").fillna(0)

    mensual = df.groupby("Mes").agg(
        Operaciones     =("Monto USD", "count"),
        Facturacion_USD =("Monto USD", "sum"),
        Clientes_Unicos =("Cliente",   "nunique"),
        Dolar_Promedio  =("Dolar",     "mean"),
    ).reset_index()

    mensual["Ticket_Promedio_USD"] = (
        mensual["Facturacion_USD"] / mensual["Operaciones"]
    ).round(0)
    mensual["Facturacion_USD"] = mensual["Facturacion_USD"].round(0)
    mensual["Dolar_Promedio"]  = mensual["Dolar_Promedio"].round(0)

    def orden_mes(mes_es):
        meses_inv = {v: k for k, v in MESES_ES.items()}
        partes = mes_es.split(" ")
        if len(partes) == 2:
            return int(partes[1]) * 100 + meses_inv.get(partes[0], 0)
        return 0

    mensual["_orden"] = mensual["Mes"].apply(orden_mes)
    mensual = mensual.sort_values("_orden").drop(columns=["_orden"])

    crear_hoja_si_no_existe(spreadsheet, "AC Ventas Mensual")
    hoja_men = obtener_hoja(spreadsheet, "AC Ventas Mensual")

    encabezados = [
        "Mes", "Operaciones", "Facturacion USD",
        "Clientes Unicos", "Dolar Promedio", "Ticket Promedio USD"
    ]
    filas = []
    for _, r in mensual.iterrows():
        filas.append([
            r["Mes"],
            int(r["Operaciones"]),
            int(r["Facturacion_USD"]),
            int(r["Clientes_Unicos"]),
            int(r["Dolar_Promedio"]) if r["Dolar_Promedio"] > 0 else 0,
            int(r["Ticket_Promedio_USD"]),
        ])

    escribir_hoja(hoja_men, encabezados, filas)
    return True


# ── Funcion principal ─────────────────────────────────────────────────────────

def procesar_y_guardar(df_raw, cargado_por="sistemas"):
    """
    Funcion principal: valida, procesa, deduplica y guarda.
    Devuelve dict con resultado para mostrar en el dashboard.
    """
    # 1. Validar
    ok, error = validar_csv(df_raw)
    if not ok:
        return {"exito": False, "error": error}

    # 2. Procesar
    df = procesar_csv(df_raw, cargado_por=cargado_por)
    if df.empty:
        return {"exito": False, "error": "No se encontraron facturas validas (F/A o F/B) con montos positivos en USD."}

    # 3. Conectar a Sheets
    try:
        cliente = autenticar_sheets()
        spreadsheet = abrir_spreadsheet(cliente)
    except Exception as e:
        return {"exito": False, "error": f"No se pudo conectar a Google Sheets: {e}"}

    # 4. Deduplicar
    crear_hoja_si_no_existe(spreadsheet, "AC Ventas Detalle")
    hoja_det = obtener_hoja(spreadsheet, "AC Ventas Detalle")
    fechas_existentes = obtener_fechas_existentes(hoja_det)
    df_nuevo, n_dup = filtrar_duplicados(df, fechas_existentes)

    if df_nuevo.empty:
        return {
            "exito": False,
            "error": f"Todas las fechas del archivo ya estaban cargadas ({n_dup} filas duplicadas). No se agrego nada."
        }

    # 5. Guardar detalle
    n_guardadas = guardar_detalle(df_nuevo, spreadsheet)

    # 6. Recalcular mensual
    recalcular_mensual(spreadsheet)

    fecha_min  = df_nuevo["fecha_str"].min()
    fecha_max  = df_nuevo["fecha_str"].max()
    meses      = df_nuevo["mes_es"].unique().tolist()
    total_usd  = df_nuevo["neto_us"].sum()

    return {
        "exito":      True,
        "filas":      n_guardadas,
        "duplicados": n_dup,
        "fecha_min":  fecha_min,
        "fecha_max":  fecha_max,
        "meses":      meses,
        "total_usd":  total_usd,
        "error":      None,
    }
