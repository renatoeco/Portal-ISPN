import streamlit as st
import pandas as pd
from datetime import datetime
from bson import ObjectId
from funcoes_auxiliares import conectar_mongo_portal_ispn, dialog_editar_entregas
import streamlit_shadcn_ui as ui
import plotly.express as px
import time
import bson

st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

db = conectar_mongo_portal_ispn()
estrategia = db["estrategia"]  
programas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"]  
indicadores = db["indicadores"]
estatistica = db["estatistica"] 


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_entregas"
nome_pagina = "Entregas"

hoje = datetime.now().strftime("%d/%m/%Y")

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


# ##########################################################
# Funções
# ##########################################################


def resolver_responsaveis(lista_ids, pessoas_dict):
    nomes = []
    for rid in lista_ids:
        rid = ObjectId(rid)
        if rid in pessoas_dict:
            nomes.append(pessoas_dict[rid])
    return ", ".join(nomes)


def carregar_entregas():
    """
    Retorna DataFrame com TODAS as entregas,
    já resolvendo responsáveis e programa
    """
    pessoas = {
        p["_id"]: p["nome_completo"]
        for p in db["pessoas"].find({}, {"nome_completo": 1})
    }

    programas_dict = {
        p["_id"]: p.get("nome_programa_area", "")
        for p in programas.find({}, {"nome_programa_area": 1})
    }

    registros = []

    for projeto in projetos_ispn.find():
        programa_nome = programas_dict.get(projeto.get("programa"), "")
        nome_projeto = projeto.get("nome_do_projeto") or projeto.get("sigla", "")

        for entrega in projeto.get("entregas", []):
            
            data_raw = entrega.get("previsao_da_conclusao")

            if not data_raw:
                continue  # pula entregas sem data

            try:
                data_conclusao = datetime.strptime(data_raw, "%d/%m/%Y")
            except ValueError:
                continue  # pula datas inválidas

            registros.append({
                "nome_da_entrega": entrega.get("nome_da_entrega"),
                
                "nome_do_projeto": nome_projeto,

                # PARA O GRÁFICO
                "previsao_da_conclusao": data_conclusao,

                # PARA A TABELA (JSON-safe)
                "previsao_da_conclusao_str": data_conclusao.strftime("%d/%m/%Y"),

                "responsaveis": resolver_responsaveis(
                    entrega.get("responsaveis", []),
                    pessoas
                ),
                "situacao": entrega.get("situacao"),
                "anos_de_referencia": ", ".join(entrega.get("anos_de_referencia", [])),
                "programa": programa_nome,
                "responsaveis_ids": [ObjectId(r) for r in entrega.get("responsaveis", [])]
            })

        COLUNAS_PADRAO = [
            "nome_da_entrega",
            "nome_do_projeto",
            "previsao_da_conclusao",
            "previsao_da_conclusao_str",
            "responsaveis",
            "situacao",
            "anos_de_referencia",
            "programa",
            "responsaveis_ids"
        ]

    df = pd.DataFrame(registros)

    # GARANTIA DE ESQUEMA
    for col in COLUNAS_PADRAO:
        if col not in df.columns:
            df[col] = None

    if df.empty:
        return df[COLUNAS_PADRAO]

    return (
        df[COLUNAS_PADRAO]
        .sort_values("previsao_da_conclusao", ascending=True)
        .reset_index(drop=True)
    )



def grafico_cronograma(df, titulo):
    
    if df.empty:
        st.info("Nenhuma entrega encontrada.")
        return

    hoje = datetime.today()
    df_plot = df.copy()
    
    df_plot = df_plot[
        df_plot["situacao"].isin(["Prevista", "Atrasada"])
    ]

    # Cria as colunas primeiro
    df_plot["Inicio"] = df_plot["previsao_da_conclusao"] - pd.Timedelta(days=5)
    df_plot["Fim"] = df_plot["previsao_da_conclusao"]
    
    xmin = min(df_plot["Inicio"].min(), hoje)
    xmax = max(df_plot["Fim"].max(), hoje)


    # Agora sim pode formatar a data
    df_plot["previsao_conclusao_hover"] = df_plot["Fim"].dt.strftime("%d/%m/%Y")

    # Ordena
    df_plot = df_plot.sort_values("Fim", ascending=False)

    altura_total = max(300, len(df_plot) * 45)

    fig = px.timeline(
        df_plot,
        x_start="Inicio",
        x_end="Fim",
        y="nome_da_entrega",
        color="situacao",
        custom_data=[
        "nome_da_entrega",
        "nome_do_projeto",
        "previsao_conclusao_hover",
        "responsaveis",
        "programa"
    ],
        height=altura_total,
        title=titulo
    )

    fig.update_traces(
        hovertemplate=
        "<b>Entrega:</b> %{customdata[0]}<br>"
        "<b>Projeto:</b> %{customdata[1]}<br>"
        "<b>Previsão de Conclusão:</b> %{customdata[2]}<br>"
        "<b>Responsáveis:</b> %{customdata[3]}<br>"
        "<b>Programa:</b> %{customdata[4]}<br>"
        "<extra></extra>"
    )


    fig.update_yaxes(
        categoryorder="array",
        categoryarray=df_plot["nome_da_entrega"].tolist(),
        title=""
    )

    fig.update_xaxes(
        range=[xmin, xmax],
        tickformat="%d/%m/%Y",
        tickangle=-45,
        #title="Previsão de Conclusão"
    )


    fig.update_layout(
        margin=dict(l=180, r=40, t=60, b=40)
    )

    st.plotly_chart(fig, width="stretch")


# ##########################################################
# Main
# ##########################################################


st.header("Entregas")

st.write("")

df_entregas = carregar_entregas()

COLUNAS_LEGIVEIS = {
    "nome_do_projeto": "Projeto",
    "nome_da_entrega": "Entrega",
    "previsao_da_conclusao_str": "Previsão de Conclusão",
    "responsaveis": "Responsáveis",
    "situacao": "Situação",
    "anos_de_referencia": "Anos de Referência",
    "programa": "Programa"
}

if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}:
    with st.container(horizontal_alignment="right"):
        st.write('')    
        if st.button("Gerenciar entregas", icon=":material/edit:", width=300):
            dialog_editar_entregas()


aba_minhas, aba_todas = st.tabs(["Minhas entregas","Todas as entregas"])

with aba_minhas:

    usuario_id = ObjectId(st.session_state["id_usuario"])

    df_minhas = df_entregas[
        df_entregas["responsaveis_ids"].apply(
            lambda x: usuario_id in x
        )
    ]

    ui.table(
        data=df_minhas[list(COLUNAS_LEGIVEIS.keys())]
            .rename(columns=COLUNAS_LEGIVEIS)
    )

    grafico_cronograma(
        df_minhas,
        "Cronograma de Entregas"
    )

with aba_todas:
   
    ui.table(
        data=df_entregas[list(COLUNAS_LEGIVEIS.keys())]
            .rename(columns=COLUNAS_LEGIVEIS)
    )

    grafico_cronograma(
        df_entregas,
        "Cronograma de Entregas"
    )
    
