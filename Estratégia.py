import streamlit as st
import pandas as pd
import time
import streamlit_shadcn_ui as ui
from datetime import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn, formatar_nome_legivel, br_to_float, float_to_br
from bson import ObjectId
import re


###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
###########################################################################################################

# Conecta-se ao banco de dados MongoDB (usa cache automático para melhorar performance)
db = conectar_mongo_portal_ispn()

# Define as coleções específicas que serão utilizadas a partir do banco
estatistica = db["estatistica"]
colaboradores = db["colaboradores"]
estrategia = db["estrategia"]
projetos_ispn = db["projetos_ispn"]
indicadores = db["indicadores"]
lancamentos_indicadores = db["lancamentos_indicadores"]

###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_estrategia"
nome_pagina = "Estratégia"

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


###########################################################################################################
# FUNÇÕES
###########################################################################################################

# Função para comparar dataframes e detectar se tem mudanças, para fazer a gravação automática ao editar o data_editor
def df_tem_mudancas(df_novo: pd.DataFrame, df_antigo: pd.DataFrame) -> bool:
    """
    Compara dois DataFrames e retorna True se houver qualquer diferença.
    Considera tanto os valores quanto a ordem das colunas e linhas.

    Args:
        df_novo (pd.DataFrame): DataFrame novo editado.
        df_antigo (pd.DataFrame): DataFrame original para comparar.

    Returns:
        bool: True se os DataFrames forem diferentes, False se iguais.
    """
    
    return not df_novo.equals(df_antigo)


# Editar Teoria da Mudança  
@st.dialog("Editar Teoria da Mudança", width="large")
def editar_info_teoria_mudanca_dialog():
    # Pega o documento da coleção estratégia com a teoria da mudança
    teoria_doc = estrategia.find_one({"teoria da mudança": {"$exists": True}})

    # Cria lista com os valores atuais da teoria da mudança
    lista_tm = teoria_doc["teoria da mudança"] if teoria_doc else []

    # Valores padrões
    problema_atual = ""
    proposito_atual = ""
    impacto_atual = ""

    # Percorre a lista e extrai os valores atuais
    for item in lista_tm:
        if "problema" in item:
            problema_atual = item["problema"]
        if "proposito" in item:
            proposito_atual = item["proposito"]
        if "impacto" in item:
            impacto_atual = item["impacto"]

    # Input para novos valores
    novo_problema = st.text_area("Problema", value=problema_atual, height="content")
    novo_proposito = st.text_area("Propósito", value=proposito_atual, height="content")
    novo_impacto = st.text_area("Impacto", value=impacto_atual, height="content")

    # Botão para salvar alterações
    if st.button("Salvar alterações", key="salvar_teoria_mudanca", icon=":material/save:"):
        # Cria lista com os novos valores
        novos_dados = [
            {"problema": novo_problema},
            {"proposito": novo_proposito},
            {"impacto": novo_impacto}
        ]

        # Verifica se o documento existe
        if teoria_doc:
            # Atualiza o documento
            estrategia.update_one(
                {"_id": teoria_doc["_id"]},
                {"$set": {"teoria da mudança": novos_dados}}
            )
            st.success("Teoria da mudança atualizada com sucesso!")
        else:
            # Cria um novo documento
            estrategia.insert_one({"teoria da mudança": novos_dados})
            st.success("Teoria da mudança criada com sucesso!")

        # Espera 2 segundos e recarrega a página
        time.sleep(2)
        st.rerun()


# Editar Estratégia
@st.dialog("Editar Estratégia", width="large")
def editar_estrategia_dialog():
    # Busca o documento da estratégia que possui a chave "estrategia"
    estrategia_doc = estrategia.find_one({"estrategia": {"$exists": True}})

    # Obtém o título atual da página de estratégias, se existir
    titulo_pagina_atual = estrategia_doc.get("estrategia", {}).get("titulo_pagina_estrategia", "") if estrategia_doc else ""

    # Campo de entrada para um novo título da página de estratégias
    novo_titulo_pagina = st.text_input("Título da página de estratégias", value=titulo_pagina_atual)

    # Botão para atualizar o título da página
    if st.button("Atualizar título da página", key="atualizar_titulo_pagina_estrategias", icon=":material/save:"):
        if estrategia_doc:
            estrategia.update_one(
                {"_id": estrategia_doc["_id"]},
                {"$set": {"estrategia.titulo_pagina_estrategia": novo_titulo_pagina}}
            )
            st.success("Título da página atualizado com sucesso!")
            time.sleep(2)
            st.rerun()
        else:
            st.error("Documento não encontrado.")


# Função do diálogo para editar ou adicionar resultados de médio prazo
@st.dialog("Editar Título da Página", width="large")
def editar_titulo_pagina_resultados_mp_dialog():
    # Recupera os dados atuais do banco
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {}) if doc else {}

    # Título da aba principal de Resultados de Médio Prazo
    titulo_atual = resultados_data.get("titulo_pagina_resultados_mp", "")

    # Campo para editar o título da aba
    novo_titulo = st.text_input("Título da página de Resultados de Médio Prazo", value=titulo_atual)
    if st.button("Atualizar", key="atualizar_titulo_mp", icon=":material/save:"):
        estrategia.update_one(
            {"_id": doc["_id"]},
            {"$set": {"resultados_medio_prazo.titulo_pagina_resultados_mp": novo_titulo}}
        )
        st.success("Título da página atualizado com sucesso!")
        time.sleep(2)
        st.rerun()


# Função do diálogo para editar resultados de médio prazo
@st.dialog("Editar Informações do Resultado", width="large")
def editar_titulo_de_cada_resultado_mp_dialog(resultado_idx):
    # Recupera os dados do banco
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {})
    resultados = resultados_data.get("resultados_mp", [])

    # Verifica se o índice é válido
    if resultado_idx < 0 or resultado_idx >= len(resultados):
        st.error("Índice de resultado inválido.")
        return

    resultado = resultados[resultado_idx]
    
    if "admin" in st.session_state.tipo_usuario:
    
        # Tab para editar o título
        aba1, aba2, aba3 = st.tabs(["Título", "Metas", "Ações Estratégicas"])

        # Aba de Título
        with aba1:
            st.subheader("Editar Título do Resultado")
            st.write("")
            titulo_atual = resultado.get("titulo", "")
            novo_titulo = st.text_input("Novo título", value=titulo_atual)

            st.write("")

            if st.button("Salvar Título", key=f"salvar_titulo_{resultado_idx}", icon=":material/save:"):
                # Atualiza título
                resultados[resultado_idx]["titulo"] = novo_titulo

                # Se não tiver _id, gera um novo ObjectId como string
                if "_id" not in resultados[resultado_idx]:
                    resultados[resultado_idx]["_id"] = str(ObjectId())

                # Atualiza no Mongo
                estrategia.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                )
                st.success("Título do resultado atualizado com sucesso!")
                time.sleep(2)
                st.rerun()

        # -------------------------- #
        # ABA 2 - METAS
        # -------------------------- #
        with aba2:
            metas = resultado.get("metas", [])
            
            st.subheader("Adicionar uma meta")
            st.write("")
            
            # Adicionar nova meta
            novo_nome_meta = st.text_input("Título da meta", key=f"nova_meta_nome_{resultado_idx}")
            novo_objetivo = st.text_input("Objetivo da meta", key=f"nova_meta_obj_{resultado_idx}")

            if st.button("Adicionar Meta", key=f"btn_add_meta_{resultado_idx}", icon=":material/add:"):
                nova_meta = {
                    "_id": str(ObjectId()),
                    "nome_meta_mp": novo_nome_meta,
                    "objetivo": novo_objetivo
                }
                resultados[resultado_idx].setdefault("metas", []).append(nova_meta)

                estrategia.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                )
                st.success("Nova meta adicionada com sucesso!")
                time.sleep(2)
                st.rerun()
                    
            # st.write("")

            # for m_idx, meta in enumerate(metas):
            #     titulo_meta = meta.get("nome_meta_mp", f"Meta {m_idx + 1}")
            #     with st.expander(f"{titulo_meta}", expanded=False):
            #         novo_nome_meta = st.text_input(
            #             "Título",
            #             value=meta.get("nome_meta_mp", ""),
            #             key=f"nome_meta_{resultado_idx}_{m_idx}"
            #         )
            #         novo_objetivo = st.text_input(
            #             "Objetivo",
            #             value=meta.get("objetivo", ""),
            #             key=f"obj_{resultado_idx}_{m_idx}"
            #         )
            #         novo_alcancado = st.text_input(
            #             "Alcançado",
            #             value=meta.get("alcancado", ""),
            #             key=f"alcan_{resultado_idx}_{m_idx}"
            #         )

            #         if st.button("Salvar", key=f"salvar_meta_{resultado_idx}_{m_idx}", icon=":material/save:"):
            #             resultados[resultado_idx]["metas"][m_idx]["nome_meta_mp"] = novo_nome_meta
            #             resultados[resultado_idx]["metas"][m_idx]["objetivo"] = novo_objetivo
            #             resultados[resultado_idx]["metas"][m_idx]["alcancado"] = novo_alcancado

            #             if "_id" not in resultados[resultado_idx]["metas"][m_idx]:
            #                 resultados[resultado_idx]["metas"][m_idx]["_id"] = str(ObjectId())

            #             estrategia.update_one(
            #                 {"_id": doc["_id"]},
            #                 {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
            #             )
            #             st.success("Meta atualizada com sucesso!")
            #             time.sleep(2)
            #             st.rerun()


        # -------------------------- #
        # ABA 3 - AÇÕES ESTRATÉGICAS
        # -------------------------- #
        with aba3:
            acoes = resultado.get("acoes_estrategicas", [])
            
            # 🔹 Expander para adicionar nova ação estratégica (com atividades e anotações)
            with st.expander("Adicionar nova ação estratégica", expanded=False, icon=":material/add_notes:"):
                novo_titulo_acao = st.text_area("Título da nova ação estratégica", key=f"nova_acao_titulo_{resultado_idx}")

                if st.button("Adicionar ação estratégica", key=f"btn_add_acao_{resultado_idx}", icon=":material/add:"):
                    nova_acao = {
                        "_id": str(ObjectId()),
                        "nome_acao_estrategica": novo_titulo_acao,
                    }

                    resultados[resultado_idx].setdefault("acoes_estrategicas", []).append(nova_acao)

                    estrategia.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                    )

                    st.success("Nova ação estratégica adicionada com sucesso!")
                    time.sleep(2)
                    st.rerun()
            
            st.write("")
        
            # Edição das ações estratégicas existentes
            for a_idx, acao in enumerate(acoes):
                titulo_acao = acao.get("nome_acao_estrategica", f"Ação Estratégica {a_idx + 1}")
                with st.expander(f"{titulo_acao}"):
                
                    novo_nome_acao = st.text_area(
                        "Título da ação estratégica",
                        value=titulo_acao,
                        height="content",
                        key=f"acao_estrat_{resultado_idx}_{a_idx}"
                    )

                    if st.button(f"Salvar", key=f"salvar_acao_{resultado_idx}_{a_idx}", icon=":material/save:"):
                        resultados[resultado_idx]["acoes_estrategicas"][a_idx].update({
                            "nome_acao_estrategica": novo_nome_acao,
                        })
                        estrategia.update_one(
                            {"_id": doc["_id"]},
                            {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                        )
                        st.success("Ação estratégica atualizada com sucesso!")
                        time.sleep(2)
                        st.rerun()
                    
    else:
        
        metas = resultado.get("metas", [])
            
        # Expander para adicionar nova meta
        with st.expander("Adicionar meta", expanded=False, icon=":material/add_notes:"):
            novo_nome_meta = st.text_input("Título da meta", key=f"nova_meta_nome_{resultado_idx}")
            novo_objetivo = st.text_input("Objetivo da meta", key=f"nova_meta_obj_{resultado_idx}")

            if st.button("Adicionar Meta", key=f"btn_add_meta_{resultado_idx}", icon=":material/add:"):
                nova_meta = {
                    "_id": str(ObjectId()),
                    "nome_meta_mp": novo_nome_meta,
                    "objetivo": novo_objetivo
                }
                resultados[resultado_idx].setdefault("metas", []).append(nova_meta)

                estrategia.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                )
                st.success("Nova meta adicionada com sucesso!")
                time.sleep(2)
                st.rerun()
                
        st.write("")

        for m_idx, meta in enumerate(metas):
            titulo_meta = meta.get("nome_meta_mp", f"Meta {m_idx + 1}")
            with st.expander(f"{titulo_meta}", expanded=False):
                novo_nome_meta = st.text_input(
                    "Título",
                    value=meta.get("nome_meta_mp", ""),
                    key=f"nome_meta_{resultado_idx}_{m_idx}"
                )
                novo_objetivo = st.text_input(
                    "Objetivo",
                    value=meta.get("objetivo", ""),
                    key=f"obj_{resultado_idx}_{m_idx}"
                )
                novo_alcancado = st.text_input(
                    "Alcançado",
                    value=meta.get("alcancado", ""),
                    key=f"alcan_{resultado_idx}_{m_idx}"
                )

                if st.button("Salvar", key=f"salvar_meta_{resultado_idx}_{m_idx}", icon=":material/save:"):
                    resultados[resultado_idx]["metas"][m_idx]["nome_meta_mp"] = novo_nome_meta
                    resultados[resultado_idx]["metas"][m_idx]["objetivo"] = novo_objetivo
                    resultados[resultado_idx]["metas"][m_idx]["alcancado"] = novo_alcancado

                    if "_id" not in resultados[resultado_idx]["metas"][m_idx]:
                        resultados[resultado_idx]["metas"][m_idx]["_id"] = str(ObjectId())

                    estrategia.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                    )
                    st.success("Meta atualizada com sucesso!")
                    time.sleep(2)
                    st.rerun()

     
@st.dialog("Editar eixo da estratégia")
def editar_eixos_da_estrategia_dialog(estrategia_item, estrategia_doc, estrategia):
    novo_titulo = st.text_input("Eixo da estratégia:", estrategia_item.get("titulo", ""))
    
    st.write("")
    
    col1, col2 = st.columns(2)
    
    if col1.button("Salvar", use_container_width=False, icon=":material/save:"):
        # Atualiza o título no documento original
        for eixo in estrategia_doc["estrategia"]["eixos_da_estrategia"]:
            if eixo["titulo"] == estrategia_item["titulo"]:
                eixo["titulo"] = novo_titulo
                break

        # Salva no MongoDB
        estrategia.update_one(
            {"_id": estrategia_doc["_id"]},
            {"$set": {"estrategia.eixos_da_estrategia": estrategia_doc["estrategia"]["eixos_da_estrategia"]}}
        )

        st.success("Título atualizado com sucesso!")
        st.rerun()
            

@st.dialog("Editar título da página")
def editar_titulo_pagina_resultados_lp_dialog():

    # Buscar documento
    doc = estrategia.find_one({"resultados_longo_prazo": {"$exists": True}})
    if not doc:
        st.error("Nenhum documento encontrado com 'resultados_longo_prazo'.")
        return

    dados_lp = doc.get("resultados_longo_prazo", {})
    titulo_atual = dados_lp.get("titulo_pagina_resultados_lp", "")

    # Campos editáveis
    novo_titulo = st.text_input("Título da página", value=titulo_atual)

    # Botão de salvar
    if st.button("Salvar alterações", icon=":material/save:", use_container_width=False):
        estrategia.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "resultados_longo_prazo.titulo_pagina_resultados_lp": novo_titulo,
            }}
        )
        st.success("Título da página atualizado com sucesso!")
        time.sleep(2)
        st.rerun()
            
            
@st.dialog("Editar resultado de longo prazo", width="large")
def editar_titulo_de_cada_resultado_lp_dialog(resultado_idx):
    # Buscar documento
    doc = estrategia.find_one({"resultados_longo_prazo": {"$exists": True}})
    if not doc:
        st.error("Nenhum documento encontrado com 'resultados_longo_prazo'.")
        return

    resultados_lp = doc.get("resultados_longo_prazo", {}).get("resultados_lp", [])
    if resultado_idx is None or resultado_idx >= len(resultados_lp):
        st.error("Índice de resultado inválido.")
        return

    resultado = resultados_lp[resultado_idx]

    # Campos principais
    novo_titulo = st.text_area("Título do resultado", value=resultado.get("titulo", ""), height="content")

    # Botão de salvar
    if st.button("Salvar alterações", icon=":material/save:", use_container_width=False):

        estrategia.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                f"resultados_longo_prazo.resultados_lp.{resultado_idx}.titulo": novo_titulo,
            }}
        )
        st.success("Resultado atualizado com sucesso!")
        time.sleep(2)
        st.rerun()

def _safe_key(text):
    """Gera uma chave segura para Streamlit a partir de um texto (sem chars especiais)."""
    if text is None:
        return "none"
    return re.sub(r"\W+", "_", str(text)).strip("_").lower()

def _format_responsaveis_list(responsaveis_list, responsaveis_dict):
    """
    Recebe lista de responsáveis (pode conter dicts com {'$oid': '...'} ou ObjectId/str)
    e retorna string formatada com nomes.
    """
    nomes = []
    for r in responsaveis_list:
        if isinstance(r, dict) and "$oid" in r:
            key = str(r["$oid"])
        else:
            key = str(r)
        nomes.append(responsaveis_dict.get(key, "Desconhecido"))
    return ", ".join(nomes) if nomes else "-"

def normalizar_lista_ids(lista):
    """
    Converte uma lista que pode conter ObjectId, dict {'$oid': ...} ou str
    para uma lista de strings.
    """
    ids = []
    for item in lista or []:
        if isinstance(item, ObjectId):
            ids.append(str(item))
        elif isinstance(item, dict) and "$oid" in item:
            ids.append(str(item["$oid"]))
        else:
            ids.append(str(item))
    return ids

def buscar_entregas_relacionadas_por_id(
    *,
    eixo_id=None,
    acoes_rm_relacionados=None,
    resultado_lp_id=None
):
    entregas_filtradas = []

    projetos = list(
        projetos_ispn.find({}, {"entregas": 1, "sigla": 1})
    )

    df_pessoas = pd.DataFrame(list(db["pessoas"].find()))
    responsaveis_dict = {
        str(row["_id"]): row["nome_completo"]
        for _, row in df_pessoas.iterrows()
    } if not df_pessoas.empty else {}

    for projeto in projetos:
        sigla = projeto.get("sigla", "-")

        for entrega in projeto.get("entregas", []) or []:

            eixos_ids = normalizar_lista_ids(entrega.get("eixos_relacionados", []))
            acoes_ids = normalizar_lista_ids(entrega.get("acoes_resultados_medio_prazo", []))
            resultados_lp_ids = normalizar_lista_ids(entrega.get("resultados_longo_prazo_relacionados", []))

            if (
                (eixo_id and eixo_id in eixos_ids)
                or (acoes_rm_relacionados and acoes_rm_relacionados in acoes_ids)
                or (resultado_lp_id and resultado_lp_id in resultados_lp_ids)
            ):

                entregas_filtradas.append({
                    "Projeto": sigla,
                    "Entrega": entrega.get("nome_da_entrega", "-"),
                    "Previsão de Conclusão": entrega.get("previsao_da_conclusao", "-"),
                    "Responsáveis": _format_responsaveis_list(
                        entrega.get("responsaveis", []),
                        responsaveis_dict
                    ),
                    "Situação": entrega.get("situacao", "-"),
                    "Ano(s) de Referência": ", ".join(entrega.get("anos_de_referencia", []) or []),
                    "Anotações": entrega.get("anotacoes", "-"),
                })

    return entregas_filtradas

def exibir_entregas_como_tabela(entregas_list, key_prefix="tabela", key_suffix=None):
    """
    Recebe a lista de entregas (lista de dicts) e exibe como ui.table com key única.
    Faz parsing da coluna 'Previsão de Conclusão' para ordenar corretamente (DD/MM/YYYY).
    """
    if not entregas_list:
        return None

    df = pd.DataFrame(entregas_list)

    # Parse para datetime considerando dia/mês/ano; mantém strings inválidas como NaT
    if "Previsão de Conclusão" in df.columns:
        df["_dt_previsao"] = pd.to_datetime(df["Previsão de Conclusão"], dayfirst=True, errors="coerce")
        df = df.sort_values(by="_dt_previsao", ascending=True).drop(columns=["_dt_previsao"])

    # montar key única
    if key_suffix is None:
        key_suffix = pd.util.hash_pandas_object(df).sum()  # fallback (não muito legível, mas único)
    key = f"{key_prefix}_{_safe_key(key_suffix)}"

    # exibir
    ui.table(data=df, key=key)
    return df

def buscar_entregas_por_acao(nome_acao):
    entregas_relacionadas = []

    projetos = projetos_ispn.find(
        {"entregas.acoes_resultados_medio_prazo": nome_acao},
        {"sigla": 1, "entregas": 1}
    )

    for projeto in projetos:
        sigla = projeto.get("sigla", "")

        for entrega in projeto.get("entregas", []):
            if nome_acao in entrega.get("acoes_resultados_medio_prazo", []):

                entregas_relacionadas.append({
                    "Projeto": sigla,
                    "Entrega": entrega.get("nome_da_entrega", ""),
                    "Situação": entrega.get("situacao", ""),
                    "Previsão": entrega.get("previsao_da_conclusao", ""),
                    "Ano(s) de Referência": ", ".join(entrega.get("anos_de_referencia", [])),
                    "Observações": entrega.get("anotacoes", "")
                })

    return entregas_relacionadas


###########################################################################################################
# INTERFACE PRINCIPAL
###########################################################################################################


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

if "modo_edicao" not in st.session_state:
    st.session_state.modo_edicao = False


st.header("Planejamento Estratégico")
st.write('')


# aba_tm, aba_est, aba_res_mp, aba_res_lp, aba_ebj_est_ins = st.tabs(['Teoria da mudança', 'Estratégia', 'Resultados de Médio Prazo', 'Resultados de Longo Prazo', 'Objetivos Estratégicos Institucionais'])
aba_est, aba_res_mp, aba_res_lp, aba_ebj_est_ins = st.tabs(['Estratégia', 'Resultados de Médio Prazo', 'Resultados de Longo Prazo', 'Objetivos Estratégicos Organizacionais'])

# ---------------------------
# ABA ESTRATÉGIA
# ---------------------------
with aba_est:

    # ----------------------------------------------------
    # ESTADO INICIAL
    # ----------------------------------------------------
    if "modo_edicao_1" not in st.session_state:
        st.session_state.modo_edicao_1 = False

    # ----------------------------------------------------
    # CARREGAR ESTRATÉGIA
    # ----------------------------------------------------
    estrategia_doc = estrategia.find_one({"estrategia": {"$exists": True}})

    titulo_pagina_atual = (
        estrategia_doc.get("estrategia", {}).get("titulo_pagina_estrategia", "")
        if estrategia_doc else ""
    )

    lista_estrategias_atual = (
        estrategia_doc.get("estrategia", {}).get("eixos_da_estrategia", [])
        if estrategia_doc else []
    )

    # ----------------------------------------------------
    # MODO EDIÇÃO
    # ----------------------------------------------------
    if set(st.session_state.tipo_usuario) & {"admin"}:
        col1, col2 = st.columns([4, 1])
        col1.toggle("Modo de edição", value=False, key="modo_edicao_1")

        if st.session_state.modo_edicao_1:
            with col2:
                st.button(
                    "Editar página",
                    icon=":material/edit:",
                    key="editar_titulo_estrategia",
                    on_click=editar_estrategia_dialog,
                    use_container_width=True
                )

    st.write("")
    st.subheader(
        titulo_pagina_atual
        if titulo_pagina_atual
        else "Promoção de Paisagens Produtivas Ecossociais"
    )
    st.write("")

    # ----------------------------------------------------
    # FILTRO POR ANO (MULTISELECT)
    # ----------------------------------------------------
    ver_filtros = st.toggle("Ver filtros", key="ver_filtros")

    anos_selecionados = []

    if ver_filtros:
        # Buscar apenas anos existentes nos lançamentos
        anos_disponiveis = sorted(
            {
                lanc.get("ano")
                for lanc in lancamentos_indicadores.find(
                    {"ano": {"$exists": True, "$ne": ""}},
                    {"ano": 1}
                )
            },
            reverse=True
        )

        anos_selecionados = st.multiselect(
            "Selecione o(s) ano(s):",
            options=anos_disponiveis,
            default=anos_disponiveis[:1] if anos_disponiveis else []
        )

    st.write("")

    # ----------------------------------------------------
    # PREPARAR FILTRO PARA LANÇAMENTOS
    # ----------------------------------------------------
    filtro_lancamentos = {}
    if anos_selecionados:
        filtro_lancamentos["ano"] = {"$in": anos_selecionados}

    # ----------------------------------------------------
    # PRÉ-CARREGAR LANÇAMENTOS E SOMAR POR INDICADOR
    # ----------------------------------------------------
    todos_lancamentos = list(
        lancamentos_indicadores.find(filtro_lancamentos)
    )

    mapa_soma_indicadores = {}

    for lanc in todos_lancamentos:
        id_indicador = str(lanc.get("id_do_indicador"))

        valor = br_to_float(lanc.get("valor"))

        mapa_soma_indicadores[id_indicador] = (
            mapa_soma_indicadores.get(id_indicador, 0) + valor
        )


    # ----------------------------------------------------
    # ORDENAR EIXOS
    # ----------------------------------------------------
    def extrair_numero(item):
        try:
            return int(item["titulo"].split(" - ")[0])
        except:
            return float("inf")

    lista_estrategias_ordenada = sorted(
        lista_estrategias_atual,
        key=extrair_numero
    )

    # ----------------------------------------------------
    # MAPA DE INDICADORES POR EIXO
    # ----------------------------------------------------
    todos_indicadores = list(indicadores.find())

    mapa_indicadores_por_eixo = {}

    for ind in todos_indicadores:
        for eixo_id in ind.get("colabora_estrategia", []):
            eixo_id_str = str(eixo_id)
            mapa_indicadores_por_eixo.setdefault(eixo_id_str, []).append(ind)

    # ----------------------------------------------------
    # LOOP DOS EIXOS
    # ----------------------------------------------------
    for eixo in lista_estrategias_ordenada:

        eixo_id = str(eixo["_id"])
        titulo_eixo = eixo.get("titulo", "Título não definido")

        titulo_eixo = eixo.get("titulo", "Título não definido")

        with st.expander(f"**{titulo_eixo}**"):

            # --------------------------------------------
            # BOTÃO EDITAR EIXO
            # --------------------------------------------
            if st.session_state.modo_edicao_1:
                col1, col2 = st.columns([4, 1])
                col2.button(
                    "Editar eixo",
                    key=f"editar_{_safe_key(titulo_eixo)}",
                    on_click=editar_eixos_da_estrategia_dialog,
                    args=(eixo, estrategia_doc, estrategia),
                    use_container_width=True,
                    icon=":material/edit:"
                )

            st.write("")
            st.write("**:material/package_2: Entregas Planejadas / Realizadas:**")
            st.write("")

            # --------------------------------------------
            # ENTREGAS DO EIXO
            # --------------------------------------------
            entregas_filtradas = buscar_entregas_relacionadas_por_id(
                eixo_id=str(eixo["_id"])
            )

            if entregas_filtradas:
                exibir_entregas_como_tabela(
                    entregas_filtradas,
                    key_prefix="tabela_entregas_eixo",
                    key_suffix=_safe_key(titulo_eixo)
                )
            else:
                st.write("Nenhuma entrega registrada para este eixo.")

            # --------------------------------------------
            # INDICADORES DO EIXO (COM SOMA FILTRADA POR ANO)
            # --------------------------------------------
            st.divider()
            st.markdown("##### :material/monitoring: Indicadores:")

            indicadores_eixo = mapa_indicadores_por_eixo.get(eixo_id, [])
            
            if not indicadores_eixo:
                st.write("Nenhum indicador relacionado a este eixo.")
            else:
                for ind in indicadores_eixo:
                    nome_bruto = ind.get("nome_indicador", "Indicador sem nome")
                    nome_legivel = formatar_nome_legivel(nome_bruto)

                    id_indicador = str(ind["_id"])
                    valor_total = mapa_soma_indicadores.get(id_indicador, 0)

                    valor_formatado = float_to_br(valor_total)

                    st.markdown(f"**{nome_legivel}:** {valor_formatado}")


# ---------------------------
# ABA RESULTADOS DE MÉDIO PRAZO
# ---------------------------
with aba_res_mp:

    # ----------------------------------------------------
    # ESTADO INICIAL
    # ----------------------------------------------------
    if "modo_edicao_2" not in st.session_state:
        st.session_state.modo_edicao_2 = False

    # ----------------------------------------------------
    # CARREGAR DOCUMENTO DE RESULTADOS MP
    # ----------------------------------------------------
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {}) if doc else {}

    titulo_pagina = resultados_data.get(
        "titulo_pagina_resultados_mp",
        "Resultados de Médio Prazo"
    )
    lista_resultados = resultados_data.get("resultados_mp", [])

    # ----------------------------------------------------
    # MODO EDIÇÃO
    # ----------------------------------------------------
    if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}:
        col1, col2 = st.columns([4, 1])
        col1.toggle("Modo de edição", value=False, key="modo_edicao_2")

        if st.session_state.modo_edicao_2 and "admin" in st.session_state.tipo_usuario:
            with col2:
                st.button(
                    "Editar página",
                    icon=":material/edit:",
                    key="editar_titulo_result_mp",
                    on_click=editar_titulo_pagina_resultados_mp_dialog,
                    use_container_width=True
                )

    st.write("")
    st.subheader(titulo_pagina)
    st.write("")

    # ----------------------------------------------------
    # PRÉ-CARREGAR INDICADORES (MAPA POR RESULTADO MP)
    # ----------------------------------------------------
    todos_indicadores = list(indicadores.find())

    mapa_indicadores_por_resultado_mp = {}

    for ind in todos_indicadores:
        for rmp_id in ind.get("colabora_resultado_mp", []):
            rmp_id_str = str(rmp_id)
            mapa_indicadores_por_resultado_mp.setdefault(rmp_id_str, []).append(ind)


    # ----------------------------------------------------
    # PRÉ-CARREGAR LANÇAMENTOS DE INDICADORES
    # ----------------------------------------------------
    todos_lancamentos = list(lancamentos_indicadores.find())

    mapa_soma_indicadores = {}
    for lanc in todos_lancamentos:
        id_indicador = str(lanc.get("id_do_indicador"))
        valor = br_to_float(lanc.get("valor"))

        mapa_soma_indicadores[id_indicador] = (
            mapa_soma_indicadores.get(id_indicador, 0) + valor
        )

    # ----------------------------------------------------
    # LOOP PELOS RESULTADOS DE MÉDIO PRAZO
    # ----------------------------------------------------
    for idx, resultado in enumerate(lista_resultados):

        titulo_result = resultado.get("titulo", f"Resultado {idx + 1}")

        with st.expander(titulo_result):

            # --------------------------------------------
            # BOTÃO EDITAR RESULTADO
            # --------------------------------------------
            if st.session_state.modo_edicao_2:
                col1, col2 = st.columns([4, 1])
                col2.button(
                    "Editar resultado",
                    icon=":material/edit:",
                    key=f"editar_resultado_mp_{idx}",
                    on_click=lambda i=idx: editar_titulo_de_cada_resultado_mp_dialog(i),
                    use_container_width=True
                )

            @st.fragment
            def fragmento_metas_mp(
                *,
                metas,
                idx,
                resultado,
                doc,
                estrategia
            ):
                if not metas:
                    st.caption("Nenhuma meta cadastrada.")
                    return

                st.markdown("##### :material/target: Metas:")
                st.write("")

                df_metas = pd.DataFrame([
                    {
                        "Meta": m.get("nome_meta_mp", ""),
                        "Objetivo": m.get("objetivo", ""),
                        "Alcançado": m.get("alcancado", "")
                    }
                    for m in metas
                ])

                if st.session_state.modo_edicao_2:
                    chave_original = f"df_metas_original_mp_{idx}"
                    chave_editado = f"df_metas_editado_mp_{idx}"

                    if chave_original not in st.session_state:
                        st.session_state[chave_original] = df_metas.copy()

                    df_editado = st.data_editor(
                        st.session_state.get(
                            chave_editado,
                            st.session_state[chave_original],
                        ),
                        hide_index=True,
                        key=f"editor_metas_mp_{idx}",
                        column_config={
                            "Meta": st.column_config.TextColumn(
                                "Meta",
                                disabled=True
                            ),
                            "Objetivo": st.column_config.TextColumn("Objetivo"),
                            "Alcançado": st.column_config.TextColumn("Alcançado"),
                        },
                        num_rows="fixed"
                    )

                    st.session_state[chave_editado] = df_editado.copy()

                    houve_mudanca = df_tem_mudancas(
                        df_editado,
                        st.session_state[chave_original]
                    )

                    if houve_mudanca:
                        container_botao = st.container(horizontal_alignment="left", width=300)
                        if container_botao.button(
                            "Atualizar metas",
                            icon=":material/save:",
                            key=f"salvar_metas_mp_{idx}",
                            use_container_width=True
                        ):
                            nova_lista_metas = []
                            for i, meta in enumerate(metas):
                                nova_lista_metas.append({
                                    **meta,
                                    "objetivo": df_editado.loc[i, "Objetivo"],
                                    "alcancado": df_editado.loc[i, "Alcançado"]
                                })

                            estrategia.update_one(
                                {
                                    "_id": doc["_id"],
                                    f"resultados_medio_prazo.resultados_mp.{idx}._id": resultado["_id"]
                                },
                                {
                                    "$set": {
                                        f"resultados_medio_prazo.resultados_mp.{idx}.metas": nova_lista_metas
                                    }
                                }
                            )

                            st.session_state[chave_original] = df_editado.copy()
                            st.session_state.pop(chave_editado, None)

                            msg = st.empty()
                            msg.success("Metas atualizadas com sucesso")
                            time.sleep(2)
                            msg.empty()

                else:
                    st.dataframe(df_metas, hide_index=True)
            
            fragmento_metas_mp(
                metas=resultado.get("metas", []),
                idx=idx,
                resultado=resultado,
                doc=doc,
                estrategia=estrategia
            )
            
            st.divider()

            # --------------------------------------------
            # AÇÕES ESTRATÉGICAS / ENTREGAS
            # --------------------------------------------
            st.markdown("##### :material/package_2: Entregas por Ação Estratégica:")
            st.write("")

            acoes_estrategicas = resultado.get("acoes_estrategicas", [])

            if not acoes_estrategicas:
                st.caption("Nenhuma ação estratégica cadastrada para este resultado.")
            else:
                for idx_acao, acao in enumerate(acoes_estrategicas):

                    nome_acao = acao.get(
                        "nome_acao_estrategica",
                        f"Ação {idx_acao + 1}"
                    )

                    st.write(f"**{nome_acao}**")

                    entregas_vinculadas = buscar_entregas_relacionadas_por_id(
                        acoes_rm_relacionados=str(acao["_id"])
                    )

                    # st.write("**:material/package_2: Entregas:**")

                    if entregas_vinculadas:
                        exibir_entregas_como_tabela(
                            entregas_vinculadas,
                            key_prefix="tabela_entrega_por_acao",
                            key_suffix=f"{idx}_{idx_acao}"
                        )
                    else:
                        st.caption("Nenhuma entrega vinculada a esta ação estratégica.")

                    st.divider()

            # --------------------------------------------
            # INDICADORES DO RESULTADO DE MÉDIO PRAZO
            # --------------------------------------------
            st.markdown("##### :material/monitoring: Indicadores:")
            st.write("")
            
            resultado_id = str(resultado["_id"])
            titulo_result = resultado.get("titulo", f"Resultado {idx + 1}")

            indicadores_resultado = mapa_indicadores_por_resultado_mp.get(
                resultado_id,
                []
            )


            if not indicadores_resultado:
                st.caption("Nenhum indicador relacionado a este resultado.")
            else:
                for ind in indicadores_resultado:

                    nome_bruto = ind.get(
                        "nome_indicador",
                        "Indicador sem nome"
                    )
                    nome_legivel = formatar_nome_legivel(nome_bruto)

                    id_indicador = str(ind["_id"])
                    valor_total = mapa_soma_indicadores.get(id_indicador, 0)
                    valor_formatado = float_to_br(valor_total)

                    st.markdown(
                        f"**{nome_legivel}:** {valor_formatado}"
                    )


# ---------------------------
# ABA RESULTADOS DE LONGO PRAZO
# ---------------------------
with aba_res_lp:

    # ----------------------------------------------------
    # ESTADO INICIAL
    # ----------------------------------------------------
    if "modo_edicao_lp" not in st.session_state:
        st.session_state.modo_edicao_lp = False

    # ----------------------------------------------------
    # CARREGAR DOCUMENTO DE RESULTADOS DE LONGO PRAZO
    # ----------------------------------------------------
    doc = estrategia.find_one({"resultados_longo_prazo": {"$exists": True}})
    resultados_lp_data = doc.get("resultados_longo_prazo", {}) if doc else {}

    titulo_pagina_lp = resultados_lp_data.get(
        "titulo_pagina_resultados_lp",
        "Resultados de Longo Prazo - 2030"
    )
    lista_resultados_lp = resultados_lp_data.get("resultados_lp", [])

    # ----------------------------------------------------
    # MODO DE EDIÇÃO
    # ----------------------------------------------------
    if set(st.session_state.tipo_usuario) & {"admin"}:
        col1, col2 = st.columns([4, 1])
        col1.toggle("Modo de edição", value=False, key="modo_edicao_lp")

        if st.session_state.modo_edicao_lp:
            with col2:
                st.button(
                    "Editar página",
                    icon=":material/edit:",
                    key="editar_titulo_result_lp",
                    on_click=editar_titulo_pagina_resultados_lp_dialog,
                    use_container_width=True
                )

    st.write("")
    st.subheader(titulo_pagina_lp)
    st.write("")

    # ----------------------------------------------------
    # MAPA DE INDICADORES POR RESULTADO DE LONGO PRAZO
    # (usa campo colabora_resultado_lp na coleção 'indicadores')
    # ----------------------------------------------------
    todos_indicadores_lp = list(indicadores.find())

    mapa_indicadores_por_resultado_lp = {}
    for ind in todos_indicadores_lp:
        for resultado_lp in ind.get("colabora_resultado_lp", []):
            resultado_lp_id = str(resultado_lp)
            mapa_indicadores_por_resultado_lp.setdefault(
                resultado_lp_id, []
            ).append(ind)


    # ----------------------------------------------------
    # PRÉ-CARREGAR LANÇAMENTOS DE INDICADORES
    # (usa br_to_float para somar valores em formato BR)
    # ----------------------------------------------------
    todos_lancamentos_lp = list(lancamentos_indicadores.find())

    mapa_soma_indicadores_lp = {}
    for lanc in todos_lancamentos_lp:
        id_indicador = str(lanc.get("id_do_indicador"))
        valor = br_to_float(lanc.get("valor"))

        mapa_soma_indicadores_lp[id_indicador] = (
            mapa_soma_indicadores_lp.get(id_indicador, 0) + valor
        )

    # ----------------------------------------------------
    # LOOP DOS RESULTADOS DE LONGO PRAZO
    # ----------------------------------------------------
    if lista_resultados_lp:
        for idx, resultado in enumerate(lista_resultados_lp):
            
            resultado_lp_id = str(resultado["_id"])
            titulo_result_lp = resultado.get("titulo", f"Resultado {idx + 1}")

            with st.expander(titulo_result_lp):

                # --------------------------------------------
                # BOTÃO EDITAR RESULTADO
                # --------------------------------------------
                if st.session_state.modo_edicao_lp:
                    col1, col2 = st.columns([4, 1])
                    col2.button(
                        "Editar resultado",
                        icon=":material/edit:",
                        key=f"editar_resultado_lp_{idx}",
                        on_click=lambda i=idx: editar_titulo_de_cada_resultado_lp_dialog(i),
                        use_container_width=True
                    )

                # ====================================================
                # ENTREGAS PLANEJADAS / REALIZADAS (PRIMEIRO)
                # ====================================================
                st.write("")
                st.markdown("**Entregas Planejadas / Realizadas:**")

                entregas_lp = buscar_entregas_relacionadas_por_id(
                    resultado_lp_id=str(resultado["_id"])
                )

                if entregas_lp:
                    exibir_entregas_como_tabela(
                        entregas_lp,
                        key_prefix="tabela_entregas_lp",
                        key_suffix=f"{idx}_{_safe_key(titulo_result_lp)}"
                    )
                else:
                    st.caption(
                        "Nenhuma entrega registrada para este resultado de longo prazo."
                    )

                st.divider()

                # ====================================================
                # INDICADORES (VINDOS DA COLEÇÃO 'indicadores')
                # ====================================================
                st.markdown("##### :material/monitoring: Indicadores:") 

                indicadores_resultado = mapa_indicadores_por_resultado_lp.get(
                    resultado_lp_id,
                    []
                )

                if not indicadores_resultado:
                    st.caption(
                        "Nenhum indicador relacionado a este resultado de longo prazo."
                    )
                else:
                    for ind in indicadores_resultado:
                        # Nome legível do indicador
                        nome_bruto = ind.get(
                            "nome_indicador",
                            "Indicador sem nome"
                        )
                        nome_legivel = formatar_nome_legivel(nome_bruto)

                        # Soma dos lançamentos desse indicador
                        id_indicador = str(ind["_id"])
                        valor_total = mapa_soma_indicadores_lp.get(
                            id_indicador,
                            0
                        )
                        valor_formatado = float_to_br(valor_total)

                        st.markdown(
                            f"**{nome_legivel}:** {valor_formatado}"
                        )
    else:
        st.caption("Nenhum resultado de longo prazo encontrado no banco de dados.")




# -----------------------------------------------------------
# ABA OBJETIVOS ESTRATEGICOS INSTITUCIONAIS
# -----------------------------------------------------------

with aba_ebj_est_ins:
    
    doc = estrategia.find_one(
        {"objetivos_estrategicos_institucionais": {"$exists": True}},
        {"_id": 0, "objetivos_estrategicos_institucionais": 1}
    )

    objetivos = doc["objetivos_estrategicos_institucionais"]["obj_estrat_inst"]
    
    st.write('')
    st.subheader(doc["objetivos_estrategicos_institucionais"]["titulo_pagina_obj_estrat_inst"])
    st.write('')
    st.markdown('<span style="color:red">**Página não implementada*</span>', unsafe_allow_html=True)
    st.write('')

    # Objetivo 1
    with st.expander(f'**Objetivo 1 - {objetivos[0]["titulo"]}**'):
        st.write('')

    # Objetivo 2
    with st.expander(f'**Objetivo 2 - {objetivos[1]["titulo"]}**'):
        st.write('')

    # Objetivo 3
    with st.expander(f'**Objetivo 3 - {objetivos[2]["titulo"]}**'):
        st.write('')

    # Objetivo 4
    with st.expander(f'**Objetivo 4 - {objetivos[3]["titulo"]}**'):
        st.write('')

    # Objetivo 5
    with st.expander(f'**Objetivo 5 - {objetivos[4]["titulo"]}**'):
        st.write('')

    # Objetivo 6
    with st.expander(f'**Objetivo 6 - {objetivos[5]["titulo"]}**'):
        st.write('')

    # Objetivo 7
    with st.expander(f'**Objetivo 7 - {objetivos[6]["titulo"]}**'):
        st.write('')

    # Objetivo 8
    with st.expander(f'**Objetivo 8 - {objetivos[7]["titulo"]}**'):
        st.write('')   
        