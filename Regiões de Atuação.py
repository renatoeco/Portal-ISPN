# import streamlit as st
# import pydeck as pdk
# import json
# from funcoes_auxiliares import conectar_mongo_portal_ispn

# st.set_page_config(layout="wide")
# st.title("Mapa de Regiões de Atuação — ISPN")

# # =============================================================================
# # 1. MongoDB → códigos de UF
# # =============================================================================
# db = conectar_mongo_portal_ispn()

# colecoes = ["projetos_pf", "projetos_pj", "projetos_ispn"]
# regioes = []

# codigos_ufs = set()
# codigos_municipios = set()

# for nome in colecoes:
#     for doc in db[nome].find({"regioes_atuacao": {"$exists": True, "$ne": []}}):
#         for r in doc["regioes_atuacao"]:
#             if r.get("tipo") == "estado":
#                 try:
#                     codigos_ufs.add(int(r["codigo"]))
#                 except:
#                     pass

#             elif r.get("tipo") == "municipio":
#                 try:
#                     codigos_municipios.add(str(r["codigo"]))  # município = string
#                 except:
#                     pass

# #st.write("Estados encontrados (CD_UF):", codigos)

# # =============================================================================
# # 2. GeoJSON das UFs
# # =============================================================================

# with open(
#     r"geojsons\brazil-states.geojson",
#     encoding="utf-8"
# ) as f:
#     geojson_ufs = json.load(f)

# with open(
#     r"geojsons\geojs-100-mun.json",
#     encoding="utf-8"
# ) as f:
#     geojson_municipios = json.load(f)


# # =============================================================================
# # 3. Layer GeoJson (AQUI FUNCIONA)
# # =============================================================================
# layer_ufs = pdk.Layer(
#     "GeoJsonLayer",
#     data=geojson_ufs,
#     pickable=True,
#     filled=True,
#     stroked=True,
#     opacity=0.6,

#     get_fill_color=[
#         "case",
#         ["in", ["get", "codigo_ibg"], ["literal", list(codigos_ufs)]],
#         [255, 150, 0, 120],   # laranja claro
#         [220, 220, 220, 40],  # fundo bem leve
#     ],

#     get_line_color=[80, 80, 80, 120],
#     line_width_min_pixels=1,
# )


# layer_municipios = pdk.Layer(
#     "GeoJsonLayer",
#     data=geojson_municipios,
#     pickable=True,
#     filled=True,
#     stroked=False,

#     get_fill_color=[
#         "case",
#         ["in", ["get", "id"], ["literal", list(codigos_municipios)]],
#         #[0, 120, 255, 160],   # azul
#         #[0, 0, 0, 0],         # invisível
#     ],

#     line_width_min_pixels=3,

#     #get_elevation=0,
# )


# # =============================================================================
# # 4. Mapa
# # =============================================================================
# tooltip = {
#     "html": "<b>{name}</b>",
#     "style": {"backgroundColor": "rgba(0,0,0,0.7)", "color": "white"}
# }


# deck = pdk.Deck(
#     map_style="mapbox://styles/mapbox/light-v9",
#     initial_view_state=pdk.ViewState(
#         latitude=-15,
#         longitude=-54,
#         zoom=4.5,
#     ),
#     layers=[
#         layer_ufs,
#         #layer_municipios,  
#     ],
#     tooltip=tooltip,
#     api_keys={"mapbox": st.secrets["MAPBOX"]["MAPBOX_TOKEN"]},
# )

# st.pydeck_chart(deck)


#CODIGO COM MAPBOX


import streamlit as st
import pydeck as pdk
from funcoes_auxiliares import conectar_mongo_portal_ispn

st.set_page_config(layout="wide")
st.title("Mapa de Regiões de Atuação — ISPN")

# =============================================================================
# 1. MongoDB → códigos de UF
# =============================================================================
db = conectar_mongo_portal_ispn()

colecoes = ["projetos_pf", "projetos_pj", "projetos_ispn"]
regioes = []

for nome in colecoes:
    for doc in db[nome].find({"regioes_atuacao": {"$exists": True, "$ne": []}}):
        for r in doc["regioes_atuacao"]:
            if r.get("tipo") == "estado":
                try:
                    regioes.append(int(r["codigo"]))
                except:
                    pass

codigos = sorted(set(regioes))

if not codigos:
    st.warning("Nenhum estado encontrado.")
    st.stop()

#st.write("Estados encontrados (CD_UF):", codigos)

# TILESET_ESTADOS = "mapbox://be-braga.983ceeql"
CAMPO_UF = "codigo_ibg"

layer_ufs = pdk.Layer(
    "MVTLayer",
    data="mapbox://be-braga.983ceeql",
    pickable=True,
    filled=True,
    stroked=True,
    opacity=0.7,

    loadOptions={
        "mvt": {
            "layers": ["brazil-states-2q8gfm"]
        }
    },

    get_fill_color=[
        "case",
        ["in", ["get", "id"], ["literal", codigos]],
        [255, 150, 0, 180],
        [200, 200, 200, 30],
    ],

    get_line_color=[0, 0, 0, 200],
    line_width_min_pixels=1,
)


deck = pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v9",
    initial_view_state=pdk.ViewState(
        latitude=-15,
        longitude=-54,
        zoom=4.5,
    ),
    layers=[layer_ufs],
    api_keys={"mapbox": st.secrets["MAPBOX"]["MAPBOX_TOKEN"]},
    tooltip={
        "text": "{name}"  # ou {sigla}, depende do tileset
    },
)

st.pydeck_chart(deck)



