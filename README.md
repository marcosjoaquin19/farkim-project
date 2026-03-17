# Farkim - Sistema de Inteligencia Comercial

Sistema de extracción, procesamiento y visualización de datos comerciales para Farkim S.R.L.

## Descripción

Este proyecto conecta Python con Odoo y Alto Cerró para extraer datos de ventas,
procesarlos y cargarlos en Google Sheets para su análisis y visualización en dashboards.

## Empresa

**Farkim S.R.L.** — Equipamiento médico B2B
Rosario y Córdoba, Argentina

## Estructura del proyecto

```
Farkim-project/
  scripts/       → Scripts Python de extracción y análisis
  data/          → Archivos de datos fuente (Excel, CSV)
  notebooks/     → Jupyter Notebooks para análisis exploratorio
  outputs/       → Archivos de salida generados por los scripts
  .env           → Credenciales (NO subir a Git)
  credentials.json → Credenciales Google Cloud (NO subir a Git)
```

## Scripts principales

- `conexion_odoo.py` — Conexión con Odoo via XML-RPC
- `conexion_sheets.py` — Conexión con Google Sheets
- `analisis_pipeline.py` — Extrae pipeline de Odoo y carga en Sheets
- `analisis_alto_cerro.py` — Procesa Excel de Alto Cerró y carga en Sheets

## Google Sheets

**Nombre:** Farkim - Base de Datos
**Pestañas:** 12 hojas con datos reales

## Autor

Farkim S.R.L. — Área de Sistemas
Fecha de inicio: 2026-03-17
