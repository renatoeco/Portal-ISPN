import streamlit as st





# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
from datetime import datetime
# import time

from funcoes_auxiliares import conectar_mongo_portal_ispn


# Exibe o logo do ISPN na página
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

# Cabeçalho da página
st.header("Wekan")
st.write('')

######################################################################################################
# CONEXÃO COM O BANCO
######################################################################################################


# Conecta no MongoDB
db = conectar_mongo_portal_ispn()

estatistica = db["estatistica"]  # Coleção de estatísticas


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_kanban"
nome_pagina = "Kanban"

hoje = datetime.now().strftime("%d/%m/%Y")

pagina_anterior = st.session_state.get("pagina_anterior")
navegou_para_esta_pagina = (pagina_anterior != PAGINA_ID)

if navegou_para_esta_pagina:

    # Obter o único documento
    doc = estatistica.find_one({})

    # Criar o campo caso não exista
    if nome_pagina not in doc:
        estatistica.update_one(
            {},
            {"$set": {nome_pagina: []}}
        )

    estatistica.update_one(
            {},
            {"$inc": {f"{nome_pagina}.$[elem].numero_de_acessos": 1}},
            array_filters=[{"elem.data": hoje}]
        )

    estatistica.update_one(
        {f"{nome_pagina}.data": {"$ne": hoje}},
        {"$push": {
            nome_pagina: {"data": hoje, "numero_de_acessos": 1}
        }}
    )

# Registrar página anterior
st.session_state["pagina_anterior"] = PAGINA_ID






######################################################################################################
# INTERFACE
######################################################################################################
st.write('')



st.markdown("""
                
**Wekan** é uma ferramenta de **gestão de atividades** baseada no métido *Kanban*, que consiste em organizar **cartões de atividades** em **colunas**.

A forma mais clássica de usar o *kanban* é com 3 colunas: **'A fazer'**, **'Fazendo'** e **'Concluído'**.
                                    
As colunas são organizadas em um **painel**. Você pode ter um ou mais painéis.
            
Cada painel pode ser usado **individualmente** ou **em grupo**.
                            
""")


st.write('')

st.write('**Wekan** é um software independente que roda fora do sistema Jataí. Você precisa criar uma **conta de usuário** e uma **senha** para utilizá-lo.')




st.write('')
st.write('')
st.write('')
st.write('')
st.write('')
st.write('')




col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <div style="text-align:center;">
            <span class="material-icons" style="font-size:80px; color:#888;">
                account_balance
            </span><br>
            <br>
            <span style="font-size:18px;">
                Se você está conectado(a) na <b>rede wifi do escritório do ISPN em Brasília</b>
            </span><br><br>
            <a href="http://192.168.0.63:8081" target="_blank" style="font-size:22px;">
                Acesse por esse link
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        """
        <div style="text-align:center;">
            <span class="material-icons" style="font-size:80px; color:#888;">
                public
            </span><br>
            <br>
            <span style="font-size:18px;">
                Se você está <b>fora da rede wifi do ISPN de Brasília</b>
            </span><br><br>
            <a href="http://179.185.74.126:8081" target="_blank" style="font-size:22px;">
                Acesse por esse link
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )


