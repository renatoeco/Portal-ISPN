import streamlit as st
import pandas as pd
import folium
import math
import plotly.express as px
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

pj = list(db["projetos_pj"].find())
pf = list(db["projetos_pf"].find())
projetos_ispn = list(db["projetos_ispn"].find())

colecao_doadores = db["doadores"]
ufs_municipios = db["ufs_municipios"]
pessoas = db["pessoas"]
estatistica = db["estatistica"]  # Coleção de estatísticas

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
    

@st.cache_data
def carregar_pontos_focais(_todos_projetos):
    ids = [p["ponto_focal"] for p in _todos_projetos if isinstance(p.get("ponto_focal"), ObjectId)]
    pessoas = db["pessoas"].find({"_id": {"$in": ids}})
    return {p["_id"]: p.get("nome_completo", "Não encontrado") for p in pessoas}
    

@st.dialog("Detalhes do projeto", width="large")
def mostrar_detalhes(i):
    projeto_df = df_filtrado.iloc[i]
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

    # Buscar indicadores com base no código do projeto
    codigo_projeto = projeto.get("codigo", "")

    nomes_legiveis = {
        "numero_de_organizacoes_apoiadas": "Número de organizações apoiadas",
        "numero_de_comunidades_fortalecidas": "Número de comunidades fortalecidas",
        "numero_de_familias": "Número de famílias beneficiadas",
        "numero_de_homens_jovens": "Número de homens jovens",
        "numero_de_homens_adultos": "Número de homens adultos",
        "numero_de_mulheres_jovens": "Número de mulheres jovens",
        "numero_de_mulheres_adultas": "Número de mulheres adultas",
        "numero_de_indigenas": "Número de indígenas",
        "numero_de_lideranas_comunitarias_fortalecidas": "Número de lideranças comunitárias fortalecidas",
        "numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_ppp_ecos": "Número de famílias comercializando produtos da sociobio com apoio do PPP-ECOS",
        "numero_de_familias_acessando_vendas_institucionais_com_apoio_do_ppp_ecos": "Número de famílias acessando vendas institucionais com apoio do PPP-ECOS",
        "numero_de_estudantes_recebendo_bolsa": "Número de estudantes recebendo bolsa",
        "numero_de_capacitacoes_realizadas": "Número de capacitações realizadas",
        "numero_de_homens_jovens_capacitados": "Número de homens jovens capacitados",
        "numero_de_homens_adultos_capacitados": "Número de homens adultos capacitados",
        "numero_de_mulheres_jovens_capacitadas": "Número de mulheres jovens capacitadas",
        "numero_de_mulheres_adultas_capacitadas": "Número de mulheres adultas capacitadas",
        "numero_de_intercambios_realizados": "Número de intercâmbios realizados",
        "numero_de_homens_em_intercambios": "Número de homens em intercâmbios",
        "numero_de_mulheres_em_intercambios": "Número de mulheres em intercâmbios",
        "numero_de_iniciativas_de_gestao_territorial_implantadas": "Número de iniciativas de gestão territorial implantadas",
        "area_com_manejo_ecologico_do_fogo_ha": "Área com manejo ecológico do fogo (ha)",
        "area_com_manejo_agroecologico_ha": "Área com manejo agroecológico (ha)",
        "area_com_manejo_para_restauracao_ha": "Área com manejo para restauração (ha)",
        "area_com_manejo_para_extrativismo_ha": "Área com manejo para extrativismo (ha)",
        "numero_de_agroindustiras_implementadas_ou_reformadas": "Número de agroindústrias implementadas ou reformadas",
        "numero_de_tecnologias_instaladas": "Número de tecnologias instaladas",
        "numero_de_pessoas_beneficiadas_com_tecnologias": "Número de pessoas beneficiadas com tecnologias",
        "numero_de_videos_produzidos": "Número de vídeos produzidos",
        "numero_de_aparicoes_na_midia": "Número de aparições na mídia",
        "numero_de_publicacoes_de_carater_tecnico": "Número de publicações de caráter técnico",
        "numero_de_artigos_academicos_produzidos_e_publicados": "Número de artigos acadêmicos produzidos e publicados",
        "numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn": "Número de comunicadores comunitários contribuindo na execução das ações do ISPN",
        "faturamento_bruto_anual_pre_projeto": "Faturamento bruto anual pré-projeto",
        "faturamento_bruto_anual_pos_projeto": "Faturamento bruto anual pós-projeto",
        "volume_financeiro_de_vendas_institucionais_com_apoio_do_ppp_ecos": "Volume financeiro de vendas institucionais com apoio do PPP-ECOS",
        "numero_de_visitas_de_monitoramento_realizadas_ao_projeto_apoiado": "Número de visitas de monitoramento realizadas ao projeto apoiado",
        "valor_da_contrapartida_financeira_projetinhos": "Valor da contrapartida financeira (projetinhos)",
        "valor_da_contrapartida_nao_financeira_projetinhos": "Valor da contrapartida não financeira (projetinhos)",
        "especies": "Espécies",
        "numero_de_organizacoes_apoiadas_que_alavancaram_recursos": "Número de organizações que alavancaram recursos",
        "valor_mobilizado_de_novos_recursos": "Valor mobilizado de novos recursos",
        "numero_de_politicas_publicas_monitoradas_pelo_ispn": "Número de políticas públicas monitoradas pelo ISPN",
        "numero_de_proposicoes_legislativas_acompanhadas_pelo_ispn": "Número de proposições legislativas acompanhadas pelo ISPN",
        "numero_de_contribuicoes_notas_tecnicas_participacoes_e_ou_documentos_que_apoiam_a_construcao_e_aprimoramento_de_politicas_publicas": "Número de contribuições (notas técnicas, participações e/ou documentos) que apoiam a construção e aprimoramento de políticas públicas",
        "numero_de_imoveis_rurais_com_producao_sustentavel": "Número de imóveis rurais com produção sustentável",
        "area_de_vegetacao_natural_diretamente_manejada": "Área de vegetação natural diretamente manejada (ha)",
        "area_de_recuperacao_tecnica_saf": "Área de recuperação técnica (SAF) (ha)",
        "area_de_recuperacao_tecnica_regeneracao": "Área de recuperação técnica (regeneração) (ha)",
        "area_de_recuperacao_tecnica_plantio_adensamento": "Área de recuperação técnica (plantio/adensamento) (ha)",
        "numero_de_unidades_demonstrativas_de_plantio": "Número de unidades demonstrativas de plantio",
        "numero_de_infraestruturas_de_producao_implantadas": "Número de infraestruturas de produção implantadas",
        "numero_de_transportes_adquiridos_para_plantio": "Número de transportes adquiridos para plantio",
        "numero_de_transportes_adquiridos_para_beneficiamento": "Número de transportes adquiridos para beneficiamento",
        "faturamento_bruto_produtos_in_natura": "Faturamento bruto de produtos in natura",
        "faturamento_bruto_produtos_beneficiados": "Faturamento bruto de produtos beneficiados"
    }


    if codigo_projeto:
        indicadores = db["indicadores"].find_one({"codigo": codigo_projeto})

        if indicadores:
            # Remove campos que não são indicadores
            indicadores_filtrados = {
                k: v for k, v in indicadores.items()
                if k not in ["_id", "codigo", "sigla"] and str(v).strip() not in ["", "None", "nan"]
            }

            if indicadores_filtrados:
                # Criar dataframe para exibição
                df_indicadores = pd.DataFrame(
                    list(indicadores_filtrados.items()),
                    columns=["Indicador", "Valor"]
                )

                df_indicadores["Indicador"] = df_indicadores["Indicador"].map(
                    lambda x: nomes_legiveis.get(x, x)  # Usa nome legível se existir, senão mantém original
                )


                st.write("**Indicadores do projeto:**")
                st.dataframe(df_indicadores, hide_index=True, use_container_width=True)
            else:
                st.info("Este projeto não possui indicadores preenchidos.")
        else:
            st.info("Nenhum indicador encontrado para este projeto.")



######################################################################################################
# TRATAMENTO DE DADOS
######################################################################################################


# # Capturar os valores legíveis de doador e programa-----------------------------------
# # --- 1. Converter listas de documentos em DataFrames ---
# df_doadores = pd.DataFrame(list(db["doadores"].find()))
# df_programas = pd.DataFrame(list(db["programas_areas"].find()))
# df_projetos_ispn = pd.DataFrame(list(db["projetos_ispn"].find()))

# # --- 2. Criar dicionários de mapeamento ---
# mapa_doador = {d["_id"]: d["nome_doador"] for d in db["doadores"].find()}
# mapa_programa = {p["_id"]: p["nome_programa_area"] for p in db["programas_areas"].find()}

# # --- 3. Aplicar os mapeamentos ao df_projetos_ispn ---
# df_projetos_ispn["doador_nome"] = df_projetos_ispn["doador"].map(mapa_doador)
# df_projetos_ispn["programa_nome"] = df_projetos_ispn["programa"].map(mapa_programa)
# # --------------------------------------------------------------------------------------
# st.write(df_projetos_ispn.head(1))

# # Renomear as colunas
# df_projetos_ispn.rename(columns={"programa": "id_programa",
#                                  "doador": "id_doador"}, inplace=True)
# df_projetos_ispn.rename(columns={"programa_nome": "programa",
#                                  "doador_nome": "doador"}, inplace=True)




# Combine os dados
todos_projetos = pj + pf

dados_municipios = list(ufs_municipios.find())

mapa_nome_doador = {
    str(d["_id"]): d.get("nome_doador", "") for d in colecao_doadores.find()
}

mapa_doador = {}
for proj in projetos_ispn:
    id_proj = str(proj["_id"])
    id_doador = proj.get("doador")
    
    if isinstance(id_doador, ObjectId):
        nome_doador = mapa_nome_doador.get(str(id_doador), "")
        mapa_doador[id_proj] = nome_doador
    else:
        mapa_doador[id_proj] = ""



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
    "municipio_principal",
    "cnpj",
    "programa"
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
    "municipio_principal": "Município Principal",
    "cnpj": "CNPJ"
})

df_projetos_codigos = df_projetos


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




# Capturar os valores legíveis de doador e programa-----------------------------------
# --- 1. Converter listas de documentos em DataFrames ---
df_doadores = pd.DataFrame(list(db["doadores"].find()))
# df_programas = pd.DataFrame(list(db["programas_areas"].find()))
# df_projetos = pd.DataFrame(list(db["projetos_ispn"].find()))

# --- 2. Criar dicionários de mapeamento ---

# Criar o dicionário com as chaves como strings
mapa_doador = {str(d["_id"]): d["nome_doador"] for d in db["doadores"].find()}
# Transformar os valores da coluna "Doador" em string antes de mapear
df_projetos["doador_nome"] = df_projetos["Doador"].astype(str).map(mapa_doador)

# mapa_doador = {d["_id"]: d["nome_doador"] for d in db["doadores"].find()}
# mapa_programa = {p["_id"]: p["nome_programa_area"] for p in db["programas_areas"].find()}


# --- 3. Aplicar os mapeamentos ao df_projetos ---
df_projetos["doador_nome"] = df_projetos["Doador"].map(mapa_doador)
# df_projetos["programa_nome"] = df_projetos["programa"].map(mapa_programa)
# --------------------------------------------------------------------------------------


# Renomear as colunas
df_projetos.rename(columns={"Doador": "id_doador"}, inplace=True)
df_projetos.rename(columns={"doador_nome": "Doador"}, inplace=True)


# ########################################################################################
# INTERFACE
# ########################################################################################



st.header("Fundo Ecos")

st.write('')

with st.expander("Filtros", expanded=False, icon=":material/filter_alt:"):
        df_filtrado = df_projetos.copy()

        # ===== PRIMEIRA LINHA =====
        
        # Tipo
        col1, col2 = st.columns(2)
        tipos_disponiveis = ["Projetos PJ", "Projetos PF"]
        tipo_sel = col1.pills("Tipo", tipos_disponiveis, selection_mode="multi")

        if tipo_sel:
            if "Projetos PJ" in tipo_sel and "Projetos PF" not in tipo_sel:
                df_filtrado = df_filtrado[df_filtrado["Tipo"] == "PJ"]
            elif "Projetos PF" in tipo_sel and "Projetos PJ" not in tipo_sel:
                df_filtrado = df_filtrado[df_filtrado["Tipo"] == "PF"]

        col1, col2, col3, col4 = st.columns(4)

        # Edital
        editais_disponiveis = sorted(df_filtrado["Edital"].dropna().unique(), key=lambda x: float(x))
        edital_sel = col1.multiselect("Edital", options=editais_disponiveis, placeholder="Todos")
        if edital_sel:
            df_filtrado = df_filtrado[df_filtrado["Edital"].isin(edital_sel)]

        # Ano
        anos_disponiveis = sorted(df_filtrado["Ano"].dropna().unique())
        ano_sel = col2.multiselect("Ano", options=anos_disponiveis, placeholder="Todos")
        if ano_sel:
            df_filtrado = df_filtrado[df_filtrado["Ano"].isin(ano_sel)]

        # Doador
        doadores_disponiveis = sorted(df_filtrado["Doador"].dropna().unique())
        doador_sel = col3.multiselect("Doador", options=doadores_disponiveis, placeholder="Todos")
        if doador_sel:
            df_filtrado = df_filtrado[df_filtrado["Doador"].isin(doador_sel)]

        # Código
        codigos_disponiveis = sorted(df_filtrado["Código"].dropna().unique())
        codigo_sel = col4.multiselect("Código", options=codigos_disponiveis, placeholder="Todos")
        if codigo_sel:
            df_filtrado = df_filtrado[df_filtrado["Código"].isin(codigo_sel)]
        

        # ===== SEGUNDA LINHA =====
        col5, col6= st.columns(2)
        
        # Estado
        estados_unicos = sorted(
            df_filtrado["Estado(s)"].dropna().apply(lambda x: [m.strip() for m in x.split(",")]).explode().unique()
        )
        uf_sel = col5.multiselect("Estado(s)", options=estados_unicos, placeholder="Todos")
        if uf_sel:
            df_filtrado = df_filtrado[
                df_filtrado["Estado(s)"].apply(
                    lambda x: any(m.strip() in uf_sel for m in x.split(",")) if isinstance(x, str) else False
                )
            ]

        # Município
        municipios_unicos = sorted(
            df_filtrado["Município(s)"].dropna().apply(lambda x: [m.strip() for m in x.split(",")]).explode().unique()
        )
        municipio_sel = col6.multiselect("Município", options=municipios_unicos, placeholder="Todos")
        if municipio_sel:
            df_filtrado = df_filtrado[
                df_filtrado["Município(s)"].apply(
                    lambda x: any(m.strip() in municipio_sel for m in x.split(",")) if isinstance(x, str) else False
                )
            ]


        # ===== AVISO =====
        if df_filtrado.empty:
            st.warning("Nenhum projeto encontrado")

geral, lista, mapa = st.tabs(["Visão geral", "Projetos", "Mapa"])

# VISÃO GERAL
with geral:
    
    # Separar projetos PF e PJ
    df_pf = df_filtrado[df_filtrado['Tipo'] == 'PF']
    df_pj = df_filtrado[df_filtrado['Tipo'] == 'PJ']


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
    total_projetos = len(df_filtrado)

    # Total de editais únicos (remover vazios)
    total_editais = df_filtrado["Edital"].replace("", pd.NA).dropna().nunique()

    # Total de doadores únicos (remover vazios)
    total_doador = df_filtrado["Doador"].replace("", pd.NA).dropna().nunique()

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
    
    # Contar CNPJs únicos (organizações apoiadas)
    total_organizacoes = df_pj["CNPJ"].replace("", pd.NA).dropna().nunique()

    col1.metric("Editais", f"{total_editais}")
    col1.metric("Doadores", f"{total_doador}")
    col1.metric("Organizações apoiadas", f"{total_organizacoes}")

    
    col2.metric("Total de apoios", f"{total_projetos}")
    col2.metric("Apoios a Pessoa Jurídica", f"{total_projetos_pj}")
    col2.metric("Apoios a Pessoa Física", f"{total_projetos_pf}")
    

    col3.metric("Estados", f"{total_ufs}")
    col3.metric("Municípios", f"{total_municipios}")

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

    st.write("")
    st.write("")
 
    # Gráfico

    # Garantir campos como string
    df_filtrado["Ano"] = df_filtrado["Ano"].astype(str)
    df_filtrado["Doador"] = df_filtrado["Doador"].astype(str)

    # Agrupamento
    dados = (
        df_filtrado
        .groupby(["Ano", "Doador"])
        .size()
        .reset_index(name="apoios")
    )

    # Garantir que os campos são string
    df_filtrado["Ano"] = df_filtrado["Ano"].astype(str)
    df_filtrado["Doador"] = df_filtrado["Doador"].astype(str)

    # Agrupamento dos apoios existentes
    dados = (
        df_filtrado
        .groupby(["Ano", "Doador"])
        .size()
        .reset_index(name="apoios")
    )

    # Obter intervalo completo de anos
    anos_todos = list(map(str, range(int(df_filtrado["Ano"].min()), int(df_filtrado["Ano"].max()) + 1)))

    # Preencher com 0 onde não há apoio (para doadores já existentes)
    doadores = dados["Doador"].unique()
    todos_anos_doador = pd.MultiIndex.from_product([anos_todos, doadores], names=["Ano", "Doador"])
    dados_completos = dados.set_index(["Ano", "Doador"]).reindex(todos_anos_doador, fill_value=0).reset_index()

    # Paleta com mais cores distintas (exemplo: 'Plotly', 'Viridis', 'Turbo', ou personalizada)
    paleta_cores = px.colors.qualitative.Light24
    
    # Criar gráfico
    fig = px.bar(
        dados_completos,
        x="Ano",
        y="apoios",
        color="Doador",
        color_discrete_sequence=paleta_cores,
        barmode="stack",
        title="Número de apoios por doador e ano",
        labels={"apoios": "Número de apoios", "Ano": ""},
        height=600,
        category_orders={"Ano": anos_todos}  # ordem cronológica
    )

    # Estética
    fig.update_layout(
        xaxis_tickangle=-45,
        xaxis=dict(type='category'),
        legend_font_size=17,
        bargap=0.1,         # espaço entre anos
        bargroupgap=0.05,   # barras mais grossas
        margin=dict(t=60, b=60, l=40, r=10)
    )

    # Mostrar
    st.plotly_chart(fig, use_container_width=True)


with lista:

    

    st.write("")

    # Define o número de itens (linhas) por página
    itens_por_pagina = 50

    # Calcula o total de linhas no DataFrame filtrado
    total_linhas = len(df_filtrado)

    # Calcula o total de páginas, garantindo pelo menos uma
    total_paginas = max(math.ceil(len(df_filtrado) / itens_por_pagina), 1)

    # Cria uma linha com 3 colunas para layout (a última será usada para selecionar a página)
    col1, col2, col3 = st.columns([5, 1, 1])

    # Campo numérico para o usuário selecionar a página atual (na coluna 3)
    pagina_atual = col3.number_input(
        "Página", min_value=1, max_value=total_paginas, value=1, step=1, key="pagina_projetos"
    )

    # Calcula o índice inicial e final da página atual
    inicio = (pagina_atual - 1) * itens_por_pagina
    fim = inicio + itens_por_pagina

    # Fatia o DataFrame para obter apenas os dados da página atual
    df_paginado = df_filtrado.iloc[inicio:fim]

    # Exibe um resumo de quais itens estão sendo mostrados atualmente
    with col1:
        st.write("")
        st.subheader(f"Mostrando {inicio + 1} a {min(fim, total_linhas)} de {total_linhas} projetos")
        st.write("")
        st.write("")

    st.write("")

    # Define as colunas que serão visíveis (remove algumas colunas sensíveis ou irrelevantes)
    colunas_visiveis = [col for col in df_filtrado.columns if col not in ["Tipo", "Município Principal", "CNPJ", "id_doador"]]

    # Define os cabeçalhos das colunas da tabela, adicionando uma coluna "Detalhes" ao final
    headers = colunas_visiveis + ["Detalhes"]

    # Define o tamanho relativo de cada coluna no layout da tabela
    col_sizes = [2, 2, 1, 2, 2, 2, 1, 2, 3, 3]

    # Cria colunas no layout da tabela para os cabeçalhos
    header_cols = st.columns(col_sizes)

    # Escreve os cabeçalhos nas colunas
    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    # Adiciona uma linha divisória visual após os cabeçalhos
    st.divider()

    # Itera sobre cada linha da página atual do DataFrame
    for i, row in df_paginado.iterrows():
        # Cria colunas para a linha atual de dados
        cols = st.columns(col_sizes)

        # Preenche cada coluna com os valores da linha, exceto o botão "Detalhes"
        for j, key in enumerate(colunas_visiveis):
            cols[j].write(row[key])

        # Obtém o índice original da linha no DataFrame
        idx_original = row.name

        # Cria um botão "Detalhes" para a linha atual, que chama a função mostrar_detalhes ao ser clicado
        cols[-1].button(
            "Detalhes",
            key=f"ver_{idx_original}",
            on_click=mostrar_detalhes,
            args=(idx_original,),
            icon=":material/menu:"
        )

        # Adiciona uma linha divisória entre cada item
        st.divider()




with mapa:
    
    
    ######################################################################################################
    # MAPA SOMENTE DOS MUNICÍPIOS PRINCIPAIS 
    ######################################################################################################
    
    
    st.subheader("Mapa de distribuição de projetos")

    pontos_focais_dict = carregar_pontos_focais(todos_projetos)

    # Carregar CSV de municípios
    url_municipios = "https://raw.githubusercontent.com/kelvins/Municipios-Brasileiros/master/csv/municipios.csv"
    df_munis = pd.read_csv(url_municipios)

    # Renomear a coluna e ajustar tipo
    df_munis.rename(columns={'codigo_ibge': 'codigo_municipio'}, inplace=True)
    df_munis['codigo_municipio'] = df_munis['codigo_municipio'].astype(str)

    # Filtra df_projetos_codigos para conter apenas os projetos filtrados atualmente
    df_projetos_codigos_filtrado = df_projetos_codigos[df_projetos_codigos["Código"].isin(df_filtrado["Código"])]
    
    #st.write(df_projetos_codigos)
    # Garantir que os códigos no dataframe de projetos também sejam string
    df_projetos_codigos_filtrado['codigo_municipio'] = df_projetos_codigos_filtrado['Município Principal'].astype(str)
    
    df_projetos_codigos_filtrado['Ano'] = df_projetos_codigos_filtrado['Ano'].astype(str)
    df_projetos_codigos_filtrado["Ano"] = df_projetos_codigos_filtrado["Ano"].str.replace(".0", "", regex=False)
    

    # Cruzamento via código
    df_coords_projetos = df_projetos_codigos_filtrado.merge(
        df_munis,
        left_on='codigo_municipio',
        right_on='codigo_municipio',
        how='left'
    ).dropna(subset=['latitude', 'longitude']).drop_duplicates(subset='Código')


    # Criar o mapa
    m = folium.Map(location=[-15.78, -47.93], zoom_start=4, tiles="CartoDB positron", height="800px")
    cluster = MarkerCluster().add_to(m)

    for _, row in df_coords_projetos.iterrows():
        lat, lon = row['latitude'], row['longitude']
        nome_muni = row['nome'].title()
        codigo = row['Código']
        ano_de_aprovacao = row['Ano']

        projeto = next((p for p in todos_projetos if p.get("codigo") == codigo), None)
        if projeto:
            proponente = projeto.get('proponente', '')
            nome_proj = projeto.get('nome_do_projeto', '')
            ponto_focal_obj = projeto.get("ponto_focal")
            tipo_do_projeto = projeto.get("tipo")
            categoria = projeto.get("categoria")
            nome_ponto_focal = pontos_focais_dict.get(ponto_focal_obj, "Não informado")
            

        popup_html = f"""
            <b>Município:</b> {nome_muni}<br>
            <hr>
            <b>{tipo_do_projeto} - {categoria}</b><br>
            <b>Código:</b> {codigo}<br>
            <b>Proponente:</b> {proponente}<br>
            <b>Projeto:</b> {nome_proj}<br>
            <b>Ano:</b> {ano_de_aprovacao}<br>
            <b>Ponto Focal:</b> {nome_ponto_focal}
        """

        folium.Marker(location=[lat, lon], popup=folium.Popup(popup_html, max_width=300)).add_to(cluster)

    st_folium(m, width=None, height=800, returned_objects=[])