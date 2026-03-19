# ==============================================
# Nombre:      diagnostico_monedas.py
# Descripción: Consulta Odoo y muestra qué moneda y qué montos
#              tiene cada oportunidad por mes, para saber exactamente
#              cuáles están en ARS y cuáles en USD antes de convertir.
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-19
# ==============================================

import sys
import os
from datetime import datetime

# Agregamos la carpeta scripts/ al path para importar los módulos de conexión
sys.path.append(os.path.dirname(__file__))
from conexion_odoo import autenticar, obtener_modelo


def diagnosticar_monedas(uid):
    """
    Extrae todas las oportunidades de Odoo incluyendo el campo currency_id
    (que indica si el monto está en ARS o USD) y muestra un resumen por mes.
    """

    print("\nConsultando Odoo — campos de moneda y montos...")

    # Traemos los campos necesarios para el diagnóstico
    # currency_id no existe en Odoo 19 para crm.lead — detectamos por magnitud
    campos = [
        "name",             # Nombre de la oportunidad
        "expected_revenue", # Monto esperado
        "create_date",      # Fecha de creación
        "partner_id",       # Cliente
    ]

    oportunidades = obtener_modelo(
        uid,
        modelo="crm.lead",
        campos=campos,
        filtros=[["type", "=", "opportunity"]],
        limite=500
    )

    if not oportunidades:
        print("No se encontraron oportunidades en Odoo.")
        return

    print(f"Total de oportunidades encontradas: {len(oportunidades)}\n")

    # Agrupamos por mes para ver el total y ejemplos de montos
    # Estructura: { "2025-10": { "cantidad": N, "total": X, "ejemplos": [...] } }
    resumen_por_mes = {}

    for op in oportunidades:
        # Extraemos el mes de la fecha de creación
        fecha_raw = op.get("create_date", "")
        mes = str(fecha_raw)[:7] if fecha_raw else "Sin fecha"

        monto = op.get("expected_revenue", 0) or 0

        if mes not in resumen_por_mes:
            resumen_por_mes[mes] = {"cantidad": 0, "total": 0, "ejemplos": []}

        resumen_por_mes[mes]["cantidad"] += 1
        resumen_por_mes[mes]["total"]    += monto

        # Guardamos hasta 3 ejemplos con monto > 0 para ver el orden de magnitud
        if len(resumen_por_mes[mes]["ejemplos"]) < 3 and monto > 0:
            cliente = op["partner_id"][1] if op.get("partner_id") else "Sin cliente"
            resumen_por_mes[mes]["ejemplos"].append(f"{cliente}: {monto:,.0f}")

    # ── MOSTRAR RESUMEN ──────────────────────────────────────────
    print("=" * 70)
    print("  DIAGNÓSTICO DE MONTOS POR MES — ODOO FARKIM")
    print("=" * 70)
    print(f"{'Mes':<12} {'Cant.':<8} {'Total':>20}  {'Moneda estimada':<12}  Ejemplos")
    print("-" * 70)

    for mes in sorted(resumen_por_mes.keys()):
        datos    = resumen_por_mes[mes]
        cantidad = datos["cantidad"]
        total    = datos["total"]
        ejemplos = " | ".join(datos["ejemplos"])

        # Si el promedio supera 10.000 → probablemente ARS
        # Si el promedio es menor a 10.000 → probablemente USD
        promedio = total / cantidad if cantidad > 0 else 0
        moneda_estimada = "→ ARS" if promedio > 10_000 else "→ USD"

        print(f"{mes:<12} {cantidad:<8} {total:>20,.0f}  {moneda_estimada:<16} {ejemplos}")

    print("=" * 70)
    print("\nCONCLUSION:")
    print("  Montos promedio > 10.000  →  probablemente ARS (hay que convertir)")
    print("  Montos promedio < 10.000  →  probablemente USD (ya están bien)\n")


def main():
    print("=" * 65)
    print("  DIAGNÓSTICO DE MONEDAS — FARKIM")
    print("=" * 65)
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    print("\n[1/2] Conectando a Odoo...")
    uid = autenticar()
    if uid is None:
        print("FALLO: No se pudo conectar a Odoo.")
        return

    print("[2/2] Analizando monedas por mes...")
    diagnosticar_monedas(uid)


if __name__ == "__main__":
    main()
