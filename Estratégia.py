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
    titulo_pagina_atual = estrategia_doc.get("estrategia", {}).get("titulo_aba_estrategia", "") if estrategia_doc else ""

    # Obtém a lista atual de estratégias, se existir
    lista_estrategias_atual = estrategia_doc.get("estrategia", {}).get("estrategias", []) if estrategia_doc else []

    # Campo de entrada para um novo título da página de estratégias
    novo_titulo_pagina = st.text_input("Título da página de estratégias", value=titulo_pagina_atual)

    # Botão para atualizar o título da página
    if st.button("Atualizar título da página", key="atualizar_titulo_aba_estrategias"):
        if estrategia_doc:
            estrategia.update_one(
                {"_id": estrategia_doc["_id"]},
                {"$set": {"estrategia.titulo_aba_estrategia": novo_titulo_pagina}}
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
            update_data["estrategia.titulo_aba_estrategia"] = novo_titulo_pagina

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
            update_data["estrategia.titulo_aba_estrategia"] = novo_titulo_pagina

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
                    update_data["estrategia.titulo_aba_estrategia"] = novo_titulo_pagina
                estrategia.update_one(
                    {"_id": estrategia_doc["_id"]},
                    {"$set": update_data}
                )
            else:
                estrategia.insert_one({
                    "estrategia": {
                        "titulo_aba_estrategia": novo_titulo_pagina,
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
@st.dialog("Editar Resultados de Médio Prazo", width="large")
def editar_resultados_mp_dialog():
    # Recupera os dados atuais do banco
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {}) if doc else {}

    # Título da aba principal de Resultados de Médio Prazo
    titulo_atual = resultados_data.get("titulo_aba_resultados_mp", "")
    lista_resultados = resultados_data.get("resultados_mp", [])

    # Ordenar pelos números antes do " - " no título (sem regex)
    def extrair_numero(titulo):
        try:
            return int(titulo.split(" - ", 1)[0])
        except (ValueError, IndexError):
            return float("inf")  # Envia para o final se não for número

    lista_resultados = sorted(lista_resultados, key=lambda r: extrair_numero(r.get("titulo", "")))


    # Campo para editar o título da aba
    novo_titulo = st.text_input("Título da aba de Resultados de Médio Prazo", value=titulo_atual)
    if st.button("Atualizar título da aba", key="atualizar_titulo_mp"):
        estrategia.update_one(
            {"_id": doc["_id"]},
            {"$set": {"resultados_medio_prazo.titulo_aba_resultados_mp": novo_titulo}}
        )
        st.success("Título da aba atualizado com sucesso!")
        time.sleep(2)
        st.rerun()

    st.markdown("---")

    # Cria abas: uma para novo resultado + uma para cada resultado existente
    abas = ["+ Adicionar novo resultado"] + [r["titulo"] for r in lista_resultados]
    tabs = st.tabs(abas)

    for i, tab in enumerate(tabs):
        with tab:
            is_new = (i == 0)  # Se for a primeira aba, é novo resultado
            resultado_data = {} if is_new else lista_resultados[i - 1]

            st.subheader("Novo resultado" if is_new else "Editar resultado")
            novo_titulo_resultado = st.text_input("Título do resultado", value=resultado_data.get("titulo", ""), key=f"titulo_resultado_{i}")
            st.markdown("---")

            # Inicialização de campos dinâmicos para metas
            if f"metas_{i}" not in st.session_state:
                st.session_state[f"metas_{i}"] = (
                    [{"nome": "", "objetivo": ""}] if is_new else resultado_data.get("metas", [])
                )

            # Inicialização de campos dinâmicos para ações estratégicas
            if f"acoes_{i}" not in st.session_state:
                st.session_state[f"acoes_{i}"] = (
                    [ {
                        "nome": "",
                        "responsavel": "",
                        "data_inicio": "",
                        "data_fim": "",
                        "status": "",
                        "atividades": [{"responsavel": "", "data_inicio": "", "data_fim": "", "status": "", "anotacoes": []}]
                    }] if is_new else resultado_data.get("acoes_estrategicas", [])
                )

            # === Metas ===
            st.markdown("### Metas")
            for idx, meta in enumerate(st.session_state[f"metas_{i}"]):
                meta["nome"] = st.text_input("Meta", value=meta.get("nome", meta.get("nome_meta_mp", "")), key=f"meta_nome_{i}_{idx}")
                meta["objetivo"] = st.text_input("Objetivo", value=meta.get("objetivo", ""), key=f"meta_obj_{i}_{idx}")

            # Botão para adicionar nova meta
            st.write("")
            st.button("Adicionar nova meta", key=f"add_meta_btn_{i}", on_click=adicionar_meta, args=(i,))
            st.markdown("---")

            # === Ações Estratégicas ===
            st.markdown("### Ações Estratégicas")
            for a_idx, acao in enumerate(st.session_state[f"acoes_{i}"]):
                acao["nome"] = st.text_input("Ação Estratégica", value=acao.get("nome", acao.get("nome_acao_estrategica", "")), key=f"acao_nome_{i}_{a_idx}")
                acao["responsavel"] = st.text_input("Responsável", value=acao.get("responsavel", ""), key=f"acao_resp_{i}_{a_idx}")
                acao["data_inicio"] = st.text_input("Data de início", value=acao.get("data_inicio", ""), key=f"acao_ini_{i}_{a_idx}")
                acao["data_fim"] = st.text_input("Data de fim", value=acao.get("data_fim", ""), key=f"acao_fim_{i}_{a_idx}")
                acao["status"] = st.text_input("Status", value=acao.get("status", ""), key=f"acao_status_{i}_{a_idx}")

                # === Atividades ===
                for at_idx, atividade in enumerate(acao["atividades"]):
                    atividade["responsavel"] = st.text_input("Responsável da Atividade", value=atividade.get("responsavel", ""), key=f"atividade_resp_{i}_{a_idx}_{at_idx}")
                    atividade["data_inicio"] = st.text_input("Data de Início da Atividade", value=atividade.get("data_inicio", ""), key=f"atividade_ini_{i}_{a_idx}_{at_idx}")
                    atividade["data_fim"] = st.text_input("Data de Fim da Atividade", value=atividade.get("data_fim", ""), key=f"atividade_fim_{i}_{a_idx}_{at_idx}")
                    atividade["status"] = st.text_input("Status da Atividade", value=atividade.get("status", ""), key=f"atividade_status_{i}_{a_idx}_{at_idx}")

                    # === Anotações ===
                    st.markdown("---")
                    st.markdown("#### Anotações")
                    for n_idx, anotacao in enumerate(atividade["anotacoes"]):
                        anotacao["data"] = st.text_input("Data da anotação", value=anotacao.get("data", ""), key=f"anot_data_{i}_{a_idx}_{at_idx}_{n_idx}")
                        anotacao["anotacao"] = st.text_area("Texto da anotação", value=anotacao.get("anotacao", ""), key=f"anot_text_{i}_{a_idx}_{at_idx}_{n_idx}")
                        anotacao["autor"] = st.text_input("Autor", value=anotacao.get("autor", ""), key=f"anot_autor_{i}_{a_idx}_{at_idx}_{n_idx}")

                    st.write("")

                    st.button(
                        "Adicionar nova anotação",
                        key=f"add_anot_btn_{i}_{a_idx}_{at_idx}",
                        on_click=adicionar_anotacao,
                        args=(i, a_idx, at_idx)
                    )

                    st.markdown("---")

            # Botão para adicionar nova ação
            st.button("Adicionar nova ação estratégica", key=f"add_acao_btn_{i}", on_click=adicionar_acao, args=(i,))

            #st.markdown("---")

            # === Salvamento dos dados ===
            if is_new:
                # Adicionar novo resultado
                if st.button("Adicionar resultado", key=f"add_result_{i}"):
                    metas = [{
                        "_id": str(ObjectId()),
                        "nome_meta_mp": meta["nome"],
                        "objetivo": meta["objetivo"]
                    } for meta in st.session_state[f"metas_{i}"]]

                    acoes = []
                    for acao in st.session_state[f"acoes_{i}"]:
                        atividades = []
                        for atividade in acao["atividades"]:
                            atividades.append({
                                "responsavel": atividade["responsavel"],
                                "data_inicio": atividade["data_inicio"],
                                "data_fim": atividade["data_fim"],
                                "status": atividade["status"],
                                "anotacoes": [
                                    {
                                        "data": anot.get("data", ""),
                                        "anotacao": anot.get("anotacao", ""),
                                        "autor": anot.get("autor", "")
                                    } for anot in atividade.get("anotacoes", [])
                                ]
                            })


                        acoes.append({
                            "_id": acao.get("_id", str(ObjectId())),
                            "nome_acao_estrategica": acao["nome"],
                            "responsavel": acao["responsavel"],
                            "data_inicio": acao["data_inicio"],
                            "data_fim": acao["data_fim"],
                            "status": acao["status"],
                            "atividades": atividades
                        })


                    novo_resultado = {
                        "_id": str(ObjectId()),
                        "titulo": novo_titulo_resultado,
                        "metas": metas,
                        "acoes_estrategicas": acoes
                    }

                    lista_resultados.insert(0, novo_resultado)  # Adiciona no topo da lista

                    estrategia.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {
                            "resultados_medio_prazo.resultados_mp": lista_resultados,
                            "resultados_medio_prazo.titulo_aba_resultados_mp": novo_titulo
                        }}
                    )
                    st.success("Resultado adicionado com sucesso!")
                    # Limpa os campos após adicionar
                    st.session_state[f"metas_{i}"] = [{"nome": "", "objetivo": ""}]
                    st.session_state[f"acoes_{i}"] = [{"nome": "", "responsavel": "", "data_inicio": "", "data_fim": "", "status": "", "atividades": []}]
                    time.sleep(2)
                    st.rerun()
            else:
                # Atualização de resultado existente
                if st.button("Confirmar alterações", key=f"confirma_result_{i}"):
                    metas = [{
                        "_id": meta.get("_id", str(ObjectId())),
                        "nome_meta_mp": meta["nome"],
                        "objetivo": meta["objetivo"]
                    } for meta in st.session_state[f"metas_{i}"]]
                    
                    acoes = []
                    for acao in st.session_state[f"acoes_{i}"]:
                        atividades = []
                        for atividade in acao.get("atividades", []):
                            anotacoes = [
                                {
                                    "data": anot.get("data", ""),
                                    "anotacao": anot.get("anotacao", ""),
                                    "autor": anot.get("autor", "")
                                } for anot in atividade.get("anotacoes", [])
                            ]
                            atividades.append({
                                "responsavel": atividade.get("responsavel", ""),
                                "data_inicio": atividade.get("data_inicio", ""),
                                "data_fim": atividade.get("data_fim", ""),
                                "status": atividade.get("status", ""),
                                "anotacoes": anotacoes
                            })

                        acoes.append({
                            "_id": acao.get("_id", str(ObjectId())),
                            "nome_acao_estrategica": acao.get("nome", ""),
                            "responsavel": acao.get("responsavel", ""),
                            "data_inicio": acao.get("data_inicio", ""),
                            "data_fim": acao.get("data_fim", ""),
                            "status": acao.get("status", ""),
                            "atividades": atividades
                        })


                    lista_resultados[i - 1]["titulo"] = novo_titulo_resultado
                    lista_resultados[i - 1]["metas"] = metas
                    lista_resultados[i - 1]["acoes_estrategicas"] = acoes

                    estrategia.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {
                            "resultados_medio_prazo.resultados_mp": lista_resultados,
                            "resultados_medio_prazo.titulo_aba_resultados_mp": novo_titulo
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
    titulo_pagina_atual = estrategia_doc.get("estrategia", {}).get("titulo_aba_estrategia", "") if estrategia_doc else ""
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

    if st.session_state.get("tipo_usuario") == "adm":
        col1, col2 = st.columns([7, 1])  # Ajuste os pesos conforme necessário
        with col2:
            st.button("Editar", icon=":material/edit:", key="editar_result_mp", on_click=editar_resultados_mp_dialog)

    st.write('')
    st.subheader('Resultados de Médio Prazo - 2025')
    st.write('')
      

    st.write('')

    with st.expander('**RESULTADO 1 - XXXX**'):

        st.write('')

        st.write('**METAS:**')

        metas = {
            "Meta": [
                "Meta 1",
                "Meta 2",
            ],
            "Indicador": [
                "Indicador x",
                "Indicador x",
            ],

            "Objetivo": [
                "50%",
                "50%",
            ],
            "Alcançado": [
                '28%',
                '34%',
            ]
        }
        df_metas = pd.DataFrame(metas)
        st.dataframe(df_metas, hide_index=True)

        st.write('')


        st.write('**AÇÕES ESTRATÉGICAS:**')


        st.write('**1 - Ação estratégica x**')

        # Dados
        acoes = {
            "Ações estratégicas": [
                "Ação x",
                "Ação x",
                "Ação x",
                "Ação x"
            ],
            "Responsável": [
                "X",
                "Y",
                "Z",
                "W"
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

        st.write('Ações de projetos')

        df_acoes_proj = pd.DataFrame(
            {
                "Atividades": ["atv 1", "atv 2"],
                "Responsável": ["Y", "X"],
                "Programa": ["Programa 1", "Programa 2"],
                "Projeto": ["Y", "X"],
                "Status": ["Em andamento", "Aguardando recursos"],
                "Observações": ["", ""]
            }
        )

        st.dataframe(df_acoes_proj, hide_index=True)

        st.write('')

        st.write('**2 - Ação estratégica x**')

        # Dados
        acoes = {
            "Ações estratégicas": [
                "ação x",
                "ação x",
            ],
            "Responsável": [
                "Coordenadores",
                "x",
            ],
            "Início": [
                "janeiro/2024",
                "",
            ],
            "Fim": [
                "dezembro/2024",
                "dezembro/2024",
            ],
            "Status": [
                "Em andamento",
                "Aguardando recursos",
            ],
            "Observações": [
                "",
                "OBS x"
            ]
        }

        df_acoes_est = pd.DataFrame(acoes)
        st.dataframe(df_acoes_est, hide_index=True)
        st.write('Ações de projetos')

        df_acoes_proj = pd.DataFrame(
            {
                "Atividades": ["x", "y"],
                "Responsável": ["Equipe Fundo Ecos", "x"],
                "Programa": ["Programa 1", "Programa 2"],
                "Projeto": ["CEPF", "PACT"],
                "Status": ["Em andamento", "Aguardando recursos"],
                "Observações": ["", ""]
            }
        )

        st.dataframe(df_acoes_proj, hide_index=True)


        st.write('')

        st.write('**3 - Cção estratégica x**')

        # Dados
        acoes = {
            "Ações estratégicas": [
                "x",
                "y",
                "z ",
                "w"
            ],
            "Responsável": [
                "Equipe Fundo Ecos",
                "x",
                "y",
                "z"
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

        st.write('Ações de projetos')

        df_acoes_proj = pd.DataFrame(
            {
                "Atividades": ["x", "y"],
                "Responsável": ["Equipe Fundo Ecos", "x"],
                "Programa": ["Programa 2", "Programa 1"],
                "Projeto": ["CEPF", "PACT"],
                "Status": ["Em andamento", "Aguardando recursos"],
                "Observações": ["", ""]
            }
        )

        st.dataframe(df_acoes_proj, hide_index=True)



        st.write('')

        st.write('**4 - Ação estratégica x**')
        st.write('')

        st.write('**5 - Ação estratégica x**')
        st.write('')

        st.write('**6 - Pção estratégica x**')
        st.write('')

        st.write('**7 - Ação estratégica x**')
        st.write('')

        st.write('**8 - Ação estratégica x**')
        st.write('')

        st.write('**9 - Ação estratégica x**')
        st.write('')

        st.write('**10 - ção estratégica x**')
        st.write('')

        st.write('**11 - ção estratégica x**')

    with st.expander('**RESULTADO 2 - XXXX**'):
        st.write('')
    
    with st.expander('**RESULTADO 3 - XXXX**'):
        st.write('')



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
        