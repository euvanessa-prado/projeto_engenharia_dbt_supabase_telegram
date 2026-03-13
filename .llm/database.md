# Gold Layer - Catálogo de Dados (Data Marts)

> Documento técnico para analistas de dados, catálogos de dados e agentes de IA (Claude Code).
> Contém schemas, colunas, tipos, regras de negócio, sample data e perguntas analíticas prontas.

---

## Visão Geral

| Propriedade | Valor |
|---|---|
| **Banco de Dados** | PostgreSQL (Supabase) |
| **Arquitetura** | Medalhão (Bronze → Silver → Gold) |
| **Ferramenta de Modelagem** | dbt |
| **Materialização Gold** | `table` |
| **Total de Data Marts** | 3 |

### Data Marts disponíveis

| # | Schema | Tabela | Domínio | Objetivo |
|---|---|---|---|---|
| 1 | `public_gold_sales` | `vendas_temporais` | Vendas | Métricas de vendas agregadas por dia/hora |
| 2 | `public_gold_cs` | `clientes_segmentacao` | Customer Success | Segmentação de clientes por receita (RFM simplificado) |
| 3 | `public_gold_pricing` | `precos_competitividade` | Pricing | Análise de competitividade de preços vs concorrentes |

### Fluxo de dados (Lineage)

```
┌─────────────────────────────────────────────────────────────────────┐
│ RAW (schema: public)                                                │
│ vendas │ clientes │ produtos │ preco_competidores                   │
└────┬────────┬──────────┬────────────┬───────────────────────────────┘
     ▼        ▼          ▼            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ BRONZE (views - cópia exata das tabelas raw)                        │
│ bronze_vendas │ bronze_clientes │ bronze_produtos │ bronze_preco_*  │
└────┬────────────┬─────────────────┬───────────────┬─────────────────┘
     ▼            ▼                 ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SILVER (tables - limpeza, cálculos, enriquecimento)                 │
│ silver_vendas │ silver_clientes │ silver_produtos │ silver_preco_*  │
└────┬────────────┬─────────────────┬───────────────┬─────────────────┘
     ▼            ▼                 ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ GOLD (tables - KPIs prontos para consumo)                           │
│ vendas_temporais │ clientes_segmentacao │ precos_competitividade     │
└─────────────────────────────────────────────────────────────────────┘
```

### Volume de dados (fonte raw)

| Tabela Raw | Registros | Descrição |
|---|---|---|
| `vendas` | ~3.020 | Transações de vendas |
| `clientes` | 50 | Base de clientes cadastrados |
| `produtos` | 215 | Catálogo de produtos |
| `preco_competidores` | ~728 | Preços coletados de concorrentes |

---

## Data Mart 1: `vendas_temporais`

### Metadados

| Propriedade | Valor |
|---|---|
| **Schema** | `public_gold_sales` |
| **Materialização** | table |
| **Granularidade** | 1 linha por combinação de `data_venda` + `hora_venda` |
| **Fonte Silver** | `silver_vendas` |
| **Tags dbt** | `gold`, `kpi`, `metrics` |
| **Domínio** | Vendas |

### Objetivo de negócio

Fornecer métricas de vendas agregadas por dimensão temporal (dia, semana, hora) para análise de performance comercial, identificação de padrões sazonais e tomada de decisão em tempo hábil.

### Schema completo

| Coluna | Tipo | Nullable | Descrição |
|---|---|---|---|
| `data_venda` | `DATE` | NOT NULL | Data da venda (YYYY-MM-DD) |
| `ano_venda` | `INTEGER` | NOT NULL | Ano extraído da data (ex: 2025) |
| `mes_venda` | `INTEGER` | NOT NULL | Mês extraído da data (1-12) |
| `dia_venda` | `INTEGER` | NOT NULL | Dia do mês (1-31) |
| `dia_semana_nome` | `VARCHAR` | NOT NULL | Nome do dia da semana em português (Domingo, Segunda, ..., Sábado) |
| `hora_venda` | `INTEGER` | NOT NULL | Hora da venda (0-23) |
| `receita_total` | `NUMERIC` | NOT NULL | Soma da receita total (quantidade × preço unitário) no período |
| `quantidade_total` | `INTEGER` | NOT NULL | Soma das quantidades vendidas no período |
| `total_vendas` | `INTEGER` | NOT NULL | Contagem distinta de transações (id_venda) |
| `total_clientes_unicos` | `INTEGER` | NOT NULL | Contagem distinta de clientes que compraram no período |
| `ticket_medio` | `NUMERIC` | NOT NULL | Receita média por transação (AVG de receita_total) |

### Regras de negócio

- `receita_total` = SUM de (`quantidade` × `preco_unitario`) já calculado na silver como `receita_total`
- `ticket_medio` = AVG da receita por transação individual (não é receita_total / total_vendas)
- `dia_semana_nome` mapeado de EXTRACT(DOW): 0=Domingo, 1=Segunda, ..., 6=Sábado
- Agrupamento por: `data_venda_date`, `ano_venda`, `mes_venda`, `dia_venda`, `dia_semana_nome`, `hora_venda`
- Ordenação: `data_venda DESC`, `hora_venda ASC`

### SQL de origem

```sql
SELECT
    v.data_venda_date AS data_venda,
    v.ano_venda,
    v.mes_venda,
    v.dia_venda,
    CASE v.dia_semana
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda'
        WHEN 2 THEN 'Terça'
        WHEN 3 THEN 'Quarta'
        WHEN 4 THEN 'Quinta'
        WHEN 5 THEN 'Sexta'
        WHEN 6 THEN 'Sábado'
    END AS dia_semana_nome,
    v.hora_venda,
    SUM(v.receita_total) AS receita_total,
    SUM(v.quantidade) AS quantidade_total,
    COUNT(DISTINCT v.id_venda) AS total_vendas,
    COUNT(DISTINCT v.id_cliente) AS total_clientes_unicos,
    AVG(v.receita_total) AS ticket_medio
FROM silver_vendas v
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY data_venda DESC, v.hora_venda
```

### Sample Data

| data_venda | ano_venda | mes_venda | dia_venda | dia_semana_nome | hora_venda | receita_total | quantidade_total | total_vendas | total_clientes_unicos | ticket_medio |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-12-13 | 2025 | 12 | 13 | Sábado | 17 | 1006.00 | 6 | 3 | 3 | 335.33 |
| 2025-12-13 | 2025 | 12 | 13 | Sábado | 10 | 89.50 | 1 | 1 | 1 | 89.50 |
| 2025-12-13 | 2025 | 12 | 13 | Sábado | 22 | 190.71 | 1 | 1 | 1 | 190.71 |
| 2025-12-13 | 2025 | 12 | 13 | Sábado | 13 | 51.99 | 1 | 1 | 1 | 51.99 |
| 2025-12-13 | 2025 | 12 | 13 | Sábado | 09 | 189.00 | 1 | 1 | 1 | 189.00 |

### Perguntas de negócio que esta tabela responde

1. **Qual a receita total por dia/semana/mês?** → Agrupar `receita_total` por `data_venda`, `mes_venda` ou `ano_venda`
2. **Qual o dia da semana com maior volume de vendas?** → Agrupar por `dia_semana_nome`, somar `total_vendas`
3. **Qual o horário de pico de vendas?** → Agrupar por `hora_venda`, somar `receita_total`
4. **Qual a evolução do ticket médio ao longo do tempo?** → Média ponderada de `ticket_medio` por `data_venda`
5. **Quantos clientes únicos compram por dia?** → Usar `total_clientes_unicos` por `data_venda`
6. **Existe sazonalidade nas vendas?** → Comparar `receita_total` por `mes_venda` entre anos
7. **Qual a tendência de crescimento de vendas?** → Série temporal de `receita_total` por `data_venda`
8. **Qual o volume de vendas nos finais de semana vs dias úteis?** → Filtrar `dia_semana_nome` IN ('Sábado', 'Domingo') vs demais

### Queries prontas para dashboards

```sql
-- Receita total por mês
SELECT ano_venda, mes_venda,
       SUM(receita_total) AS receita_mensal,
       SUM(total_vendas) AS vendas_mensal
FROM public_gold_sales.vendas_temporais
GROUP BY ano_venda, mes_venda
ORDER BY ano_venda, mes_venda;

-- Top 5 horários de pico
SELECT hora_venda,
       SUM(receita_total) AS receita,
       SUM(total_vendas) AS vendas
FROM public_gold_sales.vendas_temporais
GROUP BY hora_venda
ORDER BY receita DESC
LIMIT 5;

-- Comparação dias úteis vs fins de semana
SELECT
    CASE WHEN dia_semana_nome IN ('Sábado', 'Domingo') THEN 'Fim de Semana' ELSE 'Dia Útil' END AS tipo_dia,
    SUM(receita_total) AS receita,
    AVG(ticket_medio) AS ticket_medio
FROM public_gold_sales.vendas_temporais
GROUP BY 1;
```

---

## Data Mart 2: `clientes_segmentacao`

### Metadados

| Propriedade | Valor |
|---|---|
| **Schema** | `public_gold_cs` |
| **Materialização** | table |
| **Granularidade** | 1 linha por cliente |
| **Fontes Silver** | `silver_vendas`, `silver_clientes` |
| **Tags dbt** | `gold`, `kpi`, `metrics` |
| **Domínio** | Customer Success |

### Objetivo de negócio

Segmentar a base de clientes em tiers baseados em receita acumulada (VIP, TOP_TIER, REGULAR) para direcionar estratégias de retenção, campanhas de marketing e identificação de clientes de alto valor.

### Schema completo

| Coluna | Tipo | Nullable | Descrição |
|---|---|---|---|
| `cliente_id` | `VARCHAR` | NOT NULL | Identificador único do cliente (formato: `cus_xxxxxxxxxxxx`) |
| `nome_cliente` | `VARCHAR` | NULL | Nome completo do cliente (pode conter títulos: Dr., Dra., Srta.) |
| `estado` | `VARCHAR(2)` | NULL | Sigla do estado brasileiro (UF) |
| `receita_total` | `NUMERIC` | NOT NULL | Soma total da receita gerada pelo cliente |
| `total_compras` | `INTEGER` | NOT NULL | Contagem distinta de transações do cliente |
| `ticket_medio` | `NUMERIC` | NOT NULL | Receita média por transação do cliente |
| `primeira_compra` | `DATE` | NOT NULL | Data da primeira compra do cliente |
| `ultima_compra` | `DATE` | NOT NULL | Data da última compra do cliente |
| `segmento_cliente` | `VARCHAR` | NOT NULL | Segmento: `VIP`, `TOP_TIER` ou `REGULAR` |
| `ranking_receita` | `INTEGER` | NOT NULL | Posição no ranking de receita (1 = maior receita) |

### Regras de negócio e segmentação

```
┌──────────────────────────────────────────────────────┐
│             REGRAS DE SEGMENTAÇÃO                    │
├──────────────┬───────────────────────────────────────┤
│ Segmento     │ Critério                              │
├──────────────┼───────────────────────────────────────┤
│ VIP          │ receita_total >= R$ 10.000             │
│ TOP_TIER     │ receita_total >= R$ 5.000 e < R$10.000│
│ REGULAR      │ receita_total < R$ 5.000              │
└──────────────┴───────────────────────────────────────┘
```

- Thresholds configuráveis via variáveis dbt:
  - `segmentacao_vip_threshold`: default `10000`
  - `segmentacao_top_tier_threshold`: default `5000`
- `ranking_receita` = `ROW_NUMBER() OVER (ORDER BY receita_total DESC)` — ranking 1 = maior receita
- JOIN entre `silver_vendas` e `silver_clientes` via `id_cliente`
- Agregação por `id_cliente`, `nome_cliente`, `estado`

### SQL de origem

```sql
WITH receita_por_cliente AS (
    SELECT
        v.id_cliente,
        c.nome_cliente,
        c.estado,
        SUM(v.receita_total) AS receita_total,
        COUNT(DISTINCT v.id_venda) AS total_compras,
        AVG(v.receita_total) AS ticket_medio,
        MIN(v.data_venda_date) AS primeira_compra,
        MAX(v.data_venda_date) AS ultima_compra
    FROM silver_vendas v
    LEFT JOIN silver_clientes c
        ON v.id_cliente = c.id_cliente
    GROUP BY 1, 2, 3
)
SELECT
    id_cliente AS cliente_id,
    nome_cliente,
    estado,
    receita_total,
    total_compras,
    ticket_medio,
    primeira_compra,
    ultima_compra,
    CASE
        WHEN receita_total >= 10000 THEN 'VIP'
        WHEN receita_total >= 5000 THEN 'TOP_TIER'
        ELSE 'REGULAR'
    END AS segmento_cliente,
    ROW_NUMBER() OVER (ORDER BY receita_total DESC) AS ranking_receita
FROM receita_por_cliente
ORDER BY receita_total DESC
```

### Sample Data

| cliente_id | nome_cliente | estado | receita_total | total_compras | ticket_medio | primeira_compra | ultima_compra | segmento_cliente | ranking_receita |
|---|---|---|---|---|---|---|---|---|---|
| cus_2b1b3e2a1515 | ANA SOPHIA PEREIRA | MG | 30716.63 | 53 | 579.56 | - | - | VIP | 1 |
| cus_25d1cb23f872 | MELISSA PASTOR | AC | 30211.93 | 68 | 444.29 | - | - | VIP | 2 |
| cus_c3944101594c | MURILO DA MATA | RR | 28285.82 | 81 | 349.21 | - | - | VIP | 3 |
| cus_fa3a88d1ccef | DR. BENÍCIO GOMES | AL | 27424.23 | 72 | 380.89 | - | - | VIP | 4 |
| cus_f64907d41a69 | HENRIQUE DA CONCEIÇÃO | DF | 26687.99 | 77 | 346.60 | - | - | VIP | 5 |
| cus_b0026583b709 | DRA. MARIANE PACHECO | MT | 25454.83 | 73 | 348.70 | - | - | VIP | 6 |
| cus_4e62d52db97a | JOSUÉ SOUZA | RJ | 24750.17 | 50 | 495.00 | - | - | VIP | 7 |
| cus_c9cd13d1ae9f | SRTA. YASMIN SIQUEIRA | PA | 23674.10 | 53 | 446.68 | - | - | VIP | 8 |
| cus_3580317ddeab | BELLA BORGES | AM | 22865.99 | 57 | 401.16 | - | - | VIP | 9 |
| cus_0343c0763f76 | VITOR GABRIEL DA LUZ | RS | 22734.53 | 65 | 349.76 | - | - | VIP | 10 |

### Perguntas de negócio que esta tabela responde

1. **Quantos clientes temos em cada segmento?** → `COUNT(*) GROUP BY segmento_cliente`
2. **Qual a receita total por segmento?** → `SUM(receita_total) GROUP BY segmento_cliente`
3. **Quem são os top 10 clientes por receita?** → `WHERE ranking_receita <= 10`
4. **Qual estado concentra mais clientes VIP?** → `WHERE segmento_cliente = 'VIP' GROUP BY estado`
5. **Qual o ticket médio por segmento?** → `AVG(ticket_medio) GROUP BY segmento_cliente`
6. **Qual a frequência de compra dos clientes VIP vs REGULAR?** → `AVG(total_compras) GROUP BY segmento_cliente`
7. **Quais clientes não compram há mais tempo?** → Comparar `ultima_compra` com data atual
8. **Qual a distribuição geográfica da receita?** → `SUM(receita_total) GROUP BY estado`
9. **Qual o lifetime (primeira à última compra) dos clientes por segmento?** → `ultima_compra - primeira_compra GROUP BY segmento_cliente`
10. **Quais clientes estão próximos de mudar de segmento?** → Ex: `WHERE segmento_cliente = 'TOP_TIER' AND receita_total >= 9000`

### Queries prontas para dashboards

```sql
-- Distribuição de clientes por segmento
SELECT segmento_cliente,
       COUNT(*) AS total_clientes,
       SUM(receita_total) AS receita_total,
       AVG(ticket_medio) AS ticket_medio_avg,
       AVG(total_compras) AS compras_avg
FROM public_gold_cs.clientes_segmentacao
GROUP BY segmento_cliente
ORDER BY receita_total DESC;

-- Top 10 clientes por receita
SELECT cliente_id, nome_cliente, estado,
       receita_total, total_compras, segmento_cliente
FROM public_gold_cs.clientes_segmentacao
WHERE ranking_receita <= 10;

-- Receita por estado
SELECT estado,
       COUNT(*) AS total_clientes,
       SUM(receita_total) AS receita_total,
       COUNT(*) FILTER (WHERE segmento_cliente = 'VIP') AS clientes_vip
FROM public_gold_cs.clientes_segmentacao
GROUP BY estado
ORDER BY receita_total DESC;

-- Clientes próximos de upgrade para VIP
SELECT cliente_id, nome_cliente, receita_total,
       10000 - receita_total AS falta_para_vip
FROM public_gold_cs.clientes_segmentacao
WHERE segmento_cliente = 'TOP_TIER'
ORDER BY receita_total DESC;
```

---

## Data Mart 3: `precos_competitividade`

### Metadados

| Propriedade | Valor |
|---|---|
| **Schema** | `public_gold_pricing` |
| **Materialização** | table |
| **Granularidade** | 1 linha por produto (que tenha dados de concorrentes) |
| **Fontes Silver** | `silver_produtos`, `silver_preco_competidores`, `silver_vendas` |
| **Tags dbt** | `gold`, `kpi`, `metrics` |
| **Domínio** | Pricing / Inteligência Competitiva |

### Objetivo de negócio

Analisar o posicionamento de preços dos produtos em relação à concorrência (Mercado Livre, Amazon, Shopee, Magalu), identificando oportunidades de reprecificação e correlacionando competitividade de preço com volume de vendas.

### Schema completo

| Coluna | Tipo | Nullable | Descrição |
|---|---|---|---|
| `produto_id` | `VARCHAR` | NOT NULL | Identificador único do produto (formato: `prd_xxxxxxxxxxxx`) |
| `nome_produto` | `VARCHAR` | NOT NULL | Nome do produto |
| `categoria` | `VARCHAR` | NOT NULL | Categoria do produto (Eletrônicos, Casa, Moda, Games, Cozinha, Beleza, Acessórios) |
| `marca` | `VARCHAR` | NOT NULL | Marca do produto (Samsung, Apple, Xiaomi, LG, Philips, etc.) |
| `nosso_preco` | `NUMERIC` | NOT NULL | Preço atual do produto na nossa loja |
| `preco_medio_concorrentes` | `NUMERIC` | NULL | Média dos preços coletados dos concorrentes |
| `preco_minimo_concorrentes` | `NUMERIC` | NULL | Menor preço encontrado entre os concorrentes |
| `preco_maximo_concorrentes` | `NUMERIC` | NULL | Maior preço encontrado entre os concorrentes |
| `total_concorrentes` | `INTEGER` | NOT NULL | Quantidade de concorrentes com preço coletado para este produto |
| `diferenca_percentual_vs_media` | `NUMERIC` | NULL | Diferença % do nosso preço vs média dos concorrentes. Positivo = mais caro, Negativo = mais barato |
| `diferenca_percentual_vs_minimo` | `NUMERIC` | NULL | Diferença % do nosso preço vs menor preço concorrente |
| `classificacao_preco` | `VARCHAR` | NOT NULL | Classificação competitiva do produto |
| `receita_total` | `NUMERIC` | NOT NULL | Receita total gerada pelo produto (0 se sem vendas) |
| `quantidade_total` | `INTEGER` | NOT NULL | Quantidade total vendida do produto (0 se sem vendas) |

### Regras de negócio e classificação

```
┌─────────────────────────────────────────────────────────────────────┐
│             CLASSIFICAÇÃO DE COMPETITIVIDADE                        │
├─────────────────────────┬───────────────────────────────────────────┤
│ Classificação           │ Critério                                  │
├─────────────────────────┼───────────────────────────────────────────┤
│ MAIS_CARO_QUE_TODOS     │ nosso_preco > preco_maximo_concorrentes  │
│ MAIS_BARATO_QUE_TODOS   │ nosso_preco < preco_minimo_concorrentes  │
│ ACIMA_DA_MEDIA          │ nosso_preco > preco_medio_concorrentes   │
│ ABAIXO_DA_MEDIA         │ nosso_preco < preco_medio_concorrentes   │
│ NA_MEDIA                │ nosso_preco = preco_medio_concorrentes   │
└─────────────────────────┴───────────────────────────────────────────┘
```

- `diferenca_percentual_vs_media` = `((nosso_preco - preco_medio) / preco_medio) × 100`
- `diferenca_percentual_vs_minimo` = `((nosso_preco - preco_minimo) / preco_minimo) × 100`
- Somente produtos com pelo menos 1 concorrente são incluídos (`WHERE preco_medio_concorrentes IS NOT NULL`)
- Receita e quantidade vêm de LEFT JOIN com vendas — produtos sem vendas mostram 0
- Concorrentes conhecidos: **Mercado Livre**, **Amazon**, **Shopee**, **Magalu**
- Ordenação: `diferenca_percentual_vs_media DESC` (mais caros primeiro)

### SQL de origem

```sql
WITH precos_por_produto AS (
    SELECT
        p.id_produto,
        p.nome_produto,
        p.categoria,
        p.marca,
        p.preco_atual AS nosso_preco,
        AVG(pc.preco_concorrente) AS preco_medio_concorrentes,
        MIN(pc.preco_concorrente) AS preco_minimo_concorrentes,
        MAX(pc.preco_concorrente) AS preco_maximo_concorrentes,
        COUNT(DISTINCT pc.nome_concorrente) AS total_concorrentes
    FROM silver_produtos p
    LEFT JOIN silver_preco_competidores pc
        ON p.id_produto = pc.id_produto
    GROUP BY 1, 2, 3, 4, 5
),
vendas_por_produto AS (
    SELECT
        v.id_produto,
        SUM(v.receita_total) AS receita_total,
        SUM(v.quantidade) AS quantidade_total
    FROM silver_vendas v
    GROUP BY 1
)
SELECT
    pp.id_produto AS produto_id,
    pp.nome_produto,
    pp.categoria,
    pp.marca,
    pp.nosso_preco,
    pp.preco_medio_concorrentes,
    pp.preco_minimo_concorrentes,
    pp.preco_maximo_concorrentes,
    pp.total_concorrentes,
    CASE
        WHEN pp.preco_medio_concorrentes > 0 THEN
            ((pp.nosso_preco - pp.preco_medio_concorrentes) / pp.preco_medio_concorrentes) * 100
        ELSE NULL
    END AS diferenca_percentual_vs_media,
    CASE
        WHEN pp.preco_minimo_concorrentes > 0 THEN
            ((pp.nosso_preco - pp.preco_minimo_concorrentes) / pp.preco_minimo_concorrentes) * 100
        ELSE NULL
    END AS diferenca_percentual_vs_minimo,
    CASE
        WHEN pp.nosso_preco > pp.preco_maximo_concorrentes THEN 'MAIS_CARO_QUE_TODOS'
        WHEN pp.nosso_preco < pp.preco_minimo_concorrentes THEN 'MAIS_BARATO_QUE_TODOS'
        WHEN pp.nosso_preco > pp.preco_medio_concorrentes THEN 'ACIMA_DA_MEDIA'
        WHEN pp.nosso_preco < pp.preco_medio_concorrentes THEN 'ABAIXO_DA_MEDIA'
        ELSE 'NA_MEDIA'
    END AS classificacao_preco,
    COALESCE(vp.receita_total, 0) AS receita_total,
    COALESCE(vp.quantidade_total, 0) AS quantidade_total
FROM precos_por_produto pp
LEFT JOIN vendas_por_produto vp
    ON pp.id_produto = vp.id_produto
WHERE pp.preco_medio_concorrentes IS NOT NULL
ORDER BY diferenca_percentual_vs_media DESC
```

### Sample Data

| produto_id | nome_produto | categoria | marca | nosso_preco | preco_medio_concorrentes | preco_minimo | preco_maximo | total_concorrentes | dif_%_media | classificacao_preco | receita_total | qtd_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| prd_2293732b7542 | Cortina Blackout | Casa | Xiaomi | 68.90 | 67.98 | 65.45 | 70.97 | 3 | +1.35% | ACIMA_DA_MEDIA | 1240.20 | 18 |
| prd_84a009f1889d | Cortina Box | Casa | Consul | 32.90 | 32.32 | 31.25 | 33.89 | 4 | +1.79% | ACIMA_DA_MEDIA | 625.10 | 19 |
| prd_ff35b88df534 | SSD 500GB | Eletrônicos | Acer | 211.90 | 210.84 | 194.95 | 224.61 | 4 | +0.50% | ACIMA_DA_MEDIA | 2330.90 | 11 |
| prd_38c1b898aecc | Microfone Stream | Games | Samsung | 140.90 | 136.42 | 133.85 | 140.90 | 4 | +3.28% | NA_MEDIA | 845.40 | 6 |

### Perguntas de negócio que esta tabela responde

1. **Quantos produtos estão acima/abaixo da média do mercado?** → `COUNT(*) GROUP BY classificacao_preco`
2. **Quais produtos estão mais caros que todos os concorrentes?** → `WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'`
3. **Qual a diferença média de preço por categoria?** → `AVG(diferenca_percentual_vs_media) GROUP BY categoria`
4. **Existe correlação entre competitividade de preço e volume de vendas?** → Analisar `diferenca_percentual_vs_media` vs `quantidade_total`
5. **Quais categorias têm maior oportunidade de reprecificação?** → Categorias com maior `diferenca_percentual_vs_media` positiva
6. **Qual concorrente é mais agressivo em preço?** → Analisar `preco_minimo_concorrentes` (dados detalhados na silver)
7. **Quais produtos mais baratos que a concorrência têm baixo volume de vendas?** → `WHERE classificacao_preco LIKE 'MAIS_BARATO%' AND quantidade_total < X`
8. **Qual o impacto em receita dos produtos acima da média?** → `SUM(receita_total) WHERE classificacao_preco IN ('ACIMA_DA_MEDIA', 'MAIS_CARO_QUE_TODOS')`
9. **Quais marcas têm posicionamento premium vs economia?** → `AVG(diferenca_percentual_vs_media) GROUP BY marca`
10. **Qual a receita em risco por preços não competitivos?** → `SUM(receita_total) WHERE diferenca_percentual_vs_media > 10`

### Queries prontas para dashboards

```sql
-- Distribuição de produtos por classificação de preço
SELECT classificacao_preco,
       COUNT(*) AS total_produtos,
       AVG(diferenca_percentual_vs_media) AS dif_media_pct,
       SUM(receita_total) AS receita_total
FROM public_gold_pricing.precos_competitividade
GROUP BY classificacao_preco
ORDER BY total_produtos DESC;

-- Top 10 produtos mais caros vs concorrência
SELECT produto_id, nome_produto, categoria, marca,
       nosso_preco, preco_medio_concorrentes,
       diferenca_percentual_vs_media,
       receita_total
FROM public_gold_pricing.precos_competitividade
ORDER BY diferenca_percentual_vs_media DESC
LIMIT 10;

-- Competitividade por categoria
SELECT categoria,
       COUNT(*) AS total_produtos,
       AVG(diferenca_percentual_vs_media) AS dif_media_pct,
       SUM(receita_total) AS receita_total,
       COUNT(*) FILTER (WHERE classificacao_preco IN ('MAIS_CARO_QUE_TODOS', 'ACIMA_DA_MEDIA')) AS produtos_caros,
       COUNT(*) FILTER (WHERE classificacao_preco IN ('MAIS_BARATO_QUE_TODOS', 'ABAIXO_DA_MEDIA')) AS produtos_baratos
FROM public_gold_pricing.precos_competitividade
GROUP BY categoria
ORDER BY dif_media_pct DESC;

-- Oportunidades de reprecificação (produtos caros com baixa venda)
SELECT produto_id, nome_produto, categoria,
       nosso_preco, preco_medio_concorrentes,
       diferenca_percentual_vs_media,
       quantidade_total
FROM public_gold_pricing.precos_competitividade
WHERE classificacao_preco IN ('MAIS_CARO_QUE_TODOS', 'ACIMA_DA_MEDIA')
  AND quantidade_total < 5
ORDER BY diferenca_percentual_vs_media DESC;
```

---

## Relacionamentos entre Data Marts

```
┌──────────────────────────┐
│   clientes_segmentacao   │
│   (public_gold_cs)       │
│                          │
│  cliente_id ─────────────┼──┐
│  estado                  │  │
│  segmento_cliente        │  │
│  receita_total           │  │
└──────────────────────────┘  │
                              │  JOIN via silver_vendas.id_cliente
┌──────────────────────────┐  │
│   vendas_temporais       │◄─┘ (dados vêm da mesma silver_vendas)
│   (public_gold_sales)    │
│                          │
│  data_venda ─────────────┼──┐
│  receita_total           │  │
│  total_clientes_unicos   │  │
└──────────────────────────┘  │
                              │  JOIN via silver_vendas.id_produto
┌──────────────────────────┐  │
│  precos_competitividade  │◄─┘ (vendas_por_produto vem de silver_vendas)
│  (public_gold_pricing)   │
│                          │
│  produto_id              │
│  categoria               │
│  classificacao_preco     │
│  receita_total           │
└──────────────────────────┘
```

> **Nota**: As 3 tabelas gold não possuem chaves estrangeiras diretas entre si. A relação acontece através das tabelas silver (especialmente `silver_vendas`). Para análises cross-domain, faça JOINs via as tabelas silver ou crie CTEs combinando as gold.

### Query cross-domain de exemplo

```sql
-- Análise cruzada: segmento de cliente × competitividade de preço
-- (requer acesso às tabelas silver para o JOIN)
WITH vendas_detalhe AS (
    SELECT
        v.id_cliente,
        v.id_produto,
        v.receita_total
    FROM public_silver.silver_vendas v
)
SELECT
    cs.segmento_cliente,
    pc.classificacao_preco,
    COUNT(DISTINCT vd.id_cliente) AS total_clientes,
    SUM(vd.receita_total) AS receita
FROM vendas_detalhe vd
JOIN public_gold_cs.clientes_segmentacao cs ON vd.id_cliente = cs.cliente_id
JOIN public_gold_pricing.precos_competitividade pc ON vd.id_produto = pc.produto_id
GROUP BY 1, 2
ORDER BY 1, 2;
```

---

## Categorias e valores conhecidos

### Categorias de produtos
`Eletrônicos`, `Casa`, `Moda`, `Games`, `Cozinha`, `Beleza`, `Acessórios`

### Marcas
`Samsung`, `Apple`, `Xiaomi`, `LG`, `Philips`, `Motorola`, `Consul`, `Acer`, `Asus`

### Canais de venda (disponível na silver)
`ecommerce`, `loja_fisica`

### Estados (UF) presentes na base de clientes
Todos os estados brasileiros podem aparecer: `AC`, `AL`, `AM`, `CE`, `DF`, `ES`, `GO`, `MA`, `MG`, `MS`, `MT`, `PA`, `RJ`, `RR`, `RS`, `SE`, `SP`, `TO`, entre outros.

### Concorrentes monitorados
`Mercado Livre`, `Amazon`, `Shopee`, `Magalu`

### Segmentos de cliente
`VIP` (receita >= R$10.000), `TOP_TIER` (receita >= R$5.000), `REGULAR` (receita < R$5.000)

### Classificações de preço
`MAIS_CARO_QUE_TODOS`, `ACIMA_DA_MEDIA`, `NA_MEDIA`, `ABAIXO_DA_MEDIA`, `MAIS_BARATO_QUE_TODOS`

---

## Informações de conexão

| Propriedade | Valor |
|---|---|
| **Host** | Supabase (verificar `.env` ou `profiles.yml`) |
| **Porta** | 5432 (padrão PostgreSQL) |
| **Profile dbt** | `ecommerce` |
| **Schemas** | `public_gold_sales`, `public_gold_cs`, `public_gold_pricing` |

### Acesso via Python (exemplo)

```python
import psycopg2
import pandas as pd

# Conexão (ajustar credenciais)
conn = psycopg2.connect(
    host="SEU_HOST_SUPABASE",
    port=5432,
    dbname="postgres",
    user="postgres",
    password="SUA_SENHA"
)

# Leitura de cada data mart
df_vendas = pd.read_sql("SELECT * FROM public_gold_sales.vendas_temporais", conn)
df_clientes = pd.read_sql("SELECT * FROM public_gold_cs.clientes_segmentacao", conn)
df_precos = pd.read_sql("SELECT * FROM public_gold_pricing.precos_competitividade", conn)
```