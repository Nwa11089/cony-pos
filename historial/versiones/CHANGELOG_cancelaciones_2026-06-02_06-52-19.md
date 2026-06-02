# Nuevo: Sistema de Cancelaciones con autorización de Admin
# Fecha: 2026-06-02_06-52-19 UTC

## Archivos modificados
- pos_cony.py — backend (nuevos endpoints + validación de cierre)
- dashboard.html — frontend (nuevo estado pendiente-autorizacion)
- admin.html — frontend (nueva pestaña Cancelaciones)

## Flujo de cancelación

### Cajero cancela un pedido:
1. En dashboard > Pedidos, el cajero selecciona "Cancelar" en el select
2. El backend detecta que NO es admin/superuser → estado cambia a 4 "pendiente-autorizacion"
3. El pedido se muestra con badge 🟡 Warning en la lista
4. El pedido NO se descuenta del corte (sigue contando)

### Admin autoriza/rechaza:
1. Admin entra a Admin Panel > pestaña **Cancelaciones** 🅧
2. Ve la lista de pedidos pendientes con botones ✅ Aceptar / ❌ Rechazar
3. ✅ Aceptar → pedido pasa a cancelado (estado 0), se descuenta del corte
4. ❌ Rechazar → pedido regresa a pendiente (estado 1)

### Restricciones:
- El cierre de corte NO permite cerrar si hay pedidos en estado "pendiente-autorizacion"
- El mensaje específica: "cancelaciones pendientes de autorizar"
- Solo admin/superuser ven la pestaña Cancelaciones

### Nuevos endpoints:
- GET /api/cancelaciones/pendientes — lista pedidos estado=4 (admin)
- PUT /api/cancelaciones/{pid}/autorizar — admin autoriza (estado 4→0)
- PUT /api/cancelaciones/{pid}/rechazar — admin rechaza (estado 4→1)

### Estados actualizados:
0 = cancelado
1 = pendiente
2 = completado
3 = en-preparacion
4 = pendiente-autorizacion 🆕

## Estado
- Cancelación con autorización de admin funcional ✅
- Bloqueo de cierre si hay pendientes ✅
- Admin puede aceptar/rechazar ✅
- Cajero no puede cancelar directo ✅

