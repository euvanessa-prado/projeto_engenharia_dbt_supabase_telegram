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