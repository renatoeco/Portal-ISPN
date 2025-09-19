import streamlit as st
from pymongo import MongoClient

@st.cache_resource
def conectar_mongo_portal_ispn():
    cliente = MongoClient(
    st.secrets["senhas"]["senha_mongo_portal_ispn"])
    db_portal_ispn = cliente["ISPN_Hub"]                   
    return db_portal_ispn


@st.cache_resource
def conectar_mongo_pls():
    cliente_2 = MongoClient(
    st.secrets["senhas"]["senha_mongo_pls"])
    db_pls = cliente_2["db_pls"]
    return db_pls



def ajustar_altura_dataframe(
    df_nao_atualizado,
    linhas_adicionais=0,
    altura_maxima=None,  # Se None, não aplica limite
    use_container_width=True,
    hide_index=True,
    column_config={
        "Link": st.column_config.Column(
            width="medium"  
        ),
        "Data da Última Ação Legislativa": st.column_config.Column(
            label="Última ação",  
        )
    }
):
    """
    Ajusta a altura da exibição de um DataFrame no Streamlit com base no número de linhas.
    Se 'altura_maxima' for informado, limita a altura até esse valor.
    """

    # Define a altura em pixels de cada linha
    altura_por_linha = 35  

    # Calcula a altura total necessária
    altura_total = ((df_nao_atualizado.shape[0] + linhas_adicionais) * altura_por_linha) + 2

    # Se altura_maxima foi informada, aplica o limite
    if altura_maxima is not None:
        altura_total = min(altura_total, altura_maxima)

    # Exibe o DataFrame no Streamlit
    st.dataframe(
        df_nao_atualizado,
        height=altura_total,
        use_container_width=use_container_width,
        hide_index=hide_index,
        column_config=column_config
    )



