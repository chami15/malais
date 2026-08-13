"""Servidor do Malais. Um endpoint que importa: POST /comando.

Starlette em vez de FastAPI de propósito. O FastAPI depende do pydantic, que
depende do pydantic-core — escrito em Rust e sem wheel pronto pra várias
combinações de Python e ARM. Num celular isso trava a instalação.

Starlette é o que roda por baixo do FastAPI de qualquer jeito, e é Python puro.
A gente perde a validação automática de schema e a página /docs. Pra uma API
de um endpoint com um campo só, é troca barata: a validação cabe em três linhas.
"""
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.banco import preparar, registrar
from app.cerebro import pensar
from app.config import config
from app.ferramentas import FUNCOES


async def saude(request: Request) -> JSONResponse:
    """Bate aqui pra saber se o servidor está de pé, sem gastar API."""
    return JSONResponse({
        "status": "ok",
        "cerebro": "ligado" if config.tem_cerebro else "modo eco",
        "ferramentas": sorted(FUNCOES.keys()),
    })


async def comando(request: Request) -> JSONResponse:
    if config.TOKEN and request.headers.get("x-malais-token") != config.TOKEN:
        return JSONResponse({"erro": "Token inválido."}, status_code=401)

    try:
        corpo = await request.json()
    except Exception:
        return JSONResponse({"erro": "JSON inválido."}, status_code=400)

    texto = str(corpo.get("texto") or "").strip()
    if not texto:
        return JSONResponse({"resposta": "Não entendi nada. Repete?"})

    # pensar() é bloqueante (HTTP pra Groq + SQLite). Sem o threadpool ele
    # travaria o event loop e o servidor pararia de responder enquanto pensa.
    resposta = await run_in_threadpool(pensar, texto)
    await run_in_threadpool(registrar, texto, resposta)

    return JSONResponse({"resposta": resposta})


@asynccontextmanager
async def ciclo_de_vida(app: Starlette):
    preparar()  # cria as tabelas se ainda não existirem
    yield


app = Starlette(
    routes=[
        Route("/saude", saude, methods=["GET"]),
        Route("/comando", comando, methods=["POST"]),
    ],
    lifespan=ciclo_de_vida,
)