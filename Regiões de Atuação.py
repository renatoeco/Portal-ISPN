import streamlit as st
import pymongo
import pydeck as pdk
import pandas as pd

from funcoes_auxiliares import conectar_mongo_portal_ispn


# =============================================================================
# CONFIG STREAMLIT
# =============================================================================
st.set_page_config(layout="wide")
st.title("Mapa de Regiões de Atuação — ISPN")


# =============================================================================
# 1. CONEXÃO COM O MONGODB
# =============================================================================
db = conectar_mongo_portal_ispn()

colecoes = ["projetos_pf", "projetos_pj", "projetos_ispn"]

regioes = []

for nome_colecao in colecoes:
    col = db[nome_colecao]
    docs = col.find({"regioes_atuacao": {"$exists": True, "$ne": []}})

    for doc in docs:
        for regiao in doc.get("regioes_atuacao", []):
            tipo = regiao.get("tipo")
            codigo = str(regiao.get("codigo"))

            if tipo and codigo:
                regioes.append({
                    "tipo": tipo,
                    "codigo": codigo,
                    "colecao": nome_colecao,
                    "projeto": doc.get("nome_do_projeto", ""),
                    "proponente": doc.get("proponente", "")
                })

df = pd.DataFrame(regioes)

st.dataframe(df)

if df.empty:
    st.warning("Nenhuma região encontrada nos projetos.")
    st.stop()


# =============================================================================
# 2. DICIONÁRIO DE TILESETS (VOCÊ PREENCHE COM OS SEUS)
# =============================================================================
TILESETS = {
    #"municipio":      "be-braga.4hwsg2i2",
    "estado":         "be-braga.4sp3fnvc"
    # "ti":             "usuario.terras_indigenas",
    # "uc":             "usuario.unidades_conservacao",
    # "bioma":          "usuario.biomas",
    # "quilombo":       "usuario.quilombos",
    # "assentamento":   "usuario.assentamentos",
    # "bacia_macro":    "usuario.bacia_macro",
    # "bacia_meso":     "usuario.bacia_meso",
    # "bacia_micro":    "usuario.bacia_micro",
}


# =============================================================================
# 3. CAMPOS DE FILTRO POR TILESET
# (VOCÊ AJUSTA CONFORME OS ATRIBUTOS DO SEU TILESET)
# =============================================================================
# Exemplos comuns do IBGE / INCRA / FUNAI / ANA
MAPBOX_FILTER_FIELD = {
    #"municipio": "id",          # Ex.: 2927408
    "estado": "CD_UF",           # Ex.: BA
    # "ti": "Cod_TI",
    # "uc": "cod_uc",
    # "bioma": "CD_BIOMA",
    # "quilombo": "cod_quil",
    # "assentamento": "cod_assent",
    # "bacia_macro": "CD_MACRO",
    # "bacia_meso": "CD_MESO",
    # "bacia_micro": "CD_MICRO",
}


# =============================================================================
# 4. CORES POR TIPO DE REGIÃO
# =============================================================================
CORES = {
    #"municipio":      [0, 140, 255],
    "estado":         [255, 150, 0],
    # "ti":             [255, 60, 60],
    # "uc":             [0, 200, 0],
    # "bioma":          [150, 70, 200],
    # "quilombo":       [120, 70, 20],
    # "assentamento":   [200, 150, 80],
    # "bacia_macro":    [0, 120, 200],
    # "bacia_meso":     [0, 160, 240],
    # "bacia_micro":    [100, 200, 240],
}


# =============================================================================
# 5. FUNÇÃO PARA CRIAR UMA CAMADA DO MAPBOX
# =============================================================================
def criar_layer_mapbox(tipo, codigo, cor_rgb):
    if tipo not in TILESETS:
        return None

    field = MAPBOX_FILTER_FIELD.get(tipo)
    if not field:
        return None

    codigo_val = int(codigo)
    if not codigo_val:
        return None

    # Valor literal (string) — necessário para o Mapbox
    codigo_literal = ["literal", codigo_val]

    # Fica dando erro nessa parte, não consigo entender o porquê
    filter_expr = ["==", ["get", field], codigo_literal]

    return pdk.Layer(
        "MVTLayer",
        data=f"mapbox://{TILESETS[tipo]}",
        pickable=True,
        get_fill_color=cor_rgb,
        opacity=0.5,
        filter=filter_expr,
        get_line_color=[0, 0, 0, 255]
    )


# =====================
# 6. CRIAR LISTA DE LAYERS
# =====================
layers = []

for _, row in df.drop_duplicates(subset=["tipo", "codigo"]).iterrows():
    tipo = row["tipo"]
    codigo = row["codigo"]

    # Pula tipos sem tileset definido
    if tipo not in TILESETS:
        continue

    cor = CORES.get(tipo, [200, 200, 200])

    layer = criar_layer_mapbox(tipo, codigo, cor)
    if layer:
        layers.append(layer)

# Se não tiver nenhuma layer válida
if len(layers) == 0:
    st.warning("Nenhuma camada válida para exibir no mapa!")
    st.stop()

# =====================
# 7. CONFIGURAÇÃO DO MAPA
# =====================
view_state = pdk.ViewState(
    latitude=-15.0,
    longitude=-54.0,
    zoom=4,
    pitch=0,
    bearing=0
)

deck = pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v9",
    initial_view_state=view_state,
    layers=layers,
    api_keys={"mapbox": st.secrets["MAPBOX"]["MAPBOX_TOKEN"]},
    tooltip={
        "html": "<b>Região</b>: {SIGLA_UF}",
        "style": {"color": "white"}
    }
)

st.pydeck_chart(deck)
