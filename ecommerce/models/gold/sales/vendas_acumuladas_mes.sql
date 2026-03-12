WITH vendas_mensais AS (
    SELECT
        ano_venda,
        mes_venda,
        SUM(receita_total) AS receita_total,
        SUM(quantidade) AS quantidade_total,
        COUNT(DISTINCT id_venda) AS quantidade_vendas
    FROM {{ ref('silver_vendas') }}
    GROUP BY 
        ano_venda, 
        mes_venda
)

SELECT
    ano_venda,
    mes_venda,
    receita_total,
    quantidade_total,
    quantidade_vendas,
    SUM(receita_total) OVER (PARTITION BY ano_venda ORDER BY mes_venda ASC) AS receita_acumulada_ytd
FROM vendas_mensais
ORDER BY 
    ano_venda DESC, 
    mes_venda DESC
