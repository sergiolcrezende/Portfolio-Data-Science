""" 
Pacote com todas as funções necessárias para fazer feture engineering
"""

import numpy as np
import pandas as pd

from src.tools import feature_engineering_completa, load_config   # notebook 07_xgb...
# from tools import feature_engineering_completa, load_config   #funciona 00_run_full_test_app.cmd



def fengineering_1_ordenar(df, ordenacao_base_busca):
    """ 
    Ordena a base e cria o campo sales_log
    """
    #🚩

    df = df.sort_values(by=ordenacao_base_busca, ascending=[True, True, True]).reset_index(drop=True)

    # Log Transformation (Suavizar Outliers)
    df['sales_log'] = np.log1p(df['sales'])

    print(f"Shape inicial: {df.shape}")

    return df


def fengineering_2_datas_feriados(df, target_projeto):
    """
    Cria os campos referente a datas
    """

    print("Gerando features completas...")
    df_eng = feature_engineering_completa(df, target_col=target_projeto)

    print("Verificando feriados:")
    print(df_eng[df_eng['is_holiday'] == 1][['date', 'is_holiday']].drop_duplicates().head())

    return df_eng


def fengineering_3_lag1_lag7(df_eng):
    """
    Cria as de um dia e sete dias
    """

    # Cria a diferença bruta
    df_eng['sales_diff_raw'] = df_eng.groupby(['store', 'item'])['sales'].diff(1)

    # Cria o LAG da diferença | Significado: "Quanto as vendas variaram de anteontem para ontem?"
    df_eng['sales_diff_lag1'] = df_eng.groupby(['store', 'item'])['sales_diff_raw'].shift(1)

    # mais histórico | Significado: "Quanto as vendas variaram de anteontem para 7 dias?"
    df_eng['sales_diff_lag7'] = df_eng.groupby(['store', 'item'])['sales_diff_raw'].shift(7)

    # 3. Limpeza  | removendo os NaNs gerados pelos shifts e o campos da diferença entre hoje e ontem. Para evitar Data Leakage
    df_eng = df_eng.drop(['sales_diff_raw'], axis=1)
    df_eng = df_eng.dropna()

    return df_eng


def create_cyclical_features(data, col, max_val):
    """
    Cria ciclo sen/cos com relaçõ a 365 dias
    """
    
    data[f'{col}_sin'] = np.sin(2 * np.pi * data[col] / max_val)
    data[f'{col}_cos'] = np.cos(2 * np.pi * data[col] / max_val)
    return data


def fengineering_4_cyclical(df_eng):
    """
    Cria as colunas seno e coseno para diferencia janeiro/dezembro
    """

    df_eng = create_cyclical_features(df_eng, 'month', 12)
    df_eng = create_cyclical_features(df_eng, 'day_of_week', 7)
    df_eng = create_cyclical_features(df_eng, 'day_of_year', 365)

    print("Features cíclicas criadas.")

    return df_eng


def fengineering_5_lags(df_eng, target):
    """ 
    Gerar as colunas com lags
    """

    # Lags estratégicos:
    # 1-3 dias: Memória curta recente
    # 7, 14, 21, 28: Sazonalidade semanal (muito forte neste dataset)
    # 91: Sazonalidade trimestral (objetivo do projeto)    
    #   91:7=13 ->para calcular semana inteira e cair no dia da semana certo (domingo) |  90:7=12,85 (nai na segunda)
    #   Estamos usando uma janela trimestral ajustada para sazonalidade semanal para garantir que não comparamos dias de alto fluxo com dias mortos.

    lags = [1, 2, 3, 7, 14, 21, 28, 91]   
    
    print("Gerando Lags")
    for lag in lags:
        df_eng[f'lag_{lag}'] = df_eng.groupby(['store', 'item'])[target].shift(lag)

    return df_eng


def fengineering_6_rolling(df_eng, target):
    """
    Gerando colunas de janelas no tempo
    """

    windows = [7, 28, 91]

    print("Gerando Rolling Windows...")
    for window in windows:
        # Usamos shift(1) para evitar Data Leakage (vazamento do futuro)
        # Groupby garante que o cálculo é isolado por loja/item
        
        # Média Móvel (Tendência)
        df_eng[f'rolling_mean_{window}'] = df_eng.groupby(['store', 'item'])[target].transform(
            lambda x: x.shift(1).rolling(window=window).mean()
        )
        
        # Desvio Padrão (Volatilidade)
        df_eng[f'rolling_std_{window}'] = df_eng.groupby(['store', 'item'])[target].transform(
            lambda x: x.shift(1).rolling(window=window).std()
        )

    return df_eng



def fengineering_7_final(df_eng, df):
    """ 
    Finalizando todos os ajustes na baseline
    """

    # Como usamos um Lag de 90 dias, os primeiros 3 meses de dados serão NaNs. | removê-los para o treino.
    df_final = df_eng.dropna()

    print(f"Shape Original: {df.shape}")
    print(f"Shape Final (Feature Eng): {df_final.shape}")

    # Conferência Visual
    cols_check = ['date', 'sales', 'lag_1', 'lag_91', 'is_holiday', 'month_sin']
    display(df_final[cols_check].head())

    return df_final


def fengineering_8_gerar_arquivo(df_final, output_path):
    """
    Gera o arquivo final no processo de feature engineering
    """

    # Salvar 
    df_final.to_csv(output_path, index=False)

    print(f"Dataset enriquecido salvo em: {output_path}")
