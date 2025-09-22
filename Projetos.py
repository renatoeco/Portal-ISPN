import streamlit as st
import pandas as pd
import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn, ajustar_altura_dataframe, br_to_float, float_to_br
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
estatistica = db["estatistica"]  # Coleção de estatísticas
projetos_ispn = db["projetos_ispn"]  



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
    with st.expander('Cronograma'):

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
                'Em andamento': '#007ad3',
                'Finalizado':"#83C9FF",
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

        # Aumentar largura do diálogo
        st.html("<span class='big-dialog'></span>")

        with st.form("form_cadastrar_projeto"):
            # --- Colunas ---
            col1, col2, col3 = st.columns([1,1,1])

            # --- Código ---
            codigo = col1.text_input("Código", value="")

            # --- Sigla ---
            sigla = col2.text_input("Sigla", value="")

            # --- Nome do projeto ---
            nome_do_projeto = col3.text_input("Nome do Projeto", value="")

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

            # --- Status ---
            status_options = ["", "Em andamento", "Finalizado", "Pausado"]
            status = col1.selectbox("Status", options=status_options, index=0)

            # --- Datas ---
            data_inicio = col2.date_input("Data Início", value=datetime.date.today(), format="DD/MM/YYYY")
            data_fim = col3.date_input("Data Fim", value=datetime.date.today(), format="DD/MM/YYYY")

            # --- Objetivo Geral ---
            objetivo_geral = st.text_area("Objetivo Geral", value="")
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
                        "objetivo_geral": objetivo_geral
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

                projeto_info = df_projetos_ispn[df_projetos_ispn["sigla"] == projeto_selecionado].iloc[0]

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
                        "Data Início",
                        value=pd.to_datetime(projeto_info.get("data_inicio_contrato"), format="%d/%m/%Y", errors="coerce").date()
                        if projeto_info.get("data_inicio_contrato") else "datetime.date.today()",
                        format="DD/MM/YYYY"
                    )

                    data_fim = col3.date_input(
                        "Data Fim",
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
                            # Se não houver duplicidade, salva no banco
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
                                "objetivo_geral": objetivo_geral
                            }

                            projetos_ispn.update_one({"_id": projeto_info["_id"]}, {"$set": update_doc})
                            st.success("Projeto atualizado com sucesso!")
                            time.sleep(3)
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
    # st.markdown(f'**Objetivo geral:** <span style="color: orange">{objetivo_geral}</span>', unsafe_allow_html=True)



    # Equipe do projeto
    st.write('**Equipe contratada pelo projeto:**')

    # 1- Obter o _id do projeto selecionado
    projeto_id = df_projetos_ispn.loc[
        df_projetos_ispn["sigla"] == projeto_selecionado, "_id"
    ].values[0]

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

                submit = st.form_submit_button("Salvar anotação", icon=':material/save:')

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
                        
                        if st.button("Salvar alterações", icon=":material/save:"):
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
    
    with st.container(horizontal=True):
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

        