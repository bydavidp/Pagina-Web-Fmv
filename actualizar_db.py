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

# ---------- TABLA CLIENTES (ACTUALIZADA) ----------
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
    estado TEXT
)
""")

# ---------- CREAR USUARIO ADMIN (SI NO EXISTE) ----------
clave = hashlib.sha256("1234".encode()).hexdigest()

cursor.execute("""
SELECT * FROM usuarios WHERE usuario=?
""", ("admin",))

if not cursor.fetchone():
    cursor.execute("""
    INSERT INTO usuarios (usuario, clave, rol)
    VALUES (?, ?, ?)
    """, ("admin", clave, "admin"))

conn.commit()
conn.close()

print("✅ Base de datos lista y actualizada")