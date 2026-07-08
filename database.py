"""Camada de acesso ao banco SQLite de gastos."""
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent / "finances.db"

CATEGORIAS_PADRAO = [
    "Alimentação",
    "Moradia",
    "Transporte",
    "Saúde",
    "Lazer",
    "Educação",
    "Cartão de Crédito",
    "Energia",
    "Água",
    "Internet",
    "Contas Fixas",
    "Outros",
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL,
                valor REAL NOT NULL,
                gasto_fixo_id INTEGER
            )
            """
        )
        colunas = [r["name"] for r in conn.execute("PRAGMA table_info(gastos)")]
        if "gasto_fixo_id" not in colunas:
            conn.execute("ALTER TABLE gastos ADD COLUMN gasto_fixo_id INTEGER")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gastos_fixos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                categoria TEXT NOT NULL,
                valor_esperado REAL NOT NULL
            )
            """
        )


def adicionar_gasto(
    data_gasto: date,
    descricao: str,
    categoria: str,
    valor: float,
    gasto_fixo_id: int | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO gastos (data, descricao, categoria, valor, gasto_fixo_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (data_gasto.isoformat(), descricao, categoria, valor, gasto_fixo_id),
        )


def remover_gasto(gasto_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))


def listar_gastos(ano: int | None = None, mes: int | None = None) -> list[sqlite3.Row]:
    query = "SELECT * FROM gastos"
    params: list[str] = []
    if ano is not None and mes is not None:
        prefixo = f"{ano:04d}-{mes:02d}"
        query += " WHERE data LIKE ?"
        params.append(f"{prefixo}%")
    query += " ORDER BY data DESC, id DESC"
    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def meses_disponiveis() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT substr(data, 1, 7) AS mes FROM gastos ORDER BY mes DESC"
        ).fetchall()
    return [r["mes"] for r in rows]


def adicionar_gasto_fixo(nome: str, categoria: str, valor_esperado: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO gastos_fixos (nome, categoria, valor_esperado) VALUES (?, ?, ?)",
            (nome, categoria, valor_esperado),
        )


def remover_gasto_fixo(gasto_fixo_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM gastos_fixos WHERE id = ?", (gasto_fixo_id,))


def listar_gastos_fixos() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM gastos_fixos ORDER BY nome").fetchall()


def gastos_fixos_pendentes(ano: int, mes: int) -> list[sqlite3.Row]:
    """Gastos fixos que ainda não foram lançados no mês informado."""
    prefixo = f"{ano:04d}-{mes:02d}"
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT gf.* FROM gastos_fixos gf
            WHERE NOT EXISTS (
                SELECT 1 FROM gastos g
                WHERE g.gasto_fixo_id = gf.id AND substr(g.data, 1, 7) = ?
            )
            ORDER BY gf.nome
            """,
            (prefixo,),
        ).fetchall()
