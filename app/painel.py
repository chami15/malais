"""Painel web: leitura visual do que o Malais já sabe.

Existe porque nem tudo se resolve bem falado — ver a lista inteira de
lembretes, ou revisar o histórico, é mais rápido de olhar do que de ouvir.
HTML puro, sem framework de front nenhum e sem build: Starlette já sabe
devolver `HTMLResponse`, e uma tag <style> inline resolve o visual inteiro.
Zero dependência nova.

Só leitura por enquanto. Escrever a partir do navegador (apagar lembrete,
por exemplo) fica pra quando o login por cookie já estiver testado na prática
— misturar os dois de uma vez só dificulta saber qual parte quebrou se algo
der errado.

Autenticação por cookie, não por header: reaproveita o mesmo MALAIS_TOKEN que
o `/comando` já usa (o cookie GUARDA o token, comparado direto — não é sessão
nem tem expiração própria). Sem token configurado, o painel fica aberto pra
qualquer um na rede, do mesmo jeito que o `/comando` já fica hoje nesse caso —
mesmo modelo de confiança, não um novo.

O cookie não tem `secure=True` de propósito: o servidor nunca teve HTTPS, e
com `secure` o navegador simplesmente descartaria o cookie sem avisar nada —
login pareceria não funcionar, e a causa não teria relação óbvia com o
sintoma. `httponly=True` continua valendo, e é o que importa contra script
malicioso lendo o cookie.

Não tem proteção contra CSRF. Pra um único usuário atrás de Tailscale
protegido por segredo compartilhado, o token na sessão do navegador já é a
mesma superfície de ataque que o cookie mitigaria — CSRF token seria
complexidade sem reduzir risco real aqui.
"""
import html
import time
from datetime import datetime
from urllib.parse import parse_qsl

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route

from app.banco import conexao
from app.config import config
from app.ferramentas import servidor as ferramentas_servidor

COOKIE = "malais_token"

_ABAS = [
    ("lembretes", "Lembretes"),
    ("historico", "Histórico"),
    ("servidor", "Servidor"),
]

_ESTILO = """
* { box-sizing: border-box; border-radius: 0 !important; }
body {
    margin: 0; padding: 0; background: #000; color: #eee;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
header {
    padding: 18px 12px; text-align: center; border-bottom: 1px solid #333;
    font-size: 1.2rem; font-weight: 600; letter-spacing: 0.02em;
}
nav { display: flex; width: 100%; border-bottom: 1px solid #333; }
nav a {
    flex: 1; text-align: center; padding: 14px 8px; color: #aaa;
    text-decoration: none; border-right: 1px solid #333; font-size: 0.95rem;
}
nav a:last-child { border-right: none; }
nav a.ativa { color: #fff; background: #1a1a1a; font-weight: 600; }
main { width: 100%; }
.linha {
    padding: 14px 12px; border-bottom: 1px solid #222; width: 100%;
}
.linha .texto { font-size: 1rem; white-space: pre-wrap; word-break: break-word; }
.linha .meta { font-size: 0.8rem; color: #888; margin-top: 4px; }
.linha .resposta { font-size: 0.9rem; color: #ccc; margin-top: 6px; }
.vazio { padding: 24px 12px; color: #888; text-align: center; }
form.login {
    max-width: 320px; margin: 60px auto; padding: 0 16px;
    display: flex; flex-direction: column; gap: 12px;
}
form.login input {
    padding: 12px; background: #111; border: 1px solid #333; color: #eee;
    font-size: 1rem;
}
form.login button {
    padding: 12px; background: #eee; color: #000; border: none;
    font-size: 1rem; font-weight: 600; cursor: pointer;
}
.erro { color: #f66; text-align: center; }
"""


def _layout(aba_ativa: str | None, corpo: str) -> str:
    nav = ""
    if aba_ativa:
        nav = "<nav>" + "".join(
            f'<a class="{"ativa" if slug == aba_ativa else ""}" href="/painel/{slug}">{nome}</a>'
            for slug, nome in _ABAS
        ) + "</nav>"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Malais</title>
<style>{_ESTILO}</style>
</head>
<body>
<header>Malais</header>
{nav}
<main>{corpo}</main>
</body>
</html>"""


def _autenticado(request: Request) -> bool:
    # Sem token configurado, o painel fica sem trava — mesma regra do /comando.
    if not config.TOKEN:
        return True
    return request.cookies.get(COOKIE) == config.TOKEN


def _redirecionar_login() -> RedirectResponse:
    return RedirectResponse("/painel/login", status_code=302)


def _formatar_data(bruta: str) -> str:
    """'2026-09-23 14:05:00' -> '23/09 14:05'. Cai pro texto cru se o formato mudar."""
    try:
        return datetime.strptime(bruta, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
    except (ValueError, TypeError):
        return bruta


async def login_form(request: Request) -> HTMLResponse:
    if _autenticado(request):
        return RedirectResponse("/painel", status_code=302)
    erro = "<p class='erro'>Token inválido.</p>" if request.query_params.get("erro") else ""
    corpo = f"""
    <form class="login" method="post" action="/painel/login">
        {erro}
        <input type="password" name="token" placeholder="Token do Malais" autofocus required>
        <button type="submit">Entrar</button>
    </form>
    """
    return HTMLResponse(_layout(None, corpo))


async def login_enviar(request: Request) -> HTMLResponse:
    # request.form() exigiria a dependência python-multipart só pra ler um
    # campo de texto — o formulário nunca manda enctype multipart (não tem
    # upload de arquivo), então application/x-www-form-urlencoded com
    # parse_qsl da própria stdlib resolve sem dependência nova.
    corpo = (await request.body()).decode("utf-8", errors="replace")
    dados = dict(parse_qsl(corpo))
    token = dados.get("token", "")
    if not config.TOKEN or token != config.TOKEN:
        return RedirectResponse("/painel/login?erro=1", status_code=302)
    resposta = RedirectResponse("/painel", status_code=302)
    resposta.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 365)
    return resposta


async def sair(request: Request) -> HTMLResponse:
    resposta = RedirectResponse("/painel/login", status_code=302)
    resposta.delete_cookie(COOKIE)
    return resposta


async def raiz_painel(request: Request) -> HTMLResponse:
    return RedirectResponse("/painel/lembretes", status_code=302)


async def pagina_lembretes(request: Request) -> HTMLResponse:
    if not _autenticado(request):
        return _redirecionar_login()

    with conexao() as con:
        linhas = con.execute(
            "SELECT id, texto, criada_em, atualizada_em FROM lembretes "
            "ORDER BY id DESC LIMIT 200"
        ).fetchall()

    if not linhas:
        corpo = "<div class='vazio'>Nenhum lembrete salvo ainda.</div>"
    else:
        itens = []
        for linha in linhas:
            meta = f"criado {_formatar_data(linha['criada_em'])}"
            if linha["atualizada_em"]:
                meta += f" · editado {_formatar_data(linha['atualizada_em'])}"
            itens.append(
                f"<div class='linha'>"
                f"<div class='texto'>{html.escape(linha['texto'])}</div>"
                f"<div class='meta'>{meta}</div>"
                f"</div>"
            )
        corpo = "".join(itens)

    return HTMLResponse(_layout("lembretes", corpo))


async def pagina_historico(request: Request) -> HTMLResponse:
    if not _autenticado(request):
        return _redirecionar_login()

    with conexao() as con:
        linhas = con.execute(
            "SELECT comando, resposta, criada_em FROM historico ORDER BY id DESC LIMIT 200"
        ).fetchall()

    if not linhas:
        corpo = "<div class='vazio'>Nenhum comando registrado ainda.</div>"
    else:
        itens = []
        for linha in linhas:
            resposta = html.escape(linha["resposta"] or "")
            itens.append(
                f"<div class='linha'>"
                f"<div class='texto'>{html.escape(linha['comando'])}</div>"
                f"<div class='resposta'>{resposta}</div>"
                f"<div class='meta'>{_formatar_data(linha['criada_em'])}</div>"
                f"</div>"
            )
        corpo = "".join(itens)

    return HTMLResponse(_layout("historico", corpo))


async def pagina_servidor(request: Request) -> HTMLResponse:
    if not _autenticado(request):
        return _redirecionar_login()

    linhas_dados = [
        ("Malais de pé há", ferramentas_servidor._duracao(
            time.monotonic() - ferramentas_servidor._SUBIU_EM
        )),
        ("Cérebro", "ligado" if config.tem_cerebro else "modo eco"),
        ("Modelo", config.MODELO),
        ("Aparelho ligado", ferramentas_servidor._ligado_desde()),
        ("Bateria", ferramentas_servidor._bateria()),
        ("Temperatura", ferramentas_servidor._temperatura()),
        ("Disco", ferramentas_servidor._disco()),
        ("Memória", ferramentas_servidor._memoria()),
        ("Guardado", ferramentas_servidor._guardado()),
    ]

    itens = []
    for rotulo, valor in linhas_dados:
        if valor is None:
            continue
        itens.append(
            f"<div class='linha'>"
            f"<div class='meta'>{html.escape(rotulo)}</div>"
            f"<div class='texto'>{html.escape(str(valor))}</div>"
            f"</div>"
        )

    corpo = "".join(itens) + "<div class='vazio'><a href='/painel/sair' style='color:#888'>sair</a></div>"
    return HTMLResponse(_layout("servidor", corpo))


ROTAS = [
    Route("/painel", raiz_painel, methods=["GET"]),
    Route("/painel/login", login_form, methods=["GET"]),
    Route("/painel/login", login_enviar, methods=["POST"]),
    Route("/painel/sair", sair, methods=["GET"]),
    Route("/painel/lembretes", pagina_lembretes, methods=["GET"]),
    Route("/painel/historico", pagina_historico, methods=["GET"]),
    Route("/painel/servidor", pagina_servidor, methods=["GET"]),
]
