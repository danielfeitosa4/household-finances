"""Camada de acesso ao banco de dados dos gastos.

Funciona com SQLite (arquivo local, para desenvolvimento) ou PostgreSQL
(nuvem, permanente). O banco é escolhido pela variável de ambiente
DATABASE_URL; se ela não existir, usa o SQLite local finances.db.
"""
import os
from datetime import date
from pathlib import Path

from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    insert,
    select,
)
from sqlalchemy.engine import Engine

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

metadata = MetaData()

gastos_tbl = Table(
    "gastos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("data", String, nullable=False),
    Column("descricao", String, nullable=False),
    Column("categoria", String, nullable=False),
    Column("valor", Float, nullable=False),
    Column("gasto_fixo_id", Integer, nullable=True),
)

gastos_fixos_tbl = Table(
    "gastos_fixos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nome", String, nullable=False),
    Column("categoria", String, nullable=False),
    Column("valor_esperado", Float, nullable=False),
)

_engine: Engine | None = None


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        return f"sqlite:///{DB_PATH}"
    # Provedores costumam entregar postgres:// ; SQLAlchemy espera o driver.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(_database_url(), pool_pre_ping=True)
    return _engine


def init_db() -> None:
    metadata.create_all(get_engine())


def adicionar_gasto(
    data_gasto: date,
    descricao: str,
    categoria: str,
    valor: float,
    gasto_fixo_id: int | None = None,
) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            insert(gastos_tbl).values(
                data=data_gasto.isoformat(),
                descricao=descricao,
                categoria=categoria,
                valor=valor,
                gasto_fixo_id=gasto_fixo_id,
            )
        )


def remover_gasto(gasto_id: int) -> None:
    with get_engine().begin() as conn:
        conn.execute(delete(gastos_tbl).where(gastos_tbl.c.id == gasto_id))


def listar_gastos(ano: int | None = None, mes: int | None = None) -> list[dict]:
    consulta = select(gastos_tbl)
    if ano is not None and mes is not None:
        prefixo = f"{ano:04d}-{mes:02d}"
        consulta = consulta.where(gastos_tbl.c.data.like(f"{prefixo}%"))
    consulta = consulta.order_by(gastos_tbl.c.data.desc(), gastos_tbl.c.id.desc())
    with get_engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(consulta)]


def meses_disponiveis() -> list[str]:
    with get_engine().connect() as conn:
        linhas = conn.execute(
            select(gastos_tbl.c.data).order_by(gastos_tbl.c.data.desc())
        )
        meses = {r[0][:7] for r in linhas}
    return sorted(meses, reverse=True)


def adicionar_gasto_fixo(nome: str, categoria: str, valor_esperado: float) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            insert(gastos_fixos_tbl).values(
                nome=nome, categoria=categoria, valor_esperado=valor_esperado
            )
        )


def remover_gasto_fixo(gasto_fixo_id: int) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            delete(gastos_fixos_tbl).where(gastos_fixos_tbl.c.id == gasto_fixo_id)
        )


def listar_gastos_fixos() -> list[dict]:
    with get_engine().connect() as conn:
        return [
            dict(r._mapping)
            for r in conn.execute(
                select(gastos_fixos_tbl).order_by(gastos_fixos_tbl.c.nome)
            )
        ]


def gastos_fixos_pendentes(ano: int, mes: int) -> list[dict]:
    """Gastos fixos que ainda não foram lançados no mês informado."""
    prefixo = f"{ano:04d}-{mes:02d}"
    lancados = (
        select(gastos_tbl.c.gasto_fixo_id)
        .where(gastos_tbl.c.gasto_fixo_id == gastos_fixos_tbl.c.id)
        .where(gastos_tbl.c.data.like(f"{prefixo}%"))
    )
    consulta = (
        select(gastos_fixos_tbl)
        .where(~lancados.exists())
        .order_by(gastos_fixos_tbl.c.nome)
    )
    with get_engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(consulta)]
