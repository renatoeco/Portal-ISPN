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


def corrigir_codigo(df, coluna_codigo):
    df[coluna_codigo] = (
        df[coluna_codigo]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.strip()
    )
    return df

# Dados geográficos cacheados
munis = corrigir_codigo(carregar_municipios(), "code_muni")
munis["geometry"] = munis["geometry"].simplify(tolerance=0.01, preserve_topology=True)

estados = corrigir_codigo(carregar_estados(), "code_state")
estados["geometry"] = estados["geometry"].simplify(tolerance=0.01, preserve_topology=True)

terras_ind = corrigir_codigo(carregar_terras_indigenas(), "code_terrai")
terras_ind["geometry"] = terras_ind["geometry"].simplify(tolerance=0.01, preserve_topology=True)

uc = corrigir_codigo(carregar_uc(), "code_conservation_unit")
uc["geometry"] = uc["geometry"].simplify(tolerance=0.01, preserve_topology=True)

biomas = corrigir_codigo(carregar_biomas(), "code_biome")
biomas["geometry"] = biomas["geometry"].simplify(tolerance=0.01, preserve_topology=True)

assentamentos = carregar_assentamentos()
assentamentos["geometry"] = assentamentos["geometry"].simplify(tolerance=0.01, preserve_topology=True)

quilombos = carregar_quilombos()
quilombos["geometry"] = quilombos["geometry"].simplify(tolerance=0.01, preserve_topology=True)

# --- Carregar e padronizar nomes das colunas das bacias ---
bacias_micro = carregar_bacias_micro().rename(
    columns={"cd_microRH": "codigo", "nm_microRH": "nome"}
)
bacias_micro["geometry"] = bacias_micro["geometry"].simplify(tolerance=0.01, preserve_topology=True)


bacias_meso = carregar_bacias_meso().rename(
    columns={"cd_mesoRH": "codigo", "nm_mesoRH": "nome"}
)
bacias_meso["geometry"] = bacias_meso["geometry"].simplify(tolerance=0.01, preserve_topology=True)

bacias_macro = carregar_bacias_macro().rename(
    columns={"cd_macroRH": "codigo", "nm_macroRH": "nome"}
)
bacias_macro["geometry"] = bacias_macro["geometry"].simplify(tolerance=0.01, preserve_topology=True)


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


######################################################################
# AGRUPAR REGIÕES E CONTAR PROJETOS
######################################################################

# Garante que todos os códigos são strings sem espaços
df["codigo"] = df["codigo"].astype(str).str.strip()
df["tipo"] = df["tipo"].astype(str).str.strip()

# Contagem de quantos projetos estão em cada região
contagem = df.groupby(["tipo", "codigo"]).size().reset_index(name="qtd_projetos")

# Mescla com a contagem dentro do df principal (sem duplicatas)
df_unico = (
    df.drop_duplicates(subset=["tipo", "codigo"])
    .merge(contagem, on=["tipo", "codigo"], how="left")
    .fillna({"qtd_projetos": 0})
)

# Adiciona áreas de atuação cadastradas
if not df.empty:
    for _, row in df_unico.iterrows():
        codigo_str = str(row["codigo"]).strip()
        qtd = int(row.get("qtd_projetos", 0))

        if row["tipo"] == "municipio" and show_munis:
            sel = munis[munis["code_muni"].astype(str).str.strip() == codigo_str]
            if not sel.empty:
                sel = sel.copy()
                sel["tooltip_info"] = sel["name_muni"] + f" — {qtd} projeto(s)"
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Município {codigo_str}",
                    style_function=lambda x: {"color": "orange", "weight": 0, "fillOpacity": 0.6},
                    tooltip=folium.GeoJsonTooltip(fields=["tooltip_info"], aliases=["Município:"], sticky=True, labels=True)
                ).add_to(mapa)

        elif row["tipo"] == "estado" and show_estados:
            sel = estados[estados["code_state"].astype(str).str.strip() == codigo_str]
            if not sel.empty:
                sel = sel.copy()
                sel["tooltip_info"] = sel["name_state"] + f" — {qtd} projeto(s)"
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Estado {codigo_str}",
                    style_function=lambda x: {"color": "purple", "weight": 0, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=["tooltip_info"], aliases=["Estado:"], sticky=True, labels=True)
                ).add_to(mapa)

        elif row["tipo"] == "terra_indigena" and show_terras_indigenas:
            sel = terras_ind[terras_ind["code_terrai"].astype(str) == codigo_str]
            if not sel.empty:
                sel = sel.copy()
                sel["tooltip_info"] = sel["terrai_nom"] + f" — {qtd} projeto(s)"
                folium.GeoJson(
                    sel.to_json(),
                    name=f"TI {codigo_str}",
                    style_function=lambda x: {"color": "brown", "weight": 0, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(fields=["tooltip_info"], aliases=["Terra Indígena:"], sticky=True, labels=True)
                ).add_to(mapa)

        elif row["tipo"] == "uc" and show_uc:
            sel = uc[uc["code_conservation_unit"].astype(str) == codigo_str]
            if not sel.empty:
                sel = sel.copy()
                sel["tooltip_info"] = sel["name_conservation_unit"] + f" — {qtd} projeto(s)"
                folium.GeoJson(
                    sel.to_json(),
                    name=f"UC {codigo_str}",
                    style_function=lambda x: {"color": "darkgreen", "weight": 0, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(fields=["tooltip_info"], aliases=["Unidade de Conservação:"], sticky=True, labels=True)
                ).add_to(mapa)

        elif row["tipo"] == "bioma" and show_biomas:
            sel = biomas[biomas["code_biome"].astype(str) == codigo_str]
            if not sel.empty:
                sel = sel.copy()
                sel["tooltip_info"] = sel["name_biome"] + f" — {qtd} projeto(s)"
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bioma {codigo_str}",
                    style_function=lambda x: {"color": "blue", "weight": 0, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=["tooltip_info"], aliases=["Bioma:"], sticky=True, labels=True)
                ).add_to(mapa)

        elif row["tipo"] == "assentamento" and show_assentamentos:
            sel = assentamentos[assentamentos["cd_sipra"].astype(str) == codigo_str]
            if not sel.empty:
                sel = sel.copy()
                sel["tooltip_info"] = sel["nome_proje"] + f" — {qtd} projeto(s)"
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Assentamento {codigo_str}",
                    style_function=lambda x: {"color": "yellow", "weight": 0, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(fields=["tooltip_info"], aliases=["Assentamento:"], sticky=True, labels=True)
                ).add_to(mapa)

        elif row["tipo"] == "quilombo" and show_quilombos:
            sel = quilombos[quilombos["id"].astype(str) == codigo_str]
            if not sel.empty:
                sel = sel.copy()
                sel["tooltip_info"] = sel["name"] + f" — {qtd} projeto(s)"
                for col in sel.select_dtypes(include=["datetime64[ns]"]).columns:
                    sel[col] = sel[col].astype(str)
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Quilombo {codigo_str}",
                    style_function=lambda x: {"color": "black", "weight": 0, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(fields=["tooltip_info"], aliases=["Quilombo:"], sticky=True, labels=True)
                ).add_to(mapa)

        elif row["tipo"] == "bacia_micro" and show_bacias_micro:
            nome_col = next((c for c in bacias_micro.columns if "nome" in c.lower() or "bacia" in c.lower()), "nome")
            codigo_col = next((c for c in bacias_micro.columns if "cod" in c.lower() or "id" in c.lower()), "codigo")
            sel = bacias_micro[bacias_micro[codigo_col].astype(str) == codigo_str]
            if not sel.empty:
                sel = sel.copy()
                sel["tooltip_info"] = sel[nome_col] + f" — {qtd} projeto(s)"
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bacia Micro {codigo_str}",
                    style_function=lambda x: {"color": "cyan", "weight": 0, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=["tooltip_info"], aliases=["Bacia Micro:"], sticky=True, labels=True)
                ).add_to(mapa)

        elif row["tipo"] == "bacia_meso" and show_bacias_meso:
            nome_col = next((c for c in bacias_meso.columns if "nome" in c.lower() or "bacia" in c.lower()), "nome")
            codigo_col = next((c for c in bacias_meso.columns if "cod" in c.lower() or "id" in c.lower()), "codigo")
            sel = bacias_meso[bacias_meso[codigo_col].astype(str) == codigo_str]
            if not sel.empty:
                sel = sel.copy()
                sel["tooltip_info"] = sel[nome_col] + f" — {qtd} projeto(s)"
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bacia Meso {codigo_str}",
                    style_function=lambda x: {"color": "blue", "weight": 0, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=["tooltip_info"], aliases=["Bacia Meso:"], sticky=True, labels=True)
                ).add_to(mapa)

        elif row["tipo"] == "bacia_macro" and show_bacias_macro:
            nome_col = next((c for c in bacias_macro.columns if "nome" in c.lower() or "bacia" in c.lower()), "nome")
            codigo_col = next((c for c in bacias_macro.columns if "cod" in c.lower() or "id" in c.lower()), "codigo")
            sel = bacias_macro[bacias_macro[codigo_col].astype(str) == codigo_str]
            if not sel.empty:
                sel = sel.copy()
                sel["tooltip_info"] = sel[nome_col] + f" — {qtd} projeto(s)"
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bacia Macro {codigo_str}",
                    style_function=lambda x: {"color": "navy", "weight": 0, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=["tooltip_info"], aliases=["Bacia Macro:"], sticky=True, labels=True)
                ).add_to(mapa)

# Adiciona controle de camadas
folium.LayerControl().add_to(mapa)

# Exibe o mapa
st_folium(mapa, width=1600, height=600, returned_objects=[])