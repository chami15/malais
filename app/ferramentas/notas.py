"""Anotações. Ficam no seu banco, no seu aparelho — nada sai de casa."""
from app.banco import conexao
from app.ferramentas import ferramenta


@ferramenta(
    nome="anotar",
    descricao=(
        "Salva uma anotação. Use quando o usuário pedir para anotar, lembrar, "
        "guardar ou registrar alguma informação."
    ),
    parametros={
        "type": "object",
        "properties": {
            "texto": {
                "type": "string",
                "description": "O conteúdo da anotação, já limpo e bem escrito.",
            }
        },
        "required": ["texto"],
    },
)
def anotar(texto: str) -> str:
    with conexao() as con:
        con.execute("INSERT INTO notas (texto) VALUES (?)", (texto,))
    return "Anotação salva."


@ferramenta(
    nome="listar_notas",
    descricao="Lista as anotações mais recentes do usuário.",
    parametros={
        "type": "object",
        "properties": {
            "quantidade": {
                "type": "integer",
                "description": "Quantas anotações trazer. Padrão 5.",
            }
        },
    },
)
def listar_notas(quantidade: int = 5) -> str:
       # O LLM às vezes manda "5" em vez de 5. Sem essa conversão o SQLite recebe
       # texto no LIMIT e devolve resultado errado ou erro.
    quantidade = int(quantidade)
    with conexao() as con:
        linhas = con.execute(
            "SELECT texto, criada_em FROM notas ORDER BY id DESC LIMIT ?",
            (quantidade,),
        ).fetchall()
    if not linhas:
        return "Nenhuma anotação salva ainda."
    return "\n".join(f"- {l['texto']} ({l['criada_em']})" for l in linhas)
