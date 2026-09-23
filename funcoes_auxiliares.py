import streamlit as st
from pymongo import MongoClient
import time
import pandas as pd
from datetime import datetime
from bson import ObjectId
import bson


# Google Drive API
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


@st.cache_resource
def conectar_mongo_portal_ispn():
    cliente = MongoClient(
    st.secrets["senhas"]["senha_mongo_portal_ispn"])
    db_portal_ispn = cliente["ISPN_Hub"]                   
    return db_portal_ispn


@st.cache_resource
def conectar_mongo_pls():
    cliente_2 = MongoClient(
    st.secrets["senhas"]["senha_mongo_pls"])
    db_pls = cliente_2["db_pls"]
    return db_pls



# VERSÃO NOVA
def altura_dataframe(df, linhas_adicionais=1):
    """
    Calcula a altura ideal para st.dataframe,
    garantindo que todas as linhas fiquem visíveis
    sem barra de rolagem.

    Parâmetros:
    - df: DataFrame exibido no dataframe
    - linhas_adicionais: linhas extras de folga (default=1)

    Retorna:
    - altura em pixels (int)
    """

    ALTURA_LINHA = 35      # altura média de cada linha
    ALTURA_HEADER = 38    # cabeçalho do dataframe

    try:
        total_linhas = len(df) + linhas_adicionais
    except Exception:
        total_linhas = linhas_adicionais

    altura = (total_linhas * ALTURA_LINHA) + ALTURA_HEADER

    return altura



# VERSÃO ANTIGA
def ajustar_altura_dataframe(
    df_nao_atualizado,
    linhas_adicionais=0,
    altura_maxima=None,  # Se None, não aplica limite
    #width="stretch",
    hide_index=True,
    column_config={
        "Link": st.column_config.Column(
            width="medium"  
        ),
        "Data da Última Ação Legislativa": st.column_config.Column(
            label="Última ação",  
        )
    }
):
    """
    Ajusta a altura da exibição de um DataFrame no Streamlit com base no número de linhas.
    Se 'altura_maxima' for informado, limita a altura até esse valor.
    """

    # Define a altura em pixels de cada linha
    altura_por_linha = 35  

    # Calcula a altura total necessária
    altura_total = ((df_nao_atualizado.shape[0] + linhas_adicionais) * altura_por_linha) + 2

    # Se altura_maxima foi informada, aplica o limite
    if altura_maxima is not None:
        altura_total = min(altura_total, altura_maxima)

    # Exibe o DataFrame no Streamlit
    st.dataframe(
        df_nao_atualizado,
        height=altura_total,
        #width=width,
        hide_index=hide_index,
        column_config=column_config
    )



# --- Conversor string brasileira -> float ---
def br_to_float(valor_str: str) -> float:
    """
    Converte string no formato brasileiro (1.234,56) para float (1234.56).
    """
    if not valor_str or not isinstance(valor_str, str):
        return 0.00
    # Remove pontos (milhares) e troca vírgula por ponto
    valor_str = valor_str.replace(".", "").replace(",", ".")
    try:
        return round(float(valor_str), 2)
    except ValueError:
        return 0.00


# --- Conversor float -> string brasileira ---
def float_to_br(valor_float: float) -> str:
    """
    Converte float (1234.56) para string no formato brasileiro (1.234,56).
    """
    if valor_float is None:
        return "0,00"
    return f"{valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")



def normalizar_texto(txt):
    if not txt:
        return None
    return " ".join(txt.split())

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





# Função do diálogo para exibição dos detalhes da entrega
@st.dialog("Detalhes da Entrega", width="large", on_dismiss="rerun")
def mostrar_detalhes_entrega():

    # Recupera os dados da entrega selecionada pelo botão acionado.
    entrega_id = st.session_state.get("entrega_detalhes_id")

    if not entrega_id:
        st.warning("Entrega não encontrada.")
        return

    # Recupera o projeto atualmente selecionado.
    projeto_selecionado = st.session_state.get(
        "projeto_selecionado_projetos"
    )

    if not projeto_selecionado:
        st.warning("Projeto não encontrado.")
        return

    # Conecta ao banco somente para consultar os dados necessários.
    db = conectar_mongo_portal_ispn()

    projeto = db["projetos_ispn"].find_one(
        {"sigla": projeto_selecionado}
    )

    if not projeto:
        st.warning("Projeto não encontrado no banco de dados.")
        return

    # Localiza a entrega dentro do projeto selecionado.
    entrega = None

    for item in projeto.get("entregas", []):

        if str(item.get("_id")) == str(entrega_id):
            entrega = item
            break

    if not entrega:
        st.warning("Entrega não encontrada no projeto.")
        return

    # --------------------------------------------------
    # Mapas auxiliares
    # --------------------------------------------------

    mapa_pessoas = {
        str(p["_id"]): p.get(
            "nome_completo",
            "Nome não informado"
        )
        for p in db["pessoas"].find()
    }

    mapa_indicadores = {
        str(i["_id"]): i
        for i in db["indicadores"].find()
    }

    mapa_projetos = {
        str(p["_id"]): p.get(
            "nome_do_projeto",
            p.get("sigla", "Projeto não informado")
        )
        for p in db["projetos_ispn"].find()
    }

    mapa_acoes = {
        str(a["_id"]): a
        for a in db["acoes_estrategicas"].find()
    }

    # --------------------------------------------------
    # Dados principais da entrega
    # --------------------------------------------------

    nome_entrega = entrega.get(
        "nome_da_entrega",
        "Entrega sem nome"
    )

    situacao = entrega.get(
        "situacao",
        "Não informada"
    )

    progresso = entrega.get(
        "progresso",
        0
    )

    data_inicio = entrega.get(
        "data_inicio",
        "Não informada"
    )

    previsao = entrega.get(
        "previsao_da_conclusao",
        "Não informada"
    )

    # --------------------------------------------------
    # Responsáveis
    # --------------------------------------------------

    responsaveis = entrega.get(
        "responsaveis",
        []
    )

    if not isinstance(responsaveis, list):
        responsaveis = []

    nomes_responsaveis = []

    for responsavel_id in responsaveis:

        nome = mapa_pessoas.get(
            str(responsavel_id)
        )

        if nome:
            nomes_responsaveis.append(nome)

    responsaveis_texto = (
        ", ".join(nomes_responsaveis)
        if nomes_responsaveis
        else "Nenhum responsável informado"
    )

    # --------------------------------------------------
    # Indicadores relacionados
    # --------------------------------------------------

    indicadores_ids = entrega.get(
        "indicadores_relacionados",
        []
    )

    if not isinstance(indicadores_ids, list):
        indicadores_ids = []

    nomes_indicadores = []

    for indicador_id in indicadores_ids:

        indicador = mapa_indicadores.get(
            str(indicador_id)
        )

        if indicador:

            nome_indicador = (
                indicador.get("nome")
                or indicador.get("nome_indicador")
                or indicador.get("descricao")
                or str(indicador_id)
            )

            nomes_indicadores.append(
                nome_indicador
            )

    # --------------------------------------------------
    # Projetos relacionados
    # --------------------------------------------------

    projetos_ids = entrega.get(
        "projetos_relacionados",
        []
    )

    if not isinstance(projetos_ids, list):
        projetos_ids = []

    nomes_projetos = []

    for projeto_id in projetos_ids:

        nome_projeto = mapa_projetos.get(
            str(projeto_id)
        )

        if nome_projeto:
            nomes_projetos.append(
                nome_projeto
            )

    # --------------------------------------------------
    # Ações estratégicas relacionadas
    # --------------------------------------------------

    acoes_ids = entrega.get(
        "acoes_estrat_programa",
        []
    )

    if not isinstance(acoes_ids, list):
        acoes_ids = []

    nomes_acoes = []

    for acao_id in acoes_ids:

        acao = mapa_acoes.get(
            str(acao_id)
        )

        if acao:

            nome_acao = (
                acao.get("nome")
                or acao.get("nome_acao")
                or acao.get("descricao")
                or str(acao_id)
            )

            nomes_acoes.append(
                nome_acao
            )

    # --------------------------------------------------
    # Apresentação
    # --------------------------------------------------

    st.markdown(
        f"### {nome_entrega}"
    )

    st.write("")

    col1, col2 = st.columns(
        [1, 1],
        gap="medium"
    )

    # ==================================================
    # COLUNA 1 — INFORMAÇÕES DA ENTREGA
    # ==================================================

    with col1:





        st.write(
            f"**Responsável(is):** {responsaveis_texto}"
        )



        st.write('')


        sub_col1, sub_col2 = st.columns(2        )


        sub_col1.write(
            "**Data de início:**"
        )

        sub_col1.write(
            "**Previsão de conclusão:**"
        )


        sub_col2.write(
            f"{data_inicio}"
        )


        sub_col2.write(
            f"{previsao}"
        )

        st.write('')


        st.write(
            f"**Situação:** {situacao}"
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
    # COLUNA 2 — RELAÇÕES E RESPONSABILIDADES
    # ==================================================

    with col2:


        st.write(
            "**Indicadores relacionados:**"
        )

        if nomes_indicadores:

            for nome in nomes_indicadores:
                st.write(
                    f"- {nome}"
                )

        else:

            st.caption(
                "Nenhum indicador relacionado."
            )

        st.write(
            "**Projetos relacionados:**"
        )

        if nomes_projetos:

            for nome in nomes_projetos:
                st.write(
                    f"- {nome}"
                )

        else:

            st.caption(
                "Nenhum projeto relacionado."
            )

        st.write(
            "**Ações estratégicas do programa relacionadas:**"
        )

        if nomes_acoes:

            for nome in nomes_acoes:
                st.write(
                    f"- {nome}"
                )

        else:

            st.caption(
                "Nenhuma ação estratégica relacionada."
            )





# ##########################################################
# Diálogo para edição de uma entrega específica
# ##########################################################


@st.dialog("Editar entrega", width="large", on_dismiss="rerun")
def dialog_editar_entrega(entrega_id):

    # Conexão com as coleções utilizadas no formulário.
    db = conectar_mongo_portal_ispn()

    projetos_ispn = db["projetos_ispn"]
    programas = db["programas_areas"]
    indicadores = db["indicadores"]
    pessoas = db["pessoas"]

    # Converte o identificador recebido pelo Streamlit para ObjectId.
    try:
        entrega_object_id = ObjectId(entrega_id)
    except Exception:
        st.error("Identificador da entrega inválido.")
        return

    # Localiza o projeto que contém a entrega selecionada.
    projeto = projetos_ispn.find_one(
        {
            "entregas._id": entrega_object_id
        }
    )

    if not projeto:
        st.error("Projeto da entrega não encontrado.")
        return

    # Localiza a entrega dentro do projeto encontrado.
    entrega = next(
        (
            item
            for item in projeto.get("entregas", [])
            if item.get("_id") == entrega_object_id
        ),
        None
    )

    if not entrega:
        st.error("Entrega não encontrada.")
        return

    # ----------------------------------------------------------
    # Dados básicos do projeto de origem
    # ----------------------------------------------------------

    projeto_id = projeto["_id"]
    projeto_sigla = projeto.get("sigla", "")

    # ----------------------------------------------------------
    # Mapa de pessoas
    # ----------------------------------------------------------

    pessoas_dict = {
        str(p["_id"]): p.get("nome_completo", "")
        for p in pessoas.find(
            {},
            {
                "_id": 1,
                "nome_completo": 1
            }
        )
    }

    # ----------------------------------------------------------
    # Mapa de projetos
    # ----------------------------------------------------------

    projetos_dict = {
        str(p["_id"]): p.get("sigla", "")
        for p in projetos_ispn.find(
            {},
            {
                "_id": 1,
                "sigla": 1,
                "programas": 1
            }
        )
    }

    # ----------------------------------------------------------
    # Mapa de indicadores
    # ----------------------------------------------------------

    indicadores_dict = {
        str(indicador["_id"]): indicador.get(
            "nome_indicador",
            ""
        )
        for indicador in indicadores.find(
            {},
            {
                "_id": 1,
                "nome_indicador": 1
            }
        )
    }

    indicadores_options = sorted(
        indicadores_dict.keys(),
        key=lambda x: indicadores_dict[x].lower()
    )

    # ----------------------------------------------------------
    # Projetos relacionados
    # ----------------------------------------------------------

    projetos_relacionados_existentes = [
        str(pid)
        for pid in entrega.get(
            "projetos_relacionados",
            []
        )
    ]

    projetos_relacionados_options = sorted(
        [
            projeto_id_str
            for projeto_id_str in projetos_dict.keys()
            if projeto_id_str != str(projeto_id)
        ],
        key=lambda x: projetos_dict[x].lower()
    )

    # ----------------------------------------------------------
    # Programas envolvidos na entrega
    # ----------------------------------------------------------

    programas_ids = set()

    # Programa(s) do projeto de origem.
    programas_projeto = projeto.get("programas", [])

    if not isinstance(programas_projeto, list):
        programas_projeto = []

    for programa_id in programas_projeto:

        programas_ids.add(
            str(programa_id)
        )

    # Programas dos projetos relacionados.
    for projeto_relacionado_id in projetos_relacionados_existentes:

        projeto_relacionado = projetos_ispn.find_one(
            {
                "_id": ObjectId(projeto_relacionado_id)
            },
            {
                "programas": 1
            }
        )

        if not projeto_relacionado:
            continue

        programas_relacionados = projeto_relacionado.get(
            "programas",
            []
        )

        if not isinstance(programas_relacionados, list):
            continue

        for programa_id in programas_relacionados:

            programas_ids.add(
                str(programa_id)
            )

    # ----------------------------------------------------------
    # Ações estratégicas dos programas envolvidos
    # ----------------------------------------------------------

    mapa_acoes_programa = {}
    mapa_programa_acao = {}

    for programa in programas.find():

        programa_id = str(programa["_id"])

        if programa_id not in programas_ids:
            continue

        nome_programa = programa.get(
            "nome_programa_area",
            ""
        )

        for acao in programa.get(
            "acoes_estrategicas",
            []
        ):

            acao_id = str(acao["_id"])

            mapa_acoes_programa[acao_id] = acao.get(
                "acao_estrategica",
                ""
            )

            mapa_programa_acao[acao_id] = nome_programa

    # Ordena primeiro pelo programa e depois pela ação.
    acoes_programa_options = sorted(
        mapa_acoes_programa.keys(),
        key=lambda x: (
            mapa_programa_acao.get(x, "").lower(),
            mapa_acoes_programa.get(x, "").lower()
        )
    )

    # ----------------------------------------------------------
    # Valores atualmente cadastrados
    # ----------------------------------------------------------

    responsaveis_existentes = [
        str(r)
        for r in entrega.get(
            "responsaveis",
            []
        )
    ]

    acoes_existentes = [
        str(a)
        for a in entrega.get(
            "acoes_estrat_programa",
            []
        )
    ]

    indicadores_existentes = [
        str(i)
        for i in entrega.get(
            "indicadores_relacionados",
            []
        )
    ]

    # ----------------------------------------------------------
    # Identificação da entrega
    # ----------------------------------------------------------

    st.caption(
        f"Projeto: **{projeto_sigla}**"
    )

    st.write("")



    # ----------------------------------------------------------
    # Formulário de edição
    # ----------------------------------------------------------

    nome_da_entrega = st.text_input(
        "Nome da entrega",
        value=entrega.get(
            "nome_da_entrega",
            ""
        )
    )

    col1, col2 = st.columns(2)

    # Data de início atual.
    data_inicio_raw = entrega.get(
        "data_inicio"
    )

    data_inicio = None

    if data_inicio_raw:

        data_inicio_convertida = pd.to_datetime(
            data_inicio_raw,
            format="%d/%m/%Y",
            errors="coerce"
        )

        if not pd.isna(data_inicio_convertida):
            data_inicio = data_inicio_convertida.date()

    data_inicio = col1.date_input(
        "Data de início",
        value=data_inicio,
        format="DD/MM/YYYY"
    )

    # Data de conclusão atual.
    data_fim_raw = entrega.get(
        "previsao_da_conclusao"
    )

    data_fim = None

    if data_fim_raw:

        data_fim_convertida = pd.to_datetime(
            data_fim_raw,
            format="%d/%m/%Y",
            errors="coerce"
        )

        if not pd.isna(data_fim_convertida):
            data_fim = data_fim_convertida.date()

    data_fim = col2.date_input(
        "Previsão de conclusão",
        value=data_fim,
        format="DD/MM/YYYY"
    )

    col1, col2 = st.columns(2)

    situacoes = [
        "Prevista",
        "Atrasada",
        "Concluída"
    ]

    situacao_atual = entrega.get(
        "situacao",
        "Prevista"
    )

    if situacao_atual not in situacoes:
        situacao_atual = "Prevista"

    situacao = col1.selectbox(
        "Situação",
        options=situacoes,
        index=situacoes.index(
            situacao_atual
        )
    )

    opcoes_progresso = [
        0,
        10,
        20,
        30,
        40,
        50,
        60,
        70,
        80,
        90,
        100
    ]

    progresso_atual = entrega.get(
        "progresso",
        0
    )

    try:
        progresso_atual = int(progresso_atual)
    except (TypeError, ValueError):
        progresso_atual = 0

    if progresso_atual not in opcoes_progresso:
        progresso_atual = 0

    progresso = col2.selectbox(
        "Progresso",
        options=opcoes_progresso,
        index=opcoes_progresso.index(
            progresso_atual
        ),
        format_func=lambda x: f"{x}%"
    )

    col1, col2 = st.columns(2)

    with col1:

        responsaveis = st.multiselect(
            "Responsáveis",
            options=list(
                pessoas_dict.keys()
            ),
            default=[
                r
                for r in responsaveis_existentes
                if r in pessoas_dict
            ],
            format_func=lambda x: pessoas_dict.get(
                x,
                "Pessoa não encontrada"
            ),
            placeholder=""
        )

    with col2:

        projetos_relacionados = st.multiselect(
            "Demais projetos relacionados",
            options=projetos_relacionados_options,
            default=[
                p
                for p in projetos_relacionados_existentes
                if p in projetos_relacionados_options
            ],
            format_func=lambda x: projetos_dict.get(
                x,
                "Projeto não encontrado"
            ),
            placeholder=""
        )

    # ----------------------------------------------------------
    # Ações estratégicas
    # ----------------------------------------------------------

    acoes_estrat_programa = st.multiselect(
        "Contribui com quais ações estratégicas do programa/área?",
        options=acoes_programa_options,
        default=[
            a
            for a in acoes_existentes
            if a in acoes_programa_options
        ],
        format_func=lambda x: (
            f"[{mapa_programa_acao.get(x, '')}] "
            f"{mapa_acoes_programa.get(x, '')}"
        ),
        placeholder=""
    )

    # ----------------------------------------------------------
    # Indicadores
    # ----------------------------------------------------------

    indicadores_relacionados = st.multiselect(
        "Contribui com quais indicadores?",
        options=indicadores_options,
        default=[
            i
            for i in indicadores_existentes
            if i in indicadores_options
        ],
        format_func=lambda x: indicadores_dict.get(
            x,
            "Indicador não encontrado"
        ),
        placeholder=""
    )

    st.write("")

    salvar_edicao = st.button(
        "Salvar alterações",
        icon=":material/save:",
        width=200
    )





    # ----------------------------------------------------------
    # Salvamento das alterações
    # ----------------------------------------------------------

    if salvar_edicao:

        if not nome_da_entrega.strip():
            st.warning(
                "Informe o nome da entrega."
            )
            return

        # Mantém o formato de datas utilizado nos documentos existentes.
        data_inicio_salvar = (
            data_inicio.strftime("%d/%m/%Y")
            if data_inicio
            else None
        )

        data_fim_salvar = (
            data_fim.strftime("%d/%m/%Y")
            if data_fim
            else None
        )

        # Atualiza somente os campos editáveis da entrega.
        campos_atualizacao = {
            "entregas.$.nome_da_entrega": nome_da_entrega.strip(),
            "entregas.$.data_inicio": data_inicio_salvar,
            "entregas.$.previsao_da_conclusao": data_fim_salvar,
            "entregas.$.responsaveis": [
                ObjectId(r)
                for r in responsaveis
            ],
            "entregas.$.situacao": situacao,
            "entregas.$.progresso": int(progresso),
            "entregas.$.projetos_relacionados": [
                ObjectId(p)
                for p in projetos_relacionados
            ],
            "entregas.$.acoes_estrat_programa": [
                ObjectId(a)
                for a in acoes_estrat_programa
            ],
            "entregas.$.indicadores_relacionados": [
                ObjectId(i)
                for i in indicadores_relacionados
            ]
        }

        resultado = projetos_ispn.update_one(
            {
                "_id": projeto_id,
                "entregas._id": entrega_object_id
            },
            {
                "$set": campos_atualizacao
            }
        )

        if resultado.modified_count:

            st.success(
                "Entrega atualizada com sucesso!"
            )

            time.sleep(3)

            st.rerun()

        else:

            st.info(
                "Nenhuma alteração foi realizada."
            )
































# # Função do diálogo para edição ou cadastro de uma entrega
# @st.dialog("Editar Entrega", width="large", on_dismiss="rerun")
# def dialog_editar_entrega(projeto_id, entrega_id=None):

#     # Identifica o modo de operação conforme a existência da entrega.
#     modo_edicao = entrega_id is not None

#     # Conecta ao banco para consultar o projeto selecionado.
#     db = conectar_mongo_portal_ispn()

#     projeto = db["projetos_ispn"].find_one(
#         {"_id": bson.ObjectId(str(projeto_id))}
#     )

#     if not projeto:
#         st.error("Projeto não encontrado.")
#         return

#     # Localiza a entrega somente no modo de edição.
#     entrega = None

#     if modo_edicao:

#         for item in projeto.get("entregas", []):

#             if str(item.get("_id")) == str(entrega_id):
#                 entrega = item
#                 break

#         if entrega is None:
#             st.error("Entrega não encontrada.")
#             return




#     else:

#         # Estrutura inicial utilizada para um novo cadastro.
#         entrega = {}



#     # --------------------------------------------------
#     # Dados iniciais dos campos
#     # --------------------------------------------------

#     # --------------------------------------------------
#     # Pessoas disponíveis para seleção
#     # --------------------------------------------------

#     pessoas = list(
#         db["pessoas"].find(
#             {},
#             {
#                 "_id": 1,
#                 "nome_completo": 1,
#             }
#         )
#     )

#     mapa_pessoas = {
#         str(pessoa["_id"]): pessoa.get(
#             "nome_completo",
#             "Nome não informado"
#         )
#         for pessoa in pessoas
#     }

#     mapa_pessoas_inverso = {
#         nome: pessoa_id
#         for pessoa_id, nome in mapa_pessoas.items()
#     }

#     # Recupera os responsáveis atualmente associados à entrega.
#     responsaveis_ids = entrega.get(
#         "responsaveis",
#         []
#     )

#     if not isinstance(responsaveis_ids, list):
#         responsaveis_ids = []

#     responsaveis_ids = [
#         str(responsavel_id)
#         for responsavel_id in responsaveis_ids
#     ]

#     responsaveis_selecionados = [
#         mapa_pessoas[responsavel_id]
#         for responsavel_id in responsaveis_ids
#         if responsavel_id in mapa_pessoas
#     ]



#     # --------------------------------------------------
#     # Indicadores disponíveis para seleção
#     # --------------------------------------------------

#     indicadores = list(
#         db["indicadores"].find(
#             {},
#             {
#                 "_id": 1,
#                 "nome_indicador": 1,
#             }
#         )
#     )

#     mapa_indicadores = {
#         str(indicador["_id"]): indicador.get(
#             "nome_indicador",
#             "Indicador não informado"
#         )
#         for indicador in indicadores
#     }

#     # Recupera os indicadores atualmente associados à entrega.
#     indicadores_ids = entrega.get(
#         "indicadores_relacionados",
#         []
#     )

#     if not isinstance(indicadores_ids, list):
#         indicadores_ids = []

#     indicadores_ids = [
#         str(indicador_id)
#         for indicador_id in indicadores_ids
#     ]

#     indicadores_selecionados = [
#         mapa_indicadores[indicador_id]
#         for indicador_id in indicadores_ids
#         if indicador_id in mapa_indicadores
#     ]




#     # --------------------------------------------------
#     # Projetos disponíveis para seleção
#     # --------------------------------------------------

#     projetos = list(
#         db["projetos_ispn"].find(
#             {},
#             {
#                 "_id": 1,
#                 "sigla": 1,
#             }
#         )
#     )

#     mapa_projetos = {
#         str(projeto["_id"]): projeto.get(
#             "sigla",
#             "Projeto sem sigla"
#         )
#         for projeto in projetos
#     }

#     # Recupera os projetos atualmente associados à entrega.
#     projetos_ids = entrega.get(
#         "projetos_relacionados",
#         []
#     )

#     if not isinstance(projetos_ids, list):
#         projetos_ids = []

#     projetos_ids = [
#         str(projeto_id)
#         for projeto_id in projetos_ids
#     ]

#     projetos_selecionados = [
#         mapa_projetos[projeto_id]
#         for projeto_id in projetos_ids
#         if projeto_id in mapa_projetos
#     ]










#     nome_entrega = entrega.get(
#         "nome_da_entrega",
#         ""
#     )

#     data_inicio = entrega.get(
#         "data_inicio",
#         ""
#     )

#     previsao_conclusao = entrega.get(
#         "previsao_da_conclusao",
#         ""
#     )

#     situacao = entrega.get(
#         "situacao",
#         "Prevista"
#     )

#     progresso = entrega.get(
#         "progresso",
#         0
#     )

#     try:
#         progresso = int(progresso)
#     except (TypeError, ValueError):
#         progresso = 0

#     progresso = max(
#         0,
#         min(100, progresso)
#     )





#     # --------------------------------------------------
#     # Formulário
#     # --------------------------------------------------

#     with st.form("form_editar_entrega"):

#         col1, col2 = st.columns(
#             [1, 1],
#             gap="medium"
#         )

#         # ==================================================
#         # COLUNA 1 — INFORMAÇÕES DA ENTREGA
#         # ==================================================

#         with col1:

#             nome_entrega = st.text_input(
#                 "Nome da entrega",
#                 value=nome_entrega,
#             )

#             st.write("")

#             sub_col1, sub_col2 = st.columns(2)

#             with sub_col1:

#                 st.write("**Data de início:**")

#             with sub_col2:

#                 data_inicio = st.text_input(
#                     "Data de início",
#                     value=data_inicio,
#                     label_visibility="collapsed",
#                     placeholder="dd/mm/yyyy",
#                 )

#             st.write("")

#             sub_col1, sub_col2 = st.columns(2)

#             with sub_col1:

#                 st.write("**Previsão de conclusão:**")

#             with sub_col2:

#                 previsao_conclusao = st.text_input(
#                     "Previsão de conclusão",
#                     value=previsao_conclusao,
#                     label_visibility="collapsed",
#                     placeholder="dd/mm/yyyy",
#                 )

#             st.write("")

#             situacao = st.selectbox(
#                 "Situação",
#                 options=[
#                     "Prevista",
#                     "Atrasada",
#                     "Concluída",
#                 ],
#                 index=[
#                     "Prevista",
#                     "Atrasada",
#                     "Concluída",
#                 ].index(situacao)
#                 if situacao in [
#                     "Prevista",
#                     "Atrasada",
#                     "Concluída",
#                 ]
#                 else 0,
#             )

#             progresso = st.selectbox(
#                 "Progresso",
#                 options=list(range(0, 101, 10)),
#                 index=list(range(0, 101, 10)).index(
#                     progresso
#                 )
#                 if progresso in range(0, 101, 10)
#                 else 0,
#                 format_func=lambda valor: f"{valor}%",
#             )

#         # ==================================================
#         # COLUNA 2 — RELAÇÕES
#         # ==================================================

#         with col2:

#             responsaveis_selecionados = st.multiselect(
#                 "Responsável(is)",
#                 options=list(mapa_pessoas.values()),
#                 default=responsaveis_selecionados,
#             )

#             indicadores_selecionados = st.multiselect(
#                 "Indicadores relacionados",
#                 options=list(mapa_indicadores.values()),
#                 default=indicadores_selecionados,
#             )


#             projetos_selecionados = st.multiselect(
#                 "Projetos relacionados",
#                 options=list(mapa_projetos.values()),
#                 default=projetos_selecionados,
#             )




#         st.write("")

#         salvar = st.form_submit_button(
#             "Salvar",
#             icon=":material/save:",
#             type="primary",
#         )







# Função do diálogo para gerenciar entregas  VAI SER SUBSTITUÍDO PELO DIAĹOGO DE EDITAR SOMENTE UMA ENTREGA (ACIMA)
@st.dialog("Editar Entregas", width="large", on_dismiss="rerun")
def dialog_editar_entregas():

    pagina_atual = st.session_state.get("pagina_anterior")
    mostrar_lancamentos = (pagina_atual == "pagina_projetos")
    
    db = conectar_mongo_portal_ispn()
    estrategia = db["estrategia"]  
    programas = db["programas_areas"]
    projetos_ispn = db["projetos_ispn"]  
    indicadores = db["indicadores"]
    colecao_lancamentos = db["lancamentos_indicadores"]
    
    df_projetos_ispn = pd.DataFrame(list(projetos_ispn.find()))
    df_pessoas = pd.DataFrame(list(db["pessoas"].find()))
    df_indicadores = pd.DataFrame(list(indicadores.find()))

    def entrega_pode_ser_excluida(entrega: dict, projeto_id) -> bool:
        entrega_id = entrega.get("_id")

        if not entrega_id:
            return False

        # Verifica lançamentos EMBUTIDOS no projeto
        lancamentos_embutidos = entrega.get("lancamentos_entregas", [])
        if lancamentos_embutidos:
            return False

        # Verifica lançamentos persistidos na coleção
        qtd_registros = colecao_lancamentos.count_documents({
            "projeto": projeto_id,
            "id_lanc_entrega": entrega_id
        })

        return qtd_registros == 0

    
    # Garantir string do ObjectId (Streamlit trabalha melhor)
    df_indicadores["_id"] = df_indicadores["_id"].astype(str)

    # Mapa: id -> nome legível
    mapa_indicadores = dict(
        zip(df_indicadores["_id"], df_indicadores["nome_indicador"])
    )
    
    # Mapa: id -> tipo_variavel ("int", "float" ou "str")
    mapa_tipo_variavel = dict(
        zip(df_indicadores["_id"], df_indicadores["tipo_variavel"])
    )

    # Lista de IDs (o que será salvo)
    indicadores_options = sorted(mapa_indicadores.keys(), key=lambda x: mapa_indicadores[x])

    
    # --- 2. Criar dicionários de mapeamento ---
    mapa_doador = {d["_id"]: d["nome_doador"] for d in db["doadores"].find()}
    mapa_programa = {p["_id"]: p["nome_programa_area"] for p in db["programas_areas"].find()}

    # --- 3. Aplicar os mapeamentos ao df_projetos_ispn ---
    df_projetos_ispn["doador_nome"] = df_projetos_ispn["doador"].apply(
        lambda x: mapa_doador.get(x, "não informado")
    )



    # Converte lista de programas em nomes legíveis
    def resolver_programas(lista_programas):
        """
        Converte lista de ObjectIds de programas em string com nomes legíveis.

        Parâmetros:
            lista_programas (list | None): Lista de IDs de programas.

        Retorno:
            str: Nomes dos programas separados por vírgula.
        """
        if isinstance(lista_programas, list) and lista_programas:
            return ", ".join(
                mapa_programa.get(p, "não informado")
                for p in lista_programas
            )

        return "não informado"

    df_projetos_ispn["programa_nome"] = df_projetos_ispn["programas"].apply(resolver_programas)



    # --- 4. Converter datas para datetime
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
    def resolver_programa_area(valor):
        if isinstance(valor, list):
            return ", ".join(
                mapa_programa.get(str(v), "não informado")
                for v in valor
            )
        if valor:
            return mapa_programa.get(str(valor), "não informado")
        return "não informado"

    df_pessoas["programa_area_nome"] = df_pessoas["programa_area"].apply(resolver_programa_area)

    df_pessoas["coordenador_nome"] = df_pessoas["coordenador"].map(mapa_coordenador)
    df_pessoas = df_pessoas.sort_values(by="nome_completo", ascending=True).reset_index(drop=True)
    
    st.write("")

    # =========================
    # RESOLVER PROJETO (CORRETO)
    # =========================

    projetos_options = sorted(df_projetos_ispn["sigla"].dropna().unique().tolist())

    projeto_sigla = st.selectbox(
        "Selecione o projeto",
        options=[""] + projetos_options,
        key="projeto_selecionado_entregas"
    )

    if not projeto_sigla:
        st.info("Selecione um projeto para gerenciar as entregas.")
        return


    # Projeto já definido (veio da página)
    projeto_info = df_projetos_ispn.loc[
        df_projetos_ispn["sigla"] == projeto_sigla
    ].iloc[0]


    # ==========================================================
    # ENTREGAS DO PROJETO + ENTREGAS RELACIONADAS
    # ==========================================================

    entregas_existentes = []

    projeto_atual_id = ObjectId(projeto_info["_id"])

    # ----------------------------------------------------------
    # 1. Entregas do próprio projeto
    # ----------------------------------------------------------

    entregas_projeto = projeto_info.get("entregas", [])

    # Garante lista válida
    if not isinstance(entregas_projeto, list):
        entregas_projeto = []

    for entrega_original in entregas_projeto:

        entrega = dict(entrega_original)

        entrega["_projeto_origem_id"] = projeto_info["_id"]
        entrega["_projeto_origem_sigla"] = projeto_info.get("sigla", "")

        entregas_existentes.append(entrega)

    # ----------------------------------------------------------
    # 2. Entregas de outros projetos relacionadas a este
    # ----------------------------------------------------------
    outros_projetos = projetos_ispn.find({
        "_id": {"$ne": projeto_atual_id},
        "entregas.projetos_relacionados": projeto_atual_id
    })

    for proj in outros_projetos:

        entregas_proj = proj.get("entregas", [])

        # Garante lista válida
        if not isinstance(entregas_proj, list):
            entregas_proj = []

        for entrega_original in entregas_proj:

            projetos_rel = entrega_original.get(
                "projetos_relacionados",
                []
            )

            if projeto_atual_id in projetos_rel:

                entrega = dict(entrega_original)

                entrega["_projeto_origem_id"] = proj["_id"]
                entrega["_projeto_origem_sigla"] = proj.get("sigla", "")

                entregas_existentes.append(entrega)

    # Garante que entregas_existentes seja sempre uma lista
    if not isinstance(entregas_existentes, list):
        entregas_existentes = []
        
    dados_estrategia = list(estrategia.find({}))
    dados_programas = list(programas.find({}))

    # Recupera lista de programas vinculados ao projeto
    programas_do_projeto = projeto_info.get("programas", [])

    # Garante que sempre seja lista
    if not isinstance(programas_do_projeto, list):
        programas_do_projeto = []


    #mapa_resultados_mp = {}
    mapa_metas_mp = {}
    mapa_acoes_mp = {}
    mapa_acoes_lp = {}
    mapa_eixos = {}
    mapa_objetivos = {}
    eixos_da_estrategia = []

    # ==========================================================
    # RECUPERA TODOS OS PROGRAMAS DOS PROJETOS ENVOLVIDOS
    # ==========================================================

    mapa_acoes_programa = {}
    mapa_acoes_programa_formatadas = {}

    mapa_resultados_programa = {}
    mapa_resultados_programa_formatados = {}
    

    programas_ids = set()

    # ----------------------------------------------------------
    # 1. Programa(s) do projeto selecionado
    # ----------------------------------------------------------

    programas_projeto_principal = projeto_info.get("programas", [])

    if isinstance(programas_projeto_principal, list):

        for p in programas_projeto_principal:

            programas_ids.add(
                ObjectId(p) if isinstance(p, str) else p
            )

    # ----------------------------------------------------------
    # 2. Programa(s) dos projetos relacionados
    # ----------------------------------------------------------

    for entrega in entregas_existentes:

        projetos_relacionados = entrega.get(
            "projetos_relacionados",
            []
        )

        # Inclui também o projeto de origem da entrega
        projeto_origem = entrega.get("_projeto_origem_id")

        ids_projetos_considerados = list(projetos_relacionados)

        if projeto_origem:
            ids_projetos_considerados.append(projeto_origem)

        for projeto_id in ids_projetos_considerados:

            projeto_rel = projetos_ispn.find_one({
                "_id": ObjectId(projeto_id)
            })

            if not projeto_rel:
                continue

            programas_rel = projeto_rel.get("programas", [])

            if not isinstance(programas_rel, list):
                continue

            for prog in programas_rel:

                programas_ids.add(
                    ObjectId(prog)
                    if isinstance(prog, str)
                    else prog
                )

    # ==========================================================
    # MONTA MAPAS DE AÇÕES E RESULTADOS
    # ==========================================================

    for doc in dados_programas:

        if doc.get("_id") not in programas_ids:
            continue

        nome_programa = doc.get("nome_programa_area", "")

        # -----------------------------------------
        # AÇÕES ESTRATÉGICAS
        # -----------------------------------------
        for acao in doc.get("acoes_estrategicas", []):

            acao_id = str(acao["_id"])

            mapa_acoes_programa[acao_id] = acao.get(
                "acao_estrategica",
                ""
            )

            mapa_acoes_programa_formatadas[acao_id] = nome_programa

    # Mapeia ações estratégicas considerando múltiplos programas
    programas_ids = set(programas_do_projeto)

    acoes_programa_options = sorted(
        mapa_acoes_programa.keys(),
        key=lambda x: (
            mapa_acoes_programa_formatadas.get(x, "").lower(),
            mapa_acoes_programa.get(x, "").lower()
        )
    )
        
    #  Criar lista de opções (nome + _id) ordenadas alfabeticamente
    df_pessoas_ordenado = df_pessoas.sort_values("nome_completo", ascending=True)
    responsaveis_dict = {
        str(row["_id"]): row["nome_completo"]
        for _, row in df_pessoas_ordenado.iterrows()
    }
    responsaveis_options = list(responsaveis_dict.keys())

    # ==========================================================
    # PROJETOS RELACIONADOS
    # ==========================================================

    # Cria mapa: id -> sigla
    mapa_projetos = {
        str(row["_id"]): row["sigla"]
        for _, row in df_projetos_ispn.iterrows()
        if row.get("sigla")
    }

    # ==========================================================
    # REMOVE O PROJETO ATUAL DAS OPÇÕES
    # ==========================================================

    projeto_atual_id = str(projeto_info["_id"])

    # Lista de opções do multiselect sem o projeto atual
    projetos_relacionados_options = sorted(
        [
            projeto_id
            for projeto_id in mapa_projetos.keys()
            if projeto_id != projeto_atual_id
        ],
        key=lambda x: mapa_projetos[x]
    )
    
    if mostrar_lancamentos:
        aba_entregas, aba_lancamentos_entregas = st.tabs(
            [
                ":material/package_2: Gerenciar entregas",
                ":material/rocket_launch: Registros de entregas"
            ]
        )
    else:
        aba_entregas = st.container()
        st.write("")

    with aba_entregas:

        with st.expander("Adicionar entrega", expanded=False):
            with st.form("form_nova_entrega", border=False):
                
                nome_da_entrega = st.text_input("Nome da entrega")
                
                col1, col2 = st.columns(2)
                
                data_inicio = col1.date_input(
                    "Data de início",
                    value=datetime.today(),
                    format="DD/MM/YYYY"
                )

                previsao_da_conclusao = col2.date_input(
                    "Previsão de conclusão",
                    format="DD/MM/YYYY"
                )
               
                col1, col2 = st.columns(2)
                
                situacao = col1.selectbox("Situação", ["Prevista", "Atrasada", "Concluída"])
                
                opcoes_progresso = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
                
                progresso_nova_entrega = col2.selectbox(
                    "Progresso",
                    options=opcoes_progresso,
                    format_func=lambda x: f"{x}%",
                    key="progresso_nova_entrega"
                )
                
                col1, col2 = st.columns(2)

                with col1:
                    responsaveis_selecionados = st.multiselect(
                        "Responsáveis",
                        options=responsaveis_options,
                        format_func=lambda x: responsaveis_dict.get(x, "Desconhecido"),
                        placeholder=""
                    )

                with col2:
                    projetos_relacionados = st.multiselect(
                        "Demais projetos relacionados",
                        options=projetos_relacionados_options,
                        format_func=lambda x: mapa_projetos.get(x, "Projeto não encontrado"),
                        placeholder=""
                    )
                
                acoes_relacionados = st.multiselect(
                    "Contribui com quais ações estratégicas do programa/área?",
                    options=acoes_programa_options,
                    format_func=lambda x: (
                        f"[{mapa_acoes_programa_formatadas.get(x, '')}] "
                        f"{mapa_acoes_programa.get(x, '')}"
                    ),
                    placeholder="",
                    key="nova_acoesrel"
                )
                
                indicadores_relacionados = st.multiselect(
                    "Contribui com quais indicadores?",
                    options=indicadores_options, 
                    format_func=lambda x: mapa_indicadores.get(x, ""),
                    placeholder="",
                    key="nova_indrel"
                )

                st.write("")
                
                salvar_nova = st.form_submit_button("Salvar entrega", icon=":material/save:")
                if salvar_nova:
                    
                    if not nome_da_entrega:
                        st.warning("Por favor preencha o nome da entrega.")
                    
                    else:
                        
                        nova_entrega = {
                            "_id": ObjectId(),
                            "nome_da_entrega": nome_da_entrega,
                            "previsao_da_conclusao": previsao_da_conclusao.strftime("%d/%m/%Y"),
                            "responsaveis": [ObjectId(r) for r in responsaveis_selecionados],
                            "situacao": situacao,
                            "progresso": int(progresso_nova_entrega),
                            "data_inicio": data_inicio.strftime("%d/%m/%Y"),
                            "acoes_estrat_programa": [ObjectId(a) for a in acoes_relacionados],
                            "indicadores_relacionados": [ObjectId(i) for i in indicadores_relacionados],
                            "projetos_relacionados": [ObjectId(p) for p in projetos_relacionados],
                        }

                        # adiciona ao array existente
                        projetos_ispn.update_one(
                            {"_id": projeto_info["_id"]},
                            {"$push": {"entregas": nova_entrega}}
                        )

                        st.success("Entrega adicionada com sucesso!")
                        time.sleep(2)
                        st.rerun(scope="fragment")
                        

        # ============================
        # EXIBIR ENTREGAS EXISTENTES
        # ============================
        if entregas_existentes:
            st.write("### Entregas cadastradas:")

            for i, entrega in enumerate(entregas_existentes):

                entrega_id = str(entrega.get("_id", i))

                with st.expander(f"{entrega.get('nome_da_entrega', 'Sem nome')}"):
                    # Mostrar nomes reais dos responsáveis
                    responsaveis_ids = entrega.get("responsaveis", [])
                    responsaveis_nomes = [
                        responsaveis_dict.get(str(r), "Desconhecido") for r in responsaveis_ids
                    ]
                    responsaveis_formatados = ", ".join(responsaveis_nomes) if responsaveis_nomes else "-"

                    # Alternar entre visualização e edição
                    modo_edicao = st.toggle(
                        "Modo de edição",
                        key=f"toggle_edit_entrega_{entrega_id}"
                    )


                    if not modo_edicao:
                        # --- Modo de visualização ---
                        st.write(f"**Data de início:** {entrega.get('data_inicio', '-')}")
                        st.write(f"**Previsão de conclusão:** {entrega.get('previsao_da_conclusao', '-')}")
                        st.write(f"**Situação:** {entrega.get('situacao', '-')}")
                        
                        progresso = entrega.get("progresso", 0)
                        try:
                            progresso = int(progresso)
                        except (TypeError, ValueError):
                            progresso = 0
                        st.write(f"**Progresso:** {progresso}%")
                        
                        st.write(f"**Responsáveis:** {responsaveis_formatados}")

                        projetos_rel_ids = entrega.get("projetos_relacionados", [])

                        projetos_rel_nomes = [
                            mapa_projetos.get(str(p), "Projeto não encontrado")
                            for p in projetos_rel_ids
                        ]

                        projetos_rel_formatados = (
                            ", ".join(projetos_rel_nomes)
                            if projetos_rel_nomes else "-"
                        )

                        # Projeto principal/origem da entrega
                        projeto_principal = entrega.get(
                            "_projeto_origem_sigla",
                            projeto_info.get("sigla", "-")
                        )

                        st.write(f"**Projeto principal:** {projeto_principal}")

                        # Projetos relacionados
                        projetos_rel_ids = entrega.get("projetos_relacionados", [])

                        projetos_rel_nomes = [
                            mapa_projetos.get(str(p), "Projeto não encontrado")
                            for p in projetos_rel_ids
                        ]

                        projetos_rel_formatados = (
                            ", ".join(projetos_rel_nomes)
                            if projetos_rel_nomes else "-"
                        )

                        st.write(f"**Demais projetos relacionados:** {projetos_rel_formatados}")
                        
                        st.write("")
                        
                        # Ações estratégicas do programa
                        acoes = entrega.get("acoes_estrat_programa", [])
                        if acoes:
                            st.markdown("**Ações estratégicas do programa/área:**")
                            for a in acoes:
                                nome = mapa_acoes_programa.get(str(a), "Não encontrado")
                                st.markdown(f"- {nome}")
                        else:
                            st.markdown("**Ações estratégicas do programa/área:** -")
                        
                        st.write("")
                        
                        indicadores_entrega = entrega.get("indicadores_relacionados", [])
                        
                        if indicadores_entrega:
                            st.markdown("**Indicadores:**")
                            for i in indicadores_entrega:
                                nome = mapa_indicadores.get(str(i), "Indicador não encontrado")
                                st.markdown(f"- {nome}")
                                
                        else:
                            st.markdown("**Indicadores:** -")

                        st.write("")
                        
                    else:
                        # --- Modo de edição ---
                        with st.form(f"form_edit_entrega_{i}", border=False):
                            entrega_editada = {**entrega}

                            entrega_editada["nome_da_entrega"] = st.text_input(
                                "Nome da entrega", entrega.get("nome_da_entrega", "")
                            )
                            
                            col1, col2 = st.columns(2)

                            data_inicio_raw = entrega.get("data_inicio")

                            data_inicio_edit = col1.date_input(
                                "Data de início",
                                value=(
                                    pd.to_datetime(data_inicio_raw, format="%d/%m/%Y", errors="coerce").date()
                                    if data_inicio_raw else None
                                ),
                                format="DD/MM/YYYY"
                            )

                            entrega_editada["data_inicio"] = (
                                data_inicio_edit.strftime("%d/%m/%Y")
                                if data_inicio_edit else None
                            )

                            entrega_editada["previsao_da_conclusao"] = col2.date_input(
                                "Previsão de conclusão",
                                pd.to_datetime(entrega.get("previsao_da_conclusao"), format="%d/%m/%Y").date()
                                if entrega.get("previsao_da_conclusao") else datetime.today(),
                                format="DD/MM/YYYY"
                            )
                            entrega_editada["previsao_da_conclusao"] = entrega_editada["previsao_da_conclusao"].strftime("%d/%m/%Y")

                            col1, col2 = st.columns(2)

                            entrega_editada["situacao"] = col1.selectbox(
                                "Situação",
                                ["Prevista", "Atrasada", "Concluída"],
                                index=["Prevista", "Atrasada", "Concluída"].index(
                                    entrega.get("situacao", "Prevista")
                                )
                            )
                            
                            progresso_atual = entrega.get("progresso", 0)
                            try:
                                progresso_atual = int(progresso_atual)
                            except (TypeError, ValueError):
                                progresso_atual = 0
                                
                            entrega_editada["progresso"] = col2.selectbox(
                                "Progresso",
                                options=opcoes_progresso,
                                index=opcoes_progresso.index(progresso_atual) if progresso_atual in opcoes_progresso else 0,
                                format_func=lambda x: f"{x}%",
                                key=f"entrega_progresso_{i}"
                            )

                            col1, col2 = st.columns(2)

                            responsaveis_existentes = [
                                str(r) for r in entrega.get("responsaveis", [])
                            ]

                            # Projeto principal/origem da entrega
                            projeto_principal_id = str(entrega["_projeto_origem_id"])

                            # Verifica se a entrega está sendo editada dentro do projeto principal/origem
                            edicao_no_projeto_principal = (
                                str(entrega["_projeto_origem_id"]) == str(projeto_info["_id"])
                            )

                            # Se estiver no projeto principal:
                            # remove ele mesmo das opções
                            if edicao_no_projeto_principal:

                                projetos_relacionados_options_edicao = [
                                    p
                                    for p in projetos_relacionados_options
                                    if p != projeto_principal_id
                                ]

                            # Se estiver em um projeto relacionado:
                            # mantém todas as opções para exibição
                            else:

                                projetos_relacionados_options_edicao = (
                                    projetos_relacionados_options.copy()
                                )

                            # Projetos relacionados já salvos
                            projetos_relacionados_existentes = [
                                str(p)
                                for p in entrega.get("projetos_relacionados", [])
                                if str(p) in projetos_relacionados_options_edicao
                            ]

                            with col1:
                                entrega_editada["responsaveis"] = st.multiselect(
                                    "Responsáveis",
                                    options=list(responsaveis_dict.keys()),
                                    default=responsaveis_existentes,
                                    format_func=lambda x: responsaveis_dict.get(x, "Desconhecido"),
                                    placeholder="Selecione os responsáveis"
                                )

                            with col2:
                                entrega_editada["projetos_relacionados"] = st.multiselect(
                                    "Demais projetos relacionados",
                                    options=projetos_relacionados_options_edicao,
                                    default=projetos_relacionados_existentes,
                                    format_func=lambda x: mapa_projetos.get(
                                        x,
                                        "Projeto não encontrado"
                                    ),
                                    placeholder="",
                                    disabled=not edicao_no_projeto_principal
                                )

                            entrega_editada["projetos_relacionados"] = [
                                ObjectId(p)
                                for p in entrega_editada["projetos_relacionados"]
                            ]

                            entrega_editada["acoes_estrat_programa"] = [
                                ObjectId(a) for a in entrega_editada["acoes_estrat_programa"]
                            ]

                            acoes_programa_default = [
                                str(a)
                                for a in entrega.get("acoes_estrat_programa", [])
                                if str(a) in acoes_programa_options
                            ]

                            entrega_editada["acoes_estrat_programa"] = st.multiselect(
                                "Contribui com quais ações estratégicas do programa/área?",
                                options=acoes_programa_options,
                                default=acoes_programa_default,
                                format_func=lambda x: (
                                    f"[{mapa_acoes_programa_formatadas.get(x, '')}] "
                                    f"{mapa_acoes_programa.get(x, '')}"
                                ),
                                placeholder=""
                            )

                            entrega_editada["acoes_estrat_programa"] = [
                                ObjectId(a) for a in entrega_editada["acoes_estrat_programa"]
                            ]

                            default_ids = [str(i) for i in entrega.get("indicadores_relacionados", [])]

                            entrega_editada["indicadores_relacionados"] = st.multiselect(
                                "Contribui com quais indicadores?",
                                options=indicadores_options,
                                default=default_ids,
                                format_func=lambda x: mapa_indicadores.get(x, ""),
                                placeholder=""
                            )
                            
                            entrega_editada["indicadores_relacionados"] = [
                                ObjectId(i) for i in entrega_editada["indicadores_relacionados"]
                            ]
                            
                            st.write("")
                            
                            container_botoes = st.container(horizontal=True)

                            with container_botoes:

                                salvar_edicao = st.form_submit_button("Salvar alterações", icon=":material/save:")
                                if salvar_edicao:

                                    entrega_editada["responsaveis"] = [ObjectId(r) for r in entrega_editada["responsaveis"]]

                                    # Se NÃO estiver no projeto principal, não altera os projetos relacionados
                                    if not edicao_no_projeto_principal:

                                        entrega_editada["projetos_relacionados"] = (
                                            entrega.get("projetos_relacionados", [])
                                        )

                                    atualizar_entrega_no_projeto(
                                        entrega["_projeto_origem_id"],
                                        entrega_editada
                                    )
                                    
                                    st.success("Entrega atualizada!")
                                    time.sleep(2)
                                    st.rerun(scope="fragment")

                                pode_excluir = entrega_pode_ser_excluida(
                                    entrega,
                                    projeto_info["_id"]
                                )

                                if pode_excluir:

                                    excluir = st.form_submit_button(
                                        "Excluir entrega",
                                        type="secondary",
                                        icon=":material/delete:"
                                    )

                                    if excluir:
                                        projeto_origem = projetos_ispn.find_one(
                                            {"_id": entrega["_projeto_origem_id"]}
                                        )

                                        entregas_origem = projeto_origem.get("entregas", [])

                                        entregas_origem = [
                                            e for e in entregas_origem
                                            if e.get("_id") != entrega.get("_id")
                                        ]

                                        projetos_ispn.update_one(
                                            {"_id": entrega["_projeto_origem_id"]},
                                            {"$set": {"entregas": entregas_origem}}
                                        )

                                        st.success("Entrega excluída com sucesso.")
                                        time.sleep(2)
                                        st.rerun(scope="fragment")


    if mostrar_lancamentos:
        with aba_lancamentos_entregas:

            #st.subheader("Lançamentos de entregas")

            if not entregas_existentes:
                st.info("Este projeto ainda não possui entregas cadastradas.")
                return

            with st.expander("Adicionar registro", expanded=False):

                with st.form("form_adicionar_lancamento", border=False):

                    # =========================
                    # Selecionar entrega
                    # =========================
                    nomes_entregas = [e["nome_da_entrega"] for e in entregas_existentes]

                    entrega_selecionada_nome = st.selectbox(
                        "Selecione a entrega",
                        options=nomes_entregas
                    )

                    entrega_idx = nomes_entregas.index(entrega_selecionada_nome)
                    entrega = entregas_existentes[entrega_idx]

                    # =========================
                    # Dados do lançamento
                    # =========================
                    
                    ano_atual = datetime.now().year
                    ano_inicial = ano_atual - 1
                    ano_final = ano_atual + 6

                    anos_disponiveis = list(range(ano_inicial, ano_final + 1))
                    
                    ano_lancamento = st.selectbox(
                        "Ano do registro",
                        options=anos_disponiveis,
                        index=anos_disponiveis.index(ano_atual)
                    )

                    anotacoes_lancamento = st.text_area(
                        "Anotações"
                    )

                    st.divider()
                    st.markdown("### Lançamento de indicadores")

                    valores_indicadores = {}
                    indicadores_entrega = entrega.get("indicadores_relacionados", [])

                    for indicador in indicadores_entrega:
                        nome_indicador = mapa_indicadores.get(str(indicador), "Indicador não encontrado")
                        
                        tipo_variavel = mapa_tipo_variavel.get(str(indicador), "int")
                        
                        st.markdown(f"**{nome_indicador}**")
                        
                        col1, col2 = st.columns([2, 3])
                        if tipo_variavel == "float":
                            valor = col1.number_input(
                                "Valor",
                                step=0.01,
                                format="%.2f",
                                key=f"valor_{indicador}"
                            )
                        
                        elif tipo_variavel == "str":
                            valor = col1.text_input(
                                "Valor",
                                key=f"valor_{indicador}"
                            )
                        
                        else:  # int (fallback também para indicadores sem tipo_variavel definido)
                            valor = col1.number_input(
                                "Valor",
                                step=1,
                                format="%d",
                                key=f"valor_{indicador}"
                            )
                        
                        observacoes = col2.text_input(
                            "Observações",
                            key=f"obs_{indicador}"
                        )
                        
                        valores_indicadores[indicador] = {
                            "valor": valor,
                            "observacoes": observacoes
                        }
                        
                        st.divider()

                    # =========================
                    # SUBMIT
                    # =========================
                    salvar = st.form_submit_button(
                        "Salvar registro",
                        icon=":material/save:"
                    )


                if salvar:

                    if not ano_lancamento:
                        st.warning("Informe o ano do registro.")
                        return

                    novo_lancamento_entrega = {
                        "_id": ObjectId(),
                        "ano": str(ano_lancamento),
                        "anotacoes": anotacoes_lancamento,
                        "autor": st.session_state.get("nome")
                    }

                    id_lanc_entrega = novo_lancamento_entrega["_id"]

                    entregas_existentes[entrega_idx].setdefault(
                        "lancamentos_entregas", []
                    ).append(novo_lancamento_entrega)

                    projetos_ispn.update_one(
                        {"_id": projeto_info["_id"]},
                        {"$set": {"entregas": entregas_existentes}}
                    )

                    for indicador_id, dados in valores_indicadores.items():
                        
                        if dados["valor"] in ["", None, 0]:
                            continue
                        
                        tipo_variavel = mapa_tipo_variavel.get(str(indicador_id), "int")
                        
                        if tipo_variavel == "float":
                            valor_final = float(dados["valor"])
                        
                        elif tipo_variavel == "str":
                            valor_final = str(dados["valor"])
                        
                        else:
                            valor_final = int(dados["valor"])

                        colecao_lancamentos.insert_one({
                            "id_do_indicador": ObjectId(indicador_id),
                            "projeto": projeto_info["_id"],
                            "data_anotacao": datetime.now(),
                            "autor_anotacao": st.session_state.get("nome"),
                            "valor": valor_final,
                            "ano": str(ano_lancamento),
                            "observacoes": dados["observacoes"],
                            "tipo": "ispn",
                            "id_lanc_entrega": id_lanc_entrega
                        })

                    st.success("Registro salvo com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")
                    
            st.write("")
            st.markdown("### Registros cadastrados")
            st.write("")
            
            # Verifica se existe pelo menos um lançamento
            tem_registros = any(
                entrega.get("lancamentos_entregas", [])
                for entrega in entregas_existentes
            )

            if not tem_registros:
                st.caption("Nenhum registro nesta entrega.")
                
            else:
                st.write("")

                if "editar_lancamento_entrega_id" not in st.session_state:
                    st.session_state["editar_lancamento_entrega_id"] = None

                colunas = [1, 2, 2, 2, 1]

                # --------------------------------
                # Cabeçalho
                # --------------------------------
                c1, c2, c3, c4, c5 = st.columns(colunas)

                with c1:
                    st.markdown("**Ano**")

                with c2:
                    st.markdown("**Entrega**")

                with c3:
                    st.markdown("**Autor(a)**")

                with c4:
                    st.markdown("**Indicadores**")

                with c5:
                    st.markdown("")

                st.divider()

                # --------------------------------
                # Registros
                # --------------------------------
                for entrega_idx, entrega in enumerate(entregas_existentes):

                    nome_entrega = entrega.get("nome_da_entrega", "Entrega")

                    lancamentos = entrega.get("lancamentos_entregas", [])

                    for idx_lanc, lanc in enumerate(lancamentos):

                        c1, c2, c3, c4, c5 = st.columns(colunas)

                        with c1:
                            st.write(lanc.get("ano", ""))

                        with c2:
                            st.write(nome_entrega)

                        with c3:
                            st.write(lanc.get("autor", ""))

                        with c4:

                            with st.popover(
                                "Indicadores",
                                type="tertiary"
                            ):

                                id_lanc_entrega = lanc.get("_id")

                                registros_indicadores = list(
                                    colecao_lancamentos.find(
                                        {
                                            "id_lanc_entrega": ObjectId(id_lanc_entrega)
                                        }
                                    )
                                )

                                if not registros_indicadores:
                                    st.caption("Nenhum indicador lançado.")

                                else:

                                    for reg in registros_indicadores:
                                        nome_indicador = mapa_indicadores.get(
                                            str(reg["id_do_indicador"]),
                                            "Indicador não encontrado"
                                        )
                                        
                                        st.markdown(
                                            f"**{nome_indicador}:** "
                                            f"{reg.get('valor')}"
                                        )
                                        
                                        if reg.get("observacoes"):
                                            st.caption(reg["observacoes"])

                        with c5:

                            editar = st.toggle(
                                ":material/edit: Editar",
                                value=(
                                    st.session_state["editar_lancamento_entrega_id"]
                                    == str(lanc["_id"])
                                ),
                                key=f"editar_lancamento_entrega_{lanc['_id']}"
                            )

                            if editar:
                                st.session_state["editar_lancamento_entrega_id"] = str(
                                    lanc["_id"]
                                )

                            elif (
                                st.session_state["editar_lancamento_entrega_id"]
                                == str(lanc["_id"])
                            ):
                                st.session_state["editar_lancamento_entrega_id"] = None

                        # ==================================
                        # FORMULÁRIO DE EDIÇÃO
                        # ==================================
                        if (
                            st.session_state["editar_lancamento_entrega_id"]
                            == str(lanc["_id"])
                        ):

                            with st.container(border=True):

                                st.markdown("**Editar registro**")

                                with st.form(
                                    f"form_editar_lancamento_entrega_{lanc['_id']}",
                                    border=False
                                ):

                                    ano_atual = datetime.now().year

                                    anos_disponiveis = list(
                                        range(
                                            ano_atual - 1,
                                            ano_atual + 7
                                        )
                                    )

                                    try:
                                        idx_ano = anos_disponiveis.index(
                                            int(lanc.get("ano"))
                                        )
                                    except:
                                        idx_ano = 0

                                    novo_ano = st.selectbox(
                                        "Ano do registro",
                                        options=anos_disponiveis,
                                        index=idx_ano
                                    )

                                    novas_anotacoes = st.text_area(
                                        "Anotações",
                                        value=lanc.get("anotacoes", ""),
                                        height=120
                                    )

                                    salvar = st.form_submit_button(
                                        "Salvar alterações",
                                        icon=":material/save:"
                                    )

                                if salvar:

                                    lanc["ano"] = str(novo_ano)
                                    lanc["anotacoes"] = novas_anotacoes

                                    entregas_existentes[entrega_idx][
                                        "lancamentos_entregas"
                                    ][idx_lanc] = lanc

                                    projetos_ispn.update_one(
                                        {"_id": projeto_info["_id"]},
                                        {
                                            "$set": {
                                                "entregas": entregas_existentes
                                            }
                                        }
                                    )

                                    st.success("Registro atualizado.")

                                    st.session_state[
                                        "editar_lancamento_entrega_id"
                                    ] = None

                                    time.sleep(2)

                                    st.rerun(scope="fragment")

                        st.divider()


def atualizar_entrega_no_projeto(
    projeto_origem_id,
    entrega_editada
):
    """
    Atualiza uma entrega específica
    dentro do projeto de origem.
    """

    db = conectar_mongo_portal_ispn()
    projetos_ispn = db["projetos_ispn"]  

    projeto = projetos_ispn.find_one(
        {"_id": ObjectId(projeto_origem_id)}
    )

    if not projeto:
        return

    entregas = projeto.get("entregas", [])

    for idx, ent in enumerate(entregas):

        if ent.get("_id") == entrega_editada.get("_id"):

            # Remove campos auxiliares
            entrega_limpa = {
                k: v
                for k, v in entrega_editada.items()
                if not k.startswith("_projeto_origem")
            }

            entregas[idx] = entrega_limpa
            break

    projetos_ispn.update_one(
        {"_id": ObjectId(projeto_origem_id)},
        {"$set": {"entregas": entregas}}
    )


###########################################################################################################
# CONEXÃO COM GOOGLE DRIVE
###########################################################################################################

# Escopo mínimo necessário para Drive
ESCOPO_DRIVE = ["https://www.googleapis.com/auth/drive"]


@st.cache_resource
def obter_servico_drive():
    """
    Retorna o cliente autenticado do Google Drive,
    usando as credenciais armazenadas em st.secrets.

    IMPORTANTE:
    - Não cria conexão automaticamente
    - Só executa quando chamada
    - Cache evita recriar o cliente
    """
    credenciais = Credentials.from_service_account_info(
        st.secrets["gcp_service_account_drive"],
        scopes=ESCOPO_DRIVE
    )
    return build("drive", "v3", credentials=credenciais)




def obter_ou_criar_pasta(servico, nome_pasta, id_pasta_pai):
    """
    Busca uma pasta com o nome especificado dentro da pasta pai no Google Drive.
    Se não existir, cria a pasta.

    Retorna o ID da pasta.
    """

    consulta = (
        f"name='{nome_pasta}' and "
        f"'{id_pasta_pai}' in parents and "
        f"mimeType='application/vnd.google-apps.folder' and trashed=false"
    )

    resultado = servico.files().list(
        q=consulta,
        fields="files(id)",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True
    ).execute()

    arquivos = resultado.get("files", [])

    if arquivos:
        return arquivos[0]["id"]

    pasta = servico.files().create(
        body={
            "name": nome_pasta,
            "parents": [id_pasta_pai],
            "mimeType": "application/vnd.google-apps.folder"
        },
        fields="id",
        supportsAllDrives=True
    ).execute()

    return pasta["id"]






def obter_pasta_rede(servico, id_rede, nome_rede):
    """
    Retorna o ID da pasta da rede no Google Drive.
    Cria se não existir.

    Utiliza session_state para evitar recriação desnecessária.
    """

    # Chave única para cache da pasta da rede na sessão
    chave = f"pasta_rede_{id_rede}"

    # Retorna do cache caso já exista na sessão
    if chave in st.session_state:
        return st.session_state[chave]

    # Nome da pasta padronizado para redes
    nome_pasta = nome_rede

    # Cria ou recupera a pasta dentro da pasta raiz definida no secrets
    pasta_id = obter_ou_criar_pasta(
        servico,
        nome_pasta,
        st.secrets["drive"]["pasta_drive_redes"]
    )

    # Armazena no session_state para evitar chamadas repetidas
    st.session_state[chave] = pasta_id

    return pasta_id





def enviar_arquivo_drive(servico, id_pasta, arquivo):
    """
    Faz upload seguro de um arquivo do Streamlit para o Google Drive.

    - Usa upload resumable (mais estável)
    - Trata erros de rede/SSL
    - NÃO propaga exceção para a UI
    - Retorna None em caso de erro
    """

    try:
        # Garante que o ponteiro do arquivo está no início
        arquivo.seek(0)

        media = MediaIoBaseUpload(
            arquivo,
            mimetype=arquivo.type,
            resumable=True
        )

        arq = servico.files().create(
            body={
                "name": arquivo.name,
                "parents": [id_pasta]
            },
            media_body=media,
            fields="id",
            supportsAllDrives=True
        ).execute()

        return arq["id"]

    except Exception as e:
        st.error("Erro temporário ao enviar arquivo. Tente novamente mais tarde.")

        # Retorna None para a camada de UI decidir o que fazer
        return None






def gerar_link_drive(id_arquivo):
    """
    Gera o link público padrão de visualização do Google Drive.
    """
    return f"https://drive.google.com/file/d/{id_arquivo}/view"

