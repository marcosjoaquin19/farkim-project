# ==============================================
# Nombre:      analisis_pipeline.py
# Descripción: Extrae el pipeline comercial completo desde Odoo CRM,
#              convierte montos de ARS a USD para oct-dic 2025,
#              y carga los datos procesados en Google Sheets.
#              Hoja destino: "Pipeline Completo"
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-17
# Datos:       Modelo crm.lead de Odoo — 380 oportunidades desde oct 2025
# ==============================================

import pandas as pd          # Para procesar y transformar los datos en tablas
import requests              # Para consultar la API de conversión de moneda
from datetime import datetime  # Para manejar fechas
import sys                   # Para agregar la carpeta scripts/ al path de Python
import os

# ----------------------------------------------
# Agregar la carpeta scripts/ al path para poder
# importar los módulos de conexión que ya creamos
# ----------------------------------------------
# __file__ es la ruta de este script
# dirname(__file__) es la carpeta donde está (scripts/)
sys.path.append(os.path.dirname(__file__))

# Importamos las funciones que ya hicimos en los otros scripts
from conexion_odoo import autenticar, obtener_modelo
from conexion_sheets import (
    autenticar as autenticar_sheets,
    abrir_spreadsheet,
    obtener_hoja,
    escribir_hoja,
    registrar_error
)

# ----------------------------------------------
# Tipos de cambio ARS → USD confirmados
# oct-dic 2025 en Odoo están en ARS
# desde enero 2026 ya están en USD
# ----------------------------------------------
TIPOS_CAMBIO_ARS = {
    "2025-10": 1475.0,
    "2025-11": 1475.0,
    "2025-12": 1480.0,
}


def obtener_tipo_cambio_api(anio, mes):
    """
    Consulta la API de ArgentinaDatos para obtener el dólar oficial
    del mes indicado. Se usa como respaldo si el mes no está en el
    diccionario TIPOS_CAMBIO_ARS.

    Parámetros:
      anio → año en formato string, ej: "2025"
      mes  → mes en formato string con cero, ej: "10"

    Devuelve el valor del dólar oficial o None si falla.
    """
    try:
        url = f"https://api.argentinadatos.com/v1/cotizaciones/dolares/oficial"
        respuesta = requests.get(url, timeout=10)

        if respuesta.status_code != 200:
            print(f"  Advertencia: API de cambio respondió {respuesta.status_code}")
            return None

        # La API devuelve una lista de cotizaciones diarias
        # Buscamos el último valor del mes pedido
        cotizaciones = respuesta.json()
        clave_mes = f"{anio}-{mes}"

        valores_del_mes = [
            c for c in cotizaciones
            if c.get("fecha", "").startswith(clave_mes)
        ]

        if valores_del_mes:
            # Tomamos el último día disponible del mes
            ultimo = sorted(valores_del_mes, key=lambda x: x["fecha"])[-1]
            return float(ultimo.get("venta", 0))

        return None

    except Exception as e:
        print(f"  Error al consultar API de cambio: {e}")
        return None


def convertir_a_usd(monto, fecha_str):
    """
    Convierte un monto a USD según la fecha.
    - Si la fecha es oct-dic 2025: usa tipo de cambio ARS conocido
    - Si la fecha es enero 2026 en adelante: ya está en USD, no convierte
    - Si no tiene fecha: devuelve el monto sin convertir

    Parámetros:
      monto    → número con el valor monetario
      fecha_str → fecha en formato "YYYY-MM-DD" o False si no tiene fecha

    Devuelve el monto en USD como float.
    """
    # Si no hay monto, devolvemos 0
    if not monto:
        return 0.0

    # Si no hay fecha, asumimos que ya está en USD (datos recientes)
    if not fecha_str or fecha_str is False:
        return float(monto)

    try:
        # Extraemos año y mes de la fecha (ej: "2025-10-15" → "2025", "10")
        partes = str(fecha_str)[:7]  # Tomamos los primeros 7 caracteres: "2025-10"
        anio, mes = partes.split("-")
        clave = f"{anio}-{mes}"

        # Si es antes de enero 2026, el monto está en ARS → convertir a USD
        if int(anio) < 2026:
            tipo_cambio = TIPOS_CAMBIO_ARS.get(clave)

            # Si no tenemos el valor guardado, consultamos la API
            if tipo_cambio is None:
                print(f"  Consultando tipo de cambio para {clave} en la API...")
                tipo_cambio = obtener_tipo_cambio_api(anio, mes)

            if tipo_cambio and tipo_cambio > 0:
                return round(float(monto) / tipo_cambio, 2)
            else:
                print(f"  Advertencia: sin tipo de cambio para {clave}, monto sin convertir.")
                return float(monto)

        # Enero 2026 en adelante: ya está en USD
        return float(monto)

    except Exception as e:
        print(f"  Error al convertir moneda: {e}")
        return float(monto)


def extraer_pipeline(uid):
    """
    Extrae todas las oportunidades del CRM de Odoo.
    Usa el modelo 'crm.lead' que almacena el pipeline comercial.

    Devuelve una lista de diccionarios con los datos crudos de Odoo,
    o None si falla.
    """
    print("Extrayendo pipeline de Odoo...")

    # Campos que queremos traer de cada oportunidad
    campos = [
        "name",             # Nombre de la oportunidad
        "partner_id",       # Cliente (devuelve [id, nombre])
        "user_id",          # Vendedor asignado (devuelve [id, nombre])
        "expected_revenue", # Monto esperado (en ARS u USD según fecha)
        "stage_id",         # Etapa del pipeline (devuelve [id, nombre])
        "probability",      # Probabilidad de cierre (0-100)
        "date_deadline",    # Fecha límite esperada de cierre
        "create_date",      # Fecha de creación de la oportunidad
        "date_closed",      # Fecha de cierre real (si ya cerró)
        "active",           # Si está activa o archivada
        "priority",         # Prioridad (0=normal, 1=alta)
        "tag_ids",          # Etiquetas asignadas
    ]

    # Traemos TODAS las oportunidades sin filtro (límite alto para no perder datos)
    oportunidades = obtener_modelo(
        uid,
        modelo="crm.lead",
        campos=campos,
        filtros=[["type", "=", "opportunity"]],  # Solo oportunidades, no leads
        limite=500  # Más que suficiente para las 380 actuales
    )

    return oportunidades


def procesar_pipeline(oportunidades):
    """
    Transforma la lista cruda de Odoo en un DataFrame de pandas limpio.
    - Extrae los nombres de campos relacionales (partner_id, user_id, stage_id)
    - Convierte montos ARS a USD según la fecha
    - Calcula días sin movimiento
    - Agrega columna de alerta por abandono

    Devuelve un DataFrame listo para cargar a Sheets.
    """
    print("Procesando datos del pipeline...")

    # Lista donde vamos a guardar cada oportunidad procesada
    filas = []

    for op in oportunidades:
        # Los campos relacionales en Odoo devuelven [id, nombre] o False
        # Usamos una función auxiliar para extraer solo el nombre
        cliente  = op["partner_id"][1] if op["partner_id"] else "Sin cliente"
        vendedor = op["user_id"][1]    if op["user_id"]    else "Sin vendedor"
        etapa    = op["stage_id"][1]   if op["stage_id"]   else "Sin etapa"

        # Fecha de creación — viene como string "2025-10-15 10:30:00"
        # Tomamos solo los primeros 10 caracteres para quedarnos con "2025-10-15"
        fecha_creacion = str(op.get("create_date", ""))[:10] if op.get("create_date") else ""
        fecha_cierre   = str(op.get("date_deadline", ""))[:10] if op.get("date_deadline") else ""

        # Calcular días sin movimiento desde la fecha de creación
        dias_sin_movimiento = 0
        if fecha_creacion:
            try:
                fecha_dt = datetime.strptime(fecha_creacion, "%Y-%m-%d")
                dias_sin_movimiento = (datetime.today() - fecha_dt).days
            except:
                dias_sin_movimiento = 0

        # Convertir monto a USD usando la fecha de creación como referencia
        monto_original = op.get("expected_revenue", 0) or 0
        monto_usd = convertir_a_usd(monto_original, fecha_creacion)

        # Alerta de abandono: oportunidades sin movimiento +60 días
        if dias_sin_movimiento >= 60:
            alerta = "ABANDONADA"
        elif dias_sin_movimiento >= 30:
            alerta = "En riesgo"
        else:
            alerta = "Activa"

        # Armar la fila final con todos los campos
        filas.append({
            "Oportunidad":         op.get("name", ""),
            "Cliente":             cliente,
            "Vendedor":            vendedor,
            "Etapa":               etapa,
            "Monto USD":           monto_usd,
            "Probabilidad %":      op.get("probability", 0),
            "Fecha Creación":      fecha_creacion,
            "Fecha Cierre Est.":   fecha_cierre,
            "Días Sin Movimiento": dias_sin_movimiento,
            "Alerta":              alerta,
            "Activa":              "Sí" if op.get("active") else "No",
        })

    # Convertimos la lista de diccionarios a un DataFrame de pandas
    # Un DataFrame es como una tabla de Excel en Python
    df = pd.DataFrame(filas)

    # Ordenamos por monto descendente para ver las más importantes primero
    df = df.sort_values("Monto USD", ascending=False)

    print(f"Pipeline procesado: {len(df)} oportunidades.")
    print(f"  - Activas:    {len(df[df['Activa'] == 'Sí'])}")
    print(f"  - Abandonadas (+60 días): {len(df[df['Alerta'] == 'ABANDONADA'])}")
    print(f"  - Monto total USD: ${df['Monto USD'].sum():,.0f}")

    return df


def cargar_a_sheets(df, spreadsheet):
    """
    Carga el DataFrame del pipeline en la hoja 'Pipeline Completo'
    de Google Sheets, reemplazando el contenido anterior.

    Parámetros:
      df          → DataFrame con los datos procesados
      spreadsheet → objeto spreadsheet abierto con conexion_sheets
    """
    print("Cargando datos en Google Sheets...")

    hoja = obtener_hoja(spreadsheet, "Pipeline Completo")
    if hoja is None:
        registrar_error(spreadsheet, "analisis_pipeline.py", "Hoja 'Pipeline Completo' no encontrada")
        return False

    # Preparamos los datos en el formato que espera escribir_hoja()
    # encabezados: lista con los nombres de columna
    encabezados = list(df.columns)

    # filas: lista de listas con los valores de cada fila
    # fillna("") reemplaza los valores vacíos con texto vacío (Sheets no acepta NaN)
    filas = df.fillna("").values.tolist()

    escribir_hoja(hoja, encabezados, filas)
    print("¡Datos cargados en 'Pipeline Completo' exitosamente!")
    return True


def main():
    """
    Función principal: orquesta todo el proceso ETL del pipeline.
    ETL = Extract (extraer) → Transform (transformar) → Load (cargar)
    """
    print("=" * 55)
    print("  ANÁLISIS DE PIPELINE COMERCIAL — FARKIM")
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

    # ── PASO 3: Extraer y procesar el pipeline de Odoo ──
    print("\n[3/4] Extrayendo y procesando pipeline de Odoo...")
    oportunidades = extraer_pipeline(uid)

    if not oportunidades:
        mensaje = "No se obtuvieron oportunidades de Odoo"
        print(f"FALLO: {mensaje}")
        registrar_error(spreadsheet, "analisis_pipeline.py", mensaje)
        return

    df_pipeline = procesar_pipeline(oportunidades)

    # ── PASO 4: Cargar en Google Sheets ─────────────────
    print("\n[4/4] Cargando en Google Sheets...")
    exito = cargar_a_sheets(df_pipeline, spreadsheet)

    if exito:
        print("\n" + "=" * 55)
        print("  PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 55)
        print(f"  Oportunidades cargadas: {len(df_pipeline)}")
        print(f"  Monto total pipeline:   ${df_pipeline['Monto USD'].sum():,.0f} USD")
        print(f"  Abandonadas (+60 días): {len(df_pipeline[df_pipeline['Alerta'] == 'ABANDONADA'])}")
    else:
        registrar_error(spreadsheet, "analisis_pipeline.py", "Error al cargar datos en Sheets")


if __name__ == "__main__":
    main()
