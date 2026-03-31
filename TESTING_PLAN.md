# Plan de Validación - Carga Semanal Excel (Semana 3)

## Objetivo
Validar que los 5 fixes funcionan correctamente en un escenario real de producción con datos de April 2026.

---

## Validación Phase 1: Lógica de Código ✅
**Status:** COMPLETADO
- Test 1: Case-insensitive matching → [PASS]
- Test 2: RAW value_input_option → [PASS]
- Test 3: Session state logic → [PASS]
- Test 4: Transactional pattern → [PASS]

**Resultado:** La lógica de todos los fixes es correcta y ha sido validada.

---

## Validación Phase 2: Testing Real (Próximo Viernes)

### 2.1 - Cargar Excel de Abril 2026
**Qué hacer:**
1. El próximo viernes (Abril 4, 2026), exportar Excel semanal desde Alto Cerró
2. En el dashboard, ir a **"Cargar Excel semanal"** expander
3. Seleccionar el archivo y observar el resultado

**Qué verificar:**
- ✅ El uploader NO reprocesa el archivo si lo dejas seleccionado
- ✅ El ticket promedio debe ser ~$350-400 USD (según dato histórico)
- ✅ Los datos de Marzo se reemplazan completamente (no se acumulan)
- ✅ No hay errores en la consola de navegador (F12 → Console)

**Resultado Esperado:**
```
✅ 460 registros cargados (2026-04-01 al 2026-04-30)
— Total: $164,218 USD
```

### 2.2 - Verificar Datos en Google Sheets
**Qué hacer:**
1. Abrir Google Sheets: "Farkim - Base de Datos"
2. Ir a hoja "AC Ventas Detalle"
3. Desplazarse y revisar el mes

**Qué verificar:**
- ✅ Mes debe ser "Abril 2026" (title case, no "abril 2026")
- ✅ No hay datos de Marzo en esta hoja (fueron reemplazados)
- ✅ Hoja "AC Ventas Mensual" tiene "Abril 2026" con ticket promedio correcto

### 2.3 - Verificar Session State
**Qué hacer:**
1. Cargar Excel una vez (verifica que procesa)
2. Sin recargar la página, clickear el uploader nuevamente
3. Seleccionar el mismo archivo
4. Observar resultado

**Qué verificar:**
- ✅ Segunda vez: debe mostrar "✅ 460 registros cargados..." sin procesar
- ✅ No debe decir "Procesando..." ni hacer spinning loader
- ✅ Debe mostrar resultado cacheado de la primera carga

### 2.4 - Verificar No hay Regresiones
**Qué hacer:**
1. Navegar por todas las pestañas del dashboard
2. Verificar que cada pestaña carga correctamente

**Qué verificar:**
- ✅ Tab "Ventas del Mes" muestra datos correctos
- ✅ Tab "Pipeline Completo" carga sin errores
- ✅ Tab "Vendedores" muestra datos correctos
- ✅ Tab "Histórico" muestra últimos 10 años correctamente
- ✅ Tab "Evolución" muestra gráficos sin errores

### 2.5 - Monitorear 429 Errors
**Qué hacer:**
1. Mientras navegas el dashboard, abre DevTools (F12 → Network)
2. Filtra por "googleapis" y busca errores 429

**Qué verificar:**
- ✅ No debe haber errores 429 visibles
- Si hay: el dashboard debe recuperarse automáticamente (BackOffHTTPClient reintentando)

---

## Criterios de Aceptación

| Criterio | Expected | Resultado |
|----------|----------|-----------|
| Uploader no reprocesa mismo archivo | ✅ | |
| Ticket average es ~$350+ | ✅ | |
| Mes en Google Sheets es title case | ✅ | |
| Datos viejos se reemplazan (no acumulan) | ✅ | |
| Session state cachea resultado | ✅ | |
| Todas las tabs cargan correctamente | ✅ | |
| No hay 429 errors o se recupera | ✅ | |

---

## Si Hay Problemas

### Uploader reprocesa múltiples veces
- [ ] Verificar que `app.py` tiene `session_state` tracking (línea 1304+)
- [ ] Verificar que el spinner existe (línea 1331)

### Mes se guarda en minúscula
- [ ] Verificar que `carga_semanal_ac.py` usa `value_input_option="RAW"` (línea 304, 369)
- [ ] Verificar que month matching usa `.str.title()` (línea 326, 334)

### Datos viejos no se eliminan (acumulación)
- [ ] Verificar que `guardar_con_reemplazo()` tiene 3-fase pattern
- [ ] Verificar que FASE 1 (lectura en RAM) ocurre antes de FASE 3 (escritura)

### 429 errors constantes
- [ ] Verificar que `BackOffHTTPClient` está importado (línea 19 en conexion_sheets.py)
- [ ] Verificar que se usa en `autenticar()` (línea 82-84, 101-103)
- [ ] Reducir frecuencia de refreshes en dashboard (aumentar TTL en @st.cache_data)

---

## Próximas Acciones

### Si Testing Fase 2 es EXITOSO:
1. Proceder con Week 4-5: Análisis Exploratorio (EDA)
2. Optimizar otras tabs por bugs similares
3. Implementar Looker Studio dashboard (Week 6-7)

### Si Testing Fase 2 Falla:
1. Diagnosticar específicamente qué falló
2. Crear test unitario para reproducer
3. Fijar el issue
4. Re-validar

---

## Timeline

| Fecha | Tarea | Status |
|-------|-------|--------|
| Mar 31 | Fixes development + unit tests | ✅ DONE |
| Apr 4 (Viernes) | Upload real Excel de Abril | ⏳ PENDING |
| Apr 7 | Review results + sign-off | ⏳ PENDING |
| Apr 14+ | Week 4-5: EDA | ⏳ PENDING |

---

**Documento creado:** 2026-03-31
**Responsable:** Marcos Joaquin
