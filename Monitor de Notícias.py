import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
import seaborn as sns
import matplotlib.dates as mdates
import time
from funcoes_auxiliares import conectar_mongo_portal_ispn
import locale


st.set_page_config(layout="wide")
st.header("Visualizador de Notícias do Google Alertas")


# ----------------------------------------------------------------------------------------------------
# CONEXÃO COM O BANCO DE DADOS MONGODB
# ----------------------------------------------------------------------------------------------------


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas
monitor_noticias = db["monitor_noticias"]  # Coleção de notícias monitoradas

# Obtém todos os documentos da coleção
documentos = list(monitor_noticias.find())


# ----------------------------------------------------------------------------------------------------
# FUNÇÕES
# ----------------------------------------------------------------------------------------------------


# Diálogo de triagem para revisão e alteração de status das notícias
@st.dialog("Triagem", width="large")
def editar_status_noticias_dialog():
    titulos_busca = monitor_noticias.distinct("Palavra-chave")
    abas = st.tabs(titulos_busca)

    for i, titulo in enumerate(titulos_busca):
        with abas[i]:
            mostrar_irrelevantes = st.checkbox("Mostrar notícias irrelevantes", key=f"mostrar_irrelevantes_{i}")
            renderizar_noticias_fragment(titulo, mostrar_irrelevantes=mostrar_irrelevantes)


# Fragmento reutilizável que renderiza as notícias e os botões de triagem
@st.fragment
def renderizar_noticias_fragment(titulo, mostrar_irrelevantes=False):
    doc = monitor_noticias.find_one({"Palavra-chave": titulo})
    noticias = doc.get("noticias", []) if doc else []

    # Filtra as notícias com base no status
    if mostrar_irrelevantes:
        noticias_exibidas = [n for n in noticias if n.get("Status") == "Irrelevante"]
    else:
        noticias_exibidas = [n for n in noticias if not n.get("Status")]

    if not noticias_exibidas:
        st.info("Nenhuma notícia para exibir.")
        return

    # Loop para exibir cada notícia
    for idx, noticia in enumerate(noticias_exibidas):
        st.markdown(f"#### {noticia['Título da notícia']}")
        data = pd.to_datetime(noticia.get("Data"), errors='coerce')
        data_fmt = data.strftime('%d/%m/%Y') if not pd.isna(data) else "Data inválida"
        st.markdown(f"**{data_fmt}** | **{noticia['Fonte']}**")
        st.markdown(f"[Abrir notícia]({noticia['Link']})", unsafe_allow_html=True)

        if mostrar_irrelevantes:
            st.markdown(f"**Status:** {noticia.get('Status', 'Sem status')}")

        # Centraliza os botões na interface
        left_col, center_col, right_col = st.columns([1, 2, 1])
        with center_col:
            btn_cols = st.columns(2)
            if mostrar_irrelevantes:
                # Mostra apenas o botão "Relevante"
                if st.button("Relevante", key=f"relevante_{titulo}_{idx}", icon=":material/check:", use_container_width=True):
                    monitor_noticias.update_one(
                        {"Palavra-chave": titulo, "noticias.Link": noticia["Link"]},
                        {"$set": {"noticias.$.Status": "Relevante"}}
                    )
                    st.success("Status atualizado para **Relevante** com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")
            else:
                # Mostra os dois botões: Relevante e Irrelevante
                if btn_cols[0].button("Relevante", key=f"relevante_{titulo}_{idx}", icon=":material/check:"):
                    monitor_noticias.update_one(
                        {"Palavra-chave": titulo, "noticias.Link": noticia["Link"]},
                        {"$set": {"noticias.$.Status": "Relevante"}}
                    )
                    st.success("Status atualizado para **Relevante** com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")

                if btn_cols[1].button("Irrelevante", key=f"irrelevante_{titulo}_{idx}", icon=":material/close:"):
                    monitor_noticias.update_one(
                        {"Palavra-chave": titulo, "noticias.Link": noticia["Link"]},
                        {"$set": {"noticias.$.Status": "Irrelevante"}}
                    )
                    st.success("Status atualizado para **Irrelevante** com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")

        st.divider()  # Linha divisória para separar notícias


# ----------------------------------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------------------------------


# Define o locale para formatação de datas
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except locale.Error:
    pass

# Verifica se há dados no banco
if not documentos:
    st.info("Nenhuma notícia encontrada no banco de dados.")
else:
    # Compila todas as notícias em um único DataFrame
    noticias = []
    for doc in documentos:
        titulo_busca = doc["Palavra-chave"]
        for n in doc.get("noticias", []):
            noticias.append({
                "Palavra-chave": titulo_busca,
                "Título da notícia": n.get("Título da notícia"),
                "Data": n.get("Data"),
                "Fonte": n.get("Fonte"),
                "Link": n.get("Link"),
                "Status": n.get("Status")
            })

    df = pd.DataFrame(noticias)

    # Prepara colunas auxiliares para filtros
    def limpar_texto(texto):
        return texto.strip().lower() if texto else ""

    df["Palavra-chave limpa"] = df["Palavra-chave"].apply(limpar_texto)
    df["Fonte limpa"] = df["Fonte"].apply(limpar_texto)
    df["Data_Convertida"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
    df = df.sort_values("Data_Convertida", ascending=False).reset_index(drop=True)
    df["Data da notícia"] = df["Data_Convertida"].dt.strftime("%d/%m/%Y")

    # Prepara opções de filtro
    titulos_opcoes = sorted(df["Palavra-chave limpa"].unique())
    fontes_opcoes  = sorted(df["Fonte limpa"].unique())

    # Exibe painel de filtros
    with st.expander("Filtros", expanded=False, icon=":material/info:"):
        with st.form("filtros_form"):

            titulos_selecionados = st.multiselect(
                "Filtrar por palavra-chave",
                options=titulos_opcoes,
                format_func=lambda x: df[df["Palavra-chave limpa"] == x]["Palavra-chave"].iloc[0],
                placeholder="Escolha uma palavra-chave"
            )

            # Filtra as opções de fontes com base nas palavras-chave selecionadas
            if titulos_selecionados:
                df_filtrado_por_titulo = df[df["Palavra-chave limpa"].isin(titulos_selecionados)]
                fontes_opcoes_filtradas = sorted(df_filtrado_por_titulo["Fonte limpa"].unique())
            else:
                fontes_opcoes_filtradas = fontes_opcoes  # Mostra todas se nenhuma palavra-chave foi selecionada

            fontes_selecionadas = st.multiselect(
                "Filtrar por fonte",
                options=fontes_opcoes_filtradas,
                format_func=lambda x: df[df["Fonte limpa"] == x]["Fonte"].iloc[0],
                placeholder="Escolha uma fonte"
            )

            data_min = df["Data_Convertida"].min().date()
            data_max = df["Data_Convertida"].max().date()
            intervalo_datas = st.date_input("Período", value=(data_min, data_max), format="DD/MM/YYYY")

            aplicar = st.form_submit_button("Aplicar filtros")


    # Aplica os filtros selecionados
    if aplicar:
        if not titulos_selecionados:
            titulos_selecionados = titulos_opcoes
        if not fontes_selecionadas:
            fontes_selecionadas = fontes_opcoes

        df_filtrado = df[
            (df["Palavra-chave limpa"].isin(titulos_selecionados)) &
            (df["Fonte limpa"].isin(fontes_selecionadas)) &
            (df["Data_Convertida"].dt.date >= intervalo_datas[0]) &
            (df["Data_Convertida"].dt.date <= intervalo_datas[1])
        ]
    else:
        df_filtrado = df

    # Se usuário for admin, exibe botão para triagem
    tipos_usuario = st.session_state.get("tipo_usuario", [])
    if "adm" in tipos_usuario:
        noticias_sem_status = df[df["Status"].isna() | (df["Status"].str.strip() == "")]
        qtd_sem_status = len(noticias_sem_status)

        col1, col2 = st.columns([4, 1])
        with col1:
            if qtd_sem_status > 0:
                st.warning(f"{qtd_sem_status} notícia(s) ainda precisam ser triadas.")
        with col2:
            st.button("Triagem de notícias", icon=":material/settings:", on_click=editar_status_noticias_dialog)

    # Filtra apenas notícias marcadas como Relevantes para exibição
    df_filtrado = df_filtrado[df_filtrado["Status"] == "Relevante"]

    st.subheader(f"{len(df_filtrado)} notícia(s) encontrada(s)")

    tabela = df_filtrado[["Palavra-chave", "Data da notícia", "Título da notícia", "Fonte", "Link"]].copy()

    # Configura grid interativo
    linhas_por_pagina = 20
    gb = GridOptionsBuilder.from_dataframe(tabela)
    gb.configure_default_column(editable=True, groupable=True)
    gb.configure_column("Link", cellStyle={"whiteSpace": "nowrap", "overflow": "visible", "textOverflow": "clip"}, autoHeight=False)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=linhas_por_pagina)

    altura_dinamica = linhas_por_pagina * 30 + 40
    grid_options = gb.build()

    AgGrid(
        tabela,
        gridOptions=grid_options,
        height=altura_dinamica,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True
    )





