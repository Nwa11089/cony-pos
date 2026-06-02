# Análisis de Perplexity - Sistema POS CONY

> Fecha: 2026-06-02 (madrugada)
> Prompt enviado a Perplexity por Neto Alv

---

## Veredicto General

Tu stack actual **sí es viable** para un restaurante pequeño como CONY, pero ya estás entrando en una etapa donde el valor no está en "tener más pantallas", sino en cerrar huecos operativos, endurecer seguridad y quitar cuellos de botella antes de que te afecten en horas pico. FastAPI + Bootstrap no es tu problema hoy; tus riesgos reales son más bien SQLite bajo concurrencia, CORS abierto, manejo de sesión/Auth en frontend y ausencia probable de controles operativos típicos de POS comerciales ligeros.

---

## 1. Faltantes Operativos

Comparado con POS ligeros para restaurantes pequeños, ya cubres bastante bien caja, pedidos, autorizaciones y roles, pero aún faltan piezas que suelen volverse críticas cuando sube el volumen o delegas operación a empleados.

**Prioridad alta:**
- **Inventario básico por insumo** — no solo catálogo de productos; descuento automático de pan, salchicha, alitas, aderezos, bebidas y extras por venta, alertas de reposición y merma
- **Modificadores reales de producto** — "sin cebolla", "extra queso", "combo", "tamaño", "2 salsas"; en comida rápida esto evita notas libres y reduce errores operativos
- **Impresión o envío a cocina por estación** — separar cocina/barra/caja
- **Reimpresión de ticket**, duplicado de comanda, historial completo por pedido y auditoría de edición de precio/cantidad/descuento
- **Descuentos controlados**, cortesías, promociones por horario y combos
- **Modo delivery/recoger/comer en local** mejor estructurado con tiempos prometidos
- **Reportes de utilidad bruta aproximada** — costo estimado por producto
- **Cierre por turno/cajero**, no solo corte global
- **Respaldos automáticos** y restauración sencilla

---

## 2. Riesgos de Seguridad

**Mayor fortaleza:** Ya manejas roles, contraseñas hasheadas y autorizaciones administrativas.

**Riesgos identificados:**

1. **CORS abierto** — si está realmente abierto a cualquier origen, facilitas abuso desde sitios externos. Cerrarlo a dominios exactos.
2. **Basic Auth desde sessionStorage** — débil para app web porque cualquier XSS puede leerlo
3. **Probable falta de CSRF/XSS hardening** — sanitización de campos editables, notas y nombres de cliente
4. **SQLite en VPS expuesto** — integridad y disponibilidad; apagado brusco o bloqueo por escrituras concurrentes puede tumbar operación
5. **Posible falta de rate limiting** en login y endpoints sensibles
6. **Bitácora insuficiente para seguridad** — registrar IP, usuario, timestamp y diff exacto
7. **Backups y secretos** — si la DB vive en el mismo VPS sin respaldo externo cifrado

**Prioridad de seguridad:**
1. Cerrar CORS a dominios específicos
2. Migrar de Basic Auth a sesión firmada o JWT corto con refresh controlado
3. Añadir CSP, escape estricto de HTML y revisión de cualquier innerHTML
4. Rate limiting para login y acciones administrativas
5. Backups automáticos cifrados y prueba de restauración
6. Logs de auditoría más detallados

---

## 3. Escalabilidad

FastAPI en 1 vCPU y 2 GB RAM puede seguir bien si el tráfico es bajo o moderado. El cuello real es **SQLite** cuando hay más escrituras concurrentes.

**Recomendaciones:**
- Mantente en FastAPI, separa escalabilidad inmediata de migración mayor
- Activa **WAL en SQLite**, foreign_keys=ON, índices en pedidos, estatus, fecha, usuario y corte_id
- Mueve tareas lentas a background jobs (notificaciones, reportes pesados, backups)
- Estandariza acceso a DB con SQLAlchemy/SQLModel
- Si piensas crecer a más terminales → **PostgreSQL**, no cambiar de framework
- Añade caché ligera para catálogos y reportes de dashboard

**Regla práctica:** Si ya tienes más de 3-5 usuarios simultáneos escribiendo, o piensas abrir otra sucursal, empieza a planear PostgreSQL desde ahora.

---

## 4. Notificaciones de Corte

Arquitectura recomendada:
- Cuando el endpoint de cierre confirma el corte → genera evento interno `corte_cerrado`
- Ese evento manda tarea asíncrona con resumen (sucursal, cajero, hora, folio, fondo, venta total, arqueo, diferencia)
- **Telegram** > WhatsApp para alertas operativas (más rápido, barato, sencillo)
- WhatsApp después si quieres formato más empresarial

Mensaje recomendado: Sucursal, usuario que cerró, hora, fondo inicial, total ventas, efectivo esperado, efectivo arqueado, diferencia, método de pago resumido, link al detalle del corte.

---

## 5. Framework

| Decisión | Recomendación | Motivo |
|---|---|---|
| Backend | Quédate en FastAPI | Ya funciona, ligero, suficiente para una sucursal |
| Frontend | Bootstrap + JS | Para POS interno importa más velocidad y estabilidad |
| BD | Planea migración a PostgreSQL | SQLite será tu primer límite real |
| Reescritura total | No ahora | Alto costo, poco retorno inmediato |
| Refactor interno | Sí, gradual | Más auditoría, seguridad, colas y modularidad |

Solo considera Django/Laravel si: abrirás varias sucursales pronto, necesitas más desarrolladores entrando, o tu código actual ya es difícil de mantener.

**Veredicto:** No migres de framework. Migra de base de datos y endurece seguridad primero.

---

## 6. Prioridad Sugerida

1. Endurecer seguridad: CORS, sesión/Auth, sanitización y rate limiting
2. Backups automáticos y plan de recuperación
3. PostgreSQL como siguiente paso técnico grande
4. Inventario por insumo + modificadores + descuentos auditables
5. Notificación automática de corte por Telegram desde backend
6. Reportes de utilidad, ventas por hora y desempeño por cajero

> Tu sistema ya está más avanzado que muchos POS "ligeros" hechos a medida; ahora el reto ya no es construir más rápido, sino hacerlo más **operable, seguro y resistente**.

---

## Fuentes citadas por Perplexity

[1] Does FastAPI Work With SQLite? - StackCompat
[2] Learn 10 Crucial Security Practices for Your Restaurant POS - Clotouch
[3] Top Restaurant POS Systems - POSzeo
[4] Restaurant POS Systems: Features, Benefits - Salesplay
[5] How to Choose the Perfect POS for Your Small Restaurant - POSEase
[6] Guide to Restaurant POS Systems (2026 Edition) - myr.io
[7] 7 Essential Features Your Restaurant POS Software Must Have - Clotouch
[8] 12 Essential Features Every Restaurant POS System Needs - Applova
[9] Secure Your Business With Retail POS Security - SumUp
[10] What to Look for in a POS System for a Small Restaurant - Star Micronics
[11] How to Protect Your Restaurants Data from Cyber Threats - RestaurantSoftwareManagement
[12] A Guide to Restaurant Security Systems and Theft Protection - Business.com
[13] SQL (Relational) Databases - FastAPI
[14] 44 Restaurant POS Features You Shouldn't Miss in 2026 - Quantic
[15] Integrating SQLite with FastAPI - LinkedIn
