import streamlit as st
import pandas as pd
import time
from datetime import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn 
from bson import ObjectId



###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
###########################################################################################################

# Conecta-se ao banco de dados MongoDB (usa cache automático para melhorar performance)
db = conectar_mongo_portal_ispn()

# Define as coleções específicas que serão utilizadas a partir do banco
#estatistica = db["estatistica"]
colaboradores = db["colaboradores"]
estrategia = db["estrategia"]


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
    # if df_novo.shape != df_antigo.shape:
    #     return True

    # # Compara índice e colunas
    # if not df_novo.index.equals(df_antigo.index):
    #     return True
    # if not df_novo.columns.equals(df_antigo.columns):
    #     return True

    # Compara valores (elemento a elemento)
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
    novo_problema = st.text_input("Problema", value=problema_atual)
    novo_proposito = st.text_input("Propósito", value=proposito_atual)
    novo_impacto = st.text_input("Impacto", value=impacto_atual)

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

    # Obtém a lista atual de estratégias, se existir
    lista_estrategias_atual = estrategia_doc.get("estrategia", {}).get("estrategias", []) if estrategia_doc else []

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

    # st.markdown("---")

    # # Organiza as estratégias por ordem alfabética
    # estrategias_ordenadas = sorted(lista_estrategias_atual, key=lambda x: x.get("titulo", "").lower())
    # opcoes_estrategias = ["- Nova estratégia -"] + [e["titulo"] for e in estrategias_ordenadas]

    # titulo_selecionado = st.selectbox("Selecione a estratégia para editar", options=opcoes_estrategias)
    # estrategia_selecionada = None
    # index_estrategia = None

    # if titulo_selecionado != "- Nova estratégia -":
    #     # Encontrar a estratégia com base no título
    #     estrategia_selecionada = next((e for e in lista_estrategias_atual if e["titulo"] == titulo_selecionado), None)
    #     index_estrategia = lista_estrategias_atual.index(estrategia_selecionada) if estrategia_selecionada else None

    # st.subheader("Editar estratégia" if estrategia_selecionada else "Adicionar nova estratégia")

    # novo_titulo = st.text_input("Título", value=estrategia_selecionada.get("titulo", "") if estrategia_selecionada else "")

    # # Atualizar estratégia existente
    # if estrategia_selecionada and st.button("Atualizar estratégia", key="atualizar_estrategia", icon=":material/save:"):
    #     lista_estrategias_atual[index_estrategia]["titulo"] = novo_titulo

    #     update_data = {"estrategia.estrategias": lista_estrategias_atual}
    #     if novo_titulo_pagina != titulo_pagina_atual:
    #         update_data["estrategia.titulo_pagina_estrategia"] = novo_titulo_pagina

    #     estrategia.update_one(
    #         {"_id": estrategia_doc["_id"]},
    #         {"$set": update_data}
    #     )
    #     st.success("Estratégia atualizada com sucesso!")
    #     time.sleep(2)
    #     st.rerun()

    # # Excluir estratégia
    # if estrategia_selecionada and st.button("Excluir estratégia", key="excluir_estrategia", icon=":material/delete:"):
    #     lista_estrategias_atual.pop(index_estrategia)

    #     update_data = {"estrategia.estrategias": lista_estrategias_atual}
    #     if novo_titulo_pagina != titulo_pagina_atual:
    #         update_data["estrategia.titulo_pagina_estrategia"] = novo_titulo_pagina

    #     estrategia.update_one(
    #         {"_id": estrategia_doc["_id"]},
    #         {"$set": update_data}
    #     )
    #     st.success("Estratégia excluída com sucesso!")
    #     time.sleep(2)
    #     st.rerun()

    # # Adicionar nova estratégia
    # if not estrategia_selecionada and st.button("Adicionar estratégia", key="adicionar_estrategia", icon=":material/add:"):
    #     update_data = {}

    #     if novo_titulo.strip():
    #         nova_estrategia = {
    #             "_id": str(ObjectId()),  # Gerar um novo ObjectId para a estratégia
    #             "titulo": novo_titulo
    #         }
    #         lista_estrategias_atual.append(nova_estrategia)
    #         update_data["estrategia.estrategias"] = lista_estrategias_atual

    #         if estrategia_doc:
    #             if novo_titulo_pagina != titulo_pagina_atual:
    #                 update_data["estrategia.titulo_pagina_estrategia"] = novo_titulo_pagina
    #             estrategia.update_one(
    #                 {"_id": estrategia_doc["_id"]},
    #                 {"$set": update_data}
    #             )
    #         else:
    #             estrategia.insert_one({
    #                 "estrategia": {
    #                     "titulo_pagina_estrategia": novo_titulo_pagina,
    #                     "estrategias": [nova_estrategia]
    #                 }
    #             })
    #         st.success("Nova estratégia adicionada com sucesso!")

    #     time.sleep(2)
    #     st.rerun()


# Função que adiciona uma nova anotação vazia para a atividade correspondente
def adicionar_anotacao(i, a_idx, at_idx):
    st.session_state[f"acoes_{i}"][a_idx]["atividades"][at_idx]["anotacoes"].append({
        "data": "",
        "anotacao": "",
        "autor": ""
    })



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
    
    # Tab para editar o título
    aba1, aba2, aba3 = st.tabs(["Título", "Metas", "Ações Estratégicas"])

    # Aba de Título
    with aba1:
        st.subheader("Editar Título do Resultado")
        st.write("")
        titulo_atual = resultado.get("titulo", "")
        novo_titulo = st.text_input("Novo título", value=titulo_atual)

        st.write("")

        if st.button("Salvar Título", key=f"salvar_titulo_{resultado_idx}"):
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

            if st.button("Adicionar Meta", key=f"btn_add_meta_{resultado_idx}"):
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

                if st.button("Salvar", key=f"salvar_meta_{resultado_idx}_{m_idx}"):
                    resultados[resultado_idx]["metas"][m_idx]["nome_meta_mp"] = novo_nome_meta
                    resultados[resultado_idx]["metas"][m_idx]["objetivo"] = novo_objetivo

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
            novo_titulo_acao = st.text_input("Título da nova ação estratégica", key=f"nova_acao_titulo_{resultado_idx}")

            st.markdown("---")
            st.markdown("### Atividades")
            nova_atividade = st.text_input("Descrição da atividade", key=f"nova_acao_atividade_{resultado_idx}")
            novo_responsavel = st.text_input("Responsável", key=f"nova_acao_responsavel_{resultado_idx}")

            # ✅ Campos de data convertidos para date_input e salvos como str
            nova_data_inicio = st.date_input("Data de início", key=f"nova_acao_data_inicio_{resultado_idx}", format="DD/MM/YYYY")
            nova_data_fim = st.date_input("Data de fim", key=f"nova_acao_data_fim_{resultado_idx}", format="DD/MM/YYYY")

            novo_status = st.selectbox(
                "Status",
                ["Pendente", "Em andamento", "Concluída"],
                index=0,
                key=f"nova_acao_status_{resultado_idx}"
            )

            st.markdown("---")
            st.markdown("### Anotações")
            nova_data_anot = st.date_input("Data da anotação", key=f"nova_acao_anot_data_{resultado_idx}", format="DD/MM/YYYY")
            novo_autor_anot = st.text_input("Autor da anotação", key=f"nova_acao_anot_autor_{resultado_idx}")
            novo_texto_anot = st.text_area("Anotação", key=f"nova_acao_anot_texto_{resultado_idx}")

            if st.button("Adicionar Ação Estratégica", key=f"btn_add_acao_{resultado_idx}"):
                nova_acao = {
                    "_id": str(ObjectId()),
                    "nome_acao_estrategica": novo_titulo_acao,
                    "atividades": [],
                }

                # Adiciona atividade se preenchida
                if nova_atividade.strip():
                    nova_atividade_dict = {
                        "_id": str(ObjectId()),
                        "atividade": nova_atividade,
                        "responsavel": novo_responsavel,
                        "data_inicio": nova_data_inicio.strftime("%d/%m/%Y"),
                        "data_fim": nova_data_fim.strftime("%d/%m/%Y"),
                        "status": novo_status,
                    }

                    # Adiciona anotação se preenchida
                    if novo_texto_anot.strip():
                        nova_atividade_dict["anotacoes"] = [{
                            "_id": str(ObjectId()),
                            "data": nova_data_anot.strftime("%d/%m/%Y"),
                            "autor": novo_autor_anot,
                            "anotacao": novo_texto_anot,
                        }]
                    else:
                        nova_atividade_dict["anotacoes"] = []

                    nova_acao["atividades"].append(nova_atividade_dict)

                resultados[resultado_idx].setdefault("acoes_estrategicas", []).append(nova_acao)

                estrategia.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                )

                st.success("Nova ação estratégica adicionada com sucesso!")
                time.sleep(2)
                st.rerun()
        
        st.write("")
        
        # 🔹 Edição das ações estratégicas existentes
        for a_idx, acao in enumerate(acoes):
            titulo_acao = acao.get("nome_acao_estrategica", f"Ação Estratégica {a_idx + 1}")
            with st.expander(f"{titulo_acao}"):
                abas = st.tabs(["Título", "Atividades", "Anotações"])

                # ---- Título ----
                with abas[0]:
                    novo_nome_acao = st.text_input(
                        "Título da Ação Estratégica",
                        value=titulo_acao,
                        key=f"acao_estrat_{resultado_idx}_{a_idx}"
                    )

                # ---- Atividades ----
                with abas[1]:
                    atividades = acao.get("atividades", [])
                    for atv_idx, atividade in enumerate(atividades):
                        nova_atividade = st.text_input(
                            "Descrição da Atividade",
                            value=atividade.get("atividade", ""),
                            key=f"atividade_{resultado_idx}_{a_idx}_{atv_idx}"
                        )
                        novo_responsavel = st.text_input(
                            "Responsável",
                            value=atividade.get("responsavel", ""),
                            key=f"responsavel_{resultado_idx}_{a_idx}_{atv_idx}"
                        )

                        # ✅ Conversão para date_input com fallback se for string
                        data_inicio_str = atividade.get("data_inicio", "")
                        data_fim_str = atividade.get("data_fim", "")

                        try:
                            data_inicio_dt = datetime.strptime(data_inicio_str, "%d/%m/%Y").date()
                        except:
                            data_inicio_dt = datetime.today().date()
                        try:
                            data_fim_dt = datetime.strptime(data_fim_str, "%d/%m/%Y").date()
                        except:
                            data_fim_dt = datetime.today().date()

                        nova_data_inicio = st.date_input(
                            "Data de Início",
                            value=data_inicio_dt,
                            key=f"data_inicio_{resultado_idx}_{a_idx}_{atv_idx}",
                            format="DD/MM/YYYY"
                        )
                        nova_data_fim = st.date_input(
                            "Data de Fim",
                            value=data_fim_dt,
                            key=f"data_fim_{resultado_idx}_{a_idx}_{atv_idx}",
                            format="DD/MM/YYYY"
                        )

                        novo_status = st.selectbox(
                            "Status",
                            ["Pendente", "Em andamento", "Concluída"],
                            index=["Pendente", "Em andamento", "Concluída"].index(
                                atividade.get("status", "Pendente")
                            ),
                            key=f"status_{resultado_idx}_{a_idx}_{atv_idx}"
                        )

                        atividade.update({
                            "atividade": nova_atividade,
                            "responsavel": novo_responsavel,
                            "data_inicio": nova_data_inicio.strftime("%d/%m/%Y"),
                            "data_fim": nova_data_fim.strftime("%d/%m/%Y"),
                            "status": novo_status,
                        })
                        if "_id" not in atividade:
                            atividade["_id"] = str(ObjectId())

                # ---- Anotações ----
                with abas[2]:
                    atividades = acao.get("atividades", [])
                    for atv_idx, atividade in enumerate(atividades):
                        anotacoes = atividade.get("anotacoes", [])
                        for nota_idx, anotacao in enumerate(anotacoes):
                            st.markdown(f"**Anotação {nota_idx + 1}**")

                            # ✅ Date input com conversão
                            data_str = anotacao.get("data", "")
                            try:
                                data_dt = datetime.strptime(data_str, "%d/%m/%Y").date()
                            except:
                                data_dt = datetime.today().date()

                            nova_data = st.date_input(
                                "Data",
                                value=data_dt,
                                key=f"anot_data_{resultado_idx}_{a_idx}_{atv_idx}_{nota_idx}",
                                format="DD/MM/YYYY"
                            )
                            novo_autor = st.text_input(
                                "Autor", value=anotacao.get("autor", ""),
                                key=f"anot_autor_{resultado_idx}_{a_idx}_{atv_idx}_{nota_idx}"
                            )
                            novo_texto = st.text_area(
                                "Anotação", value=anotacao.get("anotacao", ""),
                                key=f"anot_texto_{resultado_idx}_{a_idx}_{atv_idx}_{nota_idx}"
                            )
                            anotacao.update({
                                "data": nova_data.strftime("%d/%m/%Y"),
                                "autor": novo_autor,
                                "anotacao": novo_texto
                            })

                if st.button(f"Salvar", key=f"salvar_acao_{resultado_idx}_{a_idx}"):
                    resultados[resultado_idx]["acoes_estrategicas"][a_idx].update({
                        "nome_acao_estrategica": novo_nome_acao,
                        "atividades": atividades
                    })
                    estrategia.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                    )
                    st.success("Ação estratégica atualizada com sucesso!")
                    time.sleep(2)
                    st.rerun()

        
@st.dialog("Editar eixo da estratégia")
def editar_eixos_da_estrategia_dialog(estrategia_item, estrategia_doc, estrategia):
    novo_titulo = st.text_input("Eixo da estratégia:", estrategia_item.get("titulo", ""))
    
    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Salvar", use_container_width=False, icon=":material/save:"):
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
            
            
@st.dialog("Editar resultado de longo prazo")
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
    novo_titulo = st.text_input("Título do resultado", value=resultado.get("titulo", ""))

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


###########################################################################################################
# INTERFACE PRINCIPAL
###########################################################################################################


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

if "modo_edicao" not in st.session_state:
    st.session_state.modo_edicao = False


st.header("Planejamento Estratégico")
st.write('')


aba_tm, aba_est, aba_res_mp, aba_res_lp, aba_ebj_est_ins = st.tabs(['Teoria da mudança', 'Estratégia', 'Resultados MP 2025', 'Resultados LP 2030', 'Objetivos Estratégicos Institucionais'])

# Aba Teoria da mudança
with aba_tm:
    
    # Busca o documento da coleção 'estrategia' que contenha a chave "teoria da mudança"
    teoria_doc = estrategia.find_one({"teoria da mudança": {"$exists": True}})

    # Inicializa os textos com valores padrão
    problema = "Problema não cadastrado ainda."
    proposito = "Propósito não cadastrado ainda."
    impacto = "Impacto não cadastrado ainda."

    # Se o documento for encontrado, percorre a lista e extrai os textos
    if teoria_doc:
        lista_tm = teoria_doc.get("teoria da mudança", [])
        for item in lista_tm:
            if "problema" in item:
                problema = item["problema"]
            if "proposito" in item:
                proposito = item["proposito"]
            if "impacto" in item:
                impacto = item["impacto"]

    tipos_usuario = st.session_state.get("tipo_usuario", [])
    if "adm" in tipos_usuario:
        col1, col2 = st.columns([7, 1])
        with col2:
            st.button("Editar página", icon=":material/edit:", key="editar_info_tm", on_click=editar_info_teoria_mudanca_dialog, use_container_width=True)

    st.write('')
    st.subheader('Teoria da Mudança')
    st.write('')

    st.write('**Problema:**')
    st.write(problema)

    st.write('')
    st.write('**Propósito:**')
    st.write(proposito)

    st.write('')
    st.write('**Impacto:**')
    st.write(impacto)


# Aba Estratégia
with aba_est:
    estrategia_doc = estrategia.find_one({"estrategia": {"$exists": True}})

    # Acessa o título e a lista de estratégias de forma segura
    titulo_pagina_atual = estrategia_doc.get("estrategia", {}).get("titulo_pagina_estrategia", "") if estrategia_doc else ""
    lista_estrategias_atual = estrategia_doc.get("estrategia", {}).get("eixos_da_estrategia", []) if estrategia_doc else []

    # Roteamento de tipo de usuário
    if set(st.session_state.tipo_usuario) & {"admin"}:
        col1, col2 = st.columns([7, 1])  # Ajuste os pesos conforme necessário
        col1.toggle('Modo de edição', value=False, key='modo_edicao_1')

        if st.session_state.modo_edicao_1:
            with col2:
                st.button("Editar página", icon=":material/edit:", key="editar_titulo_estrategia", on_click=editar_estrategia_dialog, use_container_width=True)

    st.write('')
    st.subheader(titulo_pagina_atual if titulo_pagina_atual else 'Promoção de Paisagens Produtivas Ecossociais')
    st.write('')

    col1, col2, col3 = st.columns(3)

    with col1:
        anos = list(range(1994, datetime.now().year + 1))
        ano_selecionado = st.selectbox("Selecione o ano:", sorted(anos, reverse=True))

    with col2:
        programa_selecionado = st.selectbox("Selecione o programa:", ["Todos os programas", "Programa 1", "Programa 2", "Programa 3"])

    with col3:
        projeto_selecionado = st.selectbox("Selecione o projeto:", ["Todos os projetos", "Projeto 1", "Projeto 2", "Projeto 3"])

    st.write('')

    # Função para ordenar estratégias com base no número do título
    def extrair_numero(estrategia):
        try:
            return int(estrategia["titulo"].split(" - ")[0])
        except:
            return float('inf')  # Coloca no final se não for possível extrair

    lista_estrategias_ordenada = sorted(lista_estrategias_atual, key=extrair_numero)

    for estrategia_item in lista_estrategias_ordenada:
        with st.expander(f"**{estrategia_item.get('titulo', 'Título não definido')}**"):
            
            if st.session_state.modo_edicao_1:
                
                col1, col2 = st.columns([7, 1])
                
                col2.button(
                    "Editar eixo",
                    key=f"editar_{estrategia_item['titulo']}",
                    on_click=editar_eixos_da_estrategia_dialog,
                    args=(estrategia_item, estrategia_doc, estrategia),
                    use_container_width=True, 
                    icon=":material/edit:"
                )

            st.write('')
            st.write('**ENTREGAS PLANEJADAS / REALIZADAS:**')

            # Dados simulados - substituir futuramente se necessário
            st.write('**Programa 1**')
            st.write('**Projeto 1**')
            st.dataframe(pd.DataFrame({
                "Entregas": ["Entrega 1", "Entrega 2", "Entrega 3"],
                "Status": ["realizado", "realizado", "não realizado"],
                "Ano": ['2020', '2021', '2022'],
            }), hide_index=True)

            st.write('')
            st.write('**Programa 2**')
            st.write('**Projeto 2**')
            st.dataframe(pd.DataFrame({
                "Entregas": ["Entrega 1", "Entrega 2", "Entrega 3"],
                "Status": ["realizado", "realizado", "não realizado"],
                "Ano": ['2020', '2021', '2022'],
            }), hide_index=True)

            st.divider()
            st.write('')
            st.write('**INDICADORES:**')
            st.dataframe(pd.DataFrame({
                "Indicador": [
                    "1.1 - Indicador x",
                    "1.2 - Indicador x",
                    "1.3 - Indicador x",
                    "1.4 - Indicador x",
                    "1.5 - Indicador x",
                ],
                "Alcançado": [120, 500, 2000, 3000, 1000]
            }), hide_index=True)



with aba_res_mp:
    # Título da seção
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {}) if doc else {}

    titulo_pagina = resultados_data.get("titulo_pagina_resultados_mp", "Resultados de Médio Prazo")
    lista_resultados = resultados_data.get("resultados_mp", [])

    # Roteamento de tipo de usuário
    if set(st.session_state.tipo_usuario) & {"admin"}:
        col1, col2 = st.columns([7, 1])  # Ajuste os pesos conforme necessário
        col1.toggle('Modo de edição', value=False, key='modo_edicao_2')

        if st.session_state.modo_edicao_2:
            with col2:
                st.button("Editar página", icon=":material/edit:", key="editar_titulo_result_mp", on_click=editar_titulo_pagina_resultados_mp_dialog, use_container_width=True)

    st.write('')
    st.subheader(titulo_pagina)
    st.write('')



    # # Botão de adicionar novo resultado de médio prazo só para admin
    # # Roteamento de tipo de usuário
    # if set(st.session_state.tipo_usuario) & {"admin"}:

    #     col1, col2 = st.columns([1, 7])  

    #     # Botão para adicionar novo resultado de médio prazo
    #     with col1:
    #         st.button(
    #             "Adicionar",
    #             key="adicionar_result_mp",
    #             icon=":material/add:",
    #             on_click=editar_titulo_de_cada_resultado_mp_dialog,
    #             kwargs={"resultado_idx": None}
    #         )




    # Lista os resultados de médio prazo
    for idx, resultado in enumerate(lista_resultados):
        with st.expander(resultado["titulo"]):
            
            # Botão para editar o título do resultado — aparece apenas no modo de edição
            if st.session_state.modo_edicao_2:
                col1, col2 = st.columns([2, 1])
                col2.button(
                    "Editar resultado",
                    icon=":material/edit:",
                    key=f"editar_resultado_{idx}",
                    on_click=lambda i=idx: editar_titulo_de_cada_resultado_mp_dialog(i),
                    use_container_width=True
                )
            
            # Metas
            metas = resultado.get("metas", [])
            if metas:
                df_metas = pd.DataFrame([
                    {
                        "Meta": m.get("nome_meta_mp", ""),
                        "Objetivo": m.get("objetivo", ""),
                        "Alcançado": ""
                    }
                    for m in metas
                ])

                # Modo edição
                if st.session_state.modo_edicao:
                    if "df_original" not in st.session_state:
                        st.session_state.df_original = df_metas.copy()

                    df_metas_editado = st.data_editor(
                        st.session_state.df_original,
                        hide_index=True,
                        key=f"tabela_metas_{idx}"
                    )

                    if df_tem_mudancas(df_metas_editado, st.session_state.df_original):
                        st.session_state.df_original = df_metas_editado.copy()
                        nova_lista = df_metas_editado.to_dict(orient="records")

                        estrategia.update_one(
                            {"_id": documento["_id"]},
                            {"$set": {"resultados_medio_prazo.resultados_mp": nova_lista}}
                        )
                        st.success("Alterações salvas automaticamente no MongoDB")

                # Modo leitura
                else:
                    st.dataframe(df_metas, hide_index=True)

            else:
                st.info("Nenhuma meta cadastrada.")

            # Ações estratégicas
            st.write("")
            st.write("**ENTREGAS:**")
            acoes = resultado.get("acoes_estrategicas", [])
            if not acoes:
                st.info("Nenhuma ação estratégica cadastrada.")
            else:
                for a_idx, acao in enumerate(acoes):
                    col_acao, col_popover = st.columns([7, 1])
                    with col_acao:
                        st.write(f"**{a_idx + 1} - {acao.get('nome_acao_estrategica', '')}**")
                    with col_popover:
                        with st.popover("Anotações"):
                            atividades = acao.get("atividades", [])
                            if atividades:
                                for atv in atividades:
                                    anotacoes = atv.get("anotacoes", [])
                                    if anotacoes:
                                        for anot in anotacoes:
                                            st.markdown(f"- **{anot.get('data', '')}**")
                                            st.markdown(f"*{anot.get('autor', '')}*")
                                            st.write(f"Anotação: {anot.get('anotacao', '')}")
                                            st.write("---")
                                    else:
                                        st.write("Sem anotações para esta atividade.")
                            else:
                                st.write("Sem atividades registradas.")

                    atividades = acao.get("atividades", [])
                    if atividades:
                        df_atividades = pd.DataFrame([
                            {
                                "Atividade": atv.get("atividade", ""),
                                "Responsável": atv.get("responsavel", ""),
                                "Início": atv.get("data_inicio", ""),
                                "Fim": atv.get("data_fim", ""),
                                "Status": atv.get("status", "")
                            }
                            for atv in atividades
                        ])
                        st.dataframe(df_atividades, hide_index=True)
                    else:
                        st.info("Nenhuma atividade registrada.")


with aba_res_lp:
    # --- Buscar dados no MongoDB ---
    doc = estrategia.find_one({"resultados_longo_prazo": {"$exists": True}})
    resultados_lp_data = doc.get("resultados_longo_prazo", {}) if doc else {}

    titulo_pagina_lp = resultados_lp_data.get("titulo_pagina_resultados_lp", "Resultados de Longo Prazo - 2030")
    lista_resultados_lp = resultados_lp_data.get("resultados_lp", [])

    # ==============================================================
    # Cabeçalho e controle de edição
    # ==============================================================
    if set(st.session_state.tipo_usuario) & {"admin"}:
        col1, col2 = st.columns([7, 1])
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

    # ==============================================================
    # Lista de Resultados de Longo Prazo
    # ==============================================================
    if lista_resultados_lp:
        for idx, resultado in enumerate(lista_resultados_lp):
            with st.expander(resultado.get("titulo", f"Resultado {idx+1}")):
                
                # Botão para editar o resultado (somente no modo edição)
                if st.session_state.modo_edicao_lp:
                    col1, col2 = st.columns([7, 1])
                    col2.button(
                        "Editar resultado",
                        icon=":material/edit:",
                        key=f"editar_resultado_lp_{idx}",
                        on_click=lambda i=idx: editar_titulo_de_cada_resultado_lp_dialog(i),
                        use_container_width=True
                    )

                st.write('')
                st.write('**INDICADORES:**')

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

                    # --- Modo de edição ---
                    if st.session_state.modo_edicao_lp:
                        if f"df_original_lp_{idx}" not in st.session_state:
                            st.session_state[f"df_original_lp_{idx}"] = df_indicadores.copy()

                        df_editado = st.data_editor(
                            st.session_state[f"df_original_lp_{idx}"],
                            hide_index=True,
                            key=f"tabela_indicadores_lp_{idx}"
                        )

                        # Verifica se houve alterações e atualiza no MongoDB
                        if df_tem_mudancas(df_editado, st.session_state[f"df_original_lp_{idx}"]):
                            st.session_state[f"df_original_lp_{idx}"] = df_editado.copy()
                            nova_lista = df_editado.to_dict(orient="records")

                            estrategia.update_one(
                                {"_id": doc["_id"]},
                                {f"$set": {f"resultados_longo_prazo.resultados_lp.{idx}.indicadores": nova_lista}}
                            )
                            st.success("Alterações salvas automaticamente no MongoDB")

                    # --- Modo leitura ---
                    else:
                        st.dataframe(df_indicadores, hide_index=True)

                else:
                    st.info("Nenhum indicador cadastrado.")
    else:
        st.info("Nenhum resultado de longo prazo encontrado no banco de dados.")


with aba_ebj_est_ins:
    st.write('')
    st.subheader('Objetivos Estratégicos Organizacionais')
    st.write('')

    with st.expander('**OBJETIVO 1 - Ampliação da captação de recursos com fontes de financiamento flexíveis e alinhadas à estratégia institucional do ISPN, bem como condições de contratação que gerem benefícios trabalhistas e sociais para a equipe.**'):
        st.write('')

        st.write('')

        st.write('**METAS:**')

        metas = {
            "Meta": [
                "Fontes de recursos flexíveis captadas para fortalecimento institucional",
            ],
            "Indicador": [
                "Contratos para fortalecimento institucional"
            ],

            "Objetivo": [
                "2",
            ],
            "Alcançado": [
                '1',
            ]
        }

        df_metas = pd.DataFrame(metas)
        st.dataframe(df_metas, hide_index=True)

        st.write('')


        st.write('**AÇÕES ESTRATÉGICAS:**')


        st.write('**1 - x**')

        # Dados
        acoes = {
            "Ações estratégicas": [
                "x",
                "x",
                "x",
                "x"
            ],
            "Responsável": [
                "Equipe Fundo Ecos",
                "",
                "x",
                "x"
            ],
            "Início": [
                "janeiro/2024",
                "",
                "janeiro/2024",
                ""
            ],
            "Fim": [
                "dezembro/2024",
                "dezembro/2024",
                "dezembro/2024",
                ""
            ],
            "Status": [
                "Em andamento",
                "Aguardando recursos",
                "",
                "Em andamento"
            ],
            "Observações": [
                "",
                "",
                "",
                ""
            ]
        }

        df_acoes_est = pd.DataFrame(acoes)
        st.dataframe(df_acoes_est, hide_index=True)


        st.write('')


        st.write('**2 - xs**')

        # Dados
        acoes = {
            "Ações estratégicas": [
                "x",
            ],
            "Responsável": [
                "Equipe Fundo Ecos",
            ],
            "Início": [
                "janeiro/2024",
            ],
            "Fim": [
                "dezembro/2024",
            ],
            "Status": [
                "Em andamento",
            ],
            "Observações": [
                "",
            ]
        }

        df_acoes_est = pd.DataFrame(acoes)
        st.dataframe(df_acoes_est, hide_index=True)


    with st.expander('**RESULTADO 2 - x**'):
        st.write('')

    with st.expander('**RESULTADO 3 - x**'):
        st.write('')        

    with st.expander('**RESULTADO 4 - x**'):
        st.write('')        

    with st.expander('**RESULTADO 5 - x**'):
        st.write('')        

    with st.expander('**RESULTADO 6 - x**'):
        st.write('')        

    with st.expander('**RESULTADO 7 - x**'):
        st.write('')        

    with st.expander('**RESULTADO 8 - x**'):
        st.write('')        
        