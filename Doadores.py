import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import random
from funcoes_auxiliares import conectar_mongo_portal_ispn


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas
doadores = db["projetos_ispn"] 

# Busca documentos com valor preenchido
cursor = doadores.find({
    "valor": {"$exists": True, "$ne": ""}
})
   

######################################################################################################
# MAIN
######################################################################################################


st.header("Doadores")

dados = list(cursor)
df = pd.DataFrame(dados)

# Conversão e limpeza do valor
df["valor"] = (
    df["valor"]
    .astype(str)
    .str.replace(".", "", regex=False)   # Remove separadores de milhar
    .str.replace(",", ".", regex=False)  # Troca vírgula decimal por ponto
)
df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

df["tipo_de_doador"] = df["tipo_de_doador"].str.capitalize()

tab1, tab2 = st.tabs(["Visão geral", "Doadores"])

with tab1:
    st.write('')

    col1, col2, col3 = st.columns(3)
    col1.selectbox("Projetos vigentes entre", ["2023", "2024", "2025"])
    col2.selectbox("e", ["2023", "2024", "2025"])

    st.write('')

    # Conversão e limpeza de dados
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["valor"])
    df["doador"] = df["doador"].fillna("Desconhecido")
    df["tipo_de_doador"] = df["tipo_de_doador"].fillna("Outro")

    # Agrupar por doador
    resumo = df.groupby(["doador", "tipo_de_doador"], as_index=False).agg({
        "valor": "sum",
        "_id": "count"
    }).rename(columns={
        "valor": "Valor",
        "_id": "Numero de projetos apoiados",
        "doador": "Doadores",
        "tipo_de_doador": "Tipo de Doador"
    })

    # Gerar cores únicas por doador
    def gerar_cor():
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))
    resumo["Cor"] = [gerar_cor() for _ in range(len(resumo))]

    # Gráfico com Altair
    resumo["Valor_br"] = resumo["Valor"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    chart = alt.Chart(resumo).mark_circle().encode(
        x=alt.X('Numero de projetos apoiados', title='Número de Projetos Apoiados'),
        y=alt.Y('Valor', title='Valor (R$)'),
        size=alt.Size('Valor', legend=None),
        color=alt.Color('Doadores:N', scale=alt.Scale(domain=resumo['Doadores'], range=resumo['Cor'])),
        tooltip=[
            'Doadores',
            alt.Tooltip('Valor_br', type='nominal', title='Valor'),
            'Numero de projetos apoiados'
        ]
    ).properties(
        width=700,
        height=500,
        title='Doadores x Número de projetos e Valores'
    )


    st.altair_chart(chart, use_container_width=True)

    st.write('')
    st.write('')

    # Gráfico de pizza por tipo de doador
    tipo_valor = resumo.groupby("Tipo de Doador", as_index=False)["Valor"].sum()
    tipo_valor["Porcentagem"] = (tipo_valor["Valor"] / tipo_valor["Valor"].sum()) * 100
    tipo_valor["Valor_br"] = tipo_valor["Valor"].apply(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    pie_chart = alt.Chart(tipo_valor).mark_arc().encode(
        theta=alt.Theta(field="Valor", type="quantitative"),
        color=alt.Color(field="Tipo de Doador", type="nominal"),
        tooltip=["Tipo de Doador", alt.Tooltip("Valor_br", type="nominal", title="Valor")]
    )

    st.altair_chart(pie_chart, use_container_width=True)

    st.write('')
    st.dataframe(
        tipo_valor[["Tipo de Doador", "Valor", "Porcentagem"]]
        .sort_values(by="Porcentagem", ascending=False)
        .style.format({
            "Valor": lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "Porcentagem": "{:.2f}%"
        }),
        hide_index=True,
        use_container_width=True
    )


with tab2:
    st.write('')

    df = df.dropna(subset=["valor"])
    df["doador"] = df["doador"].fillna("Desconhecido")
    df["data_inicio_contrato"] = df["data_inicio_contrato"].fillna("")
    df["data_fim_contrato"] = df["data_fim_contrato"].fillna("")

    # Lista de doadores únicos
    doadores_unicos = sorted(df["doador"].unique())

    # Filtros
    col1, col2, col3 = st.columns(3)
    doador_selecionado = col1.selectbox("Selecione o doador", doadores_unicos)
    col2.selectbox("Projetos vigentes entre", ["2023", "2024", "2025"], key="doador1")
    col3.selectbox("e", ["2023", "2024", "2025"], key="doador2")

    st.write('')

    st.subheader(doador_selecionado)

    # Filtrar dados do doador
    df_doador = df[df["doador"] == doador_selecionado].copy()

    # Converter datas
    def parse_data(data_str):
        try:
            return pd.to_datetime(data_str, format="%d/%m/%Y")
        except:
            return pd.NaT

    df_doador["Início"] = df_doador["data_inicio_contrato"].apply(parse_data)
    df_doador["Fim"] = df_doador["data_fim_contrato"].apply(parse_data)
    df_doador["Projeto"] = df_doador["nome_do_projeto"].fillna("Sem nome")
    df_doador["Situação"] = df_doador["status"].fillna("Desconhecido")

    # Mostrar métrica total
    valor_total = df_doador['valor'].sum()
    st.metric('Valor total dos apoios', f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))


    st.write('')
    st.write('**Projetos**')

    # E na exibição do dataframe:
    st.dataframe(
        df_doador[["Projeto", "valor", "data_inicio_contrato", "data_fim_contrato", "Situação"]]
        .rename(columns={
            "valor": "Valor (R$)",
            "data_inicio_contrato": "Início",
            "data_fim_contrato": "Fim"
        })
        .sort_values(by="Início")
        .style.format({
            "Valor (R$)": lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        }),
        hide_index=True
        )

    st.write('')
    st.write('**Cronograma de projetos**')

    # Ordena por data de início para exibir em ordem cronológica
    df_doador_sorted = df_doador.sort_values(by="Início", ascending=False)

    fig = px.timeline(
        df_doador_sorted,
        x_start='Início',
        x_end='Fim',
        y='Projeto',
        color='Situação',
        hover_data=['valor'],
        height=300
    )

    # Atualiza o eixo Y com os projetos na ordem correta
    fig.update_yaxes(
        categoryorder='array',
        categoryarray=df_doador_sorted["Projeto"].tolist()
    )


    st.plotly_chart(fig)