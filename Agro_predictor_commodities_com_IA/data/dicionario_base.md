base postgres

| Campo | Descrição |
| :--- | :--- |
| **record_date** | Data de referência do registro (formato YYYY-MM-DD). |
| **ticker** | Código de identificação da commodity no mercado financeiro (ex: milho, soja). |
| **close_price** | Preço de fechamento da commodity em Reais (BRL) na data do registro. |
| **regiao_foco_clima** | Cidade ou região principal utilizada para a coleta dos dados meteorológicos. |
| **pct_change_d1** | Variação percentual do preço em relação ao dia anterior (D-1). |
| **ma_7d** | Média móvel simples (SMA) do preço de fechamento dos últimos 7 dias. |
| **volatility_7d** | Desvio padrão do preço nos últimos 7 dias, indicando a volatilidade do ativo no período. |
| **temp_max** | Temperatura máxima registrada na região na data do registro. |
| **precipitation_mm** | Volume de chuva acumulado em milímetros no dia. |
| **rain_lag_3** | Volume de chuva registrado há exatamente 3 dias em relação à data atual. |
| **rain_lag_5** | Volume de chuva registrado há exatamente 5 dias em relação à data atual. |
| **temp_lag_3** | Temperatura máxima registrada há exatamente 3 dias em relação à data atual. |
| **rain_accum_7d** | Soma total da precipitação acumulada nos últimos 7 dias (janela móvel). |
| **is_extreme_heat** | Flag binária: 1 se a temperatura máxima ultrapassou 35°C, caso contrário 0. |
| **is_drought_risk** | Flag binária: 1 se não houve chuva e a umidade do solo estiver abaixo de 20%, caso contrário 0. |
| **day_of_year** | Dia sequencial do ano (1 a 365/366), útil para análises de sazonalidade. |
| **month_num** | Número do mês da extração (1 a 12). |
| **temp_anomaly_30d** | Diferença entre a temperatura atual e a média histórica dos 30 dias anteriores. |
| **soil_moisture** | Nível de umidade do solo registrado na região. |
| **is_heavy_rain_lag3** | Flag binária: 1 se houve chuva acima de 10mm há 3 dias, caso contrário 0. |
| **price_intensity** | Valor absoluto da variação percentual, medindo a magnitude do movimento de preço. |
| **is_mild_climate** | Flag binária: 1 se a anomalia térmica dos últimos 30 dias ficou entre -2 e 2 (estabilidade). |
| **climate_category** | Categoria qualitativa: 'Negative_Shock' (extremo), 'Positive_Ideal' (ótimo) ou 'Neutral'. |









