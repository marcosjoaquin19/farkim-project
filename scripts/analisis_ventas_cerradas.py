# ==============================================
# Nombre:      analisis_ventas_cerradas.py
# Descripción: Extrae oportunidades GANADAS de Odoo
#              (probability=100 o etapa "Ganada") y las carga
#              en Google Sheets para el seguimiento mensual
#              de ventas vs objetivos.
#              Hojas destino: "Ventas Cerradas" y "Objetivos Mensuales"
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-25
# ==============================================

import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(__file__))

from conexion_odoo import autenticar, obtener_modelo
from conexion_sheets import (
    autenticar as autenticar_sheets,
    abrir_spreadsheet,
    obtener_hoja,
    escribir_hoja,
    registrar_error
)
from analisis_pipeline import convertir_a_usd

# ----------------------------------------------
# Nombres de meses en español
# ----------------------------------------------
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def formato_mes_es(fecha_str):
    """
    Convierte "2026-04" o "2026-04-15" a "Abril 2026".
    """
    try:
        partes = str(fecha_str)[:7].split("-")
        anio = int(partes[0])
        mes = int(partes[1])
        return f"{MESES_ES[mes]} {anio}"
    except Exception:
        return str(fecha_str)


def extraer_ganadas(uid):
    """
    Extrae oportunidades ganadas de Odoo.
    Una oportunidad ganada tiene probability=100.
    """
    print("Extrayendo oportunidades ganadas de Odoo...")

    campos = [
        "name",
        "partner_id",
        "user_id",
        "expected_revenue",
        "stage_id",
        "probability",
        "create_date",
        "date_closed",
        "write_date",
    ]

    # Filtro: solo oportunidades ganadas (probability = 100)
    ganadas = obtener_modelo(
        uid,
        modelo="crm.lead",
        campos=campos,
        filtros=[
            ["type", "=", "opportunity"],
            ["probability", "=", 100],
        ],
        limite=500
    )

    return ganadas


def procesar_ganadas(oportunidades):
    """
    Procesa las oportunidades ganadas en un DataFrame limpio.
    Usa date_closed como fecha de la venta. Si no tiene, usa write_date.
    """
    print("Procesando ventas cerradas...")

    filas = []

    for op in oportunidades:
        cliente = op["partner_id"][1] if op["partner_id"] else "Sin cliente"
        vendedor = op["user_id"][1] if op["user_id"] else "Sin vendedor"
        etapa = op["stage_id"][1] if op["stage_id"] else "Ganada"

        # Fecha de cierre: preferimos date_closed, fallback a write_date
        fecha_cierre_raw = op.get("date_closed") or op.get("write_date") or op.get("create_date")
        fecha_cierre = str(fecha_cierre_raw)[:10] if fecha_cierre_raw else ""

        fecha_creacion = str(op.get("create_date", ""))[:10] if op.get("create_date") else ""

        # Convertir monto a USD usando fecha de cierre como referencia
        monto_original = op.get("expected_revenue", 0) or 0
        monto_usd = convertir_a_usd(monto_original, fecha_cierre or fecha_creacion)

        # Mes de cierre en formato español
        mes_cierre = formato_mes_es(fecha_cierre) if fecha_cierre else "Sin fecha"

        # Semana del mes (1-5)
        semana_mes = ""
        if fecha_cierre:
            try:
                dia = int(fecha_cierre[8:10])
                semana_mes = f"Semana {((dia - 1) // 7) + 1}"
            except Exception:
                semana_mes = ""

        filas.append({
            "Oportunidad": op.get("name", ""),
            "Cliente": cliente,
            "Vendedor": vendedor,
            "Etapa": etapa,
            "Monto USD": monto_usd,
            "Fecha Cierre": fecha_cierre,
            "Mes Cierre": mes_cierre,
            "Semana": semana_mes,
            "Fecha Creación": fecha_creacion,
        })

    df = pd.DataFrame(filas)

    if not df.empty:
        df = df.sort_values("Fecha Cierre", ascending=False)

    print(f"Ventas cerradas procesadas: {len(df)} oportunidades ganadas.")
    if not df.empty:
        print(f"  Monto total: ${df['Monto USD'].sum():,.0f} USD")

    return df


def crear_hoja_si_no_existe(spreadsheet, nombre_hoja):
    """
    Crea una hoja nueva en el spreadsheet si no existe.
    """
    hojas_existentes = [h.title for h in spreadsheet.worksheets()]
    if nombre_hoja not in hojas_existentes:
        spreadsheet.add_worksheet(title=nombre_hoja, rows=100, cols=20)
        print(f"Hoja '{nombre_hoja}' creada.")
    else:
        print(f"Hoja '{nombre_hoja}' ya existe.")


def cargar_ventas_cerradas(df, spreadsheet):
    """Carga las ventas cerradas en Google Sheets."""
    crear_hoja_si_no_existe(spreadsheet, "Ventas Cerradas")
    hoja = obtener_hoja(spreadsheet, "Ventas Cerradas")
    if hoja is None:
        return False

    encabezados = list(df.columns)
    filas = df.fillna("").values.tolist()
    escribir_hoja(hoja, encabezados, filas)
    print("Ventas cerradas cargadas en 'Ventas Cerradas'.")
    return True


def inicializar_objetivos(spreadsheet):
    """
    Crea la hoja 'Objetivos Mensuales' con encabezados si no existe.
    No sobreescribe datos existentes.
    """
    crear_hoja_si_no_existe(spreadsheet, "Objetivos Mensuales")
    hoja = obtener_hoja(spreadsheet, "Objetivos Mensuales")

    # Solo escribir encabezados si la hoja está vacía
    datos = hoja.get_all_values()
    if len(datos) == 0:
        hoja.update([["Mes", "Objetivo USD", "Editado por", "Fecha edición"]])
        print("Encabezados de 'Objetivos Mensuales' creados.")
    else:
        print("'Objetivos Mensuales' ya tiene datos, no se sobreescribe.")


def main():
    print("=" * 55)
    print("  ANÁLISIS DE VENTAS CERRADAS — FARKIM")
    print("=" * 55)
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # Conectar a Odoo
    print("\n[1/4] Conectando a Odoo...")
    uid = autenticar()
    if uid is None:
        print("FALLO: No se pudo conectar a Odoo.")
        return

    # Conectar a Google Sheets
    print("\n[2/4] Conectando a Google Sheets...")
    cliente_sheets = autenticar_sheets()
    if cliente_sheets is None:
        return

    spreadsheet = abrir_spreadsheet(cliente_sheets)
    if spreadsheet is None:
        return

    # Extraer y procesar
    print("\n[3/4] Extrayendo ventas cerradas...")
    ganadas = extraer_ganadas(uid)

    if not ganadas:
        print("No se encontraron oportunidades ganadas en Odoo.")
        # Igual creamos las hojas para que el dashboard no falle
        inicializar_objetivos(spreadsheet)
        crear_hoja_si_no_existe(spreadsheet, "Ventas Cerradas")
        return

    df = procesar_ganadas(ganadas)

    # Cargar en Sheets
    print("\n[4/4] Cargando en Google Sheets...")
    cargar_ventas_cerradas(df, spreadsheet)
    inicializar_objetivos(spreadsheet)

    print("\n" + "=" * 55)
    print("  PROCESO COMPLETADO")
    print("=" * 55)
    print(f"  Ventas cerradas: {len(df)}")
    print(f"  Monto total: ${df['Monto USD'].sum():,.0f} USD")


if __name__ == "__main__":
    main()
