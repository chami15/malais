"""Registro de ferramentas.

Cada ferramenta é uma função Python decorada. O decorator cuida de:
  1. guardar a função pra execução
  2. gerar o schema JSON que o LLM lê pra saber que ela existe

Todo arquivo .py desta pasta é importado sozinho na subida do servidor. Criar
uma capacidade nova é criar um arquivo aqui e decorar a função — nada mais.
Antes os módulos eram listados na mão, e esquecer de listar não dava erro:
a ferramenta simplesmente não existia e o assistente dizia que não sabia fazer.
"""
import importlib
import pkgutil
import threading
from pathlib import Path
from typing import Callable

FUNCOES: dict[str, Callable] = {}
ESQUEMAS: list[dict] = []

# Canal pra ferramenta pedir algo ao aparelho que fez a requisição.
#
# O servidor não alcança o iPhone — não existe push. Mas o atalho lê a resposta
# antes de falar, então dá pra mandar junto um recado que ele executa. Ferramenta
# devolve string (o LLM lê), e string não serve pra isso: precisa de um campo
# separado no JSON. Daí este canal.
#
# É threading.local porque pensar() roda no threadpool do Starlette: com uma
# variável de módulo comum, duas requisições ao mesmo tempo trocariam de ação.
_local = threading.local()


def limpar_acao() -> None:
    """Zera o canal. Thread do pool é reaproveitada — sem isso, a ação de uma
    requisição vazaria pra próxima que caísse na mesma thread."""
    _local.acao = None


def marcar_acao(acao: str) -> None:
    """Ferramenta chama pra pedir que o aparelho execute algo."""
    _local.acao = acao


def acao_marcada() -> str | None:
    return getattr(_local, "acao", None)


def ferramenta(nome: str, descricao: str, parametros: dict | None = None):
    def decorador(fn: Callable):
        if nome in FUNCOES:
            # Dois módulos registrando o mesmo nome deixaria o LLM vendo a
            # ferramenta duplicada e chamando a versão errada. Melhor estourar
            # na subida do que debugar comportamento aleatório depois.
            raise RuntimeError(f"Ferramenta '{nome}' registrada duas vezes.")
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


def _descobrir():
    """Importa todo módulo desta pasta pra que os decorators rodem."""
    pasta = str(Path(__file__).resolve().parent)
    for modulo in pkgutil.iter_modules([pasta]):
        if not modulo.name.startswith("_"):
            importlib.import_module(f"{__name__}.{modulo.name}")


_descobrir()
