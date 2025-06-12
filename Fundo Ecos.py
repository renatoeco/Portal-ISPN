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
    
def converter_uf_codigo_para_nome(valor):
    """
    Converte um ou mais códigos de UF para seus nomes correspondentes.
    Exemplo de entrada: "12,27"
    """
    if not valor:
        return ""

    try:
        partes = [v.strip() for v in valor.split(",") if v.strip()]
        nomes = []

        for parte in partes:
            if parte.isdigit():
                nome = uf_para_nome.get(parte, parte)
                nomes.append(nome)
            else:
                nomes.append(parte)

        return ", ".join(nomes)
    except Exception as e:
        return valor

    

@st.dialog("Detalhes do projeto", width="large")
def mostrar_detalhes(i):
    projeto_df = df_projetos.iloc[i]
    projeto = todos_projetos[i]  # Supondo que todos_projetos e df_projetos estão na mesma ordem

    st.write(f"**Proponente:** {projeto_df['Proponente']}")
    st.write(f"**Nome do projeto:** {projeto.get('nome_do_projeto', '')}")
    st.write(f"**Edital:** {projeto_df['Edital']}")
    st.write(f"**Ano de aprovação:** {projeto_df['Ano']}")
    st.write(f"**Ponto Focal:** {projeto.get('ponto_focal', '')}")
    st.write(f"**Estado:** {converter_uf_codigo_para_nome(projeto.get('ufs', ''))}")
    st.write(f"**Município(s):** {projeto_df['Municípios']}")
    st.write(f"**Situação:** {projeto.get('status', '')}")
    st.write(f"**Data de início:** {projeto.get('data_inicio_do_contrato', '')}")
    st.write(f"**Data de fim:** {projeto.get('data_final_do_contrato', '')}")
    st.write(f"**Doador:** {projeto_df['Doador']}")
    st.write(f"**Moeda:** {projeto.get('moeda', '')}")
    st.write(f"**Valor:** {projeto_df['Valor']}")
    st.write(f"**Tipo:** {projeto_df['Tipo']}")

    if "indicadores" in projeto:
        df_indicadores = pd.DataFrame(projeto["indicadores"])
        st.write("**Indicadores:**")
        st.dataframe(df_indicadores, hide_index=True)


######################################################################################################
# MAIN
######################################################################################################


# Combine os dados
todos_projetos = pj + pf

dados_municipios = list(ufs_municipios.find())

mapa_doador = {str(proj["_id"]): proj.get("doador", "") for proj in projetos_ispn}

# Criar dicionário código_uf -> nome_uf
uf_para_nome = {}
for doc in dados_municipios:
    for uf in doc.get("ufs", []):
        uf_para_nome[str(uf["codigo_uf"])] = uf["nome_uf"]

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

    # Contabilização única e limpa de UFs
    ufs_unicos = set()

    for projeto in todos_projetos:
        ufs_str = projeto.get("ufs", "")
        ufs_list = [uf.strip() for uf in ufs_str.split(",") if uf.strip()]
        ufs_unicos.update(ufs_list)

    # Contar apenas UFs válidas
    total_ufs = len(ufs_unicos)

    # Total de projetos apoiados
    total_projetos = len(df_projetos)

    # Total de editais únicos (remover vazios)
    total_editais = df_projetos["Edital"].replace("", pd.NA).dropna().nunique()

    # Total de doadores únicos (remover vazios)
    total_doador = df_projetos["Doador"].replace("", pd.NA).dropna().nunique()

    # Total de estados únicos a partir dos municípios (código do estado antes do traço)
    estados_unicos = set()
    for municipios in df_projetos["Municípios"]:
        for m in municipios.split(","):
            m = m.strip()
            if " - " in m:
                estado = m.split(" - ")[0]  # Pega o que vem ANTES do traço (ex: "BA")
                estados_unicos.add(estado)

    total_estados = len(estados_unicos)

    # Contabilização única e limpa de municípios
    municipios_unicos = set()

    for projeto in todos_projetos:
        municipios_str = projeto.get("municipios", "")
        codigos = [m.strip() for m in municipios_str.split(",") if m.strip()]
        nomes = [codigo_para_nome.get(cod, cod) for cod in codigos]
        municipios_unicos.update(nomes)

    total_municipios = len(municipios_unicos)

    # Apresentar em colunas organizadas
    col1, col2, col3 = st.columns(3)

    col1.metric("Projetos apoiados", f"{total_projetos}")
    col2.metric("Editais", f"{total_editais}")
    col3.metric("Doadores", f"{total_doador}")

    col1.metric("Estados", f"{total_ufs}")
    col2.metric("Municípios", f"{total_municipios}")

    st.divider()

    # Converter valores para float
    # df_projetos["Valor_float"] = pd.to_numeric(df_projetos["Valor"].str.replace(",", "").str.replace(".", "", regex=False), errors="coerce")

    # contratos_usd = df_projetos[df_projetos["Doador"].str.upper().str.contains("USAID")]["Valor_float"].sum()
    # contratos_eur = df_projetos[df_projetos["Doador"].str.upper().str.contains("UE|EURO|EU ")]["Valor_float"].sum()
    # contratos_brl = df_projetos[~df_projetos["Doador"].str.upper().str.contains("USAID|UE|EURO|EU ")]["Valor_float"].sum()

    #total_convertido_usd = contratos_usd + contratos_eur + contratos_brl  # Aqui você pode aplicar conversão real se quiser

    # Apresentar

    #col1, col2, col3 = st.columns(3)

    # col1.metric("Contratos em US$", f"{contratos_usd:,.2f}")
    # col2.metric("Contratos em EU$", f"{contratos_eur:,.2f}")
    # col3.metric("Contratos em R$", f"{contratos_brl:,.2f}")

    # col1.metric("Total convertido para US$", f"{total_convertido_usd:,.2f}")

with lista:

    # ui.table(data=df_projetos)
    # Cabeçalho da tabela
    headers = list(df_projetos.columns) + ["Detalhes"]
    col_sizes = [1, 1, 2, 1, 1, 1, 2, 1, 1]  # Personalize os tamanhos das colunas

    st.markdown("### Projetos")
    st.write('')

    # Número de itens por página
    itens_por_pagina = 20

    # Total de linhas do DataFrame
    total_linhas = len(df_projetos)

    # Total de páginas
    total_paginas = (total_linhas - 1) // itens_por_pagina + 1

    col1, col2, col3 = st.columns([5, 2, 1])

    # Seleciona página atual (com key para manter estado)
    pagina_atual = col3.number_input(
        "Página",
        min_value=1,
        max_value=total_paginas,
        value=1,
        step=1,
        key="pagina_projetos"
    )

    # Calcula os índices da página atual
    inicio = (pagina_atual - 1) * itens_por_pagina
    fim = inicio + itens_por_pagina

    # Fatiar DataFrame com os dados da página atual
    df_paginado = df_projetos.iloc[inicio:fim]

    # Exibir informação de paginação
    with col2:
        st.write("")
        st.write("")
        st.write(f"Mostrando {inicio + 1} a {min(fim, total_linhas)} de {total_linhas} resultados")

    st.write("")

    # Cabeçalho visual
    header_cols = st.columns(col_sizes)
    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.divider()

    # Fatia do DataFrame
    df_paginado = df_projetos.iloc[inicio:fim]

    

    # Linhas
    for i, row in df_paginado.iterrows():
        cols = st.columns(col_sizes)
        for j, key in enumerate(df_projetos.columns):
            cols[j].write(row[key])

        # Botão de detalhes, o índice original é necessário
        idx_original = row.name
        cols[-1].button("Detalhes", key=f"ver_{idx_original}", on_click=mostrar_detalhes, args=(idx_original,))
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