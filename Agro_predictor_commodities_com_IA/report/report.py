# report.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Agro-Trade Intelligence Dashboard", layout="wide")

def main():
    st.title("🌾 Agro-Trade Intelligence - MVP")
    st.markdown("### Monitoramento de Preços e Influência Climática")

    # --- SIDEBAR: Filtros ---
    st.sidebar.header("Filtros")
    commodity = st.sidebar.selectbox("Commodity", ["Soja (ZS=F)"])
    region = st.sidebar.selectbox("Região de Foco", ["Sorriso - MT", "Rio Verde - GO"])
    date_range = st.sidebar.date_input("Período", [])

    # --- KPIs PRINCIPAIS ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Preço Atual (USD)", "$ 12.45", "-1.2%")
    col2.metric("Câmbio (USD/BRL)", "R$ 5.10", "+0.5%")
    col3.metric("Preço em BRL", "R$ 63.50", "-0.7%")
    col4.metric("Status Climático", "Alerta: Seca", delta_color="inverse")

    # --- GRÁFICOS ---
    st.divider()
    
    row1_col1, row1_col2 = st.columns(2)
    
    with row1_col1:
        st.subheader("Análise de Preços e Câmbio")
        # Simulação de dados da tabela finance.prices e exchange_rates
        df_prices = pd.DataFrame({
            'Data': pd.date_range(start='2024-01-01', periods=20),
            'Preço_BRL': [60, 61, 59, 62, 63, 62, 64, 65, 63, 62, 61, 63, 64, 66, 67, 65, 64, 63, 62, 63]
        })
        fig_price = px.line(df_prices, x='Data', y='Preço_BRL', title="Evolução do Preço da Soja (R$)")
        st.plotly_chart(fig_price, use_container_width=True)

    with row1_col2:
        st.subheader("Precipitação Acumulada vs. Média")
        # Simulação de dados da tabela weather.climate_data
        df_weather = pd.DataFrame({
            'Data': pd.date_range(start='2024-01-01', periods=20),
            'Chuva_Real': [5, 10, 0, 0, 2, 15, 20, 5, 0, 0, 2, 4, 10, 0, 0, 5, 8, 12, 0, 0],
            'Media_Historica': [8]*20
        })
        fig_weather = go.Figure()
        fig_weather.add_trace(go.Bar(x=df_weather['Data'], y=df_weather['Chuva_Real'], name='Chuva Real'))
        fig_weather.add_trace(go.Scatter(x=df_weather['Data'], y=df_weather['Media_Historica'], name='Média Histórica', line=dict(color='red', dash='dash')))
        fig_weather.update_layout(title="Precipitação em Sorriso - MT (mm)")
        st.plotly_chart(fig_weather, use_container_width=True)

    # --- INSIGHTS DE IA ---
    st.divider()
    st.subheader("🤖 Insights de Previsão (ML)")
    
    col_ml1, col_ml2 = st.columns([1, 2])
    
    with col_ml1:
        # Gauge para Volatilidade
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = 75,
            title = {'text': "Probabilidade de Volatilidade (7 dias)"},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "orange"}}
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
    with col_ml2:
        st.info("""
        **Análise do Modelo:** A falta de chuvas persistente na região de Sorriso-MT nas últimas 2 semanas 
        tem uma correlação histórica de 85% com o aumento da volatilidade nos contratos futuros 
        da Soja. Recomenda-se monitorar o fechamento do câmbio para ajustes de hedge.
        """)


if __name__ == "__main__":
    main()

