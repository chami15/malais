"""Checagem de fumaça do Malais.

    python verificar.py

Roda no GitHub Actions a cada push, e vale rodar na mão antes de commitar.

Não é suíte de teste — é a rede de segurança pro deploy automático. Como o
celular se atualiza sozinho e é o único servidor, commit quebrado derruba o
Malais enquanto ninguém está olhando. O que está aqui é o que já quebrou de
verdade neste projeto:

- ferramenta com nome duplicado, que estoura na subida
- coluna nova que não chega em banco antigo
- tabela renomeada que perde o que já estava salvo
- canal de ação vazando entre requisições
- o servidor simplesmente não subir

Usa banco temporário e modo eco: não encosta no seu malais.db nem gasta API.
"""
import os
import sqlite3
import sys
import tempfile
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

# Tem que vir antes de importar app.config: ele lê o ambiente na importação, e
# o load_dotenv não sobrescreve variável que já existe. Assim a checagem roda
# igual na sua máquina (que tem .env) e no CI (que não tem).
_BANCO = Path(tempfile.mkdtemp()) / "verificar.db"
os.environ["BANCO"] = str(_BANCO)
os.environ["GROQ_API_KEY"] = ""      # modo eco: sem chamar a Groq
os.environ["MALAIS_TOKEN"] = ""      # sem autenticação nesta checagem
os.environ["ACERVO_BASE_URL"] = ""   # acervo "não configurado" nesta checagem

import httpx  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from app.banco import conexao, preparar, registrar, ultimas_trocas  # noqa: E402
from app.cerebro import responder  # noqa: E402
from app.ferramentas import (  # noqa: E402
    FUNCOES,
    acao_marcada,
    executar,
    limpar_acao,
)
from app.main import app  # noqa: E402

FALHAS: list[str] = []


def conferir(condicao, descricao: str) -> None:
    if condicao:
        print(f"  ok   {descricao}")
    else:
        print(f"  FALHOU  {descricao}")
        FALHAS.append(descricao)


def ferramentas_registradas() -> None:
    """Importar app.main já dispara _descobrir(). Nome duplicado estouraria antes daqui."""
    print("ferramentas")
    esperadas = {
        "data_e_hora", "lembrar", "listar_lembretes", "buscar_lembretes",
        "atualizar_lembrete", "apagar_lembrete", "acao_no_celular", "estado_do_servidor",
    }
    faltando = esperadas - set(FUNCOES)
    conferir(not faltando, f"todas registradas (faltou: {faltando or 'nada'})")


def banco_antigo_migra() -> None:
    """Banco criado antes de uma coluna existir, e antes da tabela se chamar
    `lembretes`, tem que chegar são no esquema atual — sem perder o que já
    estava salvo.

    Duas falhas que não aparecem em teste normal: o CREATE TABLE IF NOT EXISTS
    passa e a coluna não entra; e sem o rename explícito, `lembretes` nasceria
    vazia do lado de `notas` cheia — o aparelho continuaria de pé, mas amnésico.
    """
    print("migração de banco antigo")
    antigo = Path(tempfile.mkdtemp()) / "antigo.db"
    con = sqlite3.connect(antigo)
    con.executescript(
        "CREATE TABLE notas (id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT NOT NULL,"
        " criada_em TEXT NOT NULL DEFAULT (datetime('now','localtime')));"
        "CREATE TABLE historico (id INTEGER PRIMARY KEY AUTOINCREMENT, comando TEXT NOT NULL,"
        " resposta TEXT, criada_em TEXT NOT NULL DEFAULT (datetime('now','localtime')));"
    )
    con.execute("INSERT INTO notas (texto) VALUES ('nota que já existia')")
    con.commit()
    con.close()

    from app.config import config
    original, config.BANCO = config.BANCO, str(antigo)
    try:
        preparar()
        with conexao() as c:
            tabelas = {l["name"] for l in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            colunas = {l["name"] for l in c.execute("PRAGMA table_info(lembretes)")}
            sobreviveu = c.execute("SELECT count(*) n FROM lembretes").fetchone()["n"]
    finally:
        config.BANCO = original

    conferir("lembretes" in tabelas, "notas virou lembretes")
    conferir("notas" not in tabelas, "o nome antigo não sobra duplicado")
    conferir("atualizada_em" in colunas, "coluna nova entrou em banco antigo")
    conferir(sobreviveu == 1, "lembrete preexistente sobreviveu ao rename")


def crud_dos_lembretes() -> None:
    print("CRUD dos lembretes")
    preparar()
    executar("lembrar", {"texto": "comprar café na padaria"})

    achou = executar("buscar_lembretes", {"termo": "café"})
    conferir("café" in achou and "[" in achou, "buscar devolve o lembrete com o id")

    with conexao() as c:
        id_lembrete = c.execute("SELECT id FROM lembretes ORDER BY id DESC LIMIT 1").fetchone()["id"]

    # O LLM manda número como string. Já quebrou antes; fica coberto.
    executar("atualizar_lembrete", {"id": str(id_lembrete), "texto": "comprar chá na padaria"})
    conferir("chá" in executar("buscar_lembretes", {"termo": "chá"}), "atualizar troca o texto")

    apagou = executar("apagar_lembrete", {"id": str(id_lembrete)})
    conferir("chá" in apagou, "apagar devolve o texto do que sumiu")
    conferir(
        "não existe" in executar("apagar_lembrete", {"id": "99999"}).lower(),
        "id inexistente vira frase, não exceção",
    )


def memoria_curta() -> None:
    """A memória tem que pegar o que acabou de acontecer e ignorar o resto.

    Os dois limites importam por motivos diferentes: sem o de quantidade o prompt
    cresce sem teto, e sem o de tempo a conversa da manhã volta à noite.
    """
    print("memória curta")
    preparar()
    with conexao() as con:
        con.execute("DELETE FROM historico")
        # Antiga demais: dentro do limite de quantidade, fora do de tempo.
        con.execute(
            "INSERT INTO historico (comando, resposta, criada_em) "
            "VALUES ('conversa de ontem', 'resposta velha', datetime('now','localtime','-2 days'))"
        )
        con.execute(
            "INSERT INTO historico (comando, resposta, criada_em) "
            "VALUES ('sem resposta', '', datetime('now','localtime'))"
        )
    registrar("anota que preciso comprar café", "Lembrete salvo.")
    registrar("que horas são", "São dez horas.")

    trocas = ultimas_trocas(quantidade=3, minutos=30)
    comandos = [t["comando"] for t in trocas]

    conferir("conversa de ontem" not in comandos, "troca fora da janela de tempo fica de fora")
    conferir("sem resposta" not in comandos, "troca sem resposta fica de fora")
    conferir(
        comandos == ["anota que preciso comprar café", "que horas são"],
        f"vem em ordem cronológica (veio {comandos})",
    )
    conferir(
        len(ultimas_trocas(quantidade=1, minutos=30)) == 1,
        "respeita o limite de quantidade",
    )
    conferir(ultimas_trocas(quantidade=0, minutos=30) == [], "quantidade 0 desliga a memória")

    # O que de fato chega no prompt: cada troca vira um par user/assistant antes
    # da fala de agora.
    import app.cerebro as cerebro

    capturado = {}

    def espiar(mensagens):
        capturado["mensagens"] = mensagens
        return {"content": "ok"}

    original, cerebro._chamar_llm = cerebro._chamar_llm, espiar
    tinha_chave, cerebro.config.GROQ_API_KEY = cerebro.config.GROQ_API_KEY, "falsa"
    try:
        cerebro.pensar("na verdade era chá")
    finally:
        cerebro._chamar_llm = original
        cerebro.config.GROQ_API_KEY = tinha_chave

    papeis = [m["role"] for m in capturado["mensagens"]]
    conferir(
        papeis == ["system", "user", "assistant", "user", "assistant", "user"],
        f"histórico entra como pares user/assistant (veio {papeis})",
    )
    conferir(
        capturado["mensagens"][-1]["content"] == "na verdade era chá",
        "a fala de agora é a última mensagem",
    )
    conferir(
        "café" in capturado["mensagens"][1]["content"],
        "o comando anterior chegou no prompt",
    )


def estado_do_servidor() -> None:
    """Bateria e temperatura são lidas de /sys, que não existe neste container.

    Sem apontar pra uma pasta de mentira, a parte mais provável de estar errada
    no aparelho seria justamente a única que nunca roda em teste. E o oposto
    também importa: leitura ausente tem que sumir da frase, não quebrar nada.
    """
    print("estado do servidor")
    import app.ferramentas.servidor as servidor

    preparar()
    conferir("estado_do_servidor" in FUNCOES, "a ferramenta está registrada")

    # Sem bateria nem sensor térmico: a frase sai mesmo assim.
    vazio = Path(tempfile.mkdtemp())
    bat_orig, term_orig = servidor.CAMINHO_BATERIA, servidor.CAMINHO_TERMICO
    servidor.CAMINHO_BATERIA = servidor.CAMINHO_TERMICO = vazio
    try:
        frase = executar("estado_do_servidor", {})
        conferir("Malais de pé há" in frase, "responde mesmo sem bateria nem sensor")
        conferir("bateria" not in frase, "leitura ausente some da frase")
    finally:
        servidor.CAMINHO_BATERIA, servidor.CAMINHO_TERMICO = bat_orig, term_orig

    # Agora com os arquivos que o celular tem.
    falso = Path(tempfile.mkdtemp())
    (falso / "battery").mkdir()
    (falso / "battery" / "capacity").write_text("87\n")
    (falso / "thermal_zone0").mkdir()
    (falso / "thermal_zone0" / "temp").write_text("41200\n")   # milésimos de grau
    (falso / "thermal_zone1").mkdir()
    (falso / "thermal_zone1" / "temp").write_text("999999\n")  # absurdo, ignorar

    servidor.CAMINHO_BATERIA = servidor.CAMINHO_TERMICO = falso
    try:
        conferir(servidor._bateria() == "87% de bateria", "lê a bateria de /sys")
        conferir(servidor._temperatura() == "41 graus", "converte milésimos e descarta absurdo")
    finally:
        servidor.CAMINHO_BATERIA, servidor.CAMINHO_TERMICO = bat_orig, term_orig

    conferir(servidor._duracao(30) == "menos de um minuto", "duração abaixo de um minuto")
    conferir(servidor._duracao(3700) == "1 hora e 1 minuto", "singular sem o (s) no ouvido")
    conferir(servidor._duracao(200000) == "2 dias e 7 horas", "plural em dias e horas")


def acervo() -> None:
    """As ferramentas do acervo não podem tentar rede quando ele não está
    configurado, e todo erro de rede precisa virar frase — nunca exceção
    vazando pro executar() genérico. Nada disto sai da máquina: o `httpx.get`
    do cliente é trocado por um dublê que simula cada situação, do mesmo jeito
    que `memoria_curta()` troca o `_chamar_llm` da Groq.
    """
    print("acervo")
    conferir("acervo_buscar" in FUNCOES, "acervo_buscar está registrado")
    conferir("acervo_consultar_ficha" in FUNCOES, "acervo_consultar_ficha está registrado")

    from app.config import config
    import app.ferramentas.acervo.cliente as cliente

    original_url = config.ACERVO_BASE_URL
    original_get = cliente.httpx.get

    class _RespostaFalsa:
        def __init__(self, status_code, corpo=None):
            self.status_code = status_code
            self._corpo = corpo or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("erro", request=None, response=self)

        def json(self):
            return self._corpo

    try:
        # Sem URL configurada: nem tenta rede. É o estado do servidor até você
        # preencher ACERVO_BASE_URL quando a VPS estiver de pé.
        config.ACERVO_BASE_URL = ""
        conferir(
            "não está configurado" in executar("acervo_buscar", {"termo": "x"}),
            "sem configuração, devolve frase sem tentar rede",
        )

        # Com URL configurada, mas toda chamada de rede simulada.
        config.ACERVO_BASE_URL = "http://acervo.invalido.teste"

        cliente.httpx.get = lambda *a, **k: (_ for _ in ()).throw(httpx.TimeoutException("x"))
        conferir(
            "demorou demais" in executar("acervo_buscar", {"termo": "x"}),
            "timeout vira frase, não exceção",
        )

        cliente.httpx.get = lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("x"))
        conferir(
            "Não consegui falar" in executar("acervo_buscar", {"termo": "x"}),
            "servidor inatingível vira frase",
        )

        cliente.httpx.get = lambda *a, **k: _RespostaFalsa(404)
        conferir(
            "Não encontrei" in executar("acervo_buscar", {"termo": "x"}),
            "404 vira frase específica",
        )

        cliente.httpx.get = lambda *a, **k: _RespostaFalsa(500)
        conferir(
            "erro 500" in executar("acervo_buscar", {"termo": "x"}),
            "erro do servidor vira frase com o código",
        )

        # Caminho feliz: resposta bem formada, incluindo os dois formatos de
        # plural — é fácil esquecer um dos dois ao mexer na frase.
        cliente.httpx.get = lambda *a, **k: _RespostaFalsa(
            200, {"total": 1, "videos": [{"titulo": "Docker do zero"}]}
        )
        conferir(
            "1 ocorrência de" in executar("acervo_buscar", {"termo": "docker"}),
            "singular sem o (s) no ouvido",
        )
        cliente.httpx.get = lambda *a, **k: _RespostaFalsa(
            200, {"total": 3, "videos": [{"titulo": "A"}, {"titulo": "B"}]}
        )
        conferir(
            "3 ocorrências de" in executar("acervo_buscar", {"termo": "docker"}),
            "plural quando é mais de um",
        )
    finally:
        cliente.httpx.get = original_get
        config.ACERVO_BASE_URL = original_url


def canal_de_acao() -> None:
    """A ação não pode vazar entre requisições nem entre threads.

    Thread do pool é reaproveitada: sem limpar, quem pediu 'que horas são' receberia
    a lanterna pedida pela requisição anterior.
    """
    print("canal de ação")
    limpar_acao()
    executar("acao_no_celular", {"acao": "lanterna_ligar"})
    conferir(acao_marcada() == "lanterna_ligar", "ação válida marca o canal")

    limpar_acao()
    executar("acao_no_celular", {"acao": "abrir_geladeira"})
    conferir(acao_marcada() is None, "ação inventada não marca nada")

    vistos = {}

    def trabalhador(nome, acao):
        limpar_acao()
        executar("acao_no_celular", {"acao": acao})
        import time
        time.sleep(0.05)  # dá tempo da outra thread mexer no canal
        vistos[nome] = acao_marcada()

    fios = [
        threading.Thread(target=trabalhador, args=("a", "lanterna_ligar")),
        threading.Thread(target=trabalhador, args=("b", "musica_pausar")),
    ]
    for f in fios:
        f.start()
    for f in fios:
        f.join()
    conferir(
        vistos == {"a": "lanterna_ligar", "b": "musica_pausar"},
        "threads simultâneas não trocam de ação",
    )


def servidor_responde() -> None:
    print("servidor")
    with TestClient(app) as cliente:
        # Abrir a raiz no navegador é a primeira coisa que se faz. 404 ali parece
        # servidor caído e manda a investigação pro lado errado.
        conferir(cliente.get("/").status_code == 200, "a raiz responde em vez de dar 404")

        saude = cliente.get("/saude")
        conferir(saude.status_code == 200, "/saude responde 200")
        conferir(saude.json()["cerebro"] == "modo eco", "sem chave, entra em modo eco")
        conferir(saude.json().get("modelo"), "/saude diz qual modelo está valendo")

        eco = cliente.post("/comando", json={"texto": "oi"})
        conferir("Modo eco" in eco.json()["resposta"], "/comando responde em modo eco")
        conferir("acao" not in eco.json(), "sem ação, a chave 'acao' nem aparece")

        conferir(
            cliente.post("/comando", json={"texto": "  "}).json()["resposta"],
            "texto vazio devolve frase, não erro",
        )
        conferir(
            cliente.post("/comando", content=b"nao sou json").status_code == 400,
            "corpo inválido devolve 400",
        )


def acao_chega_no_json() -> None:
    """A chave 'acao' precisa aparecer no JSON — é o que o 'Se' do atalho lê."""
    print("ação no JSON da resposta")
    import app.cerebro as cerebro

    original = cerebro.pensar
    cerebro.pensar = lambda texto: (
        executar("acao_no_celular", {"acao": "lanterna_ligar"}) and "Acendendo."
        if "lanterna" in texto else "Nada a fazer."
    )
    try:
        com = responder("acende a lanterna")
        sem = responder("bom dia")
    finally:
        cerebro.pensar = original

    conferir(com.acao == "lanterna_ligar", "ferramenta de ação chega em responder()")
    conferir(sem.acao is None, "requisição seguinte não herda a ação da anterior")


if __name__ == "__main__":
    for checagem in (
        ferramentas_registradas,
        banco_antigo_migra,
        crud_dos_lembretes,
        memoria_curta,
        estado_do_servidor,
        acervo,
        canal_de_acao,
        servidor_responde,
        acao_chega_no_json,
    ):
        checagem()

    print()
    if FALHAS:
        print(f"{len(FALHAS)} falha(s): " + "; ".join(FALHAS))
        raise SystemExit(1)
    print("tudo certo.")
