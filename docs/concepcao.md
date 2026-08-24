# Malais — Concepção

> Status: em desenvolvimento ativo · Fase 1 concluída, Fase 2 em andamento
> Início: 12/08/2026

---

## 1. A dor que originou a ideia

Um Galaxy S20 FE velho, parado numa gaveta, ligado 24 horas por dia porque não
tem mais uso nenhum. A ideia: transformar ele num servidor que executa comando
por voz — anotar, consultar, mandar mensagem — sem precisar abrir aplicativo
nenhum, disparado do iPhone com um Toque nas Costas.

**Não é chatbot. É executor.** A diferença importa porque muda o que se mede
como sucesso: um chatbot é bom quando conversa bem; o Malais é bom quando faz
a coisa e devolve uma frase curta, pronta pra ser ouvida andando na rua.

## 2. Por que self-hosted, e não um assistente hospedado

Essa pergunta foi feita durante o desenvolvimento — literalmente uma síndrome
de impostor, ao notar que "anotar" e "ver agenda" é território que a Siri e
qualquer assistente hospedado já cobrem, com menos manutenção e melhor
integração nativa.

A resposta que ficou, e que decide o resto deste documento:

**Um assistente hospedado roda na nuvem do fornecedor e só alcança o que for
endpoint público.** Conector do Claude, por exemplo, é servidor MCP acessado
a partir da nuvem da Anthropic — não do seu aparelho, não da sua rede. Ele
nunca vai enxergar um banco de dados interno, um serviço rodando na sua rede
local, ou o estado do seu próprio servidor. Pra alcançar isso, você teria que
**expor essas coisas na internet** — exatamente o que Tailscale existe pra
evitar.

O Malais roda dentro da sua rede e alcança o que a sua rede alcança. Essa é a
única vantagem que importa, e ela só se paga se existirem coisas de verdade
pra automatizar que um assistente hospedado não toca: consultar o acervo
pessoal de conhecimento (outro projeto, mesma tailnet), ver estado de serviço
interno, futuramente WhatsApp e agenda com escrita.

**O teste combinado:** usar por uma semana com o que já existe. Se em uma
semana não surgir um "queria que ele fizesse X" que a Siri não faz, a resposta
honesta é que a arquitetura não se pagou pra esse caso de uso — e não tem
problema nenhum em admitir isso. Até agora, tem surgido (acervo, estado do
servidor, ação no aparelho).

## 3. A restrição que decide toda escolha técnica

**Nenhuma dependência com código compilado.** Python 3.14 rodando dentro de
Ubuntu via proot no Termux, em ARM — combinação pra qual o PyPI não publica
wheel pronta de quase nada compilado, e o pip cai pra compilar do zero no
próprio celular. Já custou várias rodadas de retrabalho antes de virar regra
escrita.

Essa restrição está documentada em detalhe no `CLAUDE.md` (tabela de pacotes
descartados, o comando de verificação, o caso específico do `google-auth`) e
o CI cobra ela a cada push. Não repito aqui — é o tipo de regra que só precisa
existir num lugar.

## 4. O orçamento que molda cada ferramenta

**5 segundos.** O usuário está parado esperando o celular falar. Isso não é
detalhe de performance — é restrição de produto: uma ferramenta que responde
em 8 segundos não é uma versão mais lenta do Malais, é um Malais que as
pessoas param de usar.

Medido no aparelho: comando com uma ferramenta e uma ida à Groq responde em
~1 segundo. Isso deixa margem pra ferramentas que fazem uma chamada externa a
mais (acervo, futuramente Calendar) — mas a margem não é infinita, e cada
integração nova precisa medir contra essa linha de base, não assumir que
cabe.

## 5. O que já existe (Fase 1, concluída em 19/08/2026)

- Servidor Starlette + Groq (`gpt-oss-120b`, tool calling), rodando 24/7
- CRUD de lembretes, com identificação de registro por voz (id nunca falado)
- Memória curta (últimas trocas, janela de tempo) — "na verdade era chá"
  funciona
- Ação no aparelho via canal JSON + `Se` no atalho (lanterna, foco, música —
  ver backlog: nem toda ação tem o ramo montado ainda)
- Estado do próprio servidor (bateria, temperatura, disco, uptime) — o
  aparelho "se descreve" por voz
- Boot automático, SSH, deploy com rollback (`atualizar.sh`), CI validando
  cada push
- Atalho do iPhone com ditado + fala + automações (Share Sheet, briefing por
  horário)
- Primeira integração com o acervo (busca e ficha, só leitura)

## 6. O que ainda não existe, e por quê essa ordem

Ver `docs/backlog.md` pros itens concretos e datados. Em linhas gerais, o que
falta cair na Fase 2:

1. **Google Calendar** — o maior valor diário que falta, mas o maior trabalho
   (OAuth, consent no navegador). Caminho já mapeado: httpx direto na API
   REST, sem `google-auth` — ver a restrição técnica acima.
2. **WhatsApp via Baileys** — chip separado, risco de banimento de número.
   Adiado por ser o mais arriscado, não por ser o menos útil.
3. **Piper** — deliberadamente fora da fila. A voz aprimorada do iOS resolveu
   o problema que o Piper resolveria, com zero custo de manutenção. Só volta
   a fazer sentido se alguém quiser voz específica ou áudio gerado pelo
   próprio servidor.

## 7. O que o Malais explicitamente não é

- **Não é um concorrente de assistente hospedado em conhecimento geral.**
  Pergunta solta sobre o mundo, ele responde pior que qualquer LLM comercial
  — não é esse o jogo.
- **Não é multiusuário.** Um dono, um aparelho, uma tailnet. Se isso mudar um
  dia, é reprojeto, não extensão.
- **Não é uma interface de chat.** É comando → execução → frase curta. Uma
  conversa longa não é o caso de uso — é o `MEMORIA_VOLTAS` curto lembrando
  disso de propósito.
