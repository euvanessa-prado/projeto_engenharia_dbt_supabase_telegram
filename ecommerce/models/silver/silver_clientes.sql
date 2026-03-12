SELECT
    id_cliente::varchar(30) AS id_cliente,
    nome_cliente,
    estado,
    pais,
    data_cadastro
FROM {{ ref('bronze_clientes') }}
