from flask import Flask, render_template, request, redirect, session, Response
from datetime import datetime
import sqlite3, hashlib, os, csv

app = Flask(__name__)
app.secret_key = "fmv_secret_key"

DB = "clientes_web.db"


UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/subir", methods=["GET", "POST"])
def subir():
    if request.method == "POST":
        file = request.files["archivo"]
        if file:
            path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(path)
            return "Archivo subido"

    return render_template("subir.html")

# ---------- USUARIOS ----------

@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    if "user" not in session:
        return redirect("/")

    # 🔐 Solo admin
    if session.get("rol") != "admin":
        return "Acceso restringido", 403

    db = get_db()
    error = ""

    if request.method == "POST":
        usuario = request.form["usuario"]
        clave = request.form["clave"]
        rol = request.form["rol"]

        if not usuario or not clave:
            error = "Usuario y contraseña obligatorios"
        else:
            db.execute("""
                INSERT INTO usuarios (usuario, clave, rol)
                VALUES (?, ?, ?)
            """, (
                usuario,
                hash_pwd(clave),
                rol
            ))
            db.commit()

    usuarios = db.execute("SELECT * FROM usuarios").fetchall()

    return render_template("usuarios.html", usuarios=usuarios, error=error)

# ---------- DB ----------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pwd(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        db = get_db()

        user = db.execute(
            "SELECT * FROM usuarios WHERE usuario=? AND clave=?",
            (request.form["usuario"], hash_pwd(request.form["clave"]))
        ).fetchone()

        if user:
            session["user"] = user["usuario"]
            session["rol"] = user["rol"]
            return redirect("/dashboard")

        error = "Credenciales incorrectas"

    return render_template("login.html", error=error)

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    db = get_db()

    total_clientes = db.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    total_eventos = db.execute("SELECT COUNT(*) FROM calendario").fetchone()[0]
    pendientes = db.execute(
        "SELECT COUNT(*) FROM calendario WHERE estado='PENDIENTE'"
    ).fetchone()[0]

    return render_template(
        "dashboard.html",
        total_clientes=total_clientes,
        total_eventos=total_eventos,
        pendientes=pendientes
    )

@app.context_processor
def inject_active():
    return dict(current_path=request.path)

# ---------- ELIMINAR CLIENTE ----------

@app.route("/eliminar_cliente/<int:id>")
def eliminar_cliente(id):
    if "user" not in session:
        return redirect("/")

    db = get_db()
    db.execute("DELETE FROM clientes WHERE id=?", (id,))
    db.commit()

    return redirect("/clientes")

# ---------- EDITAR CLIENTE ----------

@app.route("/editar_cliente/<int:id>", methods=["GET", "POST"])
def editar_cliente(id):
    if "user" not in session:
        return redirect("/")

    db = get_db()

    if request.method == "POST":
        db.execute("""
            UPDATE clientes SET
            representante=?, razon=?, nit=?, contacto=?, telefono=?, correo=?, direccion=?
            WHERE id=?
        """, (
            request.form["representante"],
            request.form["razon"],
            request.form["nit"],
            request.form["contacto"],
            request.form["telefono"],
            request.form["correo"],
            request.form["direccion"],
            id
        ))
        db.commit()
        return redirect("/clientes")

    cliente = db.execute("SELECT * FROM clientes WHERE id=?", (id,)).fetchone()

    return render_template("editar_cliente.html", c=cliente)

# ---------- EXPORTAR CLIENTES ----------

@app.route("/exportar_clientes")
def exportar_clientes():
    if "user" not in session:
        return redirect("/")

    db = get_db()
    clientes = db.execute("SELECT * FROM clientes").fetchall()

    def generar():
        data = []
        encabezados = ["ID", "Razon", "NIT", "Contacto", "Telefono", "Correo", "Direccion"]
        data.append(encabezados)

        for c in clientes:
            data.append([
                c["id"],
                c["razon"],
                c["nit"],
                c["contacto"],
                c["telefono"],
                c["correo"],
                c["direccion"]
            ])

        for fila in data:
            yield ",".join([str(i) for i in fila]) + "\n"

    return Response(
        generar(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=clientes.csv"}
    )

# ---------- CLIENTES ----------
def solo_admin():
    return session.get("rol") == "admin"

# ---------- CLIENTES ----------
@app.route("/clientes", methods=["GET", "POST"])



def clientes():
    if "user" not in session:
        return redirect("/")

    if not solo_admin():
        return "Acceso restringido", 403

    db = get_db()
    error = ""

    if request.method == "POST":

        razon = request.form["razon"]
        nit = request.form["nit"]

        # 🔴 VALIDACIÓN
        if not razon or not nit:
            error = "Razón social y NIT son obligatorios"
        else:
            db.execute("""
                INSERT INTO clientes 
                (representante, razon, nit, correo, contacto, telefono, direccion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                request.form["representante"],
                razon,
                nit,
                request.form["correo"],
                request.form["contacto"],
                request.form["telefono"],
                request.form["direccion"]
            ))
            db.commit()

    # PAGINACIÓN COMPLETA
    # PAGINACIÓN
    page = request.args.get("page", default=1, type=int)
    limite = 5
    offset = (page - 1) * limite

    clientes = db.execute(
        "SELECT * FROM clientes LIMIT ? OFFSET ?",
        (limite, offset)
    ).fetchall()

    # TOTAL
    total = db.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    total_paginas = (total + limite - 1) // limite

    return render_template(
        "clientes.html",
        clientes=clientes,
        error=error,
        page=page,
        total_paginas=total_paginas
)




# ---------- FORMATO DE SERVICIO ----------
@app.route("/formato", methods=["GET", "POST"])
def formato():
    if "user" not in session:
        return redirect("/")

    db = get_db()

    clientes = db.execute("SELECT * FROM clientes").fetchall()
    empleados = db.execute("SELECT * FROM usuarios").fetchall()

    cliente = None
    empleado = None

    consecutivo = None
    fecha = datetime.now().strftime("%Y-%m-%d")

    hora_inicio = hora_fin = servicio = observaciones = None

    if request.method == "POST":
        cliente_id = request.form["cliente_id"]
        empleado_id = request.form["empleado_id"]

        cliente = db.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
        emp = db.execute("SELECT * FROM usuarios WHERE id=?", (empleado_id,)).fetchone()
        empleado = emp["usuario"]

        # 🔢 consecutivo
        consecutivo = db.execute("SELECT numero FROM consecutivos").fetchone()[0]
        db.execute("UPDATE consecutivos SET numero = numero + 1")
        db.commit()

        hora_inicio = request.form["hora_inicio"]
        hora_fin = request.form["hora_fin"]
        servicio = request.form["servicio"]
        observaciones = request.form["observaciones"]

    return render_template(
        "formato.html",
        clientes=clientes,
        empleados=empleados,
        cliente=cliente,
        empleado=empleado,
        consecutivo=consecutivo,
        fecha=fecha,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        servicio=servicio,
        observaciones=observaciones
    )

# ---------- CALENDARIO ----------
@app.route("/calendario", methods=["GET", "POST"])
def calendario():
    if "user" not in session:
        return redirect("/")

    db = get_db()

    # 👉 GUARDAR EVENTO
    if request.method == "POST":
        db.execute("""
            INSERT INTO calendario 
            (fecha, hora, titulo, estado, cliente_id, tipo, valor, empleado_id)
            VALUES (?, ?, ?, 'PENDIENTE', ?, ?, ?, ?)
        """, (
            request.form["fecha"],
            request.form["hora"],
            request.form["titulo"],
            request.form["cliente_id"],
            request.form["tipo"],
            request.form["valor"],
            request.form["empleado_id"]
        ))
        db.commit()

    # 🔥 TRAER EVENTOS + CLIENTE + EMPLEADO
    eventos = db.execute("""
        SELECT calendario.*, 
               clientes.razon, clientes.telefono, clientes.direccion,
               usuarios.usuario AS empleado
        FROM calendario
        LEFT JOIN clientes ON calendario.cliente_id = clientes.id
        LEFT JOIN usuarios ON calendario.empleado_id = usuarios.id
    """).fetchall()

    # 🔥 TRAER CLIENTES
    clientes = db.execute("SELECT * FROM clientes").fetchall()

    # 🔥 TRAER EMPLEADOS (USUARIOS)
    empleados = db.execute("SELECT * FROM usuarios").fetchall()

    return render_template(
        "calendario.html",
        eventos=eventos,
        clientes=clientes,
        empleados=empleados
    )# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- RUN ----------
if __name__ == "__main__":
    app.run()
