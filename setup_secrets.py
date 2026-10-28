"""
Crea los scopes si no existen y actualiza los secretos de Massive y Lakebase.

Ejecutar con una identidad autenticada en Databricks:
    python setup_secrets.py

No guardes ni publiques los valores de los secretos.
"""

import getpass
from urllib.parse import urlsplit

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import ResourceAlreadyExists
from databricks.sdk.service import workspace


def ensure_scope(client: WorkspaceClient, scope: str) -> None:
    """Crea el scope; si ya existe, continúa sin borrarlo."""
    try:
        client.secrets.create_scope(scope=scope)
        print(f"Scope '{scope}' creado.")
    except ResourceAlreadyExists:
        print(f"Scope '{scope}' ya existe; se reutilizará.")


def read_lakebase_url() -> str:
    """Solicita una conexión PostgreSQL sin mostrar su contenido."""
    while True:
        value = getpass.getpass(
            "Pega la conexión PostgreSQL de Lakebase: "
        ).strip()

        try:
            parts = urlsplit(value)
            valid = (
                parts.scheme in ("postgresql", "postgres")
                and bool(parts.hostname)
                and not parts.hostname.lower().endswith(
                    ".databricksapps.com"
                )
                and bool(parts.username)
                and parts.path not in ("", "/")
                and not parts.fragment
            )
            # También comprueba que el puerto sea válido.
            _ = parts.port
        except ValueError:
            valid = False

        if valid:
            return value

        print(
            "Conexión no válida. Copia la URL desde Lakebase > Connect.\n"
            "Formato esperado:\n"
            "postgresql://usuario:contraseña@host:5432/"
            "databricks_postgres?sslmode=require\n"
            "No uses la dirección https://...databricksapps.com."
        )


def main() -> None:
    # Recoger los valores antes de modificar los secretos.
    massive_api_key = getpass.getpass(
        "Pega tu API key de Massive: "
    ).strip()

    if not massive_api_key:
        raise ValueError("La API key de Massive no puede estar vacía.")

    lakebase_url = read_lakebase_url()

    client = WorkspaceClient()

    ensure_scope(client, "massive")
    ensure_scope(client, "database")

    client.secrets.put_secret(
        scope="massive",
        key="api-key",
        string_value=massive_api_key,
    )
    print("Secreto 'massive/api-key' actualizado.")

    client.secrets.put_secret(
        scope="database",
        key="lakebase-url",
        string_value=lakebase_url,
    )
    print("Secreto 'database/lakebase-url' actualizado.")

    # Conserva los permisos del script original:
    # el grupo 'users' puede leer ambos scopes.
    for scope in ("database", "massive"):
        client.secrets.put_acl(
            scope=scope,
            principal="users",
            permission=workspace.AclPermission.READ,
        )
        print(f"Permiso READ configurado para 'users' en '{scope}'.")

    print(
        "Configuración completada. "
        "Vuelve a desplegar la app en Databricks."
    )


if __name__ == "__main__":
    main()