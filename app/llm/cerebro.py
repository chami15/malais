"""O cérebro: recebe texto, decide quais ferramentas chamar, devolve resposta falada.

Fala com a Groq por HTTP puro, sem o SDK da OpenAI de propósito. O SDK arrasta
o `jiter`, que é compilado em Rust e não tem wheel pronto pra todo ARM — num
celular isso vira compilação de meia hora ou erro seco de instalação.
A API é REST simples. Não precisamos de SDK pra um POST.
"""
import json
from typing import NamedTuple

import httpx

from app.banco import ultimas_trocas
from app.config import config
from app.ferramentas import ESQUEMAS, acao_marcada, executar, limpar_acao

PERSONA = """Você é o Malais, assistente pessoal do Bernardo.

Regras da sua resposta:
- Ela vai ser FALADA em voz alta, não lida. Escreva pra ouvido, não pra tela.
- Direto e curto. Uma ou duas frases na maioria dos casos.
- Nada de markdown, bullet, emoji, link ou formatação. Só texto corrido.
- Nada de "claro!", "com certeza!", "posso ajudar em mais alguma coisa?".
- Números e datas por extenso quando soar melhor falado.
- Se usou uma ferramenta, confirme o que foi feito em poucas palavras.
- Se faltar informação pra executar, pergunte objetivamente o que falta.
"""

LIMITE_VOLTAS = 5  # trava de segurança contra loop infinito de ferramentas
TIMEOUT = 30.0


class Resultado(NamedTuple):
    """O que sai de uma volta completa: a fala, e o que o aparelho deve executar."""

    resposta: str
    acao: str | None = None


def _chamar_llm(mensagens: list[dict]) -> dict:
    corpo = {
        "model": config.MODELO,
        "messages": mensagens,
        "tools": ESQUEMAS,
        "temperature": 0.3,
    }

    # Só vai no payload se estiver configurado: modelo que não raciocina
    # rejeita o campo com 400, e aí o Malais fica mudo sem motivo aparente.
    if config.ESFORCO_RACIOCINIO:
        corpo["reasoning_effort"] = config.ESFORCO_RACIOCINIO

    resposta = httpx.post(
        f"{config.GROQ_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json=corpo,
        timeout=TIMEOUT,
    )
    resposta.raise_for_status()
    return resposta.json()["choices"][0]["message"]


def pensar(texto: str) -> str:
    # Modo eco: sem chave de API o servidor ainda responde. Isso deixa você
    # validar Termux, Tailscale e o atalho do iPhone antes de plugar o LLM.
    if not config.tem_cerebro:
        return f"Modo eco. Você disse: {texto}"

    mensagens = [{"role": "system", "content": PERSONA}]

    # Memória curta. O registrar() só grava depois que esta volta termina, então
    # o comando de agora ainda não está aqui — não tem risco de se repetir.
    for troca in ultimas_trocas(config.MEMORIA_VOLTAS, config.MEMORIA_MINUTOS):
        mensagens.append({"role": "user", "content": troca["comando"]})
        mensagens.append({"role": "assistant", "content": troca["resposta"]})

    mensagens.append({"role": "user", "content": texto})

    try:
        for _ in range(LIMITE_VOLTAS):
            msg = _chamar_llm(mensagens)
            chamadas = msg.get("tool_calls") or []

            if not chamadas:
                return (msg.get("content") or "").strip()

            mensagens.append(msg)
            for chamada in chamadas:
                argumentos = json.loads(chamada["function"].get("arguments") or "{}")
                resultado = executar(chamada["function"]["name"], argumentos)
                mensagens.append({
                    "role": "tool",
                    "tool_call_id": chamada["id"],
                    "content": resultado,
                })

        return "Me embananei tentando resolver isso. Tenta de novo?"

    except httpx.HTTPStatusError as erro:
        codigo = erro.response.status_code
        if codigo == 401:
            return "Minha chave de API está inválida."
        if codigo == 429:
            return "Estourei o limite da API. Espera um pouco."
        return f"A API respondeu erro {codigo}."
    except httpx.RequestError:
        return "Não consegui falar com a API. Confere a internet do servidor."


def responder(texto: str) -> Resultado:
    """Uma volta completa: pensa e recolhe o que alguma ferramenta pediu ao aparelho.

    Existe separado de `pensar()` porque o canal de ação é por thread, e `pensar()`
    roda no threadpool. Lido do lado de fora — do event loop — viria sempre vazio.
    """
    limpar_acao()
    return Resultado(pensar(texto), acao_marcada())