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


def _acrescentar_colunas(con):
    """Cuida das colunas que nasceram depois do banco.

    `CREATE TABLE IF NOT EXISTS` não mexe em tabela que já existe: coluna nova
    entra em quem instalou hoje e não entra em quem já tinha o banco. O sintoma
    é o pior possível — funciona na sua máquina, quebra no aparelho que está de
    pé há meses. Toda coluna adicionada depois da primeira versão entra aqui.
    """
    novas = {
        "notas": {"atualizada_em": "TEXT"},
    }
    for tabela, colunas in novas.items():
        existentes = {linha["name"] for linha in con.execute(f"PRAGMA table_info({tabela})")}
        for coluna, tipo in colunas.items():
            if coluna not in existentes:
                con.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")


def preparar():
    with conexao() as con:
        con.executescript(ESQUEMA)
        _acrescentar_colunas(con)


def registrar(comando: str, resposta: str):
    """Todo comando fica logado. Isso vira ouro pra debugar o Malais depois."""
    with conexao() as con:
        con.execute(
            "INSERT INTO historico (comando, resposta) VALUES (?, ?)",
            (comando, resposta),
        )
