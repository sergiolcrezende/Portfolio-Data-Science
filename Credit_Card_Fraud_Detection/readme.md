# 🛡️ Detecção de Fraude em Cartões de Crédito

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Status](https://img.shields.io/badge/Status-Concluído-success)
![Libs](https://img.shields.io/badge/Libs-Scikit--Learn%20|%20XGBoost%20|%20Pandas-yellow)
**[Ver Código Fonte do Projeto](https://github.com/sergiolcrezende/Portfolio-Data-Science/tree/main/Credit_Card_Fraud_Detection)**

> **Resumo Executivo:** Este projeto aborda o problema de desbalanceamento severo (0,17% de fraudes) em transações financeiras. A solução final utiliza um modelo **XGBoost com técnica SMOTE**, priorizando a métrica **Recall** para minimizar prejuízos financeiros. O estudo revelou um insight de negócio crítico: transações realizadas na madrugada possuem risco relativo 7,5x maior.

---

## 💼 O Problema de Negócio

As fraudes em cartão de crédito representam prejuízos bilionários para instituições financeiras e consumidores. O desafio técnico principal é o **extremo desbalanceamento dos dados**: a grande maioria das transações é legítima, tornando difícil para os algoritmos aprenderem o padrão da fraude sem gerar muitos alarmes falsos (falsos positivos).

**Objetivo:** Desenvolver um modelo de Machine Learning capaz de identificar transações fraudulentas com alta sensibilidade (Recall), minimizando o risco financeiro.

**Dados:** O dataset contém transações de cartões de crédito europeus (Kaggle), onde as variáveis originais foram transformadas via PCA (V1 a V28) por questões de privacidade, mantendo-se apenas `Time` e `Amount` originais.

---

## 🔍 Principais Hipóteses e Insights

Durante a Análise Exploratória de Dados (EDA), validamos estatisticamente três hipóteses principais:

### 1. O Padrão da Madrugada (Hipótese Temporal)
* **Pergunta:** As fraudes ocorrem em horários específicos?
* **Conclusão:** Sim. Embora o volume absoluto de transações caia na madrugada (02h às 04h), a **taxa de fraude** dispara.
* **Insight:** Uma transação realizada neste horário tem **7,5x mais chance de ser fraude** do que no restante do dia.

### 2. O "Teste" do Fraudador (Hipótese Financeira)
* **Pergunta:** Fraudes são sempre de valores altos?
* **Conclusão:** Não. O teste de Mann-Whitney confirmou que a mediana das fraudes ($9,21) é significativamente menor que a das transações legítimas ($22,00).
* **Insight:** Fraudadores frequentemente testam o cartão com valores baixos antes de tentar golpes maiores.

### 3. Complexidade Não-Linear
* **Pergunta:** Modelos simples resolvem o problema?
* **Conclusão:** Não. A análise de correlação mostrou que a fraude não segue um padrão linear simples. Variáveis como `V14`, `V12` e `V17` mostram comportamentos erráticos em casos de fraude, exigindo modelos robustos baseados em árvores de decisão.

---

## 🛠️ Metodologia e Estratégia

O projeto seguiu as seguintes etapas técnicas:

1.  **Engenharia de Recursos:**
    * Criação da variável `Hour` a partir do timestamp.
    * Escalonamento (StandardScaler) de `Amount` e `Time`.
2.  **Tratamento de Desbalanceamento:**
    * Teste comparativo entre **Undersampling** e **SMOTE** (Synthetic Minority Over-sampling Technique).
    * O SMOTE provou-se superior para preservar a informação da classe minoritária.
3.  **Modelagem:**
    * Comparação entre **Regressão Logística** (Baseline) e **XGBoost** (Gradient Boosting).
    * O XGBoost apresentou melhor capacidade de capturar as relações não lineares identificadas na EDA.
4.  **Avaliação:**
    * Foco nas métricas **Recall** (para capturar a fraude) e **F1-Score**. A Acurácia foi descartada devido ao desbalanceamento.

---

## 📊 Resultados do Modelo Final (XGBoost)

O modelo final atingiu o objetivo de maximizar a detecção de fraudes sem inviabilizar a operação com falsos positivos excessivos.

* **Recall (Sensibilidade):** ~87% (O modelo detecta a grande maioria das fraudes).
* **Matriz de Confusão:** O foco foi minimizar o quadrante de **Falsos Negativos** (fraudes que passam despercebidas), pois este é o erro que gera prejuízo direto.

*(Insira aqui a imagem da sua Matriz de Confusão se desejar)*

---

## 🚀 Conclusão e Recomendação de Negócio

Além do modelo preditivo, a análise dos dados sugere ações imediatas para a regra de negócio:

1.  **Bloqueio Preventivo na Madrugada:** Implementar autenticação forte (2FA) obrigatória para transações online entre 02h00 e 04h00.
2.  **Monitoramento de "Micro-Transações":** Criar alertas para sequências de transações de valor baixo (< $10), pois indicam fase de validação do cartão pelo fraudador.
3.  **Adoção do Modelo:** Substituir regras lineares simples pelo modelo XGBoost treinado, capaz de correlacionar horário, valor e comportamento anômalo simultaneamente.

---

## 💻 Como reproduzir este projeto

1. Clone este repositório.
2. Instale as dependências:
   ```bash

   pip install -r requirements.txt


