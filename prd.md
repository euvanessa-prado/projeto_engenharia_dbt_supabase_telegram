# PRD - Camada Analitica dbt | Jornada de Dados

## Contexto

Projeto dbt para criar uma camada analitica sobre um banco PostgreSQL de e-commerce.
Arquitetura Medalhao com 3 camadas: Bronze, Silver, Gold.
Banco: PostgreSQL (Supabase). Dialeto SQL: PostgreSQL.

---

## Tabelas Fonte (Raw)

As 4 tabelas fonte estao no schema `public` do PostgreSQL. Sao referenciadas via `{{ source('raw', 'nome_tabela') }}`.

### raw.vendas

Transacoes de venda realizadas.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_venda | int | PK - ID unico da venda |
| data_venda | timestamp | Data e hora da venda |
| id_cliente | int | FK -> clientes.id_cliente |
| id_produto | int | FK -> produtos.id_produto |
| canal_venda | varchar | Canal de venda (ex: ecommerce, loja_fisica) |
| quantidade | int | Quantidade de itens vendidos |
| preco_unitario | numeric | Preco unitario praticado na venda |

### raw.clientes

Cadastro de clientes.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_cliente | int | PK - ID unico do cliente |
| nome_cliente | varchar | Nome completo do cliente |
| estado | varchar | Estado (UF) do cliente |
| pais | varchar | Pais do cliente |
| data_cadastro | timestamp | Data de cadastro |

### raw.produtos

Catalogo de produtos.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_produto | int | PK - ID unico do produto |
| nome_produto | varchar | Nome do produto |
| categoria | varchar | Categoria do produto |
| marca | varchar | Marca do produto |
| preco_atual | numeric | Preco atual de venda |
| data_criacao | timestamp | Data de criacao do produto |

### raw.preco_competidores

Precos coletados de concorrentes para os mesmos produtos.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_produto | int | FK -> produtos.id_produto |
| nome_concorrente | varchar | Nome do concorrente |
| preco_concorrente | numeric | Preco praticado pelo concorrente |
| data_coleta | timestamp | Data e hora da coleta do preco |

---

## Arquitetura

```
models/
├── _sources.yml
├── bronze/          -> 4 models (view)
├── silver/          -> 4 models (table)
└── gold/            -> 3 models (table), 1 por data mart
    ├── sales/
    ├── customer_success/
    └── pricing/
```

### Configuracao dbt_project.yml

```yaml
models:
  ecommerce:
    bronze:
      +materialized: view
      +schema: bronze
    silver:
      +materialized: table
      +schema: silver
    gold:
      +materialized: table
      +schema: gold

vars:
  segmentacao_vip_threshold: 10000
  segmentacao_top_tier_threshold: 5000
```

---

## Exemplo completo: ETL de Vendas

Os 3 modelos abaixo mostram o fluxo completo para a tabela de vendas. Use como referencia para criar os demais.

### bronze_vendas.sql

```sql
SELECT
    id_venda,
    data_venda,
    id_cliente,
    id_produto,
    canal_venda,
    quantidade,
    preco_unitario
FROM {{ source('raw', 'vendas') }}
```

### silver_vendas.sql

```sql
SELECT
    v.id_venda,
    v.id_cliente,
    v.id_produto,
    v.quantidade,
    v.preco_unitario AS preco_venda,
    v.data_venda,
    v.canal_venda,
    v.quantidade * v.preco_unitario AS receita_total,
    DATE(v.data_venda::timestamp) AS data_venda_date,
    EXTRACT(YEAR FROM v.data_venda::timestamp) AS ano_venda,
    EXTRACT(MONTH FROM v.data_venda::timestamp) AS mes_venda,
    EXTRACT(DAY FROM v.data_venda::timestamp) AS dia_venda,
    EXTRACT(DOW FROM v.data_venda::timestamp) AS dia_semana,
    EXTRACT(HOUR FROM v.data_venda::timestamp) AS hora_venda
FROM {{ ref('bronze_vendas') }} v
```

### vendas_temporais.sql (gold/sales/)

```sql
SELECT
    v.data_venda_date AS data_venda,
    v.ano_venda,
    v.mes_venda,
    v.dia_venda,
    CASE v.dia_semana
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda'
        WHEN 2 THEN 'Terca'
        WHEN 3 THEN 'Quarta'
        WHEN 4 THEN 'Quinta'
        WHEN 5 THEN 'Sexta'
        WHEN 6 THEN 'Sabado'
    END AS dia_semana_nome,
    v.hora_venda,
    SUM(v.receita_total) AS receita_total,
    SUM(v.quantidade) AS quantidade_total,
    COUNT(DISTINCT v.id_venda) AS total_vendas,
    COUNT(DISTINCT v.id_cliente) AS total_clientes_unicos,
    AVG(v.receita_total) AS ticket_medio
FROM {{ ref('silver_vendas') }} v
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY data_venda DESC, v.hora_venda
```

---

## Modelos restantes a criar

### Camada Bronze

**Objetivo:** Copia exata das tabelas raw. Sem transformacao. Serve como contrato do dado.
**Materializacao:** view
**Regra:** SELECT explicito de todas as colunas da fonte. Sem WHERE, sem CAST, sem transformacao.
**Referencia:** Usar `{{ source('raw', 'nome_tabela') }}`

#### bronze_clientes.sql
- Fonte: `{{ source('raw', 'clientes') }}`
- Colunas: id_cliente, nome_cliente, estado, pais, data_cadastro

#### bronze_produtos.sql
- Fonte: `{{ source('raw', 'produtos') }}`
- Colunas: id_produto, nome_produto, categoria, marca, preco_atual, data_criacao

#### bronze_preco_competidores.sql
- Fonte: `{{ source('raw', 'preco_competidores') }}`
- Colunas: id_produto, nome_concorrente, preco_concorrente, data_coleta

---

## Camada Silver

**Objetivo:** Manter todas as colunas do bronze + criar novas colunas calculadas.
**Materializacao:** table
**Regras gerais:**
- Cada silver corresponde a exatamente 1 bronze (relacao 1:1)
- Sem JOINs entre tabelas
- Sem WHERE (nao filtrar dados)
- Sem UPPER, TRIM ou limpeza de texto
- Sem flags de validacao
- Apenas adicionar colunas calculadas derivadas das colunas existentes
- Referencia: Usar `{{ ref('bronze_nome') }}`

### Modelos a criar

#### silver_clientes.sql
- Fonte: `{{ ref('bronze_clientes') }}`
- Colunas: id_cliente, nome_cliente, estado, pais, data_cadastro
- Sem colunas calculadas (pass-through)

#### silver_produtos.sql
- Fonte: `{{ ref('bronze_produtos') }}`
- Colunas originais mantidas: id_produto, nome_produto, categoria, marca, preco_atual, data_criacao
- Colunas calculadas:
  - `faixa_preco` = CASE WHEN preco_atual > 1000 THEN 'PREMIUM' WHEN preco_atual > 500 THEN 'MEDIO' ELSE 'BASICO' END

#### silver_preco_competidores.sql
- Fonte: `{{ ref('bronze_preco_competidores') }}`
- Colunas originais mantidas: id_produto, nome_concorrente, preco_concorrente, data_coleta
- Colunas calculadas:
  - `data_coleta_date` = DATE(data_coleta::timestamp)

---

## Camada Gold

**Objetivo:** Responder perguntas de negocio. JOINs entre tabelas silver + agregacoes + metricas.
**Materializacao:** table
**Regras gerais:**
- Fazer JOINs entre tabelas silver conforme necessidade
- Usar LEFT JOIN (nao perder registros da tabela principal)
- Agregacoes com GROUP BY
- Referencia: Usar `{{ ref('silver_nome') }}`
- Variaveis de negocio: Usar `{{ var('nome_variavel', valor_default) }}`
- 1 modelo por data mart (3 data marts)

### Data Mart: Customer Success

#### clientes_segmentacao.sql

**Pergunta de negocio:** Quais sao meus melhores clientes?

- Pasta: `models/gold/customer_success/`
- Fontes: `{{ ref('silver_vendas') }}` v LEFT JOIN `{{ ref('silver_clientes') }}` c ON v.id_cliente = c.id_cliente
- Usar CTE `receita_por_cliente` para agregar antes de segmentar
- Agrupamento na CTE: GROUP BY v.id_cliente, c.nome_cliente, c.estado
- Ordenacao: ORDER BY receita_total DESC

**Colunas da CTE receita_por_cliente:**

| Coluna | Logica |
|--------|--------|
| id_cliente | v.id_cliente |
| nome_cliente | c.nome_cliente |
| estado | c.estado |
| receita_total | SUM(v.receita_total) |
| total_compras | COUNT(DISTINCT v.id_venda) |
| ticket_medio | AVG(v.receita_total) |
| primeira_compra | MIN(v.data_venda_date) |
| ultima_compra | MAX(v.data_venda_date) |

**Colunas de saida (SELECT final sobre a CTE):**

| Coluna | Logica |
|--------|--------|
| cliente_id | id_cliente (alias) |
| nome_cliente | nome_cliente |
| estado | estado |
| receita_total | receita_total |
| total_compras | total_compras |
| ticket_medio | ticket_medio |
| primeira_compra | primeira_compra |
| ultima_compra | ultima_compra |
| segmento_cliente | CASE: receita_total >= var('segmentacao_vip_threshold', 10000) -> 'VIP', receita_total >= var('segmentacao_top_tier_threshold', 5000) -> 'TOP_TIER', ELSE -> 'REGULAR' |
| ranking_receita | ROW_NUMBER() OVER (ORDER BY receita_total DESC) |

**Regras de segmentacao:**
- VIP: receita_total >= R$ 10.000 (configuravel via var)
- TOP_TIER: receita_total >= R$ 5.000 (configuravel via var)
- REGULAR: receita_total < R$ 5.000

---

### Data Mart: Pricing

#### precos_competitividade.sql

**Pergunta de negocio:** Como estamos em relacao a concorrencia?

- Pasta: `models/gold/pricing/`
- Usar 2 CTEs antes do SELECT final
- Ordenacao: ORDER BY diferenca_percentual_vs_media DESC

**CTE 1 - precos_por_produto:**
- Fontes: `{{ ref('silver_produtos') }}` p LEFT JOIN `{{ ref('silver_preco_competidores') }}` pc ON p.id_produto = pc.id_produto
- Agrupamento: GROUP BY p.id_produto, p.nome_produto, p.categoria, p.marca, p.preco_atual

| Coluna | Logica |
|--------|--------|
| id_produto | p.id_produto |
| nome_produto | p.nome_produto |
| categoria | p.categoria |
| marca | p.marca |
| nosso_preco | p.preco_atual |
| preco_medio_concorrentes | AVG(pc.preco_concorrente) |
| preco_minimo_concorrentes | MIN(pc.preco_concorrente) |
| preco_maximo_concorrentes | MAX(pc.preco_concorrente) |
| total_concorrentes | COUNT(DISTINCT pc.nome_concorrente) |

**CTE 2 - vendas_por_produto:**
- Fonte: `{{ ref('silver_vendas') }}` v
- Agrupamento: GROUP BY v.id_produto

| Coluna | Logica |
|--------|--------|
| id_produto | v.id_produto |
| receita_total | SUM(v.receita_total) |
| quantidade_total | SUM(v.quantidade) |

**SELECT final:**
- JOIN: precos_por_produto pp LEFT JOIN vendas_por_produto vp ON pp.id_produto = vp.id_produto
- Filtro: WHERE pp.preco_medio_concorrentes IS NOT NULL (so produtos com dados de concorrentes)

| Coluna | Logica |
|--------|--------|
| produto_id | pp.id_produto (alias) |
| nome_produto | pp.nome_produto |
| categoria | pp.categoria |
| marca | pp.marca |
| nosso_preco | pp.nosso_preco |
| preco_medio_concorrentes | pp.preco_medio_concorrentes |
| preco_minimo_concorrentes | pp.preco_minimo_concorrentes |
| preco_maximo_concorrentes | pp.preco_maximo_concorrentes |
| total_concorrentes | pp.total_concorrentes |
| diferenca_percentual_vs_media | ((nosso_preco - preco_medio_concorrentes) / preco_medio_concorrentes) * 100 -- NULL se preco_medio = 0 |
| diferenca_percentual_vs_minimo | ((nosso_preco - preco_minimo_concorrentes) / preco_minimo_concorrentes) * 100 -- NULL se preco_minimo = 0 |
| classificacao_preco | Ver regras abaixo |
| receita_total | COALESCE(vp.receita_total, 0) |
| quantidade_total | COALESCE(vp.quantidade_total, 0) |

**Regras de classificacao de preco:**
1. Se nosso_preco > preco_maximo_concorrentes -> 'MAIS_CARO_QUE_TODOS'
2. Se nosso_preco < preco_minimo_concorrentes -> 'MAIS_BARATO_QUE_TODOS'
3. Se nosso_preco > preco_medio_concorrentes -> 'ACIMA_DA_MEDIA'
4. Se nosso_preco < preco_medio_concorrentes -> 'ABAIXO_DA_MEDIA'
5. Senao -> 'NA_MEDIA'

A ordem dos CASE WHEN importa (avaliar de cima para baixo).

---

## Arquivo _sources.yml

Criar em `models/_sources.yml`. Definir as 4 tabelas fonte com source name `raw`, schema `public`, e documentar todas as colunas de cada tabela conforme descrito na secao "Tabelas Fonte".

---

## Resumo de Entrega

| Camada | Modelos | Materializacao | Regra principal |
|--------|---------|----------------|-----------------|
| Bronze | 4 | view | SELECT explicito da fonte, sem transformacao |
| Silver | 4 | table | Colunas originais + colunas calculadas, sem JOIN, sem filtro |
| Gold | 3 | table | JOINs + agregacoes + regras de negocio, 1 por data mart |

**Total: 11 modelos SQL + 1 _sources.yml + 1 dbt_project.yml**