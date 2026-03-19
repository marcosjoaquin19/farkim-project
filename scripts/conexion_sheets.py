# ==============================================
# Nombre:      conexion_sheets.py
# Descripción: Conecta Python con Google Sheets usando
#              credenciales de cuenta de servicio (credentials.json).
#              Permite leer y escribir datos en el spreadsheet
#              "Farkim - Base de Datos".
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-17
# ==============================================

import gspread                              # Librería para manejar Google Sheets
from google.oauth2.service_account import Credentials  # Autenticación con cuenta de servicio
import os                                   # Para construir rutas de archivos
from dotenv import load_dotenv              # Lee las credenciales del archivo .env
from datetime import datetime               # Para registrar fecha y hora en el log

# ----------------------------------------------
# Cargar variables de entorno desde .env
# ----------------------------------------------
load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")  # ID del Google Sheets de Farkim

# ----------------------------------------------
# Ruta al archivo credentials.json
# ----------------------------------------------
# os.path.dirname(__file__) devuelve la carpeta donde está este script (scripts/)
# os.path.join sube un nivel (..) y busca credentials.json en la raíz del proyecto
RUTA_CREDENTIALS = os.path.join(
    os.path.dirname(__file__),
    "..",
    "credentials.json"
)

# ----------------------------------------------
# Permisos que le pedimos a Google
# ----------------------------------------------
# Estos "scopes" le dicen a Google qué puede hacer nuestra aplicación
# drive → para acceder a archivos de Drive
# spreadsheets → para leer y escribir en Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def autenticar():
    """
    Se autentica con Google usando el archivo credentials.json
    y devuelve un cliente de gspread listo para usar.
    Devuelve None si falla.
    """
    try:
        # Verificar que el archivo credentials.json existe
        if not os.path.exists(RUTA_CREDENTIALS):
            print("ERROR: No se encontró el archivo credentials.json")
            print(f"Buscado en: {os.path.abspath(RUTA_CREDENTIALS)}")
            return None

        # Credentials.from_service_account_file() lee el archivo JSON
        # y crea un objeto de credenciales con los permisos indicados
        credenciales = Credentials.from_service_account_file(
            RUTA_CREDENTIALS,
            scopes=SCOPES
        )

        # gspread.authorize() crea el cliente usando esas credenciales
        cliente = gspread.authorize(credenciales)

        print("Autenticación con Google Sheets exitosa.")
        return cliente

    except FileNotFoundError:
        print("ERROR: No se encontró el archivo credentials.json")
        return None

    except Exception as e:
        print(f"ERROR al autenticar con Google: {e}")
        return None


def abrir_spreadsheet(cliente):
    """
    Abre el spreadsheet de Farkim usando el ID del .env
    Devuelve el objeto spreadsheet o None si falla.
    """
    try:
        # open_by_key() abre el spreadsheet por su ID único
        spreadsheet = cliente.open_by_key(SPREADSHEET_ID)
        print(f"Spreadsheet abierto: '{spreadsheet.title}'")
        return spreadsheet

    except gspread.exceptions.SpreadsheetNotFound:
        print("ERROR: No se encontró el spreadsheet.")
        print("Verificá que el SPREADSHEET_ID en .env sea correcto.")
        print("También verificá que la cuenta de servicio tenga acceso al archivo.")
        return None

    except Exception as e:
        print(f"ERROR al abrir el spreadsheet: {e}")
        return None


def obtener_hoja(spreadsheet, nombre_hoja):
    """
    Devuelve una hoja específica del spreadsheet por su nombre.
    Por ejemplo: obtener_hoja(spreadsheet, "Pipeline")
    Devuelve None si la hoja no existe.
    """
    try:
        hoja = spreadsheet.worksheet(nombre_hoja)
        print(f"Hoja '{nombre_hoja}' encontrada.")
        return hoja

    except gspread.exceptions.WorksheetNotFound:
        print(f"ERROR: No se encontró la hoja '{nombre_hoja}'.")
        print("Verificá el nombre exacto de la pestaña en Google Sheets.")
        return None

    except Exception as e:
        print(f"ERROR al acceder a la hoja '{nombre_hoja}': {e}")
        return None


def registrar_error(spreadsheet, script, mensaje_error):
    """
    Guarda un registro de error en la hoja 'Log de Errores' del spreadsheet.
    Esto permite llevar un historial de qué falló y cuándo.

    Parámetros:
      spreadsheet    → objeto spreadsheet abierto
      script         → nombre del script que generó el error
      mensaje_error  → descripción del error ocurrido
    """
    try:
        hoja_log = obtener_hoja(spreadsheet, "Log de Errores")

        if hoja_log is None:
            print("No se pudo registrar el error: hoja 'Log de Errores' no encontrada.")
            return

        # Fecha y hora actual formateada
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Agregar una fila nueva al final del log
        # append_row() agrega los datos como una fila nueva
        hoja_log.append_row([fecha_hora, script, mensaje_error])
        print(f"Error registrado en 'Log de Errores': {mensaje_error}")

    except Exception as e:
        # Si falla el log, solo mostramos en consola para no generar un loop de errores
        print(f"No se pudo escribir en el log de errores: {e}")


def leer_hoja(hoja):
    """
    Lee todos los datos de una hoja y los devuelve como
    lista de diccionarios (una fila = un diccionario).
    La primera fila se usa como encabezado (nombres de columna).
    """
    try:
        # get_all_records() lee toda la hoja y convierte cada fila
        # en un diccionario usando la primera fila como encabezado
        datos = hoja.get_all_records()
        print(f"Se leyeron {len(datos)} filas de la hoja.")
        return datos

    except Exception as e:
        print(f"ERROR al leer la hoja: {e}")
        return None


def escribir_hoja(hoja, encabezados, filas):
    """
    Escribe datos en una hoja, reemplazando todo el contenido anterior.
    Primero escribe los encabezados y luego las filas de datos.

    Parámetros:
      hoja        → objeto hoja obtenido con obtener_hoja()
      encabezados → lista con los nombres de columna, ej: ['Nombre', 'Monto', 'Etapa']
      filas       → lista de listas con los datos, ej: [['Cliente A', 1000, 'Ganado'], ...]
    """
    try:
        # clear() borra todo el contenido actual de la hoja
        hoja.clear()

        # update() escribe los datos comenzando desde la celda A1
        # Combinamos encabezados + filas en una sola lista
        hoja.update([encabezados] + filas)

        print(f"Se escribieron {len(filas)} filas en la hoja.")

    except Exception as e:
        print(f"ERROR al escribir en la hoja: {e}")


def main():
    """
    Función principal: prueba la conexión con Google Sheets
    y lista todas las hojas disponibles en el spreadsheet.
    """
    print("=" * 50)
    print("  PRUEBA DE CONEXIÓN CON GOOGLE SHEETS - FARKIM")
    print("=" * 50)

    # Paso 1: autenticarse con Google
    cliente = autenticar()
    if cliente is None:
        return

    # Paso 2: abrir el spreadsheet de Farkim
    spreadsheet = abrir_spreadsheet(cliente)
    if spreadsheet is None:
        return

    # Paso 3: listar todas las hojas disponibles
    hojas = spreadsheet.worksheets()
    print(f"\nHojas encontradas en el spreadsheet ({len(hojas)} en total):")
    for hoja in hojas:
        print(f"  - {hoja.title}")

    print("\n¡Conexión con Google Sheets funcionando correctamente!")


if __name__ == "__main__":
    main()
