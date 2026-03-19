# ==============================================
# Nombre:      analisis_sin_movimiento.py
# Descripción: Extrae del pipeline de Odoo las oportunidades
#              que llevan más de 60 días sin actividad (inactivas)
#              y las carga en la hoja "Sin Movimiento" de Sheets
#              para que el gerente pueda revisarlas y actuar.
#              Hoja destino: "Sin Movimiento"
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
from analisis_pipeline import extraer_pipeline, procesar_pipeline

# ── Umbral de días para considerar una oportunidad inactiva ──
# Esto lo definimos como constante para poder cambiarlo fácilmente
DIAS_INACTIVIDAD = 60


def filtrar_inactivas(df):
    """
    Filtra el DataFrame del pipeline para quedarse solo con las
    oportunidades que llevan más de DIAS_INACTIVIDAD días sin actividad.

    También agrega una columna de urgencia para ayudar al gerente a priorizar:
      - CRITICA:  más de 180 días sin actividad (6 meses)
      - ALTA:     entre 90 y 180 días
      - MEDIA:    entre 60 y 90 días

    Devuelve un DataFrame ordenado de mayor a menor por días sin actividad.
    """
    print(f"Filtrando oportunidades con más de {DIAS_INACTIVIDAD} días sin actividad...")

    # Filtramos solo las inactivas
    df_inactivas = df[df["Estado"] == "Inactiva"].copy()

    # Agregamos columna de urgencia para que el gerente pueda priorizar
    def calcular_urgencia(dias):
        if dias >= 180:
            return "CRITICA — +6 meses sin contacto"
        elif dias >= 90:
            return "ALTA — +3 meses sin contacto"
        else:
            return "MEDIA — +2 meses sin contacto"

    df_inactivas["Urgencia"] = df_inactivas["Días Sin Actividad"].apply(calcular_urgencia)

    # Seleccionamos y ordenamos las columnas que son útiles para el gerente
    columnas = [
        "Urgencia",
        "Días Sin Actividad",
        "Oportunidad",
        "Cliente",
        "Vendedor",
        "Etapa",
        "Monto USD",
        "Probabilidad %",
        "Fecha Creación",
        "Última Actividad",
    ]
    df_inactivas = df_inactivas[columnas]

    # Ordenamos por días sin actividad — las más viejas primero
    df_inactivas = df_inactivas.sort_values("Días Sin Actividad", ascending=False)

    # Contamos por nivel de urgencia para el resumen
    criticas = len(df_inactivas[df_inactivas["Urgencia"].str.startswith("CRITICA")])
    altas    = len(df_inactivas[df_inactivas["Urgencia"].str.startswith("ALTA")])
    medias   = len(df_inactivas[df_inactivas["Urgencia"].str.startswith("MEDIA")])

    print(f"Oportunidades inactivas encontradas: {len(df_inactivas)}")
    print(f"  CRITICAS (+180 días): {criticas}")
    print(f"  ALTAS    (+90 días):  {altas}")
    print(f"  MEDIAS   (+60 días):  {medias}")

    return df_inactivas


def cargar_a_sheets(df_inactivas, spreadsheet):
    """
    Carga el listado de oportunidades inactivas en la hoja 'Sin Movimiento'
    de Google Sheets. Reemplaza el contenido anterior.
    """
    print("Cargando datos en Google Sheets...")

    hoja = obtener_hoja(spreadsheet, "Sin Movimiento")
    if hoja is None:
        registrar_error(spreadsheet, "analisis_sin_movimiento.py", "Hoja 'Sin Movimiento' no encontrada")
        return False

    encabezados = list(df_inactivas.columns)
    filas = df_inactivas.fillna("").values.tolist()

    escribir_hoja(hoja, encabezados, filas)
    print("¡Datos cargados en 'Sin Movimiento' exitosamente!")
    return True


def main():
    """
    Función principal: extrae el pipeline de Odoo, filtra las oportunidades
    inactivas y las carga en Google Sheets para revisión del gerente.
    """
    print("=" * 55)
    print("  OPORTUNIDADES SIN MOVIMIENTO — FARKIM")
    print("=" * 55)
    print(f"  Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Umbral de inactividad: {DIAS_INACTIVIDAD} días")
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

    # ── PASO 3: Extraer pipeline y filtrar inactivas ─────
    print("\n[3/4] Extrayendo pipeline y filtrando oportunidades inactivas...")
    oportunidades = extraer_pipeline(uid)

    if not oportunidades:
        mensaje = "No se obtuvieron oportunidades de Odoo"
        print(f"FALLO: {mensaje}")
        registrar_error(spreadsheet, "analisis_sin_movimiento.py", mensaje)
        return

    df_pipeline  = procesar_pipeline(oportunidades)
    df_inactivas = filtrar_inactivas(df_pipeline)

    if df_inactivas.empty:
        print("No hay oportunidades inactivas. No se carga nada en Sheets.")
        return

    # ── PASO 4: Cargar en Google Sheets ─────────────────
    print("\n[4/4] Cargando en Google Sheets...")
    exito = cargar_a_sheets(df_inactivas, spreadsheet)

    if exito:
        monto_en_riesgo = df_inactivas["Monto USD"].sum()
        vendedor_top = (
            df_inactivas.groupby("Vendedor")["Oportunidad"]
            .count()
            .idxmax()
        )

        print("\n" + "=" * 55)
        print("  PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 55)
        print(f"  Oportunidades inactivas cargadas: {len(df_inactivas)}")
        print(f"  Monto total en riesgo:            ${monto_en_riesgo:,.0f} USD")
        print(f"  Vendedor con más inactivas:       {vendedor_top}")
        print(f"  Acción recomendada: revisar con el gerente")
    else:
        registrar_error(spreadsheet, "analisis_sin_movimiento.py", "Error al cargar en Sheets")


if __name__ == "__main__":
    main()
