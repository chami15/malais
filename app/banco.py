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


def ultimas_trocas(quantidade: int, minutos: int) -> list[sqlite3.Row]:
    """As últimas trocas recentes, em ordem cronológica, pra virar memória curta.

    Dois limites, e os dois precisam existir:

    - `quantidade` segura o custo. Cada troca vira duas mensagens no prompt, e
      todas viajam em toda chamada à Groq.
    - `minutos` segura o absurdo. Sem ele, o que você falou de manhã voltaria
      como contexto à noite, e o Malais responderia a uma conversa que acabou.

    Descarta resposta vazia: mensagem de erro e eco viram assistant turn sem
    conteúdo útil, e só confundem quem lê depois.
    """
    if quantidade <= 0:
        return []
    with conexao() as con:
        linhas = con.execute(
            "SELECT comando, resposta FROM historico "
            "WHERE resposta IS NOT NULL AND resposta != '' "
            "  AND criada_em >= datetime('now', 'localtime', ?) "
            "ORDER BY id DESC LIMIT ?",
            (f"-{int(minutos)} minutes", int(quantidade)),
        ).fetchall()
    # Vem do mais novo pro mais velho por causa do LIMIT; o prompt precisa do contrário.
    return list(reversed(linhas))
