# PRD - Case 1: Dashboard Streamlit

## Contexto

Dashboard para 3 diretores de um e-commerce consumirem os Data Marts gold do banco PostgreSQL (Supabase). Cada diretor tem necessidades distintas. O dashboard deve ser self-service: abrir, selecionar filtros, ver os numeros.

**Banco:** PostgreSQL (Supabase)
**Referencia tecnica:** Ler o arquivo `database.md` para schemas completos, colunas, tipos e regras de negocio.

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
    Streamlit App (app.py)
    ├── Pagina: Vendas
    ├── Pagina: Clientes
    └── Pagina: Pricing
```

**Stack:**
- Python 3.10+
- Streamlit
- psycopg2-binary (conexao PostgreSQL)
- pandas
- plotly (graficos interativos)
- python-dotenv (variaveis de ambiente)

---

## Conexao com o Banco

Usar variaveis de ambiente via `.env`:

```
SUPABASE_HOST=seu-host.supabase.co
SUPABASE_PORT=5432
SUPABASE_DB=postgres
SUPABASE_USER=seu-usuario
SUPABASE_PASSWORD=sua-senha
```

Criar funcao de conexao reutilizavel que leia do `.env` e retorne um `pandas.DataFrame` a partir de uma query SQL.

---

## Estrutura do App

### Sidebar

- Titulo do dashboard: "E-commerce Analytics"
- Navegacao entre as 3 paginas usando `st.sidebar.selectbox` ou `st.sidebar.radio`:
  - Vendas
  - Clientes
  - Pricing

### Pagina 1: Vendas (Diretor Comercial)

**Tabela fonte:** `public_gold_sales.vendas_temporais`

**KPIs no topo (metricas grandes com st.metric):**

| KPI | Calculo | Formato |
| --- | ------- | ------- |
| Receita Total | SUM(receita_total) | R$ XXX.XXX,XX |
| Total de Vendas | SUM(total_vendas) | X.XXX |
| Ticket Medio | Receita Total / Total de Vendas | R$ XXX,XX |
| Clientes Unicos | SUM(total_clientes_unicos) ponderado ou MAX por dia | XXX |

Mostrar os 4 KPIs em uma linha usando `st.columns(4)`.

**Grafico 1 - Receita por Dia (linha):**
- Eixo X: `data_venda`
- Eixo Y: `SUM(receita_total)` agrupado por `data_venda`
- Titulo: "Receita Diaria"
- Usar plotly `px.line`

**Grafico 2 - Receita por Dia da Semana (barras):**
- Eixo X: `dia_semana_nome` (ordem: Segunda, Terca, ..., Domingo)
- Eixo Y: `SUM(receita_total)` agrupado por `dia_semana_nome`
- Titulo: "Receita por Dia da Semana"
- Usar plotly `px.bar`

**Grafico 3 - Vendas por Hora (barras):**
- Eixo X: `hora_venda` (0-23)
- Eixo Y: `SUM(total_vendas)` agrupado por `hora_venda`
- Titulo: "Volume de Vendas por Hora"
- Usar plotly `px.bar`

**Filtro opcional:** Seletor de mes (`mes_venda`) no topo da pagina.

---

### Pagina 2: Clientes (Diretora de Customer Success)

**Tabela fonte:** `public_gold_cs.clientes_segmentacao`

**KPIs no topo (st.metric):**

| KPI | Calculo | Formato |
| --- | ------- | ------- |
| Total Clientes | COUNT(*) | XXX |
| Clientes VIP | COUNT(*) WHERE segmento_cliente = 'VIP' | XX |
| Receita VIP | SUM(receita_total) WHERE segmento_cliente = 'VIP' | R$ XXX.XXX |
| Ticket Medio Geral | AVG(ticket_medio) | R$ XXX,XX |

Mostrar os 4 KPIs em uma linha usando `st.columns(4)`.

**Grafico 1 - Distribuicao por Segmento (pizza ou donut):**
- Valores: COUNT(*) GROUP BY segmento_cliente
- Labels: VIP, TOP_TIER, REGULAR
- Titulo: "Distribuicao de Clientes por Segmento"
- Usar plotly `px.pie`

**Grafico 2 - Receita por Segmento (barras):**
- Eixo X: `segmento_cliente`
- Eixo Y: `SUM(receita_total)` GROUP BY segmento_cliente
- Titulo: "Receita por Segmento"
- Usar plotly `px.bar`

**Grafico 3 - Top 10 Clientes por Receita (barras horizontais):**
- Eixo Y: `nome_cliente` (top 10 por `ranking_receita`)
- Eixo X: `receita_total`
- Titulo: "Top 10 Clientes"
- Usar plotly `px.bar` com `orientation='h'`

**Grafico 4 - Clientes por Estado (barras):**
- Eixo X: `estado`
- Eixo Y: COUNT(*) GROUP BY estado
- Titulo: "Clientes por Estado"
- Ordenar por quantidade DESC
- Usar plotly `px.bar`

**Tabela detalhada:**
- Mostrar `st.dataframe` com todas as colunas da tabela
- Filtro por segmento usando `st.selectbox`

---

### Pagina 3: Pricing (Diretor de Pricing)

**Tabela fonte:** `public_gold_pricing.precos_competitividade`

**KPIs no topo (st.metric):**

| KPI | Calculo | Formato |
| --- | ------- | ------- |
| Total Produtos Monitorados | COUNT(*) | XXX |
| Mais Caros que Todos | COUNT(*) WHERE classificacao = 'MAIS_CARO_QUE_TODOS' | XX |
| Mais Baratos que Todos | COUNT(*) WHERE classificacao = 'MAIS_BARATO_QUE_TODOS' | XX |
| Diferenca Media vs Mercado | AVG(diferenca_percentual_vs_media) | +X.X% |

Mostrar os 4 KPIs em uma linha usando `st.columns(4)`.

**Grafico 1 - Distribuicao por Classificacao (pizza):**
- Valores: COUNT(*) GROUP BY classificacao_preco
- Titulo: "Posicionamento de Preco vs Concorrencia"
- Usar plotly `px.pie`

**Grafico 2 - Diferenca % Media por Categoria (barras):**
- Eixo X: `categoria`
- Eixo Y: `AVG(diferenca_percentual_vs_media)` GROUP BY categoria
- Titulo: "Competitividade por Categoria"
- Colorir: verde para negativo (mais barato), vermelho para positivo (mais caro)
- Usar plotly `px.bar`

**Grafico 3 - Scatter: Preco vs Volume de Vendas:**
- Eixo X: `diferenca_percentual_vs_media`
- Eixo Y: `quantidade_total`
- Cor: `classificacao_preco`
- Tamanho: `receita_total`
- Titulo: "Competitividade x Volume de Vendas"
- Usar plotly `px.scatter`

**Tabela de alertas:**
- Mostrar `st.dataframe` apenas com produtos classificados como `MAIS_CARO_QUE_TODOS`
- Colunas: produto_id, nome_produto, categoria, nosso_preco, preco_maximo_concorrentes, diferenca_percentual_vs_media
- Titulo: "Produtos em Alerta (mais caros que todos os concorrentes)"

**Filtro:** Seletor de categoria usando `st.multiselect`.

---

## Requisitos Nao Funcionais

- **Nao usar cache agressivo**: os dados do gold mudam apos cada `dbt run`
- **Tratar erros de conexao**: mostrar mensagem amigavel se o banco estiver fora
- **Formatar numeros**: usar formato brasileiro (R$ com ponto de milhar e virgula decimal)
- **Layout**: usar `st.set_page_config(layout="wide")` para aproveitar a tela
- **Cores dos graficos**: manter consistencia entre paginas

---

## Arquivos a Gerar

| Arquivo | Descricao |
| ------- | --------- |
| `case-01-dashboard/app.py` | App Streamlit completo com as 3 paginas |
| `case-01-dashboard/requirements.txt` | Dependencias Python |
| `case-01-dashboard/.env.example` | Template das variaveis de ambiente |

---

## Como Testar

```bash
cd case-01-dashboard
cp .env.example .env
# Editar .env com as credenciais reais do Supabase
pip install -r requirements.txt
streamlit run app.py
```

O dashboard deve abrir em `http://localhost:8501` com dados reais do banco.