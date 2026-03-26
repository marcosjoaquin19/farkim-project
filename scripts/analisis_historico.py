# ==============================================
# Nombre:      analisis_historico.py
# Descripción: Procesa el archivo histórico de ventas de Alto Cerró
#              (2020-2026) con cotización del dólar por venta.
#              Calcula facturación mensual en USD y carga a Google Sheets.
#              Hoja destino: "Historico Mensual USD"
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-26
# Datos:       farkim_historico_ventas.csv — 54,723 registros
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
    registrar_error
)

# Ruta al archivo CSV (relativa a la raíz del proyecto)
RUTA_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "farkim_historico_ventas.csv")

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def cargar_csv():
    """Lee el CSV histórico de Alto Cerró y lo devuelve como DataFrame."""
    print("Leyendo archivo CSV histórico...")

    ruta = os.path.normpath(RUTA_CSV)
    if not os.path.exists(ruta):
        print(f"ERROR: No se encontró el archivo en {ruta}")
        return None

    df = pd.read_csv(ruta, encoding='utf-8')
    print(f"  Archivo leído: {len(df):,} registros, {len(df.columns)} columnas")
    return df


def procesar_historico(df):
    """
    Procesa el DataFrame crudo:
    - Parsea fechas
    - Filtra solo facturas (excluye notas de crédito/débito)
    - Calcula monto USD = precio_fin / dolar
    - Agrupa por mes
    """
    print("Procesando datos históricos...")

    # Parsear fechas (formato: "02-Jan-20")
    df['fecha_dt'] = pd.to_datetime(df['fecha'], format='%d-%b-%y', errors='coerce')
    nulos_fecha = df['fecha_dt'].isna().sum()
    if nulos_fecha > 0:
        print(f"  Advertencia: {nulos_fecha} registros sin fecha válida, se excluyen.")
        df = df.dropna(subset=['fecha_dt'])

    # Filtrar solo facturas (F/A y F/B) — excluir notas de crédito, débito, etc.
    facturas = df[df['tipo_compr'].isin(['F/A', 'F/B'])].copy()
    print(f"  Facturas válidas: {len(facturas):,} de {len(df):,} registros")

    # Filtrar montos positivos (excluir devoluciones)
    facturas = facturas[facturas['precio_fin'] > 0].copy()

    # Calcular monto en USD usando el dólar del día de la venta
    facturas['monto_usd'] = facturas['precio_fin'] / facturas['dolar']

    # Extraer año y mes
    facturas['anio'] = facturas['fecha_dt'].dt.year
    facturas['mes_num'] = facturas['fecha_dt'].dt.month
    facturas['periodo'] = facturas['fecha_dt'].dt.to_period('M').astype(str)  # "2020-01"

    return facturas


def agrupar_por_mes(facturas):
    """
    Agrupa las facturas por mes y calcula métricas:
    - Cantidad de operaciones
    - Facturación ARS y USD
    - Ticket promedio USD
    - Clientes únicos
    - Dólar promedio del mes
    """
    print("Agrupando por mes...")

    mensual = facturas.groupby('periodo').agg(
        operaciones=('monto_usd', 'count'),
        facturacion_ars=('precio_fin', 'sum'),
        facturacion_usd=('monto_usd', 'sum'),
        clientes_unicos=('cliente', 'nunique'),
        dolar_promedio=('dolar', 'mean'),
    ).reset_index()

    # Ticket promedio
    mensual['ticket_promedio_usd'] = mensual['facturacion_usd'] / mensual['operaciones']

    # Acumulado USD
    mensual = mensual.sort_values('periodo')
    mensual['acumulado_usd'] = mensual['facturacion_usd'].cumsum()

    # Nombre del mes en español
    mensual['mes_es'] = mensual['periodo'].apply(lambda p: f"{MESES_ES[int(p[5:7])]} {p[:4]}")

    # Redondear
    mensual['facturacion_ars'] = mensual['facturacion_ars'].round(0)
    mensual['facturacion_usd'] = mensual['facturacion_usd'].round(0)
    mensual['ticket_promedio_usd'] = mensual['ticket_promedio_usd'].round(0)
    mensual['dolar_promedio'] = mensual['dolar_promedio'].round(0)
    mensual['acumulado_usd'] = mensual['acumulado_usd'].round(0)

    print(f"  Meses procesados: {len(mensual)}")
    return mensual


def agrupar_por_anio(facturas):
    """Agrupa por año para el resumen anual."""
    print("Agrupando por año...")

    anual = facturas.groupby('anio').agg(
        operaciones=('monto_usd', 'count'),
        facturacion_usd=('monto_usd', 'sum'),
        clientes_unicos=('cliente', 'nunique'),
        productos_unicos=('producto', 'nunique'),
        dolar_promedio=('dolar', 'mean'),
    ).reset_index()

    anual['ticket_promedio_usd'] = anual['facturacion_usd'] / anual['operaciones']
    anual['facturacion_usd'] = anual['facturacion_usd'].round(0)
    anual['ticket_promedio_usd'] = anual['ticket_promedio_usd'].round(0)
    anual['dolar_promedio'] = anual['dolar_promedio'].round(0)

    return anual


def cargar_a_sheets(mensual, anual, spreadsheet):
    """Carga los datos procesados en Google Sheets."""
    print("Cargando en Google Sheets...")

    # Hoja 1: Historico Mensual USD
    hoja_mensual = obtener_hoja(spreadsheet, "Historico Mensual USD")
    if hoja_mensual:
        encabezados = ["Periodo", "Mes", "Operaciones", "Facturacion ARS",
                       "Facturacion USD", "Ticket Promedio USD",
                       "Clientes Unicos", "Dolar Promedio", "Acumulado USD"]
        filas = []
        for _, r in mensual.iterrows():
            filas.append([
                r['periodo'], r['mes_es'], int(r['operaciones']),
                int(r['facturacion_ars']), int(r['facturacion_usd']),
                int(r['ticket_promedio_usd']), int(r['clientes_unicos']),
                int(r['dolar_promedio']), int(r['acumulado_usd'])
            ])
        escribir_hoja(hoja_mensual, encabezados, filas)
        print(f"  'Historico Mensual USD': {len(filas)} meses cargados")

    # Hoja 2: Historico Anual USD
    hoja_anual = obtener_hoja(spreadsheet, "Historico Anual USD")
    if hoja_anual:
        encabezados = ["Anio", "Operaciones", "Facturacion USD",
                       "Ticket Promedio USD", "Clientes Unicos",
                       "Productos Unicos", "Dolar Promedio"]
        filas = []
        for _, r in anual.iterrows():
            filas.append([
                int(r['anio']), int(r['operaciones']), int(r['facturacion_usd']),
                int(r['ticket_promedio_usd']), int(r['clientes_unicos']),
                int(r['productos_unicos']), int(r['dolar_promedio'])
            ])
        escribir_hoja(hoja_anual, encabezados, filas)
        print(f"  'Historico Anual USD': {len(filas)} años cargados")

    return True


def main():
    print("=" * 55)
    print("  ANÁLISIS HISTÓRICO ALTO CERRÓ — FARKIM")
    print("=" * 55)
    print(f"  Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # Paso 1: Leer CSV
    print("\n[1/4] Leyendo CSV...")
    df = cargar_csv()
    if df is None:
        return

    # Paso 2: Procesar
    print("\n[2/4] Procesando datos...")
    facturas = procesar_historico(df)

    # Paso 3: Agrupar
    print("\n[3/4] Agrupando por período...")
    mensual = agrupar_por_mes(facturas)
    anual = agrupar_por_anio(facturas)

    # Mostrar resumen
    print("\n  RESUMEN POR AÑO:")
    for _, r in anual.iterrows():
        print(f"    {int(r['anio'])}: ${r['facturacion_usd']:>12,.0f} USD | {int(r['operaciones']):>6,} ops | {int(r['clientes_unicos'])} clientes")

    # Paso 4: Cargar a Sheets
    print("\n[4/4] Conectando a Google Sheets...")
    cliente_sheets = autenticar_sheets()
    if cliente_sheets is None:
        print("FALLO: No se pudo conectar a Google Sheets.")
        return

    spreadsheet = abrir_spreadsheet(cliente_sheets)
    if spreadsheet is None:
        return

    exito = cargar_a_sheets(mensual, anual, spreadsheet)

    if exito:
        print("\n" + "=" * 55)
        print("  PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 55)
        print(f"  Total facturas procesadas: {len(facturas):,}")
        print(f"  Período: {facturas['fecha_dt'].min().strftime('%Y-%m-%d')} → {facturas['fecha_dt'].max().strftime('%Y-%m-%d')}")
        print(f"  Meses cargados: {len(mensual)}")
        print(f"  Facturación total USD: ${facturas['monto_usd'].sum():,.0f}")


if __name__ == "__main__":
    main()
