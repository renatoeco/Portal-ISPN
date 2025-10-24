import streamlit as st
from datetime import datetime
import pandas as pd
import folium
import geopandas as gpd
from geobr import read_municipality, read_state, read_indigenous_land, read_conservation_units, read_biomes
from streamlit_folium import st_folium
from funcoes_auxiliares import conectar_mongo_portal_ispn


st.set_page_config(layout="wide")


###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
###########################################################################################################


db = conectar_mongo_portal_ispn()
#estatistica = db["estatistica"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################

# # Nome da página atual, usado como chave para contagem de acessos
# nome_pagina = "Regiões de Atuação"

# # Cria um timestamp formatado com dia/mês/ano hora:minuto:segundo
# timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# # Cria o nome do campo dinamicamente baseado na página
# campo_timestamp = f"{nome_pagina}.Visitas"

# # Atualiza a coleção de estatísticas com o novo acesso, incluindo o timestamp
# estatistica.update_one(
#     {},
#     {"$push": {campo_timestamp: timestamp}},
#     upsert=True  # Cria o documento se ele ainda não existir
# )


######################################################################
# FUNÇÕES COM CACHE
######################################################################


@st.cache_data(show_spinner="Carregando municípios...")
def carregar_municipios(ano=2024):
    return read_municipality(year=ano)

@st.cache_data(show_spinner="Carregando estados...")
def carregar_estados(ano=2020):
    return read_state(year=ano)

@st.cache_data(show_spinner="Carregando terras indígenas...")
def carregar_terras_indigenas(data=201907):
    return read_indigenous_land(date=data)

@st.cache_data(show_spinner="Carregando unidades de conservação...")
def carregar_uc(data=201909):
    return read_conservation_units(date=data)

@st.cache_data(show_spinner="Carregando biomas...")
def carregar_biomas(ano=2019):
    return read_biomes(year=ano)

@st.cache_data(show_spinner="Carregando assentamentos...")
def carregar_assentamentos():
    return gpd.read_file("shapefiles/Assentamentos-SAB-INCRA.shp")

@st.cache_data(show_spinner="Carregando quilombos...")
def carregar_quilombos():
    return gpd.read_file("shapefiles/Quilombos-SAB-INCRA.shp")

@st.cache_data(show_spinner="Carregando bacias hidrográficas (micro)...")
def carregar_bacias_micro():
    return gpd.read_file("shapefiles/micro_RH.shp")

@st.cache_data(show_spinner="Carregando bacias hidrográficas (meso)...")
def carregar_bacias_meso():
    return gpd.read_file("shapefiles/meso_RH.shp")

@st.cache_data(show_spinner="Carregando bacias hidrográficas (macro)...")
def carregar_bacias_macro():
    return gpd.read_file("shapefiles/macro_RH.shp")


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

# Dados geográficos cacheados
munis = carregar_municipios()
estados = carregar_estados()
terras_ind = carregar_terras_indigenas()
uc = carregar_uc()
biomas = carregar_biomas()
assentamentos = carregar_assentamentos()
quilombos = carregar_quilombos()

# --- Carregar e padronizar nomes das colunas das bacias ---
bacias_micro = carregar_bacias_micro().rename(
    columns={"cd_microRH": "codigo", "nm_microRH": "nome"}
)
bacias_meso = carregar_bacias_meso().rename(
    columns={"cd_mesoRH": "codigo", "nm_mesoRH": "nome"}
)
bacias_macro = carregar_bacias_macro().rename(
    columns={"cd_macroRH": "codigo", "nm_macroRH": "nome"}
)


######################################################################
# MAPA
######################################################################


# Verifica os tipos que existem na coleção
tipos_existentes = df["tipo"].unique() if not df.empty else []

# Cria o mapa base
mapa = folium.Map(location=[-19.0, -38.0], zoom_start=4)

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

# Adiciona áreas de atuação cadastradas
if not df.empty:
    for _, row in df.iterrows():
        codigo_str = str(row["codigo"]).strip()  # garante tipo string e remove espaços

        if row["tipo"] == "municipio" and show_munis:
            sel = munis[munis["code_muni"].astype(str) == codigo_str]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Município {codigo_str}",
                    style_function=lambda x: {"color": "orange", "weight": 0, "fillOpacity": 0.6},
                    tooltip=folium.GeoJsonTooltip(fields=["name_muni"], aliases=["Município:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "estado" and show_estados:
            sel = estados[estados["code_state"].astype(str) == codigo_str]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Estado {codigo_str}",
                    style_function=lambda x: {"color": "purple", "weight": 0, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=["name_state"], aliases=["Estado:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "terra_indigena" and show_terras_indigenas:
            sel = terras_ind[terras_ind["code_terrai"].astype(str) == codigo_str]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"TI {codigo_str}",
                    style_function=lambda x: {"color": "brown", "weight": 0, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(fields=["terrai_nom"], aliases=["Terra Indígena:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "uc" and show_uc:
            sel = uc[uc["code_conservation_unit"].astype(str) == codigo_str]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"UC {codigo_str}",
                    style_function=lambda x: {"color": "darkgreen", "weight": 0, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(fields=["name_conservation_unit"], aliases=["Unidade de Conservação:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "bioma" and show_biomas:
            sel = biomas[biomas["code_biome"].astype(str) == codigo_str]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bioma {codigo_str}",
                    style_function=lambda x: {"color": "blue", "weight": 0, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=["name_biome"], aliases=["Bioma:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "assentamento" and show_assentamentos:
            sel = assentamentos[assentamentos["cd_sipra"].astype(str) == codigo_str]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Assentamento {codigo_str}",
                    style_function=lambda x: {"color": "yellow", "weight": 0, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(fields=["nome_proje"], aliases=["Assentamento:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "quilombo" and show_quilombos:
            sel = quilombos[quilombos["id"].astype(str) == codigo_str]
            if not sel.empty:
                sel_json = sel.copy()
                for col in sel_json.select_dtypes(include=["datetime64[ns]"]).columns:
                    sel_json[col] = sel_json[col].astype(str)
                folium.GeoJson(
                    sel_json.to_json(),
                    name=f"Quilombo {codigo_str}",
                    style_function=lambda x: {"color": "black", "weight": 0, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Quilombo:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "bacia_micro" and show_bacias_micro:
            nome_col = next((c for c in bacias_micro.columns if "nome" in c.lower() or "bacia" in c.lower()), "nome")
            codigo_col = next((c for c in bacias_micro.columns if "cod" in c.lower() or "id" in c.lower()), "codigo")
            sel = bacias_micro[bacias_micro[codigo_col].astype(str) == codigo_str]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bacia Micro {codigo_str}",
                    style_function=lambda x: {"color": "cyan", "weight": 0, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=[nome_col], aliases=["Bacia Micro:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "bacia_meso" and show_bacias_meso:
            nome_col = next((c for c in bacias_meso.columns if "nome" in c.lower() or "bacia" in c.lower()), "nome")
            codigo_col = next((c for c in bacias_meso.columns if "cod" in c.lower() or "id" in c.lower()), "codigo")
            sel = bacias_meso[bacias_meso[codigo_col].astype(str) == codigo_str]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bacia Meso {codigo_str}",
                    style_function=lambda x: {"color": "blue", "weight": 0, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=[nome_col], aliases=["Bacia Meso:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "bacia_macro" and show_bacias_macro:
            nome_col = next((c for c in bacias_macro.columns if "nome" in c.lower() or "bacia" in c.lower()), "nome")
            codigo_col = next((c for c in bacias_macro.columns if "cod" in c.lower() or "id" in c.lower()), "codigo")
            sel = bacias_macro[bacias_macro[codigo_col].astype(str) == codigo_str]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bacia Macro {codigo_str}",
                    style_function=lambda x: {"color": "navy", "weight": 0, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=[nome_col], aliases=["Bacia Macro:"], sticky=True)
                ).add_to(mapa)



# Adiciona controle de camadas
folium.LayerControl().add_to(mapa)

# Exibe o mapa
st_folium(mapa, width=1600, height=600, returned_objects=[])
