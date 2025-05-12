import streamlit as st
import pandas as pd
import time
from datetime import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn 


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


@st.dialog("Editar Informações das Estratégias", width="large")
def editar_titulo_estrategia_dialog():
    estrategia_doc = estrategia.find_one({"titulo_aba_estrategia": {"$exists": True}})
    titulo_pagina_atual = estrategia_doc["titulo_aba_estrategia"] if estrategia_doc else ""
    lista_estrategias_atual = estrategia_doc["estrategias"] if estrategia_doc and "estrategias" in estrategia_doc else []

    novo_titulo_pagina = st.text_input("Título da página de estratégias", value=titulo_pagina_atual)

    # Botão para atualizar o título da página
    if st.button("Atualizar título da página", key="atualizar_titulo_aba_estrategias"):
        if estrategia_doc:
            estrategia.update_one(
                {"_id": estrategia_doc["_id"]},
                {"$set": {"titulo_aba_estrategia": novo_titulo_pagina}}
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
        estrategia_selecionada = next((e for e in lista_estrategias_atual if e["titulo"] == titulo_selecionado), None)
        index_estrategia = lista_estrategias_atual.index(estrategia_selecionada) if estrategia_selecionada else None

    st.subheader("Editar estratégia" if estrategia_selecionada else "Adicionar nova estratégia")

    novo_titulo = st.text_input("Título", value=estrategia_selecionada.get("titulo", "") if estrategia_selecionada else "")

    # Atualizar estratégia existente
    if estrategia_selecionada and st.button("Atualizar estratégia", key="atualizar_estrategia"):
        lista_estrategias_atual[index_estrategia]["titulo"] = novo_titulo

        update_data = {"estrategias": lista_estrategias_atual}

        if novo_titulo_pagina != titulo_pagina_atual:
            update_data["titulo_aba_estrategia"] = novo_titulo_pagina

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

        update_data = {"estrategias": lista_estrategias_atual}
        if novo_titulo_pagina != titulo_pagina_atual:
            update_data["titulo_aba_estrategia"] = novo_titulo_pagina

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
            nova_estrategia = {"titulo": novo_titulo}
            lista_estrategias_atual.append(nova_estrategia)
            update_data["estrategias"] = lista_estrategias_atual

            if estrategia_doc:
                estrategia.update_one(
                    {"_id": estrategia_doc["_id"]},
                    {"$set": update_data}
                )
            else:
                estrategia.insert_one({
                    "titulo_aba_estrategia": novo_titulo_pagina,
                    "estrategias": [nova_estrategia]
                })
            st.success("Nova estratégia adicionada com sucesso!")

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
    estrategia_doc = estrategia.find_one({"titulo_aba_estrategia": {"$exists": True}})
    titulo_pagina_atual = estrategia_doc["titulo_aba_estrategia"] if estrategia_doc else ""
    lista_estrategias_atual = estrategia_doc["estrategias"] if estrategia_doc and "estrategias" in estrategia_doc else []

    if st.session_state.get("tipo_usuario") == "adm":
        col1, col2 = st.columns([7, 1])  # Ajuste os pesos conforme necessário
        with col2:
            st.button("Editar", icon=":material/edit:", key="editar_titulo_estrategia", on_click=editar_titulo_estrategia_dialog)

    st.write('')
    st.subheader(titulo_pagina_atual if titulo_pagina_atual else 'Promoção de Paisagens Produtivas Ecossociais')
    st.write('')

    col1, col2, col3 = st.columns(3)

    with col1:
        anos = list(range(1994, datetime.now().year + 1))
        ano_selecionado = st.selectbox("Selecione o ano:", sorted(anos, reverse=True))

    with col2:
        programa_selecionado = st.selectbox("Selecione o programa:", ["Todos os programas","Programa 1", "Programa 2", "Programa 3"])

    with col3:
        projeto_selecionado = st.selectbox("Selecione o projeto:", ["Todos os projetos", "Projeto 1", "Projeto 2", "Projeto 3"])

    st.write('')

    # Ordenar estratégias com base no número extraído do título, ex: "1 - Estratégia x"
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
        