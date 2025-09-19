import streamlit as st
import pandas as pd
from datetime import datetime
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
    tabs = st.tabs([":material/info: Informações gerais", ":material/notes: Anotações"])

    # Aba 1: Informações gerais
    with tabs[0]:
        st.write("**Rede/Articulação**", rede_doc.get("rede_articulacao", ""))
        st.write("**Tema:**", rede_doc.get("tema", ""))
        st.write("**Ponto Focal:**", rede_doc.get("ponto_focal", ""))
        st.write("**Grau de Prioridade:**", rede_doc.get("prioridade", ""))
        st.write("**Dedicação:**", rede_doc.get("dedicacao", ""))
        st.write("**Programa:**", rede_doc.get("programa", ""))

    # Aba 2: Anotações
    with tabs[1]:
        usuario_logado = st.session_state.get("nome", "Desconhecido")
        anotacoes = rede_doc.get("anotacoes") or []

        # ---------------- EXPANDER PARA ADICIONAR ANOTAÇÃO ----------------
        with st.expander("Adicionar nova anotação", expanded=False, icon=":material/add_notes:"):
            nova_data = datetime.now().date()
            novo_texto = st.text_area("Texto da anotação", key="nova_anotacao", height="content")

            if st.button("Adicionar anotação", key="btn_add_anotacao", icon=":material/add_notes:"):
                if novo_texto.strip():
                    nova_entry = {
                        "data_anotacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "autor_anotacao": usuario_logado,
                        "anotacao": novo_texto.strip()
                    }
                    redes.update_one(
                        {"_id": rede_doc["_id"]},
                        {"$push": {"anotacoes": nova_entry}}
                    )
                    st.success("Anotação salva com sucesso.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning("O campo da anotação não pode estar vazio.")

        st.write("")
        st.write("**Anotações existentes:**")

        # ---------------- LISTA DE ANOTAÇÕES ----------------
        # Ordena por data (decrescente)
        anotacoes_ordenadas = []
        for idx, a in enumerate(anotacoes):
            data_str = a.get("data_anotacao", "")
            data_dt = datetime.min
            if data_str:
                try:
                    data_dt = datetime.strptime(data_str.split()[0], "%d/%m/%Y")
                except:
                    pass
            anotacoes_ordenadas.append((idx, data_dt, a))

        anotacoes_ordenadas.sort(key=lambda x: x[1], reverse=True)

        # ---------------- RENDERIZA CADA ANOTAÇÃO ----------------
        for original_idx, _, anotacao in anotacoes_ordenadas:
            container_key = f"anotacao_{rede_doc['_id']}_{original_idx}"
            toggle_key = f"toggle_edicao_{container_key}"
            delete_key = f"delete_confirm_{container_key}"

            with st.container(border=True):
                modo_edicao = st.toggle("Editar", key=toggle_key, value=False)

                if modo_edicao:
                    # Data (apenas exibe já formatada)
                    data_valor = anotacao.get("data_anotacao", "")
                    data_formatada = data_valor.split()[0] if data_valor else datetime.now().strftime("%d/%m/%Y")

                    st.write(f"**Data:** {data_formatada}")
                    st.write(f"**Autor:** {anotacao.get('autor_anotacao', '')}")

                    novo_texto = st.text_area(
                        "Texto da anotação",
                        value=anotacao.get("anotacao", ""),
                        key=f"texto_{container_key}", height="content"
                    )

                    botoes = st.container(horizontal=True)

                    if botoes.button("Salvar alterações", key=f"salvar_{container_key}", icon=":material/save:"):
                        anotacoes[original_idx]["anotacao"] = novo_texto.strip()
                        redes.update_one(
                            {"_id": rede_doc["_id"]},
                            {"$set": {"anotacoes": anotacoes}}
                        )
                        st.success("Anotação atualizada.")
                        time.sleep(2)
                        st.rerun()

                    if botoes.button("Deletar anotação", key=f"deletar_{container_key}", icon=":material/delete:"):
                        st.session_state[delete_key] = True

                    if st.session_state.get(delete_key, False):
                        st.warning("Tem certeza que deseja apagar esta anotação?")
                        colA, colB = st.columns(2)
                        if colA.button("Sim", key=f"confirmar_delete_{container_key}"):
                            anotacoes.pop(original_idx)
                            redes.update_one(
                                {"_id": rede_doc["_id"]},
                                {"$set": {"anotacoes": anotacoes}}
                            )
                            st.success("Anotação apagada com sucesso.")
                            st.session_state[delete_key] = False
                            time.sleep(2)
                            st.rerun()
                        if colB.button("Não", key=f"cancelar_delete_{container_key}"):
                            st.session_state[delete_key] = False

                else:
                    # Modo visualização
                    data_str = anotacao.get("data_anotacao", "")
                    if data_str:
                        data_str = data_str.split()[0]
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.write(f"**Data:** {data_str}")
                    with col2:
                        st.write(f"**Autor:** {anotacao.get('autor_anotacao', '')}")
                    st.write(anotacao.get("anotacao", ""))


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
st.write("")
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


# --- Preparar listas únicas para filtros ---
# Garante que cada ponto focal aparece separado e único
pontos_unicos = (
    df_redes["Ponto Focal"]
    .dropna()
    .astype(str)
    .str.split(",")               # separa caso seja string "A, B"
    .explode()                    # transforma em linhas
    .str.strip()                  # tira espaços extras
    .unique()
    .tolist()
)

programas_unicos = (df_redes["Programa"].dropna().astype(str).str.split(",").explode().str.strip().unique().tolist()
)

# --- Filtros ---
with st.expander("Filtros", expanded=True, icon=":material/filter_alt:"):
    colf1, colf2, colf3, colf4, colf5 = st.columns(5)
    
    rede_sel = colf1.multiselect(
        "Rede",
        options=sorted(df_redes["Rede/Articulação"].dropna().unique().tolist()), placeholder=""
    )
    ponto_sel = colf2.multiselect(
        "Ponto Focal",
        options=sorted(pontos_unicos), placeholder=""
    )
    prioridade_sel = colf3.multiselect(
        "Grau de Prioridade",
        options=["Estratégico", "Médio", "Baixo"], placeholder=""
    )
    dedicacao_sel = colf4.multiselect(
        "Dedicação",
        options=sorted(df_redes["Dedicação"].dropna().unique().tolist()), placeholder=""
    )
    programa_sel = colf5.multiselect(
        "Programa",
        options=sorted(programas_unicos), placeholder=""
    )


st.write("")
st.write("")
st.write("")

# --- Aplica filtros ---
df_filtrado = df_redes.copy()

# Filtro direto
if rede_sel:
    df_filtrado = df_filtrado[df_filtrado["Rede/Articulação"].isin(rede_sel)]

if prioridade_sel:
    df_filtrado = df_filtrado[df_filtrado["Grau de Prioridade"].isin(prioridade_sel)]

if dedicacao_sel:
    df_filtrado = df_filtrado[df_filtrado["Dedicação"].isin(dedicacao_sel)]

# Filtro Ponto Focal (explode na lógica)
if ponto_sel:
    df_filtrado = df_filtrado[
        df_filtrado["Ponto Focal"]
        .astype(str)
        .apply(lambda x: any(p in x for p in ponto_sel))
    ]

# Filtro Programa (explode na lógica)
if programa_sel:
    df_filtrado = df_filtrado[
        df_filtrado["Programa"]
        .astype(str)
        .apply(lambda x: any(p in x for p in programa_sel))
    ]

# --- Ordenação customizada pelo Grau de Prioridade ---
ordem_prioridade = ["Estratégico", "Médio", "Baixo"]
df_filtrado["Grau de Prioridade"] = pd.Categorical(
    df_filtrado["Grau de Prioridade"],
    categories=ordem_prioridade,
    ordered=True
)

df_exibir = (
    df_filtrado
    .sort_values(by=["Rede/Articulação"])
    .reset_index(drop=True)
)


# # --- Paginação ---
# itens_por_pagina = 20
# total_linhas = len(df_exibir)
# total_paginas = max(math.ceil(total_linhas / itens_por_pagina), 1)

# if "pagina_atual_redes" not in st.session_state:
#     st.session_state["pagina_atual_redes"] = 1
# if "pagina_topo_redes" not in st.session_state:
#     st.session_state["pagina_topo_redes"] = st.session_state["pagina_atual_redes"]
# if "pagina_rodape_redes" not in st.session_state:
#     st.session_state["pagina_rodape_redes"] = st.session_state["pagina_atual_redes"]

# --- Controle topo ---
#col1, col2, col3 = st.columns([5, 2, 1])

# col3.number_input(
#     "Página",
#     min_value=1,
#     max_value=total_paginas,
#     key="pagina_topo_redes",
#     on_change=atualizar_topo_redes
# )

# inicio = (st.session_state["pagina_atual_redes"] - 1) * itens_por_pagina
# fim = inicio + itens_por_pagina
# df_paginado = df_exibir.iloc[inicio:fim]

# col3.write(f"Mostrando **{inicio + 1}** a **{min(fim, total_linhas)}** de **{total_linhas}** redes")
# st.write("")
# st.divider()

# --- Layout da tabela customizada ---
colunas_visiveis = list(df_exibir.columns)
headers = colunas_visiveis + ["Detalhes"]

# Ajuste dos tamanhos de coluna (ponto focal mais estreito)
col_sizes = [3, 3, 2, 1, 1, 2]

# Cabeçalho
header_cols = st.columns(col_sizes)
for col, header in zip(header_cols, headers):
    col.markdown(f"**{header}**")

st.divider()

# Linhas
for i, row in df_exibir.iterrows():
    cols = st.columns(col_sizes)
    for j, key in enumerate(colunas_visiveis):
        cols[j].write(row[key])
    if cols[-1].button("Detalhes", key=f"detalhes_{i}", icon=":material/menu:"):
        # Busca documento original no Mongo
        rede_doc = redes.find_one({"rede_articulacao": row["Rede/Articulação"]})
        if rede_doc:
            mostrar_detalhes(rede_doc)
    st.divider()

# # --- Controle rodapé ---
# col1, col2, col3 = st.columns([5, 2, 1])

# col3.number_input(
#     "Página",
#     min_value=1,
#     max_value=total_paginas,
#     value=st.session_state["pagina_rodape_redes"],
#     step=1,
#     key="pagina_rodape_redes",
#     on_change=atualizar_rodape_redes
# )

# col3.write(f"Mostrando **{inicio + 1}** a **{min(fim, total_linhas)}** de **{total_linhas}** redes")
# st.write("")












# # TESTE DE CAIXA DE ANOTAÇÕES COM LIMITE DE CARACTERES

# MAX_CARACTERES = 2000

# texto = st.text_area("Digite seu texto (máx. 2000 caracteres):", height=400)
# num_caracteres = len(texto)
# caracteres_restantes = MAX_CARACTERES - num_caracteres

# if caracteres_restantes < 0:
#     st.markdown(f"<span style='color:red'>{num_caracteres} / {MAX_CARACTERES} - Você ultrapassou o limite em {-caracteres_restantes} caracteres!</span>", unsafe_allow_html=True)
# else:
#     st.write(f"{num_caracteres} / {MAX_CARACTERES}")
# st.write(f"*Clique fora da caixa de texto para atualizar o contador")