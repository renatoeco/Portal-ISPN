import streamlit as st
import pandas as pd 
import streamlit_shadcn_ui as ui
import plotly.express as px

st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png")


st.header("Pessoas")
st.write('')

tab1, tab2 = st.tabs(["Pessoas", "Férias"])

# with st.expander("Filtros"):
with tab1:
    col1, col2, col3, col4 = st.columns(4)

    col1.selectbox("Programa", ["Todos", "Cerrado", "Iniciativas Comunitárias", "Maranhão", "Sociobiodiversidade", "Povos Indígenas"])
    col2.selectbox("Setor", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3", "Projeto 4", "Projeto 5"])


    col3.selectbox("Doador", ["Todos", "USAID", "GEF", "UE", "Laudes Foundation"])
    col4.selectbox("Projeto", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3", "Projeto 4", "Projeto 5"])

    pessoas = pd.DataFrame(
        {
            "Nome": ["Ana", "Pedro", "João", "Maria", "Paulo", "Lívia", "Matheus", "Vitória", "Terena"],
            "Programa": ["Cerrado", "Administrativo", "Administrativo", "Iniciativas Comunitárias", "Povos Indígenas", "Administrativo", "Maranhão", "Sociobiodiversidade", "Administrativo"],
            "Projeto": ["Projeto 1", "Projeto 2", "Projeto 2", "Projeto 4", "Projeto 5", "Projeto 2", "Projeto 7", "Projeto 8", "Projeto 9"],
            "Setor": ["Administração", "Comunicação", "Gestão de Projetos", "Gestão de Projetos", "Gestão de Projetos", "Administração", "Comunicação", "Gestão de Projetos", "Gestão de Projetos"],
            "Cargo": ["Assistente Administrativo", "Assistente de Comunicação", "Coordenador de Projetos", "Coordenadora de Projetos", "Coordenador de Projetos", "Assistente Administrativo", "Assistente de Comunicação", "Coordenador de Projetos", "Coordenadora de Projetos"],
            "Escolaridade": ["Segundo grau", "Pós graduação", "Mestrado", "Doutorado", "Especialização", "Graduação", "Segundo grau", "Pós graduação", "Mestrado"],
            "E-mail": ["ana@ispn.org.br", "pedro@ispn.org.br", "joao@ispn.org.br", "maria@ispn.org.br", "paulo@ispn.org.br", "livia@ispn.org.br", "matheus@ispn.org.br", "vitoria@ispn.org.br", "terena@ispn.org.br"],
            "Telefone": ["(61) 99999-9999", "(61) 99999-9999", "(61) 99999-9999", "(61) 99999-9999", "(61) 99999-9999", "(61) 99999-9999", "(61) 99999-9999", "(61) 99999-9999", "(61) 99999-9999"],
            "Gênero": ["Feminino", "Masculino", "Masculino", "Feminino", "Masculino", "Feminino", "Masculino", "Feminino", "Masculino"],
            "Raça": ["Branca", "Preta", "Parda", "Amarela", "Indígena", "Branca", "Preta", "Parda", "Amarela"]
        }
    )

    st.subheader(f'{len(pessoas)} colaboradores(as)')
    st.write('')

    st.dataframe(pessoas, hide_index=True)

    col1, col2 = st.columns(2)

    # Programa
    fig = px.bar(pessoas, x='Programa', color='Programa', title='Distribuição de Pessoas por Programa')
    col1.plotly_chart(fig)

    # Projeto
    fig = px.bar(pessoas, x='Projeto', color='Programa', title='Distribuição de Pessoas por Projeto')
    col2.plotly_chart(fig)


    # Setor
    fig = px.pie(pessoas, names='Setor', title='Distribuição de Pessoas por Setor')
    col1.plotly_chart(fig)


    # col1, col2, col3 = st.columns(3)


    # Cargo
    fig = px.pie(pessoas, names='Cargo', title='Distribuição de Pessoas por Cargo')
    col2.plotly_chart(fig)


    # Genero
    fig = px.pie(pessoas, names='Gênero', title='Distribuição de Pessoas por Gênero')
    col1.plotly_chart(fig)


    # Raça
    fig = px.pie(pessoas, names='Raça', title='Distribuição de Pessoas por Raça')
    col2.plotly_chart(fig)

    # Escolaridade
    fig = px.pie(pessoas, names='Escolaridade', title='Distribuição de Pessoas por Escolaridade')
    col1.plotly_chart(fig)


with tab2:
    st.write('Painel de férias')
    st.markdown("[Gaivota Streamlit App](https://gaivota.streamlit.app)")

