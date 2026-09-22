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

    # O llama-3.3-70b-versatile foi desligado pela Groq em agosto de 2026.
    # O gpt-oss-120b é o sucessor indicado por eles e tem tool calling nativo,
    # que é do que o cerebro.py depende inteiro.
    MODELO = os.getenv("MODELO", "openai/gpt-oss-120b")

    # O gpt-oss é modelo de raciocínio e o padrão da Groq é "medium" — que gasta
    # segundos pensando até pra responder que horas são. Com 5s de orçamento e o
    # usuário parado esperando o celular falar, "low" é o certo aqui.
    # Vazio não manda o parâmetro: modelo sem raciocínio recusa esse campo.
    ESFORCO_RACIOCINIO = os.getenv("ESFORCO_RACIOCINIO", "low")

    # Banco. Fase 1 é SQLite pra não ter serviço extra rodando no celular.
    # Quando o Malais estabilizar, troca por Postgres.
    BANCO = os.getenv("BANCO", str(RAIZ / "malais.db"))

    FUSO = os.getenv("FUSO", "America/Sao_Paulo")

    # Memória curta: quantas trocas anteriores entram no prompt, e de quanto
    # tempo atrás. Serve pra "na verdade era chá" funcionar depois de "anota que
    # preciso comprar café" — não pra lembrar da semana passada.
    #
    # Os dois limites juntos de propósito: a quantidade segura o custo (cada
    # troca viaja em toda chamada), e os minutos evitam que a conversa da manhã
    # volte à noite. MEMORIA_VOLTAS=0 desliga.
    MEMORIA_VOLTAS = int(os.getenv("MEMORIA_VOLTAS", "3"))
    MEMORIA_MINUTOS = int(os.getenv("MEMORIA_MINUTOS", "30"))

    @property
    def tem_cerebro(self) -> bool:
        return bool(self.GROQ_API_KEY)


config = Config()
