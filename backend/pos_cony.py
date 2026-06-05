"""
POS Web CONY - Backend FastAPI
Puerto: 8200 | Proyecto: CONY
"""
import hashlib
import secrets
import sqlite3
import uuid
import bcrypt
from datetime import datetime, timedelta, timezone, date
import zoneinfo

MEX_TZ = zoneinfo.ZoneInfo("America/Mexico_City")

def now_mx():
    """Devuelve datetime actual en CDMX"""
    return datetime.now(MEX_TZ)
from fastapi import FastAPI, HTTPException, Depends, status, Request, Form
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import json


app = FastAPI(title="POS CONY", version="1.0.0")

@app.middleware("http")
async def eliminar_www_authenticate(request, call_next):
    response = await call_next(request)
    if response.status_code == 401:
        # Eliminar header que causa el popup nativo del navegador
        try:
            del response.headers["www-authenticate"]
        except KeyError:
            pass
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://2.25.153.27:8200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic(auto_error=False)
DB_PATH = "/var/www/pos+ia/clientes/demo/backend/cony_rest/demo_cony.db"

# ==================== MODELOS ====================
class ProductoIn(BaseModel):
    nombre: str
    categoria: str
    precio: float
    descripcion: Optional[str] = ""
    emoji: Optional[str] = ""
    disponible: Optional[int] = 1

class UsuarioIn(BaseModel):
    nombre: str
    password: str
    rol: str = "user"
    proyecto: str = "cony"
    nombre_real: str = ""
    apellidos: str = ""
    telefono: str = ""

class PedidoUpdate(BaseModel):
    estatus: str

# ==================== SEGURIDAD ====================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def hash_bcrypt(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()

def verify_bcrypt(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

SUPERUSER_PASSWORD_HASH = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"  # viejo SHA256 de "1234"
SUPERUSER_BCRYPT_HASH = "$2b$12$0p8qgXzZq6O6tGRH62f2quj6K2Gl6iYeJ5Sz7HYGpFo/XBCpWAfIu"  # bcrypt de "1234"

def verify_login(nombre: str, password: str) -> dict | None:
    # Superuser global: no necesita estar en DB
    if nombre == "superuser":
        # Intentar bcrypt primero, fallback a SHA256
        if verify_bcrypt(password, SUPERUSER_BCRYPT_HASH):
            return {"id": 0, "nombre": "superuser", "rol": "superuser", "activo": 1}
        if hash_password(password) == SUPERUSER_PASSWORD_HASH:
            return {"id": 0, "nombre": "superuser", "rol": "superuser", "activo": 1}
        return None
    # Usuarios locales (admin, user)
    conn = get_db()
    cursor = conn.execute(
        "SELECT * FROM usuarios WHERE nombre = ? AND activo = 1",
        (nombre,)
    )
    user = cursor.fetchone()
    conn.close()
    if not user:
        return None
    db_hash = user["password"]
    # Intentar bcrypt primero, fallback a SHA256
    try:
        if verify_bcrypt(password, db_hash):
            return dict(user)
    except:
        pass
    if db_hash == hash_password(password):
        return dict(user)
    return None

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"X-No-Auth": "true"},
        )
    user = verify_login(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"X-No-Auth": "true"},
        )
    return user

# ==================== FRONTEND (SIN AUTH) ====================
@app.get("/", response_class=HTMLResponse)
def get_login():
    return HTMLResponse(open("/var/www/pos+ia/clientes/demo/frontend/frontend_demo/login.html").read())

@app.get("/login", response_class=HTMLResponse)
def get_login_page():
    return HTMLResponse(open("/var/www/pos+ia/clientes/demo/frontend/frontend_demo/login.html").read())

@app.get("/api/auth/login")
@app.post("/api/auth/login")
def api_login(user: str = "", password: str = ""):
    """Login sin Basic Auth para admin. Acepta GET y POST con params user/password."""
    if not user or not password:
        raise HTTPException(400, "Usuario y contraseña requeridos")
    user_data = verify_login(user, password)
    if not user_data:
        raise HTTPException(401, "Credenciales inválidas")
    token = hashlib.sha256(f"{user}:{password}".encode()).hexdigest()
    return {
        "token": token,
        "user": user_data["nombre"],
        "rol": user_data["rol"],
        "id": user_data["id"],
        "nombre_real": user_data.get("nombre_real", ""),
        "apellidos": user_data.get("apellidos", "")
    }

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    return HTMLResponse(open("/var/www/pos+ia/clientes/demo/frontend/frontend_demo/dashboard.html").read())

@app.get("/app.js")
def get_js():
    return HTMLResponse(open("/var/www/pos+ia/clientes/demo/frontend/frontend_demo/app.js").read())

@app.get("/app.css")
def get_css():
    return HTMLResponse(open("/var/www/pos+ia/clientes/demo/frontend/frontend_demo/app.css").read())

@app.get("/favicon.svg")
def get_favicon():
    return HTMLResponse(open("/var/www/pos+ia/clientes/demo/frontend/frontend_demo/favicon.svg").read())

# ==================== API PRODUCTOS ====================
@app.get("/api/productos")
def listar_productos(user: dict = Depends(authenticate)):
    conn = get_db()
    cursor = conn.execute("SELECT * FROM productos ORDER BY categoria, nombre")
    productos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return productos

@app.post("/api/productos")
def crear_producto(p: ProductoIn, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "Sin permisos")
    conn = get_db()
    conn.execute(
        "INSERT INTO productos (nombre, categoria, precio, descripcion, emoji, disponible) VALUES (?,?,?,?,?,?)",
        (p.nombre, p.categoria, p.precio, p.descripcion, p.emoji, p.disponible)
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "mensaje": f"Producto {p.nombre} creado"}

@app.put("/api/productos/{pid}")
def actualizar_producto(pid: int, p: ProductoIn, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "Sin permisos")
    conn = get_db()
    conn.execute(
        "UPDATE productos SET nombre=?, categoria=?, precio=?, descripcion=?, emoji=?, disponible=? WHERE id=?",
        (p.nombre, p.categoria, p.precio, p.descripcion, p.emoji, p.disponible, pid)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/productos/{pid}")
def eliminar_producto(pid: int, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "Sin permisos")
    conn = get_db()
    conn.execute("DELETE FROM productos WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# ==================== API PEDIDOS ====================
@app.get("/api/pedidos")
def listar_pedidos(entregados_por: int = None, user: dict = Depends(authenticate)):
    conn = get_db()
    # Si se filtra por entregados_por, devolver entregados de ese repartidor (hoy)
    if entregados_por is not None:
        cursor = conn.execute("""
            SELECT p.*, c.nombre as cliente_nombre, c.telefono
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE p.entregado_por=1 AND p.repartidor_id=? AND date(p.fecha_entrega)=date("now","localtime")
            ORDER BY p.fecha_entrega DESC
        """, (entregados_por,))
    else:
        cursor = conn.execute("SELECT id, estado FROM cortes WHERE estado='abierto' ORDER BY id DESC LIMIT 1")
        corte_activo = cursor.fetchone()
        if corte_activo:
            corte_id = corte_activo["id"]
            cursor = conn.execute("""
                SELECT p.*, c.nombre as cliente_nombre, c.telefono
                FROM pedidos p
                LEFT JOIN clientes c ON p.cliente_id = c.id
                WHERE p.corte_id = ?
                ORDER BY p.fecha DESC LIMIT 100
            """, (corte_id,))
        else:
            conn.close()
            return []
    pedidos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return pedidos

@app.put("/api/pedidos/{pid}/estatus")
def actualizar_estatus(pid: int, data: PedidoUpdate, user: dict = Depends(authenticate)):
    conn = get_db()
    estados = {"pendiente":1, "en-preparacion":3, "completado":2, "cancelado":0, "pendiente-autorizacion":4, 1:1, 2:2, 3:3, 0:0, 4:4}
    val = estados.get(data.estatus if isinstance(data.estatus, str) else data.estatus, 1)
    # Si un cajero elige cancelar, va a pendiente-autorizacion (no directo a cancelado)
    if val == 0 and user["rol"] not in ("superuser", "admin"):
        val = 4  # pendiente-autorizacion
    # Obtener estatus anterior
    cursor = conn.execute("SELECT estado FROM pedidos WHERE id=?", (pid,))
    row = cursor.fetchone()
    anterior = row[0] if row else None
    from datetime import datetime
    ahora = now_mx().isoformat()
    conn.execute("UPDATE pedidos SET estado=? WHERE id=?", (val, pid))
    # Registrar en log
    conn.execute(
        "INSERT INTO orden_estatus_log (pedido_id, estatus_anterior, estatus_nuevo, usuario, fecha) VALUES (?,?,?,?,?)",
        (pid, anterior, val, user["nombre"], ahora)
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "estado": val}
    return {"status": "ok"}

@app.get("/api/pedidos/{pid}")
def obtener_pedido(pid: int, user: dict = Depends(authenticate)):
    """Obtener un pedido con detalle de productos"""
    conn = get_db()
    cursor = conn.execute("""
        SELECT p.*, c.nombre as cliente_nombre, c.telefono
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.id = ?
    """, (pid,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Pedido no encontrado")
    pedido = dict(row)
    estados_map = {1:"pendiente",2:"completado",3:"en-preparacion",0:"cancelado",4:"pendiente-autorizacion"}
    pedido["estatus"] = estados_map.get(pedido.get("estado"), "pendiente")
    # Parsear productos
    try:
        pedido["productos_lista"] = json.loads(pedido.get("productos", "[]")) if pedido.get("productos") else []
    except:
        pedido["productos_lista"] = []
    conn.close()
    return pedido

@app.get("/api/pedidos/{pid}/estatus-log")
def estatus_log(pid: int, user: dict = Depends(authenticate)):
    conn = get_db()
    estados = {1:"pendiente",2:"completado",3:"en-preparacion",0:"cancelado",4:"pendiente-autorizacion"}
    cursor = conn.execute(
        """SELECT el.*, p.folio, p.total, c.nombre as cliente
           FROM orden_estatus_log el
           LEFT JOIN pedidos p ON el.pedido_id = p.id
           LEFT JOIN clientes c ON p.cliente_id = c.id
           WHERE el.pedido_id = ?
           ORDER BY el.id""",
        (pid,)
    )
    logs = []
    for row in cursor.fetchall():
        d = dict(row)
        d["estatus_anterior_texto"] = estados.get(d.get("estatus_anterior"), "-")
        d["estatus_nuevo_texto"] = estados.get(d.get("estatus_nuevo"), "?")
        logs.append(d)
    conn.close()
    return logs

# ==================== API REPORTES ====================
@app.get("/api/reportes/ventas-hoy")
def ventas_hoy(user: dict = Depends(authenticate)):
    conn = get_db()
    # Solo del corte activo
    c = conn.execute("SELECT id FROM cortes WHERE estado='abierto' LIMIT 1")
    corte = c.fetchone()
    if not corte:
        conn.close()
        return {"total_pedidos": 0, "total_ventas": 0}
    hoy = now_mx().strftime("%Y-%m-%d")
    cursor = conn.execute(
        "SELECT COUNT(*) as total_pedidos, COALESCE(SUM(total),0) as total_ventas FROM pedidos WHERE fecha LIKE ? AND estado != 0 AND corte_id = ?",
        (hoy+"%", corte["id"])
    )
    res = dict(cursor.fetchone())
    conn.close()
    return res
    conn = get_db()
    cursor = conn.execute("""
        SELECT nombre, COUNT(*) as veces_vendido, SUM(precio) as total
        FROM productos
        GROUP BY nombre
        ORDER BY veces_vendido DESC LIMIT 10
    """)
    top = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return top

@app.get("/api/reportes/ventas-rango")
def ventas_rango(desde: str, hasta: str, user: dict = Depends(authenticate)):
    conn = get_db()
    cursor = conn.execute("""
        SELECT DATE(fecha) as dia, COUNT(*) as pedidos, COALESCE(SUM(total),0) as total
        FROM pedidos
        WHERE DATE(fecha) BETWEEN ? AND ? AND estatus != 'cancelado'
        GROUP BY DATE(fecha)
        ORDER BY dia
    """, (desde, hasta))
    ventas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return ventas

# ==================== API USUARIOS (solo superuser) ====================
@app.get("/api/me")
def quien_soy(user: dict = Depends(authenticate)):
    return {
        "nombre": user["nombre"],
        "rol": user["rol"],
        "id": user["id"],
        "activo": user["activo"],
        "nombre_real": user.get("nombre_real", ""),
        "apellidos": user.get("apellidos", "")
    }

@app.get("/api/usuarios")
def listar_usuarios(user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cursor = conn.execute("SELECT id, nombre, rol, proyecto, activo, nombre_real, apellidos, telefono FROM usuarios WHERE rol != ?", ("superuser",))
    return [dict(row) for row in cursor.fetchall()]

@app.post("/api/usuarios")
def crear_usuario_endpoint(u: UsuarioIn, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    if u.rol == "superuser" and user["rol"] != "superuser":
        raise HTTPException(403, "No puedes crear usuarios superuser")
    conn = get_db()
    conn.execute(
        "INSERT INTO usuarios (nombre, password, rol, proyecto, nombre_real, apellidos, telefono) VALUES (?,?,?,?,?,?,?)",
        (u.nombre, hash_bcrypt(u.password), u.rol, u.proyecto, u.nombre_real or "", u.apellidos or "", u.telefono or "")
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.put("/api/usuarios/{uid}/datos")
def actualizar_datos_usuario(uid: int, data: dict, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    conn.execute(
        "UPDATE usuarios SET nombre_real=?, apellidos=?, telefono=? WHERE id=?",
        (data.get("nombre_real", ""), data.get("apellidos", ""), data.get("telefono", ""), uid)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.put("/api/usuarios/{uid}/password")
def cambiar_password(uid: int, password: str, user: dict = Depends(authenticate)):
    if user["rol"] != "superuser" and user["id"] != uid:
        raise HTTPException(403, "No puedes cambiar password de otro usuario")
    conn = get_db()
    conn.execute("UPDATE usuarios SET password=? WHERE id=?", (hash_bcrypt(password), uid))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.put("/api/usuarios/{uid}/toggle")
def toggle_usuario(uid: int, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    c = conn.execute("SELECT activo FROM usuarios WHERE id=?", (uid,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Usuario no encontrado")
    nuevo = 0 if row["activo"] else 1
    conn.execute("UPDATE usuarios SET activo=? WHERE id=?", (nuevo, uid))
    conn.commit()
    conn.close()
    return {"status": "ok", "activo": nuevo}

@app.post("/api/comandar")
def comandar_endpoint(data: dict, user: dict = Depends(authenticate)):
    import requests
    payload = {
        "token": data.get("token", "mi_token_secreto_123"),
        "telefono": "0000000000",
        "nombre": data.get("nombre", "Mostrador"),
        "metodo_entrega": "recoger",
        "metodo_pago": data.get("metodo_pago", "Efectivo"),
        "nota": data.get("nota", ""),
        "total": data.get("total", 0),
        "productos": data.get("productos", "[]")
    }
    try:
        r = requests.post("http://127.0.0.1:8000/webhook", json=payload, timeout=5)
        if r.status_code == 200:
            return r.json()
        return {"status": "ok", "pedido_id": 0, "folio": "LOCAL-" + str(uuid.uuid4()).upper()[:8]}
    except:
        return {"status": "ok", "pedido_id": 0, "folio": "LOCAL-" + str(uuid.uuid4()).upper()[:8]}


@app.get("/api/clientes/{telefono}")
def buscar_cliente(telefono: str, user: dict = Depends(authenticate)):
    conn = get_db()
    c = conn.execute("SELECT id, nombre, telefono, direccion FROM clientes WHERE telefono = ?", (telefono,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

@app.put("/api/clientes/{cid}")
def actualizar_cliente(cid: int, data: dict, user: dict = Depends(authenticate)):
    """Actualizar datos de un cliente."""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    conn.execute(
        "UPDATE clientes SET nombre=?, telefono=?, direccion=? WHERE id=?",
        (data.get("nombre", ""), data.get("telefono", ""), data.get("direccion", ""), cid)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.post("/api/comandar_directo")
def comandar_directo(data: dict, user: dict = Depends(authenticate)):
    """Crea pedido directo en la DB con teléfono. Valida corte abierto."""
    import sqlite3
    import uuid
    from datetime import datetime
    
    db = globals().get("DB_PATH", "/var/www/pos+ia/clientes/cony/cony_rest/cony_cony.db")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    
    try:
        # === Validar que haya un corte abierto ===
        c.execute("SELECT id FROM cortes WHERE estado='abierto' LIMIT 1")
        corte = c.fetchone()
        if not corte:
            conn.close()
            raise HTTPException(400, "No hay corte de caja abierto. Debes abrir caja antes de generar pedidos.")
        corte_id = corte[0]
        
        folio = str(uuid.uuid4()).upper()[:8]
        ahora = now_mx().isoformat()
        total = float(data.get("total", 0))
        nota = data.get("nota", "")
        prds = data.get("productos", "[]")
        nombre = data.get("nombre", "Mostrador")
        metodo_pago = data.get("metodo_pago", "Efectivo")
        metodo_entrega = "recoger"
        telefono = data.get("telefono", "0000000000")
        direccion = data.get("direccion", "Mostrador")
        
        # Buscar o crear cliente por teléfono
        c.execute("SELECT id, nombre, direccion FROM clientes WHERE telefono = ?", (telefono,))
        cl = c.fetchone()
        if cl:
            cliente_id = cl[0]
            # Siempre actualizar nombre y dirección si el usuario los envió
            updates = []
            params = []
            if nombre and nombre != 'Mostrador' and nombre != (cl[1] or ''):
                updates.append("nombre=?")
                params.append(nombre)
            if direccion and direccion != 'Mostrador' and direccion != (cl[2] or ''):
                updates.append("direccion=?")
                params.append(direccion)
            if (not cl[1] or cl[1] == 'Mostrador') and nombre and nombre != 'Mostrador':
                updates.append("nombre=?")
                params.append(nombre)
            if (not cl[2] or cl[2] == 'Mostrador') and direccion and direccion != 'Mostrador':
                updates.append("direccion=?")
                params.append(direccion)
            if updates:
                params.append(cliente_id)
                c.execute(f"UPDATE clientes SET {', '.join(updates)} WHERE id=?", params)
        else:
            c.execute("INSERT INTO clientes (telefono, nombre, direccion) VALUES (?,?,?)",
                      (telefono, nombre, direccion))
            cliente_id = c.lastrowid
        
        creado_por_id = user.get("id") if user else None
        creador_nombre = user.get("nombre_real", "") + " " + user.get("apellidos", "")
        creador_nombre = creador_nombre.strip() or user.get("user", "admin")

        c.execute("""INSERT INTO pedidos (cliente_id, folio, productos, total, metodo_pago, metodo_entrega, nota, estado, estado_pago, fecha, corte_id, creado_por_id, creado_por_nombre)
                    VALUES (?,?,?,?,?,?,?,1,0,?,?,?,?)""",
                  (cliente_id, folio, prds, total, metodo_pago, metodo_entrega, nota, ahora, corte_id, creado_por_id, creador_nombre))
        
        conn.commit()
        pedido_id = c.lastrowid

        # === ENCOLAR TICKETS DE IMPRESIÓN AUTOMÁTICAMENTE ===
        try:
            prds_list = json.loads(prds) if isinstance(prds, str) else prds

            # 1) TICKET CAJA
            ticket_caja_contenido = {
                "folio": folio,
                "cliente": nombre,
                "metodo_pago": metodo_pago,
                "total": total,
                "productos": [{"nombre": p.get("nombre", "?"), "cantidad": p.get("cantidad", 1), "precio": p.get("precio", 0)} for p in prds_list],
                "fecha": ahora
            }
            c.execute("""INSERT INTO impresoras_cola (pedido_id, folio, tipo, contenido, estado)
                        VALUES (?, ?, 'caja', ?, 'pendiente')""",
                      (pedido_id, folio, json.dumps(ticket_caja_contenido)))

            # 2) TICKET COMANDA — agrupar TODOS los productos en UN SOLO ticket por rol
            #    Así no se imprime la misma comanda repetida
            comandas_por_rol = {}  # rol -> lista de productos
            for p in prds_list:
                prod_id = p.get("id", 0)
                c.execute("SELECT clasificacion_superior_id FROM productos WHERE id=?", (prod_id,))
                row_p = c.fetchone()
                cs_id = row_p[0] if row_p else 1
                c.execute("SELECT rol_impresora FROM rol_impresora_mapeo WHERE clasificacion_superior_id=?", (cs_id,))
                row_m = c.fetchone()
                rol = row_m[0] if row_m else "cocina"

                if rol not in comandas_por_rol:
                    comandas_por_rol[rol] = []
                comandas_por_rol[rol].append({
                    "producto": p.get("nombre", "?"),
                    "cantidad": p.get("cantidad", 1),
                    "precio": p.get("precio", 0)
                })

            for rol, productos_agrupados in comandas_por_rol.items():
                contenido_comanda = {
                    "folio": folio,
                    "cliente": nombre,
                    "nota": nota,
                    "productos": productos_agrupados,
                    "fecha": ahora,
                    "creado_por": creador_nombre
                }
                c.execute("""INSERT INTO impresoras_cola (pedido_id, folio, tipo, contenido, estado)
                            VALUES (?, ?, ?, ?, 'pendiente')""",
                          (pedido_id, f"C-{folio}", rol, json.dumps(contenido_comanda)))

            conn.commit()
        except Exception as e_enc:
            print(f"[ERROR encolar impresión] {e_enc}")
            conn.rollback()

        conn.commit()
        # Incrementar métrica del día
        hoy = now_mx().strftime("%Y-%m-%d")
        conn.execute("INSERT INTO metricas (fecha, pedidos_recibidos) VALUES (?, 1) ON CONFLICT(fecha) DO UPDATE SET pedidos_recibidos = pedidos_recibidos + 1", (hoy,))
        conn.commit()
        conn.close()
        return {"status": "ok", "pedido_id": pedido_id, "folio": folio, "message": f"Pedido registrado. Folio: {folio}"}
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        return {"status": "error", "message": str(e)}

# ==================== CORTE DE CAJA ====================
@app.get("/api/corte/estado")
def corte_estado(user: dict = Depends(authenticate)):
    """Ver si hay un corte abierto. Si no, el frontend bloquea pedidos."""
    conn = get_db()
    c = conn.execute("SELECT * FROM cortes WHERE estado='abierto' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"estado": "ninguno", "mensaje": "No hay corte abierto. Debes abrir caja."}


@app.post("/api/corte/abrir")
def corte_abrir(data: dict, user: dict = Depends(authenticate)):
    """Abrir un nuevo corte de caja con fondo inicial."""
    from datetime import datetime
    fondo = float(data.get("fondo_inicial", 0))
    if fondo < 0:
        raise HTTPException(400, "El fondo inicial no puede ser negativo")
    conn = get_db()
    # Verificar que no haya un corte abierto
    c = conn.execute("SELECT id FROM cortes WHERE estado='abierto' LIMIT 1")
    if c.fetchone():
        conn.close()
        raise HTTPException(400, "Ya hay un corte de caja abierto. Ciérralo primero.")
    ahora = now_mx()
    conn.execute(
        "INSERT INTO cortes (estado, fondo_inicial, fecha_apertura, hora_apertura, usuario_apertura) VALUES (?,?,?,?,?)",
        ("abierto", fondo, ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"), user["nombre"])
    )
    corte_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return {"status": "ok", "corte_id": corte_id, "mensaje": f"Corte #{corte_id} abierto con fondo de ${fondo:.2f}"}


@app.get("/api/corte/resumen")
def corte_resumen(user: dict = Depends(authenticate)):
    """Resumen del corte activo: ventas agrupadas por método de pago + totales."""
    conn = get_db()
    # Buscar corte abierto
    c = conn.execute("SELECT * FROM cortes WHERE estado='abierto' ORDER BY id DESC LIMIT 1")
    corte = c.fetchone()
    if not corte:
        conn.close()
        return {"estado": "ninguno", "mensaje": "No hay corte abierto"}
    corte = dict(corte)
    # Ventas agrupadas por método de pago (solo pedidos de este corte, no cancelados)
    cursor = conn.execute(
        """SELECT metodo_pago, COUNT(*) as cantidad, COALESCE(SUM(total),0) as subtotal
           FROM pedidos
           WHERE corte_id = ? AND estado != 0
           GROUP BY metodo_pago
           ORDER BY subtotal DESC""",
        (corte["id"],)
    )
    metodos = [dict(r) for r in cursor.fetchall()]
    total_ventas = sum(m["subtotal"] for m in metodos)
    # Totales
    total_ingresos = corte.get("total_ingresos", 0) or 0
    total_gastos = corte.get("total_gastos", 0) or 0
    # Efectivo en caja = fondo_inicial + efectivo_ventas + ingresos - gastos
    efectivo_ventas = sum(m["subtotal"] for m in metodos if m["metodo_pago"] == "Efectivo")
    efectivo_en_caja = corte["fondo_inicial"] + efectivo_ventas + total_ingresos - total_gastos
    conn.close()
    return {
        "corte": corte,
        "metodos": metodos,
        "total_ventas": round(total_ventas, 2),
        "total_ingresos": round(total_ingresos, 2),
        "total_gastos": round(total_gastos, 2),
        "efectivo_en_caja": round(efectivo_en_caja, 2),
        "fondo_inicial": corte["fondo_inicial"]
    }


@app.get("/api/corte/cerrar")
def corte_cerrar_confirmacion(user: dict = Depends(authenticate)):
    """Obtener datos de cierre para confirmación final (no cierra aún)."""
    conn = get_db()
    c = conn.execute("SELECT * FROM cortes WHERE estado='abierto' ORDER BY id DESC LIMIT 1")
    corte = c.fetchone()
    if not corte:
        conn.close()
        raise HTTPException(400, "No hay corte abierto")
    corte = dict(corte)
    cursor = conn.execute(
        """SELECT metodo_pago, COUNT(*) as cantidad, COALESCE(SUM(total),0) as subtotal
           FROM pedidos
           WHERE corte_id = ? AND estado != 0
           GROUP BY metodo_pago
           ORDER BY subtotal DESC""",
        (corte["id"],)
    )
    metodos = [dict(r) for r in cursor.fetchall()]
    total_ventas = sum(m["subtotal"] for m in metodos)
    total_ingresos = corte.get("total_ingresos", 0) or 0
    total_gastos = corte.get("total_gastos", 0) or 0
    # Efectivo esperado
    efectivo_ventas = sum(m["subtotal"] for m in metodos if m["metodo_pago"] == "Efectivo")
    efectivo_en_caja = corte["fondo_inicial"] + efectivo_ventas + total_ingresos - total_gastos
    conn.close()
    return {
        "corte": corte,
        "metodos": metodos,
        "total_ventas": round(total_ventas, 2),
        "total_ingresos": round(total_ingresos, 2),
        "total_gastos": round(total_gastos, 2),
        "efectivo_en_caja": round(efectivo_en_caja, 2),
        "fondo_inicial": corte["fondo_inicial"]
    }


@app.post("/api/corte/cerrar")
def corte_cerrar(data: dict, user: dict = Depends(authenticate)):
    """Cerrar el corte de caja activo. Todo dentro de una transacción atómica."""
    conn = get_db()
    try:
        # INICIAR TRANSACCIÓN
        conn.execute("BEGIN")
        
        c = conn.execute("SELECT * FROM cortes WHERE estado='abierto' ORDER BY id DESC LIMIT 1")
        corte = c.fetchone()
        if not corte:
            raise HTTPException(400, "No hay corte abierto")
        corte = dict(corte)
        
        # Validar que NO haya pedidos pendientes (estado=1,3,4)
        pendientes = conn.execute(
            "SELECT COUNT(*) FROM pedidos WHERE corte_id = ? AND estado NOT IN (2, 0, 5)",
            (corte["id"],)
        ).fetchone()[0]
        canc_pend = conn.execute(
            "SELECT COUNT(*) FROM pedidos WHERE corte_id = ? AND estado = 4",
            (corte["id"],)
        ).fetchone()[0]
        if pendientes > 0:
            motivo = "cancelaciones pendientes de autorizar" if canc_pend > 0 else "pedidos pendientes o en preparación"
            raise HTTPException(400, f"⚠️ Hay {pendientes} {motivo}. Deben resolverse antes de cerrar corte.")
        
        # Calcular resumen final
        cursor = conn.execute(
            """SELECT metodo_pago, COALESCE(SUM(total),0) as subtotal
               FROM pedidos
               WHERE corte_id = ? AND estado != 0
               GROUP BY metodo_pago""",
            (corte["id"],)
        )
        metodos = {r["metodo_pago"]: round(r["subtotal"], 2) for r in cursor.fetchall()}
        total_ventas = sum(metodos.values())
        
        efectivo_ventas = sum(v for k, v in metodos.items() if k == "Efectivo")
        total_ingresos = corte.get("total_ingresos", 0) or 0
        total_gastos = corte.get("total_gastos", 0) or 0
        efectivo_esperado = corte["fondo_inicial"] + efectivo_ventas + total_ingresos - total_gastos
        total_arqueado = data.get("total_arqueado", 0)
        if total_arqueado:
            efectivo_reportado = round(total_arqueado - corte["fondo_inicial"], 2)
        else:
            efectivo_reportado = data.get("efectivo_reportado")
        diferencia = round(efectivo_reportado - efectivo_ventas, 2) if efectivo_reportado is not None else 0
        
        ahora = now_mx()
        conn.execute(
            """UPDATE cortes SET
                estado='cerrado',
                fecha_cierre=?,
                hora_cierre=?,
                usuario_cierre=?,
                total_ventas=?,
                total_metodos=?,
                efectivo_reportado=?,
                total_arqueado=?,
                diferencia=?,
                observaciones=?
               WHERE id=?""",
            (ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"),
             user["nombre"], round(total_ventas, 2),
             json.dumps(metodos), efectivo_reportado,
             data.get("total_arqueado", 0), diferencia,
             data.get("observaciones", ""), corte["id"])
        )
        
        # CONFIRMAR TRANSACCIÓN — TODO O NADA
        conn.commit()
        
        return {
            "status": "ok",
            "mensaje": f"Corte #{corte['id']} cerrado."
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error al cerrar corte: {str(e)}")
    finally:
        conn.close()


@app.get("/api/corte/historial")
def corte_historial(user: dict = Depends(authenticate)):
    conn = get_db()
    cursor = conn.execute(
        "SELECT * FROM cortes ORDER BY id DESC LIMIT 50"
    )
    return [dict(r) for r in cursor.fetchall()]


# ==================== CANCELACIONES (Admin) ====================
@app.get("/api/cancelaciones/pendientes")
def cancelaciones_pendientes(user: dict = Depends(authenticate)):
    """Lista pedidos pendientes de autorizar cancelación (solo admin/superuser)"""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cursor = conn.execute("""
        SELECT p.*, c.nombre as cliente_nombre, c.telefono
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.estado = 4
        ORDER BY p.fecha DESC
    """)
    pedidos = [dict(r) for r in cursor.fetchall()]
    estados_nombres = {0:"cancelado",1:"pendiente",2:"completado",3:"en-preparacion",4:"pendiente-autorizacion"}
    estados_map = {1:"pendiente",2:"completado",3:"en-preparacion",0:"cancelado",4:"pendiente-autorizacion"}
    for d in pedidos:
        d["estatus"] = estados_map.get(d.get("estado"), "pendiente")
    conn.close()
    return pedidos

@app.put("/api/cancelaciones/{pid}/autorizar")
def cancelacion_autorizar(pid: int, user: dict = Depends(authenticate)):
    """Admin autoriza la cancelación → pedido pasa a cancelado (estado 0)"""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    c = conn.execute("SELECT estado FROM pedidos WHERE id=?", (pid,))
    row = c.fetchone()
    if not row or row[0] != 4:
        conn.close()
        raise HTTPException(400, "El pedido no está pendiente de autorización")
    conn.execute("UPDATE pedidos SET estado=0 WHERE id=?", (pid,))
    conn.execute(
        "INSERT INTO orden_estatus_log (pedido_id, estatus_anterior, estatus_nuevo, usuario, fecha) VALUES (?,?,?,?,?)",
        (pid, 4, 0, user["nombre"], now_mx().isoformat()))
    conn.commit()
    conn.close()
    return {"status": "ok", "mensaje": "Cancelación autorizada"}

@app.put("/api/cancelaciones/{pid}/rechazar")
def cancelacion_rechazar(pid: int, user: dict = Depends(authenticate)):
    """Admin rechaza la cancelación → pedido regresa a pendiente (estado 1)"""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    c = conn.execute("SELECT estado FROM pedidos WHERE id=?", (pid,))
    row = c.fetchone()
    if not row or row[0] != 4:
        conn.close()
        raise HTTPException(400, "El pedido no está pendiente de autorización")
    conn.execute("UPDATE pedidos SET estado=1 WHERE id=?", (pid,))
    conn.execute(
        "INSERT INTO orden_estatus_log (pedido_id, estatus_anterior, estatus_nuevo, usuario, fecha) VALUES (?,?,?,?,?)",
        (pid, 4, 1, user["nombre"], now_mx().isoformat()))
    conn.commit()
    conn.close()
    return {"status": "ok", "mensaje": "Cancelación rechazada, pedido regresa a pendiente"}

# ==================== ADMIN ====================
@app.get("/repartidores", response_class=HTMLResponse)
def get_repartidores():
    html = open("/var/www/pos+ia/clientes/demo/frontend/frontend_demo/repartidores.html", encoding="utf-8").read()
    return HTMLResponse(html)

@app.get("/admin", response_class=HTMLResponse)
def get_admin():
    html = open("/var/www/pos+ia/clientes/demo/frontend/frontend_demo/admin.html").read()
    return HTMLResponse(html)

@app.get("/api/admin/clientes")
def admin_clientes(user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cursor = conn.execute("""
        SELECT c.*,
               COUNT(CASE WHEN p.estado = 2 THEN 1 END) as total_pedidos,
               COALESCE(SUM(CASE WHEN p.estado = 2 THEN p.total ELSE 0 END), 0) as total_gastado
        FROM clientes c
        LEFT JOIN pedidos p ON p.cliente_id = c.id
        GROUP BY c.id
        ORDER BY c.nombre
    """)
    return [dict(r) for r in cursor.fetchall()]

@app.get("/api/admin/pedidos-cliente/{cliente_id}")
def admin_pedidos_cliente(cliente_id: int, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cursor = conn.execute("""
        SELECT p.*, c.nombre as cliente_nombre, c.telefono
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.cliente_id = ?
        ORDER BY p.fecha DESC
    """, (cliente_id,))
    return [dict(r) for r in cursor.fetchall()]

@app.get("/api/admin/cortes-detalle")
def admin_cortes_detalle(user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cursor = conn.execute("""
        SELECT co.*,
            (SELECT COUNT(*) FROM pedidos WHERE corte_id = co.id AND estado != 0) as pedidos_count,
            (SELECT COALESCE(SUM(total),0) FROM pedidos WHERE corte_id = co.id AND estado != 0 AND metodo_pago = 'Efectivo') as total_efectivo,
            (SELECT COALESCE(SUM(total),0) FROM pedidos WHERE corte_id = co.id AND estado != 0 AND metodo_pago = 'Tarjeta') as total_tarjeta,
            (SELECT COALESCE(SUM(total),0) FROM pedidos WHERE corte_id = co.id AND estado != 0 AND LOWER(metodo_pago) = 'transferencia') as total_transferencia,
            (SELECT COALESCE(SUM(total),0) FROM pedidos WHERE corte_id = co.id AND estado != 0 AND LOWER(metodo_pago) LIKE '%servicio%') as total_servicio
        FROM cortes co
        ORDER BY co.id DESC LIMIT 50
    """)
    return [dict(r) for r in cursor.fetchall()]

@app.get("/api/admin/pedidos-corte/{corte_id}")
def admin_pedidos_corte(corte_id: int, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cursor = conn.execute("""
        SELECT p.*, c.nombre as cliente_nombre, c.telefono
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.corte_id = ?
        ORDER BY p.fecha DESC
    """, (corte_id,))
    return [dict(r) for r in cursor.fetchall()]


# ==================== COMPLEMENTOS Y SALSAS ====================
@app.get("/api/productos/{pid}/complementos")
def producto_complementos(pid: int, user: dict = Depends(authenticate)):
    """Obtener complementos (ingredientes) de un producto.
    Con obligatorio=1 vienen incluidos por defecto y se pueden quitar.
    Con obligatorio=0 son extras opcionales."""
    conn = get_db()
    comps = conn.execute("""
        SELECT c.id, c.nombre, c.tipo, pc.obligatorio
        FROM complementos c
        JOIN producto_complementos pc ON pc.complemento_id = c.id
        WHERE pc.producto_id = ? AND c.activo = 1
        ORDER BY pc.obligatorio DESC, c.orden
    """, (pid,)).fetchall()
    conn.close()
    return [dict(r) for r in comps]

@app.get("/api/productos/{pid}/salsas")
def producto_salsas(pid: int, user: dict = Depends(authenticate)):
    """Obtener salsas disponibles para un producto."""
    conn = get_db()
    salsas = conn.execute("""
        SELECT s.id, s.nombre, s.nivel_picor,
               CASE s.nivel_picor
                   WHEN 0 THEN '😇 Sin picor'
                   WHEN 1 THEN '🌶️ Suave'
                   WHEN 2 THEN '🌶️🌶️ Medio'
                   WHEN 3 THEN '🌶️🌶️🌶️ Picante'
                   WHEN 4 THEN '🔥🔥🔥🔥 Extremo'
               END as picor_label
        FROM salsas s
        JOIN producto_salsas ps ON ps.salsa_id = s.id
        WHERE ps.producto_id = ? AND s.activo = 1
        ORDER BY s.nivel_picor, s.orden
    """, (pid,)).fetchall()
    conn.close()
    return [dict(r) for r in salsas]

@app.get("/api/complementos")
def listar_complementos(user: dict = Depends(authenticate)):
    """Todos los complementos disponibles (para admin)."""
    conn = get_db()
    comps = conn.execute("SELECT * FROM complementos WHERE activo=1 ORDER BY tipo, orden").fetchall()
    conn.close()
    return [dict(r) for r in comps]

@app.get("/api/salsas")
def listar_salsas(user: dict = Depends(authenticate)):
    """Todas las salsas disponibles."""
    conn = get_db()
    ss = conn.execute("""
        SELECT *, CASE nivel_picor
            WHEN 0 THEN '😇 Sin picor'
            WHEN 1 THEN '🌶️ Suave'
            WHEN 2 THEN '🌶️🌶️ Medio'
            WHEN 3 THEN '🌶️🌶️🌶️ Picante'
            WHEN 4 THEN '🔥🔥🔥🔥 Extremo'
        END as picor_label
        FROM salsas WHERE activo=1 ORDER BY nivel_picor, orden
    """).fetchall()
    conn.close()
    return [dict(r) for r in ss]

# ==================== INICIO ====================

# ==================== CONFIGURACIÓN WHATSAPP ====================

@app.get("/api/config/wp")
def get_wp_config(user: dict = Depends(authenticate)):
    """Obtiene configuración de WhatsApp del negocio."""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cfg = {}
    for row in conn.execute("SELECT clave, valor FROM config WHERE clave LIKE 'wp_%'").fetchall():
        cfg[row["clave"]] = row["valor"]
    conn.close()
    # También ver si el bot está conectado
    conectado = False
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://127.0.0.1:8203/qr-status", timeout=2)
        data = json.loads(resp.read())
        conectado = data.get("connected", False)
    except:
        pass
    return {
        "numero": cfg.get("wp_numero_negocio", ""),
        "nombre_negocio": cfg.get("wp_nombre_negocio", ""),
        "conectado": conectado
    }

@app.put("/api/config/wp")
def update_wp_config(data: dict, user: dict = Depends(authenticate)):
    """Actualiza configuración de WhatsApp (número, nombre del negocio)."""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    if "numero" in data:
        conn.execute("INSERT OR REPLACE INTO config (clave, valor) VALUES ('wp_numero_negocio', ?)", (data["numero"],))
    if "nombre_negocio" in data:
        conn.execute("INSERT OR REPLACE INTO config (clave, valor) VALUES ('wp_nombre_negocio', ?)", (data["nombre_negocio"],))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# ==================== REPARTIDORES ====================

@app.get("/api/repartidores")
def listar_repartidores(user: dict = Depends(authenticate)):
    """Lista todos los repartidores activos desde usuarios"""
    conn = get_db()
    rr = conn.execute("""
        SELECT u.id, u.nombre, u.telefono, u.email, u.activo,
               COALESCE((SELECT COUNT(*) FROM pedidos WHERE repartidor_id=u.id AND entregado_por=0 AND estado>=1), 0) as pedidos_asignados
        FROM usuarios u
        WHERE u.rol='repartidor' AND u.activo=1
        ORDER BY u.nombre
    """).fetchall()
    conn.close()
    return [dict(r) for r in rr]

@app.post("/api/repartidores")
def crear_repartidor(data: dict, user: dict = Depends(authenticate)):
    """Crea un nuevo repartidor en usuarios (rol=repartidor)."""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "Solo administradores pueden crear repartidores")
    conn = get_db()
    # Validar que el nombre no exista
    existe = conn.execute("SELECT id FROM usuarios WHERE nombre = ?", (data["nombre"],)).fetchone()
    if existe:
        conn.close()
        raise HTTPException(409, f"El nombre de usuario '{data['nombre']}' ya existe. Elige otro nombre.")
    hashed = hash_bcrypt(data["password"])
    c = conn.execute(
        "INSERT INTO usuarios (nombre, password, rol, proyecto, telefono, email, activo) VALUES (?,?,?,?,?,?,?)",
        (data["nombre"], hashed, "repartidor", "cony", data.get("telefono",""), data.get("email",""), 1)
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return {"id": new_id, "status": "ok"}

@app.get("/api/repartidores/{rid}")
def get_repartidor(rid: int, user: dict = Depends(authenticate)):
    """Obtiene un repartidor desde usuarios."""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    r = conn.execute(
        "SELECT id, nombre, telefono, email, activo FROM usuarios WHERE id=? AND rol='repartidor'",
        (rid,)
    ).fetchone()
    conn.close()
    if not r:
        raise HTTPException(404, "Repartidor no encontrado")
    return dict(r)

@app.put("/api/repartidores/{rid}")
def actualizar_repartidor(rid: int, data: dict, user: dict = Depends(authenticate)):
    """Actualiza datos de un repartidor en usuarios."""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "Solo administradores pueden modificar repartidores")
    conn = get_db()
    if "nombre" in data:
        existe = conn.execute("SELECT id FROM usuarios WHERE nombre = ? AND id != ?", (data["nombre"], rid)).fetchone()
        if existe:
            conn.close()
            raise HTTPException(409, f"El nombre de usuario '{data['nombre']}' ya existe. Elige otro nombre.")
    campos = []
    valores = []
    for k in ("nombre", "telefono", "email", "activo"):
        if k in data:
            campos.append(f"{k}=?")
            valores.append(data[k])
    if "password" in data and data["password"]:
        campos.append("password=?")
        valores.append(hash_bcrypt(data["password"]))
    if campos:
        valores.append(rid)
        conn.execute(f"UPDATE usuarios SET {', '.join(campos)} WHERE id=? AND rol='repartidor'", tuple(valores))
        conn.commit()
    conn.close()
    return {"status": "ok"}

@app.put("/api/pedidos/{pid}/asignar-repartidor")
def asignar_repartidor(pid: int, data: dict, user: dict = Depends(authenticate)):
    """Asigna un repartidor a un pedido."""
    repartidor_id = data.get("repartidor_id")
    conn = get_db()
    conn.execute("UPDATE pedidos SET repartidor_id=? WHERE id=?", (repartidor_id, pid))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.put("/api/pedidos/{pid}/completar-con-repartidor")
def completar_con_repartidor(pid: int, data: dict, user: dict = Depends(authenticate)):
    """Cambia estatus a completado y asigna repartidor de una sola vez."""
    repartidor_id = data.get("repartidor_id")
    ahora = now_mx().isoformat()
    conn = get_db()
    cursor = conn.execute("SELECT estado FROM pedidos WHERE id=?", (pid,))
    row = cursor.fetchone()
    anterior = row["estado"] if row else None
    conn.execute("UPDATE pedidos SET estado=2, repartidor_id=?, fecha_terminado=? WHERE id=?", (repartidor_id, ahora, pid))
    conn.execute(
        "INSERT INTO orden_estatus_log (pedido_id, estatus_anterior, estatus_nuevo, usuario, fecha) VALUES (?,?,?,?,?)",
        (pid, anterior, 2, user.get("nombre","admin"), ahora)
    )
    conn.commit()
    conn.close()
    return {"status": "completado", "repartidor_asignado": repartidor_id}

@app.put("/api/pedidos/{pid}/entregar")
def marcar_entregado(pid: int, user: dict = Depends(authenticate)):
    """Repartidor marca pedido como entregado."""
    from datetime import datetime
    conn = get_db()
    ahora = now_mx().isoformat()
    conn.execute("UPDATE pedidos SET estado=5, entregado_por=1, fecha_entrega=?, entregado_por_nombre=? WHERE id=?", (ahora, user.get("nombre","repartidor"), pid))
    cursor = conn.execute("SELECT estado FROM pedidos WHERE id=?", (pid,))
    anterior = cursor.fetchone()
    conn.execute(
        "INSERT INTO orden_estatus_log (pedido_id, estatus_anterior, estatus_nuevo, usuario, fecha) VALUES (?,?,?,?,?)",
        (pid, anterior[0] if anterior else None, 5, user.get("nombre","repartidor"), ahora)
    )
    conn.commit()
    conn.close()
    return {"status": "entregado", "fecha": ahora}

@app.get("/api/repartidor/login")
def login_repartidor(user: str = "", password: str = ""):
    """Login para repartidores (reutiliza verify_login)."""
    if not user or not password:
        raise HTTPException(400, "Usuario y contraseña requeridos")
    user_data = verify_login(user, password)
    if not user_data:
        raise HTTPException(401, "Credenciales inválidas")
    if user_data.get("rol") != "repartidor":
        raise HTTPException(403, "Acceso denegado: no eres repartidor")
    return {"id": user_data["id"], "nombre": user_data["nombre"], "status": "ok"}

@app.get("/api/repartidor/{rid}/pedidos")
def pedidos_repartidor(rid: int):
    """Pedidos asignados a un repartidor (sin auth - usa login por query)."""
    conn = get_db()
    pp = conn.execute("""
        SELECT p.*, c.nombre as cliente_nombre, c.telefono, c.direccion
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.repartidor_id=? AND p.entregado_por=0 AND p.estado >= 1
        ORDER BY p.fecha ASC
    """, (rid,)).fetchall()
    conn.close()
    return [dict(p) for p in pp]

@app.get("/api/repartidores/stats")
def stats_repartidores(user: dict = Depends(authenticate)):
    """Estadísticas de repartidores (desde usuarios)."""
    conn = get_db()
    rr = conn.execute("""
        SELECT u.id, u.nombre, u.telefono,
               COUNT(CASE WHEN p.entregado_por=0 AND p.estado>=1 THEN 1 END) as en_ruta,
               COUNT(CASE WHEN p.entregado_por=1 THEN 1 END) as entregados,
               COALESCE(SUM(CASE WHEN p.entregado_por=1 THEN p.total END), 0) as total_entregado
        FROM usuarios u
        LEFT JOIN pedidos p ON p.repartidor_id = u.id
        WHERE u.rol='repartidor' AND u.activo=1
        GROUP BY u.id
    """).fetchall()
    conn.close()

# ==================== MÉTRICAS ====================
@app.get("/api/metricas")
def get_metricas(user: dict = Depends(authenticate)):
    """Devuelve métricas de operación del sistema."""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    rows = conn.execute("SELECT * FROM metricas ORDER BY fecha DESC LIMIT 31").fetchall()
    conn.close()
    totales = {"pedidos":0, "mensajes_enviados":0, "mensajes_recibidos":0, "tickets_cobro":0, "tickets_cocina":0}
    for r in rows:
        totales["pedidos"] += r["pedidos_recibidos"]
        totales["mensajes_enviados"] += r["mensajes_enviados"]
        totales["mensajes_recibidos"] += r["mensajes_recibidos"]
        totales["tickets_cobro"] += r["tickets_cobro"]
        totales["tickets_cocina"] += r["tickets_cocina"]
    hoy = date.today().isoformat()
    hoy_row = [r for r in rows if r["fecha"] == hoy]
    return {
        "hoy": dict(hoy_row[0]) if hoy_row else {},
        "totales": totales,
        "detalle": [dict(r) for r in rows]
    }

@app.put("/api/admin/cambiar-password")
def cambiar_password(data: dict, user: dict = Depends(authenticate)):
    """Cambia la contraseña de un usuario (admin/superuser pueden cambiar cualquier pass)."""
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    
    user_id = data.get("user_id")
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    
    if not user_id or not new_password:
        raise HTTPException(400, "Faltan datos requeridos")
    if len(new_password) < 3:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 3 caracteres")
    
    conn = get_db()
    target = conn.execute("SELECT id, nombre, password FROM usuarios WHERE id=?", (user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(404, "Usuario no encontrado")
    
    # Verificar contraseña anterior
    if old_password:
        db_hash = target["password"]
        try:
            if not verify_bcrypt(old_password, db_hash):
                conn.close()
                raise HTTPException(401, "La contraseña anterior es incorrecta")
        except:
            if db_hash != hash_password(old_password):
                conn.close()
                raise HTTPException(401, "La contraseña anterior es incorrecta")
    
    # Actualizar con nueva contraseña
    new_hash = hash_bcrypt(new_password)
    conn.execute("UPDATE usuarios SET password=? WHERE id=?", (new_hash, user_id))
    conn.commit()
    conn.close()
    return {"status": "ok", "usuario": target["nombre"]}


# ============================================================
# MEJORAS V2.0 — Endpoints nuevos
# AGREGAR ANTES de if __name__ == "__main__"
# NO modificar nada existente
# ============================================================

# --- Clasificaciones Superiores ---
@app.get("/api/clasificaciones-superiores")
def listar_clasificaciones_superiores(user: dict = Depends(authenticate)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM clasificaciones_superiores ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/clasificaciones-superiores")
def crear_clasificacion_superior(data: dict, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cur = conn.execute("INSERT INTO clasificaciones_superiores (nombre, descripcion) VALUES (?, ?)",
                       (data["nombre"], data.get("descripcion", "")))
    conn.commit()
    conn.close()
    return {"id": cur.lastrowid, "status": "ok"}

@app.put("/api/clasificaciones-superiores/{cid}")
def actualizar_clasificacion_superior(cid: int, data: dict, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    conn.execute("UPDATE clasificaciones_superiores SET nombre=?, descripcion=? WHERE id=?",
                 (data["nombre"], data.get("descripcion", ""), cid))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/clasificaciones-superiores/{cid}")
def eliminar_clasificacion_superior(cid: int, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    conn.execute("DELETE FROM clasificaciones_superiores WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# --- Subclasificaciones ---
@app.get("/api/clasificaciones")
def listar_clasificaciones(clasificacion_superior_id: int = None, user: dict = Depends(authenticate)):
    conn = get_db()
    if clasificacion_superior_id:
        rows = conn.execute("SELECT * FROM clasificaciones WHERE clasificacion_superior_id=? ORDER BY id",
                          (clasificacion_superior_id,)).fetchall()
    else:
        rows = conn.execute("SELECT c.*, cs.nombre as superior_nombre FROM clasificaciones c "
                          "LEFT JOIN clasificaciones_superiores cs ON c.clasificacion_superior_id=cs.id "
                          "ORDER BY c.id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/clasificaciones")
def crear_clasificacion(data: dict, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cur = conn.execute("INSERT INTO clasificaciones (nombre, clasificacion_superior_id, descripcion) VALUES (?, ?, ?)",
                       (data["nombre"], data["clasificacion_superior_id"], data.get("descripcion", "")))
    conn.commit()
    conn.close()
    return {"id": cur.lastrowid, "status": "ok"}

@app.put("/api/clasificaciones/{cid}")
def actualizar_clasificacion(cid: int, data: dict, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    conn.execute("UPDATE clasificaciones SET nombre=?, clasificacion_superior_id=?, descripcion=? WHERE id=?",
                 (data["nombre"], data["clasificacion_superior_id"], data.get("descripcion", ""), cid))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/clasificaciones/{cid}")
def eliminar_clasificacion(cid: int, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    conn.execute("DELETE FROM clasificaciones WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# --- Impresoras Config ---
@app.get("/api/impresoras-config")
def listar_impresoras(user: dict = Depends(authenticate)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM impresoras_config ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/impresoras-config")
def crear_impresora(data: dict, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cur = conn.execute("""INSERT INTO impresoras_config (nombre, rol, direccion_ip, puerto, activa, notas)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (data["nombre"], data["rol"], data.get("direccion_ip", "192.168.100.100"),
         data.get("puerto", 9100), data.get("activa", 1), data.get("notas", "")))
    conn.commit()
    conn.close()
    return {"id": cur.lastrowid, "status": "ok"}

@app.put("/api/impresoras-config/{iid}")
def actualizar_impresora(iid: int, data: dict, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    conn.execute("""UPDATE impresoras_config SET nombre=?, rol=?, direccion_ip=?, puerto=?, activa=?, notas=?
        WHERE id=?""",
        (data["nombre"], data["rol"], data.get("direccion_ip", "192.168.100.100"),
         data.get("puerto", 9100), data.get("activa", 1), data.get("notas", ""), iid))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/api/impresoras-config/{iid}")
def eliminar_impresora(iid: int, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    conn.execute("DELETE FROM impresoras_config WHERE id=?", (iid,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# --- Mapeo Clasificación → Rol Impresora ---
@app.get("/api/rol-impresora-mapeo")
def listar_mapeo(user: dict = Depends(authenticate)):
    conn = get_db()
    rows = conn.execute("""SELECT r.*, cs.nombre as clasificacion_nombre
        FROM rol_impresora_mapeo r
        LEFT JOIN clasificaciones_superiores cs ON r.clasificacion_superior_id=cs.id
        ORDER BY r.id""").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/rol-impresora-mapeo")
def crear_mapeo(data: dict, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cur = conn.execute("INSERT INTO rol_impresora_mapeo (clasificacion_superior_id, rol_impresora) VALUES (?, ?)",
                       (data["clasificacion_superior_id"], data["rol_impresora"]))
    conn.commit()
    conn.close()
    return {"id": cur.lastrowid, "status": "ok"}

@app.delete("/api/rol-impresora-mapeo/{mid}")
def eliminar_mapeo(mid: int, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    conn.execute("DELETE FROM rol_impresora_mapeo WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# --- Cola de Impresión ---
@app.get("/api/cola-imprimir/pendientes")
def cola_pendientes(tipo: str = "caja", user: dict = Depends(authenticate)):
    """
    Devuelve tickets pendientes para una impresora específica.
    ?tipo=caja | cocina | cafe | barra_fria (debe coincidir con impresoras_config.rol)
    """
    conn = get_db()
    rows = conn.execute("""SELECT c.*, p.nombre as impresora_nombre
        FROM impresoras_cola c
        LEFT JOIN impresoras_config p ON p.rol=?
        WHERE c.tipo=? AND c.estado='pendiente' ORDER BY c.id""", (tipo, tipo)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/imprimir")
def encolar_impresion(data: dict, user: dict = Depends(authenticate)):
    """Encola un ticket para imprimir. Busca la impresora según el tipo de ticket (caja/cocina/barra)."""
    if user["rol"] not in ("superuser", "admin", "user"):
        raise HTTPException(403, "No autorizado")
    
    pedido_folio = data.get("pedido_folio", "")
    pedido_id = data.get("pedido_id", 0)
    tipo = data.get("tipo", "caja")  # caja, cocina, barra
    contenido = json.dumps(data.get("ticket", data.get("contenido", "")))
    
    conn = get_db()
    cur = conn.execute("""INSERT INTO impresoras_cola (pedido_id, folio, tipo, contenido, estado)
        VALUES (?, ?, ?, ?, 'pendiente')""", (pedido_id, pedido_folio, tipo, contenido))
    conn.commit()
    conn.close()
    return {"id": cur.lastrowid, "status": "encolado"}

@app.post("/api/cola-imprimir/{cid}/enviado")
def marcar_enviado(cid: int, user: dict = Depends(authenticate)):
    conn = get_db()
    conn.execute("UPDATE impresoras_cola SET estado='enviado', fecha_envio=datetime('now','-6 hours') WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return {"status": "enviado"}

@app.post("/api/cola-imprimir/{cid}/confirmar")
def confirmar_impresion(cid: int, user: dict = Depends(authenticate)):
    conn = get_db()
    conn.execute("UPDATE impresoras_cola SET estado='impreso', fecha_envio=datetime('now','-6 hours') WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return {"status": "impreso"}

@app.post("/api/cola-imprimir/{cid}/error")
def reportar_error_impresion(cid: int, data: dict, user: dict = Depends(authenticate)):
    conn = get_db()
    conn.execute("""UPDATE impresoras_cola SET estado='error', intentos=intentos+1, error=?
        WHERE id=?""", (data.get("error", "Error desconocido"), cid))
    conn.commit()
    conn.close()
    return {"status": "error reportado"}

# --- Nivel de Confianza Clientes ---
@app.get("/api/admin/clientes-confianza")
def listar_clientes_confianza(user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    rows = conn.execute("SELECT id, nombre, telefono, nivel_confianza FROM clientes ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.put("/api/admin/clientes/{cid}/confianza")
def actualizar_confianza(cid: int, data: dict, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    conn.execute("UPDATE clientes SET nivel_confianza=? WHERE id=?", (data.get("nivel_confianza", 0), cid))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# --- Prueba de impresión (para debug desde Admin) ---
@app.post("/api/prueba-impresion")
@app.get("/api/print-client.py")
def descargar_print_client():
    from fastapi.responses import PlainTextResponse
    import os
    ruta = "/var/www/maestro/frontend/print-client.py"
    if os.path.exists(ruta):
        with open(ruta, "r") as f:
            return PlainTextResponse(f.read(), media_type="text/plain")
    return PlainTextResponse("# Archivo no encontrado", status_code=404)

def prueba_impresion(data: dict, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    
    tipo = data.get("tipo", "caja")
    mensaje = data.get("mensaje", "PRUEBA DE IMPRESIÓN - CONY POS")
    
    conn = get_db()
    cur = conn.execute("""INSERT INTO impresoras_cola (folio, tipo, contenido, estado)
        VALUES (?, ?, ?, 'pendiente')""",
        (f"TEST-{int(datetime.now().timestamp())}", tipo, json.dumps({"mensaje": mensaje})))
    conn.commit()
    conn.close()
    return {"id": cur.lastrowid, "status": "prueba encolada", "tipo": tipo}

if __name__ == "__main__":
    import uvicorn
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8200)
    parser.add_argument("--db", type=str, default="/var/www/pos+ia/clientes/cony/cony_rest/cony_cony.db")
    args = parser.parse_args()
    globals()["DB_PATH"] = args.db
    uvicorn.run(app, host="127.0.0.1", port=args.port)

