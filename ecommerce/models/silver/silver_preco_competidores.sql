SELECT
    id_produto::varchar(30) AS id_produto,
    nome_concorrente,
    preco_concorrente,
    data_coleta,
    DATE(data_coleta::timestamp) AS data_coleta_date
FROM {{ ref('bronze_preco_competidores') }}
