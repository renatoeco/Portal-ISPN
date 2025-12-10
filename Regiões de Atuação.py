import streamlit as st
import pydeck as pdk
import geopandas as gpd
from funcoes_auxiliares import conectar_mongo_portal_ispn
import pandas as pd


st.set_page_config(layout="wide")


###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
###########################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]


######################################################################
# CARREGAR DADOS DAS REGIÕES DE ATUAÇÃO (de projetos)
######################################################################

colecoes = ["projetos_pf", "projetos_pj", "projetos_ispn"]

regioes = []

for nome_colecao in colecoes:
    colecao = db[nome_colecao]
    documentos = colecao.find({"regioes_atuacao": {"$exists": True, "$ne": []}})

    for doc in documentos:
        for regiao in doc.get("regioes_atuacao", []):
            tipo = regiao.get("tipo")
            codigo = regiao.get("codigo")

            if tipo and codigo:
                regioes.append({
                    "tipo": tipo,
                    "codigo": str(codigo),
                    "colecao_origem": nome_colecao,
                    "projeto_id": str(doc["_id"]),
                    "nome_projeto": doc.get("nome_do_projeto", ""),
                    "proponente": doc.get("proponente", "")
                })

# Converte para DataFrame
df = pd.DataFrame(regioes)


def corrigir_codigo(df, coluna_codigo):
    df[coluna_codigo] = (
        df[coluna_codigo]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )
    return df


######################################################################
# MAPA
######################################################################


# Verifica os tipos que existem na coleção
tipos_existentes = df["tipo"].unique() if not df.empty else []

# Checkboxes para filtrar camadas (todos desmarcados por padrão)
show_munis = st.checkbox("Municípios", value=False)
show_estados = st.checkbox("Estados", value=False)
show_terras_indigenas = st.checkbox("Terras Indígenas", value=False)
show_uc = st.checkbox("Unidades de Conservação", value=False)
show_biomas = st.checkbox("Biomas", value=False)
show_assentamentos = st.checkbox("Assentamentos", value=False)
show_quilombos = st.checkbox("Quilombo", value=False)
show_bacias_macro = st.checkbox("Bacias Hidrográficas - Macro", value=False)
show_bacias_meso = st.checkbox("Bacias Hidrográficas - Meso", value=False)
show_bacias_micro = st.checkbox("Bacias Hidrográficas - Micro", value=False)


######################################################################
# AGRUPAR REGIÕES E CONTAR PROJETOS
######################################################################


# Contagem de quantos projetos estão em cada região
contagem = df.groupby(["tipo", "codigo"]).size().reset_index(name="qtd_projetos")

# Mescla com a contagem dentro do df principal (sem duplicatas)
df_unico = (
    df.drop_duplicates(subset=["tipo", "codigo"])
    .merge(contagem, on=["tipo", "codigo"], how="left")
    .fillna({"qtd_projetos": 0})
)
