#91_monitor_deepchecks_producao.py
#executar: ./91_run_monitor_prod.sh (git bash)  -via vscode terá erro com relação src.tools

import pandas as pd
import numpy as np  # <--- ADICIONADO (Necessário para np.log1p)
import json
import joblib
import os
import sys

# --- CONFIGURAÇÃO DE CAMINHOS ---
# Ajuste isso para garantir que ele encontre o módulo 'src'
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) # Sobe um nível para a raiz do projeto
sys.path.append(os.path.join(project_root, 'src'))

# Importa a mesma engenharia usada na API
from tools import feature_engineering_completa

from deepchecks.tabular import Dataset
from deepchecks.tabular.suites import full_suite

print(f'19-diretorio raiz: {project_root}\n')

# --- CAMINHOS DOS ARQUIVOS ---
TRAIN_PATH = os.path.join(project_root, 'data', 'raw', 'train.csv')
LOG_PATH = os.path.join(project_root, 'logs', '00_resultado_previsoes_vendas.csv')
REPORT_PATH = os.path.join(project_root, 'retail-demand-forecasting', 'data', 'reports', 'relatorio_monitoramento.html')

def run_monitor():
    print("1. Carregando dados de REFERÊNCIA (Treino)...")
    try:
        df_ref = pd.read_csv(TRAIN_PATH)
        df_ref['date'] = pd.to_datetime(df_ref['date'])
        
        # --- CORREÇÃO IGUAL AO APP.PY ---
        # A engenharia de features precisa da coluna 'sales_log' para calcular os lags.
        # No app.py isso é feito no startup. Aqui precisamos repetir.
        if 'sales' in df_ref.columns:
            print("   Criando coluna 'sales_log' (np.log1p)...")
            df_ref['sales_log'] = np.log1p(df_ref['sales'])
        
        # Garante a ordenação correta para que os Lags (shift) funcionem direito
        df_ref = df_ref.sort_values(['store', 'item', 'date'])
        # -------------------------------

        # --- Aplicar Feature Engineering no Treino ---
        print("   Aplicando engenharia de features no dataset de treino...")
        df_ref = feature_engineering_completa(df_ref)
        
        # Removemos linhas com NaN gerados pelos Lags (início da série)
        df_ref = df_ref.dropna()
        
    except FileNotFoundError:
        print(f"ERRO: Arquivo de treino não encontrado em {TRAIN_PATH}")
        return

    print("2. Carregando dados ATUAIS (Logs de Produção)...")
    if not os.path.exists(LOG_PATH):
        print("Ainda não há logs de produção para monitorar.")
        return
        
    try:
        df_curr = pd.read_csv(LOG_PATH)
        df_curr['date'] = pd.to_datetime(df_curr['date'])
    except pd.errors.ParserError:
        print("ERRO: O arquivo de log está corrompido ou com formato misto. Rode o app.py novamente para recriá-lo.")
        return

    print(f"   Logs carregados: {len(df_curr)} linhas.")

    # 3. ALINHAMENTO DE COLUNAS
    # Removemos colunas exclusivas de gestão ou targets que não queremos comparar como feature
    # Nota: 'sales_log' é criado para gerar features, mas geralmente não monitoramos o target bruto como feature
    cols_to_drop = ['estoque_atual', 'pedido_final', 'timestamp_captura', 'sales', 'y_pred', 'sales_log']
    
    # Mantemos apenas as colunas que existem em ambos (Features + Identificadores)
    features_ref = set(df_ref.columns)
    features_curr = set(df_curr.columns)
    
    # Calculamos as colunas comuns
    common_cols = list(features_ref & features_curr)
    # Removemos as colunas indesejadas da lista final
    common_cols = [c for c in common_cols if c not in cols_to_drop]
    
    print(f"   Monitorando {len(common_cols)} colunas (Features).")

    # Filtramos os dataframes
    df_ref_clean = df_ref[common_cols].copy()
    df_curr_clean = df_curr[common_cols].copy()

    # 4. CRIANDO DATASETS DO DEEPCHECKS
    cat_features = ['store', 'item'] if 'store' in common_cols else []
    
    ds_ref = Dataset(df_ref_clean, cat_features=cat_features, index_name='date')
    ds_curr = Dataset(df_curr_clean, cat_features=cat_features, index_name='date')

    # 5. RODANDO A SUITE DE TESTES
    print("3. Executando Deepchecks Full Suite...")
    suite = full_suite()
    

    # --- CORREÇÃO AQUI ---
    # A linha abaixo causava o erro. Pode removê-la. 
    # O Deepchecks vai pular checks de modelo automaticamente pois não passamos o 'model' no .run()
    # suite = suite.remove_condition("Model Performance")  <-- REMOVER OU COMENTAR
    
    # Executa a suite apenas comparando os dados (Treino vs Produção)
    result = suite.run(train_dataset=ds_ref, test_dataset=ds_curr)

    # # Removemos verificações de performance do modelo pois não estamos passando (label)
    # suite = suite.remove_condition("Model Performance") 
    
    # result = suite.run(train_dataset=ds_ref, test_dataset=ds_curr)

    # 6. SALVANDO RELATÓRIO
    print(f"4. Salvando relatório em: {REPORT_PATH}")
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    result.save_as_html(REPORT_PATH)
    print("   [SUCESSO] Monitoramento concluído!")

if __name__ == "__main__":
    run_monitor()
