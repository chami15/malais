"""Ações executadas pelo aparelho que chamou, não pelo servidor.

O S20 FE não alcança o seu iPhone: iOS não deixa servidor nenhum disparar nada.
Mas o atalho lê a resposta antes de falar. Então esta ferramenta não *faz* nada —
ela anexa um recado no JSON, e o `Se` do atalho executa do outro lado.

**Toda ação daqui precisa de um ramo correspondente no atalho.** Acrescentar item
em ACOES sem acrescentar o `Se` faz o Malais dizer que ligou a lanterna enquanto
nada acontece — mentira convincente, que é o pior tipo de bug. Mexeu aqui, mexe lá.
"""
from app.ferramentas import ferramenta, marcar_acao

# O que o atalho sabe executar. A descrição é lida pelo LLM na hora de escolher.
ACOES = {
    "lanterna_ligar": "acender a lanterna",
    "lanterna_desligar": "apagar a lanterna",
    "nao_perturbe_ligar": "ligar o Não Perturbe",
    "nao_perturbe_desligar": "desligar o Não Perturbe",
    "musica_tocar": "tocar música",
    "musica_pausar": "pausar a música",
}


@ferramenta(
    nome="acao_no_celular",
    descricao=(
        "Executa uma ação no celular do usuário. Use quando ele pedir para mexer "
        "no aparelho: "
        + "; ".join(f"'{nome}' para {desc}" for nome, desc in ACOES.items())
        + ". Só existem essas ações — se ele pedir outra coisa do aparelho, diga "
        "que ainda não sabe fazer, em vez de escolher a mais parecida."
    ),
    parametros={
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                # enum trava a escolha do LLM. Sem isso ele inventa nome de ação,
                # o atalho não acha o ramo e nada acontece — sem erro nenhum.
                "enum": list(ACOES),
                "description": "Qual ação o celular deve executar.",
            }
        },
        "required": ["acao"],
    },
)
def acao_no_celular(acao: str) -> str:
    if acao not in ACOES:
        return (
            f"'{acao}' não é uma ação que o celular sabe executar. "
            f"As que existem: {', '.join(ACOES)}."
        )
    marcar_acao(acao)
    # O LLM lê isso e compõe a fala. Deixa claro que ainda não aconteceu, pra ele
    # não prometer mais do que o atalho vai cumprir.
    return f"Pedido de '{ACOES[acao]}' anexado à resposta. Confirme em poucas palavras."
