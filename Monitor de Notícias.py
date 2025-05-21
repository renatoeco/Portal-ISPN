import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from dateutil import parser
from funcoes_auxiliares import conectar_mongo_portal_ispn
import locale

st.set_page_config(layout="wide")
st.title("📰 Visualizador de Notícias do Google Alertas")

###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
###########################################################################################################

db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]
monitor_noticias = db["monitor_noticias"]

documentos = list(monitor_noticias.find())


###########################################################################################################
# FUNÇÕES
###########################################################################################################


@st.dialog("Triagem", width="large")
def editar_status_noticias_dialog():
    # Campo de busca por título da notícia
    termo_busca = st.text_input("Buscar por título da notícia")

    titulos_busca = monitor_noticias.distinct("Palavra-chave")
    abas = st.tabs(titulos_busca)

    for i, titulo in enumerate(titulos_busca):
        with abas[i]:
            doc = monitor_noticias.find_one({"Palavra-chave": titulo})
            noticias = doc.get("noticias", []) if doc else []

            edicoes = []

            # Filtra apenas as notícias que ainda não têm status definido
            noticias = [n for n in noticias if not n.get("Status")]
            # Se houver busca, refina ainda mais
            if termo_busca:
                noticias = [n for n in noticias if termo_busca.lower() in n.get("Título da notícia", "").lower()]


            if not noticias:
                st.info("Nenhuma notícia encontrada com esse título.")
                continue

            for idx, noticia in enumerate(noticias):
                st.markdown(f"#### {noticia['Título da notícia']}")
                try:
                    data_formatada = pd.to_datetime(noticia['Data'], dayfirst=True, errors="coerce").strftime('%d/%m/%Y')
                except Exception:
                    data_formatada = noticia['Data']

                st.markdown(f"**{data_formatada}** | **{noticia['Fonte']}**")
                st.markdown(f"[Link para a notícia]({noticia['Link']})", unsafe_allow_html=True)

                novo_status = st.selectbox(
                    "Status:",
                    options=["Relevante", "Irrelevante"],
                    index = None,
                    key=f"{titulo}_status_{idx}", placeholder="Definir status"
                )

                edicoes.append((noticia["Link"], novo_status))
                st.markdown("---")

            if st.button(f"Salvar alterações para: {titulo}", key=f"salvar_{i}"):
                for link, novo_status in edicoes:
                    monitor_noticias.update_one(
                        {"Palavra-chave": titulo, "noticias.Link": link},
                        {"$set": {"noticias.$.Status": novo_status}}
                    )
                st.success("Status atualizado com sucesso!")
                st.rerun()


# Função para ajustar a altura do dataframe automaticamente no Streamlit
def ajustar_altura_dataframe(tabela, linhas_adicionais=0, use_container_width=True, hide_index=True, column_config={
        "Link": st.column_config.Column(
            # label="Link",
            width="medium"  # Ajusta a largura da coluna "Link", pode ser alterado para "100px" ou outros valores
        ),
        "Data da Última Ação Legislativa": st.column_config.Column(
            label="Última ação",  # Ajusta o nome da coluna para "Última ação"
            # width="medium"  # Ajusta a largura da coluna, pode ser configurado para "100px" ou outros valores
        )
    }):
    """
    Ajusta a altura da exibição de um DataFrame no Streamlit com base no número de linhas e outros parâmetros.
    
    Args:
        tabela (pd.DataFrame): O DataFrame a ser exibido.
        linhas_adicionais int): Número adicional de linhas para ajustar a altura. (padrão é 0)
        use_container_width (bool): Se True, usa a largura do container. (padrão é True)
        hide_index (bool): Se True, oculta o índice do DataFrame. (padrão é True)
        column_config (dict): Configurações adicionais das colunas, se necessário. (padrão é None)
    """
    
    # Define a altura em pixels de cada linha
    altura_por_linha = 35  
    # Calcula a altura total necessária para exibir o DataFrame, considerando as linhas adicionais e uma margem extra
    altura_total = ((tabela.shape[0] + linhas_adicionais) * altura_por_linha) + 2
    
    # Exibe o DataFrame no Streamlit com a altura ajustada
    st.dataframe(
        tabela,
        height=altura_total,  # Define a altura do DataFrame no Streamlit
        use_container_width=use_container_width,  # Define se deve usar a largura do container
        hide_index=hide_index,  # Define se o índice do DataFrame deve ser oculto
        column_config=column_config  # Configurações adicionais para as colunas, como largura personalizada
    )


###########################################################################################################
# MAIN
###########################################################################################################


try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except locale.Error:
    pass

if not documentos:
    st.info("Nenhuma notícia encontrada no banco de dados.")
else:
    # Monta lista de notícias
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

    # Limpeza de texto para filtros
    def limpar_texto(texto):
        return texto.strip().lower() if texto else ""

    df["Palavra-chave limpa"] = df["Palavra-chave"].apply(limpar_texto)
    df["Fonte limpa"] = df["Fonte"].apply(limpar_texto)

    df["Data_Convertida"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)

    # Ordena do mais recente ao mais antigo
    df = df.sort_values("Data_Convertida", ascending=False).reset_index(drop=True)

    # Cria coluna de exibição já em string no formato DD/MM/YYYY
    df["Data da notícia"] = df["Data_Convertida"].dt.strftime("%d/%m/%Y")

    # Opções de filtro
    titulos_opcoes = sorted(df["Palavra-chave limpa"].unique())
    fontes_opcoes  = sorted(df["Fonte limpa"].unique())

    # --------------------
    # Painel de filtros
    # --------------------
    with st.expander("Filtros", expanded=False, icon=":material/info:"):
        with st.form("filtros_form"):
            titulos_selecionados = st.multiselect(
                "Filtrar por palavra-chave",
                options=titulos_opcoes,
                format_func=lambda x: df[df["Palavra-chave limpa"] == x]["Palavra-chave"].iloc[0]
            )
            fontes_selecionadas = st.multiselect(
                "Filtrar por fonte",
                options=fontes_opcoes,
                format_func=lambda x: df[df["Fonte limpa"] == x]["Fonte"].iloc[0]
            )

            data_min = df["Data_Convertida"].min().date()
            data_max = df["Data_Convertida"].max().date()
            intervalo_datas = st.date_input(
                "Período",
                value=(data_min, data_max),
                format="DD/MM/YYYY"
            )

            aplicar = st.form_submit_button("Aplicar filtros")

    # --------------------
    # Aplica filtros
    # --------------------

    
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

    # --------------------
    # Exibição da tabela
    # --------------------

    tipos_usuario = st.session_state.get("tipo_usuario", [])
    if "adm" in tipos_usuario:
        col1, col2 = st.columns([4, 1])  # Ajuste os pesos conforme necessário
        with col2:
            # Botão para abrir editor de status
            st.button("Gerenciar notícias", icon=":material/settings:", on_click=editar_status_noticias_dialog)

    st.subheader(f"{len(df_filtrado)} notícia(s) encontrada(s)")

    # Remove as notícias irrelevantes da exibição inicial
    df_filtrado = df_filtrado[df_filtrado["Status"] == "Relevante"]

    tabela = df_filtrado[[  # Apenas as colunas visíveis
        "Palavra-chave",
        "Data da notícia",
        "Título da notícia",
        "Fonte",
        "Link"
    ]].copy()

    

    ajustar_altura_dataframe(tabela)





