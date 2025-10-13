import streamlit as st
# import pandas as pd 
from funcoes_auxiliares import conectar_mongo_portal_ispn
# from bson import ObjectId
from pymongo import MongoClient
# from datetime import date
# import re
# import time
# from urllib.parse import quote
# import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials



# ##################################################################
# CONFIGURAÇÕES DA INTERFACE
# ##################################################################

st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Eventos")
st.write('')


# # CSS PARA DIALOGO MAIOR
# st.markdown(
#     """
# <style>
# div[data-testid="stDialog"] div[role="dialog"]:has(.big-dialog) {
#     width: 55vw;
    
# }
# </style>
# """,
#     unsafe_allow_html=True,
# )


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
sheet_id = st.secrets.ids.id_planilha_recebimento





# # Escopo necessário para acessar os dados do Google Sheets
# scope = [
#     "https://www.googleapis.com/auth/spreadsheets"
# ]

# # Autenticação usando a conta de serviço

# # Ler credenciais do st.secrets
# creds_dict = st.secrets["credentials_drive"]
# # Criar credenciais do Google usando os dados do st.secrets
# creds = Credentials.from_service_account_info(creds_dict, scopes=scope)

# client = gspread.authorize(creds)

# # ID da planilha
# sheet_id = st.secrets.ids.id_planilha_recebimento



# # ##################################################################
# # FUNÇÕES AUXILIARES
# # ##################################################################

# Carregar Eventos no google sheets ------------------------------
def carregar_eventos():

    sheet = client.open_by_key(sheet_id)
    
    values_eventos = sheet.worksheet("SAVs INTERNAS Portal").get_all_values()

    # Criar DataFrame de SAVs. A primeira linha é usada como cabeçalho
    df_savs = pd.DataFrame(values_eventos[1:], columns=values_eventos[0])

    # Converter as colunas de data para datetime
    df_savs["Submission Date"] = pd.to_datetime(df_savs["Submission Date"])  # Garantir que é datetime
    df_savs["Submission Date"] = df_savs["Submission Date"].dt.strftime("%d/%m/%Y")  # Converter para string no formato brasileiro

    # Filtar SAVs com o prefixo "SAV-"
    df_savs = df_savs[df_savs['Código da viagem:'].str.upper().str.startswith('SAV-')]

    df_savs = df_savs.replace({r'\$': r'\$'}, regex=True)

    return df_savs