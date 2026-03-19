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
# Tipos de cambio ARS → USD — dólar oficial BCRA
# Fuente: api.argentinadatos.com (consultado 19/03/2026)
# Oct-Dic 2025: Odoo cargado en ARS → convertir a USD
# Desde Ene 2026: Odoo cargado en USD → no convertir
# Valores fijos (dato histórico que no cambia)
# ----------------------------------------------
TIPOS_CAMBIO_ARS = {
    "2025-10-01": 1450, "2025-10-02": 1450, "2025-10-03": 1450,
    "2025-10-04": 1450, "2025-10-05": 1450, "2025-10-06": 1455,
    "2025-10-07": 1455, "2025-10-08": 1455, "2025-10-09": 1450,
    "2025-10-10": 1450, "2025-10-11": 1450, "2025-10-12": 1450,
    "2025-10-13": 1375, "2025-10-14": 1385, "2025-10-15": 1405,
    "2025-10-16": 1430, "2025-10-17": 1475, "2025-10-18": 1475,
    "2025-10-19": 1475, "2025-10-20": 1495, "2025-10-21": 1515,
    "2025-10-22": 1515, "2025-10-23": 1505, "2025-10-24": 1515,
    "2025-10-25": 1515, "2025-10-26": 1515, "2025-10-27": 1460,
    "2025-10-28": 1495, "2025-10-29": 1460, "2025-10-30": 1465,
    "2025-10-31": 1475,
    "2025-11-01": 1475, "2025-11-02": 1475, "2025-11-03": 1500,
    "2025-11-04": 1485, "2025-11-05": 1475, "2025-11-06": 1475,
    "2025-11-07": 1445, "2025-11-08": 1445, "2025-11-09": 1445,
    "2025-11-10": 1445, "2025-11-11": 1440, "2025-11-12": 1435,
    "2025-11-13": 1430, "2025-11-14": 1425, "2025-11-15": 1425,
    "2025-11-16": 1425, "2025-11-17": 1415, "2025-11-18": 1425,
    "2025-11-19": 1430, "2025-11-20": 1450, "2025-11-21": 1450,
    "2025-11-22": 1450, "2025-11-23": 1450, "2025-11-24": 1450,
    "2025-11-25": 1470, "2025-11-26": 1475, "2025-11-27": 1475,
    "2025-11-28": 1475, "2025-11-29": 1475, "2025-11-30": 1475,
    "2025-12-01": 1475, "2025-12-02": 1480, "2025-12-03": 1480,
    "2025-12-04": 1470, "2025-12-05": 1460, "2025-12-06": 1460,
    "2025-12-07": 1460, "2025-12-08": 1460, "2025-12-09": 1465,
    "2025-12-10": 1460, "2025-12-11": 1460, "2025-12-12": 1465,
    "2025-12-13": 1465, "2025-12-14": 1465, "2025-12-15": 1465,
    "2025-12-16": 1480, "2025-12-17": 1475, "2025-12-18": 1475,
    "2025-12-19": 1475, "2025-12-20": 1475, "2025-12-21": 1475,
    "2025-12-22": 1475, "2025-12-23": 1475, "2025-12-24": 1475,
    "2025-12-25": 1475, "2025-12-26": 1475, "2025-12-27": 1475,
    "2025-12-28": 1475, "2025-12-29": 1475, "2025-12-30": 1480,
    "2025-12-31": 1480,
}


def convertir_a_usd(monto, fecha_str):
    """
    Convierte un monto a USD según la fecha exacta del registro.
    - Oct-Dic 2025: usa el dólar oficial BCRA del día exacto (hardcodeado)
    - Ene 2026 en adelante: ya está cargado en USD, no se toca
    - Sin fecha: devuelve el monto sin convertir

    Parámetros:
      monto     → número con el valor monetario
      fecha_str → fecha en formato "YYYY-MM-DD" o False si no tiene fecha

    Devuelve el monto en USD como float.
    """
    if not monto:
        return 0.0

    if not fecha_str or fecha_str is False:
        return float(monto)

    try:
        # Tomamos los primeros 10 caracteres para obtener "YYYY-MM-DD"
        fecha_dia = str(fecha_str)[:10]
        anio = int(fecha_dia[:4])

        # Ene 2026 en adelante: ya está en USD, no convertir
        if anio >= 2026:
            return float(monto)

        # Oct-Dic 2025: buscar el dólar oficial del día exacto
        tipo_cambio = TIPOS_CAMBIO_ARS.get(fecha_dia)

        if tipo_cambio and tipo_cambio > 0:
            return round(float(monto) / tipo_cambio, 2)
        else:
            print(f"  Advertencia: sin tipo de cambio para {fecha_dia}, monto sin convertir.")
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
        "date_closed",           # Fecha de cierre real (si ya cerró)
        "write_date",            # Última vez que alguien tocó el registro (última actividad real)
        "date_last_stage_update",# Última vez que se cambió de etapa
        "active",                # Si está activa o archivada
        "priority",              # Prioridad (0=normal, 1=alta)
        "tag_ids",               # Etiquetas asignadas
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

        # Fechas — vienen como "2025-10-15 10:30:00", tomamos los primeros 10 caracteres
        fecha_creacion   = str(op.get("create_date", ""))[:10]   if op.get("create_date")   else ""
        fecha_cierre     = str(op.get("date_deadline", ""))[:10]  if op.get("date_deadline")  else ""
        fecha_ultima_act = str(op.get("write_date", ""))[:10]     if op.get("write_date")     else fecha_creacion

        # Calcular días sin actividad usando write_date (última vez que alguien tocó el registro)
        # Esto es más preciso que create_date porque refleja actividad real del vendedor
        dias_sin_actividad = 0
        if fecha_ultima_act:
            try:
                fecha_dt = datetime.strptime(fecha_ultima_act, "%Y-%m-%d")
                dias_sin_actividad = (datetime.today() - fecha_dt).days
            except:
                dias_sin_actividad = 0

        # Convertir monto a USD usando la fecha de creación como referencia de moneda
        monto_original = op.get("expected_revenue", 0) or 0
        monto_usd = convertir_a_usd(monto_original, fecha_creacion)

        # Clasificación según días sin actividad real
        if dias_sin_actividad >= 60:
            estado = "Inactiva"      # Nadie la tocó hace más de 60 días
        elif dias_sin_actividad >= 30:
            estado = "En riesgo"     # Sin actividad entre 30 y 60 días
        else:
            estado = "Activa"        # Actividad en los últimos 30 días

        # Armar la fila final con todos los campos
        filas.append({
            "Oportunidad":          op.get("name", ""),
            "Cliente":              cliente,
            "Vendedor":             vendedor,
            "Etapa":                etapa,
            "Monto USD":            monto_usd,
            "Probabilidad %":       op.get("probability", 0),
            "Fecha Creación":       fecha_creacion,
            "Fecha Cierre Est.":    fecha_cierre,
            "Última Actividad":     fecha_ultima_act,
            "Días Sin Actividad":   dias_sin_actividad,
            "Estado":               estado,
        })

    # Convertimos la lista de diccionarios a un DataFrame de pandas
    # Un DataFrame es como una tabla de Excel en Python
    df = pd.DataFrame(filas)

    # Ordenamos: primero inactivas (las más urgentes), luego por días sin actividad
    df = df.sort_values(["Estado", "Días Sin Actividad"], ascending=[True, False])

    # Calculamos los tres grupos por separado para mostrar números reales
    df_activas   = df[df["Estado"] == "Activa"]
    df_en_riesgo = df[df["Estado"] == "En riesgo"]
    df_inactivas = df[df["Estado"] == "Inactiva"]

    print(f"\nPipeline procesado: {len(df)} oportunidades en total.")
    print(f"")
    print(f"  ACTIVAS    (actividad en últimos 30 días): {len(df_activas):>3} oportunidades — ${df_activas['Monto USD'].sum():>12,.0f} USD")
    print(f"  EN RIESGO  (sin actividad 30-60 días):     {len(df_en_riesgo):>3} oportunidades — ${df_en_riesgo['Monto USD'].sum():>12,.0f} USD")
    print(f"  INACTIVAS  (sin actividad más de 60 días): {len(df_inactivas):>3} oportunidades — ${df_inactivas['Monto USD'].sum():>12,.0f} USD  ← REQUIEREN ATENCION")

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
        df_activas   = df_pipeline[df_pipeline["Estado"] == "Activa"]
        df_en_riesgo = df_pipeline[df_pipeline["Estado"] == "En riesgo"]
        df_inactivas = df_pipeline[df_pipeline["Estado"] == "Inactiva"]

        print("\n" + "=" * 55)
        print("  PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 55)
        print(f"  Total oportunidades cargadas: {len(df_pipeline)}")
        print(f"")
        print(f"  Activas    (<30 días):        {len(df_activas):>3} ops — ${df_activas['Monto USD'].sum():>10,.0f} USD")
        print(f"  En riesgo  (30-60 días):      {len(df_en_riesgo):>3} ops — ${df_en_riesgo['Monto USD'].sum():>10,.0f} USD")
        print(f"  INACTIVAS  (+60 días):        {len(df_inactivas):>3} ops — ${df_inactivas['Monto USD'].sum():>10,.0f} USD  ← ATENCION REQUERIDA")
    else:
        registrar_error(spreadsheet, "analisis_pipeline.py", "Error al cargar datos en Sheets")


if __name__ == "__main__":
    main()
