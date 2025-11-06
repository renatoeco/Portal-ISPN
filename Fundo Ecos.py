import streamlit as st
import pandas as pd
import folium
import fiona
import re
import unicodedata
import math
import time
import datetime
import io
from bson import ObjectId
import plotly.express as px
from folium.plugins import MarkerCluster
from plotly.colors import diverging, sequential
from streamlit_folium import st_folium
import geopandas as gpd
from geobr import read_indigenous_land, read_conservation_units, read_biomes               
from funcoes_auxiliares import conectar_mongo_portal_ispn
import streamlit_shadcn_ui as ui



st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

# Logo do Fundo Ecos no topo
container_logo = st.container(horizontal=True, horizontal_alignment="center")
container_logo.image("images/logo_fundo_ecos.png", width=300)

######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()

pj = list(db["projetos_pj"].find())
pf = list(db["projetos_pf"].find())
projetos_ispn = list(db["projetos_ispn"].find())

colecao_doadores = db["doadores"]
ufs_municipios = db["ufs_municipios"]
programas = db["programas_areas"]
pessoas = db["pessoas"]
estatistica = db["estatistica"]  # Coleção de estatísticas
org_beneficiarias = db["organizacoes_beneficiarias"]
pessoas_beneficiarias = db["pessoas_beneficiarias"]
indicadores = db["indicadores"]
colecao_lancamentos = db["lancamentos_indicadores"]




###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


# # Nome da página atual, usado como chave para contagem de acessos
# nome_pagina = "Fundo Ecos"

# # Cria um timestamp formatado com dia/mês/ano hora:minuto:segundo
# timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# # Cria o nome do campo dinamicamente baseado na página
# campo_timestamp = f"{nome_pagina}.Visitas"

# # Atualiza a coleção de estatísticas com o novo acesso, incluindo o timestamp
# estatistica.update_one(
#     {},
#     {"$push": {campo_timestamp: timestamp}},
#     upsert=True  # Cria o documento se ele ainda não existir
# )

######################################################################################################
# CSS PARA DIALOGO MAIOR
######################################################################################################


st.markdown(
    """
<style>
div[data-testid="stDialog"] div[role="dialog"]:has(.big-dialog) {
    width: 75vw;
    
}
</style>
""",
    unsafe_allow_html=True,
)


######################################################################################################
# VARIÁVEIS AUXILIARES
######################################################################################################


# listas de controle
indicadores_float = [
    "Área com manejo ecológico do fogo (ha)",
    "Área com manejo agroecológico (ha)",
    "Área com manejo para restauração (ha)",
    "Área com manejo para extrativismo (ha)",
    "Faturamento bruto anual pré-projeto",
    "Faturamento bruto anual pós-projeto",
    "Volume financeiro de vendas institucionais com apoio do Fundo Ecos",
    "Valor da contrapartida financeira projetinhos",
    "Valor da contrapartida não financeira projetinhos",
    "Valor mobilizado de novos recursos"
]
indicador_texto = "Espécies"

# Lista de nomes legíveis na ordem definida
ordem_indicadores = [
    "Número de organizações apoiadas",
    "Número de comunidades fortalecidas",
    "Número de famílias",
    "Número de homens jovens (até 29 anos)",
    "Número de homens adultos",
    "Número de mulheres jovens (até 29 anos)",
    "Número de mulheres adultas",
    "Número de indígenas",
    "Número de lideranças comunitárias fortalecidas",
    "Número de famílias comercializando produtos da sociobio com apoio do Fundo Ecos",
    "Número de famílias acessando vendas institucionais com apoio do Fundo Ecos",
    "Número de estudantes recebendo bolsa",
    "Número de capacitações realizadas",
    "Número de homens jovens capacitados (até 29 anos)",
    "Número de homens adultos capacitados",
    "Número de mulheres jovens capacitadas (até 29 anos)",
    "Número de mulheres adultas capacitadas",
    "Número de intercâmbios realizados",
    "Número de homens em intercâmbios",
    "Número de mulheres em intercâmbios",
    "Número de iniciativas de Gestão Territorial implantadas",
    "Área com manejo ecológico do fogo (ha)",
    "Área com manejo agroecológico (ha)",
    "Área com manejo para restauração (ha)",
    "Área com manejo para extrativismo (ha)",
    "Número de agroindústrias implementadas/reformadas",
    "Número de tecnologias instaladas",
    "Número de pessoas beneficiadas com tecnologias",
    "Número de vídeos produzidos",
    "Número de aparições na mídia",
    "Número de publicações de caráter técnico",
    "Número de artigos acadêmicos produzidos e publicados",
    "Número de comunicadores comunitários contribuindo na execução das ações do ISPN",
    "Faturamento bruto anual pré-projeto",
    "Faturamento bruto anual pós-projeto",
    "Volume financeiro de vendas institucionais com apoio do Fundo Ecos",
    "Número de visitas de monitoramento realizadas ao projeto apoiado",
    "Valor da contrapartida financeira projetinhos",
    "Valor da contrapartida não financeira projetinhos",
    "Espécies",
    "Número de organizações apoiadas que alavancaram recursos",
    "Valor mobilizado de novos recursos",
    "Número de políticas públicas monitoradas pelo ISPN",
    "Número de proposições legislativas acompanhadas pelo ISPN",
    "Número de contribuições (notas técnicas, participações e/ou documentos) que apoiam a construção e aprimoramento de políticas públicas"
]

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
    "numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_fundo_ecos": "Número de famílias comercializando produtos da sociobio com apoio do Fundo Ecos",
    "numero_de_familias_acessando_vendas_institucionais_com_apoio_do_fundo_ecos": "Número de famílias acessando vendas institucionais com apoio do Fundo Ecos",
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
    "valor_da_contrapartida_financeira_projetinhos": "Valor da contrapartida financeira",
    "valor_da_contrapartida_nao_financeira_projetinhos": "Valor da contrapartida não financeira",
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


######################################################################################################
# FUNÇÕES
######################################################################################################


# Função para converter lista de códigos em lista de nomes
@st.cache_data(ttl=600, show_spinner=False)
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

@st.cache_data(ttl=600, show_spinner=False)
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
def mostrar_detalhes(codigo_proj: str):
    
    st.html("<span class='big-dialog'></span>")

    projeto = projetos_por_codigo.get(codigo_proj, {})

    proj_id = projeto.get("_id")  # ObjectId do projeto
    
    ######################################################################################################
    # Funções de carregamento
    ######################################################################################################


    def carregar_atributos_shp(caminho_shp: str, campos: list = None):
        """
        Lê apenas os atributos (properties) de um shapefile usando fiona,
        ignorando completamente as geometrias.

        Parâmetros:
            caminho_shp (str): Caminho do arquivo .shp
            campos (list, opcional): Lista de colunas específicas a carregar.
                                    Se None, carrega todas as propriedades.

        Retorna:
            pd.DataFrame: DataFrame apenas com atributos.
        """
        with fiona.open(caminho_shp) as src:
            if campos:
                records = [{c: feat["properties"].get(c) for c in campos} for feat in src]
            else:
                records = [feat["properties"] for feat in src]
        return pd.DataFrame(records)

    @st.cache_data(show_spinner="Carregando terras indígenas...")
    def carregar_terras_indigenas(data=201907):
        return read_indigenous_land(date=data, simplified=True)

    @st.cache_data(show_spinner="Carregando unidades de conservação...")
    def carregar_uc(data=201909):
        return read_conservation_units(date=data, simplified=True)

    @st.cache_data(show_spinner="Carregando assentamentos (sem geometria)...")
    def carregar_assentamentos():
        return carregar_atributos_shp("shapefiles/Assentamentos-SAB-INCRA.shp")

    @st.cache_data(show_spinner="Carregando quilombos (sem geometria)...")
    def carregar_quilombos():
        return carregar_atributos_shp("shapefiles/Quilombos-SAB-INCRA.shp")

    @st.cache_data(show_spinner="Carregando bacias hidrográficas (micro, sem geometria)...")
    def carregar_bacias_micro():
        return carregar_atributos_shp("shapefiles/micro_RH.shp")

    @st.cache_data(show_spinner="Carregando bacias hidrográficas (meso, sem geometria)...")
    def carregar_bacias_meso():
        return carregar_atributos_shp("shapefiles/meso_RH.shp")

    @st.cache_data(show_spinner="Carregando bacias hidrográficas (macro, sem geometria)...")
    def carregar_bacias_macro():
        return carregar_atributos_shp("shapefiles/macro_RH.shp")


    ######################################################################
    # CARREGAR DADOS
    ######################################################################


    # --- Carregar dados ---
    dados_ti = carregar_terras_indigenas()
    dados_uc = carregar_uc()
    dados_assentamentos = carregar_assentamentos()
    dados_quilombos = carregar_quilombos()
    dados_bacias_macro = carregar_bacias_macro()
    dados_bacias_meso = carregar_bacias_meso()
    dados_bacias_micro = carregar_bacias_micro()


    # --- Padronizar nomes das colunas das bacias ---
    dados_bacias_macro = dados_bacias_macro.rename(columns={"cd_macroRH": "codigo", "nm_macroRH": "nome"})
    dados_bacias_meso = dados_bacias_meso.rename(columns={"cd_mesoRH": "codigo", "nm_mesoRH": "nome"})
    dados_bacias_micro = dados_bacias_micro.rename(columns={"cd_microRH": "codigo", "nm_microRH": "nome"})

    # Padronizar assentamentos e quilombos (ajuste conforme seus shapefiles)
    if "cd_sipra" in dados_assentamentos.columns:
        dados_assentamentos = dados_assentamentos.rename(columns={"cd_sipra": "codigo", "nome_proje": "nome"})
    if "id" in dados_quilombos.columns:
        dados_quilombos = dados_quilombos.rename(columns={"id": "codigo", "name": "nome"})
        
    # --- Ordenar alfabeticamente pelo nome ---
    dados_ti = dados_ti.sort_values(by="terrai_nom", ascending=True, ignore_index=True) if "terrai_nom" in dados_ti.columns else dados_ti
    dados_uc = dados_uc.sort_values(by="name_conservation_unit", ascending=True, ignore_index=True) if "name_conservation_unit" in dados_uc.columns else dados_uc
    dados_bacias_macro = dados_bacias_macro.sort_values(by="nome", ascending=True, ignore_index=True)
    dados_bacias_meso = dados_bacias_meso.sort_values(by="nome", ascending=True, ignore_index=True)
    dados_bacias_micro = dados_bacias_micro.sort_values(by="nome", ascending=True, ignore_index=True)
    dados_assentamentos = dados_assentamentos.sort_values(by="nome", ascending=True, ignore_index=True)
    dados_quilombos = dados_quilombos.sort_values(by="nome", ascending=True, ignore_index=True)
    
    #  UNIDADES DE CONSERVAÇÃO 

    # Unidades de Conservação
    uc_codigo_para_label = {
        str(row["code_conservation_unit"]): f"{row['name_conservation_unit']} ({row['code_conservation_unit']})"
        for _, row in dados_uc.iterrows()
    }

    # Terras Indígenas
    ti_codigo_para_label = {
        str(row["code_terrai"]): f"{row['terrai_nom']} ({int(row['code_terrai'])})"
        for _, row in dados_ti.iterrows()
    }


    # Assentamentos
    assent_codigo_para_label = {
        str(row["codigo"]): f"{row['nome']} ({row['codigo']})"
        for _, row in dados_assentamentos.iterrows()
    }

    # Quilombos
    quilombo_codigo_para_label = {
        str(row["codigo"]): f"{row['nome']} ({row['codigo']})"
        for _, row in dados_quilombos.iterrows()
    }
    
    # Bacias Hidrográficas
    bacia_micro_codigo_para_label = {
        str(row["codigo"]): f"{row['nome']} ({row['codigo']})" for _, row in dados_bacias_micro.iterrows()
    }
    bacia_meso_codigo_para_label = {
        str(row["codigo"]): f"{row['nome']} ({row['codigo']})" for _, row in dados_bacias_meso.iterrows()
    }
    bacia_macro_codigo_para_label = {
        str(row["codigo"]): f"{row['nome']} ({row['codigo']})" for _, row in dados_bacias_macro.iterrows()
    }

    # Código do projeto
    codigo_projeto = projeto['codigo']

    # Sigla do projeto
    sigla_projeto = projeto['sigla']

    # Título do projeto
    titulo_projeto = st.session_state.get("titulo_projeto", "")
    

    st.subheader(f'{codigo_projeto} - {sigla_projeto}')
    st.write('')

    # Código do projeto
    aba_detalhes, aba_indicadores = st.tabs([":material/assignment: Detalhes", ":material/show_chart: Indicadores"])


    with aba_detalhes:
        st.write(titulo_projeto)

        codigo_proj = str(codigo_proj).strip()
        df_filtrado = st.session_state.get("df_filtrado", pd.DataFrame())
        if df_filtrado.empty:
            st.error("Não há dados filtrados no momento.")
            return

        mask = df_filtrado["Código"].astype(str).str.strip() == codigo_proj
        if not mask.any():
            st.error("Projeto não encontrado nos filtros atuais.")
            return

        projeto_df = df_filtrado.loc[mask].iloc[0]

        

        nome_ponto_focal = "Não informado"
        ponto_focal_obj = projeto.get("ponto_focal")
        if isinstance(ponto_focal_obj, ObjectId):
            pessoa = db["pessoas"].find_one(
                {"_id": ponto_focal_obj},
                {"nome_completo": 1, "_id": 0}  # Projeta apenas o campo necessário → mais rápido
            )
            if pessoa:
                nome_ponto_focal = pessoa.get("nome_completo", "Não encontrado")

        # Corpo do diálogo

        st.write(f"**Situação:** {projeto.get('status', '')}")
        st.write(f"**Proponente:** {projeto.get('proponente', '')}")
        st.write(f"**Nome do projeto:** {projeto.get('nome_do_projeto', '')}")
        st.write(f"**Objetivo geral:** {projeto.get('objetivo_geral', '')}")
        
        col1, col2 = st.columns(2)
        
        col1.write(f"**Tipo:** {projeto.get('tipo', '')}")
        col1.write(f"**Edital:** {projeto_df['Edital']}")
        col1.write(f"**Doador:** {projeto_df['Doador']}")
        col1.write(f"**Valor:** {projeto_df['Valor']}")
        col1.write(f"**Categoria:** {projeto.get('categoria', '')}")
        col1.write(f"**Ano de aprovação:** {projeto_df['Ano']}")
        col1.write(f"**Duração (em meses):** {projeto.get('duracao_original_meses', '')}")
        col1.write(f"**Estado(s):** {converter_uf_codigo_para_nome(projeto.get('ufs', ''))}")
        col1.write(f"**Município principal:** {converter_codigos_para_nomes(projeto.get('municipio_principal', ''))}")
        col1.write(f"**Município(s):** {converter_codigos_para_nomes(projeto.get('municipios', ''))}")
        col1.write(f"**Latitude/Longitude principal:** {projeto.get('lat_long_principal', '')}")
        
        # Regiões de atuação (ignorando estados e municípios)
        regioes_atuacao = projeto.get("regioes_atuacao", [])  # lista de dicionários com tipo e código
        regioes_filtradas = []

        # Dicionário que mapeia tipo → dicionário de códigos para labels
        tipo_para_label = {
            "terra_indigena": ti_codigo_para_label,
            "uc": uc_codigo_para_label,
            "assentamento": assent_codigo_para_label,
            "quilombo": quilombo_codigo_para_label,
            "bacia_macro": bacia_macro_codigo_para_label,
            "bacia_meso": bacia_meso_codigo_para_label,
            "bacia_micro": bacia_micro_codigo_para_label
        }

        for reg in regioes_atuacao:
            tipo = reg.get("tipo", "").lower()
            codigo = str(reg.get("codigo", ""))
            
            # Ignora estados e municípios
            if tipo in ["estado", "municipio", "bioma"] or codigo == "":
                continue
            
            label_dict = tipo_para_label.get(tipo)
            if label_dict:
                nome = label_dict.get(codigo)
                if nome:
                    regioes_filtradas.append(nome)

        if regioes_filtradas:
            col1.write("**Regiões de atuação:**")
            for r in regioes_filtradas:
                col1.write(f"- {r}")
        
        col1.write(f"**Data de início:** {projeto.get('data_inicio_do_contrato', '')}")
        col1.write(f"**Data de fim:** {projeto.get('data_final_do_contrato', '')}")
        col1.write(f"**Ponto Focal:** {nome_ponto_focal}")
        col1.write(f"**Temas:** {projeto.get('temas', '')}")
        col1.write(f"**Público:** {projeto.get('publico', '')}")
        col1.write(f"**Bioma:** {projeto.get('bioma', '')}")

        with col2:

            st.write('**Ponto principal:**')

            lat_long_str = projeto.get('lat_long_principal', '')

            if lat_long_str:
                lat_str, lon_str = lat_long_str.split(",")
                lat, lon = float(lat_str.strip()), float(lon_str.strip())

                # Cria DataFrame
                df = pd.DataFrame({"lat": [lat], "lon": [lon]})

                # Plota o mapa
                st.map(df, zoom=6, use_container_width='stretch')        


    with aba_indicadores:

        
        # Tratamento dos dados

        lancamentos = list(db["lancamentos_indicadores"].find({"projeto": proj_id}))

        linhas = []
        if not lancamentos:
            st.info("Não há lançamentos de indicadores para este projeto.")
        else:
            
            for lan in lancamentos:
                ind_id = lan.get("id_do_indicador")
    
                # Garantir que seja ObjectId para consulta
                if isinstance(ind_id, str):
                    try:
                        ind_id_obj = ObjectId(ind_id)
                    except Exception:
                        ind_id_obj = None
                elif isinstance(ind_id, ObjectId):
                    ind_id_obj = ind_id
                else:
                    ind_id_obj = None

                indicador_nome = str(ind_id)
                
                if ind_id_obj:
                    indicador_doc = db["indicadores"].find_one({"_id": ind_id_obj})
                    if indicador_doc:
                        indicador_nome = (
                            indicador_doc.get("nome_legivel") or 
                            indicador_doc.get("nome_indicador") or 
                            indicador_doc.get("nome") or 
                            str(ind_id)
                        )
                
                # Traduzir via nomes_legiveis se aplicável
                nome_legivel_traduzido = nomes_legiveis.get(indicador_nome, indicador_nome)

                # Converte a data da anotação para str
                data_anotacao = lan.get("data_anotacao", "")
                if isinstance(data_anotacao, str):
                    try:
                        # tenta interpretar no formato ISO (ex: 2025-10-16 ou 2025-10-16T14:30:00)
                        data_anotacao = datetime.datetime.fromisoformat(data_anotacao)
                    except ValueError:
                        try:
                            # tenta no formato brasileiro
                            data_anotacao = datetime.datetime.strptime(data_anotacao, "%d/%m/%Y")
                        except ValueError:
                            data_anotacao = None

                if isinstance(data_anotacao, datetime.datetime) or isinstance(data_anotacao, datetime.date):
                    data_anotacao_str = data_anotacao.strftime("%d/%m/%Y")
                else:
                    data_anotacao_str = ""


                linhas.append({
                    "Indicador": nome_legivel_traduzido,
                    "Valor": lan.get("valor", ""),
                    "Ano": lan.get("ano", ""),
                    "Autor(a)": lan.get("autor_anotacao", ""),
                    "Observações": lan.get("observacoes", ""),
                    "Data anotação": data_anotacao_str,
                })


        # Cria o DataFrame mesmo que linhas esteja vazio
        df_indicadores = pd.DataFrame(linhas, columns=["Indicador", "Valor", "Ano", "Autor(a)", "Data anotação", "Observações"])
        df_indicadores["Valor_num"] = df_indicadores["Valor"].apply(parse_valor)

        # Resumo por indicador
        df_resumo = (
            df_indicadores.groupby("Indicador", as_index=False)["Valor_num"]
            .sum(min_count=1)
            .rename(columns={"Valor_num": "Total"})
        )
        df_resumo["Total"] = df_resumo["Total"].fillna("")

        autor_nome = st.session_state.get("nome", "")
        tipo_usuario = st.session_state.get("tipo_usuario", [])





        # Interface dos indicadores ######################################################################

        st.write('')

        linha_toggles = st.container(horizontal=True, gap="large")


        # ====================
        # Toggle para gerenciar os indicadores
        editar = linha_toggles.toggle(":material/edit: Gerenciar indicadores")

        # st.write('')

        
        # Modo de visualização (padrão)
        if not editar:

            # ====================
            # Toggle para ver consolidado ou todos os lançamentos
            ver_lancamentos = linha_toggles.toggle(":material/visibility: Ver lançamentos detalhados")


            # Mostra os indicadores consolidados ----------------------------
            if not ver_lancamentos:

                st.write('')
                st.write('**INDICADORES CONSOLIDADOS:**')

                ui.table(data=df_resumo)


            # Mostra todos os lançamentos detalhados -------------------------
            else:

                st.write('')
                st.write('**TODOS OS LANÇAMENTOS:**')

                # st.write("**Indicadores consolidados:**")
                st.dataframe(
                    df_indicadores.drop(columns=["Valor_num"], errors="ignore"),
                    hide_index=True,
                    use_container_width='stretch'
                )





            # Carrega indicadores
            indicadores_lista = list(db["indicadores"].find({}, {"_id": 1, "nome_indicador": 1}))
            indicadores_opcoes = {
                nomes_legiveis.get(i["nome_indicador"], i["nome_indicador"]): i
                for i in indicadores_lista
            }

        # Modo de edição
        else:

            st.write('')
            tab_add, tab_edit, tab_delete = st.tabs([
                ":material/add: Adicionar",
                ":material/edit: Editar",
                ":material/delete: Excluir"
            ])

            # ------------------------- ABA ADICIONAR -------------------------
            with tab_add:
                st.subheader("Novo lançamento de indicador")

                indicadores_lista = list(indicadores.find({}, {"_id": 1, "nome_indicador": 1}))
                indicadores_opcoes = {
                    nomes_legiveis.get(i["nome_indicador"], i["nome_indicador"]): i
                    for i in indicadores_lista
                }

                indicador_legivel = st.selectbox(
                    "Indicador",
                    [""] + [i for i in ordem_indicadores if i in indicadores_opcoes]
                )

                if indicador_legivel != "":
                    indicador_doc = indicadores_opcoes[indicador_legivel]
                    indicador_oid = indicador_doc["_id"]

                    with st.form(key="form_add_lancamento"):
                        col1, col2 = st.columns(2)

                        if indicador_legivel == indicador_texto:
                            valor = col1.text_input("Espécies")
                            tipo_valor = "texto"
                        elif indicador_legivel in indicadores_float:
                            valor = col1.number_input("Valor", value=0.00, step=0.01, format="%.2f")
                            tipo_valor = "float"
                        else:
                            valor = col1.number_input("Valor", value=0, step=1, format="%d")
                            tipo_valor = "int"

                        ano_atual = datetime.datetime.now().year
                        anos = ["até 2024"] + [str(ano) for ano in range(2025, ano_atual + 2)]
                        ano = col2.selectbox("Ano", anos)

                        observacoes = st.text_area("Observações", height=100)

                        submit = st.form_submit_button(":material/save: Salvar lançamento")

                    if submit:
                        if not autor_nome:
                            st.warning("Nome do autor não encontrado.")
                            st.stop()

                        if tipo_valor == "float":
                            valor = float(valor)
                        elif tipo_valor == "int":
                            valor = int(valor)

                        # Determinar o tipo do projeto
                        if db["projetos_pj"].find_one({"_id": proj_id}):
                            tipo_projeto = "PJ"
                        elif db["projetos_pf"].find_one({"_id": proj_id}):
                            tipo_projeto = "PF"
                        
                        novo_lancamento = {
                            "id_do_indicador": indicador_oid,
                            "projeto": proj_id,
                            "valor": valor,
                            "ano": str(ano),
                            "observacoes": observacoes,
                            "autor_anotacao": autor_nome,
                            "data_anotacao": datetime.datetime.now(),
                            "tipo": tipo_projeto
                        }

                        colecao_lancamentos.insert_one(novo_lancamento)
                        st.success("Lançamento salvo com sucesso!")
                        time.sleep(2)
                        st.cache_data.clear()
                        st.rerun()

            # ------------------------- ABA EDITAR -------------------------
            with tab_edit:
                st.subheader("Editar lançamento")

                lancamentos_proj = list(
                    colecao_lancamentos.find({"projeto": proj_id}).sort("data_anotacao", -1)
                )

                if "admin" not in tipo_usuario:
                    lancamentos_proj = [l for l in lancamentos_proj if l.get("autor_anotacao") == autor_nome]

                if not lancamentos_proj:
                    st.info("Nenhum lançamento de sua autoria disponível para edição.")
                else:
                    lanc_opcoes = {}
                    for l in lancamentos_proj:
                        data_str = l["data_anotacao"].strftime("%d/%m/%Y %H:%M:%S") if isinstance(l["data_anotacao"], datetime.datetime) else "Sem data"
                        autor = l.get("autor_anotacao", "Sem autor")
                        indicador = indicadores.find_one({"_id": l["id_do_indicador"]})
                        nome_original = indicador["nome_indicador"] if indicador else ""
                        indicador_nome = nomes_legiveis.get(nome_original, nome_original)

                        label = f"{data_str} - {autor} - {indicador_nome}"
                        lanc_opcoes[label] = l["_id"]

                    lanc_sel = st.selectbox("Selecione o lançamento", [""] + list(lanc_opcoes.keys()), key=f"select_lanc_{proj_id}")

                    if lanc_sel != "":
                        lanc_id = lanc_opcoes[lanc_sel]
                        doc = colecao_lancamentos.find_one({"_id": lanc_id})
                        indicador = indicadores.find_one({"_id": doc["id_do_indicador"]})
                        nome_original = indicador["nome_indicador"] if indicador else ""
                        indicador_nome_edit = nomes_legiveis.get(nome_original, nome_original)


                        col1, col2 = st.columns(2)

                        if indicador_nome_edit == indicador_texto:
                            novo_valor = col1.text_input("Espécies", value=str(doc["valor"]))
                            tipo_valor = "texto"
                        elif indicador_nome_edit in indicadores_float:
                            valor_inicial = float(doc["valor"]) if doc["valor"] != "" else 0.00
                            novo_valor = col1.number_input("Valor", value=valor_inicial, step=0.01, format="%.2f")
                            tipo_valor = "float"
                        else:
                            valor_inicial = int(doc["valor"]) if str(doc["valor"]).isdigit() else 0
                            novo_valor = col1.number_input("Valor", value=valor_inicial, step=1, format="%d")
                            tipo_valor = "int"

                        anos = ["até 2024"] + [str(ano) for ano in range(2025, datetime.datetime.now().year + 2)]
                        ano_str = doc.get("ano", "2025")
                        if ano_str not in anos:
                            anos.insert(0, ano_str)
                        novo_ano = col2.selectbox("Ano", anos, index=anos.index(ano_str))

                        novas_obs = st.text_area("Observações", value=doc.get("observacoes", ""))

                        if st.button(":material/save: Salvar alterações"):
                            if tipo_valor == "float":
                                novo_valor = float(novo_valor)
                            elif tipo_valor == "int":
                                novo_valor = int(novo_valor)

                            colecao_lancamentos.update_one(
                                {"_id": lanc_id},
                                {"$set": {"valor": novo_valor, "ano": str(novo_ano), "observacoes": novas_obs}}
                            )
                            st.success("Lançamento atualizado com sucesso!")
                            st.cache_data.clear()
                            st.rerun()

            # ------------------------- ABA EXCLUIR -------------------------
            with tab_delete:
                st.subheader("Excluir lançamento")

                lancamentos_proj = list(
                    colecao_lancamentos.find({"projeto": proj_id}).sort("data_anotacao", -1)
                )

                if "admin" not in tipo_usuario:
                    lancamentos_proj = [l for l in lancamentos_proj if l.get("autor_anotacao") == autor_nome]

                if not lancamentos_proj:
                    st.info("Nenhum lançamento disponível para exclusão.")
                else:
                    lanc_opcoes = {}
                    for l in lancamentos_proj:
                        data_str = l["data_anotacao"].strftime("%d/%m/%Y %H:%M:%S") if isinstance(l["data_anotacao"], datetime.datetime) else "Sem data"
                        autor = l.get("autor_anotacao", "Sem autor")
                        indicador = indicadores.find_one({"_id": l["id_do_indicador"]})
                        nome_original = indicador["nome_indicador"] if indicador else ""
                        indicador_nome = nomes_legiveis.get(nome_original, nome_original)

                        label = f"{data_str} - {autor} - {indicador_nome}"
                        lanc_opcoes[label] = l["_id"]

                    lanc_sel = st.selectbox("Selecione o lançamento", [""] + list(lanc_opcoes.keys()), key=f"select_lanc_2")

                    if lanc_sel != "":
                        lanc_id = lanc_opcoes[lanc_sel]
                        doc = colecao_lancamentos.find_one({"_id": lanc_id})
                        indicador = indicadores.find_one({"_id": doc["id_do_indicador"]})
                        nome_original = indicador["nome_indicador"] if indicador else ""
                        indicador_nome_exluir = nomes_legiveis.get(nome_original, nome_original)

                        valor_lanc = doc.get("valor", "Sem valor")

                        st.warning(
                            f"Tem certeza que deseja excluir o lançamento de **{indicador_nome_exluir}** "
                            f"registrado por {doc['autor_anotacao']} em {doc['data_anotacao'].strftime('%d/%m/%Y')}?\n\n"
                            f"**Valor:** {valor_lanc}"
                        )

                        if st.button("Excluir"):
                            colecao_lancamentos.delete_one({"_id": lanc_id})
                            st.success("Lançamento excluído com sucesso!")
                            st.cache_data.clear()
                            st.rerun()


# Formulário de cadastro e edição de projetos
def form_projeto(projeto, tipo_projeto, pessoas_dict, programas_dict, projetos_ispn_dict):
    form_key = f"form_projeto_{str(projeto.get('_id', 'novo'))}"

    colecao = db["projetos_pf"] if tipo_projeto == "PF" else db["projetos_pj"]

    
    ######################################################################################################
    # Funções de carregamento
    ######################################################################################################


    @st.cache_data(show_spinner="Carregando terras indígenas...")
    def carregar_terras_indigenas(data=201907):
        return read_indigenous_land(date=data, simplified=True)

    @st.cache_data(show_spinner="Carregando unidades de conservação...")
    def carregar_uc(data=201909):
        return read_conservation_units(date=data, simplified=True)

    @st.cache_data(show_spinner="Carregando assentamentos...")
    def carregar_assentamentos():
        return gpd.read_file("shapefiles/Assentamentos-SAB-INCRA.shp")

    @st.cache_data(show_spinner="Carregando quilombos...")
    def carregar_quilombos():
        return gpd.read_file("shapefiles/Quilombos-SAB-INCRA.shp")

    @st.cache_data(show_spinner="Carregando bacias hidrográficas (micro)...")
    def carregar_bacias_micro():
        return gpd.read_file("shapefiles/micro_RH.shp")

    @st.cache_data(show_spinner="Carregando bacias hidrográficas (meso)...")
    def carregar_bacias_meso():
        return gpd.read_file("shapefiles/meso_RH.shp")

    @st.cache_data(show_spinner="Carregando bacias hidrográficas (macro)...")
    def carregar_bacias_macro():
        return gpd.read_file("shapefiles/macro_RH.shp")


    ######################################################################
    # CARREGAR DADOS
    ######################################################################


    # --- Carregar dados ---
    dados_ti = carregar_terras_indigenas()
    dados_uc = carregar_uc()
    dados_assentamentos = carregar_assentamentos()
    dados_quilombos = carregar_quilombos()
    dados_bacias_macro = carregar_bacias_macro()
    dados_bacias_meso = carregar_bacias_meso()
    dados_bacias_micro = carregar_bacias_micro()


    # --- Padronizar nomes das colunas das bacias ---
    dados_bacias_macro = dados_bacias_macro.rename(columns={"cd_macroRH": "codigo", "nm_macroRH": "nome"})
    dados_bacias_meso = dados_bacias_meso.rename(columns={"cd_mesoRH": "codigo", "nm_mesoRH": "nome"})
    dados_bacias_micro = dados_bacias_micro.rename(columns={"cd_microRH": "codigo", "nm_microRH": "nome"})

    # Padronizar assentamentos e quilombos (ajuste conforme seus shapefiles)
    if "cd_sipra" in dados_assentamentos.columns:
        dados_assentamentos = dados_assentamentos.rename(columns={"cd_sipra": "codigo", "nome_proje": "nome"})
    if "id" in dados_quilombos.columns:
        dados_quilombos = dados_quilombos.rename(columns={"id": "codigo", "name": "nome"})
        
    # --- Ordenar alfabeticamente pelo nome ---
    dados_ti = dados_ti.sort_values(by="terrai_nom", ascending=True, ignore_index=True) if "terrai_nom" in dados_ti.columns else dados_ti
    dados_uc = dados_uc.sort_values(by="name_conservation_unit", ascending=True, ignore_index=True) if "name_conservation_unit" in dados_uc.columns else dados_uc
    dados_bacias_macro = dados_bacias_macro.sort_values(by="nome", ascending=True, ignore_index=True)
    dados_bacias_meso = dados_bacias_meso.sort_values(by="nome", ascending=True, ignore_index=True)
    dados_bacias_micro = dados_bacias_micro.sort_values(by="nome", ascending=True, ignore_index=True)
    dados_assentamentos = dados_assentamentos.sort_values(by="nome", ascending=True, ignore_index=True)
    dados_quilombos = dados_quilombos.sort_values(by="nome", ascending=True, ignore_index=True)

    # --- Detecta se é adicionar ou editar ---
    modo = st.session_state.get("modo_formulario", "adicionar")  # valor padrão

    # Obtemos categorias e moedas únicas a partir das duas coleções
    colecoes_projetos = [db["projetos_pf"], db["projetos_pj"]]
    categorias_set = set()
    moedas_set = set()
    for colecao in colecoes_projetos:
        categorias_set.update(filter(None, [p.get("categoria", "").strip() for p in colecao.find()]))
        moedas_set.update(filter(None, [p.get("moeda", "").strip() for p in colecao.find()]))

    opcoes_categoria = sorted(categorias_set)
    opcoes_moeda = sorted(moedas_set)

    # --- Carrega dados do Mongo ---
    doc_ufs = ufs_municipios.find_one({"ufs": {"$exists": True}})
    doc_municipios = ufs_municipios.find_one({"municipios": {"$exists": True}})

    dados_ufs = doc_ufs.get("ufs", []) if doc_ufs else []
    dados_municipios = doc_municipios.get("municipios", []) if doc_municipios else []

    # Mapas para nome <-> código
    ufs_dict = {uf["nome_uf"].strip(): int(uf["codigo_uf"]) for uf in dados_ufs}
    ufs_codigo_para_nome = {int(uf["codigo_uf"]): uf["nome_uf"].strip() for uf in dados_ufs}

    # Criar mapeamento código -> "Município - UF"
    municipios_codigo_para_label = {
        int(m["codigo_municipio"]): f'{m["nome_municipio"].strip()} - {codigo_uf_para_sigla[str(m["codigo_municipio"])[:2]]}'
        for m in dados_municipios
    }

    # Converte ufs do projeto, que estão salvos como string separada por vírgula, para lista de códigos (int)
    ufs_codigos = []
    ufs_str = projeto.get("ufs", "")
    if isinstance(ufs_str, str):
        ufs_codigos = [int(c.strip()) for c in ufs_str.split(",") if c.strip()]

    ufs_valor_nome = [ufs_codigo_para_nome.get(c) for c in ufs_codigos if c in ufs_codigo_para_nome]

    # municipio_principal do projeto (string), converte para int para buscar label
    municipio_principal_codigo = projeto.get("municipio_principal", None)
    if municipio_principal_codigo is not None:
        try:
            municipio_principal_codigo = int(municipio_principal_codigo)
        except:
            municipio_principal_codigo = None

    # municipios de atuação (string separada por vírgula)
    municipios_codigos = []
    municipios_str = projeto.get("municipios", "")
    if isinstance(municipios_str, str):
        municipios_codigos = [int(c.strip()) for c in municipios_str.split(",") if c.strip()]

    with st.form(key=f"formulario_{form_key}", border=False):

        # Linha 0 - Status
        col1, col2, col3 = st.columns([1,1,3])


        # Campos comuns
        opcoes_status = ["Em andamento", "Finalizado", "Cancelado"]
        status_valor = projeto.get("status", opcoes_status[0])

        status = col1.selectbox(
            "Status*", 
            options=opcoes_status, 
            index=opcoes_status.index(status_valor) if status_valor in opcoes_status else 0,
            key=f"status_{str(projeto.get('_id', 'novo'))}"
        )



        # Linha 1 - Código, Sigla e Proponente /////////////////////////////
        col1, col2, col3 = st.columns([1,1,3])

        # Campos comuns
        codigo = col1.text_input("Código*", projeto.get("codigo", ""))
        sigla = col2.text_input("Sigla*", projeto.get("sigla", ""))
        
        # Buscar proponentes do banco
        if tipo_projeto == "PF":
            proponentes_cursor = pessoas_beneficiarias.find()
            proponentes_dict = {
                str(p["_id"]): {
                    "nome": p.get("proponente", ""),
                    "cpf": p.get("cpf", ""),
                    "genero": p.get("genero", "")
                }
                for p in proponentes_cursor
            }
        else:
            proponentes_cursor = org_beneficiarias.find()
            proponentes_dict = {
                str(p["_id"]): {
                    "nome": p.get("proponente", ""),
                    "cnpj": p.get("cnpj", "")
                }
                for p in proponentes_cursor
            }

        # --- Garantir que o proponente salvo no projeto apareça na lista ---
        proponente_salvo = projeto.get("proponente", "")
        if proponente_salvo and not any(v["nome"] == proponente_salvo for v in proponentes_dict.values()):
            # cria uma opção fake para mostrar o proponente atual mesmo que não esteja em pessoas/org_beneficiarias
            proponentes_dict["proponente_atual"] = {"nome": proponente_salvo}

        # --- Montar opções (inclui "" e "Cadastrar proponente") ---
        proponentes_options = {"": ""}
        proponentes_options.update({
            k: v["nome"] for k, v in sorted(proponentes_dict.items(), key=lambda item: item[1]["nome"].lower())
        })

        # Seleção (default = proponente atual do projeto)
        default_key = next((k for k, v in proponentes_options.items() if v == proponente_salvo), "")

        proponente_selecionado = col3.selectbox(
            "Proponente*",
            options=list(proponentes_options.keys()),
            format_func=lambda k: proponentes_options[k],
            index=list(proponentes_options.keys()).index(default_key) if default_key in proponentes_options else 0,
            key=f"select_proponente_{tipo_projeto}_{projeto.get('_id', '')}"
        )

        
        # Preencher automaticamente os campos ligados ao proponente
        if proponente_selecionado and proponente_selecionado in proponentes_dict:
            dados_proponente = proponentes_dict[proponente_selecionado]
            if tipo_projeto == "PF":
                cpf = dados_proponente.get("cpf", "")
                genero = dados_proponente.get("genero", "")
                cnpj = ""
            else:
                cnpj = dados_proponente.get("cnpj", "")
                cpf = ""
                genero = ""
        else:
            cpf, genero, cnpj = "", "", ""


        # Linha 2 - Nome do projeto, categoria, edital e ano de aprovação //////////////////////////////////////////////
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        nome_do_projeto = col1.text_input("Nome do projeto*", projeto.get("nome_do_projeto", ""))

        categoria_valor = projeto.get("categoria", "")
        categoria = col2.selectbox(
            "Categoria*",
            options=opcoes_categoria,
            index=opcoes_categoria.index(categoria_valor) if categoria_valor in opcoes_categoria else 0,
            placeholder="",
            key=f"categoria_{form_key}"
        )

        # Edital como text_input
        edital = col3.text_input("Edital", projeto.get("edital", ""), key=f"edital_{form_key}")
        
        ano_aprovacao = col4.number_input("Ano de aprovação*", value=projeto.get("ano_de_aprovacao", 2025), step=1, key=f"ano_aprovacao_{form_key}")


        # Linha 2.1 - Objetivo geral //////////////////////////////////////////////////////////////////////////////////
        objetivo_geral = st.text_area(
            "Objetivo geral*",
            projeto.get("objetivo_geral", ""),
            key=f"objetivo_geral_{projeto.get('_id', 'novo')}"
        )

        st.divider()


        ######################################################################
        # REGIÕES DE ATUAÇÃO
        ######################################################################


        # Linha 3 - UFs, município principal e municípios de atuação //////////////////////////////////////////////
        col1, col2, col3 = st.columns(3)

        # --- Seleção de estados (não afeta municípios) ---
        ufs_selecionados = col1.multiselect(
            "Estado(s)*",
            options=sorted(ufs_dict.keys()),
            default=ufs_valor_nome,
            key=f"ufs_{form_key}",
            placeholder=""
        )

        # --- Município principal (todos os municípios) ---
        municipio_principal = col2.selectbox(
            "Município principal*",
            options=sorted(municipios_codigo_para_label.keys()),
            format_func=lambda codigo: municipios_codigo_para_label.get(codigo, ""),
            index=sorted(municipios_codigo_para_label.keys()).index(municipio_principal_codigo)
                if municipio_principal_codigo in municipios_codigo_para_label else 0,
            key=f"municipio_principal_{form_key}", 
            placeholder=""
        )

        # --- Municípios de atuação (todos os municípios) ---
        municipios_atuacao = col3.multiselect(
            "Municípios de atuação*",
            options=sorted(municipios_codigo_para_label.keys()),
            format_func=lambda codigo: municipios_codigo_para_label.get(codigo, ""),
            default=municipios_codigos,
            key=f"municipios_{form_key}",
            placeholder=""
        )


        # Linha 4 - Latitude e longitude, observações sobre o local //////////////////////////////////////////////
        col1, col2 = st.columns([1, 2])

        # --- Latitude e longitude ---

        latlong = col1.text_input(
            "Latitude, Longitude",
            value=projeto.get("lat_long_principal", ""),   # 🔹 usa o valor salvo no projeto
            # placeholder="-23.175173, -45.856398",
            key=f"latlong_{form_key}",
            help="Você pode usar o Google Maps para obter as coordenadas nesse formato '-23.175173, -45.856398'"
        )


        #  UNIDADES DE CONSERVAÇÃO 

        # Unidades de Conservação
        uc_codigo_para_label = {
            str(row["code_conservation_unit"]): f"{row['name_conservation_unit']} ({row['code_conservation_unit']})"
            for _, row in dados_uc.iterrows()
        }

        # Terras Indígenas
        ti_codigo_para_label = {
            str(row["code_terrai"]): f"{row['terrai_nom']} ({int(row['code_terrai'])})"
            for _, row in dados_ti.iterrows()
        }


        # Assentamentos
        assent_codigo_para_label = {
            str(row["codigo"]): f"{row['nome']} ({row['codigo']})"
            for _, row in dados_assentamentos.iterrows()
        }

        # Quilombos
        quilombo_codigo_para_label = {
            str(row["codigo"]): f"{row['nome']} ({row['codigo']})"
            for _, row in dados_quilombos.iterrows()
        }
        
        # Bacias Hidrográficas
        bacia_micro_codigo_para_label = {
            str(row["codigo"]): f"{row['nome']} ({row['codigo']})" for _, row in dados_bacias_micro.iterrows()
        }
        bacia_meso_codigo_para_label = {
            str(row["codigo"]): f"{row['nome']} ({row['codigo']})" for _, row in dados_bacias_meso.iterrows()
        }
        bacia_macro_codigo_para_label = {
            str(row["codigo"]): f"{row['nome']} ({row['codigo']})" for _, row in dados_bacias_macro.iterrows()
        }
        
        # Listas de códigos já selecionados no projeto
        regioes = projeto.get("regioes_atuacao", [])

        ti_default = [r["codigo"] for r in regioes if r["tipo"] == "terra_indigena"]
        uc_default = [r["codigo"] for r in regioes if r["tipo"] == "uc"]
        assent_default = [r["codigo"] for r in regioes if r["tipo"] == "assentamento"]
        quilombo_default = [r["codigo"] for r in regioes if r["tipo"] == "quilombo"]
        bacia_micro_default = [r["codigo"] for r in regioes if r["tipo"] == "bacia_micro"]
        bacia_meso_default = [r["codigo"] for r in regioes if r["tipo"] == "bacia_meso"]
        bacia_macro_default = [r["codigo"] for r in regioes if r["tipo"] == "bacia_macro"]

        ucs_selecionadas = col2.multiselect(
            "Unidades de Conservação",
            options=list(uc_codigo_para_label.values()),
            default=[uc_codigo_para_label[c] for c in uc_default if c in uc_codigo_para_label],
            placeholder=""
        )



        # ----------------------- TERRAS INDÍGENAS -----------------------
       
        col1, col2, col3 = st.columns(3)
       
        tis_selecionadas = col1.multiselect(
            "Terras Indígenas",
            options=list(ti_codigo_para_label.values()),
            default=[ti_codigo_para_label[c] for c in ti_default if c in ti_codigo_para_label],
            placeholder=""
        )

        # ----------------------- ASSENTAMENTOS -----------------------
        
        assentamentos_selecionados = col2.multiselect(
            "Assentamentos",
            options=list(assent_codigo_para_label.values()),
            default=[assent_codigo_para_label[c] for c in assent_default if c in assent_codigo_para_label],
            placeholder=""
        )

        # ----------------------- QUILOMBOS -----------------------
        quilombos_selecionados = col3.multiselect(
            "Quilombos",
            options=list(quilombo_codigo_para_label.values()),
            default=[quilombo_codigo_para_label[c] for c in quilombo_default if c in quilombo_codigo_para_label],
            placeholder=""
        )


        # ----------------------- BACIAS HIDROGRÁFICAS -----------------------
        col1, col2, col3 = st.columns(3)
        
        bacias_macro_sel = col1.multiselect(
            "Bacias Hidrográficas - Macro",
            options=list(bacia_macro_codigo_para_label.values()),
            default=[bacia_macro_codigo_para_label[c] for c in bacia_macro_default if c in bacia_macro_codigo_para_label],
            placeholder=""
        )
        

        bacias_meso_sel = col2.multiselect(
            "Bacias Hidrográficas - Meso",
            options=list(bacia_meso_codigo_para_label.values()),
            default=[bacia_meso_codigo_para_label[c] for c in bacia_meso_default if c in bacia_meso_codigo_para_label],
            placeholder=""
        )
        
        bacias_micro_sel = col3.multiselect(
            "Bacias Hidrográficas - Micro",
            options=list(bacia_micro_codigo_para_label.values()),
            default=[bacia_micro_codigo_para_label[c] for c in bacia_micro_default if c in bacia_micro_codigo_para_label],
            placeholder=""
        )
        
        
        # --- Observações sobre o local ---

        local_obs = st.text_area(
            "Observações sobre o local",
            projeto.get("observacoes_sobre_o_local", ""),
            key=f"obs_local_{form_key}",
            placeholder="Anote o nome do local se for alguma localização especial, como Terra Indígena, Assentamento, Unidade de Conservação, área urbana, etc."
        )
        
        st.divider()

        if modo == "editar":

            # Linha 5 - Duração, data início e data fim //////////////////////////////////////////////
            # --- Duração em meses ---
            col1, col2, col3, col4 = st.columns(4)
            duracao_val = col1.number_input(
                "Duração (em meses)*",
                value=int(projeto.get("duracao_original_meses", 0) or 0),
                step=1,
                
            )
            duracao = str(duracao_val)

            # Data início
            data_inicio_date = col2.date_input(
                "Data início do contrato*",

                value = datetime.datetime.strptime(projeto.get("data_inicio_do_contrato", ""), "%d/%m/%Y").date()
                if projeto.get("data_inicio_do_contrato") else None,
                format="DD/MM/YYYY"
            )
            data_inicio = data_inicio_date.strftime("%d/%m/%Y") if data_inicio_date else ""

            # Data fim
            data_fim_date = col3.date_input(
                "Data fim do contrato*",
                value=datetime.datetime.strptime(projeto.get("data_final_do_contrato", ""), "%d/%m/%Y").date()
                if projeto.get("data_final_do_contrato") else None,
                format="DD/MM/YYYY"
            )
            data_fim = data_fim_date.strftime("%d/%m/%Y") if data_fim_date else ""

            # Data relatório
            data_relatorio_date = col4.date_input(
                "Data relatório final",
                value=datetime.datetime.strptime(projeto.get("data_relatorio_monitoramento_final", ""), "%d/%m/%Y").date()
                if projeto.get("data_relatorio_monitoramento_final") else None,
                format="DD/MM/YYYY"
            )
            data_relatorio = data_relatorio_date.strftime("%d/%m/%Y") if data_relatorio_date else ""

        # Modo adicionar
        else:
            col1, col2, col3 = st.columns(3)
            duracao_val = col1.number_input(
                "Duração (em meses)*",
                value=int(projeto.get("duracao_original_meses", 0) or 0),
                step=1,
                
            )
            duracao = str(duracao_val)

            # Data início
            data_inicio_date = col2.date_input(
                "Data início do contrato*",
                value=datetime.datetime.strptime(projeto.get("data_inicio_do_contrato", ""), "%d/%m/%Y").date()
                if projeto.get("data_inicio_do_contrato") else None,
                format="DD/MM/YYYY"
            )
            data_inicio = data_inicio_date.strftime("%d/%m/%Y") if data_inicio_date else ""

            # Data fim
            data_fim_date = col3.date_input(
                "Data fim do contrato*",
                value=datetime.datetime.strptime(projeto.get("data_final_do_contrato", ""), "%d/%m/%Y").date()
                if projeto.get("data_final_do_contrato") else None,
                format="DD/MM/YYYY"
            )
            data_fim = data_fim_date.strftime("%d/%m/%Y") if data_fim_date else ""
            
            data_relatorio = ""

        # Linha 6 - Moeda e valor //////////////////////////////////////////////////
        col1, col2, col3 = st.columns([1,2,6])
        moeda_valor = projeto.get("moeda", "")
        moeda = col1.selectbox(
            "Moeda*",
            options=opcoes_moeda,
            index=opcoes_moeda.index(moeda_valor) if moeda_valor in opcoes_moeda else 0,
            placeholder="",
            key=f"moeda_{form_key}"
        )

        # --- Valor ---
        # pega valor do projeto
        valor_raw = projeto.get("valor", 0) or 0

        # se vier como string no padrão brasileiro → converte para float
        if isinstance(valor_raw, str):
            try:
                valor_raw = float(valor_raw.replace(".", "").replace(",", "."))
            except ValueError:
                valor_raw = 0.0  # fallback seguro caso venha algo inválido
        else:
            valor_raw = float(valor_raw)

        # agora usa no number_input
        valor_val = col2.number_input(
            "Valor*",
            value=valor_raw,
            step=1.0,
            format="%.2f"   # exibe com 2 casas decimais
        )


        valor = f"{valor_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


        # Linha 7 - Temas, público e bioma //////////////////////////////////////////////////
        col1, col2, col3 = st.columns(3)
        opcoes_temas = [
            "Agroecologia", "Agroextrativismo - Beneficiamento e Comercialização", "Água", "Apicultura e meliponicultura",
            "Artesanato", "Articulação", "Capacitação", "Certificação", "Conservação da biodiversidade", "Criação de animais", "Cultura",
            "Educação Ambiental", "Energia Renovável", "Fauna", "Fogo", "Gestão Territorial", "Manejo da biodiversidade", "Pesquisa", 
            "Plantas medicinais", "Política Pública", "Recuperação de áreas degradadas", "Sistemas Agroflorestais - SAFs", "Turismo", "Outro"
        ]
        opcoes_publico = ["Agricultores Familiares", "Assentados da Reforma Agrária", "Comunidade Tradicional", "Garimpeiros", 
                            "Idosos", "Indígenas", "Jovens", "Mulheres", "Pescador Artesanal", "Quilombola", "Urbano", "Outro" ]
        opcoes_bioma = ["Amazônia", "Caatinga", "Cerrado", "Mata Atlântica", "Pampas", "Pantanal"]
        # opcoes_status = ["Em andamento", "Finalizado", "Cancelado"]

        temas_valor = [
            p.strip()
            for p in projeto.get("temas", "").split(",")
            if p.strip() in opcoes_temas
        ]

        publico_valor = [p.strip() for p in projeto.get("publico", "").split(",") if p.strip()]
        bioma_valor = [b.strip() for b in projeto.get("bioma", "").split(",") if b.strip()]
        # status_valor = projeto.get("status", opcoes_status[0])

        temas = col1.multiselect("Temas*", options=opcoes_temas, default=temas_valor, placeholder="", key=f"temas_{str(projeto.get('_id', 'novo'))}")
        publico = col2.multiselect("Público*", options=opcoes_publico, default=publico_valor, placeholder="", key=f"publico_{str(projeto.get('_id', 'novo'))}")
        bioma = col3.multiselect("Bioma*", options=opcoes_bioma, default=bioma_valor, placeholder="", key=f"bioma_{str(projeto.get('_id', 'novo'))}")

        # Linha 8 - Ponto focal e programas //////////////////////////////////////////////////
        col1, col2, col3 = st.columns(3)
        pessoas_options = {str(k): v for k, v in sorted(pessoas_dict.items(), key=lambda item: item[1].lower())}
        ponto_focal_default = str(projeto.get("ponto_focal", ""))
        ponto_focal_keys = list(pessoas_options.keys())

        # insere opção vazia na primeira posição
        opcoes_ponto_focal = [""] + ponto_focal_keys

        # calcula índice ajustado
        if ponto_focal_default in ponto_focal_keys:
            index_ajustado = ponto_focal_keys.index(ponto_focal_default) + 1  # +1 pela opção vazia
        else:
            index_ajustado = 0  # opção vazia selecionada por padrão

        ponto_focal = col1.selectbox(
            "Ponto focal*",
            options=opcoes_ponto_focal,
            format_func=lambda x: pessoas_options.get(x, "") if x else "",  # mostra vazio para a opção ""
            index=index_ajustado,
            placeholder="Selecione..."
        )

        programas_excluidos = {"ADM Brasília", "ADM Santa Inês", "Comunicação", "Advocacy", "Coordenação"}
        programas_filtrados = {
            str(k): v for k, v in programas_dict.items()
            if v not in programas_excluidos and v.strip()
        }
        programas_options = {
            str(k): v for k, v in sorted(programas_filtrados.items(), key=lambda item: item[1].lower())
        }
        programa_default = str(projeto.get("programa", ""))
        programa_keys = list(programas_options.keys())

        # insere opção vazia na primeira posição
        opcoes_programa = [""] + programa_keys

        # calcula índice ajustado
        if programa_default in programa_keys:
            index_ajustado = programa_keys.index(programa_default) + 1  # +1 pela opção vazia
        else:
            index_ajustado = 0  # opção vazia selecionada por padrão

        programa = col2.selectbox(
            "Programa*",
            options=opcoes_programa,
            format_func=lambda x: programas_options.get(x, "") if x else "",  # mostra vazio para a opção ""
            index=index_ajustado,
            placeholder="Selecione..."
        )

        projetos_pai_options = {
            str(k): v for k, v in projetos_ispn_dict.items() if v.strip()
        }
        sorted_keys = sorted(projetos_pai_options, key=lambda x: projetos_pai_options[x].lower())
        codigo_pai_default = str(projeto.get("codigo_projeto_pai", ""))

        # insere opção vazia na primeira posição
        opcoes_projeto_pai = [""] + sorted_keys

        # calcula índice ajustado
        if codigo_pai_default in sorted_keys:
            index_ajustado = sorted_keys.index(codigo_pai_default) + 1  # +1 porque adicionamos a opção vazia
        else:
            index_ajustado = 0  # opção vazia selecionada por padrão

        codigo_pai = col3.selectbox(
            "Projeto financiador*",
            options=opcoes_projeto_pai,
            format_func=lambda x: projetos_pai_options.get(x, "Desconhecido") if x else "",
            index=index_ajustado,
            placeholder="Selecione..."
        )

        st.write("")

        # -------------------------
        # Botão de salvar
        # -------------------------
        salvar = st.form_submit_button("Salvar", icon=":material/save:")

        if salvar:
            # --- Campos obrigatórios ---
            campos_obrigatorios = [
                codigo, sigla, nome_do_projeto, proponente_selecionado, categoria, ano_aprovacao, 
                ponto_focal, programa, objetivo_geral, duracao, data_inicio, data_fim, 
                moeda, valor, bioma, status, temas, publico, codigo_pai, ufs_selecionados, 
                municipio_principal, municipios_atuacao
            ]

            if not all(campos_obrigatorios):
                st.warning("Preencha todos os campos obrigatórios (*) antes de salvar.")
                return None

            # --- Verificar duplicidade ---
            filtro_codigo = {"codigo": codigo} if codigo else None
            filtro_sigla = {"sigla": sigla} if sigla else None

            if modo == "editar" and projeto.get("_id"):
                try:
                    proj_id = ObjectId(projeto["_id"]) if isinstance(projeto["_id"], str) else projeto["_id"]
                except:
                    proj_id = projeto["_id"]

                if codigo:
                    filtro_codigo = {"$and": [{"_id": {"$ne": proj_id}}, {"codigo": codigo}]}
                if sigla:
                    filtro_sigla = {"$and": [{"_id": {"$ne": proj_id}}, {"sigla": sigla}]}
        
            # Checa duplicidade em PF e PJ
            codigo_existente, sigla_existente = None, None
            for col in [db["projetos_pf"], db["projetos_pj"]]:
                if filtro_codigo and not codigo_existente:
                    codigo_existente = col.find_one(filtro_codigo)
                if filtro_sigla and not sigla_existente:
                    sigla_existente = col.find_one(filtro_sigla)

            # --- Validação de latitude/longitude ---
            padrao = r"^-?\d{1,3}\.\d{1,20},\s*-?\d{1,3}\.\d{1,20}$"
            if latlong and not re.match(padrao, latlong):
                st.error("Formato de coordenadas inválido! Use o padrão: -23.175173, -45.856398")
                return None  

            # --- Mensagens de duplicidade ---
            if codigo_existente and sigla_existente:
                st.warning(f"Já existe um projeto com o código '{codigo}' e com a sigla '{sigla}'.")
                return None
            elif codigo_existente:
                st.warning(f"Já existe um projeto com o código '{codigo}'.")
                return None
            elif sigla_existente:
                st.warning(f"Já existe um projeto com a sigla '{sigla}'.")
                return None
            
            # ---------- Montagem da lista final ----------
            def extrair_codigos(lista):
                codigos = []
                for item in lista:
                    try:
                        codigo_regioes = item.split("(")[-1].replace(")", "").strip()
                        codigos.append(codigo_regioes)
                    except Exception:
                        pass
                return codigos

            regioes_atuacao = []

            # --- Adiciona UFs selecionadas como regiões de atuação ---
            for uf_nome in ufs_selecionados:
                if uf_nome in ufs_dict:
                    regioes_atuacao.append({"tipo": "estado", "codigo": str(ufs_dict[uf_nome])})

            # --- Adiciona municípios de atuação como regiões de atuação ---
            for codigo_muni in municipios_atuacao:
                regioes_atuacao.append({"tipo": "municipio", "codigo": str(codigo_muni)})
                
            # ----------------------- BIOMAS -----------------------
            biomas_dict = {
                "Amazônia": 1,
                "Caatinga": 2,
                "Cerrado": 3,
                "Mata Atlântica": 4,
                "Pampas": 5,
                "Pantanal": 6
            }
                
            # --- Adiciona biomas selecionados como regiões de atuação ---
            for bioma_nome in bioma:  
                codigo_bioma = biomas_dict.get(bioma_nome)
                if codigo_bioma is not None:
                    regioes_atuacao.append({"tipo": "bioma", "codigo": str(codigo_bioma)})

            # --- Agora adiciona os demais tipos (TI, UC, bioma, assentamentos, etc.) ---
            for tipo, selecionados in [
                ("terra_indigena", tis_selecionadas),
                ("uc", ucs_selecionadas),
                ("assentamento", assentamentos_selecionados),
                ("quilombo", quilombos_selecionados),
                ("bacia_micro", bacias_micro_sel),
                ("bacia_meso", bacias_meso_sel),
                ("bacia_macro", bacias_macro_sel),
            ]:
                for codigo_regioes in extrair_codigos(selecionados):
                    regioes_atuacao.append({"tipo": tipo, "codigo": codigo_regioes})

            # --- Se passou em todas as verificações ---
            doc = {
                "codigo": codigo,
                "sigla": sigla,
                "proponente": proponentes_dict.get(proponente_selecionado, {}).get("nome", ""),
                "nome_do_projeto": nome_do_projeto,
                "edital": edital,
                "categoria": categoria,
                "ano_de_aprovacao": ano_aprovacao,
                "lat_long_principal": latlong,
                "observacoes_sobre_o_local": local_obs,
                "duracao_original_meses": duracao,
                "data_inicio_do_contrato": data_inicio,
                "data_final_do_contrato": data_fim,
                "data_relatorio_monitoramento_final": data_relatorio,
                "moeda": moeda,
                "valor": valor,
                "bioma": ", ".join(bioma) if isinstance(bioma, list) else str(bioma),
                "status": status,
                "temas": ", ".join(temas) if isinstance(temas, list) else str(temas),
                "publico": ", ".join(publico) if isinstance(publico, list) else str(publico),
                "objetivo_geral": objetivo_geral,
                "tipo": tipo_projeto,
                "ponto_focal": ObjectId(ponto_focal) if ponto_focal and ObjectId.is_valid(ponto_focal) else None,
                "programa": ObjectId(programa) if programa and ObjectId.is_valid(programa) else None,
                "codigo_projeto_pai": ObjectId(codigo_pai) if codigo_pai and ObjectId.is_valid(codigo_pai) else None,
                "ufs": ",".join(str(ufs_dict[nome]) for nome in ufs_selecionados if nome in ufs_dict),
                "municipio_principal": str(municipio_principal) if municipio_principal is not None else "",
                "municipios": ",".join(str(codigo) for codigo in municipios_atuacao),
                "regioes_atuacao": regioes_atuacao,
            }
            if tipo_projeto == "PF":
                doc["cpf"] = proponentes_dict.get(proponente_selecionado, {}).get("cpf", "")
                doc["genero"] = proponentes_dict.get(proponente_selecionado, {}).get("genero", "")
            else:
                doc["cnpj"] = proponentes_dict.get(proponente_selecionado, {}).get("cnpj", "")
                
    
            return doc
    

@st.dialog("Cadastrar proponente", width="large")
def cadastrar_proponente():
    
    #--- Cadastro de novo proponente ---
    tipo_cadastro = st.pills(
        "Selecione o tipo",
        ["Organização", "Pessoa"],
        selection_mode="single",
        default="Organização",
        key=f"tipo_cadastro_proponente_{projeto.get('_id', '')}"
    )

    if tipo_cadastro == "Organização":
        with st.form(f"Cadastro_organizacao_{projeto.get('_id', '')}", border=False):
            nome = st.text_input("Nome da organização", key=f"nome_org_{projeto.get('_id', '')}")
            cnpj = st.text_input("CNPJ", placeholder="00.000.000/0000-00", key=f"cnpj_org_{projeto.get('_id', '')}")
            st.write("")
            cadastrar = st.form_submit_button("Cadastrar organização")

            if cadastrar:
                if not nome.strip() or not cnpj.strip():
                    st.error("Todos os campos são obrigatórios.")
                else:
                    existente = org_beneficiarias.find_one({"cnpj": cnpj.strip()})
                    if existente:
                        st.error("Já existe uma organização cadastrada com esse CNPJ.")
                    else:
                        org_beneficiarias.insert_one({"proponente": nome.strip(), "cnpj": cnpj.strip()})
                        st.success("Organização cadastrada com sucesso!")
                        time.sleep(2)
                        st.rerun()

    elif tipo_cadastro == "Pessoa":
        with st.form(f"Cadastro_pessoa_{projeto.get('_id', '')}", border=False):
            nome = st.text_input("Nome completo", key=f"nome_pessoa_{projeto.get('_id', '')}")
            cpf = st.text_input("CPF", placeholder="000.000.000-00", key=f"cpf_pessoa_{projeto.get('_id', '')}")
            genero = st.selectbox(
                "Gênero",
                ["Masculino", "Feminino", "Não binário", "Outro"],
                key=f"tipo_genero_{projeto.get('_id', '')}"
            )

            st.write("")
            cadastrar = st.form_submit_button("Cadastrar pessoa")

            if cadastrar:
                if not nome.strip() or not cpf.strip():
                    st.error("Todos os campos são obrigatórios.")
                else:
                    existente = pessoas_beneficiarias.find_one({"cpf": cpf.strip()})
                    if existente:
                        st.error("Já existe uma pessoa cadastrada com esse CPF.")
                    else:
                        pessoas_beneficiarias.insert_one(
                            {"proponente": nome.strip(), "cpf": cpf.strip(), "genero": genero.strip()}
                        )
                        st.success("Pessoa cadastrada com sucesso!")
                        time.sleep(2)
                        st.rerun()


@st.dialog("Gerenciar projetos", width="large")
def gerenciar_projetos():

    st.html("<span class='big-dialog'></span>")

    abas = st.tabs(["Adicionar", "Editar", "Excluir"])

    pessoas_dict = {p["_id"]: p.get("nome_completo", "") for p in pessoas.find()}
    programas_dict = {p["_id"]: p.get("nome_programa_area", "") for p in db["programas_areas"].find()}
    projetos_ispn_dict = {p["_id"]: p.get("codigo", "") for p in db["projetos_ispn"].find()}

    # --- Adicionar ---
    with abas[0]:
        st.session_state["modo_formulario"] = "adicionar"
        tipo_projeto = st.pills("Tipo de projeto", ["PF", "PJ"], selection_mode="single", default="PJ")
        colecao = db["projetos_pf"] if tipo_projeto == "PF" else db["projetos_pj"]
        novo = form_projeto({}, tipo_projeto, pessoas_dict, programas_dict, projetos_ispn_dict)
        if novo:
            colecao.insert_one(novo)
            st.success("Projeto adicionado com sucesso.")
            time.sleep(1)
            st.rerun()

    # --- Editar ---
    with abas[1]:
        st.session_state["modo_formulario"] = "editar"
        todos_projetos = [(p, "PF") for p in pf] + [(p, "PJ") for p in pj]

        # formarta as opções com Código e Sigla
        opcoes = {
            str(proj["_id"]): f"{proj.get('codigo', '')} ({proj.get('sigla', '')})"
            for proj, tipo in todos_projetos
        }



        if not opcoes:
            st.info("Nenhum projeto encontrado para editar.")
        else:
            # insere a opção vazia na frente
            chaves = [""] + list(opcoes.keys())

            selecionado_id = st.selectbox(
                "Selecione o projeto",
                chaves,
                format_func=lambda x: opcoes[x] if x in opcoes else ""  # mostra vazio para a opção ""
            )

            st.divider()

            if selecionado_id:  # só continua se um projeto for realmente escolhido
                tipo = "PF" if selecionado_id in [str(p["_id"]) for p, t in todos_projetos if t == "PF"] else "PJ"
                colecao = db["projetos_pf"] if tipo == "PF" else db["projetos_pj"]
                projeto = colecao.find_one({"_id": ObjectId(selecionado_id)})
                atualizado = form_projeto(projeto, tipo, pessoas_dict, programas_dict, projetos_ispn_dict)
                if atualizado:
                    colecao.update_one({"_id": ObjectId(selecionado_id)}, {"$set": atualizado})
                    st.success("Projeto atualizado com sucesso.")
                    time.sleep(1)
                    st.rerun()






    # ---------------------- Excluir ----------------------
    with abas[2]:
 
        # Roteamento de tipo de usuário especial
        if set(st.session_state.tipo_usuario) & {"admin"}:

            todos_projetos = [(p, "PF") for p in pf] + [(p, "PJ") for p in pj]

            opcoes = {
                str(proj["_id"]): f"{proj.get('codigo', '')} ({proj.get('sigla', '')})"
                for proj, tipo in todos_projetos
            }

            if not opcoes:
                st.info("Nenhum projeto encontrado para excluir.")
            else:
                selecionado_id = st.selectbox("Selecione o projeto para excluir", list(opcoes.keys()), format_func=lambda x: opcoes[x])
                tipo = "PF" if selecionado_id in [str(p["_id"]) for p, t in todos_projetos if t == "PF"] else "PJ"
                colecao = db["projetos_pf"] if tipo == "PF" else db["projetos_pj"]
                projeto = colecao.find_one({"_id": ObjectId(selecionado_id)})

                st.write("")

                if st.button(f"Excluir projeto"):
                    colecao.delete_one({"_id": ObjectId(selecionado_id)})
                    st.success("Projeto excluído com sucesso.")
                    time.sleep(1)
                    st.rerun()


@st.cache_data(ttl=600, show_spinner=False)
def extrair_itens_distintos(series: pd.Series) -> pd.Series:
        """
        Recebe uma Series de strings (ex: 'Acre, Rondônia') e retorna uma Series
        'longa' com cada item já limpo, 1 item por linha.
        """
        if series.empty:
            return pd.Series(dtype=str)

        s = (
            series.fillna("")                   # garante string
            .astype(str)
            .str.split(",")                     # divide
            .explode()                          # 1 item por linha
            .str.strip()                        # remove espaços
        )
        # remove vazios e nans textuais
        s = s[(s != "") & (s.str.lower() != "nan")]
        return s
        
               
def parse_valor(valor):
    """Converte valor string para float, retornando 0.0 se não for possível."""
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        valor = valor.strip()
        if valor == "":
            return 0.0
        # Remover separadores de milhar e converter vírgula decimal para ponto
        valor = valor.replace(".", "").replace(",", ".")
        try:
            return float(valor)
        except ValueError:
            return 0.0
    return 0.0


@st.cache_data(ttl=600, show_spinner=False)
def normalizar(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def edital_key(x):
    try:
        return float(x)
    except ValueError:
        return float('inf')  # valores não numéricos vão pro final


######################################################################################################
# MAIN
######################################################################################################


# Combine os dados
todos_projetos = pj + pf

projetos_por_codigo = {str(p.get("codigo", "")).strip(): p for p in todos_projetos if p.get("codigo") is not None}

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


# for projeto in todos_projetos:
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
    "programa",
    "temas",
    "bioma",
    "publico",
    "genero",
    "status",
    "cpf",
    "proponente",
    "ponto_focal"
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
    "cnpj": "CNPJ",
    "cpf": "CPF",
    "proponente": "Proponente",
    "programa": "Programa",
    "temas": "Temas",
    "publico": "Público",
    "bioma": "Bioma",
    "genero": "Gênero",
    "status": "Status",
    "ponto_focal": "Ponto Focal"
})


# Criar dicionário código_uf -> sigla
codigo_uf_para_sigla = {
    '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
    '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA',
    '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP',
    '41': 'PR', '42': 'SC', '43': 'RS',
    '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'
}


df_projetos_codigos = df_projetos.copy()


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


# ##################################################################
# Início da interface
# ##################################################################

st.header("Fundo Ecos")

st.write('')

with st.expander("Filtros", expanded=False, icon=":material/filter_alt:"):
    with st.form("form_filtros", border=False):
        df_base = df_projetos.copy()
        mask = pd.Series(True, index=df_base.index)

        # ===== PRIMEIRA LINHA =====
        col1, col2 = st.columns([1, 5])
        tipos_disponiveis = ["Projetos PJ", "Projetos PF"]
        tipo_sel = col1.pills("Tipo", tipos_disponiveis, selection_mode="multi")
        busca_geral = col2.text_input("Buscar por Sigla, Proponente, CNPJ ou CPF").strip()

        # ===== Segunda Linha =====
        pessoas_dict = {str(p["_id"]): p["nome_completo"] for p in pessoas.find()}
        programas_dict = {str(p["_id"]): p["nome_programa_area"] for p in programas.find()}

        df_base["Ponto Focal"] = df_base["Ponto Focal"].apply(lambda x: pessoas_dict.get(str(x), "Não informado") if pd.notna(x) else "Não informado")
        df_base["Programa"] = df_base["Programa"].apply(lambda x: programas_dict.get(str(x), "Não informado") if pd.notna(x) else "Não informado")

        col1, col2, col3, col4 = st.columns(4)
        categoria_sel = col1.multiselect("Categoria", sorted(df_base["Categoria"].dropna().unique()), placeholder="Todos")
        ponto_focal_sel = col2.multiselect("Ponto Focal", sorted(df_base["Ponto Focal"].dropna().unique()), placeholder="Todos")
        programa_sel = col3.multiselect("Programa", sorted(df_base["Programa"].dropna().unique()), placeholder="Todos")
        genero_sel = col4.multiselect("Gênero", sorted(df_base["Gênero"].dropna().unique()), placeholder="Todos")

        # ===== Terceira Linha =====
        col1, col2, col3, col4 = st.columns(4)
        edital_sel = col1.multiselect("Edital", sorted(df_base["Edital"].dropna().unique(), key=edital_key), placeholder="Todos")
        ano_sel = col2.multiselect("Ano", sorted(df_base["Ano"].dropna().unique()), placeholder="Todos")
        doador_sel = col3.multiselect("Doador", sorted(df_base["Doador"].dropna().unique()), placeholder="Todos")
        codigo_sel = col4.multiselect("Código", sorted(df_base["Código"].dropna().unique()), placeholder="Todos")

        # ===== Quarta Linha =====
        col1, col2, col3, col4 = st.columns(4)
        temas_disponiveis = sorted(df_base["Temas"].dropna().apply(lambda x: [m.strip() for m in x.split(",")]).explode().unique(), key=normalizar)
        temas_sel = col1.multiselect("Temas", temas_disponiveis, placeholder="Todos")

        publicos_disponiveis = sorted(df_base["Público"].dropna().apply(lambda x: [m.strip() for m in x.split(",")]).explode().unique(), key=normalizar)
        publicos_sel = col2.multiselect("Público", publicos_disponiveis, placeholder="Todos")

        biomas_disponiveis = sorted(df_base["Bioma"].dropna().apply(lambda x: [m.strip() for m in x.split(",")]).explode().unique(), key=normalizar)
        biomas_sel = col3.multiselect("Bioma", biomas_disponiveis, placeholder="Todos")

        status_sel = col4.multiselect("Status", sorted(df_base["Status"].dropna().unique()), placeholder="Todos")

        # ===== Quinta Linha =====
        col5, col6 = st.columns(2)
        estados_unicos = sorted(df_base["Estado(s)"].dropna().apply(lambda x: [m.strip() for m in x.split(",")]).explode().unique())
        uf_sel = col5.multiselect("Estado(s)", estados_unicos, placeholder="Todos")

        municipios_unicos = sorted(df_base["Município(s)"].dropna().apply(lambda x: [m.strip() for m in x.split(",")]).explode().unique())
        municipio_sel = col6.multiselect("Município(s)", municipios_unicos, placeholder="Todos")

        # ===== Botão =====
        aplicar = st.form_submit_button("Aplicar filtros")

    # ===== Valor padrão =====
    df_filtrado = df_base.copy()

    # ===== Se clicou, aplica =====
    if aplicar:
        # Aplica todos os filtros (como no código anterior)
        if tipo_sel:
            if "Projetos PJ" in tipo_sel and "Projetos PF" not in tipo_sel:
                mask &= (df_base["Tipo"] == "PJ")
            elif "Projetos PF" in tipo_sel and "Projetos PJ" not in tipo_sel:
                mask &= (df_base["Tipo"] == "PF")

        if busca_geral:
            termo = normalizar(busca_geral)
            def corresponde(row):
                return (
                    termo in normalizar(row["Sigla"]) or
                    termo in normalizar(row["Proponente"]) or
                    termo in normalizar(row["CNPJ"]) or
                    termo in normalizar(row["CPF"])
                )
            mask &= df_base.apply(corresponde, axis=1)

        # Demais filtros...
        if categoria_sel: mask &= df_base["Categoria"].isin(categoria_sel)
        if ponto_focal_sel: mask &= df_base["Ponto Focal"].isin(ponto_focal_sel)
        if programa_sel: mask &= df_base["Programa"].isin(programa_sel)
        if genero_sel: mask &= df_base["Gênero"].isin(genero_sel)
        if edital_sel: mask &= df_base["Edital"].isin(edital_sel)
        if ano_sel: mask &= df_base["Ano"].isin(ano_sel)
        if doador_sel: mask &= df_base["Doador"].isin(doador_sel)
        if codigo_sel: mask &= df_base["Código"].isin(codigo_sel)
        if temas_sel: mask &= df_base["Temas"].apply(lambda x: any(m.strip() in temas_sel for m in x.split(",")) if isinstance(x, str) else False)
        if publicos_sel: mask &= df_base["Público"].apply(lambda x: any(m.strip() in publicos_sel for m in x.split(",")) if isinstance(x, str) else False)
        if biomas_sel: mask &= df_base["Bioma"].apply(lambda x: any(m.strip() in biomas_sel for m in x.split(",")) if isinstance(x, str) else False)
        if status_sel: mask &= df_base["Status"].isin(status_sel)
        if uf_sel: mask &= df_base["Estado(s)"].apply(lambda x: any(m.strip() in uf_sel for m in x.split(",")) if isinstance(x, str) else False)
        if municipio_sel: mask &= df_base["Município(s)"].apply(lambda x: any(m.strip() in municipio_sel for m in x.split(",")) if isinstance(x, str) else False)

        df_filtrado = df_base.loc[mask].copy()

        if df_filtrado.empty:
            st.warning("Nenhum projeto encontrado")
        #else:
            #st.success(f"{len(df_filtrado)} projetos encontrados")


# Salva no session_state para o diálogo de detalhes
st.session_state["df_filtrado"] = df_filtrado

geral, lista, mapa = st.tabs(["Visão geral", "Projetos", "Mapa"])

with geral:
    
    # Separar projetos PF e PJ
    df_pf = df_filtrado[df_filtrado['Tipo'] == 'PF']
    df_pj = df_filtrado[df_filtrado['Tipo'] == 'PJ']


    total_projetos_pf = len(df_pf)
    total_projetos_pj = len(df_pj)
    total_projetos = len(df_filtrado)

    estados_series = extrair_itens_distintos(df_filtrado["Estado(s)"])
    total_ufs = estados_series.nunique()

    municipios_series = extrair_itens_distintos(df_filtrado["Município(s)"])
    total_municipios = municipios_series.nunique()

    # Total de editais únicos (remover vazios)
    total_editais = df_filtrado["Edital"].replace("", pd.NA).dropna().nunique()

    # Total de doadores únicos (remover vazios)
    total_doador = df_filtrado["Doador"].replace("", pd.NA).dropna().nunique()

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

    # Inicializar acumuladores
    valor_total_dolar_corrigido = 0.0
    valor_nominal_dolar = 0.0
    valor_nominal_real = 0.0

    # Criar set de códigos filtrados
    codigos_filtrados = set(df_filtrado["Código"].astype(str).str.strip())

    # Filtrar apenas os projetos que estão em df_filtrado
    projetos_filtrados = [p for p in todos_projetos if str(p.get("codigo", "")).strip() in codigos_filtrados]

    # Inicializar acumuladores
    valor_total_dolar_corrigido = 0.0
    valor_nominal_dolar = 0.0
    valor_nominal_real = 0.0

    for projeto in projetos_filtrados:
        moeda = str(projeto.get("moeda", "")).strip().lower()

        # Valor nominal em US$ (sem correção)
        valor_dolar_original = projeto.get("valor_dolar_original")
        if valor_dolar_original is None or valor_dolar_original == "":
            if moeda in ("dólar"):
                valor_dolar_original = projeto.get("valor", 0)
            else:
                valor_dolar_original = 0
        valor_nominal_dolar += parse_valor(valor_dolar_original)

        # Valor atualizado em US$ (corrigido até 2024)
        valor_dolar_atualizado = projeto.get("valor_dolar_atualizado", 0)
        valor_total_dolar_corrigido += parse_valor(valor_dolar_atualizado)

        # Valor nominal em R$ (somente para projetos em real)
        if moeda in ("real"):
            valor_nominal_real += parse_valor(projeto.get("valor", 0))



    # Exibição das métricas
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Valor total em US$ corrigido até 2024",
        f"{valor_total_dolar_corrigido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    col2.metric(
        "Valor nominal dos contratos em US$",
        f"{valor_nominal_dolar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    col3.metric(
        "Valor nominal dos contratos em R$",
        f"{valor_nominal_real:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )


    st.write("")
    st.write("")
 
    # Gráfico  

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
    
    if df_filtrado.empty:
        anos_todos = []  # garante variável existente
    else:
        try:
            anos_min = pd.to_numeric(df_filtrado["Ano"], errors="coerce").min()
            anos_max = pd.to_numeric(df_filtrado["Ano"], errors="coerce").max()

            if pd.notna(anos_min) and pd.notna(anos_max):
                anos_todos = list(map(str, range(int(anos_min), int(anos_max) + 1)))
            else:
                anos_todos = []
        except Exception as e:
            st.error(f"Erro ao calcular anos disponíveis: {e}")
            anos_todos = []

    # Preencher com 0 onde não há apoio (para doadores já existentes)
    doadores = dados["Doador"].unique()
    todos_anos_doador = pd.MultiIndex.from_product([anos_todos, doadores], names=["Ano", "Doador"])
    dados_completos = dados.set_index(["Ano", "Doador"]).reindex(todos_anos_doador, fill_value=0).reset_index()

    
    paleta_cores = diverging.Spectral_r[::2] + diverging.curl[::2]
    paleta_cores = paleta_cores[:15]  # garante 15 cores únicas
    
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
    st.plotly_chart(fig, use_container_width='stretch')


with lista:

    st.write("")

    # Gera o Excel em memória
    output = io.BytesIO()
    df_filtrado.to_excel(output, index=False)
    output.seek(0)

    # Nome do arquivo
    data_de_hoje = datetime.date.today().strftime("%d-%m-%Y")

    if set(st.session_state.tipo_usuario) & {"admin", "gestao_fundo_ecos"}:
        

        container_botoes = st.container(horizontal=True, horizontal_alignment="right")

        container_botoes.download_button(
            label="Baixar tabela",
            data=output,
            file_name=f"tabela_de_projetos_{data_de_hoje}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            # use_container_width='stretch',
            width=260,
            icon=":material/file_download:"
        )

        container_botoes.button("Cadastrar proponente", on_click=cadastrar_proponente, 
                                # use_container_width='stretch',
                                width=260, 
                                icon=":material/add_business:")

        container_botoes.button("Gerenciar projetos", on_click=gerenciar_projetos, 
                                # use_container_width='stretch',
                                width=260, 
                                icon=":material/contract_edit:")
        
        

    else:

        container_botoes = st.container(horizontal=True, horizontal_alignment="center")
        container_botoes.download_button(
            label="Baixar projetos filtrados",
            data=output,
            file_name=f"projetos_filtrados_{data_de_hoje}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width='stretch',
            icon=":material/file_download:"
        )


    # --- Ordenar Ano desc, Código asc ---
    df_exibir = (
        st.session_state["df_filtrado"]
        .copy()
        .sort_values(by=["Ano", "Código"], ascending=[False, True])
        .reset_index(drop=True)
    )

    # --- Paginação ---
    itens_por_pagina = 50
    total_linhas = len(df_exibir)
    total_paginas = max(math.ceil(total_linhas / itens_por_pagina), 1)

    # --- Inicializar paginação no session_state ---
    if "pagina_atual" not in st.session_state:
        st.session_state["pagina_atual"] = 1
    if "pagina_topo" not in st.session_state:
        st.session_state["pagina_topo"] = st.session_state["pagina_atual"]
    if "pagina_rodape" not in st.session_state:
        st.session_state["pagina_rodape"] = st.session_state["pagina_atual"]

    # --- Funções de callback para sincronização ---
    def atualizar_topo():
        st.session_state["pagina_atual"] = st.session_state["pagina_topo"]
        st.session_state["pagina_rodape"] = st.session_state["pagina_topo"]

    def atualizar_rodape():
        st.session_state["pagina_atual"] = st.session_state["pagina_rodape"]
        st.session_state["pagina_topo"] = st.session_state["pagina_rodape"]

    # --- Controle topo ---
    col1, col2, col3 = st.columns([1,2,5])


    col1.number_input(
        "Página",
        min_value=1,
        max_value=total_paginas,
        # value=st.session_state["pagina_topo"],
        step=1,
        key="pagina_topo",
        on_change=atualizar_topo
    )

    # --- Definir intervalo de linhas ---
    inicio = (st.session_state["pagina_atual"] - 1) * itens_por_pagina
    fim = inicio + itens_por_pagina
    df_paginado = df_exibir.iloc[inicio:fim]



    # --- Informação de contagem ---
    # with col1:
    # st.write("")
    st.write(f"Mostrando **{inicio + 1}** a **{min(fim, total_linhas)}** de **{total_linhas}** projetos")
    st.write("")
    st.write("")


    # --- Layout da tabela customizada ---
    # colunas_visiveis = [c for c in df_exibir.columns]  # personalizar se quiser excluir colunas
    colunas_visiveis = [c for c in df_exibir.columns if c not in ["Tipo", "Município(s)", "CNPJ", "CPF", "Proponente", "Programa", "Temas", "Público", "Bioma", "Gênero", "Status", "Ponto Focal"]]

    headers = colunas_visiveis + ["Detalhes"]

    col_sizes = [2, 2, 1, 2, 2, 2, 1, 2, 3, 3]  

    header_cols = st.columns(col_sizes)
    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.divider()

    for _, row in df_paginado.iterrows():
        cols = st.columns(col_sizes)
        for j, key in enumerate(colunas_visiveis):
            cols[j].write(row[key])

        codigo_proj = str(row["Código"]).strip()
        cols[-1].button(
            "Detalhes",
            key=f"ver_{codigo_proj}",
            on_click=mostrar_detalhes,
            args=(codigo_proj,),
            icon=":material/menu:",
            use_container_width='stretch'
        )
        st.divider()

    # --- Controle rodapé ---
    col1, col2, col3 = st.columns([1,2,5])


    # --- Informação de contagem ---

    col1.number_input(
        "Página",
        min_value=1,
        max_value=total_paginas,
        value=st.session_state["pagina_rodape"],
        step=1,
        key="pagina_rodape",
        on_change=atualizar_rodape
    )

    st.write(f"**Mostrando {inicio + 1} a {min(fim, total_linhas)} de {total_linhas} projetos**")
    st.write("")
    st.write("")

with mapa:
    st.subheader("Mapa de distribuição de projetos")

    @st.cache_data(show_spinner=False)
    def carregar_municipios():
        url = "https://raw.githubusercontent.com/kelvins/Municipios-Brasileiros/master/csv/municipios.csv"
        df = pd.read_csv(url)
        df.rename(columns={'codigo_ibge': 'codigo_municipio'}, inplace=True)
        df['codigo_municipio'] = df['codigo_municipio'].astype(str)
        return df

    df_munis = carregar_municipios()

    @st.cache_data(show_spinner=False)
    def preparar_df_coords(df_projetos_codigos, df_filtrado, df_munis):
        # Extrair código do município
        df_projetos_codigos['codigo_municipio'] = [
            m.split(",")[0].strip() if m else "" 
            for m in df_projetos_codigos['Município Principal']
        ]

        # Filtrar
        df_filtrado_proj = df_projetos_codigos[df_projetos_codigos["Código"].isin(df_filtrado["Código"])].copy()
        df_filtrado_proj['codigo_municipio'] = df_filtrado_proj['Município Principal'].astype(str)
        df_filtrado_proj['Ano'] = df_filtrado_proj['Ano'].astype(str).str.replace(".0", "", regex=False)

        # Merge para coordenadas
        df_coords = df_filtrado_proj.merge(
            df_munis,
            left_on='codigo_municipio',
            right_on='codigo_municipio',
            how='left'
        ).dropna(subset=['latitude', 'longitude']).drop_duplicates(subset='Código')

        return df_coords
    
    @st.cache_data(show_spinner=False)
    def carregar_pontos_focais(_projetos):
        ids = [p["ponto_focal"] for p in _projetos if isinstance(p.get("ponto_focal"), ObjectId)]
        if not ids:
            return {}

        pessoas = list(db["pessoas"].find(
            {"_id": {"$in": ids}},
            {"_id": 1, "nome_completo": 1}
        ))

        return {p["_id"]: p.get("nome_completo", "Não encontrado") for p in pessoas}


    df_coords_projetos = preparar_df_coords(df_projetos_codigos, df_filtrado, df_munis)
    num_proj_mapa = len(df_coords_projetos)
    pontos_focais_dict = carregar_pontos_focais(todos_projetos)
    st.write(f"{num_proj_mapa} projetos no mapa")

    @st.cache_data(show_spinner=False)
    def gerar_mapa(df_coords_projetos, _todos_projetos, df_munis):
        
        m = folium.Map(location=[-15.78, -47.93], zoom_start=4, tiles="CartoDB positron", height="800px")
        cluster = MarkerCluster().add_to(m)

        for _, row in df_coords_projetos.iterrows():
            lat, lon = row['latitude'], row['longitude']
            codigo = row['Código']
            ano_de_aprovacao = row['Ano']

            projeto = next((p for p in todos_projetos if p.get("codigo") == codigo), None)
            if not projeto:
                continue

            proponente = projeto.get("proponente", "")
            nome_proj = projeto.get("nome_do_projeto", "")
            tipo_do_projeto = projeto.get("tipo")
            categoria = projeto.get("categoria")
            sigla = projeto.get("sigla")
            edital = projeto.get("edital")

            # Ponto focal
            ponto_focal_obj = projeto.get("ponto_focal")
            nome_ponto_focal = pontos_focais_dict.get(ponto_focal_obj, "Não informado")

            # Município principal
            muni_principal_codigo = str(row.get('codigo_municipio', '')).strip()
            muni_principal_info = df_munis[df_munis['codigo_municipio'] == muni_principal_codigo]
            if not muni_principal_info.empty:
                nome_muni_principal = muni_principal_info.iloc[0]['nome'].title()
                uf_sigla_principal = codigo_uf_para_sigla.get(str(int(muni_principal_info.iloc[0]['codigo_uf'])), "")
                muni_principal_str = f"{nome_muni_principal} - {uf_sigla_principal}"
            else:
                muni_principal_str = "Não informado"

            # Demais municípios
            codigos_municipios_projeto = [c.strip() for c in str(row.get('Município(s)', '')).split(',') if c.strip()]
            demais_municipios = []
            for cod in codigos_municipios_projeto:
                if cod == muni_principal_codigo:
                    continue
                muni_info = df_munis[df_munis['codigo_municipio'] == cod]
                if not muni_info.empty:
                    nome_muni = muni_info.iloc[0]['nome'].title()
                    uf_sigla = codigo_uf_para_sigla.get(str(int(muni_info.iloc[0]['codigo_uf'])), "")
                    demais_municipios.append(f"{nome_muni} - {uf_sigla}")
            demais_municipios_html = "<br>".join(demais_municipios) if demais_municipios else "Nenhum"

            popup_html = f"""
                <b>Proponente:</b> {proponente}<br>
                <b>Projeto:</b> {nome_proj}<br><br>
                <b>Código:</b> {codigo}<br>
                <b>Sigla:</b> {sigla}<br>
                <b>Ano:</b> {ano_de_aprovacao}<br>
                <b>Edital:</b> {edital}<br>
                <b>Ponto Focal:</b> {nome_ponto_focal}<br>
                <b>{tipo_do_projeto} - {categoria}</b><br><br>
                <b>Município principal:</b> {muni_principal_str}<br>
                <b>Outros municípios:</b><br>
                {demais_municipios_html}
            """

            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=400)
            ).add_to(cluster)

        return m

    mapa_folium = gerar_mapa(df_coords_projetos, todos_projetos, df_munis)
    st_folium(mapa_folium, width=None, height=800, returned_objects=[])