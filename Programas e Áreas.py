import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
from funcoes_auxiliares import conectar_mongo_portal_ispn


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas
programas_areas = db["programas_areas"]  # Coleção de notícias monitoradas

# Buscando todos os documentos da coleção programas_areas
dados_programas = list(programas_areas.find())


######################################################################################################
# MAIN
######################################################################################################


# Lista para armazenar os programas e coordenadores
lista_programas = []

# Iterar sobre os documentos encontrados
for doc in dados_programas:
    for programa in doc.get("programas_areas", []):
        lista_programas.append({
            "titulo": programa.get("titulo_programa_area"),
            "coordenador": programa.get("coordenador")
        })


st.header("Programas")

st.write("")

df_equipe = pd.DataFrame(
    {
        "Nome": [
            "Ana",
            "Pedro",
            "João",
            "Maria",
            "Paulo"
        ],
        "Gênero": [
            "Feminino",
            "Masculino",
            "Masculino",
            "Feminino",
            "Masculino"
        ],
        "Projeto": [
            "CEPF",
            "FAMA",
            "FAMA",
            "GEF7",
            "Institucional"
        ]
    }
)


# Cria lista só com os títulos dos programas
titulos_abas = [p['titulo'] for p in lista_programas]

# Gera as abas no Streamlit
abas = st.tabs(titulos_abas)

# Para cada aba, exibe o conteúdo correspondente
for i, aba in enumerate(abas):
    with aba:
        programa = lista_programas[i]
        st.subheader(f"{programa['titulo']}")
        st.write(f"**Coordenador(a):** {programa['coordenador']}")

        st.write("")
    
        # with st.expander('**Equipe**'):
        st.write('**Equipe**:')

        st.write('5 colaboradores(as):')
        df_equipe.index += 1
        st.dataframe(df_equipe)
        st.divider()

        # PROJETOS

        st.write('')
        st.write('**Projetos:**')

        col1, col2, col3 = st.columns(3)
        col1.selectbox(
            "Situação",
            ["Todos", "Em andamento", "Concluído", "Cancelado"],
            key=f"situacao_{i}"
        )


        st.write('3 projetos:')
        # ui.table(dat"a=df_equipe)

        # Dados de exemplo
        dados_projetos = {
            "Nome do projeto": [
                "Projeto Água Viva",
                "Educação Verde",
                "Fortalecimento Comunitário"
            ],
            "início": [
                "março/2024",
                "abril/2024",
                "janeiro/2025"
            ],
            "Fim": [
                "fevereiro/2025",
                "dezembro/2024",
                "dezembro/2025"
            ],
            "Valor": [
                50000.00,
                120000.00,
                80000.00
            ],
            "Doador": [
                "Fundação X",
                "Instituto Y",
                "ONG Z"
            ],
            "Situação": [
                "Em andamento",
                "Em andamento",
                "Concluído"
            ]
        }

        # Criando o DataFrame
        df_projetos = pd.DataFrame(dados_projetos)
        df_projetos.index += 1

        # Exibindo o DataFrame
        # st.write('')
        st.dataframe(df_projetos)

        st.divider()

        # INDICADORES DO PROGRAMA
        st.write('')

        st.write('**Indicadores do Programa:**')
        st.write('')

        sel1, sel2, sel3 = st.columns(3)
        
        sel1.selectbox("Ano", ["2023", "2024", "2025"], key=f"ano_{i}")
        sel2.selectbox("Projeto", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3"], key=f"projeto_{i}")
        
        st.write('')
        st.write('')

        # Mostrar detalhes
        # Função principal decorada com dialog
        @st.dialog("Detalhes dos reportes de indicadores", width="large")
        def mostrar_detalhes():
            df_indicadores = pd.DataFrame({
                "Reporte": [
                    "Organizações do x",
                    "Projeto x",
                    "Preparação pra COP do Clima",
                    "Apoio à Central do Programa 1"
                ],
                "Valor": [
                    25,
                    2,
                    8,
                    18,
                ],
                "Ano": [
                    2023,
                    2023,
                    2023,
                    2023,
                ],"Projeto": [
                    "x",
                    "x",
                    "x",
                    "x do Programa 1",
                ],
                "Observações": [
                    "Contagem manual",
                    "Por conversa telefônica",
                    "Se refere ao seminário estadual",
                    "Contagem manual",
                ],
                "Autor": [
                    "João",
                    "Maria",
                    "José",
                    "Pedro",
                ]
            })
            # st.dataframe(df_indicadores, hide_index=True)

            ui.table(df_indicadores)


        # Função handler que será passada para on_click
        def handler():
            def _handler():
                mostrar_detalhes()
            return _handler


        col1, col2 = st.columns(2)

        with col1.container(border=True):
            st.write('**Organizações e Comunidades**')
            st.button("Indicador X **51**", on_click=handler(), type="tertiary", key=f"org_51_{i}")
            st.button("Indicador X **12**", on_click=handler(), type="tertiary", key=f"org_12_{i}")
            



        with col2.container(border=True):
        
            st.write('**Pessoas**')

            st.button("Indicador X **1500**", on_click=handler(), type="tertiary", key=f"pessoas_1500_{i}")
            st.button("Indicador X **300**", on_click=handler(), type="tertiary", key=f"pessoas_300_{i}")
            st.button("Indicador X **500**", on_click=handler(), type="tertiary", key=f"pessoas_500_{i}")
            st.button("Indicador X **350**", on_click=handler(), type="tertiary", key=f"pessoas_350_{i}")
            st.button("Indicador X **550**", on_click=handler(), type="tertiary", key=f"pessoas_550_{i}")
            st.button("Indicador X **200**", on_click=handler(), type="tertiary", key=f"pessoas_200_{i}")
            st.button("Indicador X **100**", on_click=handler(), type="tertiary", key=f"pessoas_100_{i}")
            st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"pessoas_50_{i}")
            st.button("Indicador X **75**", on_click=handler(), type="tertiary", key=f"pessoas_75_{i}")
            st.button("Indicador X **25**", on_click=handler(), type="tertiary", key=f"pessoas_25_{i}")

        with col1.container(border=True):
            st.write('**Capacitações**')
            st.button("Indicador X **10**", on_click=handler(), type="tertiary", key=f"cap_10_{i}")
            st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"cap_50_{i}")
            st.button("Indicador X **75**", on_click=handler(), type="tertiary", key=f"cap_75_{i}")
            st.button("Indicador X **60**", on_click=handler(), type="tertiary", key=f"cap_60_{i}")
            st.button("Indicador X **100**", on_click=handler(), type="tertiary", key=f"cap_100_{i}")


        with col1.container(border=True):
            st.write('**Intercâmbios**')
            st.button("Indicador X **10**", on_click=handler(), type="tertiary", key=f"inter_10_{i}")
            st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"inter_50_{i}")
            st.button("Indicador X **60**", on_click=handler(), type="tertiary", key=f"inter_60_{i}")

        with col2.container(border=True):
            st.write('**Território**')
            st.button("Indicador X **25**", on_click=handler(), type="tertiary", key=f"ter_25_{i}")
            st.button("Indicador X **235**", on_click=handler(), type="tertiary", key=f"ter_235_{i}")
            st.button("Indicador X **321**", on_click=handler(), type="tertiary", key=f"ter_321_{i}")
            st.button("Indicador X **58**", on_click=handler(), type="tertiary", key=f"ter_58_{i}")
            st.button("Indicador X **147**", on_click=handler(), type="tertiary", key=f"ter_147_{i}")

        with col1.container(border=True):
            st.write('**Tecnologia e Infra-estrutura**')
            st.button("Indicador X **20**", on_click=handler(), type="tertiary", key=f"tec_20_{i}")
            st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"tec_50_{i}")
            st.button("Indicador X **200**", on_click=handler(), type="tertiary", key=f"tec_200_{i}")

        with col1.container(border=True):
            st.write('**Financeiro**')
            st.button("Indicador X **25200**", on_click=handler(), type="tertiary", key=f"fin_25200_{i}")
            st.button("Indicador X **14000**", on_click=handler(), type="tertiary", key=f"fin_14000_{i}")

        with col2.container(border=True):
            st.write('**Comunicação**')
            st.button("Indicador X **25**", on_click=handler(), type="tertiary", key=f"com_25_{i}")
            st.button("Indicador X **14**", on_click=handler(), type="tertiary", key=f"com_14_{i}")
            st.button("Indicador X **12**", on_click=handler(), type="tertiary", key=f"com_12_{i}")
            st.button("Indicador X **35**", on_click=handler(), type="tertiary", key=f"com_35_{i}")
            st.button("Indicador X **24**", on_click=handler(), type="tertiary", key=f"com_24_{i}")

        with col1.container(border=True):
            st.write('**Políticas Públicas**')
            st.button("Indicador X **5**", on_click=handler(), type="tertiary", key=f"pol_5_{i}")
            st.button("Indicador X **2**", on_click=handler(), type="tertiary", key=f"pol_2_{i}")
            st.button("Indicador X **6**", on_click=handler(), type="tertiary", key=f"pol_6_{i}")






# with tab2:
#     st.subheader("Programa Programa 2")

# with tab3:
#     st.subheader("Programa Programa 3")

# with tab4:
#     st.subheader("Programa Programa 4")

# with tab5:
#     st.subheader("Programa Programa 5")

# with tab6:
#     st.subheader("Administrativo")