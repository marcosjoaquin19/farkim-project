# ==============================================
# Nombre:      crear_config_auth.py
# Descripción: Genera el archivo config.yaml con las credenciales
#              de acceso al dashboard de Streamlit.
#              Ejecutar UNA SOLA VEZ para crear el archivo.
#              El config.yaml está en .gitignore — nunca se sube a GitHub.
# Autor:       Farkim Sistemas - Marcos Joaquin
# Fecha:       2026-03-19
# ==============================================

import yaml
import bcrypt

# ----------------------------------------------
# USUARIOS DEL DASHBOARD
# Modificar acá para agregar o cambiar usuarios
# ----------------------------------------------
USUARIOS = {
    "gerente": {
        "nombre":    "Gerente",
        "apellido":  "Farkim",
        "email":     "sistemas.farkim@gmail.com",
        "password":  "farkim2026",   # ← cambiar por contraseña real
        "rol":       "gerente"
    },
    "sistemas": {
        "nombre":    "Marcos",
        "apellido":  "Joaquin",
        "email":     "marcosjoaquin1910@gmail.com",
        "password":  "sistemas2026",  # ← cambiar por contraseña real
        "rol":       "admin"
    }
}

def generar_config():
    """
    Genera el archivo config.yaml con las contraseñas encriptadas.
    bcrypt convierte "farkim2026" en un hash que nadie puede revertir.
    """
    print("Generando config.yaml con contraseñas encriptadas...")

    # Armamos la estructura de credenciales
    # bcrypt.hashpw encripta cada contraseña de forma irreversible
    credentials = {"usernames": {}}
    for username, datos in USUARIOS.items():
        password_hash = bcrypt.hashpw(
            datos["password"].encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        credentials["usernames"][username] = {
            "first_name": datos["nombre"],
            "last_name":  datos["apellido"],
            "email":      datos["email"],
            "password":   password_hash,   # contraseña encriptada con bcrypt
            "roles":      [datos["rol"]]
        }

    # Configuración completa del archivo YAML
    config = {
        "credentials": credentials,
        "cookie": {
            "name":         "farkim_dashboard",
            "key":          "farkim_secret_key_2026",  # clave interna para la cookie
            "expiry_days":  7   # la sesión dura 7 días sin volver a loguearse
        }
    }

    # Guardamos el archivo
    with open("config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    print("config.yaml generado exitosamente.")
    print()
    print("Usuarios creados:")
    for username, datos in USUARIOS.items():
        print(f"  Usuario: {username:<12} Contraseña: {datos['password']}")
    print()
    print("IMPORTANTE: Cambiá las contraseñas en este script antes de usar en producción.")
    print("El archivo config.yaml NO se sube a GitHub (está en .gitignore).")


if __name__ == "__main__":
    generar_config()
