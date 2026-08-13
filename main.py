"""Servidor do Malais. Um endpoint que importa: POST /comando."""
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.banco import preparar, registrar
from app.cerebro import pensar
from app.config import config
from app.ferramentas import FUNCOES

app = FastAPI(title="Malais", docs_url="/docs")


@app.on_event("startup")
def iniciar():
    preparar()


class Comando(BaseModel):
    texto: str


def _autorizar(token: str | None):
    if config.TOKEN and token != config.TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido.")


@app.get("/saude")
def saude():
    """Bate aqui pra saber se o servidor está de pé, sem gastar API."""
    return {
        "status": "ok",
        "cerebro": "ligado" if config.tem_cerebro else "modo eco",
        "ferramentas": sorted(FUNCOES.keys()),
    }


@app.post("/comando")
def comando(corpo: Comando, x_malais_token: str | None = Header(default=None)):
    _autorizar(x_malais_token)

    texto = corpo.texto.strip()
    if not texto:
        return {"resposta": "Não entendi nada. Repete?"}

    resposta = pensar(texto)
    registrar(texto, resposta)
    return {"resposta": resposta}
