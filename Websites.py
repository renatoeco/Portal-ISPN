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
estatistica = db["estatistica"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_websites"
nome_pagina = "Websites"

hoje = datetime.datetime.now().strftime("%d/%m/%Y")

pagina_anterior = st.session_state.get("pagina_anterior")
navegou_para_esta_pagina = (pagina_anterior != PAGINA_ID)

if navegou_para_esta_pagina:

    # Obter o único documento
    doc = estatistica.find_one({})

    # Criar o campo caso não exista
    if nome_pagina not in doc:
        estatistica.update_one(
            {},
            {"$set": {nome_pagina: []}}
        )

    estatistica.update_one(
            {},
            {"$inc": {f"{nome_pagina}.$[elem].numero_de_acessos": 1}},
            array_filters=[{"elem.data": hoje}]
        )

    estatistica.update_one(
        {f"{nome_pagina}.data": {"$ne": hoje}},
        {"$push": {
            nome_pagina: {"data": hoje, "numero_de_acessos": 1}
        }}
    )

# Registrar página anterior
st.session_state["pagina_anterior"] = PAGINA_ID


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

@st.cache_data(ttl=3600, show_spinner=False)
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

    max_visualizacoes = int(visitas_pagina["Visualizações"].max())

    st.markdown(f"##### Páginas mais visitadas")
    st.dataframe(visitas_pagina, height=400, hide_index=True,
                column_config={
                    "Visualizações": st.column_config.ProgressColumn(
                        format="%f",
                        min_value=0,
                        max_value=max_visualizacoes,
                    ),
                } 
            )

    # Gráfico diário
    visitas_dia = df.groupby("Data")["Visualizações"].sum().reset_index()
    fig = px.line(visitas_dia, x="Data", y="Visualizações", title=f"Evolução diária - {nome_site}")
    
    fig.update_layout(
            xaxis_title=None,
            yaxis_title="Visualizações",)
    
    st.plotly_chart(fig)
    
    
# ---------------------------------------------------------------------------------
# Função auxiliar: porcentagem por dia da semana
# ---------------------------------------------------------------------------------


def visitas_por_dia_semana(df):
    if df.empty:
        return pd.DataFrame()

    df_aux = df.copy()

    # Dia da semana (0=segunda, 6=domingo)
    df_aux["DiaSemana"] = df_aux["Data"].dt.dayofweek

    mapa_dias = {
        0: "Segunda",
        1: "Terça",
        2: "Quarta",
        3: "Quinta",
        4: "Sexta",
        5: "Sábado",
        6: "Domingo",
    }

    visitas = (
        df_aux
        .groupby("DiaSemana")["Visualizações"]
        .sum()
        .reset_index()
    )

    total = visitas["Visualizações"].sum()

    visitas["Dia da semana"] = visitas["DiaSemana"].map(mapa_dias)
    visitas["% das visitas"] = (visitas["Visualizações"] / total * 100).round(1)

    visitas = visitas[["Dia da semana", "% das visitas"]]

    # Ordena de segunda a domingo
    visitas["ordem"] = visitas["Dia da semana"].map({v: k for k, v in mapa_dias.items()})
    visitas = visitas.sort_values("ordem").drop(columns="ordem")

    return visitas


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
        
        # -----------------------------------------
        # % de visitas por dia da semana
        # -----------------------------------------
        st.write("")
        st.markdown("##### Distribuição de visitas por dia da semana")

        df_semana = visitas_por_dia_semana(df)

        if df_semana.empty:
            st.info("Sem dados suficientes para calcular os percentuais.")
        else:
            altura_df = 35 + 7 * 35
            st.dataframe(
                df_semana,
                hide_index=True,
                height=altura_df,
                column_config={
                    "% das visitas": st.column_config.ProgressColumn(
                        "% das visitas",
                        min_value=0,
                        max_value=100,
                        format="%.1f%%",
                    )
                }
            )

