import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
import plotly.express as px



st.set_page_config(layout="wide")
st.logo("/home/renato/Projetos_Python/ISPN_HUB/app_ispn_hub/images/logo_ISPN_horizontal_ass.png")

st.header("Projetos Institucionais")

st.write('')


tab1, tab2, tab3 = st.tabs(["Visão geral", "Projeto", "Atividades"])


with tab1:

    st.write('')

    col1, col2, col3 = st.columns(3)

    doador_selecionado = col1.selectbox("Doador", ["Todos os doadores", "KFW", "GIZ", "UE", "USAID", "Fundo Socioambiental Casa", "Instituto Humanitas360", "Brazil Fund", "Citi Foundation", "Cargill", "Mitsubishi Corporation"])

    programa_selecionado = col2.selectbox("Programa", ["Todos os programas", "Cerrado", "Maranhão", "Povos Indígenas", "Sociobiodiversidade", "Iniciativas Comunitárias", "Administrativo"])

    situacao = col3.selectbox("Situação", ["Todos os projetos", "Em andamento", "Concluídos", "Cancelados"])

    col1.selectbox("Projetos vigentes entre", ["2023", "2024", "2025"], key="doador1")
    col2.selectbox("até", ["2023", "2024", "2025"], key="doador2")



    st.write('')
    st.subheader('3 projetos')
    st.write('')


    st.write('**Cronograma**')

    df_projeto = pd.DataFrame({
        "Projeto": ["CEPF", "PACT", "Educação Verde", "Fortalecimento Comunitário"],
        "Valor": [50000.00, 120000.00, 80000.00, 150000.00],
        "Início": ["março/2024", "abril/2024", "janeiro/2025", "fevereiro/2025"],
        "Fim": ["fevereiro/2025", "dezembro/2024", "dezembro/2025", "junho/2025"],
        "Situação": ["Em andamento", "Em andamento", "Em andamento", "Concluído"]
    })

    # Mapeamento de meses em português para número
    meses = {
        "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
        "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
        "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
    }

    # Função para converter "mês/ano" para datetime
    def converter_data(data_str):
        mes, ano = data_str.split('/')
        mes_num = meses[mes.lower()]
        return pd.to_datetime(f"{ano}-{mes_num}-01")

    # Aplicando a conversão
    df_projeto['Início'] = df_projeto['Início'].apply(converter_data)
    df_projeto['Fim'] = df_projeto['Fim'].apply(converter_data)

    # Criando gráfico de Gantt com Plotly Express
    fig = px.timeline(
        df_projeto,
        x_start='Início',
        x_end='Fim',
        y='Projeto',
        color='Situação',
        hover_data=['Valor'],
        height=250  # Diminuindo a altura do gráfico
    )

    fig.update_yaxes(categoryorder='total ascending')

    # Movendo a legenda para baixo
    fig.update_layout(
        legend=dict(
            orientation="h",       # horizontal
            yanchor="bottom",
            y=-1,                # valor negativo posiciona abaixo do gráfico
            xanchor="center",
            x=0
        ),
        yaxis_title=None
    )

    st.plotly_chart(fig)


    st.write('')
    st.write('**Projetos**')



    dados_projetos = {
        "Nome do projeto": [
            "Projeto Água Viva",
            "Educação Verde",
            "Fortalecimento Comunitário"
        ],
        "Programa": [
            "Cerrado",
            "Maranhão",
            "Povos Indígenas"
        ],
        "Doador": [
            "Fundação X",
            "Instituto Y",
            "ONG Z"
        ],
        "Valor": [
            50000.00,
            120000.00,
            80000.00
        ],
        "início": [
            "março/2024",
            "abril/2024",
            "janeiro/2025"
        ],
        "Fim": [
            "fevereiro/2025",
            "dezembro/2024",
            "dezembro/2025"
        ],
        "Situação": [
            "Em andamento",
            "Em andamento",
            "Concluído"
        ]
    }

    # Criando o DataFrame
    df_projetos = pd.DataFrame(dados_projetos)
    df_projetos.index += 1

    # Exibindo o DataFrame
    # st.write('')
    st.dataframe(df_projetos)


with tab2:
    st.write('')

    col1, col2, col3 = st.columns(3)
    
    projeto_selecionado = col1.selectbox('Selecione o projeto', ['Ceres', 'USAID II', 'Vale Quebradeiras'])

    st.subheader(projeto_selecionado)

    col1, col2, col3 = st.columns(3)


    col3.button('Gerenciar projeto', use_container_width=True)

    col1, col2 = st.columns(2)

    col1.metric("**Valor:**", "R$ 5.000.000,00")
    col2.metric("**Contrapartida:**", "R$ 5.000.000,00")


    st.write('**Situação:** Em andamento')

    st.write('**Nome do projeto:** Fortalecimento das comunidades do Norte de Minas Gerais')

    st.write('**Objetivo geral:** Fortalecer as comunidades por meio de uma sério de treinamentos relacionados a gestão das áreas protegidas por comunidades.')

    st.write('**Objetivos específicos:**')

    st.markdown('- Objetivo específico 1 \n - Objetivo específico 2 \n - Objetivo específico 3')

    st.write('**Data de início:** 15/03/2023')
    st.write('**Data de término:** 15/08/2026')

    st.write('**Equipe contratada pelo projeto:**')
    
    dados_equipe = {
        "Nome": ["Ana", "Pedro", "João"],
        "Início do contrato": ["15/03/2023", "15/05/2023", "15/07/2023"],
        "Fim do contrato": ["15/08/2026", "15/08/2024", "15/08/2025"]
    }
    df_equipe = pd.DataFrame(dados_equipe)
    df_equipe.sort_values(by='Fim do contrato', ascending=True, inplace=True)
    df_equipe.index += 1
    st.dataframe(df_equipe)
    # ui.table(data=df_equipe)

    st.write('')

    st.write('**Anotações:**')

    # Dados em formato de lista
    dados = [
        ["15/03/2023", "Início do projeto", "Ana"],
        ["15/05/2023", "Primeiro pagamento realizado", "João"],
        ["15/07/2023", "Entrega de relatório", "Pedro"]
    ]

    # Transformar em DataFrame
    df = pd.DataFrame(dados, columns=["Data", "Anotação", "Autor"])

    # Mostrar com ui.table
    ui.table(data=df)

with tab3:

    col1, col2, col3, col4 = st.columns(4)

    programa_selecionado = col1.selectbox("Programa", ["Todos os programas", "Cerrado", "Maranhão", "Povos Indígenas", "Sociobiodiversidade", "Iniciativas Comunitárias", "Administrativo"], key="programa")
    projeto_selecionado = col2.selectbox('Projeto', ['Ceres', 'USAID II', 'Vale Quebradeiras'], key="projeto")

    col3.selectbox("Projetos vigentes entre", ["2023", "2024", "2025"], key="iicio")
    col4.selectbox("até", ["2023", "2024", "2025"], key="fim")
    # col3.write('')
    # col3.write('')

    st.checkbox("Só atividades não concluídas", key="atividades")

    st.write('')
    col1, col2, col3 = st.columns(3)

    
    col3.button("Reportar atividade", use_container_width=True)


    atividades = {
        "Atividade": ["Oficina de Advocacy", "Formação de Comunicadores", "Elaboração de Relatório", "Entrega de Relatório"],
        "Programa": ["Cerrado", "Maranhão", "Povos Indígenas", "Sociobiodiversidade"],
        "Projeto": ["Ceres", "USAID II", "Vale Quebradeiras", "Ceres"],
        "Início": ["15/03/2023", "15/05/2023", "15/07/2023", "15/08/2023"],
        "Fim": ["15/06/2023", "15/08/2023", "15/10/2023", "15/11/2023"],
        "Responsável": ["Ana", "Pedro", "João", "Ana"],
        "Situação": ["Em andamento", "Em andamento", "Concluído", "Em andamento"]
    }
    df_atividades = pd.DataFrame(atividades)

    lista, cronograma = st.tabs(["Lista de atividades", "Cronograma"])

    with lista:
        st.dataframe(df_atividades, hide_index=True)

    with cronograma:

        df_projeto = pd.DataFrame({
            "Atividade": ["Oficina de Advocacy", "Formação de Comunicadores", "Elaboração de Relatório", "Entrega de Relatório"],
            "Programa": ["Cerrado", "Maranhão", "Povos Indígenas", "Sociobiodiversidade"],
            "Projeto": ["Ceres", "USAID II", "Vale Quebradeiras", "Ceres"],
            "Início": ["março/2023", "maio/2023", "julho/2023", "agosto/2023"],
            "Fim": ["junho/2023", "agosto/2023", "outubro/2023", "novembro/2023"],
            "Responsável": ["Ana", "Pedro", "João", "Ana"],
            "Situação": ["Em andamento", "Em andamento", "Concluído", "Em andamento"]
        })
        # Mapeamento de meses em português para número
        meses = {
            "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
            "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
            "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
        }

        # Função para converter "mês/ano" para datetime
        def converter_data(data_str):
            mes, ano = data_str.split('/')
            mes_num = meses[mes.lower()]
            return pd.to_datetime(f"{ano}-{mes_num}-01")

        # Aplicando a conversão
        df_projeto['Início'] = df_projeto['Início'].apply(converter_data)
        df_projeto['Fim'] = df_projeto['Fim'].apply(converter_data)

        # Criando gráfico de Gantt com Plotly Express
        fig = px.timeline(
            df_projeto,
            x_start='Início',
            x_end='Fim',
            y='Atividade',
            color='Situação',
            # hover_data=['Valor'],
            height=250  # Diminuindo a altura do gráfico
        )

        fig.update_yaxes(categoryorder='total ascending')

        # Movendo a legenda para baixo
        fig.update_layout(
            legend=dict(
                orientation="h",       # horizontal
                yanchor="bottom",
                y=-1,                # valor negativo posiciona abaixo do gráfico
                xanchor="center",
                x=0
            ),
            yaxis_title=None
        )

        # Streamlit
        st.plotly_chart(fig, key="cronograma", use_container_width=True)
        