# PRD - Agente de Dados com Bot Telegram

## Contexto

Sistema completo de inteligência de dados para e-commerce via Telegram com 3 capacidades:

1. **Chat livre** — responde qualquer pergunta sobre o e-commerce consultando o banco em tempo real via tool use (Claude executa SQL dinamicamente).
2. **Relatório executivo** — gera relatório para 3 diretores (Comercial, CS, Pricing) com insights acionáveis a partir dos Data Marts gold.
3. **Envio automático** — envia relatórios diretamente para o Telegram sem o bot rodando, via API HTTP. Suporta agendamento via cron.

**Banco:** PostgreSQL (Supabase)
**LLM:** Claude (Anthropic API) com tool use para execução de SQL
**Bot:** python-telegram-bot v20+ (https://github.com/python-telegram-bot/python-telegram-bot)
**Referência técnica:** Ler o arquivo `database.md` para schemas completos, colunas, tipos e regras de negócio.

---

## Arquitetura

```
Supabase (PostgreSQL)
    │
    ├── public_gold_sales.vendas_temporais
    ├── public_gold_cs.clientes_segmentacao
    └── public_gold_pricing.precos_competitividade
            │
            ▼
    db.py (conexão SQLAlchemy + executor de queries)
            │
            ▼
    agente.py (lógica de IA + envio direto Telegram)
    │
    ├── chat(pergunta)         → Claude + tool use SQL → resposta
    ├── gerar_relatorio()      → 4 queries fixas → Claude → relatório .md
    └── enviar_telegram(texto) → API HTTP do Telegram → mensagem direta
            │
            ▼
    bot.py (Telegram — modo interativo)
    │
    ├── /start                 → boas-vindas + salva CHAT_ID no .env
    ├── /relatorio             → gera e envia relatório completo
    ├── texto livre            → chat() responde qualquer pergunta
    └── auto-registro         → salva CHAT_ID na primeira interação
```

### Dois modos de operação

| Modo | Comando | Precisa do bot rodando? | Uso |
| ---- | ------- | ----------------------- | --- |
| **Interativo** | `python bot.py` | Sim (polling) | Chat livre + relatório sob demanda |
| **Standalone** | `python agente.py` | Não | Gera relatório + envia via API HTTP do Telegram |

**Stack:**
- Python 3.10+
- anthropic (SDK da Anthropic — tool use)
- sqlalchemy + psycopg2-binary (conexão PostgreSQL)
- pandas + tabulate (formatação de dados)
- python-dotenv (variáveis de ambiente)
- python-telegram-bot v20+ (bot assíncrono)

---

## Variáveis de Ambiente (`.env`)

```
TELEGRAM=token-do-bot-telegram
POSTGRES_URL=postgresql://user:pass@host:5432/dbname
ANTHROPIC_API_KEY=sk-ant-...
CHAT_ID=123456789
```

| Variável | Descrição | Obrigatória | Como obter |
| -------- | --------- | ----------- | ---------- |
| `TELEGRAM` | Token do bot Telegram | Sim | @BotFather no Telegram |
| `POSTGRES_URL` | Connection string completa do PostgreSQL | Sim | Supabase Dashboard |
| `ANTHROPIC_API_KEY` | Chave da API do Claude | Sim | console.anthropic.com |
| `CHAT_ID` | ID do chat para envio automático | Auto-registrado | Salvo automaticamente na primeira interação com o bot |

**Auto-registro do CHAT_ID:** Na primeira vez que um usuário interage com o bot (qualquer mensagem, `/start` ou `/relatorio`), o `bot.py` salva o `chat_id` automaticamente no `.env`. Isso permite que o `agente.py` envie relatórios diretamente sem precisar do bot rodando.

---

## Arquivos do Projeto

| Arquivo | Descrição |
| ------- | --------- |
| `db.py` | Conexão com PostgreSQL via SQLAlchemy. Função `execute_query(sql)` que aceita apenas SELECT/WITH. |
| `agente.py` | Três funções principais: `chat()` (agente com tool use), `gerar_relatorio()` (relatório diário) e `enviar_telegram()` (envio direto via API HTTP). Executável standalone via `python agente.py`. |
| `bot.py` | Bot Telegram com polling. Handlers para `/start`, `/relatorio` e mensagens de texto. Auto-registra o `CHAT_ID` no `.env`. |
| `requirements.txt` | Dependências Python. |
| `.env` | Variáveis de ambiente (não commitado via `.gitignore`). |
| `.gitignore` | Ignora `.env`, `__pycache__/`, `*.pyc` e `relatorio_*.md`. |
| `.llm/database.md` | Catálogo de dados completo dos 3 Data Marts. |

---

## Funcionalidade 1: Chat Livre (qualquer pergunta)

### Fluxo

1. Usuário envia mensagem de texto no Telegram.
2. Bot salva o `chat_id` no `.env` (se ainda não registrado).
3. Bot mostra indicador "digitando...".
4. `agente.py` envia a pergunta ao Claude com o schema do banco como contexto.
5. Claude decide quais queries SQL executar via **tool use** (`executar_sql`).
6. O agente executa cada SQL no banco e retorna os resultados ao Claude.
7. Claude analisa os dados e gera a resposta final em português.
8. Bot envia a resposta no Telegram (com split automático se > 4096 chars).

### Tool Use — Ferramenta `executar_sql`

```json
{
    "name": "executar_sql",
    "description": "Executa query SQL SELECT no banco PostgreSQL do e-commerce.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Query SQL SELECT para executar."
            }
        },
        "required": ["sql"]
    }
}
```

- Limite de 10 iterações de tool use por pergunta (evita loops infinitos).
- Apenas SELECT e WITH são permitidos (validação no `db.py`).
- O Claude recebe o schema completo das 3 tabelas gold como contexto, então sabe quais colunas e tipos usar.

### System Prompt (Chat)

```
Você é um analista de dados de um e-commerce brasileiro.
Responda perguntas usando os dados do banco PostgreSQL.
Use a ferramenta executar_sql para consultar os dados necessários.
Formate valores monetários em R$. Responda em português.
Seja conciso e direto.

[schema das 3 tabelas gold]
```

---

## Funcionalidade 2: Relatório Executivo

### Fluxo

1. Disparo via `/relatorio` no Telegram ou `python agente.py` no terminal.
2. O agente executa as 4 queries pré-definidas nos Data Marts.
3. Os dados são formatados como tabelas Markdown via `DataFrame.to_markdown()`.
4. O prompt é enviado ao Claude com os dados e instruções para gerar o relatório.
5. O relatório é salvo como `relatorio_YYYY-MM-DD.md`.
6. O relatório é enviado no Telegram (via bot ou via API HTTP direta).

### Queries do Relatório

**Query 1 — Resumo de Vendas (últimos 7 dias):**

```sql
SELECT data_venda, dia_semana_nome,
    SUM(receita_total) AS receita,
    SUM(total_vendas) AS vendas,
    SUM(total_clientes_unicos) AS clientes,
    AVG(ticket_medio) AS ticket_medio
FROM public_gold_sales.vendas_temporais
GROUP BY data_venda, dia_semana_nome
ORDER BY data_venda DESC
LIMIT 7
```

**Query 2 — Segmentação de Clientes:**

```sql
SELECT segmento_cliente,
    COUNT(*) AS total_clientes,
    SUM(receita_total) AS receita_total,
    AVG(ticket_medio) AS ticket_medio_avg,
    AVG(total_compras) AS compras_avg
FROM public_gold_cs.clientes_segmentacao
GROUP BY segmento_cliente
ORDER BY receita_total DESC
```

**Query 3 — Alertas de Pricing:**

```sql
SELECT classificacao_preco,
    COUNT(*) AS total_produtos,
    AVG(diferenca_percentual_vs_media) AS dif_media_pct,
    SUM(receita_total) AS receita_impactada
FROM public_gold_pricing.precos_competitividade
GROUP BY classificacao_preco
ORDER BY total_produtos DESC
```

**Query 4 — Produtos Críticos:**

```sql
SELECT nome_produto, categoria, nosso_preco,
    preco_medio_concorrentes,
    diferenca_percentual_vs_media,
    receita_total
FROM public_gold_pricing.precos_competitividade
WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'
ORDER BY diferenca_percentual_vs_media DESC
LIMIT 10
```

### System Prompt (Relatório)

```
Você é um analista de dados senior de um e-commerce.
Sua função é gerar um relatório executivo diário para 3 diretores.
Cada diretor tem necessidades diferentes:

1. Diretor Comercial: receita, vendas, ticket médio e tendências.
2. Diretora de Customer Success: segmentação de clientes, VIPs e riscos.
3. Diretor de Pricing: posicionamento de preço vs concorrência e alertas.

Regras do relatório:
- Seja direto e acionável. Cada insight deve sugerir uma ação.
- Use números reais dos dados fornecidos.
- Formate valores monetários em reais (R$).
- Destaque alertas críticos no início.
- O relatório deve ter no máximo 1 página por diretor.
- Use formato Markdown.
```

### User Prompt (template)

```
Gere o relatório diário com base nos dados abaixo.

## Dados de Vendas (últimos 7 dias)
{dados_vendas.to_markdown()}

## Segmentação de Clientes
{dados_clientes.to_markdown()}

## Posicionamento de Preços
{dados_pricing.to_markdown()}

## Produtos Críticos (mais caros que todos os concorrentes)
{dados_produtos_criticos.to_markdown()}

Gere o relatório com 3 seções:
1. Comercial (para o Diretor Comercial)
2. Customer Success (para a Diretora de CS)
3. Pricing (para o Diretor de Pricing)

Comece com um resumo executivo de 3 linhas antes das seções.
```

---

## Funcionalidade 3: Envio Automático via Telegram

### Envio direto (sem bot rodando)

A função `enviar_telegram()` no `agente.py` usa a API HTTP do Telegram diretamente (via `urllib`), sem precisar do bot rodando. Isso permite envio de relatórios via cron ou qualquer script externo.

```python
from agente import gerar_relatorio, enviar_telegram

relatorio = gerar_relatorio()
enviar_telegram(relatorio)  # usa CHAT_ID do .env
```

### Comportamento do envio

- Usa o `CHAT_ID` do `.env` por padrão (pode ser passado como parâmetro).
- Divide mensagens automaticamente em partes de até 4096 caracteres (limite do Telegram).
- Tenta enviar com `parse_mode=Markdown`; se falhar, reenvia como texto puro.
- Se `CHAT_ID` não estiver configurado, exibe mensagem orientando a rodar o bot primeiro.

### Execução standalone (`python agente.py`)

Ao rodar `python agente.py` diretamente:
1. Gera o relatório completo (consulta banco + Claude API).
2. Imprime o relatório no terminal.
3. Salva como `relatorio_YYYY-MM-DD.md`.
4. Se `CHAT_ID` estiver no `.env`, envia automaticamente para o Telegram.
5. Se `CHAT_ID` não estiver configurado, exibe aviso no terminal.

---

## Funcionalidade 4: Auto-Registro do CHAT_ID

### Fluxo

1. Usuário envia qualquer mensagem para o bot no Telegram (texto, `/start` ou `/relatorio`).
2. O `bot.py` chama `salvar_chat_id(update.message.chat_id)`.
3. A função verifica se o `CHAT_ID` já está no `.env`:
   - Se não existe: adiciona `CHAT_ID=xxx` como nova linha no `.env`.
   - Se existe com valor diferente: atualiza o valor.
   - Se já é o mesmo: não faz nada.
4. Atualiza `os.environ["CHAT_ID"]` em memória.
5. Loga no terminal: `CHAT_ID=xxx salvo no .env`.

### Resultado

Após a primeira interação, o `.env` fica com 4 variáveis:

```
TELEGRAM=token-do-bot
POSTGRES_URL=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...
CHAT_ID=6852371789
```

A partir daí, `python agente.py` envia relatórios automaticamente para o Telegram.

---

## Agendamento Automático

### Opção 1 — Cron (recomendado para produção)

```bash
crontab -e

# Relatório diário às 8h da manhã
0 8 * * * cd /c/Users/11339/Documents/project_engenharia_dbt_supabase/.llm/case-02-telegram && /c/Users/11339/Documents/project_engenharia_dbt_supabase/.venv/Scripts/python agente.py >> /tmp/agente.log 2>&1

# Relatório a cada 6 horas
0 */6 * * * cd /c/Users/11339/Documents/project_engenharia_dbt_supabase/.llm/case-02-telegram && /c/Users/11339/Documents/project_engenharia_dbt_supabase/.venv/Scripts/python agente.py >> /tmp/agente.log 2>&1

# Relatório a cada 2 horas em dias úteis
0 */2 * * 1-5 cd /c/Users/11339/Documents/project_engenharia_dbt_supabase/.llm/case-02-telegram && /c/Users/11339/Documents/project_engenharia_dbt_supabase/.venv/Scripts/python agente.py >> /tmp/agente.log 2>&1
```

O `agente.py` gera o relatório e envia para o `CHAT_ID` do `.env` automaticamente. Não precisa do bot rodando.

### Opção 2 — Bot rodando + /relatorio manual

Manter `python bot.py` rodando e digitar `/relatorio` no Telegram quando quiser.

---

## Exemplo de Saída Esperada (Relatório)

```markdown
# Relatório Diário - E-commerce
Data: 12/03/2026

## Resumo Executivo
- Receita dos últimos 7 dias: R$ 45.230,00 (queda de 8% vs semana anterior)
- 49 clientes VIP respondem por 98% da receita total
- 35 produtos estão mais caros que todos os concorrentes

---

## 1. Comercial

### Tendência de Receita (últimos 7 dias)
| Data | Dia | Receita | Vendas | Ticket Médio |
| ---- | --- | ------- | ------ | ------------ |
| 12/03 | Quarta | R$ 6.120 | 42 | R$ 145,71 |
| 11/03 | Terça | R$ 7.340 | 55 | R$ 133,45 |
| ... | ... | ... | ... | ... |

### Insights
- Terça foi o melhor dia da semana (+19% vs média)
- Ticket médio caiu 5% nos últimos 3 dias
- **Ação sugerida:** Revisar campanhas de quarta e quinta

---

## 2. Customer Success

### Segmentação Atual
| Segmento | Clientes | Receita | Ticket Médio |
| -------- | -------- | ------- | ------------ |
| VIP | 49 | R$ 1.050.000 | R$ 420,00 |
| TOP_TIER | 1 | R$ 5.200 | R$ 310,00 |

### Insights
- 98% dos clientes são VIP (base altamente concentrada)
- **Ação sugerida:** Avaliar threshold de segmentação — praticamente todos são VIP

---

## 3. Pricing

### Posicionamento Geral
| Classificação | Produtos | Receita Impactada |
| ------------- | -------- | ----------------- |
| Mais caro que todos | 35 | R$ 12.000 |
| Acima da média | 92 | R$ 55.000 |
| Abaixo da média | 76 | R$ 35.000 |
| Mais barato que todos | 6 | R$ 8.000 |
| Na média | 6 | R$ 4.000 |

### Insights
- 35 produtos estão mais caros que TODOS os concorrentes
- **Ação sugerida:** Repricing imediato nos 10 produtos com maior diferença percentual
```

---

## Tratamento de Erros

| Cenário | Comportamento |
| ------- | ------------- |
| Banco fora do ar | Retorna mensagem de erro sem chamar a API do Claude |
| API do Claude indisponível | Salva dados brutos formatados em Markdown como fallback |
| Mensagem longa no Telegram | Split automático em partes de até 4096 chars. Fallback para texto puro se Markdown falhar |
| SQL inválido no chat | Apenas SELECT/WITH permitidos (validação no `db.py`). Queries de escrita rejeitadas |
| Loop infinito no tool use | Limite de 10 iterações por pergunta |
| CHAT_ID não configurado | `agente.py` exibe aviso no terminal orientando rodar o bot |
| CHAT_ID duplicado no .env | `salvar_chat_id()` atualiza o valor existente em vez de duplicar |

---

## Logging

Cada etapa gera log com timestamp no terminal:

```
[2026-03-12 08:00:01] Iniciando bot Telegram...
[2026-03-12 08:00:01] Bot rodando! Ctrl+C para parar.
[2026-03-12 08:00:05] CHAT_ID=6852371789 salvo no .env
[2026-03-12 08:00:10] Iniciando geração do relatório...
[2026-03-12 08:00:11] Consultando vendas...
[2026-03-12 08:00:12] Consultando clientes...
[2026-03-12 08:00:12] Consultando pricing...
[2026-03-12 08:00:13] Consultando produtos_criticos...
[2026-03-12 08:00:13] Enviando para Claude API...
[2026-03-12 08:00:38] Relatório salvo em: relatorio_2026-03-12.md
[2026-03-12 08:00:40] Mensagem enviada para chat_id=6852371789
```

---

## Custo

| Operação | Modelo | Custo estimado |
| -------- | ------ | -------------- |
| Relatório diário | `claude-sonnet-4-20250514` | ~$0.01 por execução |
| Chat (pergunta simples) | `claude-sonnet-4-20250514` | ~$0.005 por pergunta |
| Chat (pergunta complexa, múltiplos tool use) | `claude-sonnet-4-20250514` | ~$0.02 por pergunta |

---

## Como Executar

### Setup inicial (uma vez)

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar .env com: TELEGRAM, POSTGRES_URL, ANTHROPIC_API_KEY
```

### Modo interativo (bot)

```bash
python bot.py
```

No Telegram, abrir `@SupDbtTelegrambot` (`t.me/SupDbtTelegrambot`) e enviar `/start`. O `CHAT_ID` é salvo automaticamente.

### Modo standalone (relatório + envio automático)

```bash
python agente.py
```

Gera relatório, salva `.md` e envia para o Telegram (se `CHAT_ID` já registrado).

### Agendamento via cron

```bash
crontab -e

# Diário às 8h:
0 8 * * * cd /c/Users/11339/Documents/project_engenharia_dbt_supabase/.llm/case-02-telegram && /c/Users/11339/Documents/project_engenharia_dbt_supabase/.venv/Scripts/python agente.py >> /tmp/agente.log 2>&1
```