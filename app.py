from flask import Flask, render_template, request, redirect, session, Response
from datetime import datetime
import sqlite3, hashlib, os

app = Flask(__name__)
app.secret_key = "fmv_secret_key"

DB = "clientes_web.db"
def init_db():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    # TABLA USUARIOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        clave TEXT,
        rol TEXT,
        nombre TEXT,
        cedula TEXT,
        telefono TEXT
    )
    """)

    # TABLA CLIENTES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        representante TEXT,
        razon TEXT,
        nit TEXT,
        contacto TEXT,
        telefono TEXT,
        correo TEXT,
        direccion TEXT
    )
    """)

    # TABLA CALENDARIO
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calendario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        empleado_id INTEGER,
        fecha TEXT,
        valor REAL,
        realizado TEXT
    )
    """)

    conn.commit()
    conn.close()

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
        nombre = request.form["nombre"]
        cedula = request.form["cedula"]
        telefono = request.form["telefono"]

        db.execute("""
        INSERT INTO usuarios (usuario, clave, rol, nombre, cedula, telefono)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        usuario,
        hash_pwd(clave),    
        rol,
        nombre,     # 🆕 guarda nombre completo
        cedula,     # 🆕 guarda cédula
        telefono    # 🆕 guarda teléfono
    ))

    usuarios = db.execute("SELECT * FROM usuarios").fetchall()

    return render_template("usuarios.html", usuarios=usuarios, error=error)




# ---------- ORDEN DE SERVICIO ----------

@app.route("/orden/<int:id>")
def orden(id):
    db = get_db()

    data = db.execute("""
    SELECT c.*, cli.razon, cli.nit, cli.direccion, cli.telefono,
           u.nombre as tecnico, u.cedula
    FROM calendario c
    JOIN clientes cli ON c.cliente_id = cli.id
    JOIN usuarios u ON c.empleado_id = u.id
    WHERE c.id=?
    """, (id,)).fetchone()

    return render_template("orden.html", d=data)

    

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


    mes_actual = datetime.now().strftime("%Y-%m")

    ingresos_mes = db.execute("""
        SELECT SUM(valor) as total
        FROM calendario
        WHERE strftime('%Y-%m', fecha) = ?
    """, (mes_actual,)).fetchone()

    total_mes = ingresos_mes["total"] if ingresos_mes["total"] else 0

    # 🔥 HISTORIAL
    historial = db.execute("""
        SELECT strftime('%Y-%m', fecha) as mes, SUM(valor) as total
        FROM calendario
        WHERE realizado = 'REALIZADO'
        GROUP BY mes
        ORDER BY mes DESC
    """).fetchall()

    total_clientes = db.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]

    total_servicios = db.execute("SELECT COUNT(*) FROM calendario").fetchone()[0]

    total_ingresos = db.execute("SELECT SUM(valor) FROM calendario").fetchone()[0] or 0

    realizados = db.execute("SELECT COUNT(*) FROM calendario WHERE realizado='REALIZADO'").fetchone()[0]

    pendientes = db.execute("SELECT COUNT(*) FROM calendario WHERE realizado='PENDIENTE'").fetchone()[0]

    

    

    return render_template("dashboard.html",
        total_clientes=total_clientes,
        total_servicios=total_servicios,
        total_ingresos=total_ingresos,
        realizados=realizados,
        pendientes=pendientes,
        total_mes=total_mes,
        historial=historial
    )

# ---------- CONTEXTO ----------

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


@app.route("/api/cambiar_estado/<int:id>", methods=["POST"])
def cambiar_estado_api(id):
    db = get_db()

    evento = db.execute(
        "SELECT realizado FROM calendario WHERE id=?", 
        (id,)
    ).fetchone()

    # 🔄 Cambiar estado
    nuevo_estado = "REALIZADO" if evento["realizado"] == "PENDIENTE" else "PENDIENTE"

    db.execute(
        "UPDATE calendario SET realizado=? WHERE id=?", 
        (nuevo_estado, id)
    )
    db.commit()

    # 📤 Respuesta JSON
    return {"estado": nuevo_estado}

# ---------- CAMBIAR ESTADO EVENTO ----------

@app.route("/cambiar_estado/<int:id>")
def cambiar_estado(id):
    db = get_db()

    # 🔍 Obtener estado actual
    evento = db.execute("SELECT realizado FROM calendario WHERE id=?", (id,)).fetchone()

    # 🔄 Cambiar estado
    nuevo_estado = "REALIZADO" if evento["realizado"] == "PENDIENTE" else "PENDIENTE"

    # 💾 Guardar cambio
    db.execute("UPDATE calendario SET realizado=? WHERE id=?", (nuevo_estado, id))
    db.commit()

    return redirect("/calendario")

# ---------- EDITAR CLIENTE ----------

@app.route("/editar_cliente/<int:id>", methods=["GET", "POST"])
def editar_cliente(id):
    if "user" not in session:
        return redirect("/")

    db = get_db()

    cliente = db.execute("SELECT * FROM clientes WHERE id=?", (id,)).fetchone()

    if request.method == "POST":
        db.execute("""
            UPDATE clientes
            SET representante=?, razon=?, nit=?, contacto=?, telefono=?, correo=?, direccion=?
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

    # 👇 IMPORTANTE
    return render_template("editar_cliente.html", cliente=cliente)

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


# ---------- EXPORTAR CALENDARIO ----------
@app.route("/exportar_calendario")
def exportar_calendario():
    if "user" not in session:
        return redirect("/")

    db = get_db()

    eventos = db.execute("""
        SELECT calendario.fecha, calendario.hora,
               clientes.razon, clientes.direccion, clientes.telefono,
               usuarios.usuario AS empleado,
               calendario.tipo, calendario.valor
        FROM calendario
        LEFT JOIN clientes ON calendario.cliente_id = clientes.id
        LEFT JOIN usuarios ON calendario.empleado_id = usuarios.id
    """).fetchall()

    def generar():
        yield "Fecha,Hora,Cliente,Dirección,Teléfono,Empleado,Tipo,Valor\n"

        for e in eventos:
            yield f"{e['fecha']},{e['hora']},{e['razon']},{e['direccion']},{e['telefono']},{e['empleado']},{e['tipo']},{e['valor']}\n"

    return Response(
        generar(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=calendario.csv"}
    )

# ---------- ORDENES DE SERVICIO ----------
@app.route("/ordenes")
def ordenes():
    if "user" not in session:
        return redirect("/")

    db = get_db()

    datos = db.execute("""
        SELECT c.id, c.fecha, cl.razon, c.tipo, c.realizado
        FROM calendario c
        JOIN clientes cl ON c.cliente_id = cl.id
        ORDER BY c.id DESC
    """).fetchall()

    return render_template("ordenes.html", datos=datos)

# ---------- LISTADO DE ORDENES DE SERVICIO ----------
@app.route("/ordenes")
def listar_ordenes():
    db = get_db()

    datos = db.execute("""
        SELECT c.id, c.fecha, cl.razon, c.tipo, c.realizado
        FROM calendario c
        JOIN clientes cl ON c.cliente_id = cl.id
        ORDER BY c.id DESC
    """).fetchall()

    return render_template("ordenes.html", datos=datos)

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
            (fecha, hora, titulo, estado, cliente_id, tipo, valor, empleado_id, realizado)
            VALUES (?, ?, ?, 'PENDIENTE', ?, ?, ?, ?, ?)
        """, (
            request.form["fecha"],
            request.form["hora"],
            request.form["titulo"],
            request.form["cliente_id"],
            request.form["tipo"],
            request.form["valor"],
            request.form["empleado_id"],
            request.form.get("realizado")
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
        ORDER BY date(fecha) DESC, time(hora) DESC
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

# ---------- EDITAR USUARIO ----------          

@app.route("/editar_usuario/<int:id>", methods=["GET", "POST"])
def editar_usuario(id):
    db = get_db()

    # 🔁 si envía formulario (guardar cambios)
    if request.method == "POST":
        usuario = request.form["usuario"]
        nombre = request.form["nombre"]
        cedula = request.form["cedula"]
        telefono = request.form["telefono"]
        rol = request.form["rol"]

        db.execute("""
        UPDATE usuarios 
        SET usuario=?, nombre=?, cedula=?, telefono=?, rol=?
        WHERE id=?
        """, (usuario, nombre, cedula, telefono, rol, id))

        db.commit()
        return redirect("/usuarios")

    # 🔍 obtener usuario actual
    u = db.execute("SELECT * FROM usuarios WHERE id=?", (id,)).fetchone()

    return render_template("editar_usuario.html", u=u)

# ---------- ELIMINAR USUARIO ----------

@app.route("/eliminar_usuario/<int:id>")
def eliminar_usuario(id):
    db = get_db()  # conecta a la base de datos

    db.execute("DELETE FROM usuarios WHERE id=?", (id,))  # elimina usuario
    db.commit()  # guarda cambios

    return redirect("/usuarios")  # vuelve a la página

# ---------- RUN ----------
if __name__ == "__main__":
    app.run()
    init_db()  # inicializa la base de datos (crea tablas si no existen)
