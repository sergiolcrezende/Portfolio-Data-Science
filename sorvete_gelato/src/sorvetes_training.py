# sorvetes_training.py

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

# Pacotes
import argparse
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (mean_squared_error,
                            r2_score,
                            mean_absolute_percentage_error,
                            mean_absolute_error)
from tools import mensage_warning, load_config


# Configuração do ambiente
mensage_warning()
cfg = load_config("config_servidor.yml")
BASE_DADOS = cfg['env_vars']['base_dados']

# Bloco para ler os argumentos que vêm do comando
parser = argparse.ArgumentParser()
parser.add_argument("--data_path", type=str, help=BASE_DADOS)
args = parser.parse_args()


def main():
    # Habilitar autolog do MLflow para capturar parâmetros, métricas e o modelo
    mlflow.sklearn.autolog()

    print("Carregando dados...")
    # O Azure ML monta o dataset ou a pasta como local, então lemos direto
    sorvetes = pd.read_csv(BASE_DADOS)

    X = sorvetes[['Temperatura_C']]
    y = sorvetes['Vendas_Qtd']

    # Divisão Treino e Teste
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

    # Treinamento do Modelo
    print("Treinando modelo de Regressão Linear...")
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Avaliação
    y_pred = model.predict(X_test)
    
    # Métricas para Regressão (não Acurácia/AUC)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    mape = mean_absolute_percentage_error(y_test, y_pred)

    print('\nRESULTADO...\n')
    print(f"MSE (Mean Squared Error): {mse:.2f}")
    print(f"R2 Score: {r2:.2f}")
    print(f"RMSE (Root Mean Squared Error):  {rmse:.2f}")
    print(f"MAE  (Erro Médio Absoluto): {mae:.2f}")
    print(f"MAPE: {mape:.2%} (O modelo erra, em média, {mape*100:.1f}% do valor real)")

    # Exemplo de previsão: Se fizer 30 graus
    temp_simulada = np.array([[30]])
    previsao = model.predict(temp_simulada)
    print(f"Previsão de vendas para 30°C: {previsao[0]:.0f} sorvetes")


if __name__ == "__main__":
    main()
