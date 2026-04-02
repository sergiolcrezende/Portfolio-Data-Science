# #---
#     ### 2. Dockerfile (Para a api_agro - Usando DEBIAN SLIM)
# # Importante: Usar python:3.10-slim evita compilações demoradas no Alpine.
# FROM python:3.10-slim

# WORKDIR /app

# # Instalar dependências para o driver do Postgres
# RUN apt-get update && apt-get install -y \
#     libpq-dev \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# # Criar ambiente virtual
# RUN python3 -m venv /opt/venv
# ENV PATH="/opt/venv/bin:$PATH"

# # Atualizar ferramentas de build
# RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# # Instalar requisitos (Será MUITO rápido aqui)
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8008"]


#---
FROM python:3.10-slim

WORKDIR /app

# Instalar dependências para o driver do Postgres e compilação básica
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Criar ambiente virtual
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Atualizar ferramentas de build
RUN pip install --no-cache-dir --upgrade pip wheel "setuptools<70.0.0"

# Instalar requisitos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8008"]