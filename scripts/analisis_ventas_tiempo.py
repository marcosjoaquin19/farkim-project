# ==============================================
# Nombre:      analisis_ventas_tiempo.py
# Descripción: Extrae el pipeline de Odoo y calcula la evolución
#              de oportunidades y montos por mes y por semana.
#              Hojas destino: "Ventas por Mes USD" y "Ventas por Semana USD"
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-19
# ==============================================

import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Agregamos la carpeta scripts/ al path para poder importar los módulos
sys.path.append(os.path.dirname(__file__))

# Importamos las conexiones ya creadas
from conexion_odoo import autenticar
from conexion_sheets import (
    autenticar as autenticar_sheets,
    abrir_spreadsheet,
    obtener_hoja,
    escribir_hoja,
    registrar_error
)

# Reutilizamos la extracción y conversión del pipeline
from analisis_pipeline import extraer_pipeline, procesar_pipeline


def calcular_ventas_por_mes(df):
    """
    Agrupa las oportunidades por mes de creación y calcula:
      - Cantidad total de oportunidades creadas ese mes
      - Monto total en USD
      - Monto promedio por oportunidad
      - Cantidad de activas, en riesgo e inactivas
      - Monto acumulado (suma de todos los meses hasta ese punto)

    Devuelve un DataFrame con una fila por mes, ordenado cronológicamente.
    """
    print("Calculando ventas por mes...")

    # Convertimos la fecha de creación a formato datetime para poder agrupar por mes
    df["Fecha Creación"] = pd.to_datetime(df["Fecha Creación"], errors="coerce")

    # Creamos una columna con el mes en formato "YYYY-MM" (ej: "2025-10")
    df["Mes"] = df["Fecha Creación"].dt.to_period("M").astype(str)

    # Agrupamos por mes y calculamos las métricas
    por_mes = df.groupby("Mes").agg(
        oportunidades     = ("Oportunidad", "count"),
        monto_total_usd   = ("Monto USD", "sum"),
        monto_promedio    = ("Monto USD", "mean"),
        cant_activas      = ("Estado", lambda x: (x == "Activa").sum()),
        cant_en_riesgo    = ("Estado", lambda x: (x == "En riesgo").sum()),
        cant_inactivas    = ("Estado", lambda x: (x == "Inactiva").sum()),
    ).reset_index()

    # Redondeamos los montos para que se vean prolijos en Sheets
    por_mes["monto_total_usd"] = por_mes["monto_total_usd"].round(0)
    por_mes["monto_promedio"]  = por_mes["monto_promedio"].round(0)

    # Calculamos el monto acumulado mes a mes
    # cumsum() hace la suma acumulada — si en oct hay $100 y en nov $50, nov acumula $150
    por_mes["monto_acumulado_usd"] = por_mes["monto_total_usd"].cumsum().round(0)

    # Renombramos las columnas para que sean claras en el dashboard
    por_mes = por_mes.rename(columns={
        "Mes":                 "Mes",
        "oportunidades":       "Oportunidades Creadas",
        "monto_total_usd":     "Monto Total USD",
        "monto_promedio":      "Ticket Promedio USD",
        "cant_activas":        "Activas",
        "cant_en_riesgo":      "En Riesgo",
        "cant_inactivas":      "Inactivas",
        "monto_acumulado_usd": "Monto Acumulado USD",
    })

    # Ordenamos cronológicamente (más viejo primero)
    por_mes = por_mes.sort_values("Mes")

    print(f"Meses encontrados: {len(por_mes)}")
    for _, row in por_mes.iterrows():
        print(f"  {row['Mes']}  →  {row['Oportunidades Creadas']:>3} oportunidades  —  ${row['Monto Total USD']:>10,.0f} USD")

    return por_mes


def calcular_ventas_por_semana(df):
    """
    Agrupa las oportunidades por semana de creación y calcula:
      - Cantidad de oportunidades creadas esa semana
      - Monto total en USD
      - Monto promedio por oportunidad
      - Fecha de inicio de la semana (lunes)

    Devuelve un DataFrame con una fila por semana, ordenado cronológicamente.
    Solo muestra las últimas 16 semanas para que el gráfico sea legible.
    """
    print("Calculando ventas por semana...")

    # Convertimos la fecha a datetime si no lo es ya
    df["Fecha Creación"] = pd.to_datetime(df["Fecha Creación"], errors="coerce")

    # Creamos una columna con el lunes de esa semana
    # dt.to_period("W") agrupa por semana y .start_time da el lunes de esa semana
    df["Semana Inicio"] = df["Fecha Creación"].dt.to_period("W").apply(lambda x: x.start_time.strftime("%Y-%m-%d") if pd.notna(x) else "")

    # Filtramos las filas donde la fecha es válida
    df_valido = df[df["Semana Inicio"] != ""]

    # Agrupamos por semana
    por_semana = df_valido.groupby("Semana Inicio").agg(
        oportunidades   = ("Oportunidad", "count"),
        monto_total_usd = ("Monto USD", "sum"),
        monto_promedio  = ("Monto USD", "mean"),
    ).reset_index()

    # Redondeamos montos
    por_semana["monto_total_usd"] = por_semana["monto_total_usd"].round(0)
    por_semana["monto_promedio"]  = por_semana["monto_promedio"].round(0)

    # Ordenamos cronológicamente
    por_semana = por_semana.sort_values("Semana Inicio")

    # Renombramos las columnas
    por_semana = por_semana.rename(columns={
        "Semana Inicio":   "Semana (Lunes)",
        "oportunidades":   "Oportunidades",
        "monto_total_usd": "Monto Total USD",
        "monto_promedio":  "Ticket Promedio USD",
    })

    print(f"Semanas encontradas: {len(por_semana)}")
    for _, row in por_semana.iterrows():
        print(f"  Sem. {row['Semana (Lunes)']}  →  {row['Oportunidades']:>3} ops  —  ${row['Monto Total USD']:>10,.0f} USD")

    return por_semana


def cargar_a_sheets(df_mes, df_semana, spreadsheet):
    """
    Carga los dos DataFrames en sus respectivas hojas de Google Sheets.
    Devuelve True si ambas cargas son exitosas.
    """
    print("Cargando datos en Google Sheets...")
    exitos = 0

    # ── Hoja "Ventas por Mes USD" ─────────────────────
    hoja_mes = obtener_hoja(spreadsheet, "Ventas por Mes USD")
    if hoja_mes:
        escribir_hoja(hoja_mes, list(df_mes.columns), df_mes.fillna("").values.tolist())
        print("  → 'Ventas por Mes USD' actualizada")
        exitos += 1
    else:
        registrar_error(spreadsheet, "analisis_ventas_tiempo.py", "Hoja 'Ventas por Mes USD' no encontrada")

    # ── Hoja "Ventas por Semana USD" ──────────────────
    hoja_semana = obtener_hoja(spreadsheet, "Ventas por Semana USD")
    if hoja_semana:
        escribir_hoja(hoja_semana, list(df_semana.columns), df_semana.fillna("").values.tolist())
        print("  → 'Ventas por Semana USD' actualizada")
        exitos += 1
    else:
        registrar_error(spreadsheet, "analisis_ventas_tiempo.py", "Hoja 'Ventas por Semana USD' no encontrada")

    return exitos == 2


def main():
    """
    Función principal: extrae el pipeline de Odoo y genera los análisis
    de evolución temporal por mes y por semana.
    """
    print("=" * 55)
    print("  EVOLUCIÓN DE VENTAS EN EL TIEMPO — FARKIM")
    print("=" * 55)
    print(f"  Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # ── PASO 1: Conectar a Odoo ──────────────────────────
    print("\n[1/4] Conectando a Odoo...")
    uid = autenticar()
    if uid is None:
        print("FALLO: No se pudo conectar a Odoo. Proceso cancelado.")
        return

    # ── PASO 2: Conectar a Google Sheets ────────────────
    print("\n[2/4] Conectando a Google Sheets...")
    cliente_sheets = autenticar_sheets()
    if cliente_sheets is None:
        print("FALLO: No se pudo conectar a Google Sheets. Proceso cancelado.")
        return

    spreadsheet = abrir_spreadsheet(cliente_sheets)
    if spreadsheet is None:
        return

    # ── PASO 3: Extraer pipeline y calcular por tiempo ──
    print("\n[3/4] Extrayendo pipeline y calculando evolución temporal...")
    oportunidades = extraer_pipeline(uid)

    if not oportunidades:
        mensaje = "No se obtuvieron oportunidades de Odoo"
        print(f"FALLO: {mensaje}")
        registrar_error(spreadsheet, "analisis_ventas_tiempo.py", mensaje)
        return

    df_pipeline = procesar_pipeline(oportunidades)
    df_mes      = calcular_ventas_por_mes(df_pipeline.copy())
    df_semana   = calcular_ventas_por_semana(df_pipeline.copy())

    # ── PASO 4: Cargar en Google Sheets ─────────────────
    print("\n[4/4] Cargando en Google Sheets...")
    exito = cargar_a_sheets(df_mes, df_semana, spreadsheet)

    if exito:
        mes_top = df_mes.loc[df_mes["Monto Total USD"].idxmax()]
        print("\n" + "=" * 55)
        print("  PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 55)
        print(f"  Meses cargados:   {len(df_mes)}")
        print(f"  Semanas cargadas: {len(df_semana)}")
        print(f"  Mes con más monto: {mes_top['Mes']} — ${mes_top['Monto Total USD']:,.0f} USD")
        print(f"  Monto acumulado total: ${df_mes['Monto Acumulado USD'].iloc[-1]:,.0f} USD")
    else:
        registrar_error(spreadsheet, "analisis_ventas_tiempo.py", "Error al cargar en Sheets")


if __name__ == "__main__":
    main()
