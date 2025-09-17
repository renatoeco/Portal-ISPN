import streamlit as st
import pandas as pd
import math
import time
from funcoes_auxiliares import conectar_mongo_portal_ispn


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
redes = db["redes_articulacoes"]


######################################################################################################
# FUNÇÕES
######################################################################################################


@st.dialog("Detalhes da rede", width="large")
def mostrar_detalhes(rede_doc):
    st.subheader(rede_doc.get("rede_articulacao", ""))
    tabs = st.tabs(["Informações gerais", "Observações"])

    # Aba 1: Informações gerais
    with tabs[0]:
        st.write("**Rede/Articulação**", rede_doc.get("rede_articulacao", ""))
        st.write("**Tema:**", rede_doc.get("tema", ""))
        st.write("**Ponto Focal:**", rede_doc.get("ponto_focal", ""))
        st.write("**Grau de Prioridade:**", rede_doc.get("prioridade", ""))
        st.write("**Dedicação:**", rede_doc.get("dedicacao", ""))
        st.write("**Observações:**", rede_doc.get("observacoes", ""))
        st.write("**Programa:**", rede_doc.get("programa", ""))

    # Aba 2: Observações
    with tabs[1]:
        obs_list = rede_doc.get("observacoes") or []  # lista ou []
        
        # se não tem observações, opções = apenas adicionar
        if not obs_list:
            opcoes = ["--Adicionar observação--"]
        else:
            # Se obs_list for None ou string, transforma em lista
            if isinstance(obs_list, str):
                obs_list = [obs_list]
            elif obs_list is None:
                obs_list = []

            opcoes = ["--Adicionar observação--"] + obs_list

        
        opcao_sel = st.selectbox("Selecione uma observação:", options=opcoes)

        if opcao_sel == "--Adicionar observação--":
            nova_obs = st.text_area("Nova observação")
            if st.button("Salvar observação"):
                redes.update_one(
                    {"_id": rede_doc["_id"]},
                    {"$push": {"observacoes": nova_obs}}
                )
                st.success("Observação salva com sucesso.")
                st.rerun()
        else:
            # aqui pega o índice pelo match no array real
            idx = opcoes.index(opcao_sel) - 1  # menos 1 por causa do "--Adicionar--"
            obs_atual = obs_list[idx]
            texto_editado = st.text_area("Observação:", value=obs_atual, height="content")
            if st.button("Salvar alterações"):
                obs_list[idx] = texto_editado
                redes.update_one(
                    {"_id": rede_doc["_id"]},
                    {"$set": {"observacoes": obs_list}}
                )
                st.success("Observação atualizada.")
                st.rerun()


def atualizar_topo_redes():
    st.session_state["pagina_atual_redes"] = st.session_state["pagina_topo_redes"]
    st.session_state["pagina_rodape_redes"] = st.session_state["pagina_topo_redes"]

def atualizar_rodape_redes():
    st.session_state["pagina_atual_redes"] = st.session_state["pagina_rodape_redes"]
    st.session_state["pagina_topo_redes"] = st.session_state["pagina_rodape_redes"]


######################################################################################################
# MAIN
######################################################################################################


st.header("Redes e Articulações")
st.write("")

# --- Carrega dados do MongoDB ---
dados_redes = list(redes.find())

df_redes = pd.DataFrame(dados_redes)
df_redes = df_redes.rename(columns={
    "rede_articulacao": "Rede/Articulação",
    "ponto_focal": "Ponto Focal",
    "prioridade": "Grau de Prioridade",
    "dedicacao": "Dedicação",
    "programa": "Programa"
})
df_redes = df_redes[["Rede/Articulação", "Ponto Focal", "Grau de Prioridade", "Dedicação", "Programa"]]


# --- Filtros ---
with st.expander("Filtros", expanded=True, icon=":material/filter_alt:"):
    colf1, colf2, colf3, colf4, colf5 = st.columns(5)
    rede_sel = colf1.selectbox("Rede", options=[""] + sorted(df_redes["Rede/Articulação"].dropna().unique().tolist()))
    prioridade_sel = colf2.selectbox("Grau de Prioridade", options=[""] + ["Estratégico", "Médio", "Baixo"])
    ponto_sel = colf3.selectbox("Ponto Focal", options=[""] + sorted(df_redes["Ponto Focal"].dropna().unique().tolist()))
    dedicacao_sel = colf4.selectbox("Dedicação", options=[""] + sorted(df_redes["Dedicação"].dropna().unique().tolist()))
    programa_sel = colf5.selectbox("Programa", options=[""] + sorted(df_redes["Programa"].dropna().unique().tolist()))

st.write("")

# --- Aplica filtros ---
df_filtrado = df_redes.copy()
if rede_sel != "":
    df_filtrado = df_filtrado[df_filtrado["Rede/Articulação"] == rede_sel]
if prioridade_sel != "":
    df_filtrado = df_filtrado[df_filtrado["Grau de Prioridade"] == prioridade_sel]
if ponto_sel != "":
    df_filtrado = df_filtrado[df_filtrado["Ponto Focal"] == ponto_sel]
if dedicacao_sel != "":
    df_filtrado = df_filtrado[df_filtrado["Dedicação"] == dedicacao_sel]
if programa_sel != "":
    df_filtrado = df_filtrado[df_filtrado["Programa"] == programa_sel]

# --- Ordenação customizada pelo Grau de Prioridade ---
ordem_prioridade = ["Estratégico", "Médio", "Baixo"]
df_filtrado["Grau de Prioridade"] = pd.Categorical(
    df_filtrado["Grau de Prioridade"],
    categories=ordem_prioridade,
    ordered=True
)

df_exibir = (
    df_filtrado
    .sort_values(by=["Grau de Prioridade", "Rede/Articulação"])
    .reset_index(drop=True)
)

# --- Paginação ---
itens_por_pagina = 20
total_linhas = len(df_exibir)
total_paginas = max(math.ceil(total_linhas / itens_por_pagina), 1)

if "pagina_atual_redes" not in st.session_state:
    st.session_state["pagina_atual_redes"] = 1
if "pagina_topo_redes" not in st.session_state:
    st.session_state["pagina_topo_redes"] = st.session_state["pagina_atual_redes"]
if "pagina_rodape_redes" not in st.session_state:
    st.session_state["pagina_rodape_redes"] = st.session_state["pagina_atual_redes"]

# --- Controle topo ---
col1, col2, col3 = st.columns([5, 2, 1])

col3.number_input(
    "Página",
    min_value=1,
    max_value=total_paginas,
    key="pagina_topo_redes",
    on_change=atualizar_topo_redes
)

inicio = (st.session_state["pagina_atual_redes"] - 1) * itens_por_pagina
fim = inicio + itens_por_pagina
df_paginado = df_exibir.iloc[inicio:fim]

col3.write(f"Mostrando **{inicio + 1}** a **{min(fim, total_linhas)}** de **{total_linhas}** redes")
st.write("")
st.divider()

# --- Layout da tabela customizada ---
colunas_visiveis = list(df_exibir.columns)
headers = colunas_visiveis + ["Detalhes"]

# Ajuste dos tamanhos de coluna (ponto focal mais estreito)
col_sizes = [3, 2, 2, 2, 1, 1]

# Cabeçalho
header_cols = st.columns(col_sizes)
for col, header in zip(header_cols, headers):
    col.markdown(f"**{header}**")

st.divider()

# Linhas
for i, row in df_paginado.iterrows():
    cols = st.columns(col_sizes)
    for j, key in enumerate(colunas_visiveis):
        cols[j].write(row[key])
    if cols[-1].button("Detalhes", key=f"detalhes_{i}", icon=":material/menu:"):
        # Busca documento original no Mongo
        rede_doc = redes.find_one({"rede_articulacao": row["Rede/Articulação"]})
        if rede_doc:
            mostrar_detalhes(rede_doc)
    st.divider()

# --- Controle rodapé ---
col1, col2, col3 = st.columns([5, 2, 1])

col3.number_input(
    "Página",
    min_value=1,
    max_value=total_paginas,
    value=st.session_state["pagina_rodape_redes"],
    step=1,
    key="pagina_rodape_redes",
    on_change=atualizar_rodape_redes
)

col3.write(f"Mostrando **{inicio + 1}** a **{min(fim, total_linhas)}** de **{total_linhas}** redes")
st.write("")