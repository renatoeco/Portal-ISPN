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
estatistica = db["estatistica"]
colaboradores = db["colaboradores"]
estrategia = db["estrategia"]


###########################################################################################################
# FUNÇÕES
###########################################################################################################

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
    if st.button("Salvar alterações", key="salvar_teoria_mudanca"):
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
    if st.button("Atualizar título da página", key="atualizar_titulo_pagina_estrategias"):
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

    st.markdown("---")

    # Organiza as estratégias por ordem alfabética
    estrategias_ordenadas = sorted(lista_estrategias_atual, key=lambda x: x.get("titulo", "").lower())
    opcoes_estrategias = ["- Nova estratégia -"] + [e["titulo"] for e in estrategias_ordenadas]

    titulo_selecionado = st.selectbox("Selecione a estratégia para editar", options=opcoes_estrategias)
    estrategia_selecionada = None
    index_estrategia = None

    if titulo_selecionado != "- Nova estratégia -":
        # Encontrar a estratégia com base no título
        estrategia_selecionada = next((e for e in lista_estrategias_atual if e["titulo"] == titulo_selecionado), None)
        index_estrategia = lista_estrategias_atual.index(estrategia_selecionada) if estrategia_selecionada else None

    st.subheader("Editar estratégia" if estrategia_selecionada else "Adicionar nova estratégia")

    novo_titulo = st.text_input("Título", value=estrategia_selecionada.get("titulo", "") if estrategia_selecionada else "")

    # Atualizar estratégia existente
    if estrategia_selecionada and st.button("Atualizar estratégia", key="atualizar_estrategia"):
        lista_estrategias_atual[index_estrategia]["titulo"] = novo_titulo

        update_data = {"estrategia.estrategias": lista_estrategias_atual}
        if novo_titulo_pagina != titulo_pagina_atual:
            update_data["estrategia.titulo_pagina_estrategia"] = novo_titulo_pagina

        estrategia.update_one(
            {"_id": estrategia_doc["_id"]},
            {"$set": update_data}
        )
        st.success("Estratégia atualizada com sucesso!")
        time.sleep(2)
        st.rerun()

    # Excluir estratégia
    if estrategia_selecionada and st.button("Excluir estratégia", key="excluir_estrategia"):
        lista_estrategias_atual.pop(index_estrategia)

        update_data = {"estrategia.estrategias": lista_estrategias_atual}
        if novo_titulo_pagina != titulo_pagina_atual:
            update_data["estrategia.titulo_pagina_estrategia"] = novo_titulo_pagina

        estrategia.update_one(
            {"_id": estrategia_doc["_id"]},
            {"$set": update_data}
        )
        st.success("Estratégia excluída com sucesso!")
        time.sleep(2)
        st.rerun()

    # Adicionar nova estratégia
    if not estrategia_selecionada and st.button("Adicionar estratégia", key="adicionar_estrategia"):
        update_data = {}

        if novo_titulo.strip():
            nova_estrategia = {
                "_id": str(ObjectId()),  # Gerar um novo ObjectId para a estratégia
                "titulo": novo_titulo
            }
            lista_estrategias_atual.append(nova_estrategia)
            update_data["estrategia.estrategias"] = lista_estrategias_atual

            if estrategia_doc:
                if novo_titulo_pagina != titulo_pagina_atual:
                    update_data["estrategia.titulo_pagina_estrategia"] = novo_titulo_pagina
                estrategia.update_one(
                    {"_id": estrategia_doc["_id"]},
                    {"$set": update_data}
                )
            else:
                estrategia.insert_one({
                    "estrategia": {
                        "titulo_pagina_estrategia": novo_titulo_pagina,
                        "estrategias": [nova_estrategia]
                    }
                })
            st.success("Nova estratégia adicionada com sucesso!")

        time.sleep(2)
        st.rerun()


# Função que adiciona uma nova anotação vazia para a atividade correspondente
def adicionar_anotacao(i, a_idx, at_idx):
    st.session_state[f"acoes_{i}"][a_idx]["atividades"][at_idx]["anotacoes"].append({
        "data": "",
        "anotacao": "",
        "autor": ""
    })

# Função que adiciona uma nova meta vazia na aba correspondente
def adicionar_meta(i):
    st.session_state[f"metas_{i}"].append({"nome": "", "objetivo": ""})

# Função que adiciona uma nova ação estratégica vazia na aba correspondente
def adicionar_acao(i):
    st.session_state[f"acoes_{i}"].append({
        "nome": "",
        "responsavel": "",
        "data_inicio": "",
        "data_fim": "",
        "status": "",
        "atividades": []  # Inicializa atividades vazias
    })

# Função principal do diálogo para editar ou adicionar resultados de médio prazo
@st.dialog("Editar Título da Página", width="large")
def editar_titulo_pagina_resultados_mp_dialog():
    # Recupera os dados atuais do banco
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {}) if doc else {}

    # Título da aba principal de Resultados de Médio Prazo
    titulo_atual = resultados_data.get("titulo_pagina_resultados_mp", "")

    # Campo para editar o título da aba
    novo_titulo = st.text_input("Título da página de Resultados de Médio Prazo", value=titulo_atual)
    if st.button("Atualizar", key="atualizar_titulo_mp"):
        estrategia.update_one(
            {"_id": doc["_id"]},
            {"$set": {"resultados_medio_prazo.titulo_pagina_resultados_mp": novo_titulo}}
        )
        st.success("Título da página atualizado com sucesso!")
        time.sleep(2)
        st.rerun()


# Função principal do diálogo para editar ou adicionar resultados de médio prazo
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
            resultados[resultado_idx]["titulo"] = novo_titulo
            estrategia.update_one(
                {"_id": doc["_id"]},
                {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
            )
            st.success("Título do resultado atualizado com sucesso!")
            time.sleep(2)
            st.rerun()

    # Aba de Metas
    with aba2:
        #st.subheader("Editar Metas")
        #st.write("")
        metas = resultado.get("metas", [])
        for m_idx, meta in enumerate(metas):
            st.subheader(f"Editar Meta {m_idx + 1}")
            novo_nome_meta = st.text_input(f"Título", value=meta.get("nome_meta_mp", ""), key=f"nome_meta_{resultado_idx}_{m_idx}")
            novo_objetivo = st.text_input(f"Objetivo", value=meta.get("objetivo", ""), key=f"obj_{resultado_idx}_{m_idx}")

            st.write("")

            # Atualiza a meta na lista
            if st.button(f"Salvar", key=f"salvar_meta_{resultado_idx}_{m_idx}"):
                resultados[resultado_idx]["metas"][m_idx]["nome_meta_mp"] = novo_nome_meta
                resultados[resultado_idx]["metas"][m_idx]["objetivo"] = novo_objetivo
                estrategia.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                )
                st.success(f"Meta {m_idx + 1} atualizada com sucesso!")
                time.sleep(2)
                st.rerun()

            st.markdown("---")


    # Aba de Ações Estratégicas
    with aba3:
        
        #st.subheader("Editar Ações Estratégicas")
        #st.write("")
        acoes = resultado.get("acoes_estrategicas", [])
        for a_idx, acao in enumerate(acoes):
            st.markdown(f"### Editar Ação Estratégica {a_idx + 1}")
            novo_nome_acao = st.text_input(f"Título", value=acao.get("nome_acao_estrategica", ""), key=f"acao_estrat_{resultado_idx}_{a_idx}")
            # Campos para editar as atividades dentro de cada ação estratégica
            atividades = acao.get("atividades", [])

            st.write("")

            for atv_idx, atividade in enumerate(atividades):
                st.markdown(f"#### Atividade {atv_idx + 1}")

                nova_atividade = st.text_input(f"Atividade - Descrição", value=atividade.get("atividade", ""), key=f"atividade_{resultado_idx}_{a_idx}")

                novo_responsavel = st.text_input(f"Responsável", value=atividade.get("responsavel", ""), key=f"responsavel_{resultado_idx}_{a_idx}")

                
                nova_data_inicio = st.text_input(
                    f"Data de Início",
                    value=atividade.get("data_inicio", ""),
                    key=f"data_inicio_{resultado_idx}_{a_idx}_{atv_idx}"
                )

                nova_data_fim = st.text_input(
                    f"Data de Fim",
                    value=atividade.get("data_fim", ""),
                    key=f"data_fim_{resultado_idx}_{a_idx}_{atv_idx}"
                )


                novo_status = st.selectbox(f"Status", ["Pendente", "Em andamento", "Concluída"], index=["Pendente", "Em andamento", "Concluída"].index(atividade.get("status", "Pendente")))

                
                st.write("")
                # Salvando atividades
                if st.button(f"Salvar", key=f"salvar_atividade_{resultado_idx}_{a_idx}_{atv_idx}"):
                    resultados[resultado_idx]["acoes_estrategicas"][a_idx]["atividades"][atv_idx]["atividade"] = nova_atividade
                    resultados[resultado_idx]["acoes_estrategicas"][a_idx]["atividades"][atv_idx]["responsavel"] = novo_responsavel
                    resultados[resultado_idx]["acoes_estrategicas"][a_idx]["atividades"][atv_idx]["data_inicio"] = str(nova_data_inicio)
                    resultados[resultado_idx]["acoes_estrategicas"][a_idx]["atividades"][atv_idx]["data_fim"] = str(nova_data_fim)
                    resultados[resultado_idx]["acoes_estrategicas"][a_idx]["atividades"][atv_idx]["status"] = novo_status
                    resultados[resultado_idx]["acoes_estrategicas"][a_idx]["nome_acao_estrategica"] = novo_nome_acao

                    estrategia.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                    )
                    st.success(f"Ação estratégica e atividade atualizadas com sucesso!")
                    time.sleep(2)
                    st.rerun()

            st.markdown("---")



###########################################################################################################
# INTERFACE PRINCIPAL
###########################################################################################################


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Estratégia")


aba_tm, aba_est, aba_res_2025, aba_res_2030, aba_ebj_est_ins = st.tabs(['Teoria da mudança', 'Estratégia', 'Resultados MP 2025', 'Resultados LP 2030', 'Objetivos Estratégicos Institucionais'])

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
        
    if st.session_state.get("tipo_usuario") == "adm":
        col1, col2 = st.columns([7, 1])  # Ajuste os pesos conforme necessário
        with col2:
            st.button("Editar", icon=":material/edit:", key="editar_info_tm", on_click=editar_info_teoria_mudanca_dialog)

    
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
    lista_estrategias_atual = estrategia_doc.get("estrategia", {}).get("estrategias", []) if estrategia_doc else []

    if st.session_state.get("tipo_usuario") == "adm":
        col1, col2 = st.columns([7, 1])
        with col2:
            st.button("Editar", icon=":material/edit:", key="editar_titulo_estrategia", on_click=editar_estrategia_dialog)

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

            st.write('')
            st.write('**AÇÕES PLANEJADAS / REALIZADAS:**')

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



with aba_res_2025:
    # Título da seção
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {}) if doc else {}
    
    titulo_pagina = resultados_data.get("titulo_pagina_resultados_mp", "Resultados de Médio Prazo")
    lista_resultados = resultados_data.get("resultados_mp", [])

    if st.session_state.get("tipo_usuario") == "adm":
        col1, col2 = st.columns([7, 1])  # Ajuste os pesos conforme necessário
        with col2:
            st.button("Editar", icon=":material/edit:", key="editar_result_mp", on_click=editar_titulo_pagina_resultados_mp_dialog)

    st.subheader(titulo_pagina)
    st.write('')

    for idx, resultado in enumerate(lista_resultados):
        titulo_resultado = resultado.get("titulo", f"Resultado {idx + 1}")
        with st.expander(f"**{titulo_resultado}**"):
            # Botão de edição para ADM
            if st.session_state.get("tipo_usuario") == "adm":
                col1, col2 = st.columns([7, 1]) 
                with col2:
                    st.button(
                        "Editar",
                        key=f"editar_{idx}",
                        icon=":material/edit:",
                        on_click=editar_titulo_de_cada_resultado_mp_dialog,
                        kwargs={"resultado_idx": idx}  # você pode usar isso para passar o índice
                    )

            # Metas
            st.write("**METAS:**")
            metas = resultado.get("metas", [])
            if metas:
                df_metas = pd.DataFrame([
                    {
                        "Meta": m.get("nome_meta_mp", ""),
                        "Objetivo": m.get("objetivo", ""),
                        "Alcançado": ""  # Adapte conforme necessidade
                    }
                    for m in metas
                ])
                st.dataframe(df_metas, hide_index=True)
            else:
                st.info("Nenhuma meta cadastrada.")

            # Ações estratégicas
            st.write("")
            st.write("**AÇÕES ESTRATÉGICAS:**")
            acoes = resultado.get("acoes_estrategicas", [])
            if not acoes:
                st.info("Nenhuma ação estratégica cadastrada.")
            else:
                for a_idx, acao in enumerate(acoes):
                    st.write(f"**{a_idx + 1} - {acao.get('nome_acao_estrategica', '')}**")
                    atividades = acao.get("atividades", [])

                    if atividades:
                        df_atividades = pd.DataFrame([
                            {
                                "Atividade": atv.get("atividade", ""),
                                "Responsável": atv.get("responsavel", ""),
                                "Início": atv.get("data_inicio", ""),
                                "Fim": atv.get("data_fim", ""),
                                "Status": atv.get("status", ""),
                                "Observações": ", ".join([
                                    anot.get("anotacao", "")
                                    for anot in atv.get("anotacoes", [])
                                ])
                            }
                            for atv in atividades
                        ])
                        st.dataframe(df_atividades, hide_index=True)
                    else:
                        st.info("Nenhuma atividade registrada.")





with aba_res_2030:
    st.write('')
    st.subheader('Resultados de Longo Prazo - 2030')
    st.write('')

    with st.expander('**RESULTADO 1 - x**'):
        st.write('')

        st.write('**INDICADORES**')

        indicadores_data = {
            "Indicadores": [
                "x",
                "x"
            ],
            "Meta": [
                6,
                15000,
            ],
            "Alcançado": [
                2,
                1500,
            ]
        }

        df_indicadores_meta = pd.DataFrame(indicadores_data)
        st.dataframe(df_indicadores_meta, hide_index=True)


    with st.expander('**RESULTADO 2 - x**'):
        st.write('')

    with st.expander('**RESULTADO 3 - x**'):
        st.write('')        



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
        