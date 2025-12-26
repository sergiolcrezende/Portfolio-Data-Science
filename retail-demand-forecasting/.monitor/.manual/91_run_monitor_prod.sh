
# monitorar na produção -e mais voltado a monitoração para o usuario

# chama o notebook: 02_monitor_deepchecks_producao.py
# path: cd  ~/Desktop/_ESTUDO/_portifolio_full/retail-demand-forecasting/.monitor
# executar via 'git bash': ./91_run_monitor_prod.sh
#-------------------------------------------------------------------------------------------/

# Cores para logs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
VENV_NAME=".venv" # Nome da pasta do seu ambiente virtual

clear

echo -e "${GREEN}=== INICIANDO MONITORAÇÃO PRODUÇÃO ===${NC}"

# ATIVAR VIRTUAL ENVIRONMENT
# ---------------------------------------------------------
echo "0. Configurando ambiente virtual..."

cd ..

if [ -f "./$VENV_NAME/bin/activate" ]; then
    source "./$VENV_NAME/bin/activate"
    echo -e "${GREEN}   -> Ambiente (Linux/Mac) ativado: $VENV_NAME${NC}"
elif [ -f "./$VENV_NAME/Scripts/activate" ]; then
    source "./$VENV_NAME/Scripts/activate"
    echo -e "${GREEN}   -> Ambiente (Windows) ativado: $VENV_NAME${NC}"
else
    echo -e "${RED} ERRO: Pasta './$VENV_NAME' não encontrada ou incompleta.${NC}"
    echo "   Certifique-se de ter criado o ambiente com: python -m venv .venv"
    exit 1
fi

cd .monitor
who 


# py 02_monitor_deepchecks_producao.py  >log02.txt   # usar para capiturar erros com detalhe
py 91_monitor_deepchecks_producao.py             # para fluxo normal de execução

if [ $? -eq 0 ]; then
    echo -e "---------------------------------------------------"
    echo -e "${GREEN} Simulação concluída com sucesso!${NC}"
else
    echo -e "---------------------------------------------------"
    echo -e "${RED} Houve um erro na execução da simulação.${NC}"
fi
