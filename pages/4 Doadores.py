import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png")


st.header("Doadores")

tab1, tab2 = st.tabs(["Visão geral", "Doadores"])

with tab1:
    st.write('')

    col1, col2, col3 = st.columns(3)

    col1.selectbox("Projetos vigentes entre", ["2023", "2024", "2025"])
    col2.selectbox("e", ["2023", "2024", "2025"])

    st.write('')


    doadores = pd.DataFrame({
        "Doadores": [
            "KFW", "GIZ", "UE", "USAID", "Fundo Socioambiental Casa", 
            "Instituto Humanitas360", "Brazil Fund", "Citi Foundation", 
            "Cargill", "Mitsubishi Corporation"
        ],
        "Valor": [1000000, 500000, 200000, 150000, 100000, 50000, 30000, 20000, 10000, 5000],
        "Numero de projetos apoiados": [15, 10, 5, 5, 5, 2, 2, 2, 1, 1],
        "Cor": ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF", "#808000", "#008000", "#800080", "#808080"],
        "Tipo de Doador": [
            "Cooperação Internacional",  # KFW
            "Cooperação Internacional",  # GIZ
            "Governo",                   # UE
            "Cooperação Internacional",  # USAID
            "Filantropia Privada",       # Fundo Socioambiental Casa
            "Filantropia Privada",       # Instituto Humanitas360
            "Filantropia Privada",       # Brazil Fund
            "Filantropia Privada",       # Citi Foundation
            "Empresa",                   # Cargill
            "Empresa"                    # Mitsubishi Corporation
        ]
    })

    # Gráfico com Altair
    chart = alt.Chart(doadores).mark_circle().encode(
        x=alt.X('Numero de projetos apoiados', title='Número de Projetos Apoiados'),
        y=alt.Y('Valor', title='Valor (R$)'),
        size=alt.Size('Valor', legend=None),
        color=alt.Color('Doadores:N', scale=alt.Scale(domain=doadores['Doadores'], range=doadores['Cor'])),
        tooltip=['Doadores', 'Valor', 'Numero de projetos apoiados']
    ).properties(
        width=700,
        height=500,
        title='Doadores x Número de projetos e Valores'
    )

    st.altair_chart(chart, use_container_width=True)

    st.write('')
    st.write('')
    st.write('')

    # Gráfico de pizza
    # Agrupar por tipo de doador
    tipo_valor = doadores.groupby("Tipo de Doador", as_index=False)["Valor"].sum()

    # Calcular porcentagem
    tipo_valor["Porcentagem"] = (tipo_valor["Valor"] / tipo_valor["Valor"].sum()) * 100

    # Gráfico de pizza com Altair
    pie_chart = alt.Chart(tipo_valor).mark_arc().encode(
        theta=alt.Theta(field="Valor", type="quantitative"),
        color=alt.Color(field="Tipo de Doador", type="nominal"),
        tooltip=["Tipo de Doador", "Valor"]
    ).properties(
        width=300,
        height=300,
        title="Distribuição de Valores por Tipo de Doador"
    )

    # Exibir gráfico
    st.altair_chart(pie_chart, use_container_width=True)

    # Tabela com valor total e porcentagem formatados, ordenada por porcentagem decrescente
    st.write('')
    st.write('')
    st.dataframe(
        tipo_valor[["Tipo de Doador", "Valor", "Porcentagem"]]
        .sort_values(by="Porcentagem", ascending=False)
        .style.format({
            "Valor": "R$ {:,.2f}",
            "Porcentagem": "{:.2f}%"
        }),
        hide_index=True
    )




with tab2:
    st.write('')

    col1, col2, col3 = st.columns(3)

    doador_selecionado = col1.selectbox("Selecione o doador", ["KFW", "GIZ", "UE", "USAID", "Fundo Socioambiental Casa", "Instituto Humanitas360", "Brazil Fund", "Citi Foundation", "Cargill", "Mitsubishi Corporation"])
    col2.selectbox("Projetos vigentes entre", ["2023", "2024", "2025"], key="doador1")
    col3.selectbox("e", ["2023", "2024", "2025"], key="doador2")

    st.write('')

    st.subheader(doador_selecionado)

    df_projeto = pd.DataFrame({
        "Projeto": ["CEPF", "PACT", "Educação Verde", "Fortalecimento Comunitário"],
        "Valor": [50000.00, 120000.00, 80000.00, 150000.00],
        "Início": ["março/2024", "abril/2024", "janeiro/2025", "fevereiro/2025"],
        "Fim": ["fevereiro/2025", "dezembro/2024", "dezembro/2025", "junho/2025"],
        "Situação": ["Em andamento", "Em andamento", "Em andamento", "Concluído"]
    })

    st.write('')
    st.metric('Valor total dos apoios: R$',(df_projeto['Valor'].sum()))

    st.write('')

    st.write('**Projetos**')
    st.dataframe(df_projeto, hide_index=True)

    st.write('')

    st.write('**Cronograma de projetos**')
    
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

    # Streamlit
    st.plotly_chart(fig)