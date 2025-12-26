import numpy as np
import pandas as pd
import holidays
import yaml
import os

from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime

METRICS_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data/metrics', 'metrics_history.csv')


def process_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera features temporais e de feriados de forma robusta.
    Corrige problemas de tipagem (Timestamp vs Date) e normalização.
    """
    df = df.copy()

    # 1. Padronização da Data (com .normalize para remover horas/minutos)
    col_date = 'date' if 'date' in df.columns else 'ds'
    
    if col_date in df.columns:
        df['date'] = pd.to_datetime(df[col_date])
    elif all(c in df.columns for c in ['year', 'month', 'day']):
        df['date'] = pd.to_datetime(df[['year', 'month', 'day']])
    
    # Remove componente de hora (essencial para merge de feriados funcionar)
    df['date'] = df['date'].dt.normalize()
    
    # Ordenação obrigatória para merge_asof
    df = df.sort_values('date').reset_index(drop=True)

    # 2. Features Básicas
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day'] = df['date'].dt.day
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_name'] = df['date'].dt.day_name()
    df['day_of_year'] = df['date'].dt.dayofyear
    df['is_weekend'] = df['day_of_week'] >= 5
    df['is_payday'] = df['day'].apply(lambda x: 1 if x <= 10 else 0)

    # 3. Preparação dos Feriados
    min_ano = df['year'].min()
    max_ano = df['year'].max()
    # Garante feriados do ano atual e próximo
    # feriados_br = holidays.BR(years=range(min_ano, max_ano + 2), expand=True)
    feriados_br = holidays.BR(years=range(int(min_ano), int(max_ano) + 2), expand=True)
    
    # Cria DF auxiliar limpo
    feriados_df = pd.DataFrame(list(feriados_br.items()), columns=['date_holiday', 'holiday_name'])
    feriados_df['date_holiday'] = pd.to_datetime(feriados_df['date_holiday']).dt.normalize()
    feriados_df = feriados_df.sort_values('date_holiday').drop_duplicates(subset=['date_holiday'])

    # 4. Feature: Nome do Feriado (Correção do Bug .date())
    # Convertemos a coluna date para .dt.date para bater com as chaves do dict holidays
    df['holiday_name'] = df['date'].apply(lambda x: feriados_br.get(x.date(), 'Dia Normal'))
    df['is_holiday'] = (df['holiday_name'] != 'Dia Normal').astype(int)

    # 5. Feature: Dias até o próximo feriado (Lógica Merge AsOf)
    # Procura o PRIMEIRO feriado onde date_holiday >= date (direction='forward')
    df_merged = pd.merge_asof(
        df[['date']], # Usa apenas a coluna date para economizar memória no merge
        feriados_df[['date_holiday']],
        left_on='date', 
        right_on='date_holiday',
        direction='forward', 
        allow_exact_matches=True
    )
    
    # Cálculo seguro: Se não achou feriado (fim dos tempos), preenche com NaN depois trata
    df['days_until_holiday'] = (df_merged['date_holiday'] - df['date']).dt.days
    
    # Se não houver feriado futuro próximo (ex: dados muito no futuro), assume 365
    df['days_until_holiday'] = df['days_until_holiday'].fillna(365).astype(int)

    # 6. Features Cíclicas
    def create_cyclical(data, col, max_val):
        data[f'{col}_sin'] = np.sin(2 * np.pi * data[col] / max_val)
        data[f'{col}_cos'] = np.cos(2 * np.pi * data[col] / max_val)
        return data

    df = create_cyclical(df, 'month', 12)
    df = create_cyclical(df, 'day_of_week', 7)
    df = create_cyclical(df, 'day_of_year', 365)

    return df


def load_config(config_path='../config.yaml'):
    """
    Função para carregar a configuração
    """

    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


def config_default():

    config = load_config()
    ORDENACAO_BASE_BUSCA = config['ordenacao_base_busca']
    TARGET_PROJETO = config["target_projeto"]
    PATH_RAW = config['paths']['valida_base_raw']     # Ex: ../data/raw/test1.csv
    EXCLUIR_COLUNA_MODELO = config['excluir_colunas_modelo']
    SPLIT_DATE = config['dates']['split_date']

    print(f'Ordenação das colunas: {ORDENACAO_BASE_BUSCA}')

    return (ORDENACAO_BASE_BUSCA, 
            TARGET_PROJETO, 
            PATH_RAW, 
            EXCLUIR_COLUNA_MODELO, 
            SPLIT_DATE
        )


def validar_estrutura_estrita(df, caminho_config='../config.yaml'):
    """
    Validar estrutura das colunas da base de origem raw
    """

    # 1. Carregar Configuração
    try:
        with open(caminho_config, 'r') as file:
            config = yaml.safe_load(file)
            colunas_esperadas = config['colunas_base_origem_raw']
    except Exception as e:
            return (f"🔴CRÍTICO: Não foi possível ler o arquivo de configuração. Erro: {e}")

    # 2. Obter colunas do DataFrame
    colunas_recebidas = df.columns.tolist()

    # 3. Comparação Rigorosa (Conteúdo + Ordem + Case Sensitive)
    if colunas_recebidas != colunas_esperadas:
        return (f"🔴Erro na validação das colunas: esperadas: {colunas_esperadas} vs recebidas:{colunas_recebidas} ")
    else:
        return ("Validação OK: Estrutura correta.")


def feature_engineering_completa(df, target_col='sales_log'):
    """
    Pipeline COMPLETO (Atualizado para XGBoost):
    1. Chama process_date_features (Feriados, Datas)
    2. Calcula Diff Lags (Tendência de curto prazo) - NOVO
    3. Calcula Lags e Rolling Windows (Médias Móveis)
    """
    
    # 1. Aplica a função de datas (Features Temporais e Cíclicas)
    df = process_date_features(df)
    
    # Ordenação OBRIGATÓRIA para cálculos de tempo (shift/diff)
    df = df.sort_values(['store', 'item', 'date'])

    # --- NOVO: Features de Diferença (Requisito do XGBoost) ---
    # Cria uma coluna temporária da diferença (vendas hoje - vendas ontem)
    # Usamos f string para ser dinâmico (funcionar com 'sales' ou 'sales_log')
    col_diff = f'{target_col}_diff_raw'
    df[col_diff] = df.groupby(['store', 'item'])[target_col].diff(1)
    
    # Cria os Lags dessa diferença (Diff Lag 1 e Diff Lag 7)
    # Isso captura a "aceleração" ou mudança de tendência
    df[f'{target_col}_diff_lag1'] = df.groupby(['store', 'item'])[col_diff].shift(1)
    df[f'{target_col}_diff_lag7'] = df.groupby(['store', 'item'])[col_diff].shift(7)
    
    # Limpeza: remove a coluna auxiliar e preenche NaN dessas features específicas com 0
    # (Importante pois a primeira linha de cada loja sempre será NaN)
    df = df.drop(columns=[col_diff])
    cols_diff_lags = [f'{target_col}_diff_lag1', f'{target_col}_diff_lag7']
    df[cols_diff_lags] = df[cols_diff_lags].fillna(0)
    # ----------------------------------------------------------
    
    # Configurações de Janelas
    lags = [1, 2, 3, 7, 14, 21, 28, 91]
    windows = [7, 28, 91]
    
    # 2. Criar Lags (Atrasos de Venda)
    for lag in lags:
        df[f'lag_{lag}'] = df.groupby(['store', 'item'])[target_col].shift(lag)
        
    # 3. Criar Rolling Windows (Médias Móveis)
    for window in windows:
        grouped = df.groupby(['store', 'item'])[target_col]
        
        # Média Móvel
        df[f'rolling_mean_{window}'] = grouped.transform(
            lambda x: x.shift(1).rolling(window=window).mean()
        )
        
        # Desvio Padrão Móvel
        df[f'rolling_std_{window}'] = grouped.transform(
            lambda x: x.shift(1).rolling(window=window).std()
        )
        
    return df


def feature_engineering_completa_old(df, target_col='sales_log'):
    """
    Pipeline COMPLETO:
    1. Chama process_date_features (Feriados, Datas)
    2. Calcula Lags e Rolling Windows (Médias Móveis)
    
    Garante que Treino e Produção rodem exatamente a mesma matemática.
    """
    
    # Aplica a função de datas que já existia
    df = process_date_features(df)
    
    # Configurações de Janelas (Baseadas no Notebook 02)
    lags = [1, 2, 3, 7, 14, 21, 28, 91]
    windows = [7, 28, 91]
    
    # Ordenação OBRIGATÓRIA para cálculos de tempo
    #🚩
    df = df.sort_values(['store', 'item', 'date'])
    
    # Criar Lags (Atrasos)
    # Groupby garante que não misturamos dados de lojas/itens diferentes
    for lag in lags:
        df[f'lag_{lag}'] = df.groupby(['store', 'item'])[target_col].shift(lag)
        
    # Criar Rolling Windows (Médias Móveis)
    # shift(1) é essencial para evitar Data Leakage
    for window in windows:
        grouped = df.groupby(['store', 'item'])[target_col]
        
        # Média
        df[f'rolling_mean_{window}'] = grouped.transform(
            lambda x: x.shift(1).rolling(window=window).mean()
        )
        
        # Desvio Padrão
        df[f'rolling_std_{window}'] = grouped.transform(
            lambda x: x.shift(1).rolling(window=window).std()
        )
        
    return df


def avaliar_modelo(y_real_log, y_pred_log, nome_modelo="Modelo"):
    """
    Calcula métricas revertendo o LOG para a escala REAL de vendas.
    Padroniza a saída para Treino, Validação e Teste.
    """
    
    # Converter inputs para array numpy para evitar erros de índice do pandas
    y_real_log = np.array(y_real_log)
    y_pred_log = np.array(y_pred_log)

    # Reverter Log (expm1) para voltar à escala original
    y_real = np.expm1(y_real_log)
    y_pred = np.expm1(y_pred_log)
    
    # Trava de segurança (sem vendas negativas)
    y_pred = np.maximum(y_pred, 0)
    
    # Cálculo das Métricas
    mae = mean_absolute_error(y_real, y_pred)
    rmse = np.sqrt(mean_squared_error(y_real, y_pred))
    r2 = r2_score(y_real, y_pred)
    
    # WAPE: Erro absoluto total / Vendas totais
    # Evita divisão por zero se a soma for 0
    total_sales = np.sum(y_real)
    if total_sales == 0:
        wape = np.nan
    else:
        wape = np.sum(np.abs(y_real - y_pred)) / total_sales * 100
        
    # MAPE: Mean Absolute Percentage Error
    # Mascara valores onde y_real é 0 para evitar divisão por zero
    mask = y_real != 0
    if np.any(mask):
        mape = np.mean(np.abs((y_real[mask] - y_pred[mask]) / y_real[mask])) * 100
    else:
        mape = 0.0
    
    # Retorna dicionário caso queira logar em MLFlow ou salvar depois
    return {
        'mae': mae, 
        'rmse': rmse, 
        'wape': wape, 
        'mape': mape, 
        'r2': r2
    }


def registrar_metricas(modelo_nome, mae, rmse, wape, mape, r2=0.0, notebook="N/A", etapa="N/A"):
    """
    1. Exibe o relatório visual padronizado.
    2. Salva as métricas em um arquivo CSV histórico (append).
    """
    
    # Visualização Padronizada
    print(f"--- Performance: {modelo_nome} ---")
    print(f"MAE:  {mae:.2f} (Erro médio em unidades)")
    print(f"RMSE: {rmse:.2f} (Penaliza erros grandes)")
    print(f"WAPE: {wape:.2f}% (Erro percentual ponderado)")
    print(f"MAPE: {mape:.2f}% (Erro médio absoluto)")
    print(f"R²:   {r2:.4f} (Aderência/Variância explicada)")
    print("-" * 30)

    # Preparação dos Dados
    novos_dados = {
        'Data': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Notebook': notebook,
        'Etapa': etapa, # Treino, Validação ou Teste
        'Modelo': modelo_nome,
        'MAE': round(mae, 2),
        'RMSE': round(rmse, 2),
        'WAPE (%)': round(wape, 2),
        'MAPE (%)': round(mape, 2),
        'R2': round(r2, 4)
    }

    # Gravação no Arquivo (Append)
    # Verifica se o arquivo já existe
    if os.path.exists(METRICS_FILE_PATH):
        df_historico = pd.read_csv(METRICS_FILE_PATH)
        # Concatena o novo registro
        df_novo = pd.DataFrame([novos_dados])
        df_final = pd.concat([df_historico, df_novo], ignore_index=True)
    else:
        # Cria o arquivo se não existir
        df_final = pd.DataFrame([novos_dados])
    
    # Salva
    try:
        df_final.to_csv(METRICS_FILE_PATH, index=False)
        print(f"✅ Métricas registradas com sucesso em: {METRICS_FILE_PATH}")
    except PermissionError:
        print(f"❌ ERRO: Feche o arquivo CSV/Excel para salvar os dados!")


def ver_comparativo():
    """
    Lê o arquivo de histórico e exibe a tabela ordenada pela melhor performance (menor WAPE).
    """
    if os.path.exists(METRICS_FILE_PATH):
        df = pd.read_csv(METRICS_FILE_PATH)
        # Ordena para mostrar os mais recentes primeiro ou melhores primeiro
        # Aqui ordenando por WAPE (menor é melhor)
        return df.sort_values(by='WAPE (%)', ascending=True)
    else:
        print("Nenhum histórico de métricas encontrado ainda.")
        return None
    

def verificar_features(lista_features, lista_drop):
    """
    Verifica se alguma coluna da lista_drop está presente na lista_features.
    """

    # Identifica colunas que estão nas duas listas ao mesmo tempo
    conflitos = [col for col in lista_drop if col in lista_features]

    if conflitos:
        return (f"🔴 PROBLEMA: As seguintes colunas de drop ainda estão nas features: {conflitos}")
    else:
        return ("✅ Tudo ok. Nenhuma coluna de drop está na lista de features.")
    

def excluir_colunas_modelo(df, cols_to_drop):
    """
    Exclui as colunas que não podem ser utilizadas no calculo de modelo. Afeta na métrica
    """
    
    df = df.drop(columns=cols_to_drop, errors='ignore')
    return df


def previsao_venda_total(forecast_7d, rmse, sample_store=1, sample_item=1, lead_time=7, z_score=1.65, current_stock=10):
    """
    Faz a previsão de venda 7 dias
        forecast_7d = analise dos últimos 7 dias
        rmse = será o RMSE do modelo como proxy para volatilidade do erro
        sample_store = loja
        sample_item = item
        lead_time = dias previsão
        z_score = faixa de segurança  (comum no varejo)
        current_stock = produto em estoque
    """
        
    total_predicted_demand = sum(forecast_7d)

    # Cálculo do Estoque de Segurança (Safety Stock)
    # Fórmula Simplificada: Z * Desvio_Erro * Raiz(Tempo)
    # Z = 1.65 (para 95% de nível de serviço - só faltar produto em 5% dos casos)
    z_score = z_score       # 1.65
    lead_time = lead_time   # 7 # dias
    error_std = rmse        # Usando o RMSE do modelo como proxy para volatilidade do erro

    safety_stock = z_score * error_std * np.sqrt(lead_time)

    # Estoque Atual (Simulado)
    current_stock = current_stock        # supondo 10 unidades na prateleira

    # Pedido Final
    compra_sugerida = total_predicted_demand + safety_stock - current_stock

    print(f"--- Relatório de Reposição (Loja {sample_store} - Item {sample_item}) ---")
    print(f"1. Previsão de Vendas (7 dias): {total_predicted_demand:.2f} unidades")
    print(f"2. Estoque de Segurança (95%):  {safety_stock:.2f} unidades")
    print(f"3. Estoque Atual na Loja:       {current_stock} unidades")
    print(f"--------------------------------------------------")
    print(f"✅ SUGESTÃO DE COMPRA:          {compra_sugerida:.0f} unidades")
    print(f"--------------------------------------------------")
    print("Nota: Se comprar menos que isso, risco de Stockout > 5%.")
    print("      Se comprar muito mais, risco de custo de estocagem (Overstock).")


def recursive_forecast_7days_OLD(model, df_base, store, item, start_date, features):    #vendo .log
    """_summary_

    Args:
        model (_type_): _description_
        df_base (_type_): _description_
        store (_type_): _description_
        item (_type_): _description_
        start_date (_type_): _description_
        df (_type_): _description_
        features (_type_): _description_

    Returns:
        _type_: _description_
    """

    # Pegamos os dados históricos necessários para construir os lags
    # Precisamos de pelo menos 91 dias para trás para calcular todas as features
    history = df_base[(df_base['store'] == store) & 
                      (df_base['item'] == item) & 
                      (df_base['date'] <= start_date)].copy()
    
    predictions = []
    
    # Loop para os próximos 7 dias
    current_date = start_date
    
    for i in range(1, 8):
        next_date = current_date + pd.Timedelta(days=1)
        
        # 1. Construir a linha do 'next_date' baseada no histórico recente
        # Nota: Em um script de produção, recriaríamos as features aqui.
        # Como simplificação para o portfolio, vamos pegar a linha real da validação (se existir) 
        # mas substituindo os Lags pelas nossas previsões anteriores.
        
        # Pega a estrutura da feature do dataset original (Validation)
        # df = df_base
        # next_row = df[(df['store'] == store) & 
        #               (df['item'] == item) & 
        #               (df['date'] == next_date)].copy()
        
        next_row = df_base[(df_base['store'] == store) & 
                      (df_base['item'] == item) & 
                      (df_base['date'] == next_date)].copy()

        if next_row.empty:
            break # Acabou o dataset
            
        # --- TRUQUE RECURSIVO ---
        # Se tivermos previsões passadas (i > 1), precisamos atualizar o lag_1 na row atual
        if i > 1:
            # O lag_1 de hoje é a previsão de ontem
            last_pred_log = np.log1p(predictions[-1])
            next_row['lag_1'] = last_pred_log
            # (Idealmente atualizaríamos rolling means também, mas lag_1 é o mais forte)
        
        # Prever
        X_input = next_row[features]
        pred_log = model.predict(X_input)[0]
        pred_real = np.expm1(pred_log)
        
        predictions.append(pred_real)
        current_date = next_date
        
    return predictions


def recursive_forecast_7days(model, df_base, store, item, start_date, features):
    # Copia inicial do histórico
    history = df_base[(df_base['store'] == store) & 
                      (df_base['item'] == item) & 
                      (df_base['date'] <= start_date)].copy()
    
    predictions = []
    current_date = start_date
    
    for i in range(1, 8):
        next_date = current_date + pd.Timedelta(days=1)
        
        # Pega a linha do DataFrame base (CSV) correspondente à data futura
        next_row = df_base[(df_base['store'] == store) & 
                           (df_base['item'] == item) & 
                           (df_base['date'] == next_date)].copy()

        if next_row.empty:
            print(f"Alerta: Sem dados para a data {next_date}")
            break 
            
        # --- CORREÇÃO DO TRUQUE RECURSIVO ---
        if i > 1:
            # Pegamos a última previsão REAL (não o log)
            last_pred_real = predictions[-1]
            
            # Atualizamos o lag_1 com o valor REAL
            # IMPORTANTE: Assumindo que sua feature 'lag_1' foi treinada com valores reais
            next_row['lag_1'] = last_pred_real
            
            # Se você tiver 'sales_diff_lag1', ele também precisa ser atualizado, 
            # mas como você removeu essas colunas do treino, não precisamos mexer nelas.
        
        # Prever
        # Garante que as colunas estejam na mesma ordem do treino
        X_input = next_row[features]
        
        pred_log = model.predict(X_input)[0]
        pred_real = np.expm1(pred_log) # Converte de Log para Real
        
        # Trava de segurança: Venda não pode ser negativa
        pred_real = max(0, pred_real)
        
        predictions.append(pred_real)
        current_date = next_date
        
    return predictions

