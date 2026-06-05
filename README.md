# CONY POS - Sistema de Punto de Venta

Sistema POS para restaurante CONY con impresión automática a impresoras térmicas.

## Estructura

- `backend/` - API FastAPI (pos_cony.py)
- `frontend/` - Cliente de impresión con ESC/POS (print-client.py)
- `db/` - Esquema de base de datos SQLite
- `scripts/` - Scripts de utilidad

## Instalación Rápida

### Backend
```bash
python3 backend/pos_cony.py --port 8200 --db demo_cony.db
```

### Agente de Impresión (Caja)
```bash
python3 frontend/print-client.py --rol caja --ip 192.168.100.68
```

### Agente de Impresión (Cocina)
```bash
python3 frontend/print-client.py --rol cocina --ip 192.168.100.69
```
