import streamlit as st
from pymongo import MongoClient
import time
import random
import smtplib
from email.mime.text import MIMEText
from funcoes_auxiliares import conectar_mongo



###########################################################################################################
# Conectando ao MongoDB
###########################################################################################################

ddd
db = conectar_mongo()  # Isso vai usar o cache automaticamente
colaboradores = db["Colaboradores"]


###########################################################################################################
# Funções
###########################################################################################################


def enviar_email(destinatario, codigo): 
    remetente = st.secrets["senhas"]["endereco_email"]
    senha = st.secrets["senhas"]["senha_email"]

    assunto = "Código Para Redefinição de Senha - Portal ISPN"
    corpo = f"""
    <html>
        <body>
            <p style='font-size: 1.5em;'>
                Seu código para redefinição é: <strong>{codigo}</strong>
            </p>
        </body>
    </html>
    """

    msg = MIMEText(corpo, "html", "utf-8")  # charset adicionado
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, destinatario, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False


@st.dialog("Recuperação de Senha")
def recuperar_senha_dialog():
    st.session_state.setdefault("codigo_enviado", False)
    st.session_state.setdefault("codigo_verificacao", "")
    st.session_state.setdefault("email_verificado", "")
    st.session_state.setdefault("codigo_validado", False)  # Novo estado para validar o código

    conteudo_dialogo = st.empty()  # Container para trocar o conteúdo

    # Etapa 1: Inserir e-mail
    if not st.session_state.codigo_enviado:
        with conteudo_dialogo.form(key="recover_password_form", border=False):
            
            st.write('')

            email = st.text_input("Digite seu e-mail:")
            
            if st.form_submit_button("Confirmar"):
                
                if email:
                    verificar_colaboradores = colaboradores.find_one({"E-mail": email})  
                
                    if verificar_colaboradores:
                        codigo = str(random.randint(100, 999))
                
                        if enviar_email(email, codigo):
                            st.session_state.codigo_verificacao = codigo
                            st.session_state.codigo_enviado = True
                            st.session_state.email_verificado = email
                            st.success(f"Código enviado para {email}.")
                
                        else:
                            st.error("Erro ao enviar o e-mail. Tente novamente.")
                
                    else:
                        st.error("E-mail não encontrado. Tente novamente.")
                
                else:
                    st.error("Por favor, insira um e-mail.")

   # Etapa 2: Inserir código
    if st.session_state.codigo_enviado and not st.session_state.codigo_validado:
        
        with conteudo_dialogo.form(key="codigo_verificacao_form", border=False):
            
            st.subheader("Código de verificação")
            

            email = st.session_state.email_verificado.replace("@", "​@")  # O caractere invisível está entre as aspas
            st.info(f"Um código foi enviado para: **{email}**")

            
            codigo_input = st.text_input("Informe o código recebido por e-mail", placeholder="000")
            enviar_codigo = st.form_submit_button("Verificar")

            if enviar_codigo:
                if codigo_input == st.session_state.codigo_verificacao:
                    sucesso = st.success("✅ Código verificado com sucesso!")
                    
                    # Espera 2 segundos antes de limpar a mensagem e avançar para a próxima etapa
                    time.sleep(2)
                    
                    # Limpa a mensagem de sucesso
                    sucesso.empty()

                    # Avança para a próxima etapa
                    st.session_state.codigo_validado = True
                
                else:
                    st.error("❌ Código inválido. Tente novamente.")


    # Etapa 3: Definir nova senha
    if st.session_state.codigo_validado:
        
        with conteudo_dialogo.form("nova_senha_form", border=True):
            st.markdown("### Defina sua nova senha")
            nova_senha = st.text_input("Nova senha", type="password")
            confirmar_senha = st.text_input("Confirme a senha", type="password")
            enviar_nova_senha = st.form_submit_button("Salvar")

            if enviar_nova_senha:
        
                if nova_senha == confirmar_senha and nova_senha.strip():
                    # Atualiza no banco de dados (MongoDB)
                    colaboradores.update_one(
                        {"E-mail": st.session_state.email_verificado},
                        {"$set": {"Senha": nova_senha}}
                    )
                    st.success("Senha redefinida com sucesso!")
                    
                    # Limpa os estados após redefinir a senha
                    for key in ["codigo_enviado", "codigo_verificacao", "email_verificado", "codigo_validado"]:
                        st.session_state.pop(key, None)
                    
                    # Define o usuário como logado (pode ser usado para redirecionar)
                    st.session_state.logged_in = True

                    # Adiciona um tempo de espera de 2 segundos
                    time.sleep(2)

                    # Redireciona o usuário para a página principal ou perfil após redefinir a senha
                    st.rerun()

                else:
                    st.error("As senhas não coincidem ou estão vazias.")



# Função para a tela de login
def login():


    st.markdown(
        """
        <div style="text-align: center;">
            <img src="https://ispn.org.br/site/wp-content/uploads/2021/04/logo_ISPN_2021.png" width="300"/>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write('')
    st.write('')
    st.write('')

    st.markdown("<div style='text-align: center;'><h1 style='color: #666;'><strong>Portal do ISPN</strong></h1></div>", unsafe_allow_html=True)

    st.write('')
    st.write('')
    st.write('')


    col1, col2, col3 = st.columns([2, 3, 2])

    # Formulário para a tela de login
    with col2.form("login_form", border=False):
        # Input do usuário para a senha
        password = st.text_input("Insira a senha", type="password")

        # Verificar se o usuário clicou no botão de login
        if st.form_submit_button("Entrar"):
            # Consultar o banco de dados MongoDB somente pela senha
            usuario = colaboradores.find_one({"Senha": password})

            if usuario:
                # Senha válida encontrada
                st.session_state["logged_in"] = True
                st.success("Login bem-sucedido!")
                time.sleep(2)  # Pausa para mostrar a mensagem
                st.rerun()  # Recarrega a página após login bem-sucedido
            else:
                st.error("Senha inválida ou usuário não encontrado!")
                
    # Mostrar o botão "Esqueci a senha" caso o login falhe
    col2.button("Esqueci a senha", key="forgot_password", type="tertiary", on_click=recuperar_senha_dialog)


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
        "Projetos.py", 
        "Fundo Ecos.py", 
        "Indicadores.py", 
        "Pessoas.py", 
        "Viagens.py",
        "Monitoramento PLs.py", 
        "Manuais.py"
    ])

    # Chama o método run() para executar a página selecionada
    pg.run()
