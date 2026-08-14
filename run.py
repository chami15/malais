"""Sobe o Malais.

    python run.py

Existe pra resolver o "No module named app". O comando `uvicorn app.main:app`
procura o pacote no diretório em que você está — se você rodar de ~ ou de dentro
de app/, ele não acha. Este arquivo descobre a própria localização e coloca a
raiz do projeto no path, então funciona de qualquer lugar:

    python ~/malais/run.py
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import uvicorn  # noqa: E402

from app.main import app  # noqa: E402

if __name__ == "__main__":
    porta = int(os.getenv("PORTA", "8000"))
    print(f"Malais subindo em http://0.0.0.0:{porta}  (Ctrl+C pra parar)")
    uvicorn.run(app, host="0.0.0.0", port=porta)
