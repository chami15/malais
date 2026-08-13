"""Registro de ferramentas.

Cada ferramenta é uma função Python decorada. O decorator cuida de:
  1. guardar a função pra execução
  2. gerar o schema JSON que o LLM lê pra saber que ela existe

Adicionar capacidade nova no Malais = escrever uma função e decorar.
Nada mais precisa mudar.
"""
from typing import Callable

FUNCOES: dict[str, Callable] = {}
ESQUEMAS: list[dict] = []


def ferramenta(nome: str, descricao: str, parametros: dict | None = None):
    def decorador(fn: Callable):
        FUNCOES[nome] = fn
        ESQUEMAS.append({
            "type": "function",
            "function": {
                "name": nome,
                "description": descricao,
                "parameters": parametros or {"type": "object", "properties": {}},
            },
        })
        return fn
    return decorador


def executar(nome: str, argumentos: dict) -> str:
    fn = FUNCOES.get(nome)
    if not fn:
        return f"Ferramenta '{nome}' não existe."
    try:
        return str(fn(**argumentos))
    except Exception as erro:
        # Devolve o erro pro LLM em vez de estourar — ele consegue se corrigir
        # e tentar outra abordagem em vez de morrer a requisição inteira.
        return f"Erro ao executar '{nome}': {erro}"


# Importa os módulos pra que os decorators rodem e populem o registro.
from app.ferramentas import basico, notas  # noqa: E402,F401
