# Script temporal para ver qué campos de fecha tiene crm.lead en Odoo
import sys, os, xmlrpc.client
sys.path.append(os.path.dirname(__file__))
from conexion_odoo import autenticar
from dotenv import load_dotenv
load_dotenv()

uid = autenticar()
models = xmlrpc.client.ServerProxy(f'{os.getenv("ODOO_URL")}/xmlrpc/2/object')
campos = models.execute_kw(os.getenv("ODOO_DB"), uid, os.getenv("ODOO_API_KEY"),
    'crm.lead', 'fields_get', [], {'attributes': ['string', 'type']})

print(f"\n{'Campo':<40} {'Tipo':<12} {'Etiqueta en Odoo'}")
print("-" * 75)
for nombre, info in sorted(campos.items()):
    if info['type'] in ('date', 'datetime'):
        print(f"{nombre:<40} {info['type']:<12} {info['string']}")
