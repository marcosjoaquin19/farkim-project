# ==============================================
# Nombre:      analisis_vendedores.py
# Descripción: Extrae el pipeline de Odoo y genera un resumen
#              por vendedor: cantidad de oportunidades activas,
#              en riesgo e inactivas, y montos totales en USD.
#              Hoja destino: "Por Vendedor"
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-19
# ==============================================

import pandas as pd
from datetime import datetime
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

# Importamos la función de extracción y conversión del pipeline
# Así reutilizamos exactamente la misma lógica — si algo cambia allá, cambia acá automáticamente
from analisis_pipeline import extraer_pipeline, procesar_pipeline


def calcular_resumen_por_vendedor(df):
    """
    Toma el DataFrame del pipeline ya procesado y lo agrupa por vendedor.
    Para cada vendedor calcula:
      - Cantidad de oportunidades activas, en riesgo e inactivas
      - Monto total en USD por estado
      - Monto total general en USD
      - Promedio de días sin actividad

    Devuelve un DataFrame con una fila por vendedor, ordenado por monto total descendente.
    """
    print("Calculando resumen por vendedor...")

    # Agrupamos por vendedor y estado para contar oportunidades y sumar montos
    # pivot_table es como una tabla dinámica de Excel
    tabla_cant = df.pivot_table(
        index="Vendedor",
        columns="Estado",
        values="Oportunidad",
        aggfunc="count",
        fill_value=0   # Si un vendedor no tiene inactivas, pone 0 en vez de vacío
    ).reset_index()

    # Nos aseguramos de que existan las tres columnas aunque algún vendedor no tenga ese estado
    for estado in ["Activa", "En riesgo", "Inactiva"]:
        if estado not in tabla_cant.columns:
            tabla_cant[estado] = 0

    # Renombramos las columnas para que sean más claras en Sheets
    tabla_cant = tabla_cant.rename(columns={
        "Activa":    "Cant. Activas",
        "En riesgo": "Cant. En Riesgo",
        "Inactiva":  "Cant. Inactivas"
    })

    # Ahora calculamos los montos USD por vendedor
    montos = df.groupby("Vendedor").agg(
        monto_activas   = ("Monto USD", lambda x: x[df.loc[x.index, "Estado"] == "Activa"].sum()),
        monto_en_riesgo = ("Monto USD", lambda x: x[df.loc[x.index, "Estado"] == "En riesgo"].sum()),
        monto_inactivas = ("Monto USD", lambda x: x[df.loc[x.index, "Estado"] == "Inactiva"].sum()),
        monto_total_usd = ("Monto USD", "sum"),
        dias_prom_sin_act = ("Días Sin Actividad", "mean"),
        total_oportunidades = ("Oportunidad", "count")
    ).reset_index()

    # Redondeamos los decimales para que se vea prolijo en Sheets
    montos["dias_prom_sin_act"] = montos["dias_prom_sin_act"].round(0).astype(int)
    montos["monto_activas"]     = montos["monto_activas"].round(0)
    montos["monto_en_riesgo"]   = montos["monto_en_riesgo"].round(0)
    montos["monto_inactivas"]   = montos["monto_inactivas"].round(0)
    montos["monto_total_usd"]   = montos["monto_total_usd"].round(0)

    # Unimos las dos tablas (cantidades y montos) por el nombre del vendedor
    resumen = tabla_cant.merge(montos, on="Vendedor")

    # Renombramos las columnas finales para que sean claras en el dashboard
    resumen = resumen.rename(columns={
        "monto_activas":       "USD Activas",
        "monto_en_riesgo":     "USD En Riesgo",
        "monto_inactivas":     "USD Inactivas",
        "monto_total_usd":     "Monto Total USD",
        "dias_prom_sin_act":   "Prom. Días Sin Act.",
        "total_oportunidades": "Total Oportunidades"
    })

    # Calculamos el % de oportunidades inactivas para ver la salud por vendedor
    resumen["% Inactivas"] = (
        (resumen["Cant. Inactivas"] / resumen["Total Oportunidades"]) * 100
    ).round(1)

    # Ordenamos por monto total descendente — los vendedores con más plata en juego primero
    resumen = resumen.sort_values("Monto Total USD", ascending=False)

    # Ordenamos las columnas para que queden en un orden lógico en Sheets
    columnas_ordenadas = [
        "Vendedor",
        "Total Oportunidades",
        "Cant. Activas",
        "Cant. En Riesgo",
        "Cant. Inactivas",
        "% Inactivas",
        "USD Activas",
        "USD En Riesgo",
        "USD Inactivas",
        "Monto Total USD",
        "Prom. Días Sin Act.",
    ]
    resumen = resumen[columnas_ordenadas]

    print(f"Resumen generado: {len(resumen)} vendedores encontrados.")
    return resumen


def cargar_a_sheets(df_resumen, spreadsheet):
    """
    Carga el resumen de vendedores en la hoja 'Por Vendedor' de Google Sheets.
    Reemplaza el contenido anterior completamente.
    """
    print("Cargando datos en Google Sheets...")

    hoja = obtener_hoja(spreadsheet, "Por Vendedor")
    if hoja is None:
        registrar_error(spreadsheet, "analisis_vendedores.py", "Hoja 'Por Vendedor' no encontrada")
        return False

    encabezados = list(df_resumen.columns)
    filas = df_resumen.fillna("").values.tolist()

    escribir_hoja(hoja, encabezados, filas)
    print("¡Datos cargados en 'Por Vendedor' exitosamente!")
    return True


def main():
    """
    Función principal: extrae el pipeline de Odoo, agrupa por vendedor
    y carga el resumen en Google Sheets.
    """
    print("=" * 55)
    print("  ANÁLISIS POR VENDEDOR — FARKIM")
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

    # ── PASO 3: Extraer y procesar el pipeline ──────────
    print("\n[3/4] Extrayendo pipeline de Odoo y calculando resumen por vendedor...")
    oportunidades = extraer_pipeline(uid)

    if not oportunidades:
        mensaje = "No se obtuvieron oportunidades de Odoo"
        print(f"FALLO: {mensaje}")
        registrar_error(spreadsheet, "analisis_vendedores.py", mensaje)
        return

    # Procesamos el pipeline con la misma lógica de analisis_pipeline.py
    df_pipeline = procesar_pipeline(oportunidades)

    # Calculamos el resumen agrupado por vendedor
    df_vendedores = calcular_resumen_por_vendedor(df_pipeline)

    # ── PASO 4: Cargar en Google Sheets ─────────────────
    print("\n[4/4] Cargando en Google Sheets...")
    exito = cargar_a_sheets(df_vendedores, spreadsheet)

    if exito:
        print("\n" + "=" * 55)
        print("  PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 55)
        print(f"  Vendedores cargados: {len(df_vendedores)}")
        print(f"  Top 3 por monto:")
        for _, row in df_vendedores.head(3).iterrows():
            print(f"    {row['Vendedor']:<30} ${row['Monto Total USD']:>10,.0f} USD — {row['% Inactivas']}% inactivas")
    else:
        registrar_error(spreadsheet, "analisis_vendedores.py", "Error al cargar en Sheets")


if __name__ == "__main__":
    main()
