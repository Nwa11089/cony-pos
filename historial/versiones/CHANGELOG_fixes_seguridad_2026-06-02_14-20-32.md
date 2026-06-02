# Fixes de Seguridad y Estabilidad
# Fecha: 2026-06-02_14-20-32 UTC

## 4 Fixes aplicados

### 1. CORS 🔴
- Antes: allow_origins=["*"] → cualquiera podía hacer requests
- Ahora: allow_origins=["http://2.25.153.27:8200"] + allow_credentials=True
- Cambio: 1 línea en backend

### 2. bcrypt 🔴
- Antes: SHA256 sin salt (vulnerable a tablas arcoíris)
- Ahora: bcrypt con salt (12 rounds)
- Se agregó import bcrypt
- Función hash_bcrypt() y verify_bcrypt()
- verify_login: intenta bcrypt primero, fallback a SHA256 (transición)
- Todos los usuarios migrados a bcrypt
- Creación de nuevos usuarios y cambio de password ahora usan bcrypt

### 3. Rutas HTML protegidas 🔴
- Antes: /dashboard, /admin, /app.js, /app.css se servían sin autenticación
- Ahora: solicitan credenciales Basic Auth
  - Sin auth → redirigen a /login (307)
  - Con auth → sirven normalmente
  - /admin restringido a superuser/admin (403 si no)
  - /login y /api/auth/login siguen públicos
- Nueva función auxiliar: _check_auth(request)
- Se agregó import de RedirectResponse

### 4. Transacción atómica en cierre de corte 🔴
- Antes: operaciones sueltas → si el servidor fallaba a medio cierre, datos inconsistentes
- Ahora: conn.execute("BEGIN") al inicio, conn.commit() al final
- Si falla HTTPException: conn.rollback()
- Si falla Exception: conn.rollback() + HTTP 500
- finally: conn.close()

## Archivos modificados
- /var/www/pos+ia/clientes/cony/backend/pos_cony.py
- /var/www/pos+ia/clientes/cony/db/cony.db (hashes migrados)

## Pruebas realizadas
- Login de todos los usuarios: admin, superuser, cajero1, neto, esme ✅
- Login con credenciales incorrectas: rechazado ✅
- Dashboard sin auth: redirige a /login ✅
- Admin con cajero1: 403 ✅
- Cierre de corte con transacción: funciona correctamente ✅
- Diferencia en cierre: /usr/bin/bash.00 ✅

