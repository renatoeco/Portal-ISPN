import streamlit as st
import pandas as pd
import time
import streamlit_shadcn_ui as ui
from datetime import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn 
from bson import ObjectId
import re



###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
###########################################################################################################

# Conecta-se ao banco de dados MongoDB (usa cache automático para melhorar performance)
db = conectar_mongo_portal_ispn()

# Define as coleções específicas que serão utilizadas a partir do banco
#estatistica = db["estatistica"]
colaboradores = db["colaboradores"]
estrategia = db["estrategia"]
projetos_ispn = db["projetos_ispn"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


# Nome da página atual, usado como chave para contagem de acessos
# nome_pagina = "Estratégia"

# # Cria um timestamp formatado com dia/mês/ano hora:minuto:segundo
# timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# # Cria o nome do campo dinamicamente baseado na página
# campo_timestamp = f"{nome_pagina}.Visitas"

# # Atualiza a coleção de estatísticas com o novo acesso, incluindo o timestamp
# estatistica.update_one(
#     {},
#     {"$push": {campo_timestamp: timestamp}},
#     upsert=True  # Cria o documento se ele ainda não existir
# )


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
            
            # 🔹 Expander para adicionar nova meta
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
            
        # 🔹 Expander para adicionar nova meta
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

def buscar_entregas_relacionadas(titulo_referencia):
    """
    Busca entregas em todos os projetos que tenham o titulo_referencia em
    eixos_relacionados OR resultados_medio_prazo_relacionados OR resultados_longo_prazo_relacionados.
    Retorna lista de dicionários prontos para DataFrame.
    """
    entregas_filtradas = []

    # Obter projetos e dicionário de pessoas (para nomes dos responsáveis)
    projetos = list(projetos_ispn.find({}, {"entregas": 1, "sigla": 1, "programa": 1}))
    df_pessoas = pd.DataFrame(list(db["pessoas"].find()))
    if df_pessoas.empty:
        responsaveis_dict = {}
    else:
        df_pessoas_ordenado = df_pessoas.sort_values("nome_completo", ascending=True)
        responsaveis_dict = {
            str(row["_id"]): row["nome_completo"]
            for _, row in df_pessoas_ordenado.iterrows()
        }

    for projeto in projetos:
        sigla = projeto.get("sigla", "-")
        for entrega in projeto.get("entregas", []) or []:
            # Verifica as três possíveis ligações (eixo / resultado mp / resultado lp)
            if (
                titulo_referencia in entrega.get("eixos_relacionados", [])
                or titulo_referencia in entrega.get("resultados_medio_prazo_relacionados", [])
                or titulo_referencia in entrega.get("resultados_longo_prazo_relacionados", [])
            ):
                responsaveis_formatados = _format_responsaveis_list(entrega.get("responsaveis", []), responsaveis_dict)

                entregas_filtradas.append({
                    "Projeto": sigla,
                    "Entrega": entrega.get("nome_da_entrega", "-"),
                    "Previsão de Conclusão": entrega.get("previsao_da_conclusao", "-"),
                    "Responsáveis": responsaveis_formatados,
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
aba_est, aba_res_mp, aba_res_lp, aba_ebj_est_ins = st.tabs(['Estratégia', 'Resultados de Médio Prazo', 'Resultados de Longo Prazo', 'Objetivos Estratégicos Institucionais'])



# ---------------------------
# ABA ESTRATÉGIA
# ---------------------------
with aba_est:
    
    if "modo_edicao_1" not in st.session_state:
        st.session_state.modo_edicao_1 = False

    estrategia_doc = estrategia.find_one({"estrategia": {"$exists": True}})

    titulo_pagina_atual = estrategia_doc.get("estrategia", {}).get("titulo_pagina_estrategia", "") if estrategia_doc else ""
    lista_estrategias_atual = estrategia_doc.get("estrategia", {}).get("eixos_da_estrategia", []) if estrategia_doc else []

    # Modo edição (mantém sua lógica)
    if set(st.session_state.tipo_usuario) & {"admin"}:
        col1, col2 = st.columns([4, 1])
        col1.toggle('Modo de edição', value=False, key='modo_edicao_1')

        if st.session_state.modo_edicao_1:
            with col2:
                st.button(
                    "Editar página",
                    icon=":material/edit:",
                    key="editar_titulo_estrategia",
                    on_click=editar_estrategia_dialog,
                    use_container_width=True
                )

    st.write('')
    st.subheader(titulo_pagina_atual if titulo_pagina_atual else 'Promoção de Paisagens Produtivas Ecossociais')
    st.write('')

    # Filtros

    ver_filtros = st.toggle("Ver filtros", key="ver_filtros")

    if ver_filtros:

        col1, col2, col3 = st.columns(3)
        with col1:
            anos = list(range(1994, datetime.now().year + 1))
            ano_selecionado = st.selectbox("Selecione o ano:", sorted(anos, reverse=True))
        with col2:
            programa_selecionado = st.selectbox("Selecione o programa:", ["Todos os programas", "Programa 1", "Programa 2", "Programa 3"])
        with col3:
            projeto_selecionado = st.selectbox("Selecione o projeto:", ["Todos os projetos", "Projeto 1", "Projeto 2", "Projeto 3"])

    st.write('')

    # Carrega projetos uma vez
    projetos = list(projetos_ispn.find({}, {"entregas": 1, "sigla": 1, "programa": 1}))

    # Ordena eixos
    def extrair_numero(estrategia_item):
        try:
            return int(estrategia_item["titulo"].split(" - ")[0])
        except:
            return float('inf')

    lista_estrategias_ordenada = sorted(lista_estrategias_atual, key=extrair_numero)

    for eixo in lista_estrategias_ordenada:
        titulo_eixo = eixo.get("titulo", "Título não definido")

        with st.expander(f"**{titulo_eixo}**"):
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

            st.write('')
            st.write("**Entregas Planejadas / Realizadas:**")
            st.write('')

            # Usa a função para buscar entregas relacionadas ao eixo
            entregas_filtradas = buscar_entregas_relacionadas(titulo_eixo)

            if entregas_filtradas:
                # exibir com key única por eixo
                exibir_entregas_como_tabela(entregas_filtradas, key_prefix="tabela_entregas_eixo", key_suffix=titulo_eixo)
            else:
                st.warning("Nenhuma entrega registrada para este eixo.")

            st.divider()
            st.markdown("**Indicadores**")
            st.write("Indicadores ainda não integrados.")






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

# ---------------------------
# ABA RESULTADOS DE MÉDIO PRAZO
# ---------------------------

with aba_res_mp:
    
    if "modo_edicao_2" not in st.session_state:
        st.session_state.modo_edicao_2 = False
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {}) if doc else {}

    titulo_pagina = resultados_data.get("titulo_pagina_resultados_mp", "Resultados de Médio Prazo")
    lista_resultados = resultados_data.get("resultados_mp", [])

    if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}:
        col1, col2 = st.columns([4, 1])
        col1.toggle('Modo de edição', value=False, key='modo_edicao_2')

        if st.session_state.modo_edicao_2 and "admin" in st.session_state.tipo_usuario:
            with col2:
                st.button("Editar página", icon=":material/edit:", key="editar_titulo_result_mp", on_click=editar_titulo_pagina_resultados_mp_dialog, use_container_width=True)

    st.write('')
    st.subheader(titulo_pagina)
    st.write('')

    for idx, resultado in enumerate(lista_resultados):
        titulo_result = resultado.get("titulo", f"Resultado {idx+1}")
        with st.expander(titulo_result):
            # Botão editar título do resultado
            if st.session_state.modo_edicao_2:
                col1, col2 = st.columns([4, 1])
                col2.button(
                    "Editar resultado",
                    icon=":material/edit:",
                    key=f"editar_resultado_mp_{idx}",
                    on_click=lambda i=idx: editar_titulo_de_cada_resultado_mp_dialog(i),
                    use_container_width=True
                )

            # Metas (mantive sua lógica)
            metas = resultado.get("metas", [])
            if metas:
                st.markdown("##### Metas:")
                st.write("")

                df_metas = pd.DataFrame([
                    {"Meta": m.get("nome_meta_mp", ""), "Objetivo": m.get("objetivo", ""), "Alcançado": m.get("alcancado", "")}
                    for m in metas
                ])
                if st.session_state.get("modo_edicao"):
                    if f"df_original_mp_{idx}" not in st.session_state:
                        st.session_state[f"df_original_mp_{idx}"] = df_metas.copy()

                    df_metas_editado = st.data_editor(
                        st.session_state[f"df_original_mp_{idx}"],
                        hide_index=True,
                        key=f"tabela_metas_mp_{idx}"
                    )

                    if df_tem_mudancas(df_metas_editado, st.session_state[f"df_original_mp_{idx}"]):
                        st.session_state[f"df_original_mp_{idx}"] = df_metas_editado.copy()
                        nova_lista = df_metas_editado.to_dict(orient="records")

                        estrategia.update_one(
                            {"_id": doc["_id"]},
                            {"$set": {"resultados_medio_prazo.resultados_mp": nova_lista}}
                        )
                        st.success("Alterações salvas automaticamente no MongoDB")
                else:
                    st.dataframe(df_metas, hide_index=True)
            else:
                st.warning("Nenhuma meta cadastrada.")

            
            st.divider()
           # st.write("")
            

            # --- Exibir entregas relacionadas a este resultado de médio prazo ---
            st.markdown("##### Ações estratégicas e Entregas:")

            st.write("")
            #st.divider()

            acoes_estrategicas = resultado.get("acoes_estrategicas", [])

            if not acoes_estrategicas:
                st.warning("Nenhuma ação estratégica cadastrada para este resultado.")
            else:
                for idx_acao, acao in enumerate(acoes_estrategicas):

                    nome_acao = acao.get("nome_acao_estrategica", f"Ação {idx_acao+1}")

                    # Título da ação (SEM expander)
                    st.write(f"**{nome_acao}**")

                    # Buscar entregas vinculadas a esta ação
                    entregas_vinculadas = buscar_entregas_por_acao(nome_acao)

                    if entregas_vinculadas:
                        exibir_entregas_como_tabela(
                            entregas_vinculadas,
                            key_prefix="tabela_entrega_por_acao",
                            key_suffix=f"{idx}_{idx_acao}"
                        )
                    else:
                        st.warning("Nenhuma entrega vinculada a esta ação estratégica.")

                    # ✅ Separador visual entre as ações
                    st.divider()




# ---------------------------
# ABA RESULTADOS DE LONGO PRAZO
# ---------------------------
with aba_res_lp:
    
    if "modo_edicao_lp" not in st.session_state:
        st.session_state.modo_edicao_lp = False
        
    doc = estrategia.find_one({"resultados_longo_prazo": {"$exists": True}})
    resultados_lp_data = doc.get("resultados_longo_prazo", {}) if doc else {}

    titulo_pagina_lp = resultados_lp_data.get("titulo_pagina_resultados_lp", "Resultados de Longo Prazo - 2030")
    lista_resultados_lp = resultados_lp_data.get("resultados_lp", [])

    if set(st.session_state.tipo_usuario) & {"admin"}:
        col1, col2 = st.columns([4, 1])
        col1.toggle('Modo de edição', value=False, key='modo_edicao_lp')

        if st.session_state.modo_edicao_lp:
            with col2:
                st.button(
                    "Editar página",
                    icon=":material/edit:",
                    key="editar_titulo_result_lp",
                    on_click=editar_titulo_pagina_resultados_lp_dialog,
                    use_container_width=True
                )

    st.write('')
    st.subheader(titulo_pagina_lp)
    st.write('')

    if lista_resultados_lp:
        for idx, resultado in enumerate(lista_resultados_lp):
            titulo_result_lp = resultado.get("titulo", f"Resultado {idx+1}")
            with st.expander(titulo_result_lp):
                # Botão editar
                if st.session_state.modo_edicao_lp:
                    col1, col2 = st.columns([4, 1])
                    col2.button(
                        "Editar resultado",
                        icon=":material/edit:",
                        key=f"editar_resultado_lp_{idx}",
                        on_click=lambda i=idx: editar_titulo_de_cada_resultado_lp_dialog(i),
                        use_container_width=True
                    )

                st.write('')
                st.write('**Indicadores:**')

                indicadores = resultado.get("indicadores", [])
                if indicadores:
                    df_indicadores = pd.DataFrame([
                        {
                            "Indicador": ind.get("nome_indicador", ""),
                            "Meta": ind.get("meta", ""),
                            "Alcançado": ind.get("alcancado", "")
                        }
                        for ind in indicadores
                    ])

                    if st.session_state.modo_edicao_lp:
                        if f"df_original_lp_{idx}" not in st.session_state:
                            st.session_state[f"df_original_lp_{idx}"] = df_indicadores.copy()

                        df_editado = st.data_editor(
                            st.session_state[f"df_original_lp_{idx}"],
                            hide_index=True,
                            key=f"tabela_indicadores_lp_{idx}"
                        )

                        if df_tem_mudancas(df_editado, st.session_state[f"df_original_lp_{idx}"]):
                            st.session_state[f"df_original_lp_{idx}"] = df_editado.copy()
                            nova_lista = df_editado.to_dict(orient="records")

                            estrategia.update_one(
                                {"_id": doc["_id"]},
                                {f"$set": {f"resultados_longo_prazo.resultados_lp.{idx}.indicadores": nova_lista}}
                            )
                            st.success("Alterações salvas automaticamente no MongoDB")
                    else:
                        st.dataframe(df_indicadores, hide_index=True)
                else:
                    st.warning("Nenhum indicador cadastrado.")

                # --- Exibir entregas relacionadas a este resultado de longo prazo ---
                st.write('')
                st.markdown("**Entregas Planejadas / Realizadas:**")
                entregas_lp = buscar_entregas_relacionadas(titulo_result_lp)
                if entregas_lp:
                    exibir_entregas_como_tabela(entregas_lp, key_prefix="tabela_entregas_lp", key_suffix=f"{idx}_{titulo_result_lp}")
                else:
                    st.warning("Nenhuma entrega registrada para este resultado de longo prazo.")
    else:
        st.warning("Nenhum resultado de longo prazo encontrado no banco de dados.")


with aba_ebj_est_ins:
    
    doc = estrategia.find_one(
        {"objetivos_estrategicos_institucionais": {"$exists": True}},
        {"_id": 0, "objetivos_estrategicos_institucionais": 1}
    )

    objetivos = doc["objetivos_estrategicos_institucionais"]["obj_estrat_inst"]
    
    st.write('')
    st.subheader(doc["objetivos_estrategicos_institucionais"]["titulo_pagina_obj_estrat_inst"])
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
        