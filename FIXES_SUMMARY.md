# Resumen de Fixes - Carga Semanal Excel (Marzo 31, 2026)

## Estado Actual
**Branch:** desarrollo
**Status:** Todos los fixes validados y commiteados
**Última actualización:** 2026-03-31

---

## Problemas Identificados y Solucionados

### 1. **Infinite Loop en Uploader Excel** ❌ → ✅
**Problema:**
- `st.file_uploader` recuerda el archivo seleccionado entre reruns de Streamlit
- Cada rerun re-ejecutaba el procesamiento del mismo archivo
- Causaba 20+ ejecuciones sin que el usuario seleccione nada
- **Resultado:** Mismos datos procesados múltiples veces = acumulación exponencial

**Solución:**
- Agregar `session_state` tracking con ID único del archivo
- ID = hash de nombre + tamaño del archivo
- Si el ID del archivo actual == último ID procesado → usar resultado cacheado
- Si son distintos → procesar

**Validación:** ✅ Lógica testeada y funcionando
**Commit:** f9c1797
**Ubicación:** `app.py:1304-1349` (uploader con session_state)

---

### 2. **Lowercasing Bug - Mes guardado en minúscula** ❌ → ✅
**Problema:**
- Google Sheets (locale Spanish) interpreta "Marzo 2026" como fecha
- `value_input_option="USER_ENTERED"` causaba que Google lo guardara como "marzo 2026"
- Después, el deduplicador buscaba "Marzo 2026" pero encontraba "marzo 2026"
- No coincidían, entonces no se eliminaban las filas viejas
- **Resultado:** Acumulación infinita de datos antiguos

**Solución:**
- Cambiar `value_input_option="RAW"` en lugar de `"USER_ENTERED"`
- RAW guarda exactamente lo que se envía sin interpretar
- "Marzo 2026" → "Marzo 2026" (no cambia)
- Ahora el deduplicador encuentra coincidencias

**Validación:** ✅ Comportamiento de RAW testeado
**Commit:** 730672e
**Ubicación:**
  - `scripts/carga_semanal_ac.py:304` (guardar_resumen)
  - `scripts/carga_semanal_ac.py:369` (guardar_con_reemplazo)

---

### 3. **Deduplicación Case-Insensitive** ❌ → ✅
**Problema:**
- Aunque se use RAW, había un historial de datos con "marzo 2026" (lowercase) de antes
- Nuevo upload trae "Marzo 2026" (título case)
- Comparación exacta: "marzo 2026" != "Marzo 2026" → no se eliminaban

**Solución:**
- Normalizar todos los meses a title case ANTES de comparar
- `.str.strip().str.title()` convierte "marzo 2026" → "Marzo 2026"
- Ahora todos coinciden, y las filas viejas se reemplazan correctamente

**Validación:** ✅ Case-insensitive matching testeado
**Commit:** f9c1797
**Ubicación:** `scripts/carga_semanal_ac.py:326, 334`

---

### 4. **Pérdida de Datos por Error Mid-Process** ❌ → ✅
**Problema:**
- Código ejecutaba `hoja.clear()` inmediatamente
- Si la siguiente operación (`append_rows`) fallaba → datos perdidos
- No hay rollback en Google Sheets

**Solución:**
- Implementar patrón transaccional de 3 fases:
  1. **FASE 1:** Lectura y procesamiento completo EN RAM (sin tocar Sheets)
  2. **FASE 2:** Validación de datos en RAM (verificar que haya filas válidas)
  3. **FASE 3:** Escritura en Sheets (solo después de validar todo)
- Si cualquier cosa falla en Fase 1 o 2, Sheets no se modifica

**Validación:** ✅ Patrón transaccional testeado
**Commit:** 5419602
**Ubicación:** `scripts/carga_semanal_ac.py:262-306` (guardar_resumen), `309-371` (guardar_con_reemplazo)

---

### 5. **Google Sheets Quota Exceeded (429)** ⚠️ → ℹ️
**Problema:**
- Dashboard con 6+ tabs simultaneas leyendo de Google Sheets
- Cada tab hace múltiples `get_all_records()` requests
- Rápidamente se alcanza rate limit: "429 Too Many Requests"
- Antes: Error duro y dashboard roto

**Solución:**
- Usar `BackOffHTTPClient` de gspread
- Implementa exponential backoff automático (1s, 2s, 4s, 8s...)
- Reintenta automáticamente en caso de 429
- No causa error, solo espera más

**Validación:** ✅ BackOffHTTPClient configurado
**Commit:** 5419602
**Ubicación:** `scripts/conexion_sheets.py:19-21, 82-84, 101-103`
**Nota:** No es una "cura" completa (pueden seguir siendo lento), pero evita fallos duros.

---

## Datos Corruptos - Restauración

**Estado Pre-Fixes (2026-03-30 17:36):**
- Marzo 2026: 460 registros ✅ (correcto)
- Ticket average: ~$357 USD ✅ (correcto)

**Estado Post-Bugs (antes de limpiar):**
- Marzo 2026: 9,200 registros ❌ (20 copias de 460)
- Ticket average: $27 USD ❌ (incorrecta, $164,218 / 9,200 = $17.85)
- Razón: Infinite loop ejecutó 20+ veces

**Acción Realizada:**
- Restaurado el dataset correcto de 460 registros para Marzo
- Normalizado todos los meses a title case en AC Ventas Detalle y AC Ventas Mensual
- Recalculado métricas: Ticket promedio ahora correcto

---

## Testing Realizado

### Tests Unitarios (test_fixes.py)
```
TEST 1: Case-insensitive matching ...................... [PASS]
TEST 2: RAW value_input_option .......................... [PASS]
TEST 3: Session state logic ............................. [PASS]
TEST 4: Transactional pattern ........................... [PASS]

RESULTADO: 4/4 tests pasaron
```

### Testing Recomendado (Manual)
1. **Cargar Excel de Abril 2026** (próximo viernes)
   - Verificar que las 460 filas de Marzo se reemplazan correctamente
   - Verificar ticket average vuelve a ~$357
   - Verificar no hay datos duplicados

2. **Verificar session_state**
   - Cargar mismo archivo dos veces
   - Debe mostrar resultado cacheado en segundo intento

3. **Verificar RAW value_input_option**
   - En Google Sheets, mes debe ser "Marzo 2026" (title case)
   - No debe ser "marzo 2026" (lowercase)

---

## Archivos Modificados

| Archivo | Cambios | Commits |
|---------|---------|---------|
| `app.py` | Session state tracking en uploader | f9c1797, ca370cc |
| `scripts/carga_semanal_ac.py` | RAW option, case-insensitive, 3-fase pattern | 730672e, f9c1797, 5419602 |
| `scripts/conexion_sheets.py` | BackOffHTTPClient import y setup | 5419602 |

---

## Próximos Pasos

### Inmediato (Esta Semana)
- [ ] Cargar Excel de Abril 2026 para validación
- [ ] Verificar datos en Google Sheets (meses title case)
- [ ] Confirmar ticket average es correcto

### Corto Plazo (Próximas 2 Semanas)
- [ ] Revisar otros tabs (tab_pipeline, tab_vendedores, etc.) por bugs similares
- [ ] Validar que BackOffHTTPClient resuelve los 429 errors
- [ ] Mejorar UI de "Ventas del Mes" para indicar workflows semanales

### Mediano Plazo (Proyecto)
- [ ] Automatizar regeneración diaria de Odoo API Key
- [ ] Implementar alertas automáticas (Email/WhatsApp/Telegram)
- [ ] ML models: Churn scoring y Opportunity scoring

---

## Referencias

**Documentación del Proyecto:**
- `project_farkim.md` - Contexto completo del proyecto
- `README.md` - Setup local y estructura

**Commits Relevantes:**
- f9c1797: Loop infinito + case-insensitive
- 730672e: RAW value_input_option
- 5419602: BackOffHTTPClient + transactional safety

---

**Última revisión:** 2026-03-31 por Marcos Joaquin
