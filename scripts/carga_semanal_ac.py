# ==============================================
# Nombre:      carga_semanal_ac.py
# Descripcion: Procesa el Excel semanal de Alto Cerro y lo
#              guarda en Google Sheets hoja "AC Ventas Detalle".
#              Modo ACUMULATIVO: cada archivo reemplaza el mes completo.
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

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# Columnas requeridas en el Excel de Alto Cerro
COLUMNAS_REQUERIDAS = [
    "kx_tipfac", "iv_feccte", "neto_us",
    "iv_nombre", "ve_nombre"
]


# ── Lectura del archivo ─────────────────────────────────────────────────────────

def leer_archivo(archivo_bytes, nombre_archivo):
    """
    Lee el archivo subido (XLS, XLSX o CSV).
    Para Excel: detecta automaticamente la hoja con datos reales
    (la que empieza con 'ventas_'). Usa header=1 por la fila vacia inicial.
    Si hay varias hojas ventas_, usa la que tiene mas filas.
    Devuelve DataFrame o None si falla.
    """
    nombre = nombre_archivo.lower()
    try:
        if nombre.endswith(".csv"):
            return pd.read_csv(io.BytesIO(archivo_bytes))

        engine = "xlrd" if nombre.endswith(".xls") else "openpyxl"
        xl = pd.ExcelFile(io.BytesIO(archivo_bytes), engine=engine)

        # Buscar hojas que comiencen con 'ventas_'
        hojas_datos = [h for h in xl.sheet_names if h.lower().startswith("ventas_")]

        if not hojas_datos:
            # Si no hay ninguna con ese prefijo, usar la primera hoja no vacia
            hojas_datos = xl.sheet_names

        # Leer todas las hojas candidatas y quedarse con la de mas filas
        mejor_df = None
        mejor_filas = 0
        for hoja in hojas_datos:
            try:
                df = pd.read_excel(
                    io.BytesIO(archivo_bytes),
                    sheet_name=hoja,
                    header=1,       # fila 0 vacia, fila 1 = encabezados
                    engine=engine,
                )
                filas_validas = len(df.dropna(how="all"))
                if filas_validas > mejor_filas:
                    mejor_filas = filas_validas
                    mejor_df = df
            except Exception:
                continue

        return mejor_df

    except Exception as e:
        return None


# ── Validacion ─────────────────────────────────────────────────────────────────

def validar_df(df):
    """
    Verifica que el DataFrame tenga las columnas minimas requeridas.
    Devuelve (True, "") si es valido, (False, mensaje) si no.
    """
    if df is None:
        return False, "No se pudo leer el archivo."
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        return False, f"Faltan columnas: {', '.join(faltantes)}"
    if len(df.dropna(how="all")) == 0:
        return False, "El archivo no tiene datos."
    return True, ""


# ── Procesamiento ──────────────────────────────────────────────────────────────

def procesar_df(df, cargado_por="sistemas"):
    """
    Limpia y procesa el DataFrame:
    - Parsea fechas desde iv_feccte
    - Filtra solo F/A y F/B
    - Excluye montos negativos o cero en neto_us
    - Agrega columnas de mes, semana y metadatos
    Devuelve DataFrame limpio.
    """
    df = df.copy()

    df["fecha_dt"] = pd.to_datetime(df["iv_feccte"], errors="coerce")
    df = df.dropna(subset=["fecha_dt"])

    df = df[df["kx_tipfac"].isin(["F/A", "F/B"])].copy()

    df["neto_us"] = pd.to_numeric(df["neto_us"], errors="coerce").fillna(0)
    df = df[df["neto_us"] > 0].copy()

    if df.empty:
        return df

    if "us_dia" in df.columns:
        df["us_dia"] = pd.to_numeric(df["us_dia"], errors="coerce").fillna(0)
    else:
        df["us_dia"] = 0

    df["anio"]         = df["fecha_dt"].dt.year
    df["mes_num"]      = df["fecha_dt"].dt.month
    df["mes_es"]       = df.apply(lambda r: f"{MESES_ES[r['mes_num']]} {r['anio']}", axis=1)
    df["dia"]          = df["fecha_dt"].dt.day
    df["semana_num"]   = df["dia"].apply(lambda d: ((d - 1) // 7) + 1)
    df["semana_label"] = df["semana_num"].apply(lambda n: f"Semana {n}")
    df["fecha_str"]    = df["fecha_dt"].dt.strftime("%Y-%m-%d")
    df["cargado_el"]   = datetime.now().strftime("%Y-%m-%d %H:%M")
    df["cargado_por"]  = cargado_por

    return df


# ── Google Sheets ──────────────────────────────────────────────────────────────

def crear_hoja_si_no_existe(spreadsheet, nombre, filas=5000, cols=20):
    hojas = [h.title for h in spreadsheet.worksheets()]
    if nombre not in hojas:
        spreadsheet.add_worksheet(title=nombre, rows=filas, cols=cols)


ENCABEZADOS_DETALLE = [
    "Fecha", "Mes", "Semana",
    "Producto", "Cliente", "Vendedor",
    "Monto USD", "Dolar",
    "Cargado el", "Cargado por"
]


def guardar_con_reemplazo(df_nuevo, spreadsheet):
    """
    Modo acumulativo: reemplaza TODOS los registros de los meses
    presentes en df_nuevo con los datos nuevos.
    Pasos:
      1. Leer todo lo existente en 'AC Ventas Detalle'
      2. Eliminar filas de los meses que trae el nuevo archivo
      3. Agregar las filas nuevas
      4. Reescribir la hoja completa
    Devuelve cantidad de filas escritas para esos meses.
    """
    crear_hoja_si_no_existe(spreadsheet, "AC Ventas Detalle")
    hoja = obtener_hoja(spreadsheet, "AC Ventas Detalle")

    meses_nuevos = set(df_nuevo["mes_es"].unique())

    # Leer datos existentes
    datos_actuales = hoja.get_all_records()
    df_actual = pd.DataFrame(datos_actuales) if datos_actuales else pd.DataFrame()

    # Conservar solo los meses que NO trae el nuevo archivo
    if not df_actual.empty and "Mes" in df_actual.columns:
        df_conservar = df_actual[~df_actual["Mes"].isin(meses_nuevos)]
    else:
        df_conservar = pd.DataFrame()

    # Armar filas nuevas
    filas_nuevas = []
    for _, r in df_nuevo.iterrows():
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

    # Reescribir hoja: encabezados + filas conservadas + filas nuevas
    todas_las_filas = []
    if not df_conservar.empty:
        for _, row in df_conservar.iterrows():
            todas_las_filas.append([str(row.get(col, "")) for col in ENCABEZADOS_DETALLE])

    todas_las_filas.extend(filas_nuevas)

    hoja.clear()
    hoja.append_row(ENCABEZADOS_DETALLE)
    if todas_las_filas:
        hoja.append_rows(todas_las_filas, value_input_option="USER_ENTERED")

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

    meses_inv = {v: k for k, v in MESES_ES.items()}
    def orden_mes(mes_es):
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
    Funcion principal: valida, procesa y guarda en modo acumulativo.
    Devuelve dict con resultado para mostrar en el dashboard.
    """
    # 1. Validar
    ok, error = validar_df(df_raw)
    if not ok:
        return {"exito": False, "error": error}

    # 2. Procesar
    df = procesar_df(df_raw, cargado_por=cargado_por)
    if df.empty:
        return {"exito": False, "error": "No se encontraron facturas validas (F/A o F/B) con montos positivos."}

    # 3. Conectar a Sheets
    try:
        cliente = autenticar_sheets()
        spreadsheet = abrir_spreadsheet(cliente)
    except Exception as e:
        return {"exito": False, "error": f"No se pudo conectar a Google Sheets: {e}"}

    # 4. Guardar reemplazando el mes
    n_guardadas = guardar_con_reemplazo(df, spreadsheet)

    # 5. Recalcular mensual
    recalcular_mensual(spreadsheet)

    return {
        "exito":      True,
        "filas":      n_guardadas,
        "duplicados": 0,
        "fecha_min":  df["fecha_str"].min(),
        "fecha_max":  df["fecha_str"].max(),
        "meses":      df["mes_es"].unique().tolist(),
        "total_usd":  df["neto_us"].sum(),
        "error":      None,
    }
