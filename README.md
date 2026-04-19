📚 Biblioteca Web Personal

Aplicación web desarrollada con Flask y SQLite para gestionar una biblioteca personal.

🚀 Funcionalidades
- Registro e inicio de sesión de usuarios
- Recuperación de contraseña
- Roles de usuario y administrador
- Gestión de libros (crear, editar, eliminar)
- Clasificación por estado (leídos, pendientes, en proceso, etc.)
- Búsqueda de libros con Google Books API
- Favoritos ⭐
- Calificación de libros ⭐ (1 a 5)
- Notas personales 📝
- Panel administrador con control de usuarios
- Modo claro / oscuro 🌙

🛠️ Tecnologías
- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript

⚙️ Instalación

git clone https://github.com/tuusuario/biblioteca-web.git
cd biblioteca-web

python -m venv venv
source venv/Scripts/activate  # Windows

pip install -r requirements.txt

🔐 Configuración

Crear un archivo .env en la raíz del proyecto:

GOOGLE_API_KEY=tu_api_key
SECRET_KEY=tu_clave_segura

▶️ Ejecutar

python app.py
👩‍💻 Autora

Proyecto desarrollado por Yuri 🚀