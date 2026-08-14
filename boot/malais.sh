#!/data/data/com.termux/files/usr/bin/sh
# Sobe o Malais quando o celular liga.
#
# Copie este arquivo pra ~/.termux/boot/malais.sh — no Termux, FORA do Ubuntu —
# e dê chmod +x. O Termux:Boot roda tudo que estiver nessa pasta no boot.
#
#   mkdir -p ~/.termux/boot
#   cp ~/malais/boot/malais.sh ~/.termux/boot/malais.sh
#   chmod +x ~/.termux/boot/malais.sh
#
# Ele não fica em ~/.termux/boot direto porque essa pasta é do Termux, não do
# Ubuntu do proot — o repositório vive lá dentro e não enxerga ela.

# Impede o Android de suspender o processo quando a tela apaga.
termux-wake-lock

# O log é a única forma de saber por que não subiu, já que no boot ninguém
# está olhando a tela.
proot-distro login ubuntu -- bash -c '
  cd ~/malais &&
  source venv/bin/activate &&
  exec python run.py
' >> "$HOME/malais-boot.log" 2>&1
