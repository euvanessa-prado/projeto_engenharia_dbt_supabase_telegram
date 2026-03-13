# Feature.md — Case 01: Dashboard Streamlit | E-commerce Analytics

Documento de escopo e features do dashboard Streamlit que consome os Data Marts Gold do Supabase.
Baseado em: `prd.md` (requisitos funcionais) e `database.md` (schemas, colunas e regras de negócio).

---

## Visão Geral

| Item | Detalhe |
|---|---|
| **App** | `case-01-dashboard/app.py` |
| **Stack** | Python 3.10+, Streamlit, psycopg2-binary, pandas, plotly, python-dotenv |
| **Banco** | PostgreSQL (Supabase) |
| **Schemas Gold** | `public_gold_sales`, `public_gold_cs`, `public_gold_pricing` |
| **Usuários** | Diretor Comercial, Diretora de Customer Success, Diretor de Pricing |

---

## Arquivos a Criar

| Arquivo | Descrição |
|---|---|
| `case-01-dashboard/app.py` | App Streamlit completo com as 3 páginas |
| `case-01-dashboard/requirements.txt` | Dependências Python |
| `case-01-dashboard/.env.example` | Template das variáveis de ambiente |

---

## F-01 — Infraestrutura: Conexão e Layout Base

- `st.set_page_config(layout="wide")`
- Leitura de credenciais via `.env`:
  - `SUPABASE_HOST`, `SUPABASE_PORT`, `SUPABASE_DB`, `SUPABASE_USER`, `SUPABASE_PASSWORD`
- Função `get_data(query: str) -> pd.DataFrame` reutilizável via `psycopg2`
- Tratamento de erro de conexão com mensagem amigável
- Sidebar com título "E-commerce Analytics" e navegação entre as 3 páginas via `st.sidebar.radio`:
  - Vendas
  - Clientes
  - Pricing

---

## F-02 — Página: Vendas (Diretor Comercial)

**Tabela:** `public_gold_sales.vendas_temporais`
**Granularidade:** 1 linha por `data_venda` + `hora_venda`

### Filtro
- Seletor de mês (`mes_venda`) no topo da página

### KPIs — `st.columns(4)`

| KPI | Lógica | Formato |
|---|---|---|
| Receita Total | `SUM(receita_total)` | R$ XXX.XXX,XX |
| Total de Vendas | `SUM(total_vendas)` | X.XXX |
| Ticket Médio | Receita Total / Total de Vendas | R$ XXX,XX |
| Clientes Únicos | `SUM(total_clientes_unicos)` ponderado ou `MAX` por dia | XXX |

### Gráficos

| # | Tipo | Eixo X | Eixo Y | Título |
|---|---|---|---|---|
| 1 | `px.line` | `data_venda` | `SUM(receita_total)` agrupado por `data_venda` | "Receita Diária" |
| 2 | `px.bar` | `dia_semana_nome` (ordem: Segunda → Domingo) | `SUM(receita_total)` agrupado por `dia_semana_nome` | "Receita por Dia da Semana" |
| 3 | `px.bar` | `hora_venda` (0–23) | `SUM(total_vendas)` agrupado por `hora_venda` | "Volume de Vendas por Hora" |

---

## F-03 — Página: Clientes (Diretora de Customer Success)

**Tabela:** `public_gold_cs.clientes_segmentacao`
**Granularidade:** 1 linha por cliente

### KPIs — `st.columns(4)`

| KPI | Lógica | Formato |
|---|---|---|
| Total Clientes | `COUNT(*)` | XXX |
| Clientes VIP | `COUNT(*) WHERE segmento_cliente = 'VIP'` | XX |
| Receita VIP | `SUM(receita_total) WHERE segmento_cliente = 'VIP'` | R$ XXX.XXX |
| Ticket Médio Geral | `AVG(ticket_medio)` | R$ XXX,XX |

### Gráficos

| # | Tipo | Dados | Título |
|---|---|---|---|
| 1 | `px.pie` | `COUNT(*) GROUP BY segmento_cliente` — labels: VIP, TOP_TIER, REGULAR | "Distribuição de Clientes por Segmento" |
| 2 | `px.bar` | `SUM(receita_total) GROUP BY segmento_cliente` | "Receita por Segmento" |
| 3 | `px.bar` `orientation='h'` | Top 10 por `ranking_receita` — eixo Y: `nome_cliente`, eixo X: `receita_total` | "Top 10 Clientes" |
| 4 | `px.bar` | `COUNT(*) GROUP BY estado` ordenado DESC | "Clientes por Estado" |

### Tabela Detalhada
- `st.dataframe` com todas as colunas da tabela
- Filtro por segmento via `st.selectbox` (`VIP`, `TOP_TIER`, `REGULAR`)

---

## F-04 — Página: Pricing (Diretor de Pricing)

**Tabela:** `public_gold_pricing.precos_competitividade`
**Granularidade:** 1 linha por produto (somente produtos com dados de concorrentes)

### Filtro
- Seletor de categoria via `st.multiselect` — valores: `Eletrônicos`, `Casa`, `Moda`, `Games`, `Cozinha`, `Beleza`, `Acessórios`

### KPIs — `st.columns(4)`

| KPI | Lógica | Formato |
|---|---|---|
| Total Produtos Monitorados | `COUNT(*)` | XXX |
| Mais Caros que Todos | `COUNT(*) WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'` | XX |
| Mais Baratos que Todos | `COUNT(*) WHERE classificacao_preco = 'MAIS_BARATO_QUE_TODOS'` | XX |
| Diferença Média vs Mercado | `AVG(diferenca_percentual_vs_media)` | +X.X% |

### Gráficos

| # | Tipo | Dados | Título |
|---|---|---|---|
| 1 | `px.pie` | `COUNT(*) GROUP BY classificacao_preco` | "Posicionamento de Preço vs Concorrência" |
| 2 | `px.bar` | `AVG(diferenca_percentual_vs_media) GROUP BY categoria` — verde p/ negativo, vermelho p/ positivo | "Competitividade por Categoria" |
| 3 | `px.scatter` | X: `diferenca_percentual_vs_media`, Y: `quantidade_total`, cor: `classificacao_preco`, tamanho: `receita_total` | "Competitividade x Volume de Vendas" |

### Tabela de Alertas
- `st.dataframe` filtrado por `classificacao_preco = 'MAIS_CARO_QUE_TODOS'`
- Colunas exibidas: `produto_id`, `nome_produto`, `categoria`, `nosso_preco`, `preco_maximo_concorrentes`, `diferenca_percentual_vs_media`
- Título: "Produtos em Alerta (mais caros que todos os concorrentes)"

---

## Requisitos Não Funcionais

- Sem cache agressivo — dados mudam após cada `dbt run`
- Tratar erros de conexão com mensagem amigável
- Números em formato brasileiro (R$ com ponto de milhar e vírgula decimal)
- Cores consistentes entre páginas nos gráficos Plotly

---

## Como Testar

```bash
cd case-01-dashboard
cp .env.example .env
# Editar .env com as credenciais reais do Supabase
pip install -r requirements.txt
streamlit run app.py
```

Dashboard disponível em `http://localhost:8501`.
