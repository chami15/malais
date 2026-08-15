#!/data/data/com.termux/files/usr/bin/sh
#
# Puxa a main, reinicia o Malais, e volta atrás se o servidor não subir.
#
#   sh ~/atualizar.sh
#
# Roda no TERMUX, fora do Ubuntu — igual ao malais.sh, e pelo mesmo motivo: é o
# Termux que sabe subir o proot. Copia junto com o boot script:
#
#   cp ~/malais/boot/atualizar.sh ~/atualizar.sh    (caminho de dentro do Ubuntu)
#   chmod +x ~/atualizar.sh
#
# Por que existe: o celular é o único servidor. Commit ruim derruba o Malais, e
# se você estiver longe fica sem nada pra consertar com. Por isso toda subida é
# conferida pelo /saude, e o que não responde volta pro commit anterior sozinho.

set -u

PORTA="${PORTA:-8000}"
SAUDE="http://127.0.0.1:$PORTA/saude"
BOOT="$HOME/.termux/boot/malais.sh"

no_ubuntu() {
    # tail -1 porque o proot-distro às vezes imprime linha própria antes da saída.
    proot-distro login ubuntu -- bash -c "cd ~/malais && $1" 2>&1 | tail -1 | tr -d '\r'
}

servidor_de_pe() {
    curl -s -m 5 "$SAUDE" >/dev/null 2>&1
}

parar_servidor() {
    # O padrão vive dentro deste arquivo, não na linha de comando — por isso o
    # pkill não casa com o shell que o executou. Digitado direto no terminal,
    # esse mesmo comando mataria a sua sessão junto.
    pkill -f "python run.py" 2>/dev/null

    espera=0
    while servidor_de_pe; do
        espera=$((espera + 1))
        if [ "$espera" -gt 15 ]; then
            echo "O servidor antigo não morreu e a porta $PORTA segue ocupada."
            echo "O novo não subiria, então parei antes de piorar."
            exit 1
        fi
        sleep 1
    done
}

subir_servidor() {
    # nohup pra sobreviver ao fim da sessão SSH. O malais.sh já manda a saída
    # dele pro ~/malais-boot.log.
    nohup sh "$BOOT" >/dev/null 2>&1 &

    espera=0
    while [ "$espera" -lt 60 ]; do
        if servidor_de_pe; then
            return 0
        fi
        espera=$((espera + 1))
        sleep 1
    done
    return 1
}

curto() {
    echo "$1" | cut -c1-7
}

# --- puxar ------------------------------------------------------------------

antes=$(no_ubuntu "git rev-parse HEAD")
if [ -z "$antes" ]; then
    echo "Não consegui ler o commit atual. O Ubuntu está instalado e o projeto em ~/malais?"
    exit 1
fi

echo "Agora em $(curto "$antes"). Puxando..."

# --ff-only de propósito: se a main divergiu do que está no aparelho, é melhor
# parar e olhar do que criar merge automático num servidor sem ninguém vendo.
if ! proot-distro login ubuntu -- bash -c "cd ~/malais && git pull --ff-only"; then
    echo "git pull falhou. Nada foi alterado e o servidor não foi tocado."
    exit 1
fi

depois=$(no_ubuntu "git rev-parse HEAD")

if [ "$antes" = "$depois" ]; then
    echo "Já estava atualizado. Não mexi no servidor."
    exit 0
fi

echo "Novidade: $(curto "$antes") -> $(curto "$depois")"

# --- reiniciar --------------------------------------------------------------

echo "Reiniciando..."
parar_servidor

if subir_servidor; then
    echo "De pé em $(curto "$depois")."
    exit 0
fi

# --- volta atrás ------------------------------------------------------------

echo
echo "O servidor não respondeu em 60s. Voltando pro commit anterior."
parar_servidor
no_ubuntu "git reset --hard $antes" >/dev/null

if subir_servidor; then
    echo "Voltou pro $(curto "$antes") e está de pé."
    echo "O commit $(curto "$depois") não sobe. Veja o ~/malais-boot.log."
    exit 1
fi

echo "Não subiu nem no commit anterior. Isso não é o código novo —"
echo "olhe o ~/malais-boot.log, pode ser rede, .env ou o venv."
exit 2
