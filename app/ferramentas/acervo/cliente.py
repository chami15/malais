"""HTTP compartilhado por toda ferramenta que fala com o acervo.

Nada de dependência nova — httpx já está no projeto. O que fica aqui é só o
que se repetiria em cada arquivo: montar a URL, aplicar o timeout, e converter
erro de rede em frase que o LLM sabe usar. Ver as regras de "ferramenta que
fala com API de fora" no CLAUDE.md — timeout explícito e erro previsível
virando frase valem tanto aqui quanto valeram pra Groq.
"""
import httpx

from app.config import config


class AcervoIndisponivel(Exception):
    """Erro previsível: não configurado, fora do ar, ou demorou demais.

    Cada ferramenta do acervo pega esta exceção e devolve `str(erro)` — não
    deixa cair na rede de segurança genérica do `executar()`, que tem prefixo
    de depuração ("Erro ao executar '...'") em vez de frase limpa.
    """


def get(caminho: str, **parametros) -> dict | list:
    """GET no acervo. `caminho` começa com barra, ex.: "/busca"."""
    if not config.tem_acervo:
        raise AcervoIndisponivel(
            "O acervo ainda não está configurado neste servidor."
        )
    try:
        resposta = httpx.get(
            f"{config.ACERVO_BASE_URL}{caminho}",
            params=parametros,
            timeout=config.ACERVO_TIMEOUT,
        )
        resposta.raise_for_status()
    except httpx.TimeoutException:
        raise AcervoIndisponivel("O acervo demorou demais pra responder.") from None
    except httpx.HTTPStatusError as erro:
        codigo = erro.response.status_code
        if codigo == 404:
            raise AcervoIndisponivel("Não encontrei isso no acervo.") from None
        raise AcervoIndisponivel(f"O acervo respondeu erro {codigo}.") from None
    except httpx.RequestError:
        raise AcervoIndisponivel(
            "Não consegui falar com o acervo. Confere se ele está no ar."
        ) from None
    return resposta.json()
