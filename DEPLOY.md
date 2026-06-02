# Despliegue de CONY POS

## Servidor actual
- VPS Hostinger - Ubuntu 24.04
- IP: 2.25.153.27
- Puerto: 8200
- SSH: puerto 22022

## Usuarios del sistema
- superuser / 1234
- admin / 1234
- cajero1 / 1234
- esme / 1234
- neto / 1234

## Dependencias
- Python 3 + FastAPI + uvicorn
- SQLite3
- bcrypt

## Inicio
```bash
cd /var/www/pos+ia/clientes/cony/backend
nohup python3 -m uvicorn pos_cony:app --host 0.0.0.0 --port 8200 &
```
