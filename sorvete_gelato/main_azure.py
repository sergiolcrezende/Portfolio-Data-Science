# main.azure.py

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

from azure.ai.ml import MLClient
from azure.ai.ml import command
from azure.ai.ml import Input
from azure.ai.ml.entities import Environment
from src.tools import mensage_warning, credencial, load_config


# Configuração do ambiente
mensage_warning()
cfg = load_config("config_servidor.yml")
BASE_DADOS = cfg['env_vars']['base_dados']
FILE_CONFIG = cfg['env_vars']['file_config']
FILE_ML = cfg['env_vars']['file_ml']

credential = credencial()
ml_client = MLClient.from_config(credential=credential, path=FILE_CONFIG)

# Configuração Azure
meu_ambiente = Environment(
    name=cfg['name'],
    description=cfg['description'],
    conda_file=cfg['conda_file'], 
    image=cfg['image'], 
)

job = command(
    code=cfg['code'],
    inputs={"dados_vendas": Input(type="uri_file", path=BASE_DADOS)},
    environment=meu_ambiente, 
    environment_variables=cfg['env_vars'],
    command=f"python {FILE_ML} --data_path ${{inputs.dados_vendas}}",
    compute=cfg['compute'],
    display_name=cfg['display_name'],
    experiment_name=cfg['experiment_name']
)

print("Enviando o job para o Azure ML...")
returned_job = ml_client.create_or_update(job)

# Monitorando  MLFlow
aml_url = returned_job.studio_url
print("Monitore seu job neste link:", aml_url)

