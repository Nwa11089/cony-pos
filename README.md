# 🧪 Semillero — CONY POS

Sistema POS para restaurantes con delivery integrado.

## Estado actual
- **Stack:** Python FastAPI + SQLite + HTML/JS plano
- **Demo:** `pos.arnet.mx` (:8204)
- **Producción (CONY):** `cony.pos.arnet.mx` (:8200)
- **Manual:** `arnet.mx/manual`

## Módulos activos
- ✅ Comandero (toma de pedidos en caja)
- ✅ Menú digital público
- ✅ Panel Delivery (webhooks Rappi/Uber/Didi)
- ✅ Repartidores y asignación
- ✅ Cortes de caja
- ✅ Impresión (cola SQL + print-client)
- ✅ **Inventario con recetas** (productos-ingredientes, descuento automático)
- ✅ Manual del sistema (técnico, workflow, guía visual)

## Pendientes
- [ ] Migrar DEMO → CONY
- [ ] Integración Clip (cobro con tarjeta real)
- [ ] Lealtad/Cashback para clientes registrados
- [ ] Respaldo automático a Drive

## Repositorio
- Rama `main`: código funcional
- Rama `respaldos`: backups históricos

## Última actualización
2026-06-08 — Módulo de inventario/recetas + manual completo
