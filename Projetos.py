import streamlit as st
import pandas as pd
import datetime
from bson import ObjectId
import fiona
from funcoes_auxiliares import conectar_mongo_portal_ispn, ajustar_altura_dataframe, br_to_float, float_to_br
import geopandas as gpd
from geobr import read_indigenous_land, read_conservation_units, read_biomes, read_state, read_municipality
import streamlit_shadcn_ui as ui
import plotly.express as px
import time
import bson



st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CSS PARA DIALOGO MAIOR
######################################################################################################
st.markdown(
    """
<style>
div[data-testid="stDialog"] div[role="dialog"]:has(.big-dialog) {
    width: 50vw;
    
}
</style>
""",
    unsafe_allow_html=True,
)


######################################################################################################
# FUNÇÕES AUXILIARES
######################################################################################################


# Formatando as moedas nos valores
# Dicionário de símbolos por moeda
moedas = {
    "reais": "R$",
    "real": "R$",
    "dólares": "US$",
    "dólar": "US$",
    "euros": "€",  # Incluído para futuro uso
    "euro": "€"
}

# Dicionário de nomes legíveis dos indicadores
nomes_legiveis = {
    "numero_de_organizacoes_apoiadas": "Número de organizações apoiadas",
    "numero_de_comunidades_fortalecidas": "Número de comunidades fortalecidas",
    "numero_de_familias": "Número de famílias beneficiadas",
    "numero_de_homens_jovens": "Número de homens jovens",
    "numero_de_homens_adultos": "Número de homens adultos",
    "numero_de_mulheres_jovens": "Número de mulheres jovens",
    "numero_de_mulheres_adultas": "Número de mulheres adultas",
    "numero_de_indigenas": "Número de indígenas",
    "numero_de_liderancas_comunitarias_fortalecidas": "Número de lideranças comunitárias fortalecidas",
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


# Função de parse valor para indicadores float
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


# Função para limpar e formatar o valor com notação de moeda (duas casas decimais)
def formatar_valor(row):
    moeda = moedas.get(row['moeda'].lower(), '')
    try:
        valor = row['valor'] if row['valor'] else 0
        # Converter string brasileira para float
        valor_num = float(str(valor).replace('.', '').replace(',', '.'))
        # Formatar com ponto como separador de milhares e vírgula para decimais
        valor_formatado = f"{valor_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{moeda} {valor_formatado}"
    except:
        return f"{moeda} 0,00"



# Converter objectid para string
def convert_objectid(obj):
    if isinstance(obj, bson.ObjectId):
        return str(obj)
    elif isinstance(obj, list):
        return [convert_objectid(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    else:
        return obj





######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
estrategia = db["estrategia"]  # Coleção de estatísticas
programas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"]  
indicadores = db["indicadores"]
colecao_lancamentos = db["lancamentos_indicadores"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


# # Nome da página atual, usado como chave para contagem de acessos
# nome_pagina = "Projetos"

# # Cria um timestamp formatado com dia/mês/ano hora:minuto:segundo
# timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# # Cria o nome do campo dinamicamente baseado na página
# campo_timestamp = f"{nome_pagina}.Visitas"

# # Atualiza a coleção de estatísticas com o novo acesso, incluindo o timestamp
# estatistica.update_one(
#     {},
#     {"$push": {campo_timestamp: timestamp}},
#     upsert=True  # Cria o documento se ele ainda não existir
# 



######################################################################################################
# TRATAMENTO DOS DADOS
######################################################################################################


# --- 1. Converter listas de documentos em DataFrames ---
df_doadores = pd.DataFrame(list(db["doadores"].find()))
df_programas = pd.DataFrame(list(db["programas_areas"].find()))
df_projetos_ispn = pd.DataFrame(list(projetos_ispn.find()))
df_pessoas = pd.DataFrame(list(db["pessoas"].find()))


# PROJETOS

# --- 2. Criar dicionários de mapeamento ---
mapa_doador = {d["_id"]: d["nome_doador"] for d in db["doadores"].find()}
mapa_programa = {p["_id"]: p["nome_programa_area"] for p in db["programas_areas"].find()}

# --- 3. Aplicar os mapeamentos ao df_projetos_ispn ---
df_projetos_ispn["doador_nome"] = df_projetos_ispn["doador"].apply(
    lambda x: mapa_doador.get(x, "não informado")
)
df_projetos_ispn["programa_nome"] = df_projetos_ispn["programa"].apply(
    lambda x: mapa_programa.get(x, "não informado")
)

# --- 4. Criar a coluna 'valor_com_moeda' ---
df_projetos_ispn['valor_com_moeda'] = df_projetos_ispn.apply(formatar_valor, axis=1)


# --- 5. Converter datas para datetime
df_projetos_ispn['data_inicio_contrato'] = pd.to_datetime(
    df_projetos_ispn['data_inicio_contrato'], format="%d/%m/%Y", errors="coerce"
)
df_projetos_ispn['data_fim_contrato'] = pd.to_datetime(
    df_projetos_ispn['data_fim_contrato'], format="%d/%m/%Y", errors="coerce"
)


# PESSOAS
# Converter objectid para string em df_pessoas
df_pessoas = df_pessoas.map(convert_objectid)

# Criar mapa de _id -> nome_programa_area (como string)
mapa_programa = {str(p["_id"]): p["nome_programa_area"] for p in db["programas_areas"].find()}

# Criar mapa de _id -> nome_completo (coordenador)
mapa_coordenador = {str(p["_id"]): p["nome_completo"] for p in db["pessoas"].find()}

# Aplicar mapeamento no df_pessoas
df_pessoas["programa_area_nome"] = df_pessoas["programa_area"].map(mapa_programa)
df_pessoas["coordenador_nome"] = df_pessoas["coordenador"].map(mapa_coordenador)


# # DOADORES
# mapa_doador = {str(d["_id"]): d["nome_doador"] for d in doadores_col.find()}



######################################################################################################
# INTERFACE
######################################################################################################


st.header("Projetos do ISPN")

st.write('')


# tab1, tab2, tab3 = st.tabs(["Visão geral", "Projeto", "Entregas"])
tab1, tab2 = st.tabs(["Visão geral", "Projeto"])

# VISÃO GERAL -------------------------------------------------------------
with tab1:

    st.write('')


    # FILTROS ---------------------------------------------------------------

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

    # Filtro doadores
    doadores_disponiveis = sorted(df_projetos_ispn['doador_nome'].unique())
    doador_selecionado = col1.selectbox("Doador", options=["Todos"] + doadores_disponiveis, index=0, key="doador")

    # Filtro programas
    programas_disponiveis = sorted(df_projetos_ispn['programa_nome'].unique())
    programa_selecionado = col2.selectbox("Programa", options=["Todos"] + programas_disponiveis, index=0, key='programa_aba1')

    # Filtro situação
    situacoes_disponiveis = sorted(df_projetos_ispn['status'].unique())
    # Inclui Todas como primeira opção
    situacoes_disponiveis = ["Todos"] + situacoes_disponiveis
    # Define índice padrão como "Em andamento", se existir
    index_padrao = situacoes_disponiveis.index("Em andamento") if "Em andamento" in situacoes_disponiveis else 0
    # Selectbox com valor padrão
    status_selecionado = col3.selectbox("Situação", options=situacoes_disponiveis, index=index_padrao, key='situacao')
    # status_selecionado = col3.selectbox("Situação", options=["Todas"] + situacoes_disponiveis, index=situacoes_disponiveis.index("Em andamento"), key='situacao')

   
    # Filtro de ano de início
    # Pegar o menor e maior anos
    anos_disponiveis_inicio = sorted(df_projetos_ispn['data_inicio_contrato'].dt.year.unique())        
    anos_disponiveis_inicio = [ano for ano in anos_disponiveis_inicio if not pd.isna(ano)]        # Remove anos vazios
    menor_ano_inicio = int(anos_disponiveis_inicio[0])
    maior_ano_inicio = int(anos_disponiveis_inicio[-1])
    # Faz um range de anos entre o menor e o maior
    anos_disponiveis_inicio = [str(ano) for ano in range(menor_ano_inicio, maior_ano_inicio + 1)]
    # Input de ano de início
    ano_inicio_selecionado = col4.selectbox("Vigentes entre", options=anos_disponiveis_inicio, index=0, key="ano_inicio")

    # Filtro de ano de fim
    # Pegar o menor e maior anos
    anos_disponiveis_fim = sorted(df_projetos_ispn['data_fim_contrato'].dt.year.unique())        
    anos_disponiveis_fim = [ano for ano in anos_disponiveis_fim if not pd.isna(ano)]        # Remove anos vazios
    menor_ano_fim = anos_disponiveis_fim[0].astype(int)
    maior_ano_fim = anos_disponiveis_fim[-1].astype(int)
    # Faz um range de anos entre o menor e o maior
    anos_disponiveis_fim = [str(ano) for ano in range(menor_ano_fim, maior_ano_fim + 1)]
    # Input de ano de fim
    ano_fim_selecionado = col5.selectbox("e", options=anos_disponiveis_fim, index=len(anos_disponiveis_fim) - 1, key="ano_fim")

    # Filtrando
    df_projetos_ispn_filtrado = df_projetos_ispn.copy()

    if doador_selecionado != "Todos":
        df_projetos_ispn_filtrado = df_projetos_ispn_filtrado[df_projetos_ispn_filtrado['doador_nome'] == doador_selecionado]

    if programa_selecionado != "Todos":
        df_projetos_ispn_filtrado = df_projetos_ispn_filtrado[df_projetos_ispn_filtrado['programa_nome'] == programa_selecionado]

    if status_selecionado != "Todos":
        df_projetos_ispn_filtrado = df_projetos_ispn_filtrado[df_projetos_ispn_filtrado['status'] == status_selecionado]


    # Filtro dos anos
    # Converter anos selecionados em datas reais (01/01 e 31/12)
    data_inicio_periodo = pd.to_datetime(f"{ano_inicio_selecionado}-01-01")
    data_fim_periodo = pd.to_datetime(f"{ano_fim_selecionado}-12-31")

    # Filtrar projetos que possuem qualquer interseção com esse período
    df_projetos_ispn_filtrado = df_projetos_ispn_filtrado[
        (df_projetos_ispn_filtrado['data_fim_contrato'] >= data_inicio_periodo) &
        (df_projetos_ispn_filtrado['data_inicio_contrato'] <= data_fim_periodo)
    ]


    # Fim dos filtros -----------------------------------------------------------------------------



    # Contagem de projetos -------------------------------
    st.write('')
    st.subheader(f'{len(df_projetos_ispn_filtrado)} projetos')
    st.write('')


    # Cronograma ------------------------------------------
    with st.expander('Ver cronograma'):

        # Gráfico de gantt cronograma 

        # Organizando o df por ordem de data_fim_contrato
        df_projetos_ispn_filtrado = df_projetos_ispn_filtrado.sort_values(by='data_fim_contrato', ascending=False)

        # Mapeamento de meses em português para número
        meses = {
            "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
            "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
            "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
        }

        # Tentando calcular a altura do gráfico dinamicamente
        altura_base = 400  # altura mínima
        altura_extra = sum([10 / (1 + i * 0.01) for i in range(len(df_projetos_ispn_filtrado))])
        altura = int(altura_base + altura_extra)



        fig = px.timeline(
            df_projetos_ispn_filtrado,
            x_start='data_inicio_contrato',
            x_end='data_fim_contrato',
            y='sigla',
            color='status',
            color_discrete_map={
                'Em andamento': 'rgba(0,122,211,0.5)',
                'Finalizado': "rgba(131,201,255,0.5)",
                '': 'red',
            },
            height=altura,  
            labels={
                'sigla': 'Projeto',
                'status': 'Situação',
                'data_inicio_contrato': 'Início',
                'data_fim_contrato': 'Fim'
            },
        )

        # Adiciona a linha vertical para o dia de hoje
        fig.add_vline(
            x=datetime.datetime.today(),
            line_width=2,
            line_dash="dash",
            line_color="black",
        )

        # Ajusta layout
        fig.update_layout(
            legend=dict(
                orientation="h",   # horizontal
                yanchor="bottom",
                y=-0.2,            # move para baixo do gráfico
                xanchor="center",
                x=0.5
            ),
            yaxis=dict(
                title=None,
                side="right"       # coloca labels do eixo Y à direita
            ),
            xaxis=dict(
                showgrid=True,
                gridcolor='lightgray',
                tickmode='linear',
                dtick="M12",        # Mostra 1 tick por ano (12 meses)
                tickformat="%Y"
            )
        )

        st.plotly_chart(fig)







    # Lista de projetos --------------------------
    st.write('')
    # st.write('**Projetos**')

    # Selecionando colunas pra mostrar
    df_projetos_ispn_filtrado_show = df_projetos_ispn_filtrado[['codigo', 'nome_do_projeto', 'programa_nome', 'doador_nome', 'valor_com_moeda', 'data_inicio_contrato', 'data_fim_contrato', 'status']]

    
    # Formatando as datas
    df_projetos_ispn_filtrado_show = df_projetos_ispn_filtrado_show.copy()

    df_projetos_ispn_filtrado_show['data_inicio_contrato'] = (
        df_projetos_ispn_filtrado_show['data_inicio_contrato'].dt.strftime('%d/%m/%Y')
    )
    df_projetos_ispn_filtrado_show['data_fim_contrato'] = (
        df_projetos_ispn_filtrado_show['data_fim_contrato'].dt.strftime('%d/%m/%Y')
    )



    # Renomeando as colunas
    df_projetos_ispn_filtrado_show = df_projetos_ispn_filtrado_show.rename(columns={
        'codigo': 'Código',
        'programa_nome': 'Programa',
        'doador_nome': 'Doador',
        'data_inicio_contrato': 'Início do contrato',
        'data_fim_contrato': 'Fim do contrato',
        'status': 'Situação',
        'valor_com_moeda': 'Valor',
        'nome_do_projeto': 'Nome do projeto'
    })


    # Drop das colunas moeda e valor
    # df_projetos_ispn_filtrado_show = df_projetos_ispn_filtrado_show.drop(columns=['moeda', 'valor'])


    # Reorganizar a ordem das colunas
    df_projetos_ispn_filtrado_show = df_projetos_ispn_filtrado_show[['Código', 'Nome do projeto', 'Programa', 'Doador', 'Valor', 'Início do contrato', 'Fim do contrato', 'Situação']]

    # Exibindo o DataFrame
    ajustar_altura_dataframe(df_projetos_ispn_filtrado_show, 1)






# ABA PROJETO -------------------------------------------------------------------------------------
with tab2:
    st.write('')


    container_selecao = st.container(horizontal=True, horizontal_alignment='distribute')

    # Seleção do projeto
    projetos_selectbox = [""] + sorted(df_projetos_ispn["sigla"].unique().tolist())
    projeto_selecionado = container_selecao.selectbox('Selecione um projeto', projetos_selectbox, width=300)



    # Botão para cadastrar projeto ------------------------------------

    # Função do diálogo
    @st.dialog("Cadastrar novo projeto")
    def dialog_cadastrar_projeto(): 

        # Aumentar largura do diálogo com css
        st.html("<span class='big-dialog'></span>")
        
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

        @st.cache_data(show_spinner="Carregando estados...")
        def carregar_ufs(ano=2020):
            return read_state(year=ano, simplified=True)

        @st.cache_data(show_spinner="Carregando municipios...")
        def carregar_municipios(ano=2024):
            return read_municipality(year=ano, simplified=True)

        @st.cache_data(show_spinner="Carregando terras indígenas...")
        def carregar_terras_indigenas(data=201907):
            return read_indigenous_land(date=data, simplified=True)

        @st.cache_data(show_spinner="Carregando unidades de conservação...")
        def carregar_uc(data=201909):
            return read_conservation_units(date=data, simplified=True)

        @st.cache_data(show_spinner="Carregando biomas...")
        def carregar_biomas(ano=2019):
            return read_biomes(year=ano, simplified=True)

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
        dados_ufs = carregar_ufs()
        dados_municipios = carregar_municipios()
        dados_ti = carregar_terras_indigenas()
        dados_uc = carregar_uc()
        dados_assentamentos = carregar_assentamentos()
        dados_quilombos = carregar_quilombos()

        dados_biomas = carregar_biomas()
        # Remover linha "Sistema Costeiro" e ordenar alfabeticamente
        dados_biomas = (
            dados_biomas[dados_biomas["name_biome"] != "Sistema Costeiro"]
            .sort_values(by="name_biome", ascending=True)
            .reset_index(drop=True)
        )


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
        dados_biomas = dados_biomas.sort_values(by="name_biome", ascending=True, ignore_index=True) if "name_biome" in dados_biomas.columns else dados_biomas
        dados_bacias_macro = dados_bacias_macro.sort_values(by="nome", ascending=True, ignore_index=True)
        dados_bacias_meso = dados_bacias_meso.sort_values(by="nome", ascending=True, ignore_index=True)
        dados_bacias_micro = dados_bacias_micro.sort_values(by="nome", ascending=True, ignore_index=True)
        dados_assentamentos = dados_assentamentos.sort_values(by="nome", ascending=True, ignore_index=True)
        dados_quilombos = dados_quilombos.sort_values(by="nome", ascending=True, ignore_index=True)
        dados_municipios = dados_municipios.sort_values(by="name_muni", ascending=True, ignore_index=True) if "name_muni" in dados_municipios.columns else dados_municipios
        dados_ufs = dados_ufs.sort_values(by="name_state", ascending=True, ignore_index=True) if "name_state" in dados_ufs.columns else dados_ufs

        # --- Corrigir tipos de código para int (sem casas decimais) ---
        def corrigir_codigo(df, colunas):
            for col in colunas:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)
            return df

        dados_ufs = corrigir_codigo(dados_ufs, ["code_state"])
        dados_municipios = corrigir_codigo(dados_municipios, ["code_muni"])
        dados_biomas = corrigir_codigo(dados_biomas, ["code_biome"])

        with st.form("form_cadastrar_projeto"):
            # --- Colunas ---
            col1, col2, col3 = st.columns([1,1,1])

            # --- Código ---
            codigo = col1.text_input("Código", value="")

            # --- Sigla ---
            sigla = col2.text_input("Sigla", value="")

            # --- Nome do projeto ---
            nome_do_projeto = col3.text_input("Nome do Projeto", value="")



            # --- Status ---
            status_options = ["", "Em andamento", "Finalizado", "Pausado"]
            status = col1.selectbox("Status", options=status_options, index=0)

            # --- Datas ---
            data_inicio = col2.date_input("Data de início", value=datetime.date.today(), format="DD/MM/YYYY")
            data_fim = col3.date_input("Data de fim", value=datetime.date.today(), format="DD/MM/YYYY")




            # --- Moeda ---
            moeda_options = ["", "Dólares", "Reais", "Euros"]
            moeda = col1.selectbox("Moeda", options=moeda_options, index=0)

            # --- Valor ---
            valor = col2.number_input("Valor", value=0.00, step=0.01, min_value=0.0, format="%.2f")

            # --- Contrapartida ---
            contrapartida = col3.number_input("Contrapartida", value=0.00, step=0.01, min_value=0.0, format="%.2f")

            # --- Coordenador ---
            coordenador_options = [""] + df_pessoas["_id"].astype(str).tolist()
            coordenador = col1.selectbox(
                "Coordenador",
                options=coordenador_options,
                format_func=lambda x: "" if x=="" else df_pessoas.loc[df_pessoas["_id"].astype(str)==x, "nome_completo"].values[0],
                index=0
            )

            # --- Doador ---
            doador_options = [""] + list(mapa_doador.keys())
            doador = col2.selectbox(
                "Doador",
                options=doador_options,
                format_func=lambda x: "" if x=="" else mapa_doador[x],
                index=0
            )

            # --- Programa / Área ---
            programa_options = [""] + list(mapa_programa.keys())
            programa = col3.selectbox(
                "Programa / Área",
                options=programa_options,
                format_func=lambda x: "" if x=="" else mapa_programa[x],
                index=0
            )


            # --- Objetivo Geral ---
            objetivo_geral = st.text_area("Objetivo Geral", value="")

            
            ######################################################################
            # REGIÕES DE ATUAÇÃO
            ######################################################################

            # Estados
            uf_codigo_para_label = {
                str(row["code_state"]): f"{row['name_state']} ({int(row['code_state'])})"
                for _, row in dados_ufs.iterrows()
            }

            # Estados
            municipios_codigo_para_label = {
                str(row["code_muni"]): f"{row['name_muni']} ({int(row['code_muni'])})"
                for _, row in dados_municipios.iterrows()
            }

            # Estados
            biomas_codigo_para_label = {
                str(row["code_biome"]): f"{row['name_biome']} ({int(row['code_biome'])})"
                for _, row in dados_biomas.iterrows()
            }

            # Terras Indígenas
            ti_codigo_para_label = {
                str(row["code_terrai"]): f"{row['terrai_nom']} ({int(row['code_terrai'])})"
                for _, row in dados_ti.iterrows()
            }

            # Unidades de Conservação
            uc_codigo_para_label = {
                str(row["code_conservation_unit"]): f"{row['name_conservation_unit']} ({row['code_conservation_unit']})"
                for _, row in dados_uc.iterrows()
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
            

            # ----------------------- TERRAS INDÍGENAS -----------------------
            col1, col2, col3 = st.columns(3)

            ufs_selecionadas = col1.multiselect(
                "Estados",
                options=list(uf_codigo_para_label.values()),
                placeholder=""
            )

            municipios_selecionadas = col2.multiselect(
                "Municípios",
                options=list(municipios_codigo_para_label.values()),
                placeholder=""
            )

            biomas_selecionados = col3.multiselect(
                "Biomas",
                options=list(biomas_codigo_para_label.values()),
                placeholder=""
            )

            # ----------------------- TERRAS INDÍGENAS -----------------------
            col1, col2 = st.columns(2)

            tis_selecionadas = col1.multiselect(
                "Terras Indígenas",
                options=list(ti_codigo_para_label.values()),
                placeholder=""
            )

            # ----------------------- UNIDADES DE CONSERVAÇÃO -----------------------
            ucs_selecionadas = col2.multiselect(
                "Unidades de Conservação",
                options=list(uc_codigo_para_label.values()),
                placeholder=""
            )

            # ----------------------- ASSENTAMENTOS -----------------------
            col1, col2 = st.columns(2)
            assentamentos_selecionados = col1.multiselect(
                "Assentamentos",
                options=list(assent_codigo_para_label.values()),
                placeholder=""
            )

            # ----------------------- QUILOMBOS -----------------------
            quilombos_selecionados = col2.multiselect(
                "Quilombos",
                options=list(quilombo_codigo_para_label.values()),
                placeholder=""
            )

            # ----------------------- BACIAS HIDROGRÁFICAS -----------------------
            col1, col2, col3 = st.columns(3)

            bacias_macro_sel = col1.multiselect(
                "Bacias Hidrográficas - Macro",
                options=list(bacia_macro_codigo_para_label.values()),
                placeholder=""
            )

            bacias_meso_sel = col2.multiselect(
                "Bacias Hidrográficas - Meso",
                options=list(bacia_meso_codigo_para_label.values()),
                placeholder=""
            )

            bacias_micro_sel = col3.multiselect(
                "Bacias Hidrográficas - Micro",
                options=list(bacia_micro_codigo_para_label.values()),
                placeholder=""
            )

            st.write('')



            # --- Botão de salvar ---
            submit = st.form_submit_button("Cadastrar", icon=":material/save:", width=200, type="primary")
            if submit:
                # --- Validar unicidade de sigla e código ---
                sigla_existente = (df_projetos_ispn["sigla"] == sigla).any()
                codigo_existente = (df_projetos_ispn["codigo"] == codigo).any()

                if sigla_existente:
                    st.warning(f"A sigla '{sigla}' já está cadastrada em outro projeto. Escolha outra.")
                elif codigo_existente:
                    st.warning(f"O código '{codigo}' já está cadastrado em outro projeto. Escolha outro.")
                else:
                    # --- Criar ObjectIds ---
                    projeto_id = bson.ObjectId()
                    coordenador_objid = bson.ObjectId(coordenador) if coordenador else None
                    doador_objid = bson.ObjectId(doador) if doador else None
                    programa_objid = bson.ObjectId(programa) if programa else None

                    # ----------------------------------------------------------
                    # MONTAR LISTA DE REGIÕES DE ATUAÇÃO PARA SALVAR NO MONGODB
                    # ----------------------------------------------------------

                    # Função auxiliar
                    def get_codigo_por_label(dicionario, valor):
                        return next((codigo for codigo, label in dicionario.items() if label == valor), None)

                    regioes_atuacao = []

                    # Tipos simples com lookup
                    for tipo, selecionados, dicionario in [
                        ("uf", ufs_selecionadas, uf_codigo_para_label),
                        ("municipio", municipios_selecionadas, municipios_codigo_para_label),
                        ("bioma", biomas_selecionados, biomas_codigo_para_label),
                        ("terra_indigena", tis_selecionadas, ti_codigo_para_label),
                        ("uc", ucs_selecionadas, uc_codigo_para_label),
                        ("assentamento", assentamentos_selecionados, assent_codigo_para_label),
                        ("quilombo", quilombos_selecionados, quilombo_codigo_para_label),
                        ("bacia_micro", bacias_micro_sel, bacia_micro_codigo_para_label),
                        ("bacia_meso", bacias_meso_sel, bacia_meso_codigo_para_label),
                        ("bacia_macro", bacias_macro_sel, bacia_macro_codigo_para_label),
                    ]:
                        for item in selecionados:
                            codigo_atuacao = get_codigo_por_label(dicionario, item)
                            if codigo_atuacao:
                                regioes_atuacao.append({"tipo": tipo, "codigo": codigo_atuacao})

                    # ----------------------------------------------------------

                    # --- Montar documento ---
                    doc = {
                        "_id": projeto_id,
                        "codigo": codigo,
                        "sigla": sigla,
                        "nome_do_projeto": nome_do_projeto,
                        "moeda": moeda,
                        "valor": float_to_br(valor),
                        "valor_da_contrapartida_em_r$": float_to_br(contrapartida),
                        "coordenador": coordenador_objid,
                        "doador": doador_objid,
                        "programa": programa_objid,
                        "status": status,
                        "data_inicio_contrato": data_inicio.strftime("%d/%m/%Y"),
                        "data_fim_contrato": data_fim.strftime("%d/%m/%Y"),
                        "objetivo_geral": objetivo_geral,
                        "regioes_atuacao": regioes_atuacao,  
                    }

                    # --- Inserir no MongoDB ---
                    projetos_ispn.insert_one(doc)
                    st.success("Projeto cadastrado com sucesso!")
                    time.sleep(2)
                    st.rerun()

    # Botão para cadastrar projeto
    if container_selecao.button("Cadastrar projeto", icon=":material/add:", width=300):
        dialog_cadastrar_projeto()



    # Carrega informações do projeto
    projeto_info = df_projetos_ispn.loc[df_projetos_ispn["sigla"] == projeto_selecionado]


    if projeto_selecionado == "":
        # st.write('Selecione um projeto')
        st.stop()
    else:
        st.divider()


    with st.container(horizontal=True):

        # Sigla do projeto
        st.markdown(f"<h3 style='color:#007ad3'>{projeto_selecionado}</h3>", unsafe_allow_html=True)
        st.write('')



        # Botão de gerenciar -------------------
        
        # Roteamento de tipo de usuário especial
        if set(st.session_state.tipo_usuario) & {"admin", "gestao_projetos_doadores"}:

            # Função do diálogo para gerenciar projeto
            @st.dialog("Editar Projeto", width="large")
            def dialog_editar_projeto():
                
                # Aumentar largura do diálogo
                st.html("<span class='big-dialog'></span>")
                
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

                @st.cache_data(show_spinner="Carregando estados...")
                def carregar_ufs(ano=2020):
                    return read_state(year=ano, simplified=True)

                @st.cache_data(show_spinner="Carregando municípios...")
                def carregar_municipios(ano=2024):
                    return read_municipality(year=ano, simplified=True)

                @st.cache_data(show_spinner="Carregando TIs...")
                def carregar_terras_indigenas(data=201907):
                    return read_indigenous_land(date=data, simplified=True)

                @st.cache_data(show_spinner="Carregando UCs...")
                def carregar_uc(data=201909):
                    return read_conservation_units(date=data, simplified=True)

                @st.cache_data(show_spinner="Carregando biomas...")
                def carregar_biomas(ano=2019):
                    return read_biomes(year=ano, simplified=True)

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
                dados_ufs = carregar_ufs()
                dados_municipios = carregar_municipios()
                dados_ti = carregar_terras_indigenas()
                dados_uc = carregar_uc()
                dados_assentamentos = carregar_assentamentos()
                dados_quilombos = carregar_quilombos()

                dados_biomas = carregar_biomas()
                # Remover linha "Sistema Costeiro" e ordenar alfabeticamente
                dados_biomas = (
                    dados_biomas[dados_biomas["name_biome"] != "Sistema Costeiro"]
                    .sort_values(by="name_biome", ascending=True)
                    .reset_index(drop=True)
                )


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
                dados_biomas = dados_biomas.sort_values(by="name_biome", ascending=True, ignore_index=True) if "name_biome" in dados_biomas.columns else dados_biomas
                dados_bacias_macro = dados_bacias_macro.sort_values(by="nome", ascending=True, ignore_index=True)
                dados_bacias_meso = dados_bacias_meso.sort_values(by="nome", ascending=True, ignore_index=True)
                dados_bacias_micro = dados_bacias_micro.sort_values(by="nome", ascending=True, ignore_index=True)
                dados_assentamentos = dados_assentamentos.sort_values(by="nome", ascending=True, ignore_index=True)
                dados_quilombos = dados_quilombos.sort_values(by="nome", ascending=True, ignore_index=True)
                dados_municipios = dados_municipios.sort_values(by="name_muni", ascending=True, ignore_index=True) if "name_muni" in dados_municipios.columns else dados_municipios
                dados_ufs = dados_ufs.sort_values(by="name_state", ascending=True, ignore_index=True) if "name_state" in dados_ufs.columns else dados_ufs

                # --- Corrigir tipos de código para int (sem casas decimais) ---
                def corrigir_codigo(df, colunas):
                    for col in colunas:
                        if col in df.columns:
                            df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)
                    return df

                dados_ufs = corrigir_codigo(dados_ufs, ["code_state"])
                dados_municipios = corrigir_codigo(dados_municipios, ["code_muni"])
                dados_biomas = corrigir_codigo(dados_biomas, ["code_biome"])

                projeto_info = df_projetos_ispn[df_projetos_ispn["sigla"] == projeto_selecionado].iloc[0]

                # =============================
                # CRIAÇÃO DAS ABAS
                # =============================
                aba1, aba2 = st.tabs(["Informações gerais", "Entregas"])

                # ==============================================================
                # ABA 1 - INFORMAÇÕES GERAIS (CONTEÚDO ATUAL)
                # ==============================================================

                with aba1:

                    with st.form("form_editar_projeto"):

                        col1, col2 = st.columns(2)
                        
                        
                        # Código
                        codigo = col1.text_input("Código", value=projeto_info.get("codigo", ""))
                        
                        # Sigla
                        sigla = col2.text_input("Sigla", value=projeto_info.get("sigla", ""))
                        
                        # Nome do projeto
                        nome_do_projeto = st.text_input("Nome do Projeto", value=projeto_info.get("nome_do_projeto", ""))



                        col1, col2, col3 = st.columns(3)

                        # Status
                        status_options = ["", "Em andamento", "Finalizado", "Pausado"]

                        status_atual = projeto_info.get("status", "")
                        index_status = status_options.index(status_atual) if status_atual in status_options else 0

                        status = col1.selectbox(
                            "Status",
                            options=status_options,
                            index=index_status
                        )



                        # Datas
                        data_inicio = col2.date_input(
                            "Data de início",
                            value=pd.to_datetime(projeto_info.get("data_inicio_contrato"), format="%d/%m/%Y", errors="coerce").date()
                            if projeto_info.get("data_inicio_contrato") else "datetime.date.today()",
                            format="DD/MM/YYYY"
                        )

                        data_fim = col3.date_input(
                            "Data de fim",
                            value=pd.to_datetime(projeto_info.get("data_fim_contrato"), format="%d/%m/%Y", errors="coerce").date()
                            if projeto_info.get("data_fim_contrato") else "datetime.date.today()",
                            format="DD/MM/YYYY"
                        )


                        # Moeda
                        moeda_options = ["", "Dólares", "Reais", "Euros"]
                        moeda_atual = projeto_info.get("moeda", "")
                        index_atual = moeda_options.index(moeda_atual) if moeda_atual in moeda_options else 0
                        moeda = col1.selectbox("Moeda", options=moeda_options, index=index_atual)
                        
                        # Valor (converte do banco para float antes de exibir)
                        valor_atual = br_to_float(projeto_info.get("valor", "0"))
                        valor = col2.number_input("Valor", value=valor_atual, step=0.01, min_value=0.0, format="%.2f")

                        # Contrapartida (também convertida para float para usar number_input)
                        contrapartida_atual = br_to_float(projeto_info.get("valor_da_contrapartida_em_r$", "0"))
                        contrapartida = col3.number_input("Contrapartida em R$", value=contrapartida_atual, step=0.01, min_value=0.0, format="%.2f")


                        # Coordenador
                        coordenador_options = [""] + df_pessoas["_id"].astype(str).tolist()  # inclui vazio
                        coordenador_atual = str(projeto_info.get("coordenador", "")) if projeto_info.get("coordenador") else ""

                        index_coordenador = (
                            coordenador_options.index(coordenador_atual)
                            if coordenador_atual in coordenador_options
                            else 0
                        )

                        coordenador = col1.selectbox(
                            "Coordenador",
                            options=coordenador_options,
                            format_func=lambda x: "" if x == "" else df_pessoas.loc[df_pessoas["_id"].astype(str) == x, "nome_completo"].values[0],
                            index=index_coordenador
                        )

                        # Programa / Área
                        mapa_programa_str = {str(k): v for k, v in mapa_programa.items()}

                        programa_options = list(mapa_programa_str.keys())
                        programa_atual = str(projeto_info.get("programa", ""))  # valor do banco como string
                        index_programa = programa_options.index(programa_atual) if programa_atual in programa_options else 0

                        # Determinar índice do valor atual
                        index_programa = programa_options.index(programa_atual) if programa_atual in programa_options else 0

                        programa = col2.selectbox(
                            "Programa / Área",
                            options=programa_options,
                            format_func=lambda x: mapa_programa_str[x],  # pega o nome do programa
                            index=index_programa
                        )
                        
                        # Doador
                        doador_options = list(mapa_doador.keys())
                        doador_atual = projeto_info.get("doador", "")
                        index_doador = doador_options.index(doador_atual) if doador_atual in doador_options else 0
                        doador = col3.selectbox(
                            "Doador",
                            options=doador_options,
                            format_func=lambda x: mapa_doador[x],
                            index=index_doador
                        )



                        # Objetivo geral
                        objetivo_geral = st.text_area(
                            "Objetivo Geral",
                            value=str(projeto_info.get("objetivo_geral", "")) if pd.notna(projeto_info.get("objetivo_geral")) else ""
                        )

                        ######################################################################
                        # REGIÕES DE ATUAÇÃO
                        ######################################################################

                        # Estados
                        uf_codigo_para_label = {
                            str(row["code_state"]): f"{row['name_state']} ({int(row['code_state'])})"
                            for _, row in dados_ufs.iterrows()
                        }

                        # Municípios
                        municipios_codigo_para_label = {
                            str(row["code_muni"]): f"{row['name_muni']} ({int(row['code_muni'])})"
                            for _, row in dados_municipios.iterrows()
                        }

                        # Biomas
                        biomas_codigo_para_label = {
                            str(row["code_biome"]): f"{row['name_biome']} ({int(row['code_biome'])})"
                            for _, row in dados_biomas.iterrows()
                        }

                        # Terras Indígenas
                        ti_codigo_para_label = {
                            str(row["code_terrai"]): f"{row['terrai_nom']} ({int(row['code_terrai'])})"
                            for _, row in dados_ti.iterrows()
                        }

                        # Unidades de Conservação
                        uc_codigo_para_label = {
                            str(row["code_conservation_unit"]): f"{row['name_conservation_unit']} ({row['code_conservation_unit']})"
                            for _, row in dados_uc.iterrows()
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
                            str(row["codigo"]): f"{row['nome']} ({row['codigo']})"
                            for _, row in dados_bacias_micro.iterrows()
                        }
                        bacia_meso_codigo_para_label = {
                            str(row["codigo"]): f"{row['nome']} ({row['codigo']})"
                            for _, row in dados_bacias_meso.iterrows()
                        }
                        bacia_macro_codigo_para_label = {
                            str(row["codigo"]): f"{row['nome']} ({row['codigo']})"
                            for _, row in dados_bacias_macro.iterrows()
                        }

                        # -------------------- VALORES PADRÃO (REGIÕES JÁ CADASTRADAS) --------------------
                        regioes = projeto.get("regioes_atuacao", [])

                        ufs_default = [r["codigo"] for r in regioes if r["tipo"] == "uf"]
                        muni_default = [r["codigo"] for r in regioes if r["tipo"] == "municipio"]
                        biomas_default = [r["codigo"] for r in regioes if r["tipo"] == "bioma"]
                        ti_default = [r["codigo"] for r in regioes if r["tipo"] == "terra_indigena"]
                        uc_default = [r["codigo"] for r in regioes if r["tipo"] == "uc"]
                        assent_default = [r["codigo"] for r in regioes if r["tipo"] == "assentamento"]
                        quilombo_default = [r["codigo"] for r in regioes if r["tipo"] == "quilombo"]
                        bacia_micro_default = [r["codigo"] for r in regioes if r["tipo"] == "bacia_micro"]
                        bacia_meso_default = [r["codigo"] for r in regioes if r["tipo"] == "bacia_meso"]
                        bacia_macro_default = [r["codigo"] for r in regioes if r["tipo"] == "bacia_macro"]

                        # ----------------------- ESTADOS, MUNICÍPIOS E BIOMAS -----------------------
                        col1, col2, col3 = st.columns(3)

                        ufs_selecionadas = col1.multiselect(
                            "Estados",
                            options=list(uf_codigo_para_label.values()),
                            default=[uf_codigo_para_label[c] for c in ufs_default if c in uf_codigo_para_label],
                            placeholder=""
                        )

                        municipios_selecionadas = col2.multiselect(
                            "Municípios",
                            options=list(municipios_codigo_para_label.values()),
                            default=[municipios_codigo_para_label[c] for c in muni_default if c in municipios_codigo_para_label],
                            placeholder=""
                        )

                        biomas_selecionados = col3.multiselect(
                            "Biomas",
                            options=list(biomas_codigo_para_label.values()),
                            default=[biomas_codigo_para_label[c] for c in biomas_default if c in biomas_codigo_para_label],
                            placeholder=""
                        )

                        # ----------------------- TERRAS INDÍGENAS E UCs -----------------------
                        col1, col2 = st.columns(2)

                        tis_selecionadas = col1.multiselect(
                            "Terras Indígenas",
                            options=list(ti_codigo_para_label.values()),
                            default=[ti_codigo_para_label[c] for c in ti_default if c in ti_codigo_para_label],
                            placeholder=""
                        )

                        ucs_selecionadas = col2.multiselect(
                            "Unidades de Conservação",
                            options=list(uc_codigo_para_label.values()),
                            default=[uc_codigo_para_label[c] for c in uc_default if c in uc_codigo_para_label],
                            placeholder=""
                        )

                        # ----------------------- ASSENTAMENTOS E QUILOMBOS -----------------------
                        col1, col2 = st.columns(2)

                        assentamentos_selecionados = col1.multiselect(
                            "Assentamentos",
                            options=list(assent_codigo_para_label.values()),
                            default=[assent_codigo_para_label[c] for c in assent_default if c in assent_codigo_para_label],
                            placeholder=""
                        )

                        quilombos_selecionados = col2.multiselect(
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


                        st.write('')

                        # Botão de salvar
                        submit = st.form_submit_button("Salvar", icon=":material/save:", type="primary", width=200)
                        if submit:
                            # Converter coordenador, doador e programa para ObjectId antes de salvar
                            coordenador_objid = bson.ObjectId(coordenador) if coordenador else None
                            doador_objid = bson.ObjectId(doador) if doador else None
                            programa_objid = bson.ObjectId(programa) if programa else None


                            # Checar duplicidade de sigla
                            sigla_existente = ((df_projetos_ispn["sigla"] == sigla) & (df_projetos_ispn["_id"] != projeto_info["_id"])).any()

                            # Checar duplicidade de código
                            codigo_existente = ((df_projetos_ispn["codigo"] == codigo) & (df_projetos_ispn["_id"] != projeto_info["_id"])).any()

                            if sigla_existente:
                                st.warning(f"A sigla '{sigla}' já está cadastrada em outro projeto. Escolha outra.")
                            elif codigo_existente:
                                st.warning(f"O código '{codigo}' já está cadastrado em outro projeto. Escolha outro.")
                            else:

                                # Função auxiliar
                                def get_codigo_por_label(dicionario, valor):
                                    return next((codigo for codigo, label in dicionario.items() if label == valor), None)

                                regioes_atuacao = []

                                # Tipos simples com lookup
                                for tipo, selecionados, dicionario in [
                                    ("uf", ufs_selecionadas, uf_codigo_para_label),
                                    ("municipio", municipios_selecionadas, municipios_codigo_para_label),
                                    ("bioma", biomas_selecionados, biomas_codigo_para_label),
                                    ("terra_indigena", tis_selecionadas, ti_codigo_para_label),
                                    ("uc", ucs_selecionadas, uc_codigo_para_label),
                                    ("assentamento", assentamentos_selecionados, assent_codigo_para_label),
                                    ("quilombo", quilombos_selecionados, quilombo_codigo_para_label),
                                    ("bacia_micro", bacias_micro_sel, bacia_micro_codigo_para_label),
                                    ("bacia_meso", bacias_meso_sel, bacia_meso_codigo_para_label),
                                    ("bacia_macro", bacias_macro_sel, bacia_macro_codigo_para_label),
                                ]:
                                    for item in selecionados:
                                        codigo_atuacao = get_codigo_por_label(dicionario, item)
                                        if codigo_atuacao:
                                            regioes_atuacao.append({"tipo": tipo, "codigo": codigo_atuacao})

                                # Agora salva no MongoDB
                                update_doc = {
                                    "codigo": codigo,
                                    "sigla": sigla,
                                    "nome_do_projeto": nome_do_projeto,
                                    "moeda": moeda,
                                    "valor": float_to_br(valor),
                                    "valor_da_contrapartida_em_r$": float_to_br(contrapartida),
                                    "coordenador": coordenador_objid,
                                    "doador": doador_objid,
                                    "programa": programa_objid,
                                    "status": status,
                                    "data_inicio_contrato": data_inicio.strftime("%d/%m/%Y"),
                                    "data_fim_contrato": data_fim.strftime("%d/%m/%Y"),
                                    "objetivo_geral": objetivo_geral,
                                    "regioes_atuacao": regioes_atuacao
                                }

                                projetos_ispn.update_one({"_id": projeto_info["_id"]}, {"$set": update_doc})
                                st.success("Projeto atualizado com sucesso!")
                                time.sleep(3)
                                st.rerun()

                # ==============================================================
                # ABA 2 - ENTREGAS
                # ==============================================================

                with aba2:
                    #st.subheader("Cadastrar ou editar entregas do projeto")
                    
                    #st.write("")

                    entregas_existentes = projeto_info.get("entregas", [])
                    # Garante que entregas_existentes seja sempre uma lista
                    if not isinstance(entregas_existentes, list):
                        entregas_existentes = []
                        
                    dados_estrategia = list(estrategia.find({}))
                    dados_programas = list(programas.find({}))
                    
                    resultados_medio = []
                    resultados_longo = []
                    eixos_da_estrategia = []
                    acoes_estrategicas_dict = {}

                    for doc in dados_programas:
                        nome_programa = doc.get("nome_programa_area", "Sem programa")
                        if "acoes_estrategicas" in doc:
                            for a in doc["acoes_estrategicas"]:
                                acao = a.get("acao_estrategica")
                                if acao:
                                    texto_exibido = f"{acao} ({nome_programa})"
                                    acoes_estrategicas_dict[texto_exibido] = acao

                    for doc in dados_estrategia:
                        if "resultados_medio_prazo" in doc:
                            resultados_medio.extend(
                                [r.get("titulo") for r in doc["resultados_medio_prazo"].get("resultados_mp", []) if r.get("titulo")]
                            )
                        if "resultados_longo_prazo" in doc:
                            resultados_longo.extend(
                                [r.get("titulo") for r in doc["resultados_longo_prazo"].get("resultados_lp", []) if r.get("titulo")]
                            )
                        if "estrategia" in doc:
                            eixos_da_estrategia.extend(
                                [e.get("titulo") for e in doc["estrategia"].get("eixos_da_estrategia", []) if e.get("titulo")]
                            )
                        
                    # 🔹 Criar lista de opções (nome + _id) ordenadas alfabeticamente
                    df_pessoas_ordenado = df_pessoas.sort_values("nome_completo", ascending=True)
                    responsaveis_dict = {
                        str(row["_id"]): row["nome_completo"]
                        for _, row in df_pessoas_ordenado.iterrows()
                    }
                    responsaveis_options = list(responsaveis_dict.keys())
                    

                    with st.expander("Adicionar entrega", expanded=False):
                        with st.form("form_nova_entrega", border=False):
                            
                            nome_da_entrega = st.text_input("Nome da entrega")
                            
                            col1, col2 = st.columns(2)
                            
                            previsao_da_conclusao = col1.date_input("Previsão de conclusão", format="DD/MM/YYYY")
                            
                            responsaveis_selecionados = col2.multiselect(
                                "Responsáveis",
                                options=responsaveis_options,
                                format_func=lambda x: responsaveis_dict.get(x, "Desconhecido"),
                                placeholder=""
                            )
                            
                            col1, col2 = st.columns(2)
                            
                            situacao = col1.selectbox("Situação", ["Prevista", "Atrasada", "Concluída"])
                            anos_de_referencia = col2.text_input("Anos de referência (separar por vírgula)")
                            
                            resultados_medio_prazo_relacionados = st.multiselect(
                                "Contribui com quais resultados de médio prazo?",
                                options=resultados_medio,
                                placeholder=""
                            )
                            resultados_longo_prazo_relacionados = st.multiselect(
                                "Contribui com quais resultados de longo prazo?",
                                options=resultados_longo,
                                placeholder=""
                            )
                            eixos_relacionados = st.multiselect(
                                "Contribui com quais eixos da estratégia PPP-ECOS?",
                                options=eixos_da_estrategia,
                                placeholder=""
                            )
                            acoes_relacionados = st.multiselect(
                                "Contribui com quais ações estratégicas dos programas?",
                                options=list(acoes_estrategicas_dict.keys()),
                                placeholder=""
                            )
                            
                            anotacoes = st.text_area("Anotações")
                            
                            st.write("")
                            
                            salvar_nova = st.form_submit_button("Salvar entrega", icon=":material/save:")
                            if salvar_nova:
                                
                                if not nome_da_entrega:
                                    st.warning("Por favor preencha o nome da entrega.")
                                
                                else:
                                    
                                    acoes_puras = [acoes_estrategicas_dict[a] for a in acoes_relacionados]
                                
                                    nova_entrega = {
                                        "nome_da_entrega": nome_da_entrega,
                                        "previsao_da_conclusao": previsao_da_conclusao.strftime("%d/%m/%Y"),
                                        "responsaveis": [ObjectId(r) for r in responsaveis_selecionados],
                                        "anotacoes": anotacoes,
                                        "situacao": situacao,
                                        "anos_de_referencia": [a.strip() for a in anos_de_referencia.split(",") if a.strip()],
                                        "resultados_medio_prazo_relacionados": resultados_medio_prazo_relacionados,
                                        "resultados_longo_prazo_relacionados": resultados_longo_prazo_relacionados,
                                        "eixos_relacionados": eixos_relacionados,
                                        "acoes_relacionadas": acoes_puras
                                    }

                                    # adiciona ao array existente
                                    entregas_atualizadas = entregas_existentes + [nova_entrega]
                                    projetos_ispn.update_one(
                                        {"_id": projeto_info["_id"]},
                                        {"$push": {"entregas": nova_entrega}}
                                    )

                                    st.success("Entrega adicionada com sucesso!")
                                    time.sleep(2)
                                    st.rerun()
                    
                    st.write("")

                    # ============================
                    # EXIBIR ENTREGAS EXISTENTES
                    # ============================
                    if entregas_existentes:
                        st.write("### Entregas cadastradas:")

                        for i, entrega in enumerate(entregas_existentes):
                            with st.expander(f"{entrega.get('nome_da_entrega', 'Sem nome')}"):
                                # Mostrar nomes reais dos responsáveis
                                responsaveis_ids = entrega.get("responsaveis", [])
                                responsaveis_nomes = [
                                    responsaveis_dict.get(str(r), "Desconhecido") for r in responsaveis_ids
                                ]
                                responsaveis_formatados = ", ".join(responsaveis_nomes) if responsaveis_nomes else "-"

                                # Alternar entre visualização e edição
                                modo_edicao = st.toggle("Modo de edição", key=f"toggle_edit_{i}")

                                if not modo_edicao:
                                    # --- Modo de visualização ---
                                    st.write(f"**Previsão:** {entrega.get('previsao_da_conclusao', '-')}")
                                    st.write(f"**Responsáveis:** {responsaveis_formatados}")
                                    st.write(f"**Situação:** {entrega.get('situacao', '-')}")
                                    st.write(f"**Anos de referência:** {', '.join(entrega.get('anos_de_referencia', []))}")
                                    
                                    st.write("")

                                    # 🔹 Resultados de médio prazo
                                    resultados_medio = entrega.get("resultados_medio_prazo_relacionados", [])
                                    if resultados_medio:
                                        st.markdown("**Resultados de médio prazo:**")
                                        for r in resultados_medio:
                                            st.markdown(f"- {r}")
                                    else:
                                        st.markdown("**Resultados de médio prazo:** -")

                                    st.write("")

                                    # 🔹 Resultados de longo prazo
                                    resultados_longo = entrega.get("resultados_longo_prazo_relacionados", [])
                                    if resultados_longo:
                                        st.markdown("**Resultados de longo prazo:**")
                                        for r in resultados_longo:
                                            st.markdown(f"- {r}")
                                    else:
                                        st.markdown("**Resultados de longo prazo:** -")

                                    st.write("")

                                    # 🔹 Eixos estratégicos
                                    eixos = entrega.get("eixos_relacionados", [])
                                    if eixos:
                                        st.markdown("**Eixos estratégicos:**")
                                        for e in eixos:
                                            st.markdown(f"- {e}")
                                    else:
                                        st.markdown("**Eixos estratégicos:** -")
                                        
                                    st.write("")

                                    # 🔹 Ações estratégicas
                                    acoes = entrega.get("acoes_relacionadas", [])
                                    if acoes:
                                        st.markdown("**Ações estratégicas:**")
                                        for a in acoes:
                                            st.markdown(f"- {a}")
                                    else:
                                        st.markdown("**Ações estratégicas:** -")
                                    
                                    st.write("")

                                    st.markdown(f"**Anotações:** {entrega.get('anotacoes', '-')}")

                                    # col1, col2 = st.columns([1, 1])
                                    # if col2.button("Excluir", key=f"del_{i}"):
                                    #     entregas_existentes.pop(i)
                                    #     projetos_ispn.update_one(
                                    #         {"_id": projeto_info["_id"]},
                                    #         {"$set": {"entregas": entregas_existentes}}
                                    #     )
                                    #     st.success("Entrega removida.")
                                    #     st.rerun()

                                else:
                                    # --- Modo de edição ---
                                    with st.form(f"form_edit_entrega_{i}", border=False):
                                        entrega_editada = {**entrega}

                                        entrega_editada["nome_da_entrega"] = st.text_input(
                                            "Nome da entrega", entrega.get("nome_da_entrega", "")
                                        )
                                        
                                        col1, col2 = st.columns(2)

                                        entrega_editada["previsao_da_conclusao"] = col1.date_input(
                                            "Previsão de conclusão",
                                            pd.to_datetime(entrega.get("previsao_da_conclusao"), format="%d/%m/%Y").date()
                                            if entrega.get("previsao_da_conclusao") else datetime.today(),
                                            format="DD/MM/YYYY"
                                        )
                                        entrega_editada["previsao_da_conclusao"] = entrega_editada["previsao_da_conclusao"].strftime("%d/%m/%Y")

                                        responsaveis_existentes = [str(r) for r in entrega.get("responsaveis", [])]
                                        entrega_editada["responsaveis"] = col2.multiselect(
                                            "Responsáveis",
                                            options=list(responsaveis_dict.keys()),
                                            default=responsaveis_existentes,
                                            format_func=lambda x: responsaveis_dict.get(x, "Desconhecido"),
                                            placeholder="Selecione os responsáveis"
                                        )

                                        
                                        col1, col2 = st.columns(2)

                                        entrega_editada["situacao"] = col1.selectbox(
                                            "Situação",
                                            ["Prevista", "Atrasada", "Concluída"],
                                            index=["Prevista", "Atrasada", "Concluída"].index(
                                                entrega.get("situacao", "Prevista")
                                            )
                                        )

                                        entrega_editada["anos_de_referencia"] = col2.text_input(
                                            "Anos de referência (separar por vírgula)",
                                            ", ".join(entrega.get("anos_de_referencia", []))
                                        )

                                        entrega_editada["resultados_medio_prazo_relacionados"] = st.multiselect(
                                            "Contribui com quais resultados de médio prazo?",
                                            options=resultados_medio,
                                            default=entrega.get("resultados_medio_prazo_relacionados", []),
                                            placeholder=""
                                        )

                                        entrega_editada["resultados_longo_prazo_relacionados"] = st.multiselect(
                                            "Contribui com quais resultados de longo prazo?",
                                            options=resultados_longo,
                                            default=entrega.get("resultados_longo_prazo_relacionados", []),
                                            placeholder=""
                                        )

                                        entrega_editada["eixos_relacionados"] = st.multiselect(
                                            "Contribui com quais eixos da estratégia PPP-ECOS?",
                                            options=eixos_da_estrategia,
                                            default=entrega.get("eixos_relacionados", []),
                                            placeholder=""
                                        )

                                        acoes_selecionadas_labels = [
                                            label for label, valor in acoes_estrategicas_dict.items()
                                            if valor in entrega.get("acoes_relacionadas", [])
                                        ]

                                        acoes_selecionadas_labels = st.multiselect(
                                            "Contribui com quais ações estratégicas dos programas?",
                                            options=list(acoes_estrategicas_dict.keys()),
                                            default=acoes_selecionadas_labels,
                                            placeholder=""
                                        )

                                        # Converter de volta para o valor puro (sem o nome do programa)
                                        entrega_editada["acoes_relacionadas"] = [
                                            acoes_estrategicas_dict[label] for label in acoes_selecionadas_labels
                                        ]
                                        
                                        entrega_editada["anotacoes"] = st.text_area("Anotações", entrega.get("anotacoes", ""))
                                        
                                        st.write("")

                                        salvar_edicao = st.form_submit_button("Salvar alterações")
                                        if salvar_edicao:
                                            entrega_editada["anos_de_referencia"] = [
                                                a.strip() for a in entrega_editada["anos_de_referencia"].split(",") if a.strip()
                                            ]
                                            
                                            entrega_editada["responsaveis"] = [ObjectId(r) for r in entrega_editada["responsaveis"]]

                                            entregas_existentes[i] = entrega_editada
                                            projetos_ispn.update_one(
                                                {"_id": projeto_info["_id"]},
                                                {"$set": {"entregas": entregas_existentes}}
                                            )
                                            st.success("Entrega atualizada!")
                                            time.sleep(2)
                                            st.rerun()


            # with st.container(horizontal=True):
            st.button('Gerenciar projeto', width=300, icon=":material/contract_edit:", on_click=dialog_editar_projeto)




    # ------------------------------------------

    # Nome do projeto
    st.subheader(
        "**" + 
        df_projetos_ispn.loc[
            df_projetos_ispn['sigla'] == projeto_selecionado, 
            'nome_do_projeto'
        ].squeeze() + 
        "**"
    )

    st.write('')

    col1, col2 = st.columns(2)


    # Valor e contrapartida
 
    col1.write('')
    col1.metric("**Valor:**", df_projetos_ispn.loc[df_projetos_ispn['sigla'] == projeto_selecionado, 'valor_com_moeda'].values[0])
    col1.write('')
    

    col2.write('')
    col2.metric(
    "**Contrapartida:**",
    "R$ " + str(df_projetos_ispn.loc[
        df_projetos_ispn['sigla'] == projeto_selecionado,
        'valor_da_contrapartida_em_r$'
    ].values[0])
    )
    col2.write('')
    

    st.write('')

    # Coordenador
    coordenador_id = projeto_info["coordenador"].values[0] if not projeto_info.empty else ""
    coordenador_nome = mapa_coordenador.get(coordenador_id, "")  # retorna string vazia se não achar
    col1.write(f'**Coordenador(a):** {coordenador_nome}')

    # Doador e Programa
    doador = projeto_info["doador_nome"].values[0] if not projeto_info.empty else ""
    programa = projeto_info["programa_nome"].values[0] if not projeto_info.empty else ""
    col1.write(f'**Doador:** {doador}')
    col1.write(f'**Programa:** {programa}')



    # Situação
    col2.write(f'**Situação:** {df_projetos_ispn.loc[df_projetos_ispn["sigla"] == projeto_selecionado, "status"].values[0]}')

    # Datas de início e término
    data_inicio = df_projetos_ispn.loc[df_projetos_ispn["sigla"] == projeto_selecionado, "data_inicio_contrato"].dt.strftime("%d/%m/%Y").values[0]
    data_fim = df_projetos_ispn.loc[df_projetos_ispn["sigla"] == projeto_selecionado, "data_fim_contrato"].dt.strftime("%d/%m/%Y").values[0]
    col2.write(f'**Data de início:** {data_inicio}')
    col2.write(f'**Data de término:** {data_fim}')



    # Objetivo geral
    objetivo_geral = df_projetos_ispn.loc[
        df_projetos_ispn["sigla"] == projeto_selecionado, "objetivo_geral"
    ].values[0]
    # Verificando se é NaN ou vazio
    if pd.isna(objetivo_geral) or objetivo_geral == "":
        objetivo_geral = "_Não cadastrado_"
    st.write(f'**Objetivo geral:** {objetivo_geral}')

    st.write('')

    # Obter o _id do projeto selecionado
    projeto_id = df_projetos_ispn.loc[
        df_projetos_ispn["sigla"] == projeto_selecionado, "_id"
    ].values[0]




    # ABAS
    tab_equipe, tab_indicadores, tab_entregas, tab_anotacoes = st.tabs([":material/group: Equipe", ":material/show_chart: Indicadores", ":material/show_chart: Entregas", ":material/notes: Anotações"])




    # ##########################################################
    # Equipe do projeto
    # ##########################################################

    with tab_equipe:

        st.write('**Equipe contratada pelo projeto:**')

        # # 1- Obter o _id do projeto selecionado
        # projeto_id = df_projetos_ispn.loc[
        #     df_projetos_ispn["sigla"] == projeto_selecionado, "_id"
        # ].values[0]

        # 2- Filtrar pessoas que têm pelo menos um contrato com esse projeto
        def pertence_ao_projeto(contratos):
            if not isinstance(contratos, list):
                return False
            for c in contratos:
                if c.get("status_contrato") == "Em vigência":
                    # projeto_pagador já convertido em string se você aplicou a função anterior
                    ids = [str(p) for p in c.get("projeto_pagador", [])]
                    if str(projeto_id) in ids:
                        return True
            return False

        df_equipe = df_pessoas[df_pessoas["contratos"].apply(pertence_ao_projeto)].copy()

        # 3- Criar coluna 'datas_fim_contrato' com todas as datas de fim de contratos em vigência
        def datas_fim_em_vigencia(contratos):
            if not isinstance(contratos, list):
                return ""
            datas = [c['data_fim'] for c in contratos if c.get('status_contrato') == 'Em vigência']
            return ", ".join(datas)

        df_equipe['datas_fim_contrato'] = df_equipe['contratos'].apply(datas_fim_em_vigencia)

        # 4- Exibição
        colunas_exibir = [
            "nome_completo",
            "programa_area_nome",
            "coordenador_nome",
            "escritorio",
            "cargo",
            "tipo_contratacao",
            "datas_fim_contrato",
            "status",
        ]

        # Novo nome das colunas
        novos_nomes = {
            "nome_completo": "Nome",
            "programa_area_nome": "Programa / Área",
            "status": "Status",
            "coordenador_nome": "Coordenador(a)",
            "cargo": "Cargo",
            "tipo_contratacao": "Tipo de Contratação",
            "escritorio": "Escritório",
            "datas_fim_contrato": "Data de fim do contrato"
        }

        # Exibir somente essas colunas com os nomes renomeados
        if df_equipe.empty:
            st.write("_Não há equipe cadastrada para este projeto_")
        else:
            st.dataframe(
                df_equipe[colunas_exibir]
                .rename(columns=novos_nomes)
                .reset_index(drop=True),
                hide_index=True
            )

        st.write('')




    # ##########################################################
    # Indicadores
    # ##########################################################

    with tab_indicadores:
        st.write('**Indicadores do projeto:** (não inclui indicadores de projetos apoiados ou "grants")')


        # Tratamento dos dados

        autor_nome = st.session_state.get("nome", "")
        tipo_usuario = st.session_state.get("tipo_usuario", [])
        projeto_id = projeto_info["_id"].iloc[0]   # pega o valor da célula
        projeto_id = bson.ObjectId(projeto_id)     # garante que é ObjectId

        lancamentos = list(db["lancamentos_indicadores"].find({"projeto": projeto_id}))


        linhas = []
        if not lancamentos:
            st.info("Não há lançamentos de indicadores para este projeto.")
        else:
            
            for lan in lancamentos:
                ind_id = lan.get("id_do_indicador")
    
                # Garantir que seja ObjectId para consulta
                if isinstance(ind_id, str):
                    try:
                        ind_id_obj = bson.ObjectId(ind_id)
                    except Exception:
                        ind_id_obj = None
                elif isinstance(ind_id, bson.ObjectId):
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

                linhas.append({
                    "Indicador": nome_legivel_traduzido,
                    "Valor": lan.get("valor", ""),
                    "Ano": lan.get("ano", ""),
                    "Autor(a)": lan.get("autor_anotacao", ""),
                    "Observações": lan.get("observacoes", ""),
                    "Data anotação": lan.get("data_anotacao", ""),
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



        # Interface dos indicadores-------------------------------------------------------------

        # ====================
        # Função do diálogo de indicadores
        # ====================
        @st.dialog("Gerenciar indicadores")
        def dialog_indicadores():

            # Aumentar largura do diálogo com css
            st.html("<span class='big-dialog'></span>")

            # Carrega indicadores
            indicadores_lista = list(db["indicadores"].find({}, {"_id": 1, "nome_indicador": 1}))
            indicadores_opcoes = {
                nomes_legiveis.get(i["nome_indicador"], i["nome_indicador"]): i
                for i in indicadores_lista
            }


            tab_add, tab_edit, tab_delete = st.tabs([
                ":material/add: Adicionar",
                ":material/edit: Editar",
                ":material/delete: Excluir"
            ])

            # ------------------------- ABA ADICIONAR -------------------------
            with tab_add:
                st.subheader("Novo lançamento de indicador")

                # indicadores_lista = list(indicadores.find({}, {"_id": 1, "nome_indicador": 1}))
                # indicadores_opcoes = {
                #     nomes_legiveis.get(i["nome_indicador"], i["nome_indicador"]): i
                #     for i in indicadores_lista
                # }

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

                        submit = st.form_submit_button(":material/save: Salvar lançamento", type="primary")

                    if submit:
                        if not autor_nome:
                            st.warning("Nome do autor não encontrado.")
                            st.stop()

                        if tipo_valor == "float":
                            valor = float(valor)
                        elif tipo_valor == "int":
                            valor = int(valor)

                      
                        novo_lancamento = {
                            "id_do_indicador": indicador_oid,
                            "projeto": bson.ObjectId(projeto_id),
                            "valor": valor,
                            "ano": str(ano),
                            "observacoes": observacoes,
                            "autor_anotacao": autor_nome,
                            "data_anotacao": datetime.datetime.now(),
                            "tipo": "ispn"
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
                    colecao_lancamentos.find({"projeto": bson.ObjectId(projeto_id)}).sort("data_anotacao", -1)
                )

                if "admin" not in tipo_usuario:
                    lancamentos_proj = [l for l in lancamentos_proj if l.get("autor_anotacao") == autor_nome]

                if not lancamentos_proj:
                    st.info("Nenhum lançamento disponível para edição.")
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

                    lanc_sel = st.selectbox("Selecione o lançamento", [""] + list(lanc_opcoes.keys()), key=f"select_lanc_{bson.ObjectId(projeto_id)}")

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

                        if st.button(":material/save: Salvar alterações", type="primary"):
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
                    colecao_lancamentos.find({"projeto": bson.ObjectId(projeto_id)}).sort("data_anotacao", -1)
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

                        if st.button("Excluir", icon=":material/delete:"):
                            colecao_lancamentos.delete_one({"_id": lanc_id})
                            st.success("Lançamento excluído com sucesso!")
                            st.cache_data.clear()
                            st.rerun()

        # ====================
        # Botão para abrir o diálogo de Gerenciar indicadores
        # ====================
        
        with st.container(horizontal=True, horizontal_alignment="right"):
            
            if st.button("Gerenciar indicadores", icon=":material/edit:", width=300):
                dialog_indicadores()





        # ====================
        # Toggle para ver consolidado ou todos os lançamentos
        # ====================

        ver_lancamentos = st.toggle("Ver lançamentos detalhados")

        st.write('')





        # Renderização da tabela dataframe

        # Por padrão, mostra o consolidado
        if not ver_lancamentos:
            
            st.write('**MOSTRANDO INDICADORES CONSOLIDADOS (NÚMEROS SOMADOS):**')
            st.write('')

            ui.table(data=df_resumo.drop(columns=["Valor_num"], errors="ignore"))

            # ajustar_altura_dataframe(df_resumo.drop(columns=["Valor_num"], errors="ignore"), 
            #                             linhas_adicionais=1,
            #                             hide_index=True, 
            #                             use_container_width=True
            #                             )            

        # Ao acionar o toggle, mostra todos os lançamentos detalhados
        else:
            
            st.write('**MOSTRANDO TODOS OS LANÇAMENTOS DE INDICADORES:**')
            st.write('')

            # ui.table(data=df_indicadores.drop(columns=["Valor_num"], errors="ignore"))

            ajustar_altura_dataframe(df_indicadores.drop(columns=["Valor_num"], errors="ignore"), 
                                        linhas_adicionais=1,
                                        hide_index=True, 
                                        use_container_width='stretch')


    # ##########################################################
    # Entregas
    # ##########################################################


    with tab_entregas:
        st.write("")

        # Obter o documento completo do projeto selecionado
        projeto_doc = projetos_ispn.find_one({"_id": projeto_id})

        # Obter lista de entregas (ou lista vazia se não houver)
        entregas = projeto_doc.get("entregas", [])

        if not entregas:
            st.write("_Não há entregas cadastradas para este projeto._")
        else:
            # Criar dicionário de ObjectId -> nome_completo dos responsáveis
            df_pessoas_ordenado = df_pessoas.sort_values("nome_completo", ascending=True)
            responsaveis_dict = {
                str(row["_id"]): row["nome_completo"]
                for _, row in df_pessoas_ordenado.iterrows()
            }

            # Montar lista com apenas as colunas desejadas
            dados_entregas = []
            for entrega in entregas:
                responsaveis_ids = [
                    str(r.get("$oid")) if isinstance(r, dict) else str(r)
                    for r in entrega.get("responsaveis", [])
                ]
                responsaveis_nomes = [
                    responsaveis_dict.get(rid, f"ID não encontrado: {rid}")
                    for rid in responsaveis_ids
                ]
                dados_entregas.append({
                    "Entregas": entrega.get("nome_da_entrega", "-"),
                    "Previsão de Conclusão": entrega.get("previsao_da_conclusao", "-"),
                    "Responsáveis": ", ".join(responsaveis_nomes) if responsaveis_nomes else "-",
                    "Situação": entrega.get("situacao", "-"),
                    "Anos de Referência": ", ".join(entrega.get("anos_de_referencia", [])),
                    "Anotações": entrega.get("anotacoes", "-")
                })

            # Converter para DataFrame e exibir como tabela
            df_entregas = pd.DataFrame(dados_entregas)

            # ===============================================================
            # FILTROS
            # ===============================================================
            #st.subheader("Filtros")

            col1, col2 = st.columns(2)

            # Opções únicas para filtros
            situacoes = sorted(df_entregas["Situação"].dropna().unique().tolist())
            anos_disponiveis = sorted(
                set(
                    ano.strip()
                    for sublist in df_entregas["Anos de Referência"].dropna()
                    for ano in sublist.split(",")
                )
            )

            with col1:
                filtro_situacao = st.multiselect(
                    "Filtrar por Situação:",
                    options=situacoes,
                    default=[],
                    placeholder="",
                )

            with col2:
                filtro_ano = st.multiselect(
                    "Filtrar por Ano de Referência:",
                    options=anos_disponiveis,
                    default=[],
                    placeholder="",
                )

            # Aplicar filtros
            df_filtrado = df_entregas.copy()

            if filtro_situacao:
                df_filtrado = df_filtrado[df_filtrado["Situação"].isin(filtro_situacao)]

            if filtro_ano:
                df_filtrado = df_filtrado[
                    df_filtrado["Anos de Referência"].apply(
                        lambda x: any(ano in x for ano in filtro_ano)
                    )
                ]

            # ===============================================================
            # EXIBIÇÃO DA TABELA
            # ===============================================================

            st.write('')
            ui.table(data=df_filtrado)




    # ##########################################################
    # Anotações
    # ##########################################################

    with tab_anotacoes:
        st.write('**Anotações:**')

        # ====================
        # Função do diálogo
        # ====================
        @st.dialog("Gerenciar Anotações")
        def dialog_anotacoes():
            tab1, tab2, tab3 = st.tabs([":material/add: Nova anotação", ":material/edit: Editar", ":material/delete: Apagar"])

            # ====================
            # ABA 1: Cadastrar
            # ====================
            with tab1:
                with st.form("form_cadastrar_anotacao"):
                    hoje = datetime.datetime.today().strftime("%d/%m/%Y")

                    st.write(f"Data: {hoje}")

                    anotacao_texto = st.text_area("Anotação")

                    submit = st.form_submit_button("Salvar anotação", icon=':material/save:', type="primary")

                    if submit:
                        if not anotacao_texto.strip():
                            st.warning("A anotação não pode estar vazia.")
                        else:
                            # Buscar _id do projeto
                            projeto = projetos_ispn.find_one({"sigla": projeto_selecionado})
                            if not projeto:
                                st.error("Projeto não encontrado no banco de dados.")
                            else:
                                nova_anotacao = {
                                    "data_anotacao": datetime.datetime.today(),
                                    "autor": st.session_state.get("nome", "Desconhecido"),
                                    "anotacao": anotacao_texto.strip()
                                }

                                # Atualiza o projeto adicionando a nova anotação
                                projetos_ispn.update_one(
                                    {"_id": projeto["_id"]},
                                    {"$push": {"anotacoes": nova_anotacao}}
                                )
                                st.success("Anotação cadastrada com sucesso!")
                                time.sleep(3)
                                st.rerun()

            # ====================
            # ABA 2: Editar
            # ====================
            with tab2:
                projeto = projetos_ispn.find_one({"sigla": projeto_selecionado})
                
                if not projeto or "anotacoes" not in projeto or len(projeto["anotacoes"]) == 0:
                    st.write("_Não há anotações para editar._")
                else:
                    anotacoes = projeto["anotacoes"]
                    usuario_logado = st.session_state.get("nome", "Desconhecido")
                    
                    # Criar lista de opções com apenas anotações do próprio usuário
                    opcoes = [
                        f'{a["data_anotacao"].strftime("%d/%m/%Y") if isinstance(a["data_anotacao"], datetime.datetime) else a["data_anotacao"]} - {a["anotacao"][:30]}...'
                        for a in anotacoes if a.get("autor") == usuario_logado
                    ]
                    
                    if not opcoes:
                        st.write("_Você não possui anotações para editar._")
                    else:
                        # Adiciona opção vazia no início
                        opcoes_com_vazio = [""] + opcoes
                        
                        # Selecionar anotação (valor padrão vazio)
                        selecionada = st.selectbox(
                            "Selecione a anotação para editar",
                            options=opcoes_com_vazio,
                            index=0
                        )
                        
                        if selecionada:  # só prosseguir se o usuário selecionar algo
                            # Índice real dentro da lista completa de anotações
                            index = [i for i, a in enumerate(anotacoes) if a.get("autor") == usuario_logado][opcoes.index(selecionada)]
                            anotacao_atual = anotacoes[index]["anotacao"]
                            
                            # Campo para editar
                            nova_texto = st.text_area("Editar anotação", value=anotacao_atual)
                            
                            if st.button("Salvar alterações", icon=":material/save:", type="primary"):
                                if not nova_texto.strip():
                                    st.warning("A anotação não pode ficar vazia.")
                                else:
                                    # Atualizar a anotação no MongoDB
                                    projetos_ispn.update_one(
                                        {"_id": projeto["_id"]},
                                        {"$set": {f"anotacoes.{index}.anotacao": nova_texto.strip()}}
                                    )
                                    st.success("Anotação editada com sucesso!")
                                    time.sleep(3)  # pausa antes do rerun
                                    st.rerun()




            # ====================
            # ABA 3: Apagar
            # ====================
            with tab3:
                projeto = projetos_ispn.find_one({"sigla": projeto_selecionado})
                usuario_logado = st.session_state.get("nome", "Desconhecido")
                
                if not projeto or "anotacoes" not in projeto or len(projeto["anotacoes"]) == 0:
                    st.write("_Não há anotações para apagar._")
                else:
                    anotacoes = projeto["anotacoes"]
                    
                    # Lista apenas anotações do próprio usuário
                    opcoes = [
                        f'{a["data_anotacao"].strftime("%d/%m/%Y") if isinstance(a["data_anotacao"], datetime.datetime) else a["data_anotacao"]} - {a["anotacao"][:30]}...'
                        for a in anotacoes if a.get("autor") == usuario_logado
                    ]
                    
                    if not opcoes:
                        st.write("_Você não possui anotações para apagar._")
                    else:
                        # Adiciona opção vazia no início
                        opcoes_com_vazio = [""] + opcoes
                        
                        selecionada = st.selectbox(
                            "Selecione a anotação para apagar",
                            options=opcoes_com_vazio,
                            index=0  # valor padrão vazio
                        )
                        
                        if selecionada:  # só prosseguir se o usuário selecionar algo
                            # Índice real dentro da lista completa de anotações
                            index = [i for i, a in enumerate(anotacoes) if a.get("autor") == usuario_logado][opcoes.index(selecionada)]
                            
                            # Passo de confirmação
                            st.warning("Você tem certeza que deseja apagar essa anotação?")
                            if st.button("Sim, apagar anotação", key="confirm_delete", icon=":material/check:"):
                                # Remover a anotação pelo índice
                                projetos_ispn.update_one(
                                    {"_id": projeto["_id"]},
                                    {"$unset": {f"anotacoes.{index}": 1}}
                                )
                                # Remover o elemento "vazio" deixado pelo $unset
                                projetos_ispn.update_one(
                                    {"_id": projeto["_id"]},
                                    {"$pull": {"anotacoes": None}}
                                )
                                st.success("Anotação apagada com sucesso!")
                                time.sleep(3)
                                st.rerun()

        # ====================
        # Botão para abrir o diálogo
        # ====================
        
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button("Gerenciar anotações", icon=":material/edit:", width=300):
                dialog_anotacoes()


        # ====================
        # Mostrar as anotações existentes
        # ====================
        projeto = projetos_ispn.find_one({"sigla": projeto_selecionado})
        if projeto and "anotacoes" in projeto:
            anotacoes = [
                [a["data_anotacao"].strftime("%d/%m/%Y") if isinstance(a["data_anotacao"], datetime.datetime) else a["data_anotacao"],
                a["anotacao"],
                a.get("autor", "Desconhecido")]
                for a in projeto["anotacoes"]
            ]
            df = pd.DataFrame(anotacoes, columns=["Data", "Anotação", "Autor"])
            ui.table(data=df)
        else:
            st.write("_Não há anotações cadastradas para este projeto._")

