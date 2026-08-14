"""Conversa com o Malais pela linha de comando.

    python testar.py anota que preciso comprar café
    python testar.py                 # sem argumento, abre modo conversa

Existe pra você não precisar de curl. Testar o endpoint na mão custa caro:
no PowerShell o `curl` é outro programa e não aceita -H nem -d, no CMD as aspas
do JSON somem, o acento volta como "JSON inválido", e ainda tem que colar o IP
e o token toda vez. Nada disso tem a ver com o servidor, mas todo erro parece
bug do Malais.

Aqui o token e a porta saem do .env sozinhos e não existe aspas pra escapar.

Roda no próprio celular (dentro do Ubuntu, ao lado do servidor) ou de outra
máquina — nesse caso passa o endereço:

    MALAIS_HOST=192.168.0.42 python testar.py que horas são
"""
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import httpx  # noqa: E402

from app.config import config  # noqa: E402

# Padrão é o próprio aparelho: rodando ao lado do servidor, não depende de
# saber o IP nem de a rede estar certa.
HOST = os.getenv("MALAIS_HOST", "127.0.0.1")
BASE = f"http://{HOST}:{config.PORTA}"


def _perguntar(texto: str) -> None:
    cabecalhos = {"Content-Type": "application/json"}
    if config.TOKEN:
        cabecalhos["X-Malais-Token"] = config.TOKEN

    inicio = time.monotonic()
    try:
        resposta = httpx.post(
            f"{BASE}/comando",
            headers=cabecalhos,
            json={"texto": texto},
            timeout=60.0,
        )
    except httpx.ConnectError:
        print(f"Não achei o servidor em {BASE}.")
        print("Ele está rodando? Sobe com: python run.py")
        return
    except httpx.ReadTimeout:
        print("O servidor aceitou a conexão mas não respondeu em 60s.")
        return

    duracao = time.monotonic() - inicio

    if resposta.status_code == 401:
        print("401: token errado. O MALAIS_TOKEN do .env é o mesmo nos dois lados?")
        return
    if resposta.status_code != 200:
        print(f"{resposta.status_code}: {resposta.text}")
        return

    corpo = resposta.json()
    print(corpo.get("resposta") or corpo.get("erro", resposta.text))

    # O orçamento é 5s: o usuário fica parado esperando o celular falar.
    # Melhor ver o estouro agora do que descobrir com o atalho na mão.
    aviso = "  <- passou do orçamento de 5s" if duracao > 5 else ""
    print(f"[{duracao:.1f}s]{aviso}", file=sys.stderr)


def _checar_saude() -> bool:
    """Diz de cara se o cérebro está ligado — separa 'chave errada' de todo o resto."""
    try:
        resposta = httpx.get(f"{BASE}/saude", timeout=10.0)
        resposta.raise_for_status()
    except httpx.HTTPError:
        print(f"Não achei o servidor em {BASE}.")
        print("Ele está rodando? Sobe com: python run.py")
        return False

    dados = resposta.json()
    print(f"Malais em {BASE} — cérebro {dados['cerebro']}")
    if dados["cerebro"] == "modo eco":
        print("Sem GROQ_API_KEY no .env: ele só repete o que você disser.")
    print(f"Ferramentas: {', '.join(dados['ferramentas'])}")
    return True


if __name__ == "__main__":
    # Tudo que vier depois do nome do script é a frase. Sem aspas, sem JSON.
    if len(sys.argv) > 1:
        _perguntar(" ".join(sys.argv[1:]))
        raise SystemExit

    if not _checar_saude():
        raise SystemExit(1)

    print("Escreve e dá Enter. Ctrl+C pra sair.\n")
    while True:
        try:
            texto = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if texto:
            _perguntar(texto)
