"""Anotações. Ficam no seu banco, no seu aparelho — nada sai de casa.

Sobre o id nas respostas: quem lê o retorno destas ferramentas é o LLM, não o
usuário. Ele precisa de um identificador pra apagar ou corrigir a nota certa,
mas ninguém vai dizer "apaga a nota número sete" em voz alta. Então listar e
buscar devolvem o id, o LLM guarda, e o usuário fala "apaga a do café". O
número existe entre o LLM e o banco — nunca é falado nem ouvido.
"""
from app.banco import conexao
from app.ferramentas import ferramenta

# O id vai entre colchetes pra ficar claro pro LLM que não é parte do texto.
AVISO_ID = "O número entre colchetes é o id, para você usar em outra ferramenta. Não fale ele em voz alta."


def _formatar(linhas) -> str:
    return "\n".join(f"[{l['id']}] {l['texto']} ({l['criada_em']})" for l in linhas)


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
    descricao=(
        "Lista as anotações mais recentes do usuário. Use quando ele perguntar "
        "o que anotou, sem dizer sobre o quê. Se ele procura um assunto "
        "específico, prefira buscar_notas. " + AVISO_ID
    ),
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
            "SELECT id, texto, criada_em FROM notas ORDER BY id DESC LIMIT ?",
            (quantidade,),
        ).fetchall()
    if not linhas:
        return "Nenhuma anotação salva ainda."
    return _formatar(linhas)


@ferramenta(
    nome="buscar_notas",
    descricao=(
        "Procura anotações que contenham uma palavra ou trecho. Use SEMPRE que "
        "o usuário se referir a uma anotação por assunto — 'a do mercado', 'o que "
        "eu anotei sobre o carro' — e também antes de apagar ou atualizar, para "
        "descobrir o id da nota certa. " + AVISO_ID
    ),
    parametros={
        "type": "object",
        "properties": {
            "termo": {
                "type": "string",
                "description": (
                    "Palavra-chave a procurar. Use uma palavra só, a mais "
                    "distintiva, em vez da frase inteira."
                ),
            },
            "quantidade": {
                "type": "integer",
                "description": "Máximo de resultados. Padrão 5.",
            },
        },
        "required": ["termo"],
    },
)
def buscar_notas(termo: str, quantidade: int = 5) -> str:
    quantidade = int(quantidade)
    with conexao() as con:
        linhas = con.execute(
            "SELECT id, texto, criada_em FROM notas "
            "WHERE texto LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{termo}%", quantidade),
        ).fetchall()
    if not linhas:
        return f"Nenhuma anotação fala sobre '{termo}'."
    return _formatar(linhas)


@ferramenta(
    nome="atualizar_nota",
    descricao=(
        "Reescreve o texto de uma anotação existente. Use quando o usuário quiser "
        "corrigir, mudar ou completar algo que já anotou. Descubra o id com "
        "buscar_notas ou listar_notas antes de chamar — nunca invente um id."
    ),
    parametros={
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
                "description": "O id da anotação, vindo de buscar_notas ou listar_notas.",
            },
            "texto": {
                "type": "string",
                "description": "O novo conteúdo completo da anotação.",
            },
        },
        "required": ["id", "texto"],
    },
)
def atualizar_nota(id: int, texto: str) -> str:
    id = int(id)
    with conexao() as con:
        cursor = con.execute(
            "UPDATE notas SET texto = ?, atualizada_em = datetime('now', 'localtime') "
            "WHERE id = ?",
            (texto, id),
        )
        if not cursor.rowcount:
            # Texto de volta pro LLM, não exceção: ele busca de novo e tenta outro id.
            return f"Não existe anotação com id {id}."
    return "Anotação atualizada."


@ferramenta(
    nome="apagar_nota",
    descricao=(
        "Apaga uma anotação de vez. Use quando o usuário disser que já resolveu "
        "aquilo, ou pedir para esquecer, remover ou apagar. Descubra o id com "
        "buscar_notas ou listar_notas antes de chamar — nunca invente um id. "
        "Se a busca trouxer mais de uma nota parecida, pergunte qual antes de apagar."
    ),
    parametros={
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
                "description": "O id da anotação, vindo de buscar_notas ou listar_notas.",
            }
        },
        "required": ["id"],
    },
)
def apagar_nota(id: int) -> str:
    id = int(id)
    with conexao() as con:
        linha = con.execute("SELECT texto FROM notas WHERE id = ?", (id,)).fetchone()
        if not linha:
            return f"Não existe anotação com id {id}."
        con.execute("DELETE FROM notas WHERE id = ?", (id,))
    # Devolve o texto apagado de propósito: ditado erra, e ouvir o que sumiu é a
    # única chance do usuário perceber na hora que foi a nota errada.
    return f"Apaguei a anotação: {linha['texto']}"
