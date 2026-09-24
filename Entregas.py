import streamlit as st
import pandas as pd
from datetime import datetime
from bson import ObjectId
from funcoes_auxiliares import (
    conectar_mongo_portal_ispn, 
    mostrar_detalhes_registro_entrega, 
    dialog_editar_entrega, 
    mostrar_detalhes_entrega,
    cadastrar_entrega,
    cadastrar_registro_entrega,
    editar_registro_entrega
)
import plotly.express as px
import time
import bson
from streamlit_scroll_to_top import scroll_to_here




###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS E CARREGAMENTO
###########################################################################################################


db = conectar_mongo_portal_ispn()
# estrategia = db["estrategia"]  
programas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"]  
indicadores = db["indicadores"]
estatistica = db["estatistica"] 
colecao_lancamentos = db["lancamentos_indicadores"]




# ==========================================================
# MAPA DE INDICADORES
# ==========================================================
# Carrega o nome e o tipo da variável diretamente da coleção
# de indicadores. O campo "tipo_variavel" define qual widget
# será utilizado no lançamento e também qual tipo Python será
# salvo no MongoDB.
#
# Valores esperados para "tipo_variavel":
#   - "str"   -> texto
#   - "int"   -> número inteiro
#   - "float" -> número decimal
# ==========================================================

df_indicadores = pd.DataFrame(
    list(
        indicadores.find(
            {},
            {
                "nome_indicador": 1,
                "tipo_variavel": 1
            }
        )
    )
)

if not df_indicadores.empty:

    # Converte o ObjectId para string para facilitar o uso
    # como chave nos dicionários e nos componentes Streamlit.
    df_indicadores["_id"] = df_indicadores["_id"].astype(str)

    # Garante que indicadores antigos ou incompletos tenham
    # um tipo padrão. O padrão utilizado será "str", evitando
    # conversões numéricas indevidas.
    df_indicadores["tipo_variavel"] = (
        df_indicadores["tipo_variavel"]
        .fillna("str")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    # Mapa completo:
    # id_indicador -> nome e tipo da variável.
    mapa_indicadores = {
        row["_id"]: {
            "nome": row.get("nome_indicador", "Indicador não encontrado"),
            "tipo_variavel": row.get("tipo_variavel", "str")
        }
        for _, row in df_indicadores.iterrows()
    }

else:
    mapa_indicadores = {}


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

    # ==========================================================
    # MAPA DE PROJETOS
    # ==========================================================

    mapa_projetos = {
        str(p["_id"]): p.get("sigla", "")
        for p in projetos_ispn.find({}, {"sigla": 1})
    }

    registros = []

    for projeto in projetos_ispn.find():

        programas_ids = projeto.get("programas", [])

        def mapear_programas(lista_ids):
            """
            Converte lista de ObjectIds em nomes de programas.
            Retorna sempre lista.
            """
            if isinstance(lista_ids, list):
                return [programas_dict.get(i, "") for i in lista_ids if i in programas_dict]
            elif lista_ids:
                return [programas_dict.get(lista_ids, "")]
            return []

        programas_nomes = mapear_programas(programas_ids)
        nome_projeto = projeto.get("sigla") or projeto.get("sigla", "")

        for entrega in projeto.get("entregas", []):

            data_inicio_raw = entrega.get("data_inicio")
            data_fim_raw = entrega.get("previsao_da_conclusao")

            data_inicio = None
            data_fim = None

            try:
                if data_inicio_raw:
                    data_inicio = datetime.strptime(data_inicio_raw, "%d/%m/%Y")
            except:
                pass

            try:
                if data_fim_raw:
                    data_fim = datetime.strptime(data_fim_raw, "%d/%m/%Y")
            except:
                pass

            # ==========================================================
            # PROJETOS RELACIONADOS
            # ==========================================================

            projetos_relacionados_ids = entrega.get(
                "projetos_relacionados",
                []
            )

            projetos_relacionados_nomes = [
                mapa_projetos.get(str(pid), "")
                for pid in projetos_relacionados_ids
                if mapa_projetos.get(str(pid), "")
            ]

            # Junta projeto principal + relacionados
            todos_projetos = [nome_projeto]

            for proj in projetos_relacionados_nomes:
                if proj not in todos_projetos:
                    todos_projetos.append(proj)

            projetos_str = ", ".join(todos_projetos)

            registros.append({
                "projeto_id": projeto["_id"],
                
                "nome_da_entrega": entrega.get("nome_da_entrega"),
                "entrega_id": entrega["_id"],
                
                "projetos": todos_projetos,
                "projetos_str": projetos_str,

                "data_inicio": data_inicio,
                "data_inicio_str": data_inicio.strftime("%d/%m/%Y") if data_inicio else "",

                "previsao_da_conclusao": data_fim,
                "previsao_da_conclusao_str": data_fim.strftime("%d/%m/%Y") if data_fim else "",

                "responsaveis": resolver_responsaveis(
                    entrega.get("responsaveis", []),
                    pessoas
                ),
                "situacao": entrega.get("situacao"),
                "programa": programas_nomes,  # lista
                "programa_str": ", ".join(programas_nomes),  # string para exibição
                "responsaveis_ids": [ObjectId(r) for r in entrega.get("responsaveis", [])],

                "lancamentos_entregas": entrega.get("lancamentos_entregas", []),

                "progresso": entrega.get("progresso"),

                "acoes_resultados_medio_prazo": entrega.get("acoes_resultados_medio_prazo", []),
                "resultados_longo_prazo_relacionados": entrega.get("resultados_longo_prazo_relacionados", []),
                "eixos_relacionados": entrega.get("eixos_relacionados", []),
                "acoes_estrat_programa": entrega.get("acoes_estrat_programa", []),
                "metas_resultados_medio_prazo": entrega.get("metas_resultados_medio_prazo", []),
                "indicadores_relacionados": entrega.get("indicadores_relacionados", []),

            })

        COLUNAS_PADRAO = [
            "projeto_id",
            "nome_da_entrega",
            "entrega_id",
            "projetos",
            "projetos_str",
            "previsao_da_conclusao",
            "previsao_da_conclusao_str",
            "responsaveis",
            "situacao",
            "data_inicio",
            "data_inicio_str",
            "programa",
            "programa_str",
            "responsaveis_ids",
            "lancamentos_entregas",
            "progresso",
            "acoes_resultados_medio_prazo",
            "resultados_longo_prazo_relacionados",
            "eixos_relacionados",
            "acoes_estrat_programa",
            "metas_resultados_medio_prazo",
            "indicadores_relacionados",

        ]

    df = pd.DataFrame(registros)
    
    # Converte colunas para datetime (resolve o erro do .dt)
    df["data_inicio"] = pd.to_datetime(df["data_inicio"], errors="coerce")
    df["previsao_da_conclusao"] = pd.to_datetime(df["previsao_da_conclusao"], errors="coerce")

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

    df_plot = df.copy()

    # Considera apenas entregas ativas
    df_plot = df_plot[
        df_plot["situacao"].isin(["Prevista", "Atrasada"])
    ]

    # Considera apenas entregas com data_inicio e data_fim válidas
    df_plot = df_plot[
        df_plot["data_inicio"].notna() &
        df_plot["previsao_da_conclusao"].notna()
    ]

    if df_plot.empty:
        st.caption("Nenhuma entrega com data de início.")
        return

    df_plot["Inicio"] = df_plot["data_inicio"]
    df_plot["Fim"] = df_plot["previsao_da_conclusao"]
    
    # ==================================================
    # LIMITES DO EIXO X (ANO MAIS ANTIGO → MAIS RECENTE)
    # ==================================================

    xmin = df_plot["Inicio"].min()
    xmax = df_plot["Fim"].max()

    # ==================================================
    # HOVER
    # ==================================================

    # Ordena visualmente
    df_plot = df_plot.sort_values("Inicio", ascending=False)

    altura_total = max(300, len(df_plot) * 45)

    df_plot["inicio_hover"] = df_plot["data_inicio_str"]
    df_plot["previsao_hover"] = df_plot["previsao_da_conclusao_str"]

    fig = px.timeline(
        df_plot,
        x_start="Inicio",
        x_end="Fim",
        y="nome_da_entrega",
        color="situacao",
        custom_data=[
            "nome_da_entrega",
            "projetos_str",
            "inicio_hover",
            "previsao_hover",
            "responsaveis",
            "programa_str"
        ],
        height=altura_total,
        title=titulo
    )

    fig.update_traces(
        hovertemplate=
        "<b>Entrega:</b> %{customdata[0]}<br>"
        "<b>Projeto:</b> %{customdata[1]}<br>"
        "<b>Data de início:</b> %{customdata[2]}<br>"
        "<b>Previsão de Conclusão:</b> %{customdata[3]}<br>"
        "<b>Responsáveis:</b> %{customdata[4]}<br>"
        "<b>Programa:</b> %{customdata[5]}<br>"
        "<extra></extra>"
    )

    fig.update_yaxes(
        categoryorder="array",
        categoryarray=df_plot["nome_da_entrega"].tolist(),
        title=""
    )

    fig.update_xaxes(
        range=[xmin, xmax],

        # Intervalo maior (menos poluição)
        dtick="M1",  # 1 mês (melhor que D30)

        # Formato mais limpo
        tickformat="%b/%Y",  # Ex: Jan/2026

        hoverformat="%d/%m/%Y"
    )

    fig.update_layout(
        margin=dict(l=180, r=40, t=60, b=40)
    )

    st.plotly_chart(fig)


def verificar_entregas_atrasadas():
    hoje = datetime.now().date()

    projetos = projetos_ispn.find({"entregas": {"$exists": True}})

    for projeto in projetos:
        entregas = projeto.get("entregas", [])
        alterou = False

        for entrega in entregas:
            if entrega.get("situacao") == "Prevista":

                data_str = entrega.get("previsao_da_conclusao")

                if not data_str:
                    continue

                try:
                    data_prevista = datetime.strptime(
                        data_str, "%d/%m/%Y"
                    ).date()
                except ValueError:
                    continue

                if hoje > data_prevista:
                    entrega["situacao"] = "Atrasada"
                    alterou = True

        if alterou:
            projetos_ispn.update_one(
                {"_id": projeto["_id"]},
                {"$set": {"entregas": entregas}}
            )




# ==========================================================
# INTERFACE DA ABA DE ENTREGAS
# ==========================================================

@st.fragment
def render_entregas():

    # --------------------------------------------------
    # Estado da entrega selecionada
    # --------------------------------------------------

    if "entrega_selecionada_id" not in st.session_state:
        st.session_state["entrega_selecionada_id"] = None

    if "scroll_registros" not in st.session_state:
        st.session_state["scroll_registros"] = 0

    if "scroll_pendente" not in st.session_state:
        st.session_state["scroll_pendente"] = False


    # --------------------------------------------------
    # Scroll da tela
    # --------------------------------------------------

    if st.session_state.get("scroll_pendente", False):

        scroll_id = st.session_state["scroll_registros"]

        scroll_to_here(
            0,
            key=f"registros_entrega_{scroll_id}"
        )

        # Consome o evento após executar o scroll.
        st.session_state["scroll_pendente"] = False

    # --------------------------------------------------
    # Dados utilizados pelo fragmento
    # --------------------------------------------------

    df = df_entregas_filtrado

    if df.empty:
        st.info("Nenhuma entrega encontrada.")
        return

    # --------------------------------------------------
    # Inicialização dos estados dos checkboxes
    # --------------------------------------------------

    for _, entrega in df.iterrows():

        entrega_id = str(entrega["entrega_id"])
        chave_checkbox = f"checkbox_entrega_{entrega_id}"

        if chave_checkbox not in st.session_state:
            st.session_state[chave_checkbox] = False

    # --------------------------------------------------
    # Callback de seleção
    # --------------------------------------------------

    def alterar_entrega_selecionada(entrega_id):

        entrega_id = str(entrega_id)
        chave_checkbox = f"checkbox_entrega_{entrega_id}"

        selecionada = st.session_state.get(
            chave_checkbox,
            False
        )

        if selecionada:

            # Registra a entrega atualmente selecionada.
            st.session_state["entrega_selecionada_id"] = entrega_id

            # Gera um novo identificador para cada seleção.
            st.session_state["scroll_registros"] += 1

            # Solicita o scroll somente para esta seleção.
            st.session_state["scroll_pendente"] = True

            # Mantém apenas uma entrega selecionada.
            for _, outra_entrega in df.iterrows():

                outro_id = str(outra_entrega["entrega_id"])

                if outro_id != entrega_id:

                    outra_chave = f"checkbox_entrega_{outro_id}"

                    st.session_state[outra_chave] = False

        else:

            # Remove a seleção quando o checkbox ativo é desmarcado.
            if (
                st.session_state.get("entrega_selecionada_id")
                == entrega_id
            ):
                st.session_state["entrega_selecionada_id"] = None

    # --------------------------------------------------
    # Layout principal
    # --------------------------------------------------

    col_entregas, col_registros = st.columns(
        [1, 1],
        gap="medium"
    )

    # ==================================================
    # COLUNA ESQUERDA — ENTREGAS
    # ==================================================

    with col_entregas:

        st.markdown("#### Entregas planejadas")



        if st.button(
            "Cadastrar nova entrega",
            icon=":material/add:",
            type="primary",
            key="nova_entrega"
        ):
            cadastrar_entrega()





        for _, entrega in df.iterrows():

            entrega_id = str(entrega["entrega_id"])
            chave_checkbox = f"checkbox_entrega_{entrega_id}"

            with st.container(border=True):

                # ------------------------------------------
                # Cabeçalho do card
                # ------------------------------------------

                col1, col2 = st.columns([3, 1])

                with col1:

                    nome_entrega = entrega.get(
                        "nome_da_entrega",
                        "Entrega sem nome"
                    )

                    st.markdown(
                        f"**{nome_entrega}**"
                    )

                with col2:

                    # Menu de ações da entrega.
                    with st.container(
                        horizontal=True,
                        horizontal_alignment="right"
                    ):

                        with st.popover(
                            ":material/more_vert:",
                            width="content"
                        ):

                            # Cadastro de novo registro da entrega.
                            novo_registro = st.button(
                                "Novo registro de entrega",
                                icon=":material/add:",
                                type="tertiary",
                                key=f"novo_registro_entrega_{entrega_id}"
                            )

                            if novo_registro:
                                cadastrar_registro_entrega(entrega_id)



                            # Botão de ver detalhes.
                            ver_detalhes_entrega = st.button(
                                "Ver detalhes",
                                icon=":material/menu:",
                                type="tertiary",
                                key=f"ver_detalhes_entrega_{entrega_id}"
                            )

                            if ver_detalhes_entrega:
                                mostrar_detalhes_entrega(entrega_id)




                            # Edição da entrega utiliza o diálogo
                            # específico de gerenciamento já existente.
                            if not usuario_visitante:

                                editar_entrega = st.button(
                                    "Editar entrega",
                                    icon=":material/edit:",
                                    type="tertiary",
                                    key=f"editar_entrega_{entrega_id}"
                                )

                                if editar_entrega:
                                    dialog_editar_entrega(entrega_id)






                # ------------------------------------------
                # Responsáveis e projetos
                # ------------------------------------------

                with st.container(horizontal=True, horizontal_alignment="distribute"):


                    projetos_str = entrega.get(
                        "projetos_str",
                        ""
                    )

                    if projetos_str:

                        st.markdown(
                            f"**{projetos_str}**"
                        )

                    else:

                        st.markdown(
                            "Projeto não informado"
                        )



                    responsaveis = entrega.get(
                        "responsaveis",
                        ""
                    )

                    if responsaveis:

                        st.markdown(
                            f":material/group: {responsaveis}"
                        )

                    else:

                        st.markdown(
                            ":material/group: Não informado"
                        )













                # # ------------------------------------------
                # # Responsáveis e projetos
                # # ------------------------------------------

                # col1, col2 = st.columns(2)

                # with col1:

                #     responsaveis = entrega.get(
                #         "responsaveis",
                #         ""
                #     )

                #     if responsaveis:

                #         st.markdown(
                #             f"**Responsável(is):** {responsaveis}"
                #         )

                #     else:

                #         st.markdown(
                #             "**Responsável(is):** Não informado"
                #         )


                # with col2:

                #     projetos_siglas = []

                #     # Inclui o projeto de origem da entrega.
                #     projeto_origem_sigla = entrega.get(
                #         "_projeto_origem_sigla",
                #         ""
                #     )

                #     if projeto_origem_sigla:

                #         projetos_siglas.append(
                #             projeto_origem_sigla
                #         )

                #     # Inclui os demais projetos relacionados.
                #     projetos_relacionados = entrega.get(
                #         "projetos_relacionados",
                #         []
                #     )

                #     for projeto_id in projetos_relacionados:

                #         projeto_sigla = projetos_dict.get(
                #             str(projeto_id),
                #             ""
                #         )

                #         if projeto_sigla:
                #             projetos_siglas.append(
                #                 projeto_sigla
                #             )

                #     if projetos_siglas:

                #         st.markdown(
                #             f"**Projetos(s):** {', '.join(projetos_siglas)}"
                #         )

                #     else:

                #         st.markdown(
                #             "**Projetos(s):** Não informado"
                #         )
















                # # ------------------------------------------
                # # Responsáveis
                # # ------------------------------------------

                # responsaveis = entrega.get(
                #     "responsaveis",
                #     ""
                # )

                # if responsaveis:

                #     st.markdown(
                #         f"**Responsável(is):** {responsaveis}"
                #     )

                # else:

                #     st.markdown(
                #         "**Responsável(is):** Não informado"
                #     )

                # ------------------------------------------
                # Informações resumidas
                # ------------------------------------------

                with st.container(
                    horizontal=True,
                    horizontal_alignment="distribute"
                ):

                    situacao = entrega.get(
                        "situacao",
                        "Não informada"
                    )

                    st.markdown(
                        f"**Situação:** {situacao}"
                    )

                    previsao = entrega.get(
                        "previsao_da_conclusao_str",
                        ""
                    )

                    if previsao:

                        st.markdown(
                            f":material/schedule: {previsao}"
                        )

                    # ------------------------------------------
                    # Registros
                    # ------------------------------------------

                    lancamentos = entrega.get(
                        "lancamentos_entregas",
                        []
                    )

                    if not isinstance(lancamentos, list):
                        lancamentos = []

                    quantidade_lancamentos = len(lancamentos)

                    if quantidade_lancamentos == 0:

                        st.markdown(
                            '<span style="color:#F59E0B;"><i>Nenhum registro</i></span>',
                            unsafe_allow_html=True
                        )

                    else:

                        texto_registros = (
                            "registro"
                            if quantidade_lancamentos == 1
                            else "registros"
                        )

                        st.checkbox(
                            f"**Ver {quantidade_lancamentos} {texto_registros} >>**",
                            key=chave_checkbox,
                            on_change=alterar_entrega_selecionada,
                            args=(entrega_id,)
                        )

                # ------------------------------------------
                # Progresso
                # ------------------------------------------

                progresso = entrega.get(
                    "progresso",
                    0
                )

                try:
                    progresso = float(progresso)
                except (TypeError, ValueError):
                    progresso = 0

                progresso = max(
                    0,
                    min(100, progresso)
                )

                st.progress(
                    progresso / 100,
                    text=f"Progresso: {progresso:.0f}%"
                )

    # ==================================================
    # ENTREGA SELECIONADA
    # ==================================================

    entrega_selecionada_id = st.session_state.get(
        "entrega_selecionada_id"
    )

    entrega_selecionada = None

    if entrega_selecionada_id:

        for _, entrega in df.iterrows():

            if str(entrega["entrega_id"]) == str(
                entrega_selecionada_id
            ):

                entrega_selecionada = entrega
                break








    # ==================================================
    # COLUNA DIREITA — REGISTROS
    # ==================================================

    with col_registros:



        st.markdown("#### Registros de Entrega:")

        # Nenhuma entrega selecionada: mantém a área vazia,
        # exibindo somente as orientações de seleção.
        if entrega_selecionada is None:

            st.caption(
                "Selecione uma Entrega na coluna da esquerda"
            )

            st.caption(
                "Clique em :material/select_check_box: **Ver x registros**."
            )

        else:

            # Identificação da entrega selecionada.
            nome_entrega = entrega_selecionada.get(
                "nome_da_entrega",
                "Entrega sem nome"
            )

            st.markdown(
                f"##### {nome_entrega}"
            )

            # Obtém somente os registros pertencentes à entrega selecionada.
            lancamentos = entrega_selecionada.get(
                "lancamentos_entregas",
                []
            )

            if not isinstance(lancamentos, list):
                lancamentos = []

            if not lancamentos:

                st.caption(
                    "Nenhum registro cadastrado para esta entrega."
                )

            else:


                for lancamento in lancamentos:

                    with st.container(border=True):

                        # Cabeçalho do registro.
                        with st.container(
                            horizontal=True,
                            horizontal_alignment="distribute"
                        ):

                            with st.container(
                                horizontal=True
                            ):

                                ano = lancamento.get(
                                    "ano",
                                    "Não informado"
                                )

                                autor = lancamento.get(
                                    "autor",
                                    "Não informado"
                                )

                                st.caption(
                                    f"**{ano}** | Registrado por **{autor}**"
                                )

                            # Menu de ações do registro.
                            with st.popover(
                                ":material/more_vert:",
                                width="content"
                            ):

                                # Botão de mostrar detalhes do registro

                                ver_detalhes_registro = st.button(
                                    "Ver detalhes",
                                    icon=":material/list:",
                                    type="tertiary",
                                    key=f"ver_detalhes_registro_{lancamento['_id']}"
                                )

                                if ver_detalhes_registro:
                                    mostrar_detalhes_registro_entrega(
                                        str(lancamento["_id"]),
                                        str(entrega_selecionada["entrega_id"])
                                    )


                                # Botão de editar o registro
                                editar_registro = st.button(
                                    "Editar registro",
                                    icon=":material/edit:",
                                    type="tertiary",
                                    key=f"editar_registro_{lancamento['_id']}"
                                )

                                if editar_registro:

                                    editar_registro_entrega(
                                        str(lancamento["_id"]),
                                        str(entrega_selecionada["entrega_id"])
                                    )

                        # Anotações do registro.
                        anotacoes = lancamento.get(
                            "anotacoes",
                            ""
                        )

                        if anotacoes:

                            st.write(anotacoes)

                        else:

                            st.caption(
                                "Sem anotações cadastradas."
                            )








# ##########################################################
# INTERFACE
# ##########################################################


st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


st.header("Entregas")

st.write("")

# ==========================================================
# VERIFICAÇÃO DE ENTREGAS ATRASADAS
# ==========================================================

if "verificacao_entregas_data" not in st.session_state:
    st.session_state["verificacao_entregas_data"] = None

if st.session_state["verificacao_entregas_data"] != hoje:

    verificar_entregas_atrasadas()

    st.session_state["verificacao_entregas_data"] = hoje
    st.session_state["verificacao_entregas_rodou"] = True

else:
    st.session_state["verificacao_entregas_rodou"] = False

# Montagem do df_entregas
df_entregas = carregar_entregas()

# Converter as coluans de id para string
df_entregas["responsaveis_ids"] = df_entregas["responsaveis_ids"].apply(lambda x: [str(i) for i in x])


df_entregas_lista = df_entregas.copy()




st.write("")
st.write("")
st.write("")

# ==========================================================
# FILTROS
# ==========================================================

with st.form("filtros_entregas", border=False):

    col1, col2, col3 = st.columns(3)

    # -------- Projetos --------
    projetos_opcoes = sorted({
        projeto
        for lista in df_entregas["projetos"]
        for projeto in (lista if isinstance(lista, list) else [])
        if projeto
    })

    with col1:
        filtro_projetos = st.multiselect(
            "Projetos",
            options=projetos_opcoes,
            placeholder=""
        )

    # -------- Status --------
    status_opcoes = sorted(
        df_entregas["situacao"]
        .dropna()
        .unique()
        .tolist()
    )

    with col2:
        filtro_status = st.multiselect(
            "Situação",
            options=status_opcoes,
            placeholder=""
        )

    # -------- Programas --------
    programas_opcoes = sorted({
        prog
        for lista in df_entregas["programa"]
        for prog in (lista if isinstance(lista, list) else [])
        if prog
    })

    with col3:
        filtro_programas = st.multiselect(
            "Programa",
            options=programas_opcoes,
            placeholder=""
        )

    col1, col2 = st.columns(2)

        # -------- Datas de Início e Fim --------

    with col1:
        filtro_data_inicio = st.date_input(
            "Data de início",
            value=None,
            format="DD/MM/YYYY"
        )

    with col2:
        filtro_data_fim = st.date_input(
            "Previsão de conclusão",
            value=None,
            format="DD/MM/YYYY"
        )

    aplicar = st.form_submit_button(
        "Aplicar filtros",
        icon=":material/filter_alt:"
    )

# ==========================================================
# APLICAÇÃO DOS FILTROS
# ==========================================================

df_filtrado = df_entregas.copy()

if filtro_projetos:
    df_filtrado = df_filtrado[
        df_filtrado["projetos"].apply(
            lambda lista: any(
                projeto in filtro_projetos
                for projeto in (lista if isinstance(lista, list) else [])
            )
        )
    ]

if filtro_status:
    df_filtrado = df_filtrado[
        df_filtrado["situacao"].isin(filtro_status)
    ]

if filtro_programas:
    df_filtrado = df_filtrado[
        df_filtrado["programa"].apply(
            lambda lista: any(p in filtro_programas for p in lista)
        )
    ]

if filtro_data_inicio:
    df_filtrado = df_filtrado[
        df_filtrado["data_inicio"].notna() &
        (df_filtrado["data_inicio"] >= pd.to_datetime(filtro_data_inicio))
    ]

if filtro_data_fim:
    df_filtrado = df_filtrado[
        df_filtrado["previsao_da_conclusao"].notna() &
        (df_filtrado["previsao_da_conclusao"] <= pd.to_datetime(filtro_data_fim))
    ]

# DataFrame usado nas abas
df_entregas_filtrado = df_filtrado.copy()

st.write("")





# Verifica se o usuário é visitante
usuario_visitante = "visitante" in st.session_state.get("tipo_usuario", [])





# Abas

lista_entregas, cronograma_entregas = st.tabs(["Entregas","Cronograma"])




# --------------------------------------------------
# Interface de entregas e registros
# --------------------------------------------------

with lista_entregas:



    render_entregas()






with cronograma_entregas:

    st.caption("Somente entregas com data de início cadastrada são exibidas no cronograma.")
    grafico_cronograma(
        df_entregas_filtrado,
        "Cronograma de Entregas"
    )