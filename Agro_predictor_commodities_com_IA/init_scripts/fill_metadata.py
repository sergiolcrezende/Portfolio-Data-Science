# fill_metadata.py

# Mapeamento B3 -> Yahoo Finance (Proxy Internacional)
# B3 - https://b3.com.br/pt_br/para-voce
# yfinance - finance.yahoo.com
# prompt: https://gemini.google.com/app/6a4813fa74f75b14
# objetivo: inserir informação na tabela commodities_metadata
#           sem rodar este script não tem como rodar o modelo

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
sys.path.append(str(Path(__file__).parent.parent))

from src.agro_predictor.data_loaders.tools_db import get_db_connection, upsert_metadata
from src.agro_predictor.utils.tools_cy import load_json_data


if __name__ == "__main__":

    load_dotenv(override=True)
    CAMINHO_ARQUIVO_JSON = os.getenv('REGRA_COMMODITIES')

    # Verificação de segurança para evitar o erro de TypeError
    if not CAMINHO_ARQUIVO_JSON:
        print("ERRO: A variável de ambiente 'REGRA_COMMODITIES' não foi encontrada.")
        print("Verifique se o arquivo .env existe e se a variável está definida nele.")
        sys.exit(1) # Encerra o script aqui se não tiver o caminho

    # Carregar regra
    dados_json = load_json_data(CAMINHO_ARQUIVO_JSON)

    # Conectar e Executar
    if dados_json:
        engine = get_db_connection()

        if engine:
            connection = engine.raw_connection()

            try:
                upsert_metadata(connection, dados_json)
                connection.commit()
            finally:
                connection.close()

