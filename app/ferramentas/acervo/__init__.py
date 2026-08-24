"""Ferramentas que consultam o acervo pessoal de conhecimento.

O acervo é outro projeto do dono: servidor separado, numa VPS, na mesma
tailnet. Não é uma ferramenta — é uma integração que só tende a crescer (busca
hoje, ficha hoje, e o que mais o acervo abrir depois). Por isso é subpasta e
não um arquivo só, do mesmo jeito que `app/ferramentas/` inteira existe pra
capacidade nova ser "cria um arquivo", não "edita um arquivo que já cresceu
demais".

`cliente.py` concentra o que é comum a toda rota do acervo: URL base, timeout,
e a tradução de erro de rede em frase — pra cada arquivo novo aqui não
reinventar isso.

A descoberta é local a esta pasta, e roda quando o `_descobrir()` de
`app/ferramentas/` importa este pacote — ele já lista subpasta com
`__init__.py` como um módulo normal, então nada muda lá fora.
"""
import importlib
import pkgutil
from pathlib import Path

_IGNORAR = {"cliente"}  # não é ferramenta, é o que as ferramentas usam


def _descobrir():
    pasta = str(Path(__file__).resolve().parent)
    for modulo in pkgutil.iter_modules([pasta]):
        if not modulo.name.startswith("_") and modulo.name not in _IGNORAR:
            importlib.import_module(f"{__name__}.{modulo.name}")


_descobrir()
