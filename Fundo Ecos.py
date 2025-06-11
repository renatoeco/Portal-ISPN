import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
import ast
import plotly.express as px
from bson import ObjectId
from funcoes_auxiliares import conectar_mongo_portal_ispn

st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas
pj = list(db["projetos_pj"].find())
pf = list(db["projetos_pf"].find())
projetos_ispn = list(db["projetos_ispn"].find())
ufs_municipios = db["ufs_municipios"]


######################################################################################################
# FUNÇÕES
######################################################################################################


# Função para converter lista de códigos em lista de nomes
def converter_codigos_para_nomes(valor):
    if not valor:
        return ""

    try:
        # Divide por vírgula, remove espaços e filtra vazios
        partes = [v.strip() for v in valor.split(",") if v.strip()]
        nomes = []

        for parte in partes:
            if parte.isdigit():
                # Tenta mapear o código (int convertido para str)
                nome = codigo_para_nome.get(parte, parte)
                nomes.append(nome)
            else:
                # Já é nome (ex: 'Brasília')
                nomes.append(parte)

        return ", ".join(nomes)
    except Exception as e:
        return valor


######################################################################################################
# MAIN
######################################################################################################


# Combine os dados
todos_projetos = pj + pf

dados_municipios = list(ufs_municipios.find())

mapa_doador = {str(proj["_id"]): proj.get("doador", "") for proj in projetos_ispn}

# Criar dicionário de mapeamento código -> nome
codigo_para_nome = {}
for doc in dados_municipios:
    for m in doc.get("municipios", []):
        codigo_para_nome[str(m["codigo_municipio"])] = m["nome_municipio"]
         
for projeto in todos_projetos:
    projeto_pai_id = projeto.get("codigo_projeto_pai")
    if projeto_pai_id:
        projeto["doador"] = mapa_doador.get(str(projeto_pai_id), "")
    else:
        projeto["doador"] = ""

# Transforme em DataFrame
df_projetos = pd.DataFrame(todos_projetos)

# Lista base de colunas obrigatórias
colunas = [
    "codigo",
    "edital",
    "proponente",
    "valor",
    "ano_de_aprovacao",
    "municipios",
    "tipo"
]

# Adiciona "doador" se ela estiver presente no DataFrame
if "doador" in df_projetos.columns:
    colunas.insert(3, "doador")  # Mantém a ordem: após "proponente"

# Seleciona apenas as colunas existentes
df_projetos = df_projetos[colunas].rename(columns={
    "codigo": "Código",
    "edital": "Edital",
    "proponente": "Proponente",
    "doador": "Doador",
    "valor": "Valor",
    "ano_de_aprovacao": "Ano",
    "municipios": "Municípios",
    "tipo": "Tipo"
})


# Garantir que todos os campos estão como string
df_projetos = df_projetos.fillna("").astype(str)

# Aplicar a função na coluna 'Municípios'
df_projetos["Municípios"] = df_projetos["Municípios"].apply(converter_codigos_para_nomes)

# Corrigir a coluna 'Ano' para remover ".0"
df_projetos["Ano"] = df_projetos["Ano"].str.replace(".0", "", regex=False)


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
    # Total de projetos apoiados
    total_projetos = len(df_projetos)

    # Total de editais únicos (remover vazios)
    total_editais = df_projetos["Edital"].replace("", pd.NA).dropna().nunique()

    # Total de doadores únicos (remover vazios)
    total_doador = df_projetos["Doador"].replace("", pd.NA).dropna().nunique()

    # Total de estados únicos a partir dos municípios (usando código nomeado ex: "BA - Salvador")
    estados_unicos = set()

    for municipios in df_projetos["Municípios"]:
        for m in municipios.split(","):
            m = m.strip()
            if " - " in m:
                estado = m.split(" - ")[-1]  # Pega o que vem DEPOIS do traço
                estados_unicos.add(estado)


    # Total de municípios únicos
    todos_municipios = set()
    for municipios in df_projetos["Municípios"]:
        for m in municipios.split(","):
            m = m.strip()
            todos_municipios.add(m)
    total_municipios = len(todos_municipios)

    # Converter valores para float
    df_projetos["Valor_float"] = pd.to_numeric(df_projetos["Valor"].str.replace(",", "").str.replace(".", "", regex=False), errors="coerce")

    contratos_usd = df_projetos[df_projetos["Doador"].str.upper().str.contains("USAID")]["Valor_float"].sum()
    contratos_eur = df_projetos[df_projetos["Doador"].str.upper().str.contains("UE|EURO|EU ")]["Valor_float"].sum()
    contratos_brl = df_projetos[~df_projetos["Doador"].str.upper().str.contains("USAID|UE|EURO|EU ")]["Valor_float"].sum()

    total_convertido_usd = contratos_usd + contratos_eur + contratos_brl  # Aqui você pode aplicar conversão real se quiser

    # Apresentar
    col1, col2, col3 = st.columns(3)
    col1.metric("Projetos apoiados", f"{total_projetos}")
    col2.metric("Editais", f"{total_editais}")
    col3.metric("Doadores", f"{total_doador}")

    col1.metric("Estados", len(estados_unicos))
    col2.metric("Municípios", f"{total_municipios}")

    st.divider()

    col1, col2, col3 = st.columns(3)

    col1.metric("Contratos em US$", f"{contratos_usd:,.2f}")
    col2.metric("Contratos em EU$", f"{contratos_eur:,.2f}")
    col3.metric("Contratos em R$", f"{contratos_brl:,.2f}")

    col1.metric("Total convertido para US$", f"{total_convertido_usd:,.2f}")

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

    #df_projetos = pd.DataFrame(projetos)
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