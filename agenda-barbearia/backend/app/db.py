import os
import sqlite3
from collections.abc import Iterator


def caminho_do_banco() -> str:
    return os.environ.get("DB_PATH", "agenda.db")


def criar_tabelas() -> None:
    with sqlite3.connect(caminho_do_banco()) as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS agendamentos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo       TEXT    NOT NULL UNIQUE,
                nome         TEXT    NOT NULL,
                telefone     TEXT    NOT NULL,
                servico_id   INTEGER NOT NULL,
                inicio       TEXT    NOT NULL,
                fim          TEXT    NOT NULL,
                cancelado_em TEXT,
                criado_em    TEXT    NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conexao.execute(
            "CREATE INDEX IF NOT EXISTS idx_agendamentos_inicio ON agendamentos (inicio)"
        )


def conexao() -> Iterator[sqlite3.Connection]:
    """Uma conexão por requisição.

    isolation_level=None deixa eu controlar a transação na mão (BEGIN IMMEDIATE),
    que é o que impede duas pessoas de pegarem o mesmo horário ao mesmo tempo.
    check_same_thread=False porque o FastAPI pode abrir e usar a conexão em threads diferentes.
    """
    con = sqlite3.connect(caminho_do_banco(), isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()
