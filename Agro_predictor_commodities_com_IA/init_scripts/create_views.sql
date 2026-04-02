-- Adicione isso no início do create_views.sql
\c agro_dw;

--- Rodar uma vez  IMPORTANTE: RODAR NO BANCO LOCAL DO POSTGRES
-- Habilita a funcionalidade de busca por trigramas
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Cria o índice de alta performance na coluna de nome da região |melhora a performance quando tem 'like' na query
CREATE INDEX idx_climate_region_trgm 
ON weather.climate_data 
USING gin (upper(region_name::text) gin_trgm_ops);


--1
--- View: finance.vw_commodities_consolidated
--- Objetivo: lista preço


DROP VIEW IF EXISTS finance.vw_commodities_consolidated CASCADE;

CREATE OR REPLACE VIEW finance.vw_commodities_consolidated
 AS
 SELECT p.record_date,
    p.ticker,
    m.commodity_name,
    m.unit AS unidade_medida,
    p.close_price AS preco_original,
    m.currency AS moeda_original,
        CASE
            WHEN m.currency::text = 'BRL'::text THEN p.close_price
            WHEN m.currency::text = 'USD'::text THEN p.close_price * d.taxa_fechamento
            ELSE p.close_price
        END AS preco_brl,
    m.related_region_weather AS regiao_climatica
   FROM finance.market_data p
     JOIN finance.commodities_metadata m ON p.ticker::text = m.ticker::text
     LEFT JOIN finance.exchange_rates d ON p.record_date = d.data AND m.currency::text = 'USD'::text;

ALTER TABLE finance.vw_commodities_consolidated OWNER TO admin_agro;


---


--2
--- View: finance.vw_h123_model_features
--- Objetivo: atender as hipoteses levantadas - 1, 2, 3
---         (vide READEME.md)

DROP VIEW IF EXISTS finance.vw_h123_model_features CASCADE;

CREATE OR REPLACE VIEW finance.vw_h123_model_features AS
WITH 
    base_mapping AS (
        SELECT 
            c.record_date,
            c.ticker,
            c.preco_brl,
            c.preco_original,
                c.regiao_climatica 
            AS regiao_negociacao,
                COALESCE(map.cidade_foco_clima, split_part(c.regiao_climatica::text, ','::text, 1)::character varying) 
            AS regiao_foco_clima
        FROM finance.vw_commodities_consolidated c
        LEFT JOIN finance.config_commodity_clima map ON c.ticker::text = map.ticker::text
    ), 
    joined_data AS (
        SELECT 
            b.record_date,
            b.ticker,
                b.preco_brl 
            AS close_price,
            b.preco_original,
            b.regiao_foco_clima,
                COALESCE(w.temp_max, 0::numeric) 
            AS temp_max,
                COALESCE(w.precipitation_mm, 0::numeric) 
            AS precipitation_mm,
                COALESCE(w.soil_moisture, 0::numeric) 
            AS soil_moisture
        FROM base_mapping b
        LEFT JOIN weather.climate_data w 
          ON b.record_date = w.record_date 
          -- Substituído ~~ por LIKE
          AND TRIM(BOTH FROM upper(w.region_name::text)) LIKE ('%' || TRIM(BOTH FROM upper(b.regiao_foco_clima::text)) || '%')
    ), 
    pre_calculations AS (
        SELECT 
            *,
                COALESCE((close_price - lag(close_price) OVER w_ticker) / NULLIF(lag(close_price) OVER w_ticker, 0::numeric), 0::numeric) 
            AS pct_change_d1,
            -- Cálculo da anomalia movido para cá para ser usado no SELECT final
                temp_max - avg(temp_max) OVER (PARTITION BY regiao_foco_clima ORDER BY record_date ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING) 
            AS temp_anomaly_30d
        FROM joined_data
        WINDOW w_ticker AS (PARTITION BY ticker ORDER BY record_date)
    )

SELECT 
    record_date,
    ticker,
    close_price,
    preco_original,
    regiao_foco_clima,
    pct_change_d1,
        avg(close_price) OVER w_7d 
    AS ma_7d,
        COALESCE(stddev(close_price) OVER w_7d, 0::numeric) 
    AS volatility_7d,
    temp_max,
    precipitation_mm,
        lag(precipitation_mm, 3, 0::numeric) OVER w_region 
    AS rain_lag_3,
        lag(precipitation_mm, 5, 0::numeric) OVER w_region 
    AS rain_lag_5,
        lag(temp_max, 3, 0::numeric) OVER w_region 
    AS temp_lag_3,
        COALESCE(sum(precipitation_mm) OVER w_7d, 0::numeric) 
    AS rain_accum_7d,
        CASE WHEN temp_max > 35::numeric THEN 1 ELSE 0 END 
    AS is_extreme_heat,
        CASE WHEN precipitation_mm = 0::numeric AND soil_moisture < 20::numeric THEN 1 ELSE 0 END 
    AS is_drought_risk,
        EXTRACT(doy FROM record_date) 
    AS day_of_year,
        EXTRACT(month FROM record_date) 
    AS month_num,
    temp_anomaly_30d,
    soil_moisture,
        CASE WHEN lag(precipitation_mm, 3, 0::numeric) OVER w_region > 10::numeric THEN 1 ELSE 0 END 
    AS is_heavy_rain_lag3,
        ABS(pct_change_d1) 
    AS price_intensity,
    -- Agora o is_mild_climate funciona pois temp_anomaly_30d já foi calculada na CTE anterior
        CASE WHEN temp_anomaly_30d BETWEEN -2 AND 2 THEN 1 ELSE 0 END 
    AS is_mild_climate,
    --     CASE 
    --         WHEN temp_max > 35 OR soil_moisture < 20 THEN 'Negative_Shock'
    --         WHEN temp_max BETWEEN 20 AND 28 AND soil_moisture BETWEEN 40 AND 60 THEN 'Positive_Ideal'
    --         ELSE 'Neutral'
    --     END 
    -- AS climate_category

        CASE 
            -- Mantemos o choque negativo como prioridade
            WHEN temp_max > 35 OR soil_moisture < 20 THEN 'Negative_Shock'
            -- Tudo o que não for extremo será nosso grupo de controle "Normal"
            ELSE 'Normal_Weather'
        END 
    AS climate_category

FROM pre_calculations
WINDOW 
    w_region AS (PARTITION BY regiao_foco_clima ORDER BY record_date), 
    w_7d AS (PARTITION BY ticker ORDER BY record_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW);

ALTER TABLE finance.vw_h123_model_features OWNER TO admin_agro;


---


--3
--- View: finance.vw_q1_potencial_antecipacao
--- Objetivo: responder a pergunta 1: "É possível antecipar variações > 2% usando indicadores climáticos?"
---     (potencial de antecipação)


DROP VIEW IF EXISTS finance.vw_q1_potencial_antecipacao CASCADE;

-- 2. Criação da Nova View Unificada
CREATE OR REPLACE VIEW finance.vw_q1_potencial_antecipacao AS
SELECT 
    -- Definição dos Cenários Climáticos (baseado nos Lags para simular antecipação)
        CASE 
            WHEN rain_accum_7d > 50 THEN 'Chuva Acumulada Alta (>50mm)'
            WHEN temp_max > 35 THEN 'Calor Extremo (>35°C)'
            WHEN precipitation_mm = 0 AND soil_moisture < 20 THEN 'Risco Seca'
            ELSE 'Clima Normal/Neutro'
        END 
    AS cenario_climatico,

        COUNT(*) 
    AS total_dias,

    -- Contagem de dias com variação brusca (> 2% para cima ou para baixo)
        SUM(CASE WHEN ABS(pct_change_d1) > 0.02 THEN 1 ELSE 0 END) 
    AS qtd_dias_alta_volatilidade,

    -- A Probabilidade (O "Alpha")
        ROUND(
            (SUM(CASE WHEN ABS(pct_change_d1) > 0.02 THEN 1 ELSE 0 END)::numeric / COUNT(*)) * 100, 
            2
        ) 
    AS prob_movimento_brusco_pct,
    
    -- Média do movimento absoluto (intensidade)
        ROUND(AVG(ABS(pct_change_d1)) * 100, 2) 
    AS media_intensidade_movimento_pct

FROM finance.vw_h123_model_features
-- WHERE ticker = 'ZS=F' -- Soja Futuro
GROUP BY 1
ORDER BY prob_movimento_brusco_pct DESC;


ALTER TABLE finance.vw_q1_potencial_antecipacao OWNER TO admin_agro;


---


---4         
--- View: finance.vw_q2_desafio_rms2
--- Objetivo: Responder a pergunta 2: "O modelo consegue superar uma baseline simples em 10%?"
---         (O Desafio da Baseline (RMSE))


DROP VIEW IF EXISTS finance.vw_q2_desafio_rms2 CASCADE;

-- 2. Criação da Nova View Unificada
CREATE OR REPLACE VIEW finance.vw_q2_desafio_rms2 AS
WITH prediction_baseline AS (
    SELECT 
        ticker,
        record_date,
            close_price 
        AS valor_real,
        -- A baseline usa a média dos 7 dias ANTERIORES para prever hoje
        -- (Lag na ma_7d para evitar vazamento de dados do próprio dia)
            LAG(ma_7d) OVER (PARTITION BY ticker ORDER BY record_date) 
        AS predicao_baseline
    FROM finance.vw_h123_model_features
    ---WHERE ticker = 'ZS=F'
),
calculo_erro AS (
    SELECT
        valor_real,
        predicao_baseline,
        -- Erro Quadrático (Squared Error)
             POWER(valor_real - predicao_baseline, 2) 
        AS erro_quadratico
    FROM prediction_baseline
    WHERE predicao_baseline IS NOT NULL -- Remove os primeiros 7 dias sem média
)
SELECT 
    -- Cálculo do RMSE (Root Mean Squared Error) da Baseline
        SQRT(AVG(erro_quadratico)) 
    AS rmse_baseline,
    
    -- A Meta que seu modelo precisa atingir (10% melhor = 90% do erro)
         SQRT(AVG(erro_quadratico)) * 0.90 
    AS meta_rmse_modelo_agro

FROM calculo_erro;

ALTER TABLE finance.vw_q2_desafio_rms2 OWNER TO admin_agro;



---/View de Comparação para o Looker Studio

--- View: finance.vw_looker_performance_model
--- Objetivo: será utilizada para mostrar informações no looker



DROP VIEW IF EXISTS finance.vw_looker_performance_model CASCADE;

CREATE OR REPLACE VIEW finance.vw_looker_performance_model AS
SELECT 
    p.record_date AS data_predicao,
    p.ticker,
    p.prediction_next_day AS valor_estimado,
    m.close_price AS valor_real_no_dia_seguinte,
    (m.close_price - p.prediction_next_day) AS erro_absoluto,
    ROUND(ABS((m.close_price - p.prediction_next_day) / NULLIF(m.close_price, 0)) * 100, 2) AS mape_real
FROM finance.model_predictions p
LEFT JOIN finance.vw_h123_model_features m 
    ON m.record_date = (p.record_date + INTERVAL '1 day') 
    AND m.ticker = p.ticker;

ALTER TABLE finance.vw_looker_performance_model OWNER TO admin_agro;


---

--- View: finance.vw_looker_agro_dashboard
--- Objetivo: Fornecer uma tabela única e limpa para o Looker Studio com Preços, Câmbio e Clima.

DROP VIEW IF EXISTS finance.vw_looker_agro_dashboard CASCADE;

CREATE OR REPLACE VIEW finance.vw_looker_agro_dashboard AS
SELECT 
    f.record_date AS data,
    f.ticker,
    -- Informações de Preço
    f.close_price AS preco_usd,
    f.preco_original,
    -- Buscamos o preço em BRL da view consolidada já existente
    vc.preco_brl,
    vc.unidade_medida,
    
    -- Câmbio
    ex.taxa_fechamento AS taxa_cambio_usd_brl,

    -- Informações Climáticas da Região de Foco
    f.regiao_foco_clima,
    f.temp_max,
    f.precipitation_mm AS chuva_diaria,
    f.rain_accum_7d AS chuva_acumulada_7d,
    f.soil_moisture AS umidade_solo,
    f.temp_anomaly_30d AS anomalia_termica,

    -- Indicadores de Risco e Volatilidade
    f.volatility_7d,
    f.pct_change_d1 * 100 AS variacao_diaria_pct,
    f.is_extreme_heat,
    f.is_drought_risk,
    f.climate_category AS categoria_clima,

    -- Metas de Performance (Baseline do desafio RMSE)
    (SELECT rmse_baseline FROM finance.vw_q2_desafio_rms2) AS baseline_rmse_referencia,
    (SELECT meta_rmse_modelo_agro FROM finance.vw_q2_desafio_rms2) AS meta_rmse_alvo

FROM finance.vw_h123_model_features f
LEFT JOIN finance.vw_commodities_consolidated vc 
    ON f.record_date = vc.record_date AND f.ticker = vc.ticker
LEFT JOIN finance.exchange_rates ex 
    ON f.record_date = ex.data
ORDER BY f.record_date DESC;

ALTER VIEW finance.vw_looker_agro_dashboard OWNER TO admin_agro;


-- ---
-- GRANT SELECT ON ALL TABLES IN SCHEMA finance TO neondb_owner;
-- GRANT SELECT ON ALL VIEWS IN SCHEMA finance TO neondb_owner;
