# src/app.py

import sys
import os
import shutil
import time
import pandas as pd
import numpy as np
import joblib  
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from xgboost import XGBRegressor 
import yaml

# Imports de monitoramento
from deepchecks.tabular import Dataset
from deepchecks.tabular.suites import full_suite
from dotenv import load_dotenv

# Importa features do projeto
from tools import feature_engineering_completa

# ------------------------------------------------- CONFIGURAÇÕES
# Pega o diretório onde ESTE arquivo (app.py) está: /app/src
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

app = FastAPI(title="API Vendas & Gestão de Estoque", version="5.2 - Monitoring Fix")

PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
MODEL_PATH = os.path.join(PROJECT_ROOT, 'models', 'xgb_model.json')
HISTORY_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw', 'train.csv')
LOG_PATH = os.path.join(PROJECT_ROOT, 'logs', '00_resultado_previsoes_vendas.csv')
HTML_REPORT_DIR = os.path.join(PROJECT_ROOT, 'data', 'reports')
# CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config.yaml')

# ------------------------------------------------- MARGEM DE SEGURANÇA
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(dotenv_path)
MARGEM_SEGURANCA = int(os.getenv("MARGEM_SEGURANCA", 10))

print(f"[44-margem]{MARGEM_SEGURANCA}")


# def load_config():
#     if os.path.exists(CONFIG_PATH):
#         with open(CONFIG_PATH, 'r') as file:
#             return yaml.safe_load(file)
#     return {}
# config = load_config()

# Leitura da variável (com valor padrão 12 caso falhe)
# MARGEM_SEGURANCA = config.get('app', {}).get('margem_seguranca', 12)
# MARGEM_SEGURANCA = 12


# ------------------------------------------------- LÓGICA DE MONITORAMENTO
os.makedirs(HTML_REPORT_DIR, exist_ok=True)
# Garante que a pasta de logs existe
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

app.mount("/dashboard", StaticFiles(directory=HTML_REPORT_DIR), name="dashboard")

# ------------------------------------------------- VARIÁVEIS GLOBAIS
df_history = None 
model = None


#----------------------------------------------------------------------------------------------------\


# ------------------------------------------------- INICIALIZAÇÃO (STARTUP) 
@app.on_event("startup")
async def startup_event():
    global model, df_history
    print("[AGUARDE] Inicializando API...")
    
    # 1. CARREGAR MODELO
    print(f"   Carregando modelo de: {MODEL_PATH}")
    try:
        model = joblib.load(MODEL_PATH)
        print(f"  [OK] Modelo carregado com Joblib! (Tipo: {type(model)})")   
    except Exception as e_joblib:
        print(f" [ERRO] Falha Joblib: {e_joblib}. Tentando nativo...")       
        try:
            model = XGBRegressor()
            model.load_model(MODEL_PATH)
            print("   [OK] Modelo XGBoost carregado nativamente!")       
        except Exception as e_xgb:
            print(f"   [ERRO] CRÍTICO: Falha total ao carregar modelo: {e_xgb}")     

    # 2. CARREGAR HISTÓRICO
    if os.path.exists(HISTORY_PATH):
        print(f"   [FILE] Carregando histórico de: {HISTORY_PATH}")      
        try:
            df = pd.read_csv(HISTORY_PATH)
            df['date'] = pd.to_datetime(df['date'])

            if 'sales' in df.columns:
                df['sales_log'] = np.log1p(df['sales']) 

            # Ordena e garante colunas essenciais
            df_history = df.sort_values(['store', 'item', 'date'])
            print(f"   [OK] Histórico carregado: {len(df_history)} linhas.")       
        except Exception as e:
            print(f"   [ERRO] Erro ao ler CSV: {e}")         
            df_history = pd.DataFrame()
    else:
        print("   [ERRO] CRÍTICO: Arquivo train.csv não encontrado!")        
        df_history = pd.DataFrame()

#--------------------------------------------------------------------------------------------------\

def salvar_log_batch(df_logs):
    """
    Salva logs de forma segura. Se o esquema (colunas) mudar, 
    faz backup do arquivo antigo e cria um novo.
    """
    try:
        if df_logs.empty:
            return

        # Adiciona timestamp
        df_logs['timestamp_captura'] = datetime.now().isoformat()
        
        # Garante ordenação alfabética das colunas para evitar erros de append
        df_logs = df_logs.reindex(sorted(df_logs.columns), axis=1)

        file_exists = os.path.isfile(LOG_PATH)
        
        # VERIFICAÇÃO DE INTEGRIDADE:
        # Se o arquivo existe, verificamos se as colunas batem.
        if file_exists:
            try:
                # Lê apenas o cabeçalho
                cols_existentes = pd.read_csv(LOG_PATH, nrows=0).columns.tolist()
                cols_novas = df_logs.columns.tolist()
                
                if cols_existentes != cols_novas:
                    print(f"   [AVISO] Esquema do log mudou! Arquivando log antigo...")
                    backup_name = LOG_PATH.replace(".csv", f"_OLD_{int(time.time())}.csv")
                    shutil.move(LOG_PATH, backup_name)
                    file_exists = False # Força criar novo cabeçalho
                    print(f"   [INFO] Log antigo movido para: {backup_name}")
            except Exception as e_check:
                print(f"   [ERRO] Erro ao verificar integridade do log: {e_check}")

        # Salva no disco
        df_logs.to_csv(LOG_PATH, mode='a', header=not file_exists, index=False)
        print(f"   [LOG] {len(df_logs)} registros salvos em {LOG_PATH}")
        
    except Exception as e:
        print(f"[ERRO] Falha ao salvar log: {e}")


def run_deepchecks_task():
    """
    Tarefa de background para rodar validação se necessário.
    Para produção, idealmente isso roda separado (Airflow/Cron), 
    mas aqui deixamos o placeholder funcional.
    """
    pass


## -------------------------------------------------  CLASSES DE INPUT
class InventoryRequest(BaseModel):
    store_id: int
    item_id: int
    date: str
    estoque_atual: int


class SalesRequest(BaseModel):
    store_id: int
    item_id: int
    start_date: str
    days_ahead: int = 7


#----------------------------------------------------ENDPOINT 1: PREVISÃO SIMPLES
@app.post("/predict")
def predict_sales(request: SalesRequest):
    global df_history, model
    
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo não carregado.")

    try:
        # Input "Futuro"
        input_data = {
            'store': [request.store_id],
            'item': [request.item_id],
            'date': [pd.to_datetime(request.start_date)]
        }
        df_future = pd.DataFrame(input_data)
        df_future['sales'] = 0  
        df_future['sales_log'] = 0
        
        # Resgatar Histórico
        if df_history is not None and not df_history.empty:
            mask = (df_history['store'] == request.store_id) & (df_history['item'] == request.item_id)
            df_past = df_history[mask].tail(180).copy()
            if 'sales' not in df_past.columns: df_past['sales'] = 0 
        else:
            df_past = pd.DataFrame()

        # Concatenar e Engenharia
        df_full = pd.concat([df_past, df_future], ignore_index=True)
        df_full = df_full.sort_values('date')
        df_features_full = feature_engineering_completa(df_full)

        # Isolar linha da previsão
        df_input_ready = df_features_full.iloc[[-1]].copy()

        # Alinhamento de Colunas
        try:
            expected_cols = model.feature_names_in_
            missing = set(expected_cols) - set(df_input_ready.columns)
            for c in missing: df_input_ready[c] = 0
            df_input_ready = df_input_ready[expected_cols]
        except AttributeError:
            pass 

        # Previsão
        prediction = model.predict(df_input_ready)
        val = max(0.0, float(prediction[0]))

        # --- MONITORAMENTO ---
        # Prepara dados ricos para log (Features + Identificadores + Resultado)
        df_log = df_input_ready.copy()
        
        # Adiciona metadados essenciais
        df_log['store'] = request.store_id
        df_log['item'] = request.item_id
        df_log['date'] = request.start_date
        df_log['y_pred'] = val
        
        # Campos nulos que o outro endpoint tem, para manter padrão
        df_log['pedido_final'] = 0 
        df_log['estoque_atual'] = 0
        
        salvar_log_batch(df_log)
        # ---------------------

        return {
            "store_id": request.store_id,
            "item_id": request.item_id,
            "prediction_date": request.start_date,
            "total_sales": round(val, 2),
            "status": "success"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


#------------------------------------------------- ENDPOINT 2: RECOMENDAÇÃO DE ESTOQUE
@app.post("/recommend-purchase")
def recommend(request: list[InventoryRequest], background_tasks: BackgroundTasks):
    
    print("\n--- DEBUG: DADOS RECEBIDOS ---")
    if len(request) > 0:
        # Mostra o primeiro item completo para ver se estoque_atual veio > 0
        print(f"Primeiro Item do Payload: {request[0].dict()}") 
        
        # Verifica se tem algum item com estoque > 0 no lote todo
        soma_estoque = sum([r.estoque_atual for r in request])
        print(f"Soma total do estoque recebido no lote: {soma_estoque}")
    else:
        print("Payload vazio!")
    
    # -------------------------------------
    
    
    global df_history, model
    
    if model is None:
         raise HTTPException(status_code=503, detail="Modelo não carregado.")

    try:
        # Preparar Input
        df_input = pd.DataFrame([item.dict() for item in request])
        df_input.rename(columns={'store_id': 'store', 'item_id': 'item'}, inplace=True)
        df_input['date'] = pd.to_datetime(df_input['date'])
        df_input['sales'] = np.nan
        df_input['tipo'] = 'futuro'

        # Unir com Histórico
        if df_history is not None:
            stores = df_input['store'].unique()
            items = df_input['item'].unique()
            mask = (df_history['store'].isin(stores)) & (df_history['item'].isin(items))
            df_hist_temp = df_history[mask].copy()
            df_hist_temp['tipo'] = 'historico'
        else:
            df_hist_temp = pd.DataFrame(columns=df_input.columns)

        df_full = pd.concat([df_hist_temp, df_input], ignore_index=True)
        
        # Engenharia de Features
        df_full = feature_engineering_completa(df_full) 
        
        # Filtrar apenas as linhas do Futuro
        df_pred = df_full[df_full['tipo'] == 'futuro'].copy()
        df_pred = df_pred.fillna(0)

        # 1. Alinhamento para o Modelo
        try:
            expected_cols = model.feature_names_in_
            missing = set(expected_cols) - set(df_pred.columns)
            for c in missing: df_pred[c] = 0
            X_pred = df_pred[expected_cols].copy() 
        except AttributeError:
            X_pred = df_pred.copy()

        # 2. Previsão
        y_pred = model.predict(X_pred)
        
        # 3. Preparação do LOG
        df_log_completo = X_pred.copy()
        df_log_completo['store'] = df_pred['store'].values
        df_log_completo['item'] = df_pred['item'].values
        df_log_completo['date'] = df_pred['date'].values 
        df_log_completo['y_pred'] = y_pred
        
        # Merge para resultado final
        df_final_result = pd.merge(
            df_input, 
            pd.DataFrame({'store': df_pred['store'], 'item': df_pred['item'], 'date': df_pred['date'], 'y_pred': y_pred}),
            on=['store', 'item', 'date'], 
            how='left'
        )


        resultados_api = []
        pedidos_finais = []

        for _, row in df_final_result.iterrows():
            venda_prevista = int(np.ceil(max(0, float(row['y_pred']))))
            estoque_atual = row['estoque_atual']
            
            sugestao_compra = max(0, (venda_prevista + MARGEM_SEGURANCA) - estoque_atual)
            pedidos_finais.append(sugestao_compra)
            estoque_alvo = venda_prevista + MARGEM_SEGURANCA
            
            resultados_api.append({
                "data": row['date'].strftime("%Y-%m-%d"),
                "loja": int(row['store']),
                "produto": int(row['item']),
                "venda_prevista": venda_prevista,
                "estoque_atual": estoque_atual,
                "PEDIDO_FINAL": sugestao_compra,
                "MARGEM_SEGURANCA": MARGEM_SEGURANCA,
                "ESTOQUE_ALVO": estoque_alvo
            })
        
        # Completa o LOG com dados do negócio
        df_log_completo['pedido_final'] = pedidos_finais
        df_log_completo['estoque_atual'] = df_final_result['estoque_atual'].values

        # 4. Salvar
        salvar_log_batch(df_log_completo)
        
        background_tasks.add_task(run_deepchecks_task)

        return {
            "status": "sucesso",
            "total_itens_comprar": sum(resultados_api[i]['PEDIDO_FINAL'] for i in range(len(resultados_api))),
            "detalhes": resultados_api
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


