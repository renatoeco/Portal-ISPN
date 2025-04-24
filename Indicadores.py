import streamlit as st
import pandas as pd 
import streamlit_shadcn_ui as ui

st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Indicadores")

st.write('')


with st.expander("Filtros"):

    tipo_selecionado = st.pills("Tipo de projeto", ["Projetos Institucionais", "Projetos Fundo Ecos"], selection_mode="multi", default=["Projetos Institucionais", "Projetos Fundo Ecos"])


    col1, col2, col3, col4 = st.columns(4)

    col1.multiselect("Doador", ["Todos", "USAID", "GEF", "UE", "Laudes Foundation"], default="Todos")
    col2.multiselect("Programa", ["Todos", "Cerrado", "Iniciativas Comunitárias", "Maranhão", "Sociobiodiversidade", "Povos Indígenas"], default="Todos")
    
    col3.selectbox("Indicadores reportados entre", ["2023", "2024", "2025"], key="doador1")
    col4.selectbox("e", ["2023", "2024", "2025"], key="doador2")

    if "Projetos Institucionais" in tipo_selecionado:
        st.write('')
        st.write('**Projetos Institucionais**')
        col1, col2, col3, col4 = st.columns(4)

        col1.multiselect("Projeto", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3", "Projeto 4", "Projeto 5"], default="Todos")




    if "Projetos Fundo Ecos" in tipo_selecionado:
        st.write('')
        st.write('**Projetos Fundo Ecos**')
        col1, col2, col3, col4 = st.columns(4)

        col1.multiselect("Edital", ["Todos", "Edital 35", "Edital 36", "Edital 37", "Edital 38", "Edital 39", "Edital 40","Edital 41"], default="Todos")

        # col2.multiselect("Ano do edital", ["Todos", "2017", "2018", "2019", "2020", "2021", "2022","2023"], default="Todos")


        col2.multiselect("Ponto focal", ["Todos", "Renato", "Lívia", "Matheus", "Vitória", "Terena"], default="Todos")

        col3.multiselect("Estado", ["Todos", "BA", "CE", "MA", "TO", "PA"], default="Todos")

        col4.multiselect("Município", ["Todos", "DF - Brasília", "CE - Crateús", "MA - Bacabal", "TO - Palmas", "PA - Belmonte"], default="Todos")

    # col3.multiselect("Situação", ["Todos", "Em dia", "Atrasados", "Concluídos", "Cancelados"], default="Todos")

        col1, col2, col3, col4 = st.columns(4)

        col1.text_input("Busca por proponente")

        col2.text_input("Busca por CNPJ")

        col3.text_input("Busca por sigla do projeto")

        col4.text_input("Busca por código do projeto")



# Mostrar detalhes
# Função principal decorada com dialog
@st.dialog("Detalhes dos reportes de indicadores", width="large")
def mostrar_detalhes():
    df_indicadores = pd.DataFrame({
        "Reporte": [
            "Organizações do Cerrativismo",
            "Projeto ADEL",
            "Preparação pra COP do Clima",
            "Apoio à Central do Cerrado"
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
            "Cerrativismo",
            "ADEL",
            "USAID",
            "Central do Cerrado",
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
    st.button("Número de organizações apoiadas: **51**", on_click=handler(), type="tertiary")
    st.button("Número de comunidades fortalecidas: **12**", on_click=handler(), type="tertiary")
    



with col2.container(border=True):

    st.write('**Pessoas**')

    st.button("Número de famílias: **1500**", on_click=handler(), type="tertiary")
    st.button("Número de homens jovens (até 29): **300**", on_click=handler(), type="tertiary")
    st.button("Número de homens adultos: **500**", on_click=handler(), type="tertiary")
    st.button("Número de mulheres jovens (até 29): **350**", on_click=handler(), type="tertiary")
    st.button("Número de mulheres adultas: **550**", on_click=handler(), type="tertiary")
    st.button("Número de Indígenas: **200**", on_click=handler(), type="tertiary")
    st.button("Número de lideranças comunitárias fortalecidas: **100**", on_click=handler(), type="tertiary")
    st.button("Número de fam. comercializando produtos da sociobio: **50**", on_click=handler(), type="tertiary")
    st.button("Número de famílias acessando vendas institucionais: **75**", on_click=handler(), type="tertiary")
    st.button("Número de estudantes recebendo bolsa: **25**", on_click=handler(), type="tertiary")

with col1.container(border=True):
    st.write('**Capacitações**')
    st.button("Número de capacitações realizadas: **10**", on_click=handler(), type="tertiary")
    st.button("Número de homens jovens capacitados (até 29): **50**", on_click=handler(), type="tertiary")
    st.button("Número de homens adultos capacitados: **75**", on_click=handler(), type="tertiary")
    st.button("Número de mulheres jovens capacitadas (até 29): **60**", on_click=handler(), type="tertiary")
    st.button("Número de mulheres adultas capacitadas: **100**", on_click=handler(), type="tertiary")


with col1.container(border=True):
    st.write('**Intercâmbios**')
    st.button("Número de intercâmbios realizados: **10**", on_click=handler(), type="tertiary")
    st.button("Número de homens em intercâmbios: **50**", on_click=handler(), type="tertiary")
    st.button("Número de mulheres em intercâmbios: **60**", on_click=handler(), type="tertiary")


with col2.container(border=True):
    st.write('**Território**')
    st.button("Número de iniciativas de Gestão Territorial implantadas: **25**", on_click=handler(), type="tertiary")
    st.button("Área com manejo ecológico do fogo (ha): **235**", on_click=handler(), type="tertiary")
    st.button("Área com manejo agroecológico (ha): **321**", on_click=handler(), type="tertiary")
    st.button("Área com manejo para restauração (ha): **58**", on_click=handler(), type="tertiary")
    st.button("Área com manejo para extrativismo (ha): **147**", on_click=handler(), type="tertiary")

with col1.container(border=True):
    st.write('**Tecnologia e Infra-estrutura**')
    st.button("Número de agroindústrias implementadas/reformadas: **20**", on_click=handler(), type="tertiary")
    st.button("Número de tecnologias instaladas: **50**", on_click=handler(), type="tertiary")
    st.button("Número de pessoas beneficiadas com tecnologias: **200**", on_click=handler(), type="tertiary")

with col1.container(border=True):
    st.write('**Financeiro**')
    st.button("Incremento médio do faturamento bruto das organizações apoiadas: **25200**", on_click=handler(), type="tertiary")
    st.button("Volume financeiro de vendas institucionais das organizações apoiadas: **14000**", on_click=handler(), type="tertiary")

with col2.container(border=True):
    st.write('**Comunicação**')
    st.button("Número de vídeos produzidos: **25**", on_click=handler(), type="tertiary")
    st.button("Número de aparições na mídia: **14**", on_click=handler(), type="tertiary")
    st.button("Número de publicações de caráter técnico: **12**", on_click=handler(), type="tertiary")
    st.button("Número de artigos acadêmicos produzidos e publicados: **35**", on_click=handler(), type="tertiary")
    st.button("Número de comunicadores comunitários contribuindo na execução das ações: **12**", on_click=handler(), type="tertiary")

with col1.container(border=True):
    st.write('**Políticas Públicas**')
    st.button("Número de políticas públicas monitoradas pelo Programa: **5**", on_click=handler(), type="tertiary")
    st.button("Número de Proposições Legislativas acompanhadas pelo Programa: **2**", on_click=handler(), type="tertiary")
    st.button("Número de contribuições que apoiam a construção e aprimoramento de pol. públicas: **6**", on_click=handler(), type="tertiary")
