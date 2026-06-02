"""
POS Web CONY - Backend FastAPI
Puerto: 8200 | Proyecto: CONY
"""
import hashlib
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()
DB_PATH = "/var/www/pos+ia/clientes/cony/db/cony.db"

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

SUPERUSER_PASSWORD_HASH = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"  # hash de "1234"

def verify_login(nombre: str, password: str) -> dict:
    # Superuser global: no necesita estar en DB
    if nombre == "superuser" and hash_password(password) == SUPERUSER_PASSWORD_HASH:
        return {"id": 0, "nombre": "superuser", "rol": "superuser", "activo": 1}
    # Usuarios locales (admin, user)
    conn = get_db()
    cursor = conn.execute(
        "SELECT * FROM usuarios WHERE nombre = ? AND activo = 1",
        (nombre,)
    )
    user = cursor.fetchone()
    conn.close()
    if user and user["password"] == hash_password(password):
        return dict(user)
    return None

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    user = verify_login(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    return user

# ==================== FRONTEND (SIN AUTH) ====================
@app.get("/", response_class=HTMLResponse)
def get_login():
    return HTMLResponse(open("/var/www/pos+ia/clientes/cony/frontend/login.html").read())

@app.get("/login", response_class=HTMLResponse)
def get_login_page():
    return HTMLResponse(open("/var/www/pos+ia/clientes/cony/frontend/login.html").read())

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
    return HTMLResponse(open("/var/www/pos+ia/clientes/cony/frontend/dashboard.html").read())

@app.get("/app.js")
def get_js():
    return HTMLResponse(open("/var/www/pos+ia/clientes/cony/frontend/app.js").read())

@app.get("/app.css")
def get_css():
    return HTMLResponse(open("/var/www/pos+ia/clientes/cony/frontend/app.css").read())

@app.get("/favicon.svg")
def get_favicon():
    return HTMLResponse(open("/var/www/pos+ia/clientes/cony/frontend/favicon.svg").read())

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
def listar_pedidos(user: dict = Depends(authenticate)):
    conn = get_db()
    # Solo mostrar pedidos del corte ACTIVO (abierto)
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
        # Sin corte abierto: devolver lista vacía
        return []
    estados = {1:"pendiente",2:"completado",3:"en-preparacion",0:"cancelado"}
    pedidos = []
    for row in cursor.fetchall():
        d = dict(row)
        d["estatus"] = estados.get(d.get("estado"),"pendiente")
        pedidos.append(d)
    return pedidos

@app.put("/api/pedidos/{pid}/estatus")
def actualizar_estatus(pid: int, data: PedidoUpdate, user: dict = Depends(authenticate)):
    conn = get_db()
    estados = {"pendiente":1, "en-preparacion":3, "completado":2, "cancelado":0, 1:1, 2:2, 3:3, 0:0}
    val = estados.get(data.estatus if isinstance(data.estatus, str) else data.estatus, 1)
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
    return {"status": "ok"}

@app.get("/api/pedidos/{pid}/estatus-log")
def estatus_log(pid: int, user: dict = Depends(authenticate)):
    conn = get_db()
    estados = {1:"pendiente",2:"completado",3:"en-preparacion",0:"cancelado"}
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

def crear_usuario(u: UsuarioIn, user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
        # Admin no puede crear superuser
    if u.rol == "superuser" and user["rol"] != "superuser":
        raise HTTPException(403, "No puedes crear usuarios superuser")
    conn.execute(
        "INSERT INTO usuarios (nombre, password, rol, proyecto, nombre_real, apellidos, telefono) VALUES (?,?,?,?,?,?,?)",
        (u.nombre, hash_password(u.password), u.rol, u.proyecto, u.nombre_real or "", u.apellidos or "", u.telefono or "")
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.put("/api/usuarios/{uid}/password")
def cambiar_password(uid: int, password: str, user: dict = Depends(authenticate)):
    if user["rol"] != "superuser" and user["id"] != uid:
        raise HTTPException(403, "No puedes cambiar password de otro usuario")
    conn = get_db()
    conn.execute("UPDATE usuarios SET password=? WHERE id=?", (hash_password(password), uid))
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
    
    db = "/var/www/pos+ia/clientes/cony/db/cony.db"
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
            # Actualizar si el cliente no tenía datos
            if (not cl[1] or cl[1] == 'Mostrador') and nombre and nombre != 'Mostrador':
                c.execute("UPDATE clientes SET nombre=? WHERE id=?", (nombre, cliente_id))
            if not cl[2] or cl[2] == 'Mostrador':
                c.execute("UPDATE clientes SET direccion=? WHERE id=?", (direccion, cliente_id))
        else:
            c.execute("INSERT INTO clientes (telefono, nombre, direccion) VALUES (?,?,?)",
                      (telefono, nombre, direccion))
            cliente_id = c.lastrowid
        
        c.execute("INSERT INTO pedidos (cliente_id, folio, productos, total, metodo_pago, metodo_entrega, nota, estado, estado_pago, fecha, corte_id) VALUES (?,?,?,?,?,?,?,1,0,?,?)",
                  (cliente_id, folio, prds, total, metodo_pago, metodo_entrega, nota, ahora, corte_id))
        
        conn.commit()
        conn.close()
        return {"status": "ok", "pedido_id": c.lastrowid, "folio": folio, "message": f"Pedido registrado. Folio: {folio}"}
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
    """Cerrar el corte de caja activo."""
    from datetime import datetime
    conn = get_db()
    c = conn.execute("SELECT * FROM cortes WHERE estado='abierto' ORDER BY id DESC LIMIT 1")
    corte = c.fetchone()
    if not corte:
        conn.close()
        raise HTTPException(400, "No hay corte abierto")
    corte = dict(corte)
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
    
    # Calcular efectivo esperado y diferencia
    efectivo_ventas = sum(v for k, v in metodos.items() if k == "Efectivo")
    total_ingresos = corte.get("total_ingresos", 0) or 0
    total_gastos = corte.get("total_gastos", 0) or 0
    efectivo_esperado = corte["fondo_inicial"] + efectivo_ventas + total_ingresos - total_gastos
    efectivo_reportado = data.get("efectivo_reportado")
    diferencia = round(efectivo_reportado - efectivo_esperado, 2) if efectivo_reportado is not None else 0
    
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
            diferencia=?,
            observaciones=?
           WHERE id=?""",
        (ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"),
         user["nombre"], round(total_ventas, 2),
         json.dumps(metodos), efectivo_reportado, diferencia,
         data.get("observaciones", ""), corte["id"])
    )
    conn.commit()
    conn.close()
    return {
        "status": "ok",
        "mensaje": f"Corte #{corte['id']} cerrado. Total: ${total_ventas:.2f}",
        "total_ventas": round(total_ventas, 2),
        "metodos": metodos,
        "efectivo_esperado": round(efectivo_esperado, 2),
        "efectivo_reportado": efectivo_reportado,
        "diferencia": diferencia
    }


@app.get("/api/corte/historial")
def corte_historial(user: dict = Depends(authenticate)):
    conn = get_db()
    cursor = conn.execute(
        "SELECT * FROM cortes ORDER BY id DESC LIMIT 50"
    )
    return [dict(r) for r in cursor.fetchall()]


# ==================== ADMIN ====================
@app.get("/admin", response_class=HTMLResponse)
def get_admin():
    from fastapi.responses import HTMLResponse
    html = open("/var/www/pos+ia/clientes/cony/frontend/admin.html").read()
    return HTMLResponse(html)  # Sin autenticación — el frontend JS maneja el login

@app.get("/api/admin/clientes")
def admin_clientes(user: dict = Depends(authenticate)):
    if user["rol"] not in ("superuser", "admin"):
        raise HTTPException(403, "No autorizado")
    conn = get_db()
    cursor = conn.execute("""
        SELECT c.*, COUNT(p.id) as total_pedidos, COALESCE(SUM(p.total),0) as total_gastado
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


# ==================== INICIO ====================
if __name__ == "__main__":
    import uvicorn
