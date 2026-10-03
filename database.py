import os
import sqlite3
import time

DB_FILE = os.getenv("ACCESS_DB", "usuarios.db")


def _connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                telegram_id INTEGER PRIMARY KEY,
                expires_at INTEGER NOT NULL,
                added_by INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)


def dar_acceso(telegram_id: int, dias: int, admin_id: int) -> int:
    ahora = int(time.time())

    with _connect() as conn:
        row = conn.execute(
            "SELECT expires_at FROM usuarios WHERE telegram_id = ?",
            (telegram_id,)
        ).fetchone()

        # Si aún tiene acceso, suma los días al vencimiento actual.
        inicio = row["expires_at"] if row and row["expires_at"] > ahora else ahora
        vencimiento = inicio + dias * 86400

        conn.execute("""
            INSERT INTO usuarios (telegram_id, expires_at, added_by, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                expires_at = excluded.expires_at,
                added_by = excluded.added_by
        """, (telegram_id, vencimiento, admin_id, ahora))

    return vencimiento


def quitar_acceso(telegram_id: int):
    with _connect() as conn:
        conn.execute(
            "DELETE FROM usuarios WHERE telegram_id = ?",
            (telegram_id,)
        )


def acceso_activo(telegram_id: int) -> bool:
    ahora = int(time.time())

    with _connect() as conn:
        row = conn.execute(
            "SELECT expires_at FROM usuarios WHERE telegram_id = ?",
            (telegram_id,)
        ).fetchone()

    return bool(row and row["expires_at"] > ahora)


def obtener_vencimiento(telegram_id: int):
    with _connect() as conn:
        row = conn.execute(
            "SELECT expires_at FROM usuarios WHERE telegram_id = ?",
            (telegram_id,)
        ).fetchone()

    return row["expires_at"] if row else None


def usuarios_activos():
    ahora = int(time.time())

    with _connect() as conn:
        return conn.execute("""
            SELECT telegram_id, expires_at
            FROM usuarios
            WHERE expires_at > ?
            ORDER BY expires_at ASC
        """, (ahora,)).fetchall()
      
