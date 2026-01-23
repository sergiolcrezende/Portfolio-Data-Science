#tools.py

import warnings 
import logging
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
import yaml


def mensage_warning():
    """
    Mensagem de warning desabilitada
    """
    warnings.filterwarnings('ignore')
    warnings.filterwarnings("ignore", message=".*experimental class.*")
    warnings.filterwarnings("ignore", message="X does not have valid feature names.*")
    logging.getLogger("mlflow").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.WARNING)
    logging.getLogger("azure.ai.ml").setLevel(logging.WARNING)


def load_config(caminho_arquivo):
    """
    Arquivo de configuração do sistema
    """
        
    with open(caminho_arquivo, "r", encoding="utf-8") as stream:
        try:
            # Transforma o YAML em um dicionário Python
            config = yaml.safe_load(stream)
            return config
        except yaml.YAMLError as exc:
            print(f"Erro ao ler o arquivo YAML: {exc}")


def credencial():
    """
    Conecta no Azure
    """

    try:
        credential = DefaultAzureCredential()
        credential.get_token("https://management.azure.com/.default")
        print("Conexão ok!")
    except Exception as ex:
        credential = InteractiveBrowserCredential()
        print(f"Erro: {ex}")

    return credential

