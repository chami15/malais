"""Ficha de uma ferramenta ou tecnologia, do acervo pessoal de conhecimento.

Duas chamadas ao acervo, as duas determinísticas — nenhuma passa por LLM do
lado de lá, é leitura pura do que já foi escrito: primeiro acha a entidade
pelo nome (o LLM do Malais não sabe o slug), depois lê a ficha dela.
"""
from app.ferramentas import ferramenta
from app.ferramentas.acervo.cliente import AcervoIndisponivel, get


@ferramenta(
    nome="acervo_consultar_ficha",
    descricao=(
        "Consulta a ficha de uma ferramenta, tecnologia ou tema no acervo "
        "pessoal de conhecimento: para que serve, quando usar, quando não "
        "usar. Use quando o usuário perguntar sobre algo específico que ele já "
        "documentou ou estudou — 'para que serve o Docker', 'quando eu devo "
        "usar Redis'."
    ),
    parametros={
        "type": "object",
        "properties": {
            "nome": {
                "type": "string",
                "description": "Nome da ferramenta ou tecnologia, como foi mencionada.",
            }
        },
        "required": ["nome"],
    },
)
def acervo_consultar_ficha(nome: str) -> str:
    try:
        candidatos = get("/glossario/entidades", q=nome, limite=1)
    except AcervoIndisponivel as erro:
        return str(erro)

    if not candidatos:
        return f"'{nome}' não está no acervo."

    entidade = candidatos[0]
    if entidade["cobertura"] == "vazio":
        return f"'{entidade['nome']}' está cadastrado no acervo, mas sem nenhuma menção ainda."

    try:
        ficha = get(f"/glossario/entidades/{entidade['slug']}/ficha")
    except AcervoIndisponivel as erro:
        return str(erro)

    partes = [
        ficha.get("resumo_uma_frase"),
        ficha.get("para_que_serve"),
        ficha.get("quando_usar"),
    ]
    partes = [p for p in partes if p]
    if not partes:
        return f"'{entidade['nome']}' está no acervo, mas a ficha ainda não foi escrita."
    return " ".join(partes)
