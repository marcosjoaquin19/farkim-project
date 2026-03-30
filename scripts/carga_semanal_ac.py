# ==============================================
# Nombre:      carga_semanal_ac.py
# Descripción: Procesa el CSV semanal de Alto Cerró y lo
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

sys.path.append(os.path.dirname(__file__))

from conexion_sheets import (
    autenticar as autenticar_sheets,
    abrir_spreadsheet,
    obtener_hoja,
    escribir_hoja,
)

# Columnas requeridas en el CSV de Alto Cerró
COLUMNAS_REQUERIDAS = [
    "tipo_compr", "fecha", "precio_fin", "producto",
    "cliente", "vendedor", "dolar"
]

# Columnas opcionales (si no vienen, se rellenan con vacío)
COLUMNAS_OPCIONALES = [
    "nro_compro", "codigo_art", "cantidad",
    "cod_client", "cod_vended", "localidad", "provincia"
]

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


# ── Validación ─────────────────────────────────────────────────────────────────

def validar_csv(df):
    """
    Verifica que el CSV tenga las columnas mínimas requeridas.
    Devuelve (True, "") si es válido, (False, mensaje_error) si no.
    """
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        return False, f"Faltan columnas: {', '.join(faltantes)}"

    if len(df) == 0:
        return False, "El archivo está vacío."

    return True, ""


# ── Procesamiento ──────────────────────────────────────────────────────────────

def procesar_csv(df, cargado_por="sistemas"):
    """
    Limpia y procesa el CSV de Alto Cerró:
    - Parsea fechas
    - Filtra solo facturas válidas (F/A, F/B)
    - Excluye montos negativos (devoluciones)
    - Calcula monto USD = precio_fin / dolar
    - Agrega columnas de mes, semana y metadatos de carga
    Devuelve DataFrame limpio listo para guardar.
    """
    df = df.copy()

    # Parsear fechas (soporta "02-Jan-20" y "2026-03-15")
    for fmt in ["%d-%b-%y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            df["fecha_dt"] = pd.to_datetime(df["fecha"], format=fmt, errors="coerce")
            if df["fecha_dt"].notna().sum() > len(df) * 0.8:
                break
        except Exception:
            continue

    df = df.dropna(subset=["fecha_dt"])

    # Filtrar solo facturas (excluir notas de crédito y débito)
    if "tipo_compr" in df.columns:
        df = df[df["tipo_compr"].isin(["F/A", "F/B"])].copy()

    # Filtrar montos positivos
    df["precio_fin"] = pd.to_numeric(df["precio_fin"], errors="coerce").fillna(0)
    df = df[df["precio_fin"] > 0].copy()

    # Filtrar dólar válido
    df["dolar"] = pd.to_numeric(df["dolar"], errors="coerce").fillna(0)
    df = df[df["dolar"] > 0].copy()

    if df.empty:
        return df

    # Calcular USD
    df["monto_usd"] = (df["precio_fin"] / df["dolar"]).round(2)

    # Columnas de período
    df["anio"]    = df["fecha_dt"].dt.year
    df["mes_num"] = df["fecha_dt"].dt.month
    df["mes_es"]  = df.apply(lambda r: f"{MESES_ES[r['mes_num']]} {r['anio']}", axis=1)
    df["dia"]     = df["fecha_dt"].dt.day
    df["semana_num"] = df["dia"].apply(lambda d: ((d - 1) // 7) + 1)
    df["semana_label"] = df["semana_num"].apply(lambda n: f"Semana {n}")
    df["fecha_str"] = df["fecha_dt"].dt.strftime("%Y-%m-%d")

    # Metadatos de carga
    df["cargado_el"]  = datetime.now().strftime("%Y-%m-%d %H:%M")
    df["cargado_por"] = cargado_por

    return df


# ── Deduplicación ──────────────────────────────────────────────────────────────

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
    Elimina del df_nuevo las filas cuya fecha ya está en Sheets.
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
    Primero crea la hoja con encabezados si no existe.
    """
    crear_hoja_si_no_existe(spreadsheet, "AC Ventas Detalle")
    hoja = obtener_hoja(spreadsheet, "AC Ventas Detalle")

    encabezados = [
        "Fecha", "Mes", "Semana", "Producto",
        "Cliente", "Vendedor", "Localidad", "Provincia",
        "Monto ARS", "Dolar", "Monto USD",
        "Cargado el", "Cargado por"
    ]

    # Si la hoja está vacía, escribir encabezados primero
    datos_actuales = hoja.get_all_values()
    if len(datos_actuales) == 0:
        hoja.append_row(encabezados)

    # Armar filas nuevas
    filas_nuevas = []
    for _, r in df.iterrows():
        filas_nuevas.append([
            r["fecha_str"],
            r["mes_es"],
            r["semana_label"],
            str(r.get("producto", "")),
            str(r.get("cliente", "")),
            str(r.get("vendedor", "")),
            str(r.get("localidad", "")),
            str(r.get("provincia", "")),
            round(float(r["precio_fin"]), 2),
            round(float(r["dolar"]), 2),
            round(float(r["monto_usd"]), 2),
            r["cargado_el"],
            r["cargado_por"],
        ])

    if filas_nuevas:
        hoja.append_rows(filas_nuevas, value_input_option="USER_ENTERED")

    return len(filas_nuevas)


def recalcular_mensual(spreadsheet):
    """
    Lee 'AC Ventas Detalle' completo y recalcula 'AC Ventas Mensual'.
    Un registro por mes con: Mes, Operaciones, Facturación USD, Clientes únicos,
    Dólar promedio, Ticket promedio.
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
        Operaciones      =("Monto USD", "count"),
        Facturacion_USD  =("Monto USD", "sum"),
        Clientes_Unicos  =("Cliente",   "nunique"),
        Dolar_Promedio   =("Dolar",     "mean"),
    ).reset_index()

    mensual["Ticket_Promedio_USD"] = (
        mensual["Facturacion_USD"] / mensual["Operaciones"]
    ).round(0)
    mensual["Facturacion_USD"]  = mensual["Facturacion_USD"].round(0)
    mensual["Dolar_Promedio"]   = mensual["Dolar_Promedio"].round(0)

    # Ordenar cronológicamente usando el número de mes implícito
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
            int(r["Dolar_Promedio"]),
            int(r["Ticket_Promedio_USD"]),
        ])

    escribir_hoja(hoja_men, encabezados, filas)
    return True


# ── Función principal para llamar desde app.py ────────────────────────────────

def procesar_y_guardar(df_raw, cargado_por="sistemas"):
    """
    Función principal: valida, procesa, deduplica y guarda.
    Devuelve dict con resultado para mostrar en el dashboard.
    """
    # 1. Validar
    ok, error = validar_csv(df_raw)
    if not ok:
        return {"exito": False, "error": error}

    # 2. Procesar
    df = procesar_csv(df_raw, cargado_por=cargado_por)
    if df.empty:
        return {"exito": False, "error": "No se encontraron facturas válidas (F/A o F/B) en el archivo."}

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
            "error": f"Todas las fechas del archivo ya estaban cargadas ({n_dup} filas duplicadas). No se agregó nada."
        }

    # 5. Guardar detalle
    n_guardadas = guardar_detalle(df_nuevo, spreadsheet)

    # 6. Recalcular mensual
    recalcular_mensual(spreadsheet)

    # Rango de fechas del archivo cargado
    fecha_min = df_nuevo["fecha_str"].min()
    fecha_max = df_nuevo["fecha_str"].max()
    meses = df_nuevo["mes_es"].unique().tolist()
    total_usd = df_nuevo["monto_usd"].sum()

    return {
        "exito":       True,
        "filas":       n_guardadas,
        "duplicados":  n_dup,
        "fecha_min":   fecha_min,
        "fecha_max":   fecha_max,
        "meses":       meses,
        "total_usd":   total_usd,
        "error":       None,
    }
