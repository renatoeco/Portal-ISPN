import streamlit as st
import pandas as pd
import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn, ajustar_altura_dataframe
import streamlit_shadcn_ui as ui
import plotly.express as px
import time




st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')




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
# Função para limpar e formatar o valor
def formatar_valor(row):
    moeda = moedas.get(row['moeda'].lower(), '')
    try:
        valor = row['valor'] if row['valor'] else 0
        valor_num = float(str(valor).replace('.', '').replace(',', '.'))
        valor_formatado = f"{valor_num:,.0f}".replace(",", ".")
        return f"{moeda} {valor_formatado}"
    except:
        return f"{moeda} 0"




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


# --- 2. Criar dicionários de mapeamento ---
mapa_doador = {d["_id"]: d["nome_doador"] for d in db["doadores"].find()}
mapa_programa = {p["_id"]: p["nome_programa_area"] for p in db["programas_areas"].find()}

# --- 3. Aplicar os mapeamentos ao df_projetos_ispn ---
df_projetos_ispn["doador_nome"] = df_projetos_ispn["doador"].map(mapa_doador)
df_projetos_ispn["programa_nome"] = df_projetos_ispn["programa"].map(mapa_programa)

# --- 4. Criar a coluna 'valor_com_moeda' ---
df_projetos_ispn['valor_com_moeda'] = df_projetos_ispn.apply(formatar_valor, axis=1)


# --- 5. Converter datas para datetime
df_projetos_ispn['data_inicio_contrato'] = pd.to_datetime(
    df_projetos_ispn['data_inicio_contrato'], format="%d/%m/%Y", errors="coerce"
)
df_projetos_ispn['data_fim_contrato'] = pd.to_datetime(
    df_projetos_ispn['data_fim_contrato'], format="%d/%m/%Y", errors="coerce"
)


# df_projetos_ispn['data_inicio_contrato'] = pd.to_datetime(df_projetos_ispn['data_inicio_contrato'])
# df_projetos_ispn['data_fim_contrato'] = pd.to_datetime(df_projetos_ispn['data_fim_contrato'])

# st.write(len(df_projetos_ispn))

# st.write(df_projetos_ispn)


# # --- 6. Considerar apenas as linhas em que há algum valor em sigla e nome_projeto
# # df_projetos_ispn = df_projetos_ispn[(df_projetos_ispn['sigla'].notnull()) & (df_projetos_ispn['nome_do_projeto'].notnull())]
# df_projetos_ispn = df_projetos_ispn[
#     (df_projetos_ispn['sigla'] == '') & 
#     (df_projetos_ispn['nome_do_projeto'] == '')
# ]

# st.write(len(df_projetos_ispn))

# st.write(df_projetos_ispn)





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
    # Converter para datetime
    # df_projetos_ispn['data_inicio_contrato'] = pd.to_datetime(df_projetos_ispn['data_inicio_contrato'])
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
    # Converter para datetime
    # df_projetos_ispn['data_fim_contrato'] = pd.to_datetime(df_projetos_ispn['data_fim_contrato'])
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
            # hover_data=['Valor'],
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

        # Movendo a legenda para baixo
        fig.update_layout(
            legend=dict(
                orientation="h",       # horizontal
                yanchor="top",
                y=10.15,                # valor positivo posiciona acima do gráfico
                xanchor="center",
                x=1
            ),
            yaxis_title=None,
            xaxis=dict(
                showgrid=True,       # grade no eixo X
                gridcolor='lightgray',  # cor da linha da grade
                tickmode='linear',
                dtick="M12",  # Mostra 1 tick por ano (12 meses)
                tickformat="%Y"  # Formata como ano, ex: 2021
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



    # df_projetos_ispn_filtrado_show['data_inicio_contrato'] = df_projetos_ispn_filtrado_show['data_inicio_contrato'].dt.strftime('%d/%m/%Y')
    # df_projetos_ispn_filtrado_show['data_fim_contrato'] = df_projetos_ispn_filtrado_show['data_fim_contrato'].dt.strftime('%d/%m/%Y')



    # # Formatando as moedas nos valores
    # # Dicionário de símbolos por moeda
    # moedas = {
    #     "reais": "R$",
    #     "real": "R$",
    #     "dólares": "US$",
    #     "dólar": "US$",
    #     "euros": "€",  # Incluído para futuro uso
    #     "euro": "€"
    # }
    # # Função para limpar e formatar o valor
    # def formatar_valor(row):
    #     moeda = moedas.get(row['moeda'].lower(), '')
    #     try:
    #         valor = row['valor'] if row['valor'] else 0
    #         valor_num = float(str(valor).replace('.', '').replace(',', '.'))
    #         valor_formatado = f"{valor_num:,.0f}".replace(",", ".")
    #         return f"{moeda} {valor_formatado}"
    #     except:
    #         return f"{moeda} 0"



    # # Aplicar a função
    # df_projetos_ispn_filtrado_show['valor_com_moeda'] = df_projetos_ispn_filtrado_show.apply(formatar_valor, axis=1)


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

    # Seleção do projeto
    projetos_selectbox = [""] + sorted(df_projetos_ispn.apply(lambda row: f"{row['sigla']} - {row['nome_do_projeto']}", axis=1).tolist())
    projeto_selecionado_concat = st.selectbox('Selecione o projeto', projetos_selectbox)


    if projeto_selecionado_concat == "":
        # st.write('Selecione um projeto')
        st.stop()
    else:
        st.divider()


    # Nome do projeto
    st.subheader(projeto_selecionado_concat)
    st.write('')

    projeto_selecionado = projeto_selecionado_concat.split(" - ")[1]
    
    # Botão de gerenciar
    
    # Roteamento de tipo de usuário especial
    if set(st.session_state.tipo_usuario) & {"admin", "gestao_projetos_doadores"}:
    
        with st.container(horizontal=True):

            st.button('Gerenciar projeto', width=300, icon=":material/contract_edit:")



    # Valor e contrapartida
    col1, col2 = st.columns(2)
 
    col1.metric("**Valor:**", df_projetos_ispn.loc[df_projetos_ispn['nome_do_projeto'] == projeto_selecionado, 'valor_com_moeda'].values[0])
    
    col2.metric(
    "**Contrapartida:**",
    "R$ " + str(df_projetos_ispn.loc[
        df_projetos_ispn['nome_do_projeto'] == projeto_selecionado,
        'valor_da_contrapartida_em_r$'
    ].values[0])
)
    st.write('')

    # Situação
    st.write(f'**Situação:** {df_projetos_ispn.loc[df_projetos_ispn["nome_do_projeto"] == projeto_selecionado, "status"].values[0]}')

    # Nome do projeto
    st.write(f'**Nome do projeto:** {df_projetos_ispn.loc[df_projetos_ispn["nome_do_projeto"] == projeto_selecionado, "nome_do_projeto"].values[0]}')


    # Objetivo geral
    objetivo_geral = df_projetos_ispn.loc[
        df_projetos_ispn["nome_do_projeto"] == projeto_selecionado, "objetivo_geral"
    ].values[0]

    # Verificando se é NaN ou vazio
    if pd.isna(objetivo_geral) or objetivo_geral == "":
        objetivo_geral = "_Não cadastrado_"

    st.write(f'**Objetivo geral:** {objetivo_geral}')


    # Datas de início e término
    data_inicio = df_projetos_ispn.loc[df_projetos_ispn["nome_do_projeto"] == projeto_selecionado, "data_inicio_contrato"].dt.strftime("%d/%m/%Y").values[0]
    data_fim = df_projetos_ispn.loc[df_projetos_ispn["nome_do_projeto"] == projeto_selecionado, "data_fim_contrato"].dt.strftime("%d/%m/%Y").values[0]
    st.write(f'**Data de início:** {data_inicio}')
    st.write(f'**Data de término:** {data_fim}')




    # Equipe contratada pelo projeto
    st.write('**Equipe contratada pelo projeto:**')

    # 1- Obter o _id do projeto selecionado
    projeto_id = df_projetos_ispn.loc[
        df_projetos_ispn["nome_do_projeto"] == projeto_selecionado, "_id"
    ].values
    if len(projeto_id) == 0:
        st.write("_Nenhum projeto encontrado_")
    else:
        projeto_id = projeto_id[0]

        # 2- Filtrar pessoas que pertencem a esse projeto
        df_equipe = df_pessoas[df_pessoas["projeto_pagador"] == projeto_id].copy()


        if df_equipe.empty:
            st.write("_Não há equipe cadastrada para este projeto_")
        else:
            # 3- Selecionar colunas que quer mostrar
            df_equipe = df_equipe[["nome_completo", "data_inicio_contrato", "data_fim_contrato"]]  # ajuste nomes das colunas conforme seu df_pessoas
            df_equipe.rename(columns={
                "nome_completo": "Nome",
                "data_inicio_contrato": "Início do contrato",
                "data_fim_contrato": "Fim do contrato"
            }, inplace=True)

            # 4- Ordenar pelo fim do contrato e ajustar índice
            df_equipe.sort_values(by="Fim do contrato", ascending=True, inplace=True)
            df_equipe.index += 1

            # Resetar índice e adicionar +1 ao índice
            df_equipe.reset_index(drop=True, inplace=True)
            df_equipe.index += 1

            # 5- Exibir no Streamlit
            st.dataframe(df_equipe)


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
                # hoje = datetime.today().strftime("%d/%m/%Y")
                hoje = datetime.datetime.today().strftime("%d/%m/%Y")

                st.write(f"Data: {hoje}")

                anotacao_texto = st.text_area("Anotação")

                submit = st.form_submit_button("Salvar anotação", icon=':material/save:')

                if submit:
                    if not anotacao_texto.strip():
                        st.warning("A anotação não pode estar vazia.")
                    else:
                        # Buscar _id do projeto
                        projeto = projetos_ispn.find_one({"nome_do_projeto": projeto_selecionado})
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
            projeto = projetos_ispn.find_one({"nome_do_projeto": projeto_selecionado})
            
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
            projeto = projetos_ispn.find_one({"nome_do_projeto": projeto_selecionado})
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
    projeto = projetos_ispn.find_one({"nome_do_projeto": projeto_selecionado})
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














    # # Dados em formato de lista
    # anotacoes = [
    #     ["15/03/2023", "Início do projeto", "Ana"],
    #     ["15/05/2023", "Primeiro pagamento realizado", "João"],
    #     ["15/07/2023", "Entrega de relatório", "Pedro"]
    # ]

    # # Transformar em DataFrame
    # df = pd.DataFrame(anotacoes, columns=["Data", "Anotação", "Autor"])

    # # Mostrar com ui.table
    # ui.table(data=df)



























# with tab3:

#     col1, col2, col3, col4 = st.columns(4)

#     programa_selecionado = col1.selectbox("Programa", ["Todos os programas", "Cerrado", "Maranhão", "Povos Indígenas", "Sociobiodiversidade", "Iniciativas Comunitárias", "Administrativo"], key="programa")
#     projeto_selecionado = col2.selectbox('Projeto', ['Ceres', 'USAID II', 'Vale Quebradeiras'], key="projeto")

#     col3.selectbox("Projetos vigentes entre", ["2023", "2024", "2025"], key="iicio")
#     col4.selectbox("até", ["2023", "2024", "2025"], key="fim")
#     # col3.write('')
#     # col3.write('')

#     st.checkbox("Só entregas não concluídas", key="entregas")

#     st.write('')
#     col1, col2, col3 = st.columns(3)

    
#     col3.button("Reportar entrega", use_container_width=True)


#     entregas = {
#         "Entrega": ["Oficina de Advocacy", "Formação de Comunicadores", "Elaboração de Relatório", "Entrega de Relatório"],
#         "Programa": ["Cerrado", "Maranhão", "Povos Indígenas", "Sociobiodiversidade"],
#         "Projeto": ["Ceres", "USAID II", "Vale Quebradeiras", "Ceres"],
#         "Início": ["15/03/2023", "15/05/2023", "15/07/2023", "15/08/2023"],
#         "Fim": ["15/06/2023", "15/08/2023", "15/10/2023", "15/11/2023"],
#         "Responsável": ["Ana", "Pedro", "João", "Ana"],
#         "Situação": ["Em andamento", "Em andamento", "Concluído", "Em andamento"]
#     }
#     df_entregas = pd.DataFrame(entregas)

#     lista, cronograma = st.tabs(["Lista de entregas", "Cronograma"])

#     with lista:
#         st.dataframe(df_entregas, hide_index=True)

#     with cronograma:

#         df_projeto = pd.DataFrame({
#             "Entrega": ["Oficina de Advocacy", "Formação de Comunicadores", "Elaboração de Relatório", "Entrega de Relatório"],
#             "Programa": ["Cerrado", "Maranhão", "Povos Indígenas", "Sociobiodiversidade"],
#             "Projeto": ["Ceres", "USAID II", "Vale Quebradeiras", "Ceres"],
#             "Início": ["março/2023", "maio/2023", "julho/2023", "agosto/2023"],
#             "Fim": ["junho/2023", "agosto/2023", "outubro/2023", "novembro/2023"],
#             "Responsável": ["Ana", "Pedro", "João", "Ana"],
#             "Situação": ["Em andamento", "Em andamento", "Concluído", "Em andamento"]
#         })
#         # Mapeamento de meses em português para número
#         meses = {
#             "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
#             "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
#             "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
#         }

#         # Função para converter "mês/ano" para datetime
#         def converter_data(data_str):
#             mes, ano = data_str.split('/')
#             mes_num = meses[mes.lower()]
#             return pd.to_datetime(f"{ano}-{mes_num}-01")

#         # Aplicando a conversão
#         df_projeto['Início'] = df_projeto['Início'].apply(converter_data)
#         df_projeto['Fim'] = df_projeto['Fim'].apply(converter_data)

#         # Criando gráfico de Gantt com Plotly Express
#         fig = px.timeline(
#             df_projeto,
#             x_start='Início',
#             x_end='Fim',
#             y='Entrega',
#             color='Situação',
#             # hover_data=['Valor'],
#             height=250  # Diminuindo a altura do gráfico
#         )

#         fig.update_yaxes(categoryorder='total ascending')

#         # Movendo a legenda para baixo
#         fig.update_layout(
#             legend=dict(
#                 orientation="h",       # horizontal
#                 yanchor="bottom",
#                 y=-1,                # valor negativo posiciona abaixo do gráfico
#                 xanchor="center",
#                 x=0
#             ),
#             yaxis_title=None
#         )

#         # Streamlit
#         st.plotly_chart(fig, key="cronograma", use_container_width=True)
        