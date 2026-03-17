# ==============================================
# Nombre:      conexion_odoo.py
# Descripción: Conecta Python con Odoo via XML-RPC con SSL.
#              Permite autenticarse y ejecutar consultas
#              sobre los datos de Farkim en Odoo.
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-17
# ==============================================

import xmlrpc.client  # Módulo de Python para comunicarse con servidores XML-RPC
import ssl            # Módulo para manejar conexiones seguras (HTTPS)
import os             # Módulo para leer variables del sistema
from dotenv import load_dotenv  # Lee las credenciales del archivo .env

# ----------------------------------------------
# Cargar credenciales desde el archivo .env
# ----------------------------------------------
# load_dotenv() busca el archivo .env en la carpeta del proyecto
# y carga cada línea como una variable de entorno accesible con os.getenv()
load_dotenv()

ODOO_URL  = os.getenv("ODOO_URL")   # URL del servidor Odoo
ODOO_DB   = os.getenv("ODOO_DB")    # Nombre de la base de datos
ODOO_USER = os.getenv("ODOO_USER")  # Email del usuario
ODOO_KEY  = os.getenv("ODOO_API_KEY")  # Clave API (se regenera cada día)


def crear_contexto_ssl():
    """
    Crea un contexto SSL que acepta el certificado del servidor Odoo.
    Sin esto, Python rechaza la conexión HTTPS por seguridad.
    """
    # create_default_context() genera una configuración SSL estándar
    contexto = ssl.create_default_context()
    # check_hostname y verify_mode desactivados para evitar errores
    # con certificados autofirmados en servidores como Odoo Cloud
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE
    return contexto


def autenticar():
    """
    Se conecta al servidor Odoo y verifica usuario + API key.
    Devuelve el uid (número de usuario) si la autenticación es exitosa.
    Devuelve None si falla.
    """
    try:
        print(f"Conectando a Odoo: {ODOO_URL}")

        # El endpoint /xmlrpc/2/common es el punto de entrada público de Odoo
        # No requiere autenticación previa — sirve para hacer el login
        url_common = f"{ODOO_URL}/xmlrpc/2/common"

        # ServerProxy crea un objeto que representa al servidor remoto
        # Podemos llamar sus métodos como si fueran funciones locales
        common = xmlrpc.client.ServerProxy(
            url_common,
            context=crear_contexto_ssl()
        )

        # authenticate() verifica las credenciales y devuelve el uid del usuario
        # Si falla (contraseña incorrecta, etc.) devuelve False
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_KEY, {})

        if uid:
            print(f"Autenticación exitosa. Usuario ID: {uid}")
            return uid
        else:
            print("ERROR: Autenticación fallida.")
            print("Verificá que la API key no haya expirado (se genera cada día).")
            return None

    except ConnectionRefusedError:
        print("ERROR: No se pudo conectar al servidor.")
        print("Verificá que la URL de Odoo sea correcta y tengas internet.")
        return None

    except Exception as e:
        print(f"ERROR inesperado al autenticar: {e}")
        return None


def obtener_modelo(uid, modelo, campos, filtros=None, limite=100):
    """
    Consulta registros de cualquier modelo de Odoo (ventas, clientes, etc.)

    Parámetros:
      uid     → número de usuario obtenido en autenticar()
      modelo  → nombre del modelo Odoo, ej: 'crm.lead', 'sale.order'
      campos  → lista de campos a traer, ej: ['name', 'partner_id', 'amount_total']
      filtros → condiciones de búsqueda, ej: [['stage_id.name', '=', 'Ganado']]
                Si no se pasan filtros, trae todos los registros
      limite  → cantidad máxima de registros a devolver (por defecto 100)

    Devuelve una lista de diccionarios con los datos, o None si falla.
    """
    # Si no se pasan filtros, usamos lista vacía (sin restricciones)
    if filtros is None:
        filtros = []

    try:
        # El endpoint /xmlrpc/2/object es para consultar datos
        # Requiere autenticación (por eso necesitamos el uid)
        url_object = f"{ODOO_URL}/xmlrpc/2/object"

        models = xmlrpc.client.ServerProxy(
            url_object,
            context=crear_contexto_ssl()
        )

        # execute_kw() ejecuta métodos sobre modelos de Odoo
        # 'search_read' busca registros y devuelve los campos pedidos en un solo paso
        registros = models.execute_kw(
            ODOO_DB,    # base de datos
            uid,        # id del usuario autenticado
            ODOO_KEY,   # clave API
            modelo,     # modelo a consultar
            'search_read',  # método de Odoo: buscar y leer
            [filtros],  # condiciones de búsqueda
            {
                'fields': campos,   # campos a devolver
                'limit': limite     # máximo de registros
            }
        )

        print(f"Se obtuvieron {len(registros)} registros de '{modelo}'.")
        return registros

    except Exception as e:
        print(f"ERROR al consultar el modelo '{modelo}': {e}")
        return None


def main():
    """
    Función principal: prueba la conexión con Odoo
    y muestra información básica del servidor.
    """
    print("=" * 50)
    print("  PRUEBA DE CONEXIÓN CON ODOO - FARKIM")
    print("=" * 50)

    # Verificar que las credenciales están cargadas
    if not ODOO_URL or not ODOO_DB or not ODOO_USER or not ODOO_KEY:
        print("ERROR: Faltan credenciales en el archivo .env")
        print("Verificá que .env tenga ODOO_URL, ODOO_DB, ODOO_USER y ODOO_API_KEY")
        return

    # Intentar autenticación
    uid = autenticar()

    if uid is None:
        print("No se pudo establecer conexión con Odoo.")
        return

    # Prueba: traer los primeros 5 clientes (modelo res.partner)
    print("\nProbando consulta: primeros 5 clientes...")
    clientes = obtener_modelo(
        uid,
        modelo='res.partner',
        campos=['name', 'email', 'phone'],
        limite=5
    )

    if clientes:
        print("\nClientes encontrados:")
        for cliente in clientes:
            print(f"  - {cliente.get('name', 'Sin nombre')} | {cliente.get('email', 'Sin email')}")

    print("\n¡Conexión con Odoo funcionando correctamente!")


# Este bloque asegura que main() solo se ejecute cuando
# corremos este archivo directamente (no cuando lo importamos desde otro script)
if __name__ == "__main__":
    main()
