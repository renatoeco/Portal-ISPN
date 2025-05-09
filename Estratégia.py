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

    st.write('')
    st.subheader('Promoção de Paisagens Produtivas Ecossociais')
    st.write('')

    # st.markdown("<h5 style='text-align: left;'>Promoção de Paisagens Produtivas Ecossociais</h5>", unsafe_allow_html=True)
    # st.write('')

    col1, col2, col3 = st.columns(3)

    with col1:
        anos = list(range(1994, datetime.now().year + 1))
        ano_selecionado = st.selectbox("Selecione o ano:", sorted(anos, reverse=True))

    with col2:
        programa_selecionado = st.selectbox("Selecione o programa:", ["Todos os programas","Programa 1", "Programa 2", "Programa 3"])

    with col3:
        projeto_selecionado = st.selectbox("Selecione o projeto:", ["Todos os projetos", "Projeto 1", "Projeto 2", "Projeto 3"])

    st.write('')


    with st.expander('**1 - Estratégia 1**'):
        st.write('Descrição da estratégia.')

        st.write('')

        data = {
            "Entregas": [
                "Entrega 1",
                "Entrega 2",
                "Entrega 3"
            ],
            "Status": [
                "realizado",
                "realizado",
                "não realizado"
            ],
            "Ano": [
                '2020',
                '2021',
                '2022',
            ]
        }
        df = pd.DataFrame(data)
        
        st.write('')
        st.write('**AÇÕES PLANEJADAS / REALIZADAS:**')

        st.write('**Programa 1**')
        st.write('**Projeto 1**')
        st.dataframe(df, hide_index=True)


        st.write('')

        st.write('**Programa 2**')
        st.write('**Projeto 2**')
        st.dataframe(df, hide_index=True)

        st.divider()
        st.write('')
        st.write('**INDICADORES:**')

        df_indicadores = pd.DataFrame({
            "Indicador": [
                "1.1 - Indicador x",
                "1.2 - Indicador x",
                "1.3 - Indicador x",
                "1.4 - Indicador x",
                "1.5 - Indicador x",
            ],
            "Alcançado": [
                120,
                500,
                2000,
                3000,
                1000,
            ]
        })
        st.dataframe(df_indicadores, hide_index=True)

    with st.expander('**2 - Estratégia x**'):
        st.write('Descrição da estratégia')
    
    with st.expander('**3 - Estratégia x**'):
        st.write('Descrição da estratégia')

    with st.expander('**4 - Estratégia x**'):
        st.write('Descrição da estratégia')


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
        