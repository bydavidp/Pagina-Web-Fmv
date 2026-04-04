import sqlite3
import hashlib

conn = sqlite3.connect("clientes_web.db")
cursor = conn.cursor()

# ---------- TABLA USUARIOS ----------
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    clave TEXT,
    rol TEXT
)
""")

# ---------- TABLA CLIENTES ----------
cursor.execute("""
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    representante TEXT,
    razon TEXT,
    nit TEXT,
    correo TEXT,
    contacto TEXT,
    telefono TEXT,
    direccion TEXT
)
""")


# ---------- TABLA CALENDARIO ----------
cursor.execute("""
CREATE TABLE IF NOT EXISTS calendario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    hora TEXT,
    titulo TEXT,
    estado TEXT,
    valor REAL,
)
""")


# ---------- 🆕 TABLA CONSECUTIVO ----------
cursor.execute("""
CREATE TABLE IF NOT EXISTS consecutivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero INTEGER
)
""")

cursor.execute("SELECT * FROM consecutivos")

if not cursor.fetchone():
    cursor.execute("INSERT INTO consecutivos (numero) VALUES (1)")

# ---------- 🔥 ACTUALIZAR TABLA CALENDARIO ----------
try:
    cursor.execute("ALTER TABLE calendario ADD COLUMN cliente_id INTEGER")
except:
    print("cliente_id ya existe")

try:
    cursor.execute("ALTER TABLE calendario ADD COLUMN tipo TEXT")
except:
    print("tipo ya existe")

try:
    cursor.execute("ALTER TABLE calendario ADD COLUMN valor REAL")
except:
    print("valor ya existe")

# 🆕 👉 AGREGA ESTE BLOQUE
try:
    cursor.execute("ALTER TABLE calendario ADD COLUMN empleado_id INTEGER")
except:
    print("empleado_id ya existe")


# 🆕 🔥 NUEVO CAMPO (AQUÍ VA)
try:
    cursor.execute("ALTER TABLE calendario ADD COLUMN realizado TEXT")
except:
    print("realizado ya existe")

    # 🆕 CAMPOS NUEVOS PARA USUARIOS
try:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN nombre TEXT")
except:
    print("nombre ya existe")

try:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN cedula TEXT")
except:
    print("cedula ya existe")

try:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN telefono TEXT")
except:
    print("telefono ya existe")

# ---------- 🔥 ACTUALIZAR TABLA USUARIOS ----------
try:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN nombre TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN cedula TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE usuarios ADD COLUMN telefono TEXT")
except:
    pass

# ---------- CREAR USUARIO ADMIN ----------
clave = hashlib.sha256("1234".encode()).hexdigest()

cursor.execute("SELECT * FROM usuarios WHERE usuario=?", ("admin",))

if not cursor.fetchone():
    cursor.execute("""
    INSERT INTO usuarios (usuario, clave, rol)
    VALUES (?, ?, ?)
    """, ("admin", clave, "admin"))

conn.commit()
conn.close()

print("✅ Base de datos lista y actualizada")