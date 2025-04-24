import streamlit as st
from pymongo import MongoClient
import time
import random
import smtplib
from email.mime.text import MIMEText
from funcoes_auxiliares import conectar_mongo_portal_ispn



###########################################################################################################
# Conectando ao MongoDB
###########################################################################################################


db = conectar_mongo_portal_ispn()  # Isso vai usar o cache automaticamente
colaboradores = db["teste"]


###########################################################################################################
# Funções
###########################################################################################################


def encontrar_usuario_por_email(colaboradores, email_busca):
    for doc in colaboradores.find():
        for nome, dados in doc.items():
            if nome != "_id" and isinstance(dados, dict):
                if dados.get("e‑mail") == email_busca:
                    return nome, dados
            
    return None, None
 

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
            email = st.text_input("Digite seu e-mail:")
            if st.form_submit_button("Confirmar"):
                if email:
                    nome, verificar_colaboradores = encontrar_usuario_por_email(colaboradores, email)
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
            email_mask = st.session_state.email_verificado.replace("@", "​@")  # Caractere invisível entre aspas
            st.info(f"Um código foi enviado para: **{email_mask}**")

            codigo_input = st.text_input("Informe o código recebido por e-mail", placeholder="000")
            if st.form_submit_button("Verificar"):
                if codigo_input == st.session_state.codigo_verificacao:
                    sucesso = st.success("✅ Código verificado com sucesso!")
                    time.sleep(2)
                    sucesso.empty()
                    st.session_state.codigo_validado = True
                else:
                    st.error("❌ Código inválido. Tente novamente.")


    # Etapa 3: Definir nova senha
    if st.session_state.codigo_validado:


        # Cria um formulário com borda para redefinição de senha
        with conteudo_dialogo.form("nova_senha_form", border=True):
            st.markdown("### Defina sua nova senha")

            # Campos para digitar e confirmar a nova senha
            nova_senha = st.text_input("Nova senha", type="password")
            confirmar_senha = st.text_input("Confirme a senha", type="password")
            enviar_nova_senha = st.form_submit_button("Salvar")  # Botão de envio do formulário

            # Verifica se o botão foi pressionado
            if enviar_nova_senha:
                # Verifica se as senhas coincidem e não estão vazias
                if nova_senha == confirmar_senha and nova_senha.strip():

                    # Recupera o e-mail verificado salvo no estado da sessão
                    email = st.session_state.email_verificado

                    # Busca no banco de dados por um documento que contenha o e-mail em qualquer subcampo
                    documento_encontrado = colaboradores.find_one({
                        "$or": [
                            {f"{key}.e‑mail": email}
                            for doc in colaboradores.find()
                            for key in doc.keys()
                            if isinstance(doc.get(key), dict) and "e‑mail" in doc[key]
                        ]
                    })

                    if documento_encontrado:
                        # Tenta identificar a chave do usuário (ex: 'Renaaujo') no documento
                        usuario_chave = None
                        for chave, valor in documento_encontrado.items():
                            if isinstance(valor, dict) and valor.get("e‑mail") == email:
                                usuario_chave = chave
                                break

                        if usuario_chave:
                            # Cria os caminhos para os campos de e-mail e senha no documento
                            path_email = f"{usuario_chave}.e‑mail"
                            path_senha = f"{usuario_chave}.senha"

                            try:
                                # Atualiza a senha do usuário no banco de dados
                                result = colaboradores.update_one(
                                    {path_email: email},
                                    {"$set": {path_senha: nova_senha}}
                                )

                                if result.matched_count > 0:
                                    # Senha atualizada com sucesso
                                    st.success("Senha redefinida com sucesso!")

                                    # Remove variáveis relacionadas à verificação de e-mail da sessão
                                    for key in ["codigo_enviado", "codigo_verificacao", "email_verificado", "codigo_validado"]:
                                        st.session_state.pop(key, None)

                                    # Marca o usuário como logado e reinicia a aplicação
                                    st.session_state.logged_in = True
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("Erro ao redefinir a senha. Tente novamente.")
                            except Exception as e:
                                # Tratamento de erro caso a atualização falhe
                                st.error(f"Erro ao atualizar a senha: {e}")
                        else:
                            st.error("Usuário não encontrado com o e-mail informado.")
                    else:
                        st.error("Nenhum documento encontrado com esse e-mail.")
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
                time.sleep(2)  # Pausa para mostrar a mensagem
                st.rerun()  # Recarrega a página após login bem-sucedido
            else:
                st.error("Senha inválida ou usuário não encontrado!")
                
    # Mostrar o botão "Esqueci a senha" caso o login falhe
    col2.button("Esqueci a senha", key="forgot_password", type="tertiary", on_click=recuperar_senha_dialog)

    # Mensagem para o primeiro acesso
    col2.markdown("<div style='color: red;'><br>É o seu primeiro acesso?<br>Clique em \"Esqueci a senha\".</div>", unsafe_allow_html=True)

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
        "Programas e Áreas.py", 
        "Doadores.py", 
        "Projetos.py", 
        "Fundo Ecos.py", 
        "Indicadores.py", 
        "Pessoas.py", 
        "Viagens.py",
        "Férias.py",
        "Monitor de PLs.py", 
        "Manuais.py",
        
    ])

    # Chama o método run() para executar a página selecionada
    pg.run()
