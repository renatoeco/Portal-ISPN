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
estatistica = db["estatistica"]


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
# CARREGAR DADOS
######################################################################


# Dados cadastrados no Mongo
df = pd.DataFrame(list(db.areas_atuacao.find()))

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
# CADASTRAR NOVAS ÁREAS
######################################################################


st.sidebar.header("Cadastrar nova área de atuação")

tipo_area = st.sidebar.selectbox(
    "Tipo de área",
    [
        "Município", "Estado", "Terra Indígena", "Unidade de Conservação", "Bioma",
        "Assentamento", "Quilombo",
        "Bacia Hidrográfica - Macro", "Bacia Hidrográfica - Meso", "Bacia Hidrográfica - Micro"
    ]
)

# ----------------------- MUNICÍPIOS -----------------------
if tipo_area == "Município":
    opcoes = munis[["code_muni", "name_muni", "abbrev_state"]]
    selecao = st.sidebar.selectbox(
        "Selecione o município",
        opcoes.apply(lambda x: f"{x['name_muni']} - {x['abbrev_state']} ({int(x['code_muni'])})", axis=1)
    )
    if st.sidebar.button("Adicionar município"):
        codigo = int(float(selecao.split("(")[-1].replace(")", "")))
        if db.areas_atuacao.find_one({"tipo": "municipio", "codigo": codigo}):
            st.sidebar.warning("Esse município já está cadastrado!")
        else:
            db.areas_atuacao.insert_one({"tipo": "municipio", "codigo": codigo})
            st.sidebar.success("Município adicionado!")

# ----------------------- ESTADOS -----------------------
elif tipo_area == "Estado":
    opcoes = estados[["code_state", "name_state"]]
    selecao = st.sidebar.selectbox(
        "Selecione o estado",
        opcoes.apply(lambda x: f"{x['name_state']} ({x['code_state']})", axis=1)
    )
    if st.sidebar.button("Adicionar estado"):
        codigo = int(float(selecao.split("(")[-1].replace(")", "")))
        if db.areas_atuacao.find_one({"tipo": "estado", "codigo": codigo}):
            st.sidebar.warning("Esse estado já está cadastrado!")
        else:
            db.areas_atuacao.insert_one({"tipo": "estado", "codigo": codigo})
            st.sidebar.success("Estado adicionado!")

# ----------------------- TERRAS INDÍGENAS -----------------------
elif tipo_area == "Terra Indígena":
    opcoes = terras_ind[["code_terrai", "terrai_nom"]]
    selecao = st.sidebar.selectbox(
        "Selecione a Terra Indígena",
        opcoes.apply(lambda x: f"{x['terrai_nom']} ({int(x['code_terrai'])})", axis=1)
    )
    if st.sidebar.button("Adicionar TI"):
        codigo = int(selecao.split("(")[-1].replace(")", ""))
        if db.areas_atuacao.find_one({"tipo": "terra_indigena", "codigo": codigo}):
            st.sidebar.warning("Essa Terra Indígena já está cadastrada!")
        else:
            db.areas_atuacao.insert_one({"tipo": "terra_indigena", "codigo": codigo})
            st.sidebar.success("Terra Indígena adicionada!")

# ----------------------- UNIDADES DE CONSERVAÇÃO -----------------------
elif tipo_area == "Unidade de Conservação":
    opcoes = uc[["code_conservation_unit", "name_conservation_unit"]]
    selecao = st.sidebar.selectbox(
        "Selecione a UC",
        opcoes.apply(lambda x: f"{x['name_conservation_unit']} ({x['code_conservation_unit']})", axis=1)
    )
    if st.sidebar.button("Adicionar UC"):
        codigo = int(float(selecao.split("(")[-1].replace(")", "")))
        if db.areas_atuacao.find_one({"tipo": "uc", "codigo": codigo}):
            st.sidebar.warning("Essa UC já está cadastrada!")
        else:
            db.areas_atuacao.insert_one({"tipo": "uc", "codigo": codigo})
            st.sidebar.success("UC adicionada!")

# ----------------------- BIOMAS -----------------------
elif tipo_area == "Bioma":
    opcoes = biomas[["code_biome", "name_biome"]].dropna(subset=["code_biome"])
    selecao = st.sidebar.selectbox(
        "Selecione o Bioma",
        opcoes.apply(lambda x: f"{x['name_biome']} ({int(float(x['code_biome']))})", axis=1)
    )
    if st.sidebar.button("Adicionar Bioma"):
        codigo = int(float(selecao.split("(")[-1].replace(")", "")))
        if db.areas_atuacao.find_one({"tipo": "bioma", "codigo": codigo}):
            st.sidebar.warning("Esse bioma já está cadastrado!")
        else:
            db.areas_atuacao.insert_one({"tipo": "bioma", "codigo": codigo})
            st.sidebar.success("Bioma adicionado!")

# ----------------------- ASSENTAMENTOS -----------------------
elif tipo_area == "Assentamento":
    opcoes = assentamentos[["cd_sipra", "nome_proje"]]
    selecao = st.sidebar.selectbox(
        "Selecione o Assentamento",
        opcoes.apply(lambda x: f"{x['nome_proje']} ({x['cd_sipra']})", axis=1)
    )
    if st.sidebar.button("Adicionar Assentamento"):
        codigo = selecao.split("(")[-1].replace(")", "").strip()
        if db.areas_atuacao.find_one({"tipo": "assentamento", "codigo": codigo}):
            st.sidebar.warning("Esse assentamento já está cadastrado!")
        else:
            db.areas_atuacao.insert_one({"tipo": "assentamento", "codigo": codigo})
            st.sidebar.success("Assentamento adicionado!")

# ----------------------- QUILOMBOS -----------------------
elif tipo_area == "Quilombo":
    opcoes = quilombos[["id", "name"]]
    selecao = st.sidebar.selectbox(
        "Selecione o Quilombo",
        opcoes.apply(lambda x: f"{x['name']} ({x['id']})", axis=1)
    )
    if st.sidebar.button("Adicionar Quilombo"):
        codigo = selecao.split("(")[-1].replace(")", "").strip()
        if db.areas_atuacao.find_one({"tipo": "quilombo", "codigo": codigo}):
            st.sidebar.warning("Esse quilombo já está cadastrado!")
        else:
            db.areas_atuacao.insert_one({"tipo": "quilombo", "codigo": codigo})
            st.sidebar.success("Quilombo adicionado!")
            
# ----------------------- BACIA HIDROGRÁFICA - MICRO -----------------------
elif tipo_area == "Bacia Hidrográfica - Micro":
    nome_col = next((c for c in bacias_micro.columns if "nome" in c.lower() or "bacia" in c.lower()), None)
    codigo_col = next((c for c in bacias_micro.columns if "cod" in c.lower() or "id" in c.lower()), None)
    opcoes = bacias_micro[[codigo_col, nome_col]]
    selecao = st.sidebar.selectbox(
        "Selecione a Bacia (Micro)",
        opcoes.apply(lambda x: f"{x[nome_col]} ({x[codigo_col]})", axis=1)
    )
    if st.sidebar.button("Adicionar Bacia Micro"):
        codigo = selecao.split("(")[-1].replace(")", "").strip()
        if db.areas_atuacao.find_one({"tipo": "bacia_micro", "codigo": codigo}):
            st.sidebar.warning("Essa Bacia Micro já está cadastrada!")
        else:
            db.areas_atuacao.insert_one({"tipo": "bacia_micro", "codigo": codigo})
            st.sidebar.success("Bacia Micro adicionada!")

# ----------------------- BACIA HIDROGRÁFICA - MESO -----------------------
elif tipo_area == "Bacia Hidrográfica - Meso":
    nome_col = next((c for c in bacias_meso.columns if "nome" in c.lower() or "bacia" in c.lower()), None)
    codigo_col = next((c for c in bacias_meso.columns if "cod" in c.lower() or "id" in c.lower()), None)
    opcoes = bacias_meso[[codigo_col, nome_col]]
    selecao = st.sidebar.selectbox(
        "Selecione a Bacia (Meso)",
        opcoes.apply(lambda x: f"{x[nome_col]} ({x[codigo_col]})", axis=1)
    )
    if st.sidebar.button("Adicionar Bacia Meso"):
        codigo = selecao.split("(")[-1].replace(")", "").strip()
        if db.areas_atuacao.find_one({"tipo": "bacia_meso", "codigo": codigo}):
            st.sidebar.warning("Essa Bacia Meso já está cadastrada!")
        else:
            db.areas_atuacao.insert_one({"tipo": "bacia_meso", "codigo": codigo})
            st.sidebar.success("Bacia Meso adicionada!")

# ----------------------- BACIA HIDROGRÁFICA - MACRO -----------------------
elif tipo_area == "Bacia Hidrográfica - Macro":
    nome_col = next((c for c in bacias_macro.columns if "nome" in c.lower() or "bacia" in c.lower()), None)
    codigo_col = next((c for c in bacias_macro.columns if "cod" in c.lower() or "id" in c.lower()), None)
    opcoes = bacias_macro[[codigo_col, nome_col]]
    selecao = st.sidebar.selectbox(
        "Selecione a Bacia (Macro)",
        opcoes.apply(lambda x: f"{x[nome_col]} ({x[codigo_col]})", axis=1)
    )
    if st.sidebar.button("Adicionar Bacia Macro"):
        codigo = selecao.split("(")[-1].replace(")", "").strip()
        if db.areas_atuacao.find_one({"tipo": "bacia_macro", "codigo": codigo}):
            st.sidebar.warning("Essa Bacia Macro já está cadastrada!")
        else:
            db.areas_atuacao.insert_one({"tipo": "bacia_macro", "codigo": codigo})
            st.sidebar.success("Bacia Macro adicionada!")


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

        if row["tipo"] == "municipio" and show_munis:
            sel = munis[munis["code_muni"] == row["codigo"]]
            folium.GeoJson(
                sel,
                name=f"Município {row['codigo']}", 
                style_function=lambda x: {"color": "orange", "weight": 1, "fillOpacity": 0.6},
                tooltip=folium.GeoJsonTooltip(fields=["name_muni"], aliases=["Município:"], sticky=True)
            ).add_to(mapa)

        elif row["tipo"] == "estado" and show_estados:
            sel = estados[estados["code_state"] == row["codigo"]]
            folium.GeoJson(
                sel, 
                name=f"Estado {row['codigo']}", 
                style_function=lambda x: {"color": "purple", "weight": 2, "fillOpacity": 0.3}, 
                tooltip=folium.GeoJsonTooltip(fields=["name_state"], aliases=["Estado:"], sticky=True)
            ).add_to(mapa)

        elif row["tipo"] == "terra_indigena" and show_terras_indigenas:
            sel = terras_ind[terras_ind["code_terrai"] == row["codigo"]]
            folium.GeoJson(
                sel,
                name=f"TI {row['codigo']}", 
                style_function=lambda x: {"color": "brown", "weight": 2, "fillOpacity": 0.5},
                tooltip=folium.GeoJsonTooltip(fields=["terrai_nom"], aliases=["Terra Indígena:"], sticky=True)
            ).add_to(mapa)

        elif row["tipo"] == "uc" and show_uc:
            uc["code_conservation_unit"] = uc["code_conservation_unit"].astype(int)
            codigo_uc = int(row["codigo"])
            sel = uc[uc["code_conservation_unit"] == codigo_uc].copy()
            if not sel.empty:
                sel["name_conservation_unit"] = sel["name_conservation_unit"].astype(str)
                folium.GeoJson(
                    sel.to_json(),
                    name=f"UC {codigo_uc}",
                    style_function=lambda x: {"color": "darkgreen", "weight": 2, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(
                        fields=["name_conservation_unit"],
                        aliases=["Unidade de Conservação:"],
                        sticky=True
                    )
                ).add_to(mapa)

        elif row["tipo"] == "bioma" and show_biomas:
            biomas = biomas.dropna(subset=["code_biome"]).copy()
            biomas["code_biome"] = biomas["code_biome"].astype(int)
            codigo_bioma = int(row["codigo"])
            sel = biomas[biomas["code_biome"] == codigo_bioma].copy()
            if not sel.empty:
                sel["name_biome"] = sel["name_biome"].astype(str)
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bioma {codigo_bioma}",
                    style_function=lambda x: {"color": "blue", "weight": 2, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(
                        fields=["name_biome"],
                        aliases=["Bioma:"],
                        sticky=True
                    )
                ).add_to(mapa)

        elif row["tipo"] == "assentamento" and show_assentamentos:
            sel = assentamentos[assentamentos["cd_sipra"] == row["codigo"]]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Assentamento {row['codigo']}",
                    style_function=lambda x: {"color": "yellow", "weight": 2, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(
                        fields=["nome_proje"],
                        aliases=["Assentamento:"],
                        sticky=True
                    )
                ).add_to(mapa)

        elif row["tipo"] == "quilombo" and show_quilombos:
            sel = quilombos[quilombos["id"].astype(str) == str(row["codigo"])]

            sel_json = sel.copy()

            for col in sel_json.select_dtypes(include=["datetime64[ns]"]).columns:
                sel_json[col] = sel_json[col].astype(str)

            if not sel.empty:
                folium.GeoJson(
                    sel_json.to_json(),
                    name=f"Quilombo {row['codigo']}",
                    style_function=lambda x: {"color": "black", "weight": 2, "fillOpacity": 0.5},
                    tooltip=folium.GeoJsonTooltip(
                        fields=["name"],
                        aliases=["Quilombo:"],
                        sticky=True
                    )
                ).add_to(mapa)
                
        elif row["tipo"] == "bacia_micro" and show_bacias_micro:
            nome_col = next((c for c in bacias_micro.columns if "nome" in c.lower() or "bacia" in c.lower()), "nome")
            codigo_col = next((c for c in bacias_micro.columns if "cod" in c.lower() or "id" in c.lower()), "codigo")
            sel = bacias_micro[bacias_micro[codigo_col].astype(str) == str(row["codigo"])]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bacia Micro {row['codigo']}",
                    style_function=lambda x: {"color": "cyan", "weight": 2, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=[nome_col], aliases=["Bacia Micro:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "bacia_meso" and show_bacias_meso:
            nome_col = next((c for c in bacias_meso.columns if "nome" in c.lower() or "bacia" in c.lower()), "nome")
            codigo_col = next((c for c in bacias_meso.columns if "cod" in c.lower() or "id" in c.lower()), "codigo")
            sel = bacias_meso[bacias_meso[codigo_col].astype(str) == str(row["codigo"])]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bacia Meso {row['codigo']}",
                    style_function=lambda x: {"color": "blue", "weight": 2, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=[nome_col], aliases=["Bacia Meso:"], sticky=True)
                ).add_to(mapa)

        elif row["tipo"] == "bacia_macro" and show_bacias_macro:
            nome_col = next((c for c in bacias_macro.columns if "nome" in c.lower() or "bacia" in c.lower()), "nome")
            codigo_col = next((c for c in bacias_macro.columns if "cod" in c.lower() or "id" in c.lower()), "codigo")
            sel = bacias_macro[bacias_macro[codigo_col].astype(str) == str(row["codigo"])]
            if not sel.empty:
                folium.GeoJson(
                    sel.to_json(),
                    name=f"Bacia Macro {row['codigo']}",
                    style_function=lambda x: {"color": "navy", "weight": 2, "fillOpacity": 0.3},
                    tooltip=folium.GeoJsonTooltip(fields=[nome_col], aliases=["Bacia Macro:"], sticky=True)
                ).add_to(mapa)


# Adiciona controle de camadas
folium.LayerControl().add_to(mapa)

# Exibe o mapa
st_folium(mapa, width=1600, height=600)
