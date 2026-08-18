"""Estado do próprio aparelho que roda o Malais.

O servidor é um celular velho numa tomada, sem tela ligada e sem ninguém olhando.
Perguntar "como você está?" e ouvir a resposta é a forma mais barata de saber que
a bateria não está inchando, que o disco não encheu e que ele não está cozinhando.

Tudo aqui sai de arquivo local — nada de rede, nada de dependência nova. Cada
leitura é opcional de propósito: caminho de bateria e de temperatura mudam de
aparelho pra aparelho, e dentro do proot alguns nem existem. O que faltar
simplesmente não entra na frase, em vez de derrubar a ferramenta inteira.
"""
import shutil
import time
from pathlib import Path

from app.banco import conexao
from app.config import config
from app.ferramentas import ferramenta

# Marcado quando o módulo é importado, que é quando o servidor sobe. Não é I/O,
# então não fere a regra de não tocar em nada na importação.
_SUBIU_EM = time.monotonic()

# Módulo em vez de literal dentro da função pra o verificar.py conseguir apontar
# pra uma pasta de mentira e testar a leitura. Este container não tem bateria nem
# sensor térmico, então sem isso a parte mais provável de estar errada no
# aparelho seria a única que nunca roda em teste.
CAMINHO_BATERIA = Path("/sys/class/power_supply")
CAMINHO_TERMICO = Path("/sys/class/thermal")


def _plural(quantidade: int, singular: str, plural: str) -> str:
    """A resposta é falada. "1 anotação(ões)" no ouvido é péssimo."""
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def _duracao(segundos: float) -> str:
    """Escrito pra ser ouvido: "dois dias e três horas", não "2d 3h 14m 22s"."""
    minutos = int(segundos // 60)
    if minutos < 1:
        return "menos de um minuto"
    dias, resto = divmod(minutos, 1440)
    horas, minutos = divmod(resto, 60)
    if dias:
        return f"{_plural(dias, 'dia', 'dias')} e {_plural(horas, 'hora', 'horas')}"
    if horas:
        return f"{_plural(horas, 'hora', 'horas')} e {_plural(minutos, 'minuto', 'minutos')}"
    return _plural(minutos, "minuto", "minutos")


def _bateria() -> str | None:
    """O caminho varia por aparelho — daí o glob em vez de um caminho fixo."""
    for caminho in sorted(CAMINHO_BATERIA.glob("*/capacity")):
        try:
            return f"{int(caminho.read_text().strip())}% de bateria"
        except (OSError, ValueError):
            continue
    return None


def _temperatura() -> str | None:
    """Maior zona térmica plausível.

    O aparelho fica na tomada 24 horas por dia, sem capinha, dentro de casa.
    Temperatura é o número que avisa antes de a bateria inchar.

    Zona zero nem sempre é a CPU e algumas relatam valor absurdo, então pega a
    maior dentro de uma faixa que faz sentido pra um celular.
    """
    graus = []
    for caminho in CAMINHO_TERMICO.glob("thermal_zone*/temp"):
        try:
            valor = int(caminho.read_text().strip()) / 1000  # vem em milésimos
        except (OSError, ValueError):
            continue
        if 10 < valor < 110:
            graus.append(valor)
    if not graus:
        return None
    return f"{max(graus):.0f} graus"


def _disco() -> str | None:
    try:
        uso = shutil.disk_usage(Path(config.BANCO).parent)
    except OSError:
        return None
    return f"{uso.free / 1_000_000_000:.1f} gigabytes livres de disco"


def _memoria() -> str | None:
    try:
        for linha in Path("/proc/meminfo").read_text().splitlines():
            if linha.startswith("MemAvailable:"):
                return f"{int(linha.split()[1]) / 1_000_000:.1f} gigabytes de memória livre"
    except (OSError, ValueError, IndexError):
        pass
    return None


def _ligado_desde() -> str | None:
    """Uptime do Android, diferente do uptime do Malais.

    Os dois juntos contam a história: aparelho de pé há semanas com Malais de pé
    há minutos quer dizer que ele caiu e voltou — que é exatamente o que a gente
    quer descobrir sem precisar ler log.
    """
    try:
        segundos = float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None
    return f"o aparelho está ligado há {_duracao(segundos)}"


def _guardado() -> str | None:
    try:
        with conexao() as con:
            notas = con.execute("SELECT count(*) n FROM notas").fetchone()["n"]
            comandos = con.execute("SELECT count(*) n FROM historico").fetchone()["n"]
    except Exception:
        return None
    return (
        f"{_plural(notas, 'anotação guardada', 'anotações guardadas')} e "
        f"{_plural(comandos, 'comando', 'comandos')} no histórico"
    )


@ferramenta(
    nome="estado_do_servidor",
    descricao=(
        "Diz como está o aparelho que roda o Malais: há quanto tempo está no ar, "
        "bateria, temperatura, disco, memória e quanto já foi guardado. Use quando "
        "perguntarem como você está, se está tudo bem, há quanto tempo está ligado, "
        "quanta bateria resta, se está esquentando, ou se tem espaço. "
        "Responda só o que foi perguntado — não recite a lista inteira."
    ),
)
def estado_do_servidor() -> str:
    partes = [
        f"Malais de pé há {_duracao(time.monotonic() - _SUBIU_EM)}",
        _ligado_desde(),
        _bateria(),
        _temperatura(),
        _disco(),
        _memoria(),
        _guardado(),
    ]
    return ". ".join(p for p in partes if p) + "."
