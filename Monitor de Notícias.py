import streamlit as st
import pandas as pd
import dateparser
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
        titulo_busca = doc["Título da busca"]
        for n in doc.get("noticias", []):
            noticias.append({
                "Título da busca": titulo_busca,
                "Título da notícia": n.get("Título da notícia"),
                "Data": n.get("Data"),
                "Fonte": n.get("Fonte"),
                "Link": n.get("Link")
            })

    df = pd.DataFrame(noticias)

    # Limpeza de texto para filtros
    def limpar_texto(texto):
        return texto.strip().lower() if texto else ""

    df["Título da busca limpa"] = df["Título da busca"].apply(limpar_texto)
    df["Fonte limpa"]         = df["Fonte"].apply(limpar_texto)

    df["Data_Convertida"] = df["Data"].apply(
        lambda x: dateparser.parse(x, settings={"DATE_ORDER": "DMY"})
    )

    # Ordena do mais recente ao mais antigo
    df = df.sort_values("Data_Convertida", ascending=False).reset_index(drop=True)

    # Cria coluna de exibição já em string no formato DD/MM/YYYY
    df["Data da notícia"] = df["Data_Convertida"].dt.strftime("%d/%m/%Y")

    # Opções de filtro
    titulos_opcoes = sorted(df["Título da busca limpa"].unique())
    fontes_opcoes  = sorted(df["Fonte limpa"].unique())

    # --------------------
    # Painel de filtros
    # --------------------
    with st.expander("Filtros", expanded=False, icon=":material/info:"):
        with st.form("filtros_form"):
            titulos_selecionados = st.multiselect(
                "Filtrar por título da busca",
                options=titulos_opcoes,
                format_func=lambda x: df[df["Título da busca limpa"] == x]["Título da busca"].iloc[0]
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
            (df["Título da busca limpa"].isin(titulos_selecionados)) &
            (df["Fonte limpa"].isin(fontes_selecionadas)) &
            (df["Data_Convertida"].dt.date >= intervalo_datas[0]) &
            (df["Data_Convertida"].dt.date <= intervalo_datas[1])
        ]
    else:
        df_filtrado = df

    # --------------------
    # Exibição da tabela
    # --------------------
    st.subheader(f"{len(df_filtrado)} notícia(s) encontrada(s)")

    # Seleciona apenas a coluna de string formatada + restantes
    tabela = df_filtrado[[
        "Título da busca",
        "Data da notícia",
        "Título da notícia",
        "Fonte",
        "Link"
    ]]

    ajustar_altura_dataframe(tabela, 1)
