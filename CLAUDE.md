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
pip install -r requirements.txt          # Apenas na primeira vez

python -m streamlit run .llm\app.py      # Inicia o dashboard
```

Dashboard disponível em `http://localhost:8501`.

---

## Arquitetura

### Stack

- **Banco de dados:** PostgreSQL no Supabase
- **Transformação:** dbt Core com arquitetura Medalhão
- **Dashboard:** Streamlit + Plotly (tema Supabase: `#3ECF8E` verde, `#0F0F0F` preto)
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
| `vendas_temporais` | `public_gold_sales` | Performance de vendas por período, categoria, estado |
| `vendas_acumuladas_mes` | `public_gold_sales` | Receita acumulada mensal |
| `clientes_segmentacao` | `public_gold` | Segmentação RFM: VIP, Regular, Ocasional |
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

### `.llm/.env`

```
POSTGRES_URL=postgresql://usuario:senha@host:5432/postgres
```

Usado pelo dashboard como fallback. Não commitar — protegido pelo `.gitignore`.

---

## Dashboard (`llm/app.py`)

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
