import streamlit as st
from pymongo import MongoClient
import random
import smtplib
from email.mime.text import MIMEText


###########################################################################################################
# Conectando ao MongoDB
###########################################################################################################


client = MongoClient("mongodb+srv://renato:4hzJ9zuHjr2xw6fH@ispn-gestao.ze7aoez.mongodb.net/?retryWrites=true&w=majority&appName=ISPN-Gestao") 
db = client["ISPN_Hub"]                     
colaboradores = db["Colaboradores"]  


###########################################################################################################
# Funções
###########################################################################################################



# Função para o diálogo de recuperação de senha
@st.dialog("Recuperação de Senha", width="large")
def recuperar_senha_dialog():

    # Cria uma aba para a recuperação de senha
    #st.subheader("Recuperação de Senha")

    # Cria o formulário para o usuário inserir o e-mail
    with st.form(key="recover_password_form"):
        email = st.text_input("Digite seu e-mail para definir uma nova senha:")

        # Submete o formulário
        submit_button = st.form_submit_button("Confirmar")

        if submit_button:
            if email:
                # Verifica se o e-mail existe na coleção do Mongo
                verificar_colaboradores = colaboradores.find_one({"E-mail": email})  
                if verificar_colaboradores:
                    st.success(f"Foi enviado um código para {email}.")
                else:
                    st.error("Por favor, insira um e-mail válido.")
            else:
                st.error("Por favor, insira um e-mail.")



# Função para a tela de login
def login():
    st.title("Tela de Login")
    
    # Entrada para o usuário e senha
    #username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    # Verificar se o usuário clicou no botão de login
    if st.button("Entrar"):
        # Verificação simples de login (personalize conforme necessário)
        if password == "123":
            st.session_state["logged_in"] = True
            st.success("Login bem-sucedido!")
            st.rerun()  # Recarrega a página após login bem-sucedido
        else:
            st.error("Usuário ou senha inválidos!")
            # Mostrar o botão "Esqueci a senha" caso o login falhe
            st.button("Esqueci a senha", key="forgot_password", type="tertiary", on_click=recuperar_senha_dialog)
    

##############################################################################################################

# Verifica se o usuário está logado
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    # Se não estiver logado, exibe a tela de login
    login()
    
else:
    # Se estiver logado, exibe a navegação entre páginas
    pg = st.navigation([
        "Institucional.py", 
        "Estratégia.py", 
        "Programas.py", 
        "Doadores.py", 
        "Projetos Institucionais.py", 
        "Fundo Ecos.py", 
        "Indicadores.py", 
        "Pessoas.py", 
        "Viagens.py", 
        "Manuais.py"
    ])

    # Chama o método run() para executar a página selecionada
    pg.run()
