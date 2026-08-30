import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "activity.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Columnas añadidas después de la primera versión del esquema. `CREATE TABLE
# IF NOT EXISTS` no las añade a una base ya creada, así que se aplican a mano
# al arrancar. Añadir aquí cualquier columna nueva futura, nunca renombrar ni
# borrar (el histórico del experimento no se puede rehacer).
MIGRACIONES = {
    "metrics_snapshot": [
        ("suscriptores_organicos", "INTEGER"),
        ("suscriptores_meta", "INTEGER"),
        ("suscriptores_directos", "INTEGER"),
    ],
    "activity_log": [
        ("cambios", "TEXT"),
        ("envio", "TEXT"),
    ],
}


def _aplicar_migraciones(conn):
    for tabla, columnas in MIGRACIONES.items():
        existentes = {fila["name"] for fila in conn.execute(f"PRAGMA table_info({tabla})")}
        if not existentes:  # la tabla aún no existe: el CREATE de schema.sql ya la trae completa
            continue
        for nombre, tipo in columnas:
            if nombre not in existentes:
                conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}")


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    _aplicar_migraciones(conn)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"DB inicializada en {DB_PATH}")
