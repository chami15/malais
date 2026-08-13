"""Ferramentas que não dependem de nada externo. Servem de teste vivo:
se elas funcionam, o loop de tool calling está de pé."""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import config
from app.ferramentas import ferramenta

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


@ferramenta(
    nome="data_e_hora",
    descricao=(
        "Retorna a data e a hora atuais. Use SEMPRE que precisar saber que dia "
        "ou que horas são, inclusive para calcular datas relativas como "
        "'amanhã', 'sexta que vem' ou 'daqui a duas horas'."
    ),
)
def data_e_hora() -> str:
    agora = datetime.now(ZoneInfo(config.FUSO))
    return (
        f"{DIAS[agora.weekday()]}, {agora.strftime('%d/%m/%Y')}, "
        f"{agora.strftime('%H:%M')}"
    )
