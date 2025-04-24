import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Programas")

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



tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Programa 1", "Programa 2", "Programa 3", "Programa 4", "Programa 5", "Programa 6"])

with tab1:
    st.subheader("Programa Programa 1")

    st.write('')

    
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
    col1.selectbox("Situação", ["Todos","Em andamento", "Concluído", "Cancelado"])

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
    
    sel1.selectbox("Ano", ["2023", "2024", "2025"])
    sel2.selectbox("Projeto", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3"])
    
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
        st.button("Indicador X **51**", on_click=handler(), type="tertiary", key="org_51")
        st.button("Indicador X **12**", on_click=handler(), type="tertiary", key="org_12")
        



    with col2.container(border=True):
    
        st.write('**Pessoas**')

        st.button("Indicador X **1500**", on_click=handler(), type="tertiary", key="pessoas_1500")
        st.button("Indicador X **300**", on_click=handler(), type="tertiary", key="pessoas_300")
        st.button("Indicador X **500**", on_click=handler(), type="tertiary", key="pessoas_500")
        st.button("Indicador X **350**", on_click=handler(), type="tertiary", key="pessoas_350")
        st.button("Indicador X **550**", on_click=handler(), type="tertiary", key="pessoas_550")
        st.button("Indicador X **200**", on_click=handler(), type="tertiary", key="pessoas_200")
        st.button("Indicador X **100**", on_click=handler(), type="tertiary", key="pessoas_100")
        st.button("Indicador X **50**", on_click=handler(), type="tertiary", key="pessoas_50")
        st.button("Indicador X **75**", on_click=handler(), type="tertiary", key="pessoas_75")
        st.button("Indicador X **25**", on_click=handler(), type="tertiary", key="pessoas_25")

    with col1.container(border=True):
        st.write('**Capacitações**')
        st.button("Indicador X **10**", on_click=handler(), type="tertiary", key="cap_10")
        st.button("Indicador X **50**", on_click=handler(), type="tertiary", key="cap_50")
        st.button("Indicador X **75**", on_click=handler(), type="tertiary", key="cap_75")
        st.button("Indicador X **60**", on_click=handler(), type="tertiary", key="cap_60")
        st.button("Indicador X **100**", on_click=handler(), type="tertiary", key="cap_100")


    with col1.container(border=True):
        st.write('**Intercâmbios**')
        st.button("Indicador X **10**", on_click=handler(), type="tertiary", key="inter_10")
        st.button("Indicador X **50**", on_click=handler(), type="tertiary", key="inter_50")
        st.button("Indicador X **60**", on_click=handler(), type="tertiary", key="inter_60")


    with col2.container(border=True):
        st.write('**Território**')
        st.button("Indicador X **25**", on_click=handler(), type="tertiary", key="ter_25")
        st.button("Indicador X **235**", on_click=handler(), type="tertiary", key="ter_235")
        st.button("Indicador X **321**", on_click=handler(), type="tertiary", key="ter_321")
        st.button("Indicador X **58**", on_click=handler(), type="tertiary", key="ter_58")
        st.button("Indicador X **147**", on_click=handler(), type="tertiary", key="ter_147")

    with col1.container(border=True):
        st.write('**Tecnologia e Infra-estrutura**')
        st.button("Indicador X **20**", on_click=handler(), type="tertiary", key="tec_20")
        st.button("Indicador X **50**", on_click=handler(), type="tertiary", key="tec_50")
        st.button("Indicador X **200**", on_click=handler(), type="tertiary", key="tec_200")

    with col1.container(border=True):
        st.write('**Financeiro**')
        st.button("Indicador X **25200**", on_click=handler(), type="tertiary", key="fin_25200")
        st.button("Indicador X **14000**", on_click=handler(), type="tertiary", key="fin_14000")

    with col2.container(border=True):
        st.write('**Comunicação**')
        st.button("Indicador X **25**", on_click=handler(), type="tertiary", key="com_25")
        st.button("Indicador X **14**", on_click=handler(), type="tertiary", key="com_14")
        st.button("Indicador X **12**", on_click=handler(), type="tertiary", key="com_12")
        st.button("Indicador X **35**", on_click=handler(), type="tertiary", key="com_35")
        st.button("Indicador X **12**", on_click=handler(), type="tertiary", key="com_24")

    with col1.container(border=True):
        st.write('**Políticas Públicas**')
        st.button("Indicador X **5**", on_click=handler(), type="tertiary", key="pol_5")
        st.button("Indicador X **2**", on_click=handler(), type="tertiary", key="pol_2")
        st.button("Indicador X **6**", on_click=handler(), type="tertiary", key="pol_6")






with tab2:
    st.subheader("Programa Programa 2")

with tab3:
    st.subheader("Programa Programa 3")

with tab4:
    st.subheader("Programa Programa 4")

with tab5:
    st.subheader("Programa Programa 5")

with tab6:
    st.subheader("Administrativo")