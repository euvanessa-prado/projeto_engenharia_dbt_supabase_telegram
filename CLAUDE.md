# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Comandos Principais

### dbt

```bash
# Dentro de ecommerce/
dbt debug                        # Testa conexão com o banco
dbt run                          # Executa todos os modelos
dbt run --select bronze          # Executa apenas a camada Bronze
dbt run --select silver          # Executa apenas a camada Silver
dbt run --select gold            # Executa apenas a camada Gold
dbt run --select +clientes_segmentacao  # Executa modelo e dependências
dbt test                         # Roda os testes definidos
dbt docs generate && dbt docs serve    # Gera e serve documentação
```

### Dashboard Streamlit

```bash
# Na raiz do projeto, com .venv ativado
.venv\Scripts\activate
pip install -r requirements.txt                              # Apenas na primeira vez

python -m streamlit run .llm\case-01-dashboard\app.py       # Inicia o dashboard
```

Dashboard disponível em `http://localhost:8501`.

### Bot Telegram (Case 02)

```bash
# Dentro de .llm/case-02-telegram/, com .venv ativado
.venv\Scripts\activate
pip install -r .llm\case-02-telegram\requirements.txt       # Apenas na primeira vez

python .llm\case-02-telegram\agente.py                      # Inicia o bot (polling)
```

Configurar `.llm/case-02-telegram/.env` com `TELEGRAM`, `POSTGRES_URL`, `ANTHROPIC_API_KEY`. O `CHAT_ID` é salvo automaticamente na primeira interação com o bot.

Bot disponível em `t.me/SupDbtTelegrambot` (`@SupDbtTelegrambot`).

---

## Arquitetura

### Stack

- **Banco de dados:** PostgreSQL no Supabase
- **Transformação:** dbt Core com arquitetura Medalhão
- **Dashboard:** Streamlit + Plotly (tema Supabase: `#3ECF8E` verde, `#0F0F0F` preto)
- **Agente AI:** Anthropic SDK (`claude-sonnet-4-6`) + python-telegram-bot v20+
- **Conexão Python:** SQLAlchemy + psycopg2, credenciais lidas de `~/.dbt/profiles.yml`

### Estrutura de Camadas dbt

| Camada | Materialização | Schema | Descrição |
|--------|---------------|--------|-----------|
| Bronze | View | `public_bronze` | Espelho das tabelas raw do Supabase |
| Silver | Table | `public_silver` | Dados limpos com lógica de negócio |
| Gold | Table | `public_gold_sales` / `public_gold` | Data Marts analíticos |

### Data Marts Gold

| Modelo | Schema | Descrição |
|--------|--------|-----------|
| `vendas_temporais` | `public_gold_sales` | Performance de vendas por período, hora e dia da semana |
| `clientes_segmentacao` | `public_gold` | Segmentação RFM: VIP, TOP_TIER, REGULAR |
| `precos_competitividade` | `public_gold` | Comparativo de preços vs concorrentes |

### Variáveis de Negócio (`dbt_project.yml`)

```yaml
vars:
  segmentacao_vip_threshold: 10000   # Receita mínima para segmento VIP
  segmentacao_top_tier_threshold: 5000
```

---

## Configuração

### `profiles.yml` (dbt)

Localizado em `~/.dbt/profiles.yml`. É a fonte única de credenciais — o dashboard lê desse arquivo via PyYAML para montar a connection string do SQLAlchemy.

### `.llm/case-01-dashboard/.env`

```
POSTGRES_URL=postgresql://usuario:senha@host:5432/postgres
```

Usado pelo dashboard como fallback. Não commitar — protegido pelo `.gitignore`.

### `.llm/case-02-telegram/.env`

```
TELEGRAM=<token do @SupDbtTelegrambot — obter no @BotFather>
POSTGRES_URL=postgresql://usuario:senha@host:5432/postgres
ANTHROPIC_API_KEY=sk-ant-...
CHAT_ID=123456789
```

`CHAT_ID` é registrado automaticamente pelo `bot.py` na primeira interação. Não commitar — protegido pelo `.gitignore`.

---

## Dashboard (`.llm/case-01-dashboard/app.py`)

### Páginas

- **Vendas** — KPIs de receita, volume, sazonalidade; filtros por ano/mês/categoria/estado
- **Clientes** — Segmentação, ticket médio, ranking de clientes; tabela detalhada com labels
- **Pricing** — Competitividade vs concorrentes, alertas de produtos mais caros que todos

### Convenções do código

- `get_data(sql)` — executa query via SQLAlchemy engine
- `aplicar_labels(df)` — mapeia valores de enum do banco para português legível
- `renomear_colunas(df)` — renomeia colunas snake_case para labels profissionais
- `LABEL_SEGMENTO`, `LABEL_CLASSIFICACAO` — dicionários de mapeamento de enums
- `LABEL_COLUNAS` — dicionário de renomeação de colunas para exibição
- `CORES_SEGMENTO`, `CORES_CLASSIFICACAO` — mapas de cores fixos para Plotly
- Dias da semana: sempre ordenados via `pd.Categorical` (Segunda → Domingo)

---

## Bot Telegram + Agente AI (`.llm/case-02-telegram/`)

### Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `db.py` | Conexão SQLAlchemy. `execute_query(sql)` — apenas SELECT/WITH permitidos |
| `agente.py` | Arquivo único: `chat()`, `gerar_relatorio()`, `enviar_telegram()` + handlers do bot. `python agente.py` inicia o polling |

### Agendamento via cron (Linux/macOS)

```bash
# Caminhos deste projeto
# Projeto : /c/Users/11339/Documents/project_engenharia_dbt_supabase/.llm/case-02-telegram
# Python  : /c/Users/11339/Documents/project_engenharia_dbt_supabase/.venv/Scripts/python

# Relatório diário às 8h
0 8 * * * cd /c/Users/11339/Documents/project_engenharia_dbt_supabase/.llm/case-02-telegram && /c/Users/11339/Documents/project_engenharia_dbt_supabase/.venv/Scripts/python agente.py >> /tmp/agente.log 2>&1

# Relatório a cada 6 horas
0 */6 * * * cd /c/Users/11339/Documents/project_engenharia_dbt_supabase/.llm/case-02-telegram && /c/Users/11339/Documents/project_engenharia_dbt_supabase/.venv/Scripts/python agente.py >> /tmp/agente.log 2>&1

# Relatório a cada 2 horas em dias úteis
0 */2 * * 1-5 cd /c/Users/11339/Documents/project_engenharia_dbt_supabase/.llm/case-02-telegram && /c/Users/11339/Documents/project_engenharia_dbt_supabase/.venv/Scripts/python agente.py >> /tmp/agente.log 2>&1
```

> No Windows usar o **Agendador de Tarefas** em vez de cron.

### Convenções do código

- `execute_query(sql)` — rejeita qualquer SQL que não seja SELECT/WITH
- `chat(pergunta)` — Claude com tool use `executar_sql`, limite de 10 iterações
- `gerar_relatorio()` — 4 queries fixas nos Data Marts → Claude → Markdown
- `enviar_telegram(texto, chat_id)` — API HTTP direta, split automático a cada 4096 chars, fallback para texto puro se Markdown falhar
- `salvar_chat_id(chat_id)` — atualiza `.env` sem duplicar a chave
- Modelo: `claude-sonnet-4-6`
- Relatório salvo como `relatorio_YYYY-MM-DD.md` (ignorado pelo `.gitignore`)
