"""Busca textual no acervo pessoal de conhecimento.

Bate em GET /busca do acervo: full-text do Postgres, sem LLM do lado de lá.
Determinístico e rápido — é a rota certa pra "eu já vi algo sobre isso?".
"""
from app.ferramentas import ferramenta
from app.ferramentas.acervo.cliente import AcervoIndisponivel, get


@ferramenta(
    nome="acervo_buscar",
    descricao=(
        "Procura um termo no acervo pessoal de conhecimento do usuário — vídeos "
        "transcritos que ele assistiu, sobre ferramentas, tecnologias e outros "
        "assuntos. Use quando ele perguntar se já viu algo sobre um tema, em "
        "qual vídeo falaram de alguma ferramenta, ou o que ele tem estudado "
        "sobre um assunto."
    ),
    parametros={
        "type": "object",
        "properties": {
            "termo": {
                "type": "string",
                "description": "O que procurar. Uma palavra ou expressão curta.",
            }
        },
        "required": ["termo"],
    },
)
def acervo_buscar(termo: str) -> str:
    try:
        dados = get("/busca", q=termo, limite=5)
    except AcervoIndisponivel as erro:
        return str(erro)

    total = dados.get("total", 0)
    if not total:
        return f"Nada no acervo sobre '{termo}'."

    titulos = [v["titulo"] for v in dados.get("videos", [])[:3]]
    palavra = "ocorrência" if total == 1 else "ocorrências"
    return f"{total} {palavra} de '{termo}' no acervo. Aparece em: " + "; ".join(titulos) + "."
