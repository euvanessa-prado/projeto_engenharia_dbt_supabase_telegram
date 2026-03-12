SELECT
    id_produto::varchar(30) AS id_produto,
    nome_produto,
    categoria,
    marca,
    preco_atual,
    data_criacao,
    CASE 
        WHEN preco_atual > 1000 THEN 'PREMIUM' 
        WHEN preco_atual > 500 THEN 'MEDIO' 
        ELSE 'BASICO' 
    END AS faixa_preco
FROM {{ ref('bronze_produtos') }}
