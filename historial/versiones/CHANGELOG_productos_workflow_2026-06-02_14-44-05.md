# Productos + Workflow de personalización
# Fecha: $(date -u '+%Y-%m-%d %H:%M:%S UTC')

## Cambios en DB
- Nueva tabla: `complementos` (ingredientes como tomate, cebolla, col, etc.)
- Nueva tabla: `salsas` (con nivel de picor 0-4)
- Nueva tabla: `producto_complementos` (relación producto ↔ ingrediente)
- Nueva tabla: `producto_salsas` (relación producto ↔ salsa)
- Nuevo producto: Hot dog con mezcla de 3 quesos ($65)
- Precios corregidos:
  - Hamburguesa sencilla: $60 → $75
  - Hamburguesa de pollo: $75 → $60
  - Hot dog suizo/hawaiano: $65 → $75
  - Hot dog con queso asadero: $65 → $60
- Complementos asignados a hot dogs (tomate, cebolla, col, papas)
- Complementos asignados a hamburguesa sencilla

## Nuevos endpoints backend
- GET /api/productos/{pid}/complementos — ingredientes de un producto
- GET /api/productos/{pid}/salsas — salsas disponibles para un producto
- GET /api/complementos — todos los complementos
- GET /api/salsas — todas las salsas con nivel de picor

## Nuevo modal de personalización en dashboard
- Al seleccionar producto con complementos/salsas → modal de personalización
- Ingredientes vienen "activados" (con todo) → el cajero desactiva lo que NO lleva
- Salsas con indicador de picor (😇 Sin picor → 🔥🔥🔥🔥 Extremo)
- Extras opcionales (tipo aros de cebolla, boneless extra para Crazy burguer)
- Observaciones libres
- Preview de la personalización en el carrito con ícono 📝
- La nota se guarda en el JSON de productos

## Salsas disponibles
1. Ranch (😇) 2. BBQ (😇) 3. Mostaza miel (😇) 4. Cheddar (😇)
5. Chipotle cremoso (🌶️) 6. Ranch jalapeño (🌶️) 7. Cheddar jalapeño (🌶️)
8. BBQ picoso (🌶️🌶️) 9. Búffalo (🌶️🌶️) 10. Mango habanero (🌶️🌶️🌶️)
11. Búffalo habanero (🔥🔥🔥🔥)

## Productos con salsas
- Alitas (id=22, 23)
- Hamburguesa con boneless (id=9)
- Hot dog boneless (id=4)

## Pendiente
- Asignar complementos a las demás hamburguesas
- Mostrar la nota de personalización en la comanda impresa
