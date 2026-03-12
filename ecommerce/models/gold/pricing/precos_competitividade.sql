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
    FROM {{ ref('silver_produtos') }} p
    LEFT JOIN {{ ref('silver_preco_competidores') }} pc ON p.id_produto = pc.id_produto
    GROUP BY
        p.id_produto,
        p.nome_produto,
        p.categoria,
        p.marca,
        p.preco_atual
),
vendas_por_produto AS (
    SELECT
        id_produto,
        SUM(receita_total) AS receita_total,
        SUM(quantidade) AS quantidade_total
    FROM {{ ref('silver_vendas') }}
    GROUP BY id_produto
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
        WHEN pp.preco_medio_concorrentes > 0 THEN ((pp.nosso_preco - pp.preco_medio_concorrentes) / pp.preco_medio_concorrentes) * 100 
        ELSE NULL 
    END AS diferenca_percentual_vs_media,
    CASE 
        WHEN pp.preco_minimo_concorrentes > 0 THEN ((pp.nosso_preco - pp.preco_minimo_concorrentes) / pp.preco_minimo_concorrentes) * 100 
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
LEFT JOIN vendas_por_produto vp ON pp.id_produto = vp.id_produto
WHERE pp.preco_medio_concorrentes IS NOT NULL
ORDER BY diferenca_percentual_vs_media DESC
