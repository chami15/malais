"""SQLite. Simples de propósito — zero serviço extra rodando no celular."""
import sqlite3
from contextlib import contextmanager

from app.config import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS notas (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    texto    TEXT NOT NULL,
    criada_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS historico (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    comando   TEXT NOT NULL,
    resposta  TEXT,
    criada_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


@contextmanager
def conexao():
    con = sqlite3.connect(config.BANCO)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def preparar():
    with conexao() as con:
        con.executescript(ESQUEMA)


def registrar(comando: str, resposta: str):
    """Todo comando fica logado. Isso vira ouro pra debugar o Malais depois."""
    with conexao() as con:
        con.execute(
            "INSERT INTO historico (comando, resposta) VALUES (?, ?)",
            (comando, resposta),
        )
