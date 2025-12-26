#!/bin/bash

#-----------------------------------------------------------------/COMENTARIOS
#  chama o notebook: 92_run_monitor_api.py
# executar via 'git bash': ./92_run_monitor_web.sh
# origem: cd ~/Desktop/_ESTUDO/_portifolio_full/retail-demand-forecasting/.monitor
# web:  http://localhost:8005
#-----------------------------------------------------------------------------------------------------------------------\

# --- CONFIGURAÇÕES ---
PORT=8005
HOST="127.0.0.1"
VENV_NAME=".venv" # Nome da pasta do seu ambiente virtual

# Cores para logs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

clear

cd ..

echo -e "${GREEN}=== INICIANDO SIMULAÇÃO DA MONITORAÇÃO ===${NC}"

# ATIVAR VIRTUAL ENVIRONMENT
# ---------------------------------------------------------
echo "0. Configurando ambiente virtual..."

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

# Exibe versão do python para confirmar
echo "   -> Usando Python: $(which python)"


# SUBIR A API EM BACKGROUND
# ---------------------------------------------------------
echo -e "${GREEN} 2. Iniciando a API FastAPI na porta $PORT...${NC}"

# Entra na pasta onde está o app_monitor.py
cd .monitor  


uvicorn app_monitor:app --host $HOST --port $PORT > ../logs/00_api_monitor_log.txt 2>&1 &

API_PID=$!
cd ..  

echo "   -> API iniciada com PID: $API_PID"
echo "   -> Aguardando 5 segundos para inicialização..."
sleep 5

# Verifica se o processo ainda está rodando
if ps -p $API_PID > /dev/null; then
   echo -e "${GREEN}   -> API está rodando com sucesso!${NC}"
   echo -e "${GREEN}   -> Acesse: http://localhost:$PORT${NC}"
else
   echo -e "${RED} A API caiu logo após iniciar.${NC}" 
   echo "   Verifique o log em logs/00_api_monitor_log.txt ou rode manualmente 'uvicorn app_monitor:app' na pasta .monitor"
   # Mata o processo caso tenha ficado zumbi, só por segurança
   kill $API_PID 2>/dev/null
   exit 1
fi

# Mantém o script rodando para você ver o servidor (pressione CTRL+C para sair)
echo -e "${YELLOW} Pressione CTRL+C para encerrar o servidor e sair.${NC}"
wait $API_PID