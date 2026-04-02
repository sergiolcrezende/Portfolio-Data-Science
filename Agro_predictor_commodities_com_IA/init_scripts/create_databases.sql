-- Criação dos bancos de dados separados
CREATE DATABASE n8n_db;
CREATE DATABASE mlflow_db;
CREATE DATABASE agro_dw;

-- Garantir privilégios (caso crie usuários separados no futuro)
GRANT ALL PRIVILEGES ON DATABASE n8n_db TO admin_agro;
GRANT ALL PRIVILEGES ON DATABASE mlflow_db TO admin_agro;
GRANT ALL PRIVILEGES ON DATABASE agro_dw TO admin_agro;


-- Conectar no agro_dw para criar as tabelas de negócio
-- O comando \c troca de banco dentro do script de inicialização
\c agro_dw;

-- Criação dos Schemas
CREATE SCHEMA IF NOT EXISTS finance;
CREATE SCHEMA IF NOT EXISTS weather;


-- Tabelas 

-- Tabela de Mercado
CREATE TABLE IF NOT EXISTS finance.market_data (
    record_date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    open_price NUMERIC(15, 4),
    high_price NUMERIC(15, 4),
    low_price NUMERIC(15, 4),
    close_price NUMERIC(15, 4),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (record_date, ticker)
); 
CREATE INDEX idx_market_date ON finance.market_data(record_date);
CREATE INDEX idx_market_ticker ON finance.market_data(ticker);


-- Metadados
CREATE TABLE IF NOT EXISTS finance.commodities_metadata (
    ticker VARCHAR(20) PRIMARY KEY,
    commodity_name VARCHAR(50),
    related_region_weather VARCHAR(50),
    currency VARCHAR(5) DEFAULT 'BRL',
    unit VARCHAR(20)
);


-- Tabela de Clima
CREATE TABLE IF NOT EXISTS weather.climate_data (
    record_date DATE NOT NULL,
    region_name VARCHAR(50) NOT NULL,
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    temp_max NUMERIC(5, 2),
    temp_min NUMERIC(5, 2),
    precipitation_mm NUMERIC(6, 2),
    soil_moisture NUMERIC(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (record_date, region_name)
);
CREATE INDEX idx_weather_date ON weather.climate_data(record_date);


-- Table: finance.exchange_rates

-- DROP TABLE IF EXISTS finance.exchange_rates;

CREATE TABLE IF NOT EXISTS finance.exchange_rates
(
    data date NOT NULL,
    currency_pair character varying(10) COLLATE pg_catalog."default" DEFAULT 'USD/BRL'::character varying,
    taxa_fechamento numeric(10,4) NOT NULL,
    CONSTRAINT exchange_rates_pkey PRIMARY KEY (data)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS finance.exchange_rates
    OWNER to admin_agro;



-- tabelas criadas para atender a VIEW finance.vw_model_features
-- Criação de um esquema de configuração (opcional, ou use 'finance' ou 'public')
CREATE TABLE IF NOT EXISTS finance.config_commodity_clima (
    ticker VARCHAR(50) PRIMARY KEY,
    commodity_name VARCHAR(100), -- Opcional, apenas para documentação
    cidade_foco_clima VARCHAR(100) NOT NULL
);


-- Inserindo os dados (Aqui você define as regras sem mexer na View)
INSERT INTO finance.config_commodity_clima (ticker, commodity_name, cidade_foco_clima)
VALUES 
    ('ZS=F', 'Soja', 'Sorriso'),
    ('ZC=F', 'Milho', 'Rio Verde'),  -- Exemplo: Milho foca em Rio Verde/GO
    ('KC=F', 'Café', 'Varginha'),    -- Exemplo: Café foca em Varginha/MG
    ('CT=F', 'Algodão', 'Barreiras'); -- Exemplo: Algodão foca na Bahia

-- quando surgir outra commodities basta incluir na Tabela.
-- exemplo: cana de açucar
--       INSERT INTO finance.config_commodity_clima VALUES ('SB=F', 'Acucar', 'Ribeirao Preto');




---/criar o repositório das predições:

DROP VIEW IF EXISTS finance.model_predictions CASCADE;

CREATE TABLE finance.model_predictions (
    id SERIAL PRIMARY KEY,
    record_date DATE NOT NULL,
    ticker VARCHAR(20),
    close_price_on_day NUMERIC, -- Preço do dia da predição
    prediction_next_day NUMERIC, -- O valor que o modelo estimou
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE finance.model_predictions OWNER TO admin_agro;

 
  

---/Criar a Tabela de Logs no Banco

DROP VIEW IF EXISTS finance.process_logs CASCADE;

CREATE TABLE finance.process_logs (
    id SERIAL PRIMARY KEY,
    process_name VARCHAR(50), -- 'ETL' ou 'INFERENCE'
    status VARCHAR(20),      -- 'SUCCESS' ou 'ERROR'
    error_message TEXT,
    execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE finance.process_logs OWNER TO admin_agro;



---/Deepchecks
-- Criando uma tabela com o "retrato" dos dados usados no treino
-- Isso garante que o Deepchecks sempre tenha uma base estável para comparar o Drift
CREATE TABLE finance.train_data_baseline AS
SELECT 
    m.record_date,
    m.ticker,
    m.close_price,
    m.volume,
    w.temp_max,
    w.temp_min,
    w.precipitation_mm,
    w.soil_moisture,
    -- Aqui incluímos o alvo histórico para o Deepchecks validar performance se necessário
    LEAD(m.close_price) OVER (PARTITION BY m.ticker ORDER BY m.record_date) as target_next_day
FROM finance.market_data m
JOIN finance.config_commodity_clima c ON m.ticker = c.ticker
JOIN weather.climate_data w ON m.record_date = w.record_date 
    AND c.cidade_foco_clima = w.region_name
WHERE m.record_date < '2026-01-01'; -- Exemplo: Data limite do seu treino original

ALTER TABLE finance.train_data_baseline OWNER TO admin_agro;
