import streamlit as st
import pandas as pd 
from funcoes_auxiliares import conectar_mongo_portal_ispn
# from bson import ObjectId
from pymongo import MongoClient
# from datetime import date
import re
# import time
# from urllib.parse import quote
# import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials



# ##################################################################
# CONFIGURAÇÕES DA INTERFACE
# ##################################################################

st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Eventos")
st.write('')




# # ##################################################################
# # CONEXÃO COM O BANCO DE DADOS MONGO
# # ##################################################################


# # BANCO DE DADOS ISPN HUB / PORTAL / GESTÃO -----------------

# db = conectar_mongo_portal_ispn()
# pessoas = db["pessoas"]


# # BANCO DE DADOS ISPN VIAGENS -----------------

# @st.cache_resource
# def get_mongo_client():
#     MONGODB_URI = st.secrets['senhas']['senha_mongo_portal_viagens']
#     return MongoClient(MONGODB_URI)

# cliente = get_mongo_client()
# banco_de_dados = cliente["plataforma_sav"]



# ##################################################################
# CONEXÃO COM GOOGLE SHEETS
# ##################################################################


# Função para criar o cliente do Google Sheets
@st.cache_resource
def get_gsheet_client():
    # Escopo necessário para acessar os dados do Google Sheets
    scope = ["https://www.googleapis.com/auth/spreadsheets"]

    # Ler credenciais do st.secrets
    creds_dict = st.secrets["credentials_drive"]

    # Criar credenciais do Google usando os dados do st.secrets
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)

    # Autorizar e retornar o cliente
    client = gspread.authorize(creds)
    return client

# Obter cliente usando cache
client = get_gsheet_client()

# ID da planilha
sheet_id = st.secrets.ids.id_planilha_recebimento_eventos






# ##################################################################
# FUNÇÕES AUXILIARES
# ##################################################################

# Carregar Eventos no google sheets ------------------------------
@st.cache_data
def carregar_eventos():

    sheet = client.open_by_key(sheet_id)
    
    values_eventos = sheet.worksheet("Jotform - Solicitações de Eventos").get_all_values()

    # Criar DataFrame de Eventos. A primeira linha é usada como cabeçalho
    df_eventos = pd.DataFrame(values_eventos[1:], columns=values_eventos[0])

    # Converter as colunas de data para datetime
    df_eventos["Submission Date"] = pd.to_datetime(df_eventos["Submission Date"])  # Garantir que é datetime

    # Ordenar em ordem decrescente
    df_eventos = df_eventos.sort_values(by="Submission Date", ascending=False)

    # Converter para string no formato brasileiro
    df_eventos["Submission Date"] = df_eventos["Submission Date"].dt.strftime("%d/%m/%Y")  

    df_eventos = df_eventos.replace({r'\$': r'\$'}, regex=True)

    return df_eventos



# FUNÇÃO PARA O DIÁLOGO DE DETALHES DO EVEENTO  ---------------------------------------------


@st.dialog("Detalhes do evento", width='large')
def detalhes_evento(codigo):
    evento = df_eventos[df_eventos["Código do evento:"] == codigo].iloc[0]

    st.subheader(f"📋 Detalhes do evento {codigo}")
    st.divider()

    st.write("**Data da solicitação:**", evento["Data da solicitação:"])
    st.write("**Get Page URL:**", evento["Get Page URL"])
    st.write("**Código do evento:**", evento["Código do evento:"])
    st.write("**Técnico(a) responsável:**", evento["Técnico(a) responsável:"])
    st.write("**Fonte de recurso:**", evento["Fonte de recurso:"])
    st.write("**Escritório responsável pelo evento:**", evento["Escritório responsável pelo evento:"])
    st.write("**Atividade:**", evento["Atividade:"])
    st.write("**Objetivo da atividade:**", evento["Objetivo da atividade:"])
    st.write("**Datas e horário do evento:**", evento["Datas e horário do evento:"])
    st.write("**Local:**", evento["Local"])
    st.write("**Número de participantes:**", evento["Número de participantes"])
    st.write("**Consultores:**", evento["Consultores"])

    st.divider()
    st.write("**1) Serão necessários materiais de papelaria como pastas, canetas, xerox, entre outros?**", 
             evento["1) Serão necessários materiais de papelaria como pastas, canetas, xerox, entre outros?"])
    st.write("**Detalhe os materiais de papelaria:**", evento["Detalhe os materiais de papelaria:"])

    st.write("**2) Será necessária hospedagem para os(as) participantes?**", 
             evento["2) Será necessária hospedagem para os(as) participantes?"])
    st.write("**Relacione os(as) participantes com hospedagem:**", evento["Relacione os(as) participantes com hospedagem:"])

    st.write("**3) Será necessário transporte para os(as) participantes?**", 
             evento["3) Será necessário transporte para os(as) participantes?"])
    st.write("**Detalhe o transporte dos(as) participantes:**", evento["Detalhe o transporte dos(as) participantes:"])

    st.write("**4) Será necessário o pagamento de diárias para Participantes? (Elaborar SAV de Terceiros)**", 
             evento["4) Será necessário o pagamento de diárias para Participantes? (Elaborar SAV de Terceiros)"])
    st.write("**Quantos participantes precisam receber diárias?**", evento["Quantos participantes precisam receber diárias?"])

    st.write("**5) Será necessário o pagamento de diárias para cozinheiras?**", 
             evento["5) Será necessário o pagamento de diárias para cozinheiras?"])
    st.write("**Informações para pagamento de apoio (cozinha e outros):**", evento["Informações para pagamento de apoio (cozinha e outros):"])

    st.write("**6) Será necessário o pagamento de alimentação?**", 
             evento["6) Será necessário o pagamento de alimentação?"])
    st.write("**Detalhe a alimentação necessária (café da manhã, almoço e janta):**", evento["Detalhe a alimentação necessária (café da manhã, almoço e janta):"])

    st.write("**7) Será necessário transporte para o(a) consultor(a)?**", 
             evento["7) Será necessário transporte para o(a) consultor(a)?"])
    st.write("**Detalhe o transporte de consultor(a):**", evento["Detalhe o transporte de consultor(a):"])

    st.write("**8) Será necessário adiantamento para pagamento de despesas da atividade?**", 
             evento["8) Será necessário adiantamento para pagamento de despesas da atividade?"])
    st.write("**Descreva o(s) adiantamento(s) necessário(s):**", evento["Descreva o(s) adiantamento(s) necessário(s):"])

    st.write("**9) Será necessário aluguel de veículo(s)?**", evento["9) Será necessário aluguel de veículo(s)?"])
    st.write("**Detalhes sobre a locação de veículo(s):**", evento["Detalhes sobre a locação de veículo(s):"])

    st.write("**10) Será necessária a compra de combustível?**", evento["10) Será necessária a compra de combustível?"])
    st.write("**Descreva os tipos, locais, quantidades e demais informações relevantes sobre a compra de combustível:**", 
             evento["Descreva os tipos, locais, quantidades e demais informações relevantes sobre a compra de combustível:"])

    st.divider()
    st.write("**Informações adicionais sobre o evento (caso seja necessário):**", evento["Informações adicionais sobre o evento (caso seja necessário):"])
    st.write("**Para confirmar a edição, insira a data e horário de agora.:**", evento["Para confirmar a edição, insira a data e horário de agora."])
    st.write("**Submission IP:**", evento["Submission IP"])
    st.write("**Submission URL:**", evento["Submission URL"])
    st.write("**Submission Edit URL:**", evento["Submission Edit URL"])
    st.write("**Last Update Date:**", evento["Last Update Date"])
    st.write("**CPF:**", evento["CPF"])
    st.write("**Submission ID:**", evento["Submission ID"])
    st.write("**Data do evento:**", evento["Data do evento"])


# FUNÇÕES PARA RENDERIZAR AS ABAS DE EVENTOS  ---------------------------------------------

def todos_os_eventos():

    st.write(df_eventos.columns)

    st.write('')

    largura_colunas = [2, 2, 5, 3, 3, 3]

    # Cabeçalho das colunas

    col1, col2, col3, col4, col5, col6 = st.columns(largura_colunas)

    col1.write('**Código:**')
    col2.write('**Solicitado em:**')
    col3.write('**Atividade**:')
    col5.write('**Nome do(a) solicitante**:')
    col4.write('**Data do evento**:')
    # col6.write('**Escritório**:')
    col6.write('')
    st.write('')

    # Para cada linha da tabela, lança 6 colunas, com um botão de detalhes na última coluna
    for index, row in df_eventos.iterrows():
        col1, col2, col3, col4, col5, col6 = st.columns(largura_colunas)

        col1.write(row['Código do evento:'])
        col2.write(row['Data da solicitação:'])
        col3.write(row['Atividade:'])
        col5.write(row['Técnico(a) responsável:'])
        col4.write(row['Data do evento'])
        # col6.write(row['Escritório responsável pelo evento:'])

        # Botão de detalhes
        col6.button("Detalhes", key=f"detalhes_{index}", icon=":material/list:", width="stretch", on_click=detalhes_evento, args=(row["Código do evento:"],))


def meus_eventos():
    st.write("Meus eventos")    

def nova_solicitacao():
    st.write("Nova Solicitação de Evento")

def cronograma_eventos():
    st.write("Cronograma de Eventos")



# ##################################################################
# CARREGAMENTO E TRATAMENTO DOS DADOS
# ##################################################################

df_eventos = carregar_eventos()

# /???????????
# st.write(df_eventos.columns)


# Renomear as colunas
df_eventos = df_eventos.rename(columns={
    "Submission Date": "Data da solicitação:",
    "Qual é a fonte do recurso?": "Fonte de recurso:",
})

# Função para extrair as datas
def extrair_datas(texto):
    padrao = r'Data de Início:\s*(\d{2}-\d{2}-\d{4}),\s*Data de Fim:\s*(\d{2}-\d{2}-\d{4})'
    match = re.search(padrao, texto)
    if match:
        data_inicio, data_fim = match.groups()
        return f"{data_inicio} a {data_fim}"
    return None

# Criar a nova coluna
df_eventos["Data do evento"] = df_eventos["Datas e horário do evento:"].apply(extrair_datas)









# ##################################################################
# INTERFACE
# ##################################################################



# # ??????????????????
# st.write(df_eventos)
# st.write(st.session_state)




# Roteamento de tipo de usuário. admin e gestao_eventos podem ver a aba Todos os eventos
if set(st.session_state.tipo_usuario) & {"admin", "gestao_eventos"}:

    tabs = st.tabs(["Todos os eventos", "Meus eventos", "Nova Solicitação"])

    # Aba Todos os eventos
    with tabs[0]:
        todos_os_eventos()

    # Aba Meus eventos
    with tabs[1]:
        meus_eventos()

    # Aba Nova Solicitação
    with tabs[2]:
        nova_solicitacao()

else:
    tabs = st.tabs(["Meus eventos", "Nova Solicitação"])



    # Aba Meus eventos
    with tabs[0]:
        st.write("Meus eventos")

    # Aba Nova Solicitação
    with tabs[1]:
        st.write("Nova Solicitação de Evento")


