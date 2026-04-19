from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import urllib.parse
import urllib.request
import json
import sqlite3
import os
import re

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "clave_temporal_dev")

DATABASE = "biblioteca.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'usuarios'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS libros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            autor TEXT,
            anio TEXT,
            estado TEXT NOT NULL,
            imagen TEXT,
            usuario_id INTEGER NOT NULL,
            favorito INTEGER NOT NULL DEFAULT 0,
            rating INTEGER NOT NULL DEFAULT 0,
            nota TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    """)
    conn.commit()
    conn.close()

def crear_admin():
    conn = get_db_connection()

    admin = conn.execute(
        "SELECT * FROM usuarios WHERE email = ?",
        ("admin@biblioteca.com",)
    ).fetchone()

    if not admin:
        password_hash = generate_password_hash("Admin123*")
        conn.execute(
            "INSERT INTO usuarios (nombre, email, password, rol) VALUES (?, ?, ?, ?)",
            ("Yuri Admin", "admin@biblioteca.com", password_hash, "admin")
        )
        conn.commit()

    conn.close()

def usuario_logueado():
    return "usuario_id" in session

def es_admin():
    return session.get("usuario_rol") == "admin"

def admin_requerido():
    return usuario_logueado() and es_admin()

def password_segura(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[^\w\s]", password):
        return False
    return True

def buscar_ediciones_googlebooks(titulo):
    params = urllib.parse.urlencode({
        "q": titulo,
        "maxResults": 8,
        "langRestrict": "es",
        "key": API_KEY
    })

    url = f"https://www.googleapis.com/books/v1/volumes?{params}"

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        items = data.get("items", [])
        if not items:
            return []

        resultados = []

        for item in items:
            volume_info = item.get("volumeInfo", {})

            titulo_libro = volume_info.get("title", "")
            autor = ", ".join(volume_info.get("authors", [])) if volume_info.get("authors") else ""
            fecha_publicacion = volume_info.get("publishedDate", "")
            anio = fecha_publicacion[:4] if fecha_publicacion else ""
            idioma = volume_info.get("language", "")

            image_links = volume_info.get("imageLinks", {})
            imagen = image_links.get("thumbnail") or image_links.get("smallThumbnail") or ""

            if imagen.startswith("http://"):
                imagen = imagen.replace("http://", "https://", 1)

            resultados.append({
                "titulo": titulo_libro,
                "autor": autor,
                "anio": anio,
                "imagen": imagen,
                "idioma": idioma
            })

        return resultados

    except Exception as e:
        print("Error buscando en Google Books:", e)
        return []

@app.route("/")
def inicio():
    if not usuario_logueado():
        return redirect(url_for("login"))

    estado = request.args.get("estado", "leidos")

    conn = get_db_connection()
    libros = conn.execute(
        "SELECT * FROM libros WHERE estado = ? AND usuario_id = ? ORDER BY id DESC",
        (estado, session["usuario_id"])
    ).fetchall()
    conn.close()

    return render_template("index.html", libros=libros, estado_actual=estado)

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = request.form.get("password")

        if not password_segura(password):
            flash("La contraseña debe tener mínimo 8 caracteres, mayúscula, minúscula, número y símbolo.")
            return render_template("registro.html")

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO usuarios (nombre, email, password, rol) VALUES (?, ?, ?, ?)",
                (nombre, email, password_hash, "usuario")
            )
            conn.commit()
            flash("Cuenta creada correctamente. Ahora inicia sesión.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Ese correo ya está registrado.")
        finally:
            conn.close()

    return render_template("registro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if usuario and check_password_hash(usuario["password"], password):
            session["usuario_id"] = usuario["id"]
            session["usuario_nombre"] = usuario["nombre"]
            session["usuario_rol"] = usuario["rol"]
            return redirect(url_for("inicio"))
        else:
            flash("Correo o contraseña incorrectos.")

    return render_template("login.html")

@app.route("/olvide-password", methods=["GET", "POST"])
def olvide_password():
    if request.method == "POST":
        email = request.form.get("email")
        nueva_password = request.form.get("nueva_password")

        conn = get_db_connection()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?",
            (email,)
        ).fetchone()

        if usuario:
            if not password_segura(nueva_password):
                flash("La contraseña debe tener mínimo 8 caracteres, mayúscula, minúscula, número y símbolo.")
                return redirect(url_for("olvide_password"))

            password_hash = generate_password_hash(nueva_password)

            conn.execute(
                "UPDATE usuarios SET password = ? WHERE email = ?",
                (password_hash, email)
            )
            conn.commit()
            conn.close()

            flash("Contraseña actualizada correctamente")
            return redirect(url_for("login"))

        conn.close()
        flash("Correo no encontrado")
        return redirect(url_for("olvide_password"))

    return render_template("olvide_password.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/agregar")
def vista_agregar():
    if not usuario_logueado():
        return redirect(url_for("login"))
    return render_template("agregar.html")

@app.route("/buscar-libro", methods=["POST"])
def buscar_libro():
    if not usuario_logueado():
        return redirect(url_for("login"))

    titulo = request.form.get("titulo_busqueda", "").strip()
    resultados = buscar_ediciones_googlebooks(titulo) if titulo else []
    mensaje = None

    if titulo and not resultados:
        mensaje = "No se encontraron resultados para ese libro."

    return render_template(
        "agregar.html",
        resultados=resultados,
        titulo_busqueda=titulo,
        mensaje=mensaje
    )

@app.route("/admin")
def panel_admin():
    if not admin_requerido():
        flash("No tienes permisos para entrar al panel admin.")
        return redirect(url_for("inicio"))

    conn = get_db_connection()
    usuarios = conn.execute(
        "SELECT id, nombre, email, rol FROM usuarios ORDER BY id DESC"
    ).fetchall()

    libros = conn.execute("""
        SELECT libros.id, libros.titulo, libros.autor, libros.anio, libros.estado,
               usuarios.nombre AS usuario_nombre
        FROM libros
        JOIN usuarios ON libros.usuario_id = usuarios.id
        ORDER BY libros.id DESC
    """).fetchall()
    conn.close()

    return render_template("admin.html", usuarios=usuarios, libros=libros)

@app.route("/admin/eliminar-usuario/<int:id_usuario>", methods=["POST"])
def admin_eliminar_usuario(id_usuario):
    if not admin_requerido():
        flash("No tienes permisos para esta acción.")
        return redirect(url_for("inicio"))

    if id_usuario == session.get("usuario_id"):
        flash("No puedes eliminar tu propio usuario admin.")
        return redirect(url_for("panel_admin"))

    conn = get_db_connection()

    conn.execute("DELETE FROM libros WHERE usuario_id = ?", (id_usuario,))
    conn.execute("DELETE FROM usuarios WHERE id = ?", (id_usuario,))

    conn.commit()
    conn.close()

    flash("Usuario eliminado correctamente.")
    return redirect(url_for("panel_admin"))

@app.route("/admin/eliminar-libro/<int:id_libro>", methods=["POST"])
def admin_eliminar_libro(id_libro):
    if not admin_requerido():
        flash("No tienes permisos para esta acción.")
        return redirect(url_for("inicio"))

    conn = get_db_connection()
    conn.execute("DELETE FROM libros WHERE id = ?", (id_libro,))
    conn.commit()
    conn.close()

    flash("Libro eliminado correctamente.")
    return redirect(url_for("panel_admin"))

@app.route("/admin/usuario/<int:id_usuario>")
def admin_ver_usuario(id_usuario):
    if not admin_requerido():
        flash("No tienes permisos para entrar a esta sección.")
        return redirect(url_for("inicio"))

    conn = get_db_connection()

    usuario = conn.execute(
        "SELECT id, nombre, email, rol FROM usuarios WHERE id = ?",
        (id_usuario,)
    ).fetchone()

    if not usuario:
        conn.close()
        flash("Usuario no encontrado.")
        return redirect(url_for("panel_admin"))

    libros = conn.execute(
        "SELECT * FROM libros WHERE usuario_id = ? ORDER BY id DESC",
        (id_usuario,)
    ).fetchall()

    resumen = conn.execute("""
        SELECT estado, COUNT(*) as total
        FROM libros
        WHERE usuario_id = ?
        GROUP BY estado
    """, (id_usuario,)).fetchall()

    conn.close()

    return render_template(
        "admin_usuario.html",
        usuario=usuario,
        libros=libros,
        resumen=resumen
    )

@app.route("/usar-edicion", methods=["POST"])
def usar_edicion():
    if not usuario_logueado():
        return redirect(url_for("login"))

    datos = {
        "titulo": request.form.get("titulo", ""),
        "autor": request.form.get("autor", ""),
        "anio": request.form.get("anio", ""),
        "imagen": request.form.get("imagen", "")
    }

    return render_template("agregar.html", datos=datos)


@app.route("/guardar", methods=["POST"])
def guardar_libro():
    if not usuario_logueado():
        return redirect(url_for("login"))

    titulo = request.form.get("titulo")
    autor = request.form.get("autor")
    anio = request.form.get("anio")
    estado = request.form.get("estado")
    imagen = request.form.get("imagen")
    favorito = 1 if request.form.get("favorito") == "on" else 0
    rating = request.form.get("rating")
    nota = request.form.get("nota")

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO libros (titulo, autor, anio, estado, imagen, usuario_id, favorito, rating, nota)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (titulo, autor, anio, estado, imagen, session["usuario_id"], favorito, rating, nota)
    )
    conn.commit()
    conn.close()

    # return redirect(url_for("inicio", estado=estado))  #Se cambio por que volvia a leidos
    flash("Libro guardado correctamente")
    return redirect(url_for("vista_agregar"))


@app.route("/editar/<int:id_libro>")
def vista_editar(id_libro):
    if not usuario_logueado():
        return redirect(url_for("login"))

    conn = get_db_connection()
    libro = conn.execute(
        "SELECT * FROM libros WHERE id = ? AND usuario_id = ?",
        (id_libro, session["usuario_id"])
    ).fetchone()
    conn.close()

    if not libro:
        return redirect(url_for("inicio"))

    return render_template("editar.html", libro=libro)


@app.route("/actualizar/<int:id_libro>", methods=["POST"])
def actualizar_libro(id_libro):
    if not usuario_logueado():
        return redirect(url_for("login"))

    titulo = request.form.get("titulo")
    autor = request.form.get("autor")
    anio = request.form.get("anio")
    estado = request.form.get("estado")
    imagen = request.form.get("imagen")
    favorito = 1 if request.form.get("favorito") == "on" else 0
    rating = request.form.get("rating")
    nota = request.form.get("nota")

    conn = get_db_connection()
    conn.execute(
        """
        UPDATE libros
        SET titulo = ?, autor = ?, anio = ?, estado = ?, imagen = ?, favorito = ?, rating = ?, nota = ?
        WHERE id = ? AND usuario_id = ?
        """,
        (titulo, autor, anio, estado, imagen, favorito, rating, nota, id_libro, session["usuario_id"])
    )
    conn.commit()
    conn.close()

    return redirect(url_for("inicio", estado=estado))


@app.route("/eliminar/<int:id_libro>", methods=["POST"])
def eliminar_libro(id_libro):
    if not usuario_logueado():
        return redirect(url_for("login"))

    conn = get_db_connection()

    libro = conn.execute(
        "SELECT estado FROM libros WHERE id = ? AND usuario_id= ?",
        (id_libro, session["usuario_id"])
    ).fetchone()

    if libro:
        estado = libro["estado"]
        conn.execute("DELETE FROM libros WHERE id = ? AND usuario_id = ?", (id_libro, session["usuario_id"]))
        conn.commit()
        conn.close()
        return redirect(url_for("inicio", estado=estado))

    conn.close()
    return redirect(url_for("inicio"))


if __name__ == "__main__":
    init_db()
    crear_admin()
    app.run(debug=True)