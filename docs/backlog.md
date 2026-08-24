# Backlog — decisões adiadas e dívidas técnicas

> Mesmo formato do backlog do acervo: por severidade, cada item datado, riscado
> quando resolvido — sem apagar o histórico, só marcar que fechou.

---

## 🔴 Alta — atrapalha o uso ou pode enganar o usuário

### Ramo `Se` do atalho não montado pra todas as ações do celular

`app/ferramentas/celular.py` lista seis ações em `ACOES` (lanterna ligar e
desligar, Não Perturbe ligar e desligar, música tocar e pausar), mas o
atalho do iPhone só ganhou o bloco `Se` da primeira delas antes de o trabalho
parar — travou num problema de tipo ("file size" em vez de "text" na condição
do Atalhos).

O risco é o pior tipo: pedir "acende a lanterna" numa ação sem ramo faz o
Malais **dizer que fez** e nada acontece. Mentira convincente, pior que erro.
Enquanto não estiver todo montado, ou reduz `ACOES` pras que têm ramo de
verdade, ou aceita esse risco conscientemente.

*Aberto em 24/08/2026.*

### Acervo nunca testado contra servidor real

`acervo_buscar` e `acervo_consultar_ficha` (`app/ferramentas/acervo/`) foram
escritos e testados só contra um servidor falso local, imitando o formato
documentado das respostas do acervo. A VPS ainda não está alcançável pela
tailnet. Zero garantia de que o formato real bate com o que foi assumido —
só o primeiro uso de verdade confirma.

*Aberto em 24/08/2026.*

### Tailscale não instalado no computador do dono

`atualizar.sh` e o acesso por SSH só funcionam de dentro de casa (IP local,
`192.168.x.x`) até o Tailscale entrar no PC também. Sem isso, toda atualização
de código exige estar fisicamente em casa ou usar o celular como cliente SSH.

*Aberto em 15/08/2026.*

---

## 🟡 Média — vai incomodar conforme o Malais crescer

### Cada ferramenta nova encarece toda chamada, sem aviso automático

Toda requisição à Groq manda a `PERSONA` inteira e a descrição de **todas**
as ferramentas, sempre — mesmo pra "que horas são". O free tier caiu de ~100
conversas/dia pra ~80 só com a memória curta entrando; Calendar e WhatsApp vão
cortar mais. Não existe alarme quando a cota se aproxima — só descobre no dia
em que a API recusa.

*Aberto em 18/08/2026.*

### SSH usa senha, não chave

Funciona, e o Tailscale já limita quem alcança a porta 8022 — mas senha é
mais fraco que chave, e a troca foi adiada de propósito no Passo 9 do README
("resolve por enquanto").

*Aberto em 15/08/2026.*

### `MALAIS_TOKEN` vazio desliga a autenticação, sem aviso do servidor

Documentado em vários lugares que token vazio só serve pra teste local, e que
vira obrigatório assim que o Tailscale expõe o endpoint além da Wi-Fi de casa.
Mas isso é só documentação — o servidor não recusa subir, nem avisa no
`/saude`, se estiver rodando com token vazio numa rede que não é só local.

*Aberto em 15/08/2026.*

### `/consultor` do acervo não é voz-compatível hoje

Multi-chamada de LLM, síncrono, com custo e fila de revisão — desenhado pra
alguém sentado numa tela olhando `dry_run`, não pra pergunta solta. Se um dia
o acervo tornar essa rota assíncrona (job + callback), caberia desenhar um
padrão tipo "beleza, vou analisar seu projeto, te aviso" no Malais — mas isso
é decisão dos dois lados, não escrita ainda.

*Aberto em 24/08/2026. Depende de mudança no acervo, fora do escopo deste
repositório — ver a análise em conversa, não repetida aqui.*

### `ACERVO_TIMEOUT=4` é palpite, não medição

Escolhido por ficar dentro do orçamento de 5s somado ao ~1s que a Groq já
gasta — mas nunca foi medido contra o acervo de verdade, porque a VPS ainda
não está de pé. Vale revisitar (pra cima ou pra baixo) depois do primeiro uso
real.

*Aberto em 24/08/2026.*

---

## 🟢 Baixa — melhoria de conforto

### README ainda abre com o texto original da Fase 1

A primeira seção do `README.md` ("Nesta fase ele já: entende linguagem
natural, sabe que dia e hora são, salva e lista anotações...") é do dia 1 do
projeto e não reflete lembretes, memória curta, atalho do iPhone, estado do
servidor nem acervo. Cosmético — não atrapalha ninguém seguindo o passo a
passo — mas vale reescrever numa passada de limpeza geral.

*Aberto em 24/08/2026.*

### `testar.py` foi escrito, testado e revertido

Existiu por um commit inteiro (`3f3b229`) como alternativa ao `curl` — token e
porta lidos do `.env`, sem aspas pra escapar. O dono preferiu seguir com
`curl`/CMD direto e pediu pra reverter (`e99844c`). Registrado aqui pra
ninguém reconstruir sem saber que já existiu e foi descartado por escolha, não
por não funcionar.

*Fechado por decisão em 14/08/2026 — não é bug, é preferência registrada.*

---

## Resolvidos

### ~~`llama-3.3-70b-versatile` desligado pela Groq~~

A Groq anunciou deprecação com prazo curto. Trocado pro `gpt-oss-120b` antes
do desligamento, com `ESFORCO_RACIOCINIO=low` pra não estourar o orçamento de
latência.

*Aberto em 13/08/2026 · Resolvido em 14/08/2026.*

### ~~Modelo trocado sem forma fácil de conferir o que está valendo~~

O `.env` ganha do padrão do `config.py`, então "o que eu acho que está
rodando" podia divergir do real sem aviso nenhum.

*Aberto em 14/08/2026 · Resolvido em 16/08/2026 — `/saude` passou a expor
`"modelo"`.*

### ~~`google-auth` achado que era Python puro~~

Uma versão anterior do `CLAUDE.md` afirmava isso sem medir. Não é: arrasta
`cryptography` (Rust) e `cffi` (C), obrigatórios. Corrigido depois de medir a
árvore de verdade; o caminho pro Calendar vira httpx direto na API REST.

*Aberto (como erro de documentação) antes de 15/08/2026 · Corrigido em
15/08/2026.*

### ~~Raiz do servidor devolvia 404~~

Abrir o endereço no navegador — a primeira coisa que qualquer um faz —
devolvia "404 Not Found", que parece servidor fora do ar quando é o
contrário: só quem está de pé responde 404. Já mandou uma investigação de
boot inteira pro lado errado.

*Aberto (implícito desde o início) · Resolvido em 17/08/2026 — `GET /`
responde status.*

### ~~Colisão de nome "nota" entre Malais e acervo~~

O acervo também usa "nota", com sentido oposto (conhecimento permanente
conectado a grafo, contra lembrete leve e descartável). Renomeado
`notas`→`lembretes` no banco e nas cinco ferramentas, com migração testada
contra um banco no formato exato do que já rodava no aparelho — sem perder a
nota real que já existia lá.

*Aberto em 24/08/2026 · Resolvido no mesmo dia.*

### ~~Caminho do rootfs do proot desatualizado no README~~

O `proot-distro` mudou de layout (`containers/<nome>/rootfs/` em vez de
`installed-rootfs/<nome>/`) e o README mandava o caminho antigo, sem dizer
por quê "No such file or directory".

*Aberto em 17/08/2026 · Resolvido no mesmo dia — README mostra os dois
formatos e um `find` de saída.*
