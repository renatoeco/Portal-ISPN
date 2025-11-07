import streamlit as st
import pandas as pd
import plotly.express as px
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
from funcoes_auxiliares import conectar_mongo_portal_ispn
import datetime


# ---------------------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------------------


st.set_page_config(page_title="Relatórios de Visitação - ISPN", layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')
st.header("Websites do ISPN")
st.write("")

db = conectar_mongo_portal_ispn()

# ---------------------------------------------------------------------------------
# AUTENTICAÇÃO VIA st.secrets
# ---------------------------------------------------------------------------------

# Carrega as credenciais diretamente do secrets.toml
gcp_credentials = st.secrets["gcp_service_account"]

# Cria o objeto de credenciais a partir do dicionário
credentials = service_account.Credentials.from_service_account_info(dict(gcp_credentials))

# Cria o cliente do Google Analytics Data API
client = BetaAnalyticsDataClient(credentials=credentials)


# ---------------------------------------------------------------------------------
# DICIONÁRIO DE PROPRIEDADES (8 sites)
# ---------------------------------------------------------------------------------


SITES = {
    "ISPN": st.secrets["sites_analytics"]["site_ispn"],
    "Cerratinga": st.secrets["sites_analytics"]["site_cerratinga"],
    "Fundo Ecos": st.secrets["sites_analytics"]["site_fundo_ecos"],
    "Capta": st.secrets["sites_analytics"]["site_capta"],
    "Agroindústria": st.secrets["sites_analytics"]["site_agroindustria"],
    "Cerrado": st.secrets["sites_analytics"]["site_cerrado"],
}


# ---------------------------------------------------------------------------------
# FUNÇÃO PARA CONSULTAR DADOS DE UM SITE
# ---------------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def consultar_dados(property_id, inicio, fim):
    """Retorna um DataFrame com os dados de visitas de um site"""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="pagePath"),
            Dimension(name="pageTitle"),
            Dimension(name="date"),
        ],
        metrics=[Metric(name="screenPageViews")],
        date_ranges=[DateRange(start_date=str(inicio), end_date=str(fim))],
    )

    response = client.run_report(request)

    linhas = []
    for row in response.rows:
        linhas.append({
            "Data": row.dimension_values[2].value,
            "Página": row.dimension_values[0].value,
            "Título": row.dimension_values[1].value,
            "Visualizações": int(row.metric_values[0].value),
        })

    df = pd.DataFrame(linhas)
    if not df.empty:
        df["Data"] = pd.to_datetime(df["Data"])
    return df

# ---------------------------------------------------------------------------------
# FUNÇÃO PARA EXIBIR RELATÓRIO DE UM SITE
# ---------------------------------------------------------------------------------

def mostrar_relatorio(df, nome_site):
    """Mostra as estatísticas visuais de um site"""
    if df.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        return

    total_visitas = df["Visualizações"].sum()
    paginas_unicas = df["Página"].nunique()
    col1, col2 = st.columns(2)
    col1.metric("Total de Visualizações", f"{total_visitas:,}".replace(",", "."))
    col2.metric("Páginas únicas", paginas_unicas)

    # Tabela
    visitas_pagina = (
        df.groupby(["Página", "Título"])["Visualizações"]
        .sum()
        .reset_index()
        .sort_values(by="Visualizações", ascending=False)
    )

    st.subheader(f"Páginas mais visitadas")
    st.dataframe(visitas_pagina, width='stretch', height=400, hide_index=True)

    # Gráfico diário
    visitas_dia = df.groupby("Data")["Visualizações"].sum().reset_index()
    fig = px.line(visitas_dia, x="Data", y="Visualizações", title=f"Evolução diária - {nome_site}")
    
    fig.update_layout(
            xaxis_title=None,
            yaxis_title="Visualizações",)
    
    st.plotly_chart(fig, width='stretch')



# ---------------------------------------------------------------------------------
# FILTROS DE DATA (formato brasileiro)
# ---------------------------------------------------------------------------------

with st.container(horizontal=True):
 
    # Selecão do período
    periodo = st.selectbox(
        'Período',
        ['hoje', '7 dias', '1 mês', '3 meses', '12 meses', 'personalizado'],
        index=2,
        width=300
    )

    hoje = datetime.date.today()

    if periodo == 'hoje':
        inicio = hoje
        fim = hoje
    elif periodo == '7 dias':
        inicio = hoje - datetime.timedelta(days=7)
        fim = hoje
    elif periodo == '1 mês':
        inicio = hoje - datetime.timedelta(days=30)
        fim = hoje
    elif periodo == '3 meses':
        inicio = hoje - datetime.timedelta(days=90)
        fim = hoje
    elif periodo == '12 meses':
        inicio = hoje - datetime.timedelta(days=365)
        fim = hoje
    elif periodo == 'personalizado':
        inicio = st.date_input("Data inicial",
                                format="DD/MM/YYYY",
                                width=300)
        fim = st.date_input("Data final",
                            format="DD/MM/YYYY",
                            width=300)

st.write('')



# ---------------------------------------------------------------------------------
# CRIAR ABAS (Visão Geral + 8 sites)
# ---------------------------------------------------------------------------------

abas = st.tabs(["Visão Geral"] + list(SITES.keys()))

# ---------------------------------------------------------------------------------
# ABA 0 — VISÃO GERAL
# ---------------------------------------------------------------------------------

with abas[0]:
    #st.header("Visão Geral")
    
    st.write("")
    st.write("")
    st.write("")

    dfs = {}
    totais = []

    for nome_site, property_id in SITES.items():

        df_site = consultar_dados(property_id, inicio, fim)

        dfs[nome_site] = df_site

        if not df_site.empty:
            total = df_site["Visualizações"].sum()
            totais.append({"Site": nome_site, "Visualizações": total})

    if not totais:
        st.warning("Nenhum dado encontrado em nenhum site para o período selecionado.")
    else:
        df_totais = pd.DataFrame(totais)
        df_totais = df_totais.sort_values(by="Visualizações", ascending=False)
        total_geral = df_totais["Visualizações"].sum()

        col1, col2 = st.columns(2)
        col1.metric("Total de Visualizações", f"{total_geral:,}".replace(",", "."))
        col2.metric("Total de sites", len(df_totais))




        # Gráfico de visitas por site
        fig = px.bar(
            df_totais,
            x="Site",
            y="Visualizações",
            title="Total de Visualizações por Site",
            text="Visualizações"  # <- adiciona os números às barras
        )

        fig.update_traces(
            texttemplate='%{text}',        # mostra exatamente o valor
            textposition='inside',         # coloca o número dentro da barra
            insidetextanchor='middle'      # centraliza verticalmente
        )

        fig.update_layout(
            xaxis_title=None,
            yaxis_title="Visualizações",
            uniformtext_minsize=8,
            uniformtext_mode='hide'  # evita sobreposição se os textos ficarem grandes
        )

        st.plotly_chart(fig)



        # Evolução diária consolidada
        df_consolidado = pd.concat([df for df in dfs.values() if not df.empty], ignore_index=True)
        visitas_dia_total = df_consolidado.groupby("Data")["Visualizações"].sum().reset_index()
        fig2 = px.line(visitas_dia_total, x="Data", y="Visualizações", title="Evolução diária (todos os sites)")
        
        fig2.update_layout(
            xaxis_title=None,
            yaxis_title="Visualizações",
            yaxis=dict(
                side="right"  # <- move os valores do eixo Y para o lado direito
            )
            )
        
        st.plotly_chart(fig2)
        


# ---------------------------------------------------------------------------------
# ABAS INDIVIDUAIS (1 a 8)
# ---------------------------------------------------------------------------------

for i, (nome_site, property_id) in enumerate(SITES.items(), start=1):
    with abas[i]:
        st.header(f"🌐 {nome_site}")
        
        st.write("")
        st.write("")
        
        df = consultar_dados(property_id, inicio, fim)
        mostrar_relatorio(df, nome_site)
