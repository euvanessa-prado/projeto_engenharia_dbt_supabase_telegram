SELECT
    id_produto,
    nome_produto,
    categoria,
    marca,
    preco_atual,
    data_criacao
FROM {{ source('raw', 'produtos') }}
