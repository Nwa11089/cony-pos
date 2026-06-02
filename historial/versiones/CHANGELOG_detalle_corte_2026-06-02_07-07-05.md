# Mejora: Detalle de Corte con resumen y pedidos expandibles
# Fecha: 2026-06-02_07-07-05 UTC

## Cambios

### Backend (pos_cony.py)
- Nuevo endpoint: GET /api/pedidos/{pid} — devuelve pedido con productos_lista parseado

### Frontend Admin (admin.html)
- Al hacer clic en "Ver" en un corte, ahora muestra:
  1. **📊 RESUMEN DEL CORTE** con tarjetas: fondo inicial, efectivo, tarjeta, transferencia, servicio, total con fondo, arqueo reportado y diferencia (con colores verde/amarillo/rojo)
  2. **Tabla de pedidos** con columnas: Folio, Cliente, Total, Método pago, Estado, Fecha/Hora
  3. Cada pedido tiene botón **"Ver"** que expande un detalle con:
     - Datos del cliente, teléfono, método, total, nota, fecha
     - **📦 Partidas**: lista de cada producto, cantidad, precio unitario y subtotal
  4. Botón **🖨️** (placeholder para futura reimpresión de ticket)

### Columnas de cortes (cambio anterior reafirmado)
- Columna Fondo agregada
- Total = métodos + fondo
- Entregado = total_arqueado

