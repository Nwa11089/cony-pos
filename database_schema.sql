CREATE TABLE productos (
  id INTEGER PRIMARY KEY,
  nombre TEXT,
  categoria TEXT,
  precio REAL,
  complementos TEXT,
  disponible BOOLEAN DEFAULT 1
, emoji TEXT DEFAULT "", clasificacion_superior_id INTEGER DEFAULT 1, es_ingrediente INTEGER DEFAULT 0, stock REAL DEFAULT 0, stock_minimo REAL DEFAULT 0, unidad TEXT DEFAULT 'pieza', descripcion TEXT DEFAULT '');
CREATE TABLE clientes (
  id INTEGER PRIMARY KEY,
  nombre TEXT,
  telefono TEXT UNIQUE,
  email TEXT,
  token TEXT,
  proyecto TEXT,
  es_preferente BOOLEAN DEFAULT 0
, direccion TEXT DEFAULT 'Mostrador', nivel_confianza INTEGER DEFAULT 0);
CREATE TABLE direcciones (
  id INTEGER PRIMARY KEY,
  cliente_id INTEGER,
  calle TEXT,
  numero TEXT,
  colonia TEXT,
  codigo_postal TEXT,
  entre_calles TEXT,
  referencia TEXT,
  ubicacion_gmaps TEXT,
  FOREIGN KEY(cliente_id) REFERENCES clientes(id)
);
CREATE TABLE impresoras (
  id INTEGER PRIMARY KEY,
  nombre TEXT,
  tipo TEXT,
  direccion_ip TEXT,
  puerto INTEGER,
  clasificacion TEXT
);
CREATE TABLE producto_impresora (
  producto_id INTEGER,
  impresora_id INTEGER,
  FOREIGN KEY(producto_id) REFERENCES productos(id),
  FOREIGN KEY(impresora_id) REFERENCES impresoras(id)
);
CREATE TABLE pedidos (
  id INTEGER PRIMARY KEY,
  cliente_id INTEGER,
  direccion_id INTEGER,
  productos TEXT,
  total REAL,
  metodo_pago TEXT,
  metodo_entrega TEXT,
  envio_costo REAL DEFAULT 0,
  folio TEXT,
  nota TEXT,
  id_conversacion TEXT,
  estado INTEGER DEFAULT 1,
  estado_pago INTEGER DEFAULT 0,
  fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP, corte_id INTEGER REFERENCES cortes(id), creado_por_id INTEGER DEFAULT NULL, creado_por_nombre TEXT DEFAULT '', repartidor_id INTEGER DEFAULT NULL, entregado_por INTEGER DEFAULT 0, fecha_entrega TEXT DEFAULT NULL, entregado_por_nombre TEXT DEFAULT '', fecha_terminado TEXT DEFAULT NULL, nivel_confianza INTEGER DEFAULT 0, origen TEXT DEFAULT 'comandero',
  FOREIGN KEY(cliente_id) REFERENCES clientes(id),
  FOREIGN KEY(direccion_id) REFERENCES direcciones(id)
);
CREATE TABLE usuarios (
  id INTEGER PRIMARY KEY,
  nombre TEXT,
  rol TEXT,
  proyecto TEXT,
  password TEXT
, email TEXT, activo INTEGER DEFAULT 1, nombre_real TEXT DEFAULT '', apellidos TEXT DEFAULT '', telefono TEXT DEFAULT '');
CREATE TABLE cortes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  estado TEXT NOT NULL DEFAULT 'abierto',       -- 'abierto' | 'cerrado'
  fondo_inicial REAL NOT NULL DEFAULT 0,
  fecha_apertura TEXT NOT NULL,
  hora_apertura TEXT NOT NULL,
  usuario_apertura TEXT NOT NULL,
  fecha_cierre TEXT,
  hora_cierre TEXT,
  usuario_cierre TEXT,
  total_ventas REAL DEFAULT 0,
  total_ingresos REAL DEFAULT 0,               -- efectivo insertado manualmente
  total_gastos REAL DEFAULT 0,                 -- gastos/salidas de caja
  total_metodos TEXT DEFAULT '{}',              -- JSON: {"Efectivo": 0, "Tarjeta": 0, ...}
  diferencia REAL DEFAULT 0,
  observaciones TEXT DEFAULT ''
, efectivo_reportado REAL DEFAULT NULL, total_arqueado REAL DEFAULT 0);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE orden_estatus_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pedido_id INTEGER NOT NULL,
  estatus_anterior INTEGER,
  estatus_nuevo INTEGER NOT NULL,
  usuario TEXT NOT NULL,
  fecha TEXT NOT NULL,
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
);
CREATE TABLE complementos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  tipo TEXT NOT NULL DEFAULT 'ingrediente', -- ingrediente, salsa, extra
  categoria_complemento TEXT DEFAULT '',
  activo INTEGER DEFAULT 1,
  orden INTEGER DEFAULT 0
);
CREATE TABLE producto_complementos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  producto_id INTEGER NOT NULL,
  complemento_id INTEGER NOT NULL,
  obligatorio INTEGER DEFAULT 1, -- 1=incluido x defecto, 0=opcional extra
  UNIQUE(producto_id, complemento_id)
);
CREATE TABLE salsas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  nivel_picor INTEGER DEFAULT 0, -- 0=sin, 1=bajo, 2=medio, 3=alto, 4=extremo
  activo INTEGER DEFAULT 1,
  orden INTEGER DEFAULT 0
);
CREATE TABLE producto_salsas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  producto_id INTEGER NOT NULL,
  salsa_id INTEGER NOT NULL,
  UNIQUE(producto_id, salsa_id)
);
CREATE TABLE config (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE metricas (
  fecha TEXT PRIMARY KEY,
  pedidos_recibidos INTEGER DEFAULT 0,
  mensajes_enviados INTEGER DEFAULT 0,
  mensajes_recibidos INTEGER DEFAULT 0,
  tickets_cobro INTEGER DEFAULT 0,
  tickets_cocina INTEGER DEFAULT 0
);
CREATE TABLE clasificaciones_superiores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL UNIQUE,
  descripcion TEXT DEFAULT ''
);
CREATE TABLE clasificaciones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  clasificacion_superior_id INTEGER NOT NULL,
  descripcion TEXT DEFAULT '',
  FOREIGN KEY (clasificacion_superior_id) REFERENCES clasificaciones_superiores(id)
);
CREATE TABLE impresoras_config (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  rol TEXT NOT NULL CHECK(rol IN ('caja', 'cocina', 'barra')),
  direccion_ip TEXT NOT NULL DEFAULT '192.168.100.100',
  puerto INTEGER DEFAULT 9100,
  activa INTEGER DEFAULT 1,
  notas TEXT DEFAULT ''
);
CREATE TABLE rol_impresora_mapeo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clasificacion_superior_id INTEGER NOT NULL,
  rol_impresora TEXT NOT NULL,
  FOREIGN KEY (clasificacion_superior_id) REFERENCES clasificaciones_superiores(id),
  UNIQUE(clasificacion_superior_id, rol_impresora)
);
CREATE TABLE impresoras_cola (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pedido_id INTEGER,
  folio TEXT,
  tipo TEXT NOT NULL,
  contenido TEXT,
  estado TEXT DEFAULT 'pendiente',
  fecha_creacion TEXT DEFAULT (datetime('now','-6 hours')),
  fecha_envio TEXT,
  intentos INTEGER DEFAULT 0,
  error TEXT
);
CREATE TABLE recetas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  producto_id INTEGER NOT NULL,
  ingrediente_id INTEGER NOT NULL,
  cantidad REAL NOT NULL DEFAULT 1,
  FOREIGN KEY(producto_id) REFERENCES productos(id),
  FOREIGN KEY(ingrediente_id) REFERENCES productos(id),
  UNIQUE(producto_id, ingrediente_id)
);
