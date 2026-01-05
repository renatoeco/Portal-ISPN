import streamlit as st
import pandas as pd
from datetime import datetime
from bson import ObjectId
from funcoes_auxiliares import conectar_mongo_portal_ispn, dialog_editar_entregas, altura_dataframe
# import streamlit_shadcn_ui as ui
import plotly.express as px
import time
# import bson




###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS E CARREGAMENTO
###########################################################################################################


db = conectar_mongo_portal_ispn()
# estrategia = db["estrategia"]  
programas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"]  
# indicadores = db["indicadores"]
estatistica = db["estatistica"] 



# --------------------------------------------------
# ESTADOS DO DIÁLOGO DE REGISTRO DE ENTREGAS
# --------------------------------------------------
if "entrega_selecionada" not in st.session_state:
    st.session_state["entrega_selecionada"] = None

if "entrega_selecionada_tabela_key" not in st.session_state:
    st.session_state["entrega_selecionada_tabela_key"] = None

if "entrega" not in st.session_state:
    st.session_state["entrega"] = False




###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_entregas"
nome_pagina = "Entregas"
hoje = datetime.now().strftime("%d/%m/%Y")
pagina_anterior = st.session_state.get("pagina_anterior")
navegou_para_esta_pagina = (pagina_anterior != PAGINA_ID)
if navegou_para_esta_pagina:

    # Obter o único documento
    doc = estatistica.find_one({})

    # Criar o campo caso não exista
    if nome_pagina not in doc:
        estatistica.update_one(
            {},
            {"$set": {nome_pagina: []}}
        )

    estatistica.update_one(
            {},
            {"$inc": {f"{nome_pagina}.$[elem].numero_de_acessos": 1}},
            array_filters=[{"elem.data": hoje}]
        )

    estatistica.update_one(
        {f"{nome_pagina}.data": {"$ne": hoje}},
        {"$push": {
            nome_pagina: {"data": hoje, "numero_de_acessos": 1}
        }}
    )
# Registrar página anterior
st.session_state["pagina_anterior"] = PAGINA_ID



# ##########################################################
# Funções
# ##########################################################

@st.dialog("Acompanhamento de Entrega", width="large")
def dialog_registros_entregas():

    entrega = st.session_state.get("entrega_selecionada")
    idx = entrega.get("indice") if isinstance(entrega, dict) else None

    if idx is None:
        st.warning("Entrega inválida.")
        return

    # Dados da entrega
    nome_entrega = entrega.get("entrega", "Entrega")
    situacao = df_entregas.loc[idx, "situacao"]

    progresso = df_entregas.loc[idx, "progresso"]
    try:
        progresso = int(progresso)
    except (TypeError, ValueError):
        progresso = 0

    previsao_str = df_entregas.loc[idx, "previsao_da_conclusao_str"]
    responsaveis = df_entregas.loc[idx, "responsaveis"]
    responsaveis_ids = df_entregas.loc[idx, "responsaveis_ids"]

    # Cabeçalho
    st.markdown(f"## {nome_entrega}")
    st.write("")

    col1, col2, col3, col4 = st.columns([1, 1, 2, 2.5])

    usuarios_internos = set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}

    # Usuários internos (edição habilitada)
    if usuarios_internos:

        situacoes = ["Prevista", "Atrasada", "Concluída"]
        with col1:
            st.selectbox(
                "Situação:",
                options=situacoes,
                index=situacoes.index(situacao) if situacao in situacoes else 0,
                key=f"entrega_situacao_{idx}"
            )

        opcoes_progresso = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        with col2:
            st.selectbox(
                "Progresso:",
                options=opcoes_progresso,
                index=opcoes_progresso.index(progresso) if progresso in opcoes_progresso else 0,
                format_func=lambda x: f"{x}%",
                key=f"entrega_progresso_{idx}"
            )

        data_previsao = None
        if previsao_str:
            try:
                data_previsao = datetime.strptime(previsao_str, "%d/%m/%Y").date()
            except ValueError:
                pass

        with col3:
            st.date_input(
                "Previsão de Conclusão:",
                value=data_previsao,
                format="DD/MM/YYYY",
                key=f"entrega_previsao_{idx}"
            )

        pessoas = list(db["pessoas"].find({}, {"nome_completo": 1}))
        mapa_pessoas = {
            str(p["_id"]): p["nome_completo"]
            for p in sorted(pessoas, key=lambda x: x["nome_completo"])
        }

        with col4:
            st.multiselect(
                "Responsáveis:",
                options=list(mapa_pessoas.keys()),
                default=[str(r) for r in responsaveis_ids],
                format_func=lambda x: mapa_pessoas.get(x, x),
                key=f"entrega_responsaveis_{idx}"
            )

        st.write("")
        with st.container(horizontal_alignment="right"):
            if st.button("Salvar alterações", icon=":material/save:", width=250):

                nova_situacao = st.session_state[f"entrega_situacao_{idx}"]
                novo_progresso = st.session_state[f"entrega_progresso_{idx}"]
                nova_data = st.session_state[f"entrega_previsao_{idx}"]
                novos_responsaveis = st.session_state[f"entrega_responsaveis_{idx}"]

                nova_data_str = (
                    nova_data.strftime("%d/%m/%Y") if nova_data else None
                )

                # Salva no MongoDB
                projetos_ispn.update_one(
                    {"entregas.nome_da_entrega": nome_entrega},
                    {
                        "$set": {
                            "entregas.$.situacao": nova_situacao,
                            "entregas.$.progresso": novo_progresso,
                            "entregas.$.previsao_da_conclusao": nova_data_str,
                            "entregas.$.responsaveis": [ObjectId(r) for r in novos_responsaveis],
                        }
                    }
                )

                # Atualiza o DataFrame em memória
                df_entregas.at[idx, "situacao"] = nova_situacao
                df_entregas.at[idx, "progresso"] = novo_progresso
                df_entregas.at[idx, "previsao_da_conclusao_str"] = nova_data_str
                df_entregas.at[idx, "responsaveis_ids"] = novos_responsaveis
                df_entregas.at[idx, "responsaveis"] = ", ".join(
                    mapa_pessoas[str(r)] for r in novos_responsaveis if str(r) in mapa_pessoas
                )

                st.success("Alterações salvas com sucesso.")
                time.sleep(3)
                st.rerun()

    # Usuários externos (somente leitura)
    else:
        with col1:
            st.write(f"**Situação:** {situacao}")

        with col2:
            st.write(f"**Progresso:** {progresso}%")

        with col3:
            st.write(f"**Previsão de Conclusão:** {previsao_str}")

        with col4:
            st.write(f"**Responsáveis:** {responsaveis}")

    st.divider()

    # Lançamentos
    lancamentos = df_entregas.loc[idx, "lancamentos_entregas"]

    if not lancamentos:
        st.info("Nenhum lançamento registrado para esta entrega.")
    else:
        df_lancamentos = pd.DataFrame(lancamentos)
        for col in df_lancamentos.columns:
            df_lancamentos[col] = df_lancamentos[col].astype(str)

        st.dataframe(
            df_lancamentos,
            hide_index=True,
            use_container_width=True
        )




def resolver_responsaveis(lista_ids, pessoas_dict):
    nomes = []
    for rid in lista_ids:
        rid = ObjectId(rid)
        if rid in pessoas_dict:
            nomes.append(pessoas_dict[rid])
    return ", ".join(nomes)


def carregar_entregas():
    """
    Retorna DataFrame com TODAS as entregas,
    já resolvendo responsáveis e programa
    """
    pessoas = {
        p["_id"]: p["nome_completo"]
        for p in db["pessoas"].find({}, {"nome_completo": 1})
    }

    programas_dict = {
        p["_id"]: p.get("nome_programa_area", "")
        for p in programas.find({}, {"nome_programa_area": 1})
    }

    registros = []

    for projeto in projetos_ispn.find():
        programa_nome = programas_dict.get(projeto.get("programa"), "")
        nome_projeto = projeto.get("nome_do_projeto") or projeto.get("sigla", "")

        for entrega in projeto.get("entregas", []):
            
            data_raw = entrega.get("previsao_da_conclusao")

            if not data_raw:
                continue  # pula entregas sem data

            try:
                data_conclusao = datetime.strptime(data_raw, "%d/%m/%Y")
            except ValueError:
                continue  # pula datas inválidas

            registros.append({
                "nome_da_entrega": entrega.get("nome_da_entrega"),
                
                "nome_do_projeto": nome_projeto,

                # PARA O GRÁFICO
                "previsao_da_conclusao": data_conclusao,

                # PARA A TABELA (JSON-safe)
                "previsao_da_conclusao_str": data_conclusao.strftime("%d/%m/%Y"),

                "responsaveis": resolver_responsaveis(
                    entrega.get("responsaveis", []),
                    pessoas
                ),
                "situacao": entrega.get("situacao"),
                "anos_de_referencia": ", ".join(entrega.get("anos_de_referencia", [])),
                "programa": programa_nome,
                "responsaveis_ids": [ObjectId(r) for r in entrega.get("responsaveis", [])],

                "lancamentos_entregas": entrega.get("lancamentos_entregas", []),

                "progresso": entrega.get("progresso")
            })

        COLUNAS_PADRAO = [
            "nome_da_entrega",
            "nome_do_projeto",
            "previsao_da_conclusao",
            "previsao_da_conclusao_str",
            "responsaveis",
            "situacao",
            "anos_de_referencia",
            "programa",
            "responsaveis_ids",
            "lancamentos_entregas",
            "progresso"
        ]

    df = pd.DataFrame(registros)

    # GARANTIA DE ESQUEMA
    for col in COLUNAS_PADRAO:
        if col not in df.columns:
            df[col] = None

    if df.empty:
        return df[COLUNAS_PADRAO]

    return (
        df[COLUNAS_PADRAO]
        .sort_values("previsao_da_conclusao", ascending=True)
        .reset_index(drop=True)
    )


def grafico_cronograma(df, titulo):
    
    if df.empty:
        st.info("Nenhuma entrega encontrada.")
        return

    hoje = datetime.today()
    df_plot = df.copy()
    
    df_plot = df_plot[
        df_plot["situacao"].isin(["Prevista", "Atrasada"])
    ]

    # Cria as colunas primeiro
    df_plot["Inicio"] = df_plot["previsao_da_conclusao"] - pd.Timedelta(days=5)
    df_plot["Fim"] = df_plot["previsao_da_conclusao"]
    
    xmin = min(df_plot["Inicio"].min(), hoje)
    xmax = max(df_plot["Fim"].max(), hoje)


    # Agora sim pode formatar a data
    df_plot["previsao_conclusao_hover"] = df_plot["Fim"].dt.strftime("%d/%m/%Y")

    # Ordena
    df_plot = df_plot.sort_values("Fim", ascending=False)

    altura_total = max(300, len(df_plot) * 45)

    fig = px.timeline(
        df_plot,
        x_start="Inicio",
        x_end="Fim",
        y="nome_da_entrega",
        color="situacao",
        custom_data=[
        "nome_da_entrega",
        "nome_do_projeto",
        "previsao_conclusao_hover",
        "responsaveis",
        "programa"
    ],
        height=altura_total,
        title=titulo
    )

    fig.update_traces(
        hovertemplate=
        "<b>Entrega:</b> %{customdata[0]}<br>"
        "<b>Projeto:</b> %{customdata[1]}<br>"
        "<b>Previsão de Conclusão:</b> %{customdata[2]}<br>"
        "<b>Responsáveis:</b> %{customdata[3]}<br>"
        "<b>Programa:</b> %{customdata[4]}<br>"
        "<extra></extra>"
    )


    fig.update_yaxes(
        categoryorder="array",
        categoryarray=df_plot["nome_da_entrega"].tolist(),
        title=""
    )

    fig.update_xaxes(
        range=[xmin, xmax],
        tickformat="%d/%m/%Y",
        tickangle=-45,
        #title="Previsão de Conclusão"
    )


    fig.update_layout(
        margin=dict(l=180, r=40, t=60, b=40)
    )

    st.plotly_chart(fig, width="stretch")


# ##########################################################
# INTERFACE
# ##########################################################

st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


st.header("Entregas")

st.write("")

# Montagem do df_entregas
df_entregas = carregar_entregas()
# Converter as coluans de id para string
df_entregas["responsaveis_ids"] = df_entregas["responsaveis_ids"].apply(lambda x: [str(i) for i in x])

df_entregas_lista = df_entregas.copy()




# Botão de gerenciar entregas somente para admin e coordenadores
if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}:
    with st.container(horizontal_alignment="right"):
        st.write('')    
        if st.button("Gerenciar entregas", icon=":material/edit:", width=300):
            dialog_editar_entregas()




lista_entregas, cronograma_entregas = st.tabs(["Entregas","Cronograma"])

with lista_entregas:

    # Renomeando as colunas
    RENOMEAR = {
        "nome_da_entrega": "Entrega",
        "nome_do_projeto": "Projeto",
        "previsao_da_conclusao_str": "Previsão de Conclusão",
        "responsaveis": "Responsáveis",
        "situacao": "Situação",
        "anos_de_referencia": "Anos de Referência",
        "programa": "Programa",
        "progresso": "Progresso"
    }


    df_entregas_lista = df_entregas_lista.rename(columns=RENOMEAR)

    df_entregas_lista = df_entregas_lista[[
        "Entrega",
        "Projeto",
        "Programa",
        "Responsáveis",
        "Anos de Referência",
        "Previsão de Conclusão",
        "Situação",
        "Progresso"
    ]]

    # --------------------------------------------------------------------------
    # INTERFACE DA ABA LISTA
    # --------------------------------------------------------------------------

    st.write('')

    # --------------------------------------------------------------------------
    # CALLBACK PARA ABERTURA DO DIÁLOGO DE REGISTROS DE ENTREGAS
    # --------------------------------------------------------------------------
    def criar_callback_selecao_entrega(df_entregas, key_df):

        def handle_selecao_entrega():
            estado = st.session_state.get(key_df, {})
            linhas = estado.get("selection", {}).get("rows", [])

            if not linhas:
                return

            idx = linhas[0]
            linha = df_entregas.iloc[idx]

            st.session_state["entrega_selecionada"] = {
                "entrega": linha["Entrega"],
                "indice": idx
            }

            # st.session_state["entrega_selecionada"] = {
            #     "entrega": linha["Entrega"]
            # }

            st.session_state["abrir_dialogo_entrega"] = True

        return handle_selecao_entrega


    key_df = f"df_entregas_lista"

    callback_selecao = criar_callback_selecao_entrega(
        df_entregas_lista,
        key_df
    )

    altura_dataframe = altura_dataframe(df_entregas_lista, -0)

    st.dataframe(
        df_entregas_lista,
        hide_index=True,
        selection_mode="single-row",
        key=key_df,
        on_select=callback_selecao,
        height=altura_dataframe,
        column_config={
            "Progresso": st.column_config.ProgressColumn(
                format="%d%%"
            )
        }
    )


    # --------------------------------------------------
    # ABRIR DIÁLOGO
    # --------------------------------------------------
    if st.session_state.get("abrir_dialogo_entrega"):
        dialog_registros_entregas()
        st.session_state["abrir_dialogo_entrega"] = False



with cronograma_entregas:
   

    grafico_cronograma(
        df_entregas,
        "Cronograma de Entregas"
    )
    







































# import streamlit as st
# import pandas as pd
# from datetime import datetime
# from bson import ObjectId
# from funcoes_auxiliares import conectar_mongo_portal_ispn, dialog_editar_entregas
# import streamlit_shadcn_ui as ui
# import plotly.express as px
# import time
# import bson









# ###########################################################################################################
# # CONEXÃO COM O BANCO DE DADOS E CARREGAMENTO
# ###########################################################################################################


# db = conectar_mongo_portal_ispn()
# estrategia = db["estrategia"]  
# programas = db["programas_areas"]
# projetos_ispn = db["projetos_ispn"]  
# indicadores = db["indicadores"]
# estatistica = db["estatistica"] 



# ###########################################################################################################
# # CONTADOR DE ACESSOS À PÁGINA
# ###########################################################################################################


# PAGINA_ID = "pagina_entregas"
# nome_pagina = "Entregas"

# hoje = datetime.now().strftime("%d/%m/%Y")

# pagina_anterior = st.session_state.get("pagina_anterior")
# navegou_para_esta_pagina = (pagina_anterior != PAGINA_ID)

# if navegou_para_esta_pagina:

#     # Obter o único documento
#     doc = estatistica.find_one({})

#     # Criar o campo caso não exista
#     if nome_pagina not in doc:
#         estatistica.update_one(
#             {},
#             {"$set": {nome_pagina: []}}
#         )

#     estatistica.update_one(
#             {},
#             {"$inc": {f"{nome_pagina}.$[elem].numero_de_acessos": 1}},
#             array_filters=[{"elem.data": hoje}]
#         )

#     estatistica.update_one(
#         {f"{nome_pagina}.data": {"$ne": hoje}},
#         {"$push": {
#             nome_pagina: {"data": hoje, "numero_de_acessos": 1}
#         }}
#     )

# # Registrar página anterior
# st.session_state["pagina_anterior"] = PAGINA_ID



# # ##########################################################
# # Funções
# # ##########################################################


# def resolver_responsaveis(lista_ids, pessoas_dict):
#     nomes = []
#     for rid in lista_ids:
#         rid = ObjectId(rid)
#         if rid in pessoas_dict:
#             nomes.append(pessoas_dict[rid])
#     return ", ".join(nomes)


# def carregar_entregas():
#     """
#     Retorna DataFrame com TODAS as entregas,
#     já resolvendo responsáveis e programa
#     """
#     pessoas = {
#         p["_id"]: p["nome_completo"]
#         for p in db["pessoas"].find({}, {"nome_completo": 1})
#     }

#     programas_dict = {
#         p["_id"]: p.get("nome_programa_area", "")
#         for p in programas.find({}, {"nome_programa_area": 1})
#     }

#     registros = []

#     for projeto in projetos_ispn.find():
#         programa_nome = programas_dict.get(projeto.get("programa"), "")
#         nome_projeto = projeto.get("nome_do_projeto") or projeto.get("sigla", "")

#         for entrega in projeto.get("entregas", []):
            
#             data_raw = entrega.get("previsao_da_conclusao")

#             if not data_raw:
#                 continue  # pula entregas sem data

#             try:
#                 data_conclusao = datetime.strptime(data_raw, "%d/%m/%Y")
#             except ValueError:
#                 continue  # pula datas inválidas

#             registros.append({
#                 "nome_da_entrega": entrega.get("nome_da_entrega"),
                
#                 "nome_do_projeto": nome_projeto,

#                 # PARA O GRÁFICO
#                 "previsao_da_conclusao": data_conclusao,

#                 # PARA A TABELA (JSON-safe)
#                 "previsao_da_conclusao_str": data_conclusao.strftime("%d/%m/%Y"),

#                 "responsaveis": resolver_responsaveis(
#                     entrega.get("responsaveis", []),
#                     pessoas
#                 ),
#                 "situacao": entrega.get("situacao"),
#                 "anos_de_referencia": ", ".join(entrega.get("anos_de_referencia", [])),
#                 "programa": programa_nome,
#                 "responsaveis_ids": [ObjectId(r) for r in entrega.get("responsaveis", [])]
#             })

#         COLUNAS_PADRAO = [
#             "nome_da_entrega",
#             "nome_do_projeto",
#             "previsao_da_conclusao",
#             "previsao_da_conclusao_str",
#             "responsaveis",
#             "situacao",
#             "anos_de_referencia",
#             "programa",
#             "responsaveis_ids"
#         ]

#     df = pd.DataFrame(registros)

#     # GARANTIA DE ESQUEMA
#     for col in COLUNAS_PADRAO:
#         if col not in df.columns:
#             df[col] = None

#     if df.empty:
#         return df[COLUNAS_PADRAO]

#     return (
#         df[COLUNAS_PADRAO]
#         .sort_values("previsao_da_conclusao", ascending=True)
#         .reset_index(drop=True)
#     )



# def grafico_cronograma(df, titulo):
    
#     if df.empty:
#         st.info("Nenhuma entrega encontrada.")
#         return

#     hoje = datetime.today()
#     df_plot = df.copy()
    
#     df_plot = df_plot[
#         df_plot["situacao"].isin(["Prevista", "Atrasada"])
#     ]

#     # Cria as colunas primeiro
#     df_plot["Inicio"] = df_plot["previsao_da_conclusao"] - pd.Timedelta(days=5)
#     df_plot["Fim"] = df_plot["previsao_da_conclusao"]
    
#     xmin = min(df_plot["Inicio"].min(), hoje)
#     xmax = max(df_plot["Fim"].max(), hoje)


#     # Agora sim pode formatar a data
#     df_plot["previsao_conclusao_hover"] = df_plot["Fim"].dt.strftime("%d/%m/%Y")

#     # Ordena
#     df_plot = df_plot.sort_values("Fim", ascending=False)

#     altura_total = max(300, len(df_plot) * 45)

#     fig = px.timeline(
#         df_plot,
#         x_start="Inicio",
#         x_end="Fim",
#         y="nome_da_entrega",
#         color="situacao",
#         custom_data=[
#         "nome_da_entrega",
#         "nome_do_projeto",
#         "previsao_conclusao_hover",
#         "responsaveis",
#         "programa"
#     ],
#         height=altura_total,
#         title=titulo
#     )

#     fig.update_traces(
#         hovertemplate=
#         "<b>Entrega:</b> %{customdata[0]}<br>"
#         "<b>Projeto:</b> %{customdata[1]}<br>"
#         "<b>Previsão de Conclusão:</b> %{customdata[2]}<br>"
#         "<b>Responsáveis:</b> %{customdata[3]}<br>"
#         "<b>Programa:</b> %{customdata[4]}<br>"
#         "<extra></extra>"
#     )


#     fig.update_yaxes(
#         categoryorder="array",
#         categoryarray=df_plot["nome_da_entrega"].tolist(),
#         title=""
#     )

#     fig.update_xaxes(
#         range=[xmin, xmax],
#         tickformat="%d/%m/%Y",
#         tickangle=-45,
#         #title="Previsão de Conclusão"
#     )


#     fig.update_layout(
#         margin=dict(l=180, r=40, t=60, b=40)
#     )

#     st.plotly_chart(fig, width="stretch")


# # ##########################################################
# # INTERFACE
# # ##########################################################

# st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


# st.header("Entregas")

# st.write("")

# df_entregas = carregar_entregas()

# COLUNAS_LEGIVEIS = {
#     "nome_do_projeto": "Projeto",
#     "nome_da_entrega": "Entrega",
#     "previsao_da_conclusao_str": "Previsão de Conclusão",
#     "responsaveis": "Responsáveis",
#     "situacao": "Situação",
#     "anos_de_referencia": "Anos de Referência",
#     "programa": "Programa"
# }

# # Botão de gerenciar entregas somente para admin e coordenadores
# if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}:
#     with st.container(horizontal_alignment="right"):
#         st.write('')    
#         if st.button("Gerenciar entregas", icon=":material/edit:", width=300):
#             dialog_editar_entregas()




# aba_minhas, aba_todas = st.tabs(["Minhas entregas","Todas as entregas"])

# with aba_minhas:

#     usuario_id = ObjectId(st.session_state["id_usuario"])

#     df_minhas = df_entregas[
#         df_entregas["responsaveis_ids"].apply(
#             lambda x: usuario_id in x
#         )
#     ]

#     ui.table(
#         data=df_minhas[list(COLUNAS_LEGIVEIS.keys())]
#             .rename(columns=COLUNAS_LEGIVEIS)
#     )

#     grafico_cronograma(
#         df_minhas,
#         "Cronograma de Entregas"
#     )

# with aba_todas:
   
#     ui.table(
#         data=df_entregas[list(COLUNAS_LEGIVEIS.keys())]
#             .rename(columns=COLUNAS_LEGIVEIS)
#     )

#     grafico_cronograma(
#         df_entregas,
#         "Cronograma de Entregas"
#     )
    
