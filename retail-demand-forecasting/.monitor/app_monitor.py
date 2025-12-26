# Arquivo: .monitor/app_monitor.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
import subprocess
import os
import sys
import asyncio

app = FastAPI(title="Sistema de Monitoração Deepchecks")

# Mapeamento dos scripts
SCRIPTS = {
    "pre": "90_monitor_deepchecks_pre_implantacao.py",
    "prod": "91_monitor_deepchecks_producao.py"
}

async def gerar_logs(script_name):
    """
    Função geradora que lê o output do script linha por linha
    e envia para o navegador em tempo real.
    """
    script_path = os.path.join(os.getcwd(), script_name)
    
    if not os.path.exists(script_path):
        yield f"ERRO: Arquivo {script_name} não encontrado.\n"
        return

    # Popen inicia o processo sem bloquear. 
    # stdout=subprocess.PIPE permite ler o que ele escreve.
    # stderr=subprocess.STDOUT joga os erros no mesmo fluxo dos logs.
    process = subprocess.Popen(
        [sys.executable, "-u", script_name], # "-u" força o python a não fazer buffer (unbuffered)
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=os.getcwd()
    )

    # Loop que lê linha a linha enquanto o script roda
    for line in process.stdout:
        yield line
        # Pequena pausa para garantir que o navegador renderize
        await asyncio.sleep(0.01) 

    # Fecha o processo e verifica o código de saída
    process.stdout.close()
    return_code = process.wait()
    
    if return_code == 0:
        yield "\n--- EXECUÇÃO CONCLUÍDA COM SUCESSO ---\n"
    else:
        yield f"\n--- ERRO NA EXECUÇÃO (Código {return_code}) ---\n"



@app.get("/", response_class=HTMLResponse)
def dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monitoração Data Science</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; padding: 20px; background-color: #f4f4f9; text-align: center; }
            h1 { color: #333; }
            
            .btn-container { margin-bottom: 20px; }
            .btn {
                padding: 12px 24px; font-size: 16px; color: white; border: none; 
                border-radius: 6px; cursor: pointer; margin: 10px; 
                transition: transform 0.1s;
            }
            .btn:active { transform: scale(0.98); }
            .btn-pre { background-color: #2980b9; } 
            .btn-prod { background-color: #27ae60; }

            #terminal {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                text-align: left;
                width: 80%;
                margin: 0 auto;
                height: 500px;
                overflow-y: scroll;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                border: 1px solid #333;
                white-space: pre-wrap; 
            }
            
            /* Classes utilitárias para colorir o terminal via JS */
            .info-header { color: #f1c40f; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>Central de Monitoração Deepchecks</h1>
        <p>Selecione o ambiente para rodar a validação:</p>
        
        <div class="btn-container">
            <button onclick="rodarScript('pre')" class="btn btn-pre">🚀 Rodar Pré-Implantação</button>
            <button onclick="rodarScript('prod')" class="btn btn-prod">🌍 Rodar Produção</button>
        </div>

        <div id="terminal">Aguardando comando...</div>

        <script>
            async function rodarScript(tipo) {
                // 1. Pega o elemento terminal PRIMEIRO para evitar erros
                const terminal = document.getElementById('terminal');
                
                // 2. Define a mensagem baseada no botão
                let cabecalho = "";
                
                if (tipo === 'pre') {
                    cabecalho = "🟦 VOCÊ ACIONOU: AMBIENTE DE PRÉ-IMPLANTAÇÃO\\n" +
                                "   [Target]: Validar modelo novo antes do deploy.\\n" +
                                "----------------------------------------------------------\\n";
                } else if (tipo === 'prod') {
                    cabecalho = "🟩 VOCÊ ACIONOU: AMBIENTE DE PRODUÇÃO\\n" +
                                "   [Target]: Verificar Drift e dados reais.\\n" +
                                "----------------------------------------------------------\\n";
                }

                // 3. Define o conteúdo inicial (Cabeçalho + Aviso de loading)
                // Usamos += para garantir que tudo apareça
                terminal.innerHTML = cabecalho;
                terminal.innerHTML += "\\n⏳ Conectando ao servidor e iniciando script... aguarde...\\n\\n";
                
                // Reseta a cor padrão para verde
                terminal.style.color = "#00ff00";

                try {
                    const response = await fetch(`/run_stream/${tipo}`);
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) break;
                        
                        const text = decoder.decode(value);
                        terminal.innerHTML += text;
                        
                        terminal.scrollTop = terminal.scrollHeight;
                    }
                } catch (error) {
                    terminal.innerHTML += "\\n❌ [ERRO CRÍTICO]: " + error;
                    terminal.style.color = "#ff4444";
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/run_stream/{tipo}")
async def run_stream(tipo: str):
    if tipo not in SCRIPTS:
        raise HTTPException(status_code=404, detail="Script não encontrado")
    
    # Retorna o StreamingResponse que vai mandando os dados aos poucos
    return StreamingResponse(gerar_logs(SCRIPTS[tipo]), media_type="text/plain")