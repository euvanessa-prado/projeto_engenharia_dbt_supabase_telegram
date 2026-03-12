SELECT
    id_produto,
    nome_concorrente,
    preco_concorrente,
    data_coleta
FROM {{ source('raw', 'preco_competidores') }}
