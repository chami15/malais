# Malais — Fase 1

Servidor pessoal rodando num Galaxy S20 FE. Recebe comando em texto, decide o que
fazer, executa e devolve uma resposta pronta pra ser falada.

Nesta fase ele já: entende linguagem natural, sabe que dia e hora são, salva e lista
anotações. Google Calendar, WhatsApp e voz própria entram na Fase 2.

---

## Passo 0 — Preparar o aparelho

Antes de instalar qualquer coisa, no S20 FE:

1. **Ajustes → Bateria → Proteger bateria: ligado.** Limita a carga em 85%. Sem isso
   a bateria incha em uns 6 a 12 meses ligada na tomada.
2. Tira a capinha. Ele vai esquentar.
3. **Ajustes → Tela → Tempo até desligar a tela: 30 segundos.** A tela apagada não
   derruba o servidor, mas ligada cozinha o aparelho à toa.
4. Conecta no Wi-Fi e desativa a economia de dados.

## Passo 1 — Termux

Baixa o **F-Droid** (f-droid.org) e por dentro dele instala:

- **Termux**
- **Termux:Boot** — sobe o servidor sozinho quando o celular reinicia
- **Termux:API** — acesso a bateria, notificação, sensores

> Não instala pela Play Store. Aquela versão está abandonada há anos e trava em
> dependências velhas. É o erro que faz a maioria das pessoas desistir no dia 1.

Abre o Termux e:

```bash
pkg update -y && pkg upgrade -y
pkg install -y proot-distro
proot-distro install ubuntu
```

## Passo 2 — Por que Ubuntu por dentro

Você poderia rodar Python direto no Termux. Não faça isso.

No Termux puro, várias dependências não têm pacote pronto pra Android e o pip tenta
**compilar do zero** — inclusive coisas que precisam de Rust. São horas de build e
falhas obscuras. Dentro do Ubuntu via proot, o pip baixa binário aarch64 pronto e
instala em segundos.

Um comando a mais agora, uma tarde de dor de cabeça a menos.

```bash
proot-distro login ubuntu
```

Daqui pra frente você está dentro do Ubuntu. Sempre que fechar o Termux e voltar,
roda esse login de novo.

## Passo 3 — Instalar o Malais

```bash
apt update && apt install -y python3 python3-pip python3-venv git nano
mkdir -p ~/malais && cd ~/malais
```

Copia os arquivos do projeto pra cá (git clone do seu repositório, ou `nano` em cada
arquivo se for na unha). Depois:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

No `.env`, por enquanto preenche **só o token**. Gera um assim:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

Deixa o `GROQ_API_KEY` vazio de propósito. O servidor entra em **modo eco**: responde
repetindo o que você falou. É assim que você testa o caminho inteiro — Termux, rede,
atalho do iPhone — sem gastar um centavo de API nem debugar duas coisas ao mesmo tempo.

## Passo 4 — Subir

```bash
python run.py
```

Sempre por aqui, nunca `uvicorn app.main:app` na mão. O `run.py` descobre a raiz do
projeto sozinho — então funciona de qualquer diretório, inclusive do shell sem contexto
que o Termux:Boot usa — e é ele que lê a `PORTA` do `.env`. Pra trocar a porta numa
subida só: `PORTA=9000 python run.py`.

Ele já sobe em `0.0.0.0`, que é o que faz o servidor aceitar conexão de fora do aparelho.
Sem isso só o próprio celular enxerga.

Testa no navegador do computador, mesma Wi-Fi:

```
http://IP-DO-CELULAR:8000/saude
```

O IP você pega em Ajustes → Conexões → Wi-Fi → toca na rede.

Deve responder:

```json
{"status":"ok","cerebro":"modo eco","ferramentas":["anotar","data_e_hora","listar_notas"]}
```

**Se isso apareceu, o servidor está de pé.** É o marco da Fase 1.

## Passo 5 — Ligar o cérebro

Cria conta em `console.groq.com` e gera uma API key. **Não precisa de cartão** — o free
tier serve de sobra pra uso pessoal. Cola no `.env`:

```
GROQ_API_KEY=gsk_...
```

O `MODELO` e o `ESFORCO_RACIOCINIO` já vêm certos do `.env.example`, não precisa mexer.

Reinicia o servidor: `Ctrl+C` e `python run.py` de novo. O `.env` é lido uma vez, na
subida — editar com o servidor rodando não muda nada.

### Confere o `/saude` antes do curl

```
http://IP-DO-CELULAR:8000/saude
```

Tem que ter virado `"cerebro":"ligado"`. Se continuar `"modo eco"`, a chave não foi lida
e o problema está no `.env`, não na Groq. Quase sempre é uma destas:

- O arquivo não está na **raiz do projeto**, ao lado do `run.py`. É o único lugar onde
  o `config.py` procura.
- Ele ficou como `.env.example` mesmo, ou virou `.env.txt` — confere com `ls -a`.
- Sobrou espaço em volta do `=`. É `GROQ_API_KEY=gsk_...`, sem espaço.

Fazer essa checagem antes economiza tempo: se você for direto pro `curl` e der erro,
você não sabe se é chave, rede, token ou ferramenta.

### Agora sim, o comando

```bash
curl -X POST http://IP-DO-CELULAR:8000/comando \
  -H "Content-Type: application/json" \
  -H "X-Malais-Token: SEU_TOKEN" \
  -d '{"texto":"anota que preciso comprar café"}'
```

O header `X-Malais-Token` é obrigatório se você preencheu o `MALAIS_TOKEN` no Passo 3.
Sem ele a resposta é `401` — e é fácil confundir isso com "o cérebro não ligou".

Confirma que gravou:

```bash
curl -X POST http://IP-DO-CELULAR:8000/comando \
  -H "Content-Type: application/json" \
  -H "X-Malais-Token: SEU_TOKEN" \
  -d '{"texto":"o que eu anotei?"}'
```

Se ele responder falando do café, o loop inteiro funcionou: o LLM entendeu, escolheu a
ferramenta, ela gravou no SQLite e a resposta voltou pronta pra ser falada. **Esse é o
marco do Passo 5.**

### Testando de um PC com Windows

Os comandos acima são de shell Unix (Linux, macOS, ou o próprio Termux). No Windows eles
falham por três motivos que não têm nada a ver com o Malais:

- No PowerShell, `curl` é apelido de `Invoke-WebRequest`, que não entende `-H` nem `-d`.
- A `\` de quebra de linha é sintaxe Unix. No PowerShell é crase, no CMD é `^`.
- Mesmo chamando `curl.exe` direto, o PowerShell 5.1 remove as aspas duplas ao montar a
  linha de comando. O JSON chega quebrado e o servidor devolve `{"erro":"JSON inválido."}`
  — que parece bug do Malais e não é.

No **PowerShell**, use o cliente nativo:

```powershell
$corpo = @{ texto = "anota que preciso comprar café" } | ConvertTo-Json

Invoke-RestMethod -Uri "http://IP-DO-CELULAR:8000/comando" -Method Post `
  -Headers @{ "X-Malais-Token" = "SEU_TOKEN" } `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($corpo))
```

O `ConvertTo-Json` monta o corpo sem briga de aspas, e o `UTF8.GetBytes` é o que faz o
acento de "café" chegar inteiro. Sem ele o PowerShell manda em Latin-1, o `é` vira um byte
que não é UTF-8 válido e o servidor responde `{"erro":"JSON inválido."}` — mesma mensagem
do problema de aspas acima, causa diferente. Num assistente que fala português isso
apareceria em quase toda frase.

Ou seja, `JSON inválido` no Windows quer dizer uma de duas coisas: aspas comidas pelo
PowerShell, ou acento mandado fora de UTF-8. Se o texto do teste não tem acento, é aspas.

No **CMD**, o `curl.exe` funciona, mas tudo numa linha e com as aspas escapadas:

```
curl -X POST http://IP-DO-CELULAR:8000/comando -H "Content-Type: application/json" -H "X-Malais-Token: SEU_TOKEN" -d "{\"texto\":\"anota que preciso comprar cafe\"}"
```

Sem acento de propósito: no CMD a codificação é briga que não vale a pena num teste.

O `/saude` é GET simples e funciona em qualquer um dos dois — ou direto no navegador.

### Se der erro

| Resposta | O que é |
|---|---|
| `401` do servidor | Falta o header `X-Malais-Token`, ou está diferente do `.env` |
| "Minha chave de API está inválida" | A chave da Groq está errada — regenera no console |
| "Estourei o limite da API" | Bateu o rate limit do free tier. Espera e tenta de novo |
| "A API respondeu erro 400" ou `404` | Quase sempre é **modelo desligado**. Ver abaixo |
| "Não consegui falar com a API" | O celular está sem internet, não é problema de chave |

**Sobre modelo desligado:** a Groq aposenta modelo com prazo, e quando isso acontece o
Malais para de responder num dia em que você não mexeu em nada. Já aconteceu uma vez —
o `llama-3.3-70b-versatile`, que era o padrão do projeto, foi desligado em agosto de 2026.
Se um dia começar a dar erro do nada, confere `console.groq.com/docs/deprecations` antes
de procurar bug no código, e troca o `MODELO` no `.env`. O substituto precisa **suportar
tool calling** — sem isso o Malais vira um chatbot que não executa nada.

### Quanto dá pra usar de graça

O limite que aperta primeiro é o de tokens por dia, que dá umas **100 conversas diárias**.
Sobra pra uso pessoal.

Vale saber por que isso encolhe com o tempo: toda requisição manda a persona e a descrição
de **todas** as ferramentas, sempre. Quando a agenda e o WhatsApp entrarem, cada comando
fica mais caro — inclusive "que horas são". Se um dia o limite apertar, a causa é essa,
não o volume de uso. Os seus números reais estão em `console.groq.com/settings/limits`.

## Passo 6 — Não deixar o Android matar

O Android mata processo em background sem dó. Três travas:

```bash
termux-wake-lock
```

E no sistema: **Ajustes → Apps → Termux → Bateria → Sem restrições.**

Pra subir sozinho no boot, o script precisa ficar em `~/.termux/boot/` — que é do
**Termux**, não do Ubuntu. O Termux:Boot é um app Android e não enxerga nada de dentro
do proot.

Sai do Ubuntu com `exit` (o prompt muda; `whoami` responde `root` dentro do Ubuntu e
algo tipo `u0_a123` no Termux) e escreve o arquivo lá:

```bash
mkdir -p ~/.termux/boot
nano ~/.termux/boot/malais.sh
```

Cola o conteúdo de `boot/malais.sh` deste repositório. São 5 linhas — mais rápido do
que tentar copiar entre os dois sistemas de arquivos. Se quiser mesmo copiar, o projeto
fica em `$PREFIX/var/lib/proot-distro/installed-rootfs/ubuntu/root/malais/`, mas esse
caminho **só existe quando você está no Termux**: rodando de dentro do Ubuntu o
`$PREFIX` até expande, e aí o erro diz que o diretório não existe.

Depois, o passo que não é opcional:

```bash
chmod +x ~/.termux/boot/malais.sh
ls -l ~/.termux/boot/
```

O `ls -l` tem que mostrar `-rwx` no começo. **Script sem bit de execução é ignorado em
silêncio** — sem erro, sem log, nada. É a causa número um de "fiz tudo certo e não subiu".

A causa número dois: **abrir o app Termux:Boot uma vez**. Ele abre numa tela vazia e
parece não fazer nada, mas é isso que autoriza o Android a entregar o evento de boot.

O script grava a saída em `~/malais-boot.log` (no home do Termux). Quando o servidor não
subir depois de um reinício, esse arquivo é o único lugar que diz por quê — ninguém está
olhando a tela na hora do boot.

Reinicia o celular e confere: `/saude` tem que responder sem você abrir nada. **Espera
mais que 30 segundos** antes de concluir que falhou: o boot do Android já é lento, e só
depois dele é que o Termux:Boot dispara, faz login no proot, ativa o venv e sobe o
uvicorn. Passar de um minuto é normal.

## Passo 7 — Tailscale

Enquanto for só Wi-Fi de casa, o IP local resolve. Pra usar na rua, instala o
Tailscale nos dois aparelhos (tem na Play Store e na App Store), loga com a mesma
conta, e o celular ganha um IP fixo `100.x.x.x` que funciona de qualquer lugar.

Sem abrir porta no roteador, sem IP público, sem expor nada pra internet.

Instala antes de montar o atalho do iPhone, não depois: o IP local vem de DHCP e muda
sozinho, o que quebraria o atalho a cada semana. O `100.x.x.x` do Tailscale não muda.

A partir daqui o `MALAIS_TOKEN` é o que protege o endpoint de verdade — a rede deixou
de ser só a sua Wi-Fi. Não roda com token vazio fora de teste local.

O Tailscale usa a API de VPN do iOS, mas é **split tunnel**: só o tráfego pros endereços
`100.x.x.x` entra no túnel. O resto da internet continua saindo direto, mesma rota e
mesma velocidade. Não liga a opção **exit node** — essa sim jogaria tudo pelo túnel, e
você não precisa dela.

## Passo 8 — Atalho do iPhone

Aqui o Malais deixa de ser um `curl` e vira uma coisa que você usa. Não precisa de
código novo: o `/comando` já devolve `{"resposta": "..."}` e o app Atalhos faz o resto.

Antes: pega o IP `100.x.x.x` do S20 FE no app do Tailscale, e o `MALAIS_TOKEN` do `.env`.

No app **Atalhos**, cria um novo com quatro ações nessa ordem:

**1. Ditar Texto** — nas opções, idioma **Português (Brasil)**. No padrão ele tenta
entender seus comandos em inglês.

**2. Obter Conteúdo do URL**

| Campo | Conteúdo |
|---|---|
| URL | `http://100.x.x.x:8000/comando` — **texto puro, sem variável** |
| Método | `POST` |
| Cabeçalhos | `X-Malais-Token` → seu token |
| Corpo da Solicitação | `JSON`, com um campo de chave `texto` e valor = variável **Texto Ditado** |

O erro `couldn't convert from Rich Text to URL` significa que a variável do ditado foi
parar no campo **URL**. O Atalhos encadeia as ações sozinho e enfia a saída da anterior
na entrada da seguinte — apaga a variável do campo URL e digita o endereço na mão. O
texto ditado vai no corpo JSON, não na URL.

**3. Obter Valor do Dicionário** — chave `resposta`.

**4. Falar Texto** — nas opções, idioma **Português (Brasil)**. Sem isso ele lê português
com sotaque americano, porque herda o idioma do sistema.

Vale baixar uma voz melhor em **Ajustes → Acessibilidade → Conteúdo Falado → Vozes →
Português (Brasil)**: a padrão é comprimida e soa robótica, as "Aprimoradas" são bem
melhores. Faça isso antes de considerar o Piper — tem chance de já resolver.

Testa pelo botão de play do próprio app. Ele pede permissão de microfone e de
reconhecimento de fala na primeira vez.

Por último, **Ajustes → Acessibilidade → Toque → Toque nas Costas → Toque Duplo** e
escolhe o atalho (os atalhos ficam no fim da lista, depois das funções do sistema).
Deixa o Toque Triplo livre: o duplo dispara sozinho no bolso de vez em quando, e é bom
ter pra onde mudar.

---

## Como o projeto está montado

```
run.py               Lançador. É por aqui que o servidor sobe, sempre
boot/malais.sh       Script do Termux:Boot
app/
├── main.py          API. Um endpoint que importa: POST /comando
├── cerebro.py       Loop de tool calling. Recebe texto, devolve fala
├── config.py        Tudo que vem do .env
├── banco.py         SQLite: notas + histórico de comandos
└── ferramentas/
    ├── __init__.py  Registro. O decorator @ferramenta faz a mágica
    ├── basico.py    data_e_hora
    └── notas.py     anotar, listar_notas
```

**Adicionar capacidade nova = escrever uma função e decorar.** Nada mais muda:

```python
@ferramenta(
    nome="apagar_luz",
    descricao="Apaga a luz de um cômodo da casa.",
    parametros={
        "type": "object",
        "properties": {"comodo": {"type": "string"}},
        "required": ["comodo"],
    },
)
def apagar_luz(comodo: str) -> str:
    ...
    return f"Luz do {comodo} apagada."
```

O LLM passa a saber que essa ferramenta existe e chama sozinho quando fizer sentido.

Duas decisões que valem entender:

**SQLite, não Postgres.** Menos um serviço rodando no celular, menos uma coisa pra
quebrar. Migra quando o Malais já estiver de pé — a troca fica isolada em `banco.py`.

**Erro de ferramenta vira texto, não exceção.** Se `anotar` falhar, a mensagem de erro
volta pro LLM em vez de derrubar a requisição. Ele lê, entende e tenta outro caminho.
É o que separa um assistente que se recupera de um que morre.

---

## Fase 2

O atalho do iPhone saiu antes do previsto, e virou o Passo 8 acima: não custava código
nenhum e é o que faz o Malais deixar de depender de um PC com `curl`.

O que sobra, sem ordem fixa:

- **Ferramentas que só um servidor seu alcança** — consultar banco interno, ver o que
  está rodando, checar serviço na rede. É o que justifica a arquitetura: conector de
  assistente hospedado roda na nuvem do fornecedor e só enxerga endpoint público.
- **Google Calendar** — OAuth e as ferramentas de agenda.
- **Piper** — só se a voz do iOS não bastar. Provavelmente basta.
- **WhatsApp via Baileys** — com chip separado, porque é API não oficial e tem risco de
  banimento do número.
