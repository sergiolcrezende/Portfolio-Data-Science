# 90_monitor_deepchecks_pre_implantacao.py
# executar: ./90_run_monitor_pre.sh (git bash)  -via vscode terá erro com relação src.tools

import pandas as pd
import numpy as np
import os
import sys

# --- CONFIGURAÇÃO DE CAMINHOS ---
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
project_root = os.path.abspath(os.path.join(os.getcwd(), '..'))

print(f'24-diretorio raiz: {project_root} \n')

from src.tools import feature_engineering_completa
from deepchecks.tabular import Dataset
from deepchecks.tabular.suites import full_suite

# CAMINHOS DOS ARQUIVOS
TRAIN_PATH = os.path.join(project_root, 'data', 'raw', 'train.csv')
LOG_PATH = os.path.join(project_root, 'logs', '00_resultado_previsoes_vendas.csv')
REPORT_PATH = os.path.join(project_root, 'data', 'reports', 'relatorio_pre_implantacao.html') 


def run_pre_deployment_check():
    print("=== INICIANDO VERIFICAÇÃO PRÉ-IMPLANTAÇÃO (Deepchecks) ===")

    # 1. Carregar e Preparar REFERÊNCIA (Treino)
    print("1. Carregando dados de REFERÊNCIA (Treino)...")
    if not os.path.exists(TRAIN_PATH):
        print(f"   [ERRO] Arquivo de treino não encontrado em: {TRAIN_PATH}")
        sys.exit(1)

    df_ref = pd.read_csv(TRAIN_PATH)
    df_ref['date'] = pd.to_datetime(df_ref['date'])
    
    # Cria sales_log se não existir (necessário para feature engineering)
    if 'sales' in df_ref.columns:
        df_ref['sales_log'] = np.log1p(df_ref['sales'])

    # APLICAR ENGENHARIA DE FEATURES
    print("   Aplicando engenharia de features no dataset de treino...")
    try:
        df_ref = feature_engineering_completa(df_ref)
        df_ref = df_ref.dropna() # Remove NaNs gerados por lags iniciais
    except Exception as e:
        print(f"   [ERRO CRÍTICO] Falha na engenharia de features: {e}")
        sys.exit(1)

    # 2. Carregar e Preparar ATUAL (Logs de Teste/Produção)
    print("2. Carregando dados ATUAIS (Logs da API)...")
    if not os.path.exists(LOG_PATH):
        print(f"   [AVISO] Arquivo de log não encontrado em: {LOG_PATH}")
        print("   Dica: Rode a API e faça algumas requisições (/predict ou /recommend) para gerar dados.")
        sys.exit(1)

    try:
        df_curr = pd.read_csv(LOG_PATH)
        df_curr['date'] = pd.to_datetime(df_curr['date'])
    except Exception as e:
        print(f"   [ERRO] Falha ao ler arquivo de logs: {e}")
        sys.exit(1)

    print(f"   Registros de log encontrados: {len(df_curr)}")

    # 3. ALINHAMENTO DE COLUNAS (Interseção)
    cols_ignorar = ['estoque_atual', 'pedido_final', 'timestamp_captura', 'sales', 'y_pred']
    
    features_ref = set(df_ref.columns)
    features_curr = set(df_curr.columns)
    
    common_cols = list(features_ref & features_curr)
    common_cols = [c for c in common_cols if c not in cols_ignorar]
    common_cols.sort()

    if not common_cols:
        print("   [ERRO] Nenhuma coluna em comum encontrada entre Treino e Logs!")
        sys.exit(1)

    print(f"   Monitorando {len(common_cols)} features comuns...")

    df_ref_clean = df_ref[common_cols].copy()
    df_curr_clean = df_curr[common_cols].copy()

    # 4. CRIANDO DATASETS DEEPCHECKS
    cat_features = []
    if 'store' in common_cols: cat_features.append('store')
    if 'item' in common_cols: cat_features.append('item')

    # Correção anterior: Removido o parametro name
    ds_ref = Dataset(df_ref_clean, cat_features=cat_features, index_name='date')
    ds_curr = Dataset(df_curr_clean, cat_features=cat_features, index_name='date')

    # 5. EXECUÇÃO DA SUITE
    print("3. Executando bateria de testes...")
    
    # --- CORREÇÃO AQUI ---
    # Removido .remove_condition(...). O full_suite() já vai ignorar checagens de modelo
    # automaticamente porque não estamos passando um modelo no .run() abaixo.
    suite = full_suite()  
    
    result = suite.run(train_dataset=ds_ref, test_dataset=ds_curr)

    # 6. RESULTADOS
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    result.save_as_html(REPORT_PATH)
    print(f"   [SUCESSO] Relatório salvo em: {REPORT_PATH}")

    try:
        if result.passed():
            print("\n✅ STATUS: APROVADO (Nenhum problema crítico detectado).")
        else:
            print("\n⚠️ STATUS: ALERTA (Drift ou anomalias detectadas. Verifique o HTML).")
    except:
        pass

if __name__ == "__main__":
    run_pre_deployment_check()

