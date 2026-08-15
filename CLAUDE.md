# Malais

Assistente pessoal self-hosted. Roda num Galaxy S20 FE velho, ligado 24/7 em casa,
dentro de um Ubuntu via proot no Termux. O dono aciona do iPhone, o servidor executa
a ação e devolve uma resposta pronta pra ser **falada em voz alta**.

Não é chatbot. É executor: anotar, consultar agenda, mandar mensagem, responder
pergunta — sem abrir aplicativo nenhum.

---

## A restrição que manda em tudo

**Nenhuma dependência com código compilado.** Só wheels `py3-none-any`.

Python 3.14 + Ubuntu proot + ARM é uma combinação pra qual o PyPI não publica wheel
de praticamente nada compilado. O pip cai pra buildar do zero — o que falha ou demora
meia hora no celular. Isso já custou três rodadas de retrabalho.

Descartados e por quê:

| Pacote | Motivo |
|---|---|
| `openai` | arrasta `jiter` (Rust) |
| `fastapi` | arrasta `pydantic-core` (Rust) |
| `uvicorn[standard]` | arrasta `uvloop`, `httptools`, `watchfiles` |

Por isso o projeto usa **Starlette** (não FastAPI), **httpx puro** (não SDK) e
**`uvicorn` pelado** (nunca `[standard]`).

**Antes de adicionar qualquer dependência:**

```bash
pip download --only-binary :all: -d /tmp/check <pacote>
```

Se algum `.whl` baixado não terminar em `py3-none-any`, procure outra solução.
Vale principalmente pro Google Calendar: `google-auth` e afins são Python puro,
mas confira a árvore inteira antes de commitar.

O CI roda essa mesma checagem a cada push e reprova o commit — mas descobrir antes
de subir é mais barato que descobrir com o build vermelho.

## Antes de commitar

```bash
python verificar.py
```

Checagem de fumaça: ferramentas registradas, migração de banco antigo, CRUD, canal
de ação, e o servidor respondendo. Usa banco temporário e modo eco — não encosta no
seu `malais.db` nem gasta API. É o mesmo script que o CI roda.

Ela existe porque o celular se atualiza puxando a `main`: commit quebrado derruba o
único servidor, possivelmente com você longe dele. **Toda falha que já aconteceu de
verdade deve virar uma checagem aqui** — é assim que o arquivo se paga.

---

## Estado atual — Fase 1 concluída

Servidor de pé no aparelho, `/saude` respondendo na rede local.

```
malais/
├── run.py                    lançador — resolve o próprio path, roda de qualquer lugar
├── verificar.py              checagem de fumaça — roda no CI e vale rodar antes de commitar
├── requirements.txt          4 diretos, 11 com transitivos, todos Python puro
├── .github/workflows/        CI: só wheel py3-none-any + verificar.py a cada push
├── .env.example              contrato das variáveis — mexeu em config.py, atualize aqui
├── README.md                 guia de instalação no aparelho (Termux, proot, boot, Tailscale)
├── boot/malais.sh            script do Termux:Boot, copiado pra ~/.termux/boot/
└── app/
    ├── main.py               Starlette. GET /saude, POST /comando
    ├── cerebro.py            loop de tool calling contra a Groq via httpx
    ├── config.py             tudo vem do .env
    ├── banco.py              SQLite: notas + histórico de comandos
    └── ferramentas/
        ├── __init__.py       registro + descoberta automática de módulos
        ├── basico.py         data_e_hora
        ├── celular.py        acao_no_celular — quem executa é o atalho
        └── notas.py          CRUD: anotar, listar, buscar, atualizar, apagar
```

Subir:

```bash
source venv/bin/activate
python run.py          # PORTA=9000 python run.py pra trocar a porta
```

**`python run.py` é o único jeito de subir. Nunca `uvicorn app.main:app` na mão** — nem
no README, nem no script de boot, nem em documentação nova. O `uvicorn` continua sendo o
servidor, mas deixou de ser o comando, por três motivos:

- `uvicorn app.main:app` só resolve o pacote se o diretório atual for a raiz. O boot roda
  num shell que ninguém controla — é exatamente onde o `No module named app` aparece, e
  onde ninguém está olhando a tela pra ver.
- `PORTA` só é lida pelo `run.py`. Com o comando direto, a porta fica hardcoded em dois
  lugares e eles divergem.
- Ponto de entrada único: o que precisar rodar antes de subir (checar `.env`, warm-up do
  Piper depois) entra ali e passa a valer pra todas as formas de subida.

### Endpoints

- `GET /saude` — status, se o cérebro está ligado, lista de ferramentas. Não gasta API.
- `POST /comando` — `{"texto": "..."}` com header `X-Malais-Token`. Devolve
  `{"resposta": "..."}`, e mais `"acao"` quando alguma ferramenta pediu algo ao aparelho.
  **A chave `acao` só existe quando há ação** — é assim que o `Se` do atalho consegue
  testar só se ela tem valor.

Sem `GROQ_API_KEY` no `.env` o servidor entra em **modo eco**: repete o que recebeu.
Serve pra testar rede, atalho do iPhone e infraestrutura sem gastar API nem debugar
duas coisas ao mesmo tempo. **Preserve esse comportamento.**

Se `MALAIS_TOKEN` estiver vazio, a autenticação é desligada — só em teste local.

---

## Como funciona por dentro

`POST /comando` → `cerebro.pensar(texto)` → loop:

1. Manda `PERSONA` + histórico + `ESQUEMAS` (todas as ferramentas) pra Groq.
2. Se a resposta tem `tool_calls`, executa cada uma via `ferramentas.executar()`
   e devolve o resultado como mensagem `role: "tool"`.
3. Repete até o LLM responder sem chamar ferramenta, no máximo `LIMITE_VOLTAS` (5).

Detalhes que já mordem se forem mexidos sem cuidado:

- **`pensar()` é bloqueante** (HTTP + SQLite). `main.py` chama via `run_in_threadpool`.
  Sem isso o event loop trava e o servidor para de responder enquanto pensa.
- **Erro de HTTP vira frase falada**, não stacktrace: 401, 429 e falha de rede têm
  mensagem própria em `pensar()`.
- **Todo comando é registrado** em `historico` pelo `banco.registrar()`. Esse log é
  a ferramenta principal de debug do comportamento do LLM.

### Modelo

`openai/gpt-oss-120b`, configurável por `MODELO`. O `llama-3.3-70b-versatile` que estava
aqui antes foi desligado pela Groq em agosto de 2026 — vale a lição: **modelo deprecado
quebra o servidor num dia em que ninguém mexeu no código**. Antes de culpar o código
quando a API começar a dar 400 ou 404 do nada, confira
`console.groq.com/docs/deprecations`.

Requisito inegociável ao trocar de modelo: **tem que suportar tool calling**. Sem isso o
`cerebro.py` inteiro deixa de funcionar — o Malais vira um chatbot que não executa nada.

O gpt-oss é modelo de raciocínio. Dois detalhes:

- `ESFORCO_RACIOCINIO` vira `reasoning_effort` no payload, e está em `low` de propósito:
  o padrão da Groq é `medium`, que gasta segundos pensando até pra dizer que horas são.
  O parâmetro só é enviado se estiver preenchido — modelo que não raciocina responde 400.
- O raciocínio vem num campo `reasoning` separado, não misturado no `content`. Por isso
  ler `msg["content"]` continua correto e nada de cadeia de pensamento vaza pra fala.

Medido no aparelho, agosto de 2026, com `ESFORCO_RACIOCINIO=low`: comando com uma
ferramenta (duas idas à Groq) responde em **cerca de 1 segundo**. Nenhum raciocínio
vazou pro texto falado. É a linha de base — quando a agenda entrar e somar uma chamada
HTTP externa dentro do loop, é contra esse número que se compara.

---

## Como adicionar uma capacidade

Cria um arquivo em `app/ferramentas/` e decora a função. Só isso — todo `.py` da
pasta é importado sozinho na subida (`_descobrir()`).

```python
from app.ferramentas import ferramenta


@ferramenta(
    nome="agenda_hoje",
    descricao="Lista os compromissos de hoje. Use quando perguntarem sobre a agenda.",
    parametros={
        "type": "object",
        "properties": {"dia": {"type": "string", "description": "Data em AAAA-MM-DD."}},
        "required": ["dia"],
    },
)
def agenda_hoje(dia: str) -> str:
    return "..."
```

Regras que a base já segue e devem continuar:

- **A `descricao` é prompt, não documentação.** É por ela que o LLM decide chamar a
  ferramenta. Diga *quando* usar, não só o que faz.
- **Ferramenta devolve string**, escrita pra ser lida em voz alta.
- **Erro de ferramenta vira texto de volta pro LLM**, não exceção — ele lê, entende e
  tenta outro caminho. Ver `executar()`.
- **Converta os tipos na entrada.** O LLM manda `"5"` onde você espera `5`
  (ver `listar_notas`).
- **Nome duplicado estoura na subida de propósito.** Não silencie: ferramenta duplicada
  faz o LLM chamar a versão errada, e isso vira bug aleatório em vez de erro claro.

### Identificar um registro por voz

O CRUD das notas resolveu um problema que toda ferramenta de escrita vai reencontrar:
o banco precisa de id, e ninguém fala "apaga a nota número sete" em voz alta.

O padrão adotado: **listar e buscar devolvem o id no texto de retorno**, entre colchetes,
com um aviso na descrição pra o LLM não falar o número. Quem lê aquele retorno é o LLM,
não o usuário — então ele guarda o id, o usuário diz "apaga a do café", e o LLM chama
`apagar_nota` com o id certo. O número vive entre o LLM e o banco.

Duas consequências que devem valer pras próximas ferramentas destrutivas:

- **A descrição manda descobrir o id antes e proíbe inventar.** Sem isso o LLM chuta.
- **Apagar devolve o que foi apagado no texto de confirmação.** Ditado erra; ouvir
  "apaguei a anotação: X" é a única chance de perceber na hora que foi a nota errada.

### Ferramenta que age no aparelho, não no servidor

O servidor não alcança o iPhone: iOS não deixa nada de fora disparar ação no aparelho.
O que existe é o atalho lendo a resposta antes de falar. Então `acao_no_celular` não
executa nada — ela **anexa um recado no JSON** e o `Se` do atalho executa do outro lado.

Como ferramenta só devolve string (que é o que o LLM lê), o recado precisa de outro
caminho. É o canal em `ferramentas/__init__.py`:

- `marcar_acao()` / `acao_marcada()` / `limpar_acao()`, guardados em `threading.local`.
  **Tem que ser por thread**: `pensar()` roda no threadpool do Starlette, e uma variável
  de módulo comum faria duas requisições simultâneas trocarem de ação entre si.
- `cerebro.responder()` limpa o canal, chama `pensar()` e recolhe o que sobrou. Existe
  separado justamente porque ler do event loop — de fora da thread — daria sempre vazio.
- `limpar_acao()` no começo não é zelo: thread do pool é reaproveitada, e sem isso a ação
  de uma requisição vazaria pra próxima que caísse na mesma thread.

**O custo dessa capacidade:** cada ação nova precisa de um ramo `Se` no atalho do iPhone.
Não escala como o `@ferramenta`, que é só criar arquivo. Item em `ACOES` sem ramo no
atalho faz o Malais dizer que acendeu a lanterna enquanto nada acontece — mentira
convincente, pior que erro. Mexeu em `ACOES`, mexe no atalho.

O `enum` no schema existe pelo mesmo motivo: sem ele o LLM inventa nome de ação, o atalho
não acha o ramo, e nada acontece sem erro nenhum.

### Coluna nova em banco que já existe

`CREATE TABLE IF NOT EXISTS` não mexe em tabela existente, então coluna acrescentada
depois entra em quem instalou hoje e **não** entra no aparelho que está de pé há meses —
falha que não aparece em teste e só quebra em produção. Toda coluna nova vai em
`_acrescentar_colunas()` no `banco.py`, que compara com o `PRAGMA table_info` e roda o
`ALTER TABLE` que faltar.

---

## Convenções

- **Código, comentários e commits em português.** Domínio, funções, variáveis, tudo.
- A `PERSONA` em `cerebro.py` define como o Malais fala. A resposta é ouvida, não lida:
  sem markdown, sem emoji, sem bullet, uma ou duas frases.
- **Orçamento de latência: 5 segundos.** O usuário está parado esperando o celular falar.
  Ação lenta deve responder "beleza, fazendo" e executar em background.
- SQLite foi escolha consciente — menos um serviço vivo no celular. Migrar pra Postgres
  só depois que estabilizar, e a troca deve ficar isolada em `banco.py`.
- Fuso vem de `config.FUSO` (`America/Sao_Paulo`). **Não hardcode.**
- Segredo só no `.env`, que está no `.gitignore`. O `.env.example` é o contrato — se
  adicionar variável nova em `config.py`, adiciona lá também.

---

## Próximo passo: Google Calendar

Fase 2, item 1. O que precisa existir:

1. **OAuth** — credenciais de app desktop no Google Cloud Console, consent uma vez,
   refresh token salvo no servidor. Habilitar Google Tasks no mesmo consent: resolve
   lembretes de graça, sem segunda autorização depois.
2. **`app/ferramentas/agenda.py`** — `agenda_consultar` (por período) e `agenda_criar`
   (título, início, fim). Descrições escritas pra decisão do LLM.
3. **Datas relativas.** O LLM não sabe que dia é hoje. A ferramenta `data_e_hora` existe
   justamente pra ele resolver "amanhã" e "sexta que vem" — a descrição dela instrui
   isso, mantenha.
4. Fuso de `config.FUSO`.

Depois disso, na ordem:

- **Piper** rodando local no aparelho — o endpoint passa a devolver áudio em vez de texto.
- **Atalho do iPhone** disparado por Toque nas Costas.
- **WhatsApp** via Baileys, com chip separado (API não oficial, risco de banimento).

**Antes do atalho do iPhone, instalar Tailscale**: o IP local é DHCP e muda, o que
quebraria o atalho toda semana.

---

## Operação no aparelho

O passo a passo completo está no `README.md`. O que importa saber ao mexer no código:

- O Android mata processo em background. Três travas seguram o servidor: `termux-wake-lock`,
  **Ajustes → Apps → Termux → Bateria → Sem restrições**, e o Termux:Boot.
- O boot grava log em `~/malais-boot.log`. Quando o servidor não sobe depois de um
  reinício, é o único lugar que diz por quê.
- Fora da Wi-Fi de casa o acesso é por Tailscale (`100.x.x.x` fixo). Aí o `MALAIS_TOKEN`
  passa a ser a única proteção real do endpoint — nada de token vazio.
