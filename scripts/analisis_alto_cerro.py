# ==============================================
# Nombre:      analisis_alto_cerro.py
# Descripción: Procesa el archivo Excel de ventas de Alto Cerró
#              (e_xls.xls, 16.383 registros) y carga los análisis
#              en 6 hojas de Google Sheets.
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-17
# Datos:       e_xls.xls + listado_clientes_xls.xls (para provincias)
# Hojas destino:
#   - AC - Top Clientes
#   - AC - Top Productos
#   - AC - Por Vendedor
#   - AC - Por Zona
#   - AC - Recurrencia
#   - AC - Por Provincia
# ==============================================

import pandas as pd       # Para procesar tablas de datos
import os                 # Para construir rutas de archivos
import sys                # Para importar módulos desde scripts/
from datetime import datetime

# ----------------------------------------------
# Agregar la carpeta scripts/ al path de Python
# para poder importar conexion_sheets
# ----------------------------------------------
sys.path.append(os.path.dirname(__file__))

from conexion_sheets import (
    autenticar as autenticar_sheets,
    abrir_spreadsheet,
    obtener_hoja,
    escribir_hoja,
    registrar_error
)

# ----------------------------------------------
# Rutas a los archivos Excel
# ----------------------------------------------
# Subimos un nivel desde scripts/ para llegar a data/
RUTA_BASE = os.path.join(os.path.dirname(__file__), "..", "data")
ARCHIVO_VENTAS   = os.path.join(RUTA_BASE, "e_xls.xls")
ARCHIVO_CLIENTES = os.path.join(RUTA_BASE, "listado_clientes_xls.xls")


def leer_ventas():
    """
    Lee el archivo e_xls.xls con el historial de ventas de Alto Cerró.
    Renombra las columnas a nombres legibles en español.
    Filtra solo registros con importe positivo (excluye devoluciones).

    Devuelve un DataFrame de pandas o None si falla.
    """
    print(f"Leyendo archivo de ventas: {os.path.basename(ARCHIVO_VENTAS)}")

    try:
        # pd.read_excel() lee el archivo XLS y lo convierte en un DataFrame
        # engine='xlrd' es necesario para archivos .xls (formato antiguo de Excel)
        df = pd.read_excel(ARCHIVO_VENTAS, engine="xlrd")

        # Renombrar columnas para que sean más fáciles de leer
        # El diccionario mapea nombre original → nombre nuevo
        df = df.rename(columns={
            "kx_codigo":  "codigo_cliente",
            "kx_concmov": "cliente",
            "kx_codvend": "codigo_vendedor",
            "kx_lote":    "vendedor",
            "kx_codarti": "codigo_producto",
            "ar_descrip": "producto",
            "kx_cantmov": "cantidad",
            "importe":    "importe",
            "cajas":      "cajas",
            "canal":      "canal",
            "ca_descrip": "descripcion_canal",
            "c_zona":     "zona",
        })

        # Asegurarnos que importe sea numérico (a veces viene como texto)
        df["importe"] = pd.to_numeric(df["importe"], errors="coerce").fillna(0)

        # Filtrar solo ventas positivas — excluir devoluciones y refacturaciones
        # Los registros negativos son ajustes contables, no ventas reales
        total_original = len(df)
        df = df[df["importe"] > 0]

        print(f"  Registros totales:   {total_original}")
        print(f"  Ventas positivas:    {len(df)}")
        print(f"  Excluidos (neg/0):   {total_original - len(df)}")

        return df

    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo {ARCHIVO_VENTAS}")
        return None
    except Exception as e:
        print(f"ERROR al leer ventas: {e}")
        return None


def leer_clientes():
    """
    Lee el listado_clientes_xls.xls que tiene los datos maestros de clientes,
    incluyendo la provincia de cada uno.
    Solo necesitamos las columnas de código, nombre y provincia.

    Devuelve un DataFrame o None si falla.
    """
    print(f"Leyendo archivo de clientes: {os.path.basename(ARCHIVO_CLIENTES)}")

    try:
        df = pd.read_excel(ARCHIVO_CLIENTES, engine="xlrd")

        # Solo nos quedamos con las columnas que necesitamos
        df = df[["cl_codigo", "cl_nombre", "pc_descrip"]].rename(columns={
            "cl_codigo":  "codigo_cliente",
            "cl_nombre":  "nombre_cliente",
            "pc_descrip": "provincia",
        })

        # Limpiar espacios y convertir a mayúsculas para que el cruce funcione bien
        df["codigo_cliente"] = df["codigo_cliente"].astype(str).str.strip()
        df["provincia"] = df["provincia"].astype(str).str.strip().str.upper()

        print(f"  Clientes en el maestro: {len(df)}")
        return df

    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo {ARCHIVO_CLIENTES}")
        return None
    except Exception as e:
        print(f"ERROR al leer clientes: {e}")
        return None


def analisis_top_clientes(df, top=30):
    """
    Calcula el ranking de clientes por importe total vendido.
    Muestra los 30 más importantes (se puede cambiar con el parámetro top).

    Devuelve un DataFrame con columnas: Rank, Cliente, Total ARS, Transacciones
    """
    # groupby() agrupa todas las filas del mismo cliente
    # agg() calcula varias métricas de cada grupo a la vez
    resultado = (
        df.groupby("cliente")
        .agg(
            total_ars=("importe", "sum"),           # Suma de todos sus importes
            transacciones=("importe", "count"),      # Cantidad de líneas de venta
        )
        .reset_index()                               # Convierte el índice en columna
        .sort_values("total_ars", ascending=False)   # Ordena de mayor a menor
        .head(top)                                   # Toma solo los primeros 'top'
        .reset_index(drop=True)                      # Resetea el índice para el ranking
    )

    # Agregar columna de ranking (empieza en 1, no en 0)
    resultado.insert(0, "Rank", range(1, len(resultado) + 1))

    resultado = resultado.rename(columns={
        "cliente":      "Cliente",
        "total_ars":    "Total ARS",
        "transacciones": "Transacciones",
    })

    # Redondear importes a 2 decimales
    resultado["Total ARS"] = resultado["Total ARS"].round(2)

    return resultado


def analisis_top_productos(df, top=30):
    """
    Ranking de productos más vendidos por importe total.
    """
    resultado = (
        df.groupby("producto")
        .agg(
            total_ars=("importe", "sum"),
            unidades=("cantidad", "sum"),
            transacciones=("importe", "count"),
        )
        .reset_index()
        .sort_values("total_ars", ascending=False)
        .head(top)
        .reset_index(drop=True)
    )

    resultado.insert(0, "Rank", range(1, len(resultado) + 1))

    resultado = resultado.rename(columns={
        "producto":      "Producto",
        "total_ars":     "Total ARS",
        "unidades":      "Unidades",
        "transacciones": "Transacciones",
    })

    resultado["Total ARS"] = resultado["Total ARS"].round(2)
    resultado["Unidades"]  = resultado["Unidades"].round(0)

    return resultado


def analisis_por_vendedor(df):
    """
    Resumen de ventas por vendedor: total, transacciones y ticket promedio.
    El ticket promedio = cuánto vende en promedio por transacción.
    """
    resultado = (
        df.groupby("vendedor")
        .agg(
            total_ars=("importe", "sum"),
            transacciones=("importe", "count"),
        )
        .reset_index()
        .sort_values("total_ars", ascending=False)
        .reset_index(drop=True)
    )

    # Ticket promedio = total dividido cantidad de transacciones
    resultado["ticket_promedio"] = (
        resultado["total_ars"] / resultado["transacciones"]
    ).round(2)

    resultado = resultado.rename(columns={
        "vendedor":       "Vendedor",
        "total_ars":      "Total ARS",
        "transacciones":  "Transacciones",
        "ticket_promedio": "Ticket Promedio ARS",
    })

    resultado["Total ARS"] = resultado["Total ARS"].round(2)

    return resultado


def analisis_por_zona(df):
    """
    Ventas agrupadas por zona geográfica.
    """
    resultado = (
        df.groupby("zona")
        .agg(
            total_ars=("importe", "sum"),
            clientes_unicos=("cliente", "nunique"),   # nunique = contar únicos
            transacciones=("importe", "count"),
        )
        .reset_index()
        .sort_values("total_ars", ascending=False)
        .reset_index(drop=True)
    )

    resultado = resultado.rename(columns={
        "zona":            "Zona",
        "total_ars":       "Total ARS",
        "clientes_unicos": "Clientes Únicos",
        "transacciones":   "Transacciones",
    })

    resultado["Total ARS"] = resultado["Total ARS"].round(2)

    return resultado


def analisis_recurrencia(df):
    """
    Analiza cuántas veces compró cada cliente (recurrencia).
    Clasifica en: Único (1 vez), Ocasional (2-4), Recurrente (5-9), VIP (10+)

    Este análisis es importante para el modelo de churn:
    los clientes VIP que dejan de comprar son una alerta crítica.
    """
    # Contar cuántas transacciones tiene cada cliente
    recurrencia = (
        df.groupby("cliente")
        .agg(
            total_ars=("importe", "sum"),
            compras=("importe", "count"),
        )
        .reset_index()
    )

    # Clasificar cada cliente según su cantidad de compras
    def clasificar(n):
        if n == 1:
            return "Único (1 compra)"
        elif n <= 4:
            return "Ocasional (2-4)"
        elif n <= 9:
            return "Recurrente (5-9)"
        else:
            return "VIP (10+)"

    # apply() ejecuta la función clasificar() en cada fila de la columna "compras"
    recurrencia["segmento"] = recurrencia["compras"].apply(clasificar)

    # Ordenar por total vendido
    recurrencia = recurrencia.sort_values("total_ars", ascending=False).reset_index(drop=True)

    recurrencia = recurrencia.rename(columns={
        "cliente":  "Cliente",
        "total_ars": "Total ARS",
        "compras":  "Cantidad Compras",
        "segmento": "Segmento",
    })

    recurrencia["Total ARS"] = recurrencia["Total ARS"].round(2)

    return recurrencia


def analisis_por_provincia(df_ventas, df_clientes):
    """
    Cruza las ventas con el maestro de clientes para obtener la provincia
    de cada cliente y agrupa las ventas por provincia.

    Usa merge() de pandas — es como un JOIN de SQL:
    toma df_ventas y agrega la columna 'provincia' desde df_clientes
    usando 'codigo_cliente' como clave de cruce.
    """
    # Aseguramos que los códigos tengan el mismo formato antes de cruzar
    df_ventas = df_ventas.copy()
    df_ventas["codigo_cliente"] = df_ventas["codigo_cliente"].astype(str).str.strip()

    # merge() combina dos DataFrames por una columna en común
    # how='left' = todos los registros de ventas se mantienen,
    # aunque no encuentren provincia (quedan como NaN)
    df_cruzado = df_ventas.merge(
        df_clientes[["codigo_cliente", "provincia"]],
        on="codigo_cliente",
        how="left"
    )

    # Reemplazar provincias vacías con "Sin provincia"
    df_cruzado["provincia"] = df_cruzado["provincia"].fillna("Sin provincia")

    resultado = (
        df_cruzado.groupby("provincia")
        .agg(
            total_ars=("importe", "sum"),
            clientes_unicos=("cliente", "nunique"),
            transacciones=("importe", "count"),
        )
        .reset_index()
        .sort_values("total_ars", ascending=False)
        .reset_index(drop=True)
    )

    resultado = resultado.rename(columns={
        "provincia":       "Provincia",
        "total_ars":       "Total ARS",
        "clientes_unicos": "Clientes Únicos",
        "transacciones":   "Transacciones",
    })

    resultado["Total ARS"] = resultado["Total ARS"].round(2)

    return resultado


def cargar_analisis(spreadsheet, nombre_hoja, df):
    """
    Carga un DataFrame en una hoja específica de Google Sheets.
    Muestra un resumen de cuántas filas se cargaron.
    """
    hoja = obtener_hoja(spreadsheet, nombre_hoja)
    if hoja is None:
        registrar_error(spreadsheet, "analisis_alto_cerro.py",
                        f"Hoja '{nombre_hoja}' no encontrada")
        return False

    encabezados = list(df.columns)
    filas = df.fillna("").values.tolist()
    escribir_hoja(hoja, encabezados, filas)
    return True


def main():
    """
    Función principal: ejecuta todos los análisis de Alto Cerró
    y los carga en Google Sheets.
    """
    print("=" * 55)
    print("  ANÁLISIS ALTO CERRÓ — FARKIM")
    print("=" * 55)
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # ── PASO 1: Leer archivos Excel ──────────────────────
    print("\n[1/4] Leyendo archivos Excel...")
    df_ventas = leer_ventas()
    if df_ventas is None:
        return

    df_clientes = leer_clientes()
    if df_clientes is None:
        return

    # ── PASO 2: Conectar a Google Sheets ────────────────
    print("\n[2/4] Conectando a Google Sheets...")
    cliente_sheets = autenticar_sheets()
    if cliente_sheets is None:
        return

    spreadsheet = abrir_spreadsheet(cliente_sheets)
    if spreadsheet is None:
        return

    # ── PASO 3: Calcular los 6 análisis ─────────────────
    print("\n[3/4] Calculando análisis...")

    print("  → Top Clientes...")
    df_top_clientes = analisis_top_clientes(df_ventas)

    print("  → Top Productos...")
    df_top_productos = analisis_top_productos(df_ventas)

    print("  → Por Vendedor...")
    df_vendedor = analisis_por_vendedor(df_ventas)

    print("  → Por Zona...")
    df_zona = analisis_por_zona(df_ventas)

    print("  → Recurrencia de clientes...")
    df_recurrencia = analisis_recurrencia(df_ventas)

    print("  → Por Provincia...")
    df_provincia = analisis_por_provincia(df_ventas, df_clientes)

    # ── PASO 4: Cargar en Google Sheets ─────────────────
    print("\n[4/4] Cargando en Google Sheets...")

    analisis = [
        ("AC - Top Clientes",  df_top_clientes),
        ("AC - Top Productos", df_top_productos),
        ("AC - Por Vendedor",  df_vendedor),
        ("AC - Por Zona",      df_zona),
        ("AC - Recurrencia",   df_recurrencia),
        ("AC - Por Provincia", df_provincia),
    ]

    errores = 0
    for nombre_hoja, df in analisis:
        print(f"  → Cargando '{nombre_hoja}'...")
        exito = cargar_analisis(spreadsheet, nombre_hoja, df)
        if not exito:
            errores += 1

    # ── Resumen final ────────────────────────────────────
    print("\n" + "=" * 55)
    if errores == 0:
        print("  PROCESO COMPLETADO EXITOSAMENTE")
    else:
        print(f"  COMPLETADO CON {errores} ERROR(ES)")
    print("=" * 55)
    print(f"  Registros de ventas procesados: {len(df_ventas):,}")
    print(f"  Clientes únicos:  {df_ventas['cliente'].nunique():,}")
    print(f"  Vendedores:       {df_ventas['vendedor'].nunique():,}")
    print(f"  Total facturado:  ${df_ventas['importe'].sum():,.0f} ARS")
    print(f"  Hojas actualizadas: {len(analisis) - errores}/6")


if __name__ == "__main__":
    main()
