import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
import plotly.express as px

st.set_page_config(layout="wide")
st.logo("/home/renato/Projetos_Python/ISPN_HUB/app_ispn_hub/images/logo_ISPN_horizontal_ass.png")

st.header("Fundo Ecos")

st.write('')

with st.expander("Filtros"):

    st.pills("Tipo de apoio", ["Projetos PJ", "Projetos PF"], selection_mode="multi", default=["Projetos PJ", "Projetos PF"] )

    col1, col2, col3, col4 = st.columns(4)

    col1.multiselect("Edital", ["Todos", "Edital 35", "Edital 36", "Edital 37", "Edital 38", "Edital 39", "Edital 40","Edital 41"], default="Todos")

    col2.multiselect("Ano do edital", ["Todos", "2017", "2018", "2019", "2020", "2021", "2022","2023"], default="Todos")

    col3.multiselect("Doador", ["Todos", "USAID", "GEF", "UE", "Laudes Foundation"], default="Todos")

    col4.multiselect("Ponto focal", ["Todos", "Renato", "Lívia", "Matheus", "Vitória", "Terena"], default="Todos")

    col1.multiselect("Estado", ["Todos", "BA", "CE", "MA", "TO", "PA"], default="Todos")

    col2.multiselect("Município", ["Todos", "DF - Brasília", "CE - Crateús", "MA - Bacabal", "TO - Palmas", "PA - Belmonte"], default="Todos")

    col3.multiselect("Situação", ["Todos", "Em dia", "Atrasados", "Concluídos", "Cancelados"], default="Todos")

    col1, col2, col3, col4 = st.columns(4)


    col1.text_input("Busca por proponente")

    col2.text_input("Busca por CNPJ")

    col3.text_input("Busca por sigla do projeto")

    col4.text_input("Busca por código do projeto")

st.write('')


geral, lista, mapa = st.tabs(["Visão geral", "Projetos", "Mapa"])

with geral:

    col1, col2, col3 = st.columns(3)

    col1.metric("Projetos apoiados", "1251")

    col2.metric("Editais", "53")

    col3.metric("Doadores", "13")

    col1.metric("Estados", "18")

    col2.metric("Municípios", "294")

    st.divider()

    col1, col2, col3 = st.columns(3)

    col1.metric("Contratos em US$", "11.020.251")

    col2.metric("Contratos em EU$", "9.010.243")

    col3.metric("Contratos em R$", "29.020.251")

    col1.metric("Total convertido para US$", "85.020.251")

with lista:

    @st.dialog("Detalhes do projeto", width="large")
    def mostrar_detalhes():
        st.write("**Proponente:** Associação de moradores do Vale do Corda")
        st.write("**Nome do projeto:** Recuperação de áreas degradadas na bacia do Rio Pajeú")
        st.write("**Edital:** 38")
        st.write("**Ponto focal:** Renato")
        st.write("**Estado(s):** BA")
        st.write("**Município(s):** João Pessoa")
        st.write("**Contatos do projeto:**")
        st.write('- Jorge Palma - jorge@gmail.com - (31) 99999-9999')
        st.write("**Situação:** Em dia")
        st.write("**Visitas:** 15/03/2024 - Renato - Participação do seminário de encerramento")
        st.write("**Data de início:** 15/03/2024")
        st.write("**Data de fim:** 15/03/2025")
        st.write("**Indicadores:**")
        df_indicadores = pd.DataFrame({
            "Indicador": [
                "Número de organizações apoiadas",
                "Número de comunidades fortalecidas",
                "Número de indígenas",
                "Número de famílias"
            ],
            "Reporte": [
                "Organizações do Cerrativismo",
                "Projeto ADEL",
                "Preparação pra COP do Clima",
                "Apoio à Central do Cerrado"
            ],
            "Valor": [
                25,
                2,
                8,
                18,
            ],
            "Ano": [
                2023,
                2023,
                2023,
                2023,
            ],
            "Observações": [
                "Contagem manual",
                "Por conversa telefônica",
                "Se refere ao seminário estadual",
                "Contagem manual",
            ],
            "Autor": [
                "João",
                "Maria",
                "José",
                "Pedro",
            ]
        })
        st.dataframe(df_indicadores, hide_index=True)




    projetos = {
        "Código": [
            "BRA/25/01",
            "BRA/25/02",
            "BRA/25/03",
            "BRA/25/04",
            "BRA/25/05",
        ],
        "Edital": [
            "001/2020",
            "002/2020",
            "003/2020",
            "004/2020",
            "005/2020",
        ],
        "Proponente": [
            "Associação X",
            "Associação Y",
            "Associação Z",
            "Associação W",
            "Associação V",
        ],
        "Doador": [
            "UE",
            "GIZ",
            "KFW",
            "USAID",
            "Citi Foundation",
        ],
        "Valor": [
            "50000.0",
            "120000.0",
            "80000.0",
            "150000.0",
            "20000.0",
        ],
        "Ano": [
            "2020",
            "2020",
            "2020",
            "2020",
            "2020",
        ],
        "Municípios": [
            "Município A",
            "Município B",
            "Município C",
            "Município D",
            "Município E",
        ],
        "Tipo": [
            "PJ",
            "PJ",
            "PF",
            "PJ",
            "PJ",
        ],
    }

    df_projetos = pd.DataFrame(projetos)
    # st.dataframe(df_projetos, height=200)

    # ui.table(data=df_projetos)
    # Cabeçalho da tabela
    headers = list(df_projetos.columns) + ["Detalhes"]
    col_sizes = [1, 1, 2, 1, 1, 1, 2, 1, 1]  # Personalize os tamanhos das colunas

    st.markdown("### Projetos")
    st.write('')

    # Cabeçalho visual
    header_cols = st.columns(col_sizes)
    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.divider()

    # Linhas
    for i, row in df_projetos.iterrows():
        cols = st.columns(col_sizes)
        for j, key in enumerate(df_projetos.columns):
            cols[j].write(row[key])

        # Última coluna com botão
        cols[-1].button("Detalhes", key=f"ver_{i}", on_click=mostrar_detalhes)

        st.divider()








with mapa:


    # Lista dos pontos (latitude, longitude)
    dados = [
        {"lat": -17.952479, "lon": -50.999368},
        {"lat": -24.311754, "lon": -48.699713},
        {"lat": -6.283198,  "lon": -55.983458},
        {"lat": -3.903138,  "lon": -45.033963}
    ]

    # Criar DataFrame
    df = pd.DataFrame(dados)

    # Criar o mapa
    fig = px.scatter_map(
        df,
        lat="lat",
        lon="lon",
        zoom=3,
        height=700,
        # mapbox_style="carto-positron",
        hover_data={"lat": True, "lon": True}
    )

    # Mostrar
    st.plotly_chart(fig)