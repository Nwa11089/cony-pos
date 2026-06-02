# Cambio: Arqueo de caja + Seguridad en corte de caja
# Fecha: 2026-06-02_06-13-30 UTC

## Archivos modificados
- `dashboard.html` - frontend (función cerrarCorte + nuevo modal arqueo)
- `pos_cony.py` - backend (endpoint cierre mejorado)
- `cony.db` - BD (nueva columna total_arqueado)

## Cambios

### 1. Arqueo de caja físico (reemplaza al prompt de efectivo)
**Antes:** Al cerrar corte, mostraba resumen con métodos de pago, luego preguntaba efectivo entregado
**Ahora:** Modal con denominaciones de billetes y monedas:
- 💵 ,000, 00, 00, 00, 0, 0
- 🪙 0, , , 
- 🪙 Monedas fraccionarias (input numérico libre)
- 🔴 Total en caja calculado automáticamente
- El cajero solo ve conteo físico, NO el resumen de ventas

### 2. Seguridad: Cajero NO ve diferencia
- El backend ya NO devuelve `diferencia`, `efectivo_esperado`, `metodos` ni `total_ventas` en la respuesta del POST
- La diferencia solo se calcula internamente y se guarda en DB
- Visible exclusivamente en Admin > Cortes (solo admin/superuser)

### 3. Nueva columna en BD: `total_arqueado`
- Guarda el total del conteo físico que registró el cajero
- Permite después cuadrar contra ventas del sistema

### 4. Resumen de corte preservado para futuro
Endpoint GET /api/corte/cerrar intacto (lo usaremos para notificaciones al dueño)
Documento de diseño guardado en respaldos/cony/otros/resumen_corte_actual.md

## Flujo de cierre actual
1. Cajero da clic en "Cerrar Corte" (amarillo)
2. Confirmación: "¿Estás seguro?"
3. Modal de arqueo: llena denominaciones → calcula total
4. Da clic en "Cerrar corte"
5. Sistema guarda: efectivo_reportado (ventas), total_arqueado (conteo físico), diferencia (interna)
6. Mensaje neutral: "Corte cerrado correctamente. Cerrando sesión..."
7. Logout automático

## Estado
- Dashboard: 0 pedidos en corte nuevo ✅
- Arqueo funcional con denominaciones ✅
- Cajero no ve información sensible ✅
- Admin: cortes con diferencias visibles ✅
- Clientes editables en admin ✅

