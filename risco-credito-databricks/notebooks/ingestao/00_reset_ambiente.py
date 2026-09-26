# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# IMPORTANTE: ESTE COMANDO SÓ E EXECUTADO EM DESENVOLVIMENTO EM PRODUÇÃO SERÁ VIA JOB E A CONFIGURAÇÃO ESTÃO NO ARQUIVO resources/job.yml ou outros arquivo que será executado em produção
# MAGIC %sh uv sync

# COMMAND ----------

# ==============================================================================
# notebooks/ingestao/00_reset_ambiente.py
# Reset único do estado gerado pela estrutura ANTIGA (raw_landing sem
# subpastas training/scoring). Rode ANTES de 01_bronze.py e 02_silver.py
# na primeira execução com o novo layout. Depois disso, não precisa rodar
# de novo — não faz parte do pipeline recorrente.
# ==============================================================================


dbutils.widgets.text("catalog", "credito_dev")
dbutils.widgets.text("confirmar", "")  # precisa digitar exatamente: RESETAR

catalog = dbutils.widgets.get("catalog")
confirmar_texto = dbutils.widgets.get("confirmar")



import sys
import os

repo_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
if repo_root not in sys.path:
    sys.path.append(repo_root)

from src.ingestion.maintenance import reset_legacy_environment



reset_legacy_environment(
    spark=spark,
    dbutils=dbutils,
    catalog=catalog,
    confirm=(confirmar_texto == "RESETAR"),
)

"""
IMPORTANTE
    VAI APARAECER UMA CAIXA NO TOPO DA TELA, COM O TEXTO:
        "RESETAR"?
    PRECISA DIGITAR EXATAMENTE RESETAR, SEM ESPAÇOS, SEM MAIÚSCULAS, SEM APOSTROFES E SEM PONTUAÇÃO
    DEPOIS EXECUTA A CELULA NOVAMENTE

"""
