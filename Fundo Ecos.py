import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
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
pessoas = db["pessoas"]


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

    # Pega o valor de ponto_focal diretamente
    ponto_focal_obj = projeto.get("ponto_focal")

    # Inicializa nome padrão
    nome_ponto_focal = "Não informado"

    # Se ponto_focal existir e for ObjectId, busca na coleção
    if isinstance(ponto_focal_obj, ObjectId):
        pessoa = db["pessoas"].find_one({"_id": ponto_focal_obj})
        if pessoa:
            nome_ponto_focal = pessoa.get("nome_completo", "Não encontrado")
        else:
            nome_ponto_focal = "Não encontrado"
    

    st.write(f"**Proponente:** {projeto.get('proponente', '')}")
    st.write(f"**Nome do projeto:** {projeto.get('nome_do_projeto', '')}")
    st.write(f"**Tipo:** {projeto.get('tipo', '')}")
    st.write(f"**Edital:** {projeto_df['Edital']}")
    st.write(f"**Doador:** {projeto_df['Doador']}")
    st.write(f"**Moeda:** {projeto.get('moeda', '')}")
    st.write(f"**Valor:** {projeto_df['Valor']}")
    st.write(f"**Categoria:** {projeto.get('categoria', '')}")
    st.write(f"**Ano de aprovação:** {projeto_df['Ano']}")
    st.write(f"**Estado(s):** {converter_uf_codigo_para_nome(projeto.get('ufs', ''))}")
    st.write(f"**Município(s):** {converter_codigos_para_nomes(projeto.get('municipios', ''))}")
    st.write(f"**Data de início:** {projeto.get('data_inicio_do_contrato', '')}")
    st.write(f"**Data de fim:** {projeto.get('data_final_do_contrato', '')}")
    st.write(f"**Ponto Focal:** {nome_ponto_focal}")
    st.write(f"**Temas:** {projeto.get('temas', '')}")
    st.write(f"**Público:** {projeto.get('publico', '')}")
    st.write(f"**Bioma:** {projeto.get('bioma', '')}")
    st.write(f"**Situação:** {projeto.get('status', '')}")
    st.write(f"**Objetivo geral:** {projeto.get('objetivo_geral', '')}")

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


for projeto in todos_projetos:
    valor_bruto = projeto.get("valor")

    if isinstance(valor_bruto, str):
        valor_limpo = valor_bruto.replace(".", "").replace(",", ".")
        try:
            projeto["valor"] = float(valor_limpo)
        except:
            projeto["valor"] = None
    elif isinstance(valor_bruto, (int, float)):
        projeto["valor"] = float(valor_bruto)
    else:
        projeto["valor"] = None


# Transforme em DataFrame
df_projetos = pd.DataFrame(todos_projetos)

# Dicionário de símbolos por moeda
simbolos = {
    "reais": "R$",
    "real": "R$",
    "dólares": "US$",
    "dólar": "US$",
    "euros": "€",  # Incluído para futuro uso
    "euro": "€"
}

# Lista base de colunas obrigatórias
colunas = [
    "codigo",
    "sigla",
    "edital",
    "valor",
    "categoria",
    "ano_de_aprovacao",
    "ufs",
    "municipios",
    "tipo",
    "municipio_principal"
]

# Adiciona "doador" se ela estiver presente no DataFrame
if "doador" in df_projetos.columns:
    colunas.insert(3, "doador")  # Mantém a ordem: após "proponente"

# Seleciona apenas as colunas existentes
df_projetos = df_projetos[colunas].rename(columns={
    "codigo": "Código",
    "sigla": "Sigla",
    "edital": "Edital",
    "doador": "Doador",
    "valor": "Valor",
    "categoria": "Categoria",
    "ano_de_aprovacao": "Ano",
    "ufs": "Estado(s)",
    "municipios": "Município(s)",
    "tipo": "Tipo",
    "municipio_principal": "Município Principal"
})


# Garantir que todos os campos estão como string
df_projetos = df_projetos.fillna("").astype(str)

# Aplicar a função na coluna 'Municípios'
df_projetos["Município(s)"] = df_projetos["Município(s)"].apply(converter_codigos_para_nomes)
df_projetos["Município Principal"] = df_projetos["Município Principal"].apply(converter_codigos_para_nomes)

# Corrigir a coluna 'Ano' para remover ".0"
df_projetos["Ano"] = df_projetos["Ano"].str.replace(".0", "", regex=False)

df_projetos["Estado(s)"] = [
    converter_uf_codigo_para_nome(proj.get("ufs", "")) for proj in todos_projetos
]

valores_formatados = []
for i, projeto in enumerate(todos_projetos):
    valor = df_projetos.at[i, "Valor"]
    moeda = projeto.get("moeda", "reais").lower()

    
    simbolo = simbolos.get(moeda, "")

    # Limpar o valor original antes da conversão
    valor_limpo = valor.replace("R$", "").replace("US$", "").replace("€", "").replace(" ", "")

    try:
        # Detectar se está no formato brasileiro (vírgula como decimal)
        if "," in valor_limpo and valor_limpo.count(",") == 1 and valor_limpo.count(".") >= 0:
            # Substitui "." por "" (remove separadores de milhar) e "," por "." (converte decimal brasileiro)
            valor_float = float(valor_limpo.replace(".", "").replace(",", "."))

        else:
            valor_float = float(valor_limpo.replace(",", ""))

        valor_formatado = f"{simbolo} {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        valor_formatado = f"{simbolo} {valor}" if valor else ""

    valores_formatados.append(valor_formatado)

df_projetos["Valor"] = valores_formatados

st.header("Fundo Ecos")

st.write('')


geral, lista, mapa = st.tabs(["Visão geral", "Projetos", "Mapa"])

with geral:
    
    # Separar projetos PF e PJ
    df_pf = df_projetos[df_projetos['Tipo'] == 'PF']
    df_pj = df_projetos[df_projetos['Tipo'] == 'PJ']

    total_projetos_pf = len(df_pf)
    total_projetos_pj = len(df_pj)

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
    for municipios in df_projetos["Município(s)"]:
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
    
    col1.metric("Editais", f"{total_editais}")
    col2.metric("Doadores", f"{total_doador}")

    col1, col2, col3= st.columns(3)
    
    col1.metric("Total de apoios", f"{total_projetos}")
    col2.metric("Apoios a Pessoa Jurídica", f"{total_projetos_pj}")
    col3.metric("Apoios a Pessoa Física", f"{total_projetos_pf}")
    
    col1, col2, col3 = st.columns(3)

    col1.metric("Estados", f"{total_ufs}")
    col2.metric("Municípios", f"{total_municipios}")

    st.divider()

    # Taxas de câmbio
    TAXA_BRL_PARA_USD = 0.18   # Ex: 1 BRL = 0.18 USD
    
    contratos_brl = 0
    contratos_usd = 0
    contratos_eur = 0

    for projeto in todos_projetos:
        valor = projeto.get("valor")
        moeda = str(projeto.get("moeda", "")).strip().lower()

        if not isinstance(valor, (int, float)):
            continue

        if moeda in ["real", "reais"]:
            contratos_brl += valor
        elif moeda in ["dólar", "dólares"]:
            contratos_usd += valor
        elif moeda in ["euro", "euros"]:
            contratos_eur += valor

    # Conversão para USD
    brl_em_usd = contratos_brl * TAXA_BRL_PARA_USD

    total_convertido_usd = contratos_usd + brl_em_usd


    # Apresentar

    col1, col2, col3 = st.columns(3)

    col1.metric("Contratos em US$", f"{contratos_usd:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    #col2.metric("Contratos em EU$", f"€ {contratos_eur:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("Contratos em R$", f"{contratos_brl:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    col3.metric("Total dos contratos em US$", f"{total_convertido_usd:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))


with lista:

    with st.expander("Filtros", expanded=False, icon=":material/filter_alt:"):

        # Divisão em colunas
        col1, col2, col3, col4 = st.columns(4)

        editais_disponiveis = sorted(df_projetos["Edital"].dropna().unique(), key=lambda x: float(x))
        anos_disponiveis = sorted(df_projetos["Ano"].dropna().unique())
        doadores_disponiveis = sorted(df_projetos["Doador"].dropna().unique())
        codigos_disponiveis = sorted(df_projetos["Código"].dropna().unique())
        tipos_disponiveis = ["Projetos PJ", "Projetos PF"]
        
        # Extrair todos os estados únicos, considerando que podem estar separados por vírgula
        estados_unicos = sorted(
            df_projetos["Estado(s)"]
            .dropna()
            .apply(lambda x: [m.strip() for m in x.split(",")])
            .explode()
            .unique()
        )
        
        tipo_sel = col1.pills("Tipo", tipos_disponiveis, selection_mode="multi")

        col1, col2, col3, col4 = st.columns(4)
        
        codigo_sel = col1.multiselect("Código", options=codigos_disponiveis, default=[], placeholder="Todos")
        ano_sel = col2.multiselect("Ano", options=anos_disponiveis, default=[], placeholder="Todos")
        edital_sel = col3.multiselect("Edital", options=editais_disponiveis, default=[], placeholder="Todos")
        doador_sel = col4.multiselect("Doador", options=doadores_disponiveis, default=[], placeholder="Todos")


        col5, col6 = st.columns(2)

        uf_sel = col5.multiselect(
            "Estado(s)",
            options=estados_unicos,
            default=[],
            placeholder="Todos"
        )

        municipio_sel = col6.multiselect(
            "Município",
            options=sorted(
                df_projetos["Município(s)"]
                .dropna()
                .apply(lambda x: [m.strip() for m in x.split(",")])
                .explode()
                .unique()
            ),
            default=[],
            placeholder="Todos"
        )

        # Filtro base (considera 'Todos' se nada for selecionado)
        df_filtrado = df_projetos.copy()

        if edital_sel:
            df_filtrado = df_filtrado[df_filtrado["Edital"].isin(edital_sel)]

        if ano_sel:
            df_filtrado = df_filtrado[df_filtrado["Ano"].isin(ano_sel)]

        if doador_sel:
            df_filtrado = df_filtrado[df_filtrado["Doador"].isin(doador_sel)]
            
        # Código
        if codigo_sel:
            df_filtrado = df_filtrado[df_filtrado["Código"].isin(codigo_sel)]

        # Tipo de apoio
        if "Projetos PJ" in tipo_sel and "Projetos PF" not in tipo_sel:
            df_filtrado = df_filtrado[df_filtrado["Tipo"] == "PJ"]
        elif "Projetos PF" in tipo_sel and "Projetos PJ" not in tipo_sel:
            df_filtrado = df_filtrado[df_filtrado["Tipo"] == "PF"]


        # Filtro de estados
        if uf_sel:
            df_filtrado = df_filtrado[
                df_filtrado["Estado(s)"].apply(
                    lambda x: any(m.strip() in uf_sel for m in x.split(",")) if isinstance(x, str) else False
                )
            ]

        # Município
        if municipio_sel:
            df_filtrado = df_filtrado[
                df_filtrado["Município(s)"].apply(
                    lambda x: any(m.strip() in municipio_sel for m in x.split(","))
                )
            ]

    st.write("")

    # Paginação
    itens_por_pagina = 50
    total_linhas = len(df_filtrado)
    total_paginas = (total_linhas - 1) // itens_por_pagina + 1

    col1, col2, col3 = st.columns([5, 2, 1])
    pagina_atual = col3.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1, key="pagina_projetos")

    inicio = (pagina_atual - 1) * itens_por_pagina
    fim = inicio + itens_por_pagina
    df_paginado = df_filtrado.iloc[inicio:fim]

    with col2:
        st.write("")
        st.write("")
        st.write(f"Mostrando {inicio + 1} a {min(fim, total_linhas)} de {total_linhas} resultados")

    st.write("")

    colunas_visiveis = [col for col in df_filtrado.columns if col not in ["Tipo", "Município Principal"]]
    headers = colunas_visiveis + ["Detalhes"]

    col_sizes = [2, 2, 1, 2, 2, 2, 1, 2, 3, 3]
    header_cols = st.columns(col_sizes)
    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.divider()

    for i, row in df_paginado.iterrows():
        cols = st.columns(col_sizes)
        for j, key in enumerate(colunas_visiveis):
            cols[j].write(row[key])
        idx_original = row.name
        cols[-1].button("Detalhes", key=f"ver_{idx_original}", on_click=mostrar_detalhes, args=(idx_original,), icon=":material/menu:")
        
        st.divider()





with mapa:
    st.subheader("Mapa de distribuição de projetos")
    
    projeto = todos_projetos[i]
    
    # Pega o valor de ponto_focal diretamente
    ponto_focal_obj = projeto.get("ponto_focal")

    # Inicializa nome padrão
    nome_ponto_focal = "Não informado"

    # Se ponto_focal existir e for ObjectId, busca na coleção
    if isinstance(ponto_focal_obj, ObjectId):
        pessoa = db["pessoas"].find_one({"_id": ponto_focal_obj})
        if pessoa:
            nome_ponto_focal = pessoa.get("nome_completo", "Não encontrado")
        else:
            nome_ponto_focal = "Não encontrado"

    # Carregar CSV dos municípios com lat/lon
    url_municipios = "https://raw.githubusercontent.com/kelvins/Municipios-Brasileiros/master/csv/municipios.csv"
    df_munis = pd.read_csv(url_municipios)

    # Padronizar nomes dos municípios no CSV
    df_munis['nome_normalizado'] = df_munis['nome'].str.strip().str.lower()

    # Corrigir nomes manualmente nos projetos antes do merge (se precisar)
    correcoes_municipios = {
        'tabocão': 'fortaleza do tabocão',
        # adicionar outras correções se quiser
    }

    # Normalizar e corrigir nomes dos municípios nos projetos
    df_projetos = df_projetos.copy()
    df_projetos['Municipio_normalizado'] = (
        df_projetos['Município Principal']
        .str.lower()
        .str.strip()
        .replace(correcoes_municipios)
    )

    # Fazer o merge para pegar lat/lon
    df_coords_projetos = df_projetos.merge(
        df_munis,
        left_on='Municipio_normalizado',
        right_on='nome_normalizado',
        how='left'
    )

    # Filtrar só projetos que têm coordenadas conhecidas
    df_coords_projetos = df_coords_projetos.dropna(subset=['latitude', 'longitude'])
    
    df_coords_projetos = df_coords_projetos.drop_duplicates(subset='Código')

    # Criar o mapa
    m = folium.Map(location=[-15.78, -47.93], zoom_start=4, tiles="CartoDB positron")
    cluster = MarkerCluster().add_to(m)

    # Criar um marcador POR PROJETO
    for _, row in df_coords_projetos.iterrows():
        
        
        
        lat = row['latitude']
        lon = row['longitude']
        nome_muni = row['nome'].title()
        codigo = row['Código']
        proponente = f"{projeto.get('proponente', '')}"
        nome_proj = f"{projeto.get('nome_do_projeto', '')}"
        edital = row['Edital']
        ano_de_aprovacao = row['Ano']
        ponto_focal = f"{nome_ponto_focal}" 

        # Popup com divider (usando <hr>)
        popup_html = f"""
            <b>Município:</b> {nome_muni}<br>
            <hr>
            <b>Código:</b> {codigo}<br>
            <b>Proponente:</b> {proponente}<br>
            <b>Projeto:</b> {nome_proj}<br>
            <b>Edital:</b> {edital}<br>
            <b>Ano:</b> {ano_de_aprovacao}<br>
            <b>Ponto Focal:</b> {nome_ponto_focal}
        """


        folium.Marker(
            location=[lat, lon],
            popup=popup_html,
        ).add_to(cluster)

    # Exibir o mapa no Streamlit
    st_folium(m, width=None, height=800, returned_objects=[])

