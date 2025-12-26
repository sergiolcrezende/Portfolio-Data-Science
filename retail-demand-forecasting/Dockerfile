FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1

# --- CORREÇÃO AQUI ---
# Adiciona a pasta /app/src ao caminho de busca do Python.
# Assim, ele encontra 'tools' e 'app' não importa de onde o comando rode.
ENV PYTHONPATH="${PYTHONPATH}:/app/src"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
