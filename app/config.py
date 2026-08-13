"""Configuração central. Tudo vem do .env — nada hardcoded."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


class Config:
    # Token simples pra ninguém na sua rede chamar o endpoint.
    # Se ficar vazio, a autenticação é desligada (só use assim em teste local).
    TOKEN = os.getenv("MALAIS_TOKEN", "")

    # Cérebro. Sem chave, o servidor entra em modo eco e ainda responde —
    # útil pra validar o atalho do iPhone antes de gastar com API.
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    MODELO = os.getenv("MODELO", "llama-3.3-70b-versatile")

    # Banco. Fase 1 é SQLite pra não ter serviço extra rodando no celular.
    # Quando o Malais estabilizar, troca por Postgres.
    BANCO = os.getenv("BANCO", str(RAIZ / "malais.db"))

    FUSO = os.getenv("FUSO", "America/Sao_Paulo")

    @property
    def tem_cerebro(self) -> bool:
        return bool(self.GROQ_API_KEY)


config = Config()
