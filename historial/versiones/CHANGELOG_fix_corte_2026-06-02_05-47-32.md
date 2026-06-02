# Fix flujo corte de caja: 2026-06-02_05-47-32 UTC

## Archivos modificados
- `dashboard.html` (navbar + funciones JS)

## Cambios aplicados

### 1. Botón "Cerrar Corte" en navbar
- Nuevo botón `btnCerrarCorteNav` (amarillo, candado) al lado de "Abrir Corte"
- Visible solo cuando HAY corte abierto
- Cualquier usuario (admin o cajero) puede cerrar corte

### 2. Flujo de cierre → logout
- Al cerrar corte exitosamente: muestra resumen, luego llama a `logout()`
- El siguiente usuario deberá autenticarse y abrir su propio corte

### 3. Validación de pedidos con corte
- Si no hay `corteAbierto`, muestra alerta y abre el modal de apertura
- Antes intentaba `showTab('corte', ...)` que ya no existe

### 4. Modal de apertura forzado
- Se reforzó: backdrop static, keyboard false, listener para bloquear Escape
- No tiene botón de cerrar (ni X)
- Solo se puede salir: abriendo corte o recargando página

### 5. Botón manual "Abrir Corte"
- Ya existía, se mantiene. Si cierran el modal de alguna forma, desde navbar se reabre.

## Estado
- Dashboard funcional ✅
- Corte obligatorio para operar ✅
- Corte para todos los usuarios ✅
- Admin funcional con cortes desglosados ✅
- Respaldo pre-cambio disponible

