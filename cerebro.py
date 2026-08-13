"""O cérebro: recebe texto, decide quais ferramentas chamar, devolve resposta falada."""
import json

from openai import OpenAI

from app.config import config
from app.ferramentas import ESQUEMAS, executar

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


def _cliente() -> OpenAI:
    return OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)


def pensar(texto: str) -> str:
    # Modo eco: sem chave de API o servidor ainda responde. Isso deixa você
    # validar Termux, Tailscale e o atalho do iPhone antes de plugar o LLM.
    if not config.tem_cerebro:
        return f"Modo eco. Você disse: {texto}"

    cliente = _cliente()
    mensagens = [
        {"role": "system", "content": PERSONA},
        {"role": "user", "content": texto},
    ]

    for _ in range(LIMITE_VOLTAS):
        resposta = cliente.chat.completions.create(
            model=config.MODELO,
            messages=mensagens,
            tools=ESQUEMAS,
            temperature=0.3,
        )
        msg = resposta.choices[0].message

        if not msg.tool_calls:
            return (msg.content or "").strip()

        mensagens.append(msg)
        for chamada in msg.tool_calls:
            argumentos = json.loads(chamada.function.arguments or "{}")
            resultado = executar(chamada.function.name, argumentos)
            mensagens.append({
                "role": "tool",
                "tool_call_id": chamada.id,
                "content": resultado,
            })

    return "Me embananei tentando resolver isso. Tenta de novo?"
