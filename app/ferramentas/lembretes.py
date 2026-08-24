"""Lembretes: coisa rápida pra lembrar agora, lida e descartada depois.
Ficam no seu banco, no seu aparelho — nada sai de casa.

Chamava-se "nota" até o acervo entrar em cena. O acervo também tem "nota", mas
com outro sentido — texto que vira conhecimento permanente, conectado a um
grafo. O lembrete daqui é o oposto: peso leve, existe pra ser esquecido depois
de resolvido. Nomes diferentes evitam confundir os dois quando o Malais
aprender a falar com o acervo.

Sobre o id nas respostas: quem lê o retorno destas ferramentas é o LLM, não o
usuário. Ele precisa de um identificador pra apagar ou corrigir o lembrete
certo, mas ninguém vai dizer "apaga o lembrete número sete" em voz alta. Então
listar e buscar devolvem o id, o LLM guarda, e o usuário fala "apaga o do
café". O número existe entre o LLM e o banco — nunca é falado nem ouvido.
"""
from app.banco import conexao
from app.ferramentas import ferramenta

# O id vai entre colchetes pra ficar claro pro LLM que não é parte do texto.
AVISO_ID = "O número entre colchetes é o id, para você usar em outra ferramenta. Não fale ele em voz alta."


def _formatar(linhas) -> str:
    return "\n".join(f"[{l['id']}] {l['texto']} ({l['criada_em']})" for l in linhas)


@ferramenta(
    nome="lembrar",
    descricao=(
        "Salva um lembrete rápido. Use quando o usuário pedir para lembrar, "
        "anotar, guardar ou registrar alguma informação pra consultar depois."
    ),
    parametros={
        "type": "object",
        "properties": {
            "texto": {
                "type": "string",
                "description": "O conteúdo do lembrete, já limpo e bem escrito.",
            }
        },
        "required": ["texto"],
    },
)
def lembrar(texto: str) -> str:
    with conexao() as con:
        con.execute("INSERT INTO lembretes (texto) VALUES (?)", (texto,))
    return "Lembrete salvo."


@ferramenta(
    nome="listar_lembretes",
    descricao=(
        "Lista os lembretes mais recentes do usuário. Use quando ele perguntar "
        "o que ele tem pra lembrar, sem dizer sobre o quê. Se ele procura um "
        "assunto específico, prefira buscar_lembretes. " + AVISO_ID
    ),
    parametros={
        "type": "object",
        "properties": {
            "quantidade": {
                "type": "integer",
                "description": "Quantos lembretes trazer. Padrão 5.",
            }
        },
    },
)
def listar_lembretes(quantidade: int = 5) -> str:
    # O LLM às vezes manda "5" em vez de 5. Sem essa conversão o SQLite recebe
    # texto no LIMIT e devolve resultado errado ou erro.
    quantidade = int(quantidade)
    with conexao() as con:
        linhas = con.execute(
            "SELECT id, texto, criada_em FROM lembretes ORDER BY id DESC LIMIT ?",
            (quantidade,),
        ).fetchall()
    if not linhas:
        return "Nenhum lembrete salvo ainda."
    return _formatar(linhas)


@ferramenta(
    nome="buscar_lembretes",
    descricao=(
        "Procura lembretes que contenham uma palavra ou trecho. Use SEMPRE que "
        "o usuário se referir a um lembrete por assunto — 'o do mercado', 'o que "
        "eu tinha pra lembrar sobre o carro' — e também antes de apagar ou "
        "atualizar, para descobrir o id do lembrete certo. " + AVISO_ID
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
def buscar_lembretes(termo: str, quantidade: int = 5) -> str:
    quantidade = int(quantidade)
    with conexao() as con:
        linhas = con.execute(
            "SELECT id, texto, criada_em FROM lembretes "
            "WHERE texto LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{termo}%", quantidade),
        ).fetchall()
    if not linhas:
        return f"Nenhum lembrete fala sobre '{termo}'."
    return _formatar(linhas)


@ferramenta(
    nome="atualizar_lembrete",
    descricao=(
        "Reescreve o texto de um lembrete existente. Use quando o usuário quiser "
        "corrigir, mudar ou completar algo que já tinha pedido pra lembrar. "
        "Descubra o id com buscar_lembretes ou listar_lembretes antes de chamar "
        "— nunca invente um id."
    ),
    parametros={
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
                "description": "O id do lembrete, vindo de buscar_lembretes ou listar_lembretes.",
            },
            "texto": {
                "type": "string",
                "description": "O novo conteúdo completo do lembrete.",
            },
        },
        "required": ["id", "texto"],
    },
)
def atualizar_lembrete(id: int, texto: str) -> str:
    id = int(id)
    with conexao() as con:
        cursor = con.execute(
            "UPDATE lembretes SET texto = ?, atualizada_em = datetime('now', 'localtime') "
            "WHERE id = ?",
            (texto, id),
        )
        if not cursor.rowcount:
            # Texto de volta pro LLM, não exceção: ele busca de novo e tenta outro id.
            return f"Não existe lembrete com id {id}."
    return "Lembrete atualizado."


@ferramenta(
    nome="apagar_lembrete",
    descricao=(
        "Apaga um lembrete de vez. Use quando o usuário disser que já resolveu "
        "aquilo, ou pedir para esquecer, remover ou apagar. Descubra o id com "
        "buscar_lembretes ou listar_lembretes antes de chamar — nunca invente "
        "um id. Se a busca trouxer mais de um lembrete parecido, pergunte qual "
        "antes de apagar."
    ),
    parametros={
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
                "description": "O id do lembrete, vindo de buscar_lembretes ou listar_lembretes.",
            }
        },
        "required": ["id"],
    },
)
def apagar_lembrete(id: int) -> str:
    id = int(id)
    with conexao() as con:
        linha = con.execute("SELECT texto FROM lembretes WHERE id = ?", (id,)).fetchone()
        if not linha:
            return f"Não existe lembrete com id {id}."
        con.execute("DELETE FROM lembretes WHERE id = ?", (id,))
    # Devolve o texto apagado de propósito: ditado erra, e ouvir o que sumiu é a
    # única chance do usuário perceber na hora que foi o lembrete errado.
    return f"Apaguei o lembrete: {linha['texto']}"
