#!/usr/bin/env python3
"""print-agent v2 — Cliente de impresion POS DEMO CONY
   CONY: punto de venta directa (sin mesas)
   Impresora caja  (192.168.100.68:9100) → ticket para el cliente
   Impresora cocina (192.168.100.69:9100) → comanda para preparar
"""
import json, os, socket, sys, time, urllib.request, base64, ssl
from datetime import datetime
import argparse

# Config
API_URL = os.environ.get("POS_API_URL", "https://pos.arnet.mx")
API_USER = os.environ.get("POS_API_USER", "superuser")
API_PASS = os.environ.get("POS_API_PASS", "1234")
POLL_INTERVAL = 5

# ESC/POS
INI  = bytes([0x1b, 0x40])
CEN  = bytes([0x1b, 0x61, 0x01])
IZQ  = bytes([0x1b, 0x61, 0x00])
DER  = bytes([0x1b, 0x61, 0x02])
NEG  = bytes([0x1b, 0x45, 0x01])
NEGOFF = bytes([0x1b, 0x45, 0x00])
GRANDE = bytes([0x1d, 0x21, 0x10])
NORMAL = bytes([0x1d, 0x21, 0x00])
CORTE = bytes([0x1d, 0x56, 0x41, 0x10])
SEP = b"-" * 42 + b"\n"
SEP2 = b"=" * 42 + b"\n"

def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)

def api_get(path):
    req = urllib.request.Request(f"{API_URL}{path}")
    req.add_header("Authorization", f"Basic {base64.b64encode(f'{API_USER}:{API_PASS}'.encode()).decode()}")
    try:
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"  API GET error: {e}")
        return []

def api_post(path, data=None):
    req = urllib.request.Request(f"{API_URL}{path}", 
        data=json.dumps(data).encode() if data else None,
        headers={"Content-Type": "application/json"})
    req.add_header("Authorization", f"Basic {base64.b64encode(f'{API_USER}:{API_PASS}'.encode()).decode()}")
    try:
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"  API POST error: {e}")
        return {}

def ticket_caja(data):
    """Ticket para el cliente — formato SRB 42 col"""
    rest = data.get("restaurante", "CONY")
    folio = data.get("folio", "N/A")
    fecha = data.get("fecha", datetime.now().strftime("%d/%m/%Y %H:%M"))
    metodo = data.get("metodo_pago", "")
    total = data.get("total", 0)
    subtotal = data.get("subtotal", total)
    iva = data.get("iva", 0)
    ieps = data.get("ieps", 0)
    items = data.get("items", [])
    cliente = data.get("cliente", "")
    atendio = data.get("atendio", "")
    cortesia = data.get("cortesia", 0)

    buf = bytearray()
    buf += INI
    # SECCION 1 — Encabezado
    buf += CEN + GRANDE
    buf += f"\n{rest}\n".encode()
    buf += NORMAL + SEP2
    if folio:
        buf += IZQ + f"Ticket: #{folio}\n".encode()
    buf += f"Fecha: {fecha}\n".encode()
    if atendio:
        buf += f"Atendi\xf3: {atendio}\n".encode()
    if cliente:
        buf += f"Cliente: {cliente}\n".encode()
    buf += SEP2
    # SECCION 2 — Productos
    buf += NEG + b" CANT  PRODUCTO              IMPORTE\n" + NEGOFF
    buf += b"\n".encode()
    for item in items:
        qty = item.get("cantidad", 1)
        name = item.get("nombre", "Producto")[:20].ljust(20)
        price = item.get("precio", 0) * qty
        buf += f"  {qty}    {name}  ${price:>7.2f}\n".encode()
        notas = item.get("notas", "")
        if notas:
            buf += f"        {notas}\n".encode()
    buf += b"\n".encode()
    buf += SEP
    # SECCION 3 — Totales
    buf += DER
    buf += f"SUBTOTAL: ${subtotal:>8.2f}\n".encode()
    if iva > 0:
        buf += f"IVA (16%):  ${iva:>8.2f}\n".encode()
    if ieps > 0:
        buf += f"IEPS:       ${ieps:>8.2f}\n".encode()
    buf += NEG + f"TOTAL: ${total:>10.2f}\n".encode() + NEGOFF
    if cortesia > 0:
        buf += f"CORTES\xcdA: ${cortesia:>8.2f}\n".encode()
    buf += IZQ + SEP
    # SECCION 4 — Forma de pago
    if metodo:
        buf += b" FORMA DE PAGO              IMPORTE\n" + SEP + IZQ
        buf += f" {metodo:<29s} ${total:>7.2f}\n".encode()
        buf += SEP
    # SECCION 5 — Cierre
    buf += CEN + SEP2 + b"\n"
    buf += GRANDE + b"Gracias por su preferencia!\n"
    buf += NORMAL + f"{rest}\n".encode()
    buf += b"\n" * 4 + CORTE
    return bytes(buf)

def comanda_cocina(data):
    """Comanda para cocina — solo lo que necesita preparar el cocinero"""
    folio = data.get("folio", "N/A")
    fecha = data.get("fecha", datetime.now().strftime("%d/%m/%Y %H:%M"))
    # Aceptar 'items' (viejo) o 'productos' (nuevo backend agrupado)
    items = data.get("items", data.get("productos", []))
    notas = data.get("nota", data.get("nota_extra", ""))
    creador = data.get("creado_por", "")
    cliente = data.get("cliente", "")
    
    buf = bytearray()
    buf += INI
    buf += CEN
    buf += b"\n"
    buf += GRANDE + b"* * *  C O M A N D A  * * *\n"
    buf += NORMAL + b"\n"
    buf += SEP2
    buf += IZQ
    buf += GRANDE + f"FOLIO: #{folio}\n".encode() + NORMAL
    if cliente:
        buf += f"Cliente: {cliente}\n".encode()
    buf += SEP
    buf += f"{fecha}\n".encode()
    if creador:
        buf += NEG + f"Mesero: {creador}\n".encode() + NEGOFF
    buf += SEP2
    buf += CEN + GRANDE + b"* * *  P R E P A R A R  * * *\n" + NORMAL
    buf += SEP2
    buf += IZQ
    for item in items:
        qty = item.get("cantidad", 1)
        name = item.get("producto", item.get("nombre", "Producto"))
        notes = item.get("notas", "")
        buf += GRANDE + f"  {qty}x {name}\n".encode() + NORMAL
        if notes:
            buf += f"     Nota: {notes}\n".encode()
    if notas:
        buf += IZQ + SEP
        buf += GRANDE + f"  ** {notas} **\n".encode() + NORMAL
    buf += b"\n" * 5 + CORTE
    return bytes(buf)

def imprimir(ip, puerto, datos):
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect((ip, puerto))
        s.sendall(datos)
        s.close()
        return True
    except Exception as e:
        log(f"  Error socket: {e}")
        return False

def run(rol, printer_ip, printer_port=9100):
    """
    Cada agente se identifica con su 'rol' (caja|cocina|cafe|barra_fria).
    El backend filtra tickets solo para ese rol.
    """
    log(f"🖨️ Agente de impresión iniciado")
    log(f"   API: {API_URL}")
    log(f"   Rol: {rol} → {printer_ip}:{printer_port}")
    log(f"   Polling cada {POLL_INTERVAL}s")
    
    # Verificación inicial
    pendientes = api_get(f"/api/cola-imprimir/pendientes?tipo={rol}")
    log(f"   API OK - {len(pendientes)} pendiente(s) inicial(es)")
    log(f"   Esperando tickets para {rol}...")
    
    while True:
        try:
            tickets = api_get(f"/api/cola-imprimir/pendientes?tipo={rol}")
            
            for t in tickets:
                tid = t.get("id")
                if not tid:
                    continue
                datos_raw = t.get("contenido", "{}")
                if isinstance(datos_raw, str):
                    try:
                        datos = json.loads(datos_raw)
                    except:
                        datos = {}
                else:
                    datos = datos_raw
                
                folio = datos.get("folio", t.get("folio", "?"))
                log(f"📄 Imprimiendo #{folio} en {rol}...")
                api_post(f"/api/cola-imprimir/{tid}/enviado", {"tipo": rol})
                
                texto = comanda_cocina(datos) if rol in ("cocina",) else ticket_caja(datos)
                ok = imprimir(printer_ip, printer_port, texto)
                
                if ok:
                    api_post(f"/api/cola-imprimir/{tid}/confirmar", {"tipo": rol})
                    log(f"   ✅ Impreso #{folio}")
                else:
                    api_post(f"/api/cola-imprimir/{tid}/error", {"tipo": rol, "error": "No responde"})
                    log(f"   ❌ Fallo #{folio} - impresora no responde")
            
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            log("🛑 Detenido por el usuario"); break
        except Exception as e:
            log(f"⚠️ Error: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente de impresión POS")
    parser.add_argument("--rol", default=os.environ.get("PRINTER_ROL", "caja"),
                        help="Rol de impresora: caja | cocina | cafe | barra_fria")
    parser.add_argument("--ip", default=os.environ.get("PRINTER_IP", "192.168.100.68"),
                        help="IP de la impresora")
    parser.add_argument("--puerto", type=int, 
                        default=int(os.environ.get("PRINTER_PORT", "9100")),
                        help="Puerto RAW")
    args = parser.parse_args()
    run(args.rol, args.ip, args.puerto)
