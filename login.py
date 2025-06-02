import streamlit as st  
from pymongo import MongoClient  
import time 
import random  
import smtplib  
from email.mime.text import MIMEText  
from funcoes_auxiliares import conectar_mongo_portal_ispn  # Função personalizada para conectar ao MongoDB


##############################################################################################################
# CONEXÃO COM O BANCO DE DADOS (MONGODB)
###############################################################################################################

# Conecta ao banco de dados MongoDB usando função importada (com cache para otimizar desempenho)
db = conectar_mongo_portal_ispn()

# Define a coleção a ser utilizada, neste caso chamada "teste"
colaboradores = db["pessoas"]



##############################################################################################################
# FUNÇÕES AUXILIARES
##############################################################################################################

# Função que busca um usuário pelo e-mail dentro da coleção
# def encontrar_usuario_por_email(colaboradores, email_busca):
#     for doc in colaboradores.find():
#         for nome, dados in doc.items():
#             if nome != "_id" and isinstance(dados, dict):
#                 if dados.get("e‑mail") == email_busca:
#                     return nome, dados  # Retorna o nome do campo e os dados
#     return None, None  # Caso não encontre

def encontrar_usuario_por_email(colaboradores, email_busca):
    usuario = colaboradores.find_one({"e‑mail": email_busca})
    if usuario:
        return usuario.get("nome_completo"), usuario  # Retorna o nome e os dados do usuário
    return None, None  # Caso não encontre



# Função para enviar um e-mail com código de verificação
def enviar_email(destinatario, codigo):
    # Dados de autenticação, retirados do arquivo secrets.toml
    remetente = st.secrets["senhas"]["endereco_email"]
    senha = st.secrets["senhas"]["senha_email"]

    # Conteúdo do e-mail
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

    # Cria o e-mail formatado com HTML
    msg = MIMEText(corpo, "html", "utf-8")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    # Tenta enviar o e-mail via SMTP seguro (SSL)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, destinatario, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False


##############################################################################################################
# CAIXA DE DIÁLOGO PARA RECUPERAÇÃO DE SENHA
##############################################################################################################

@st.dialog("Recuperação de Senha")
def recuperar_senha_dialog():
    # Inicializa variáveis de sessão usadas no fluxo
    st.session_state.setdefault("codigo_enviado", False)
    st.session_state.setdefault("codigo_verificacao", "")
    st.session_state.setdefault("email_verificado", "")
    st.session_state.setdefault("codigo_validado", False)

    conteudo_dialogo = st.empty()  # Container que será atualizado conforme a etapa

    # --- Etapa 1: Solicitação do e-mail ---
    if not st.session_state.codigo_enviado:
        with conteudo_dialogo.form(key="recover_password_form", border=False):
            email = st.text_input("Digite seu e-mail:")
            if st.form_submit_button("Confirmar"):
                if email:
                    nome, verificar_colaboradores = encontrar_usuario_por_email(colaboradores, email)
                    if verificar_colaboradores:
                        codigo = str(random.randint(100, 999))  # Gera um código aleatório
                        if enviar_email(email, codigo):  # Envia o código por e-mail
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

    # --- Etapa 2: Verificação do código recebido ---
    if st.session_state.codigo_enviado and not st.session_state.codigo_validado:
        with conteudo_dialogo.form(key="codigo_verificacao_form", border=False):
            st.subheader("Código de verificação")
            email_mask = st.session_state.email_verificado.replace("@", "​@")  # Máscara leve no e-mail
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

    # --- Etapa 3: Definição da nova senha ---

    if st.session_state.codigo_validado:
        with conteudo_dialogo.form("nova_senha_form", border=True):
            st.markdown("### Defina sua nova senha")
            nova_senha = st.text_input("Nova senha", type="password")
            confirmar_senha = st.text_input("Confirme a senha", type="password")
            enviar_nova_senha = st.form_submit_button("Salvar")

            if enviar_nova_senha:
                if nova_senha == confirmar_senha and nova_senha.strip():
                    email = st.session_state.email_verificado

                    # Localiza o usuário pelo e-mail
                    usuario = colaboradores.find_one({"e‑mail": email})

                    if usuario:
                        try:
                            # Atualiza a senha no banco de dados
                            result = colaboradores.update_one(
                                {"e‑mail": email},
                                {"$set": {"senha": nova_senha}}
                            )

                            if result.matched_count > 0:
                                st.success("Senha redefinida com sucesso!")

                                # Limpa as variáveis da sessão
                                for key in ["codigo_enviado", "codigo_verificacao", "email_verificado", "codigo_validado"]:
                                    st.session_state.pop(key, None)

                                # Marca usuário como logado e reinicia o app
                                st.session_state.logged_in = True
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("Erro ao redefinir a senha. Tente novamente.")
                        except Exception as e:
                            st.error(f"Erro ao atualizar a senha: {e}")
                    else:
                        st.error("Nenhum usuário encontrado com esse e-mail.")
                else:
                    st.error("As senhas não coincidem ou estão vazias.")












    # if st.session_state.codigo_validado:
    #     with conteudo_dialogo.form("nova_senha_form", border=True):
    #         st.markdown("### Defina sua nova senha")
    #         nova_senha = st.text_input("Nova senha", type="password")
    #         confirmar_senha = st.text_input("Confirme a senha", type="password")
    #         enviar_nova_senha = st.form_submit_button("Salvar")

    #         if enviar_nova_senha:
    #             if nova_senha == confirmar_senha and nova_senha.strip():
    #                 email = st.session_state.email_verificado

    #                 # Tenta localizar o documento correspondente ao e-mail
    #                 documento_encontrado = colaboradores.find_one({
    #                     "$or": [
    #                         {f"{key}.e‑mail": email}
    #                         for doc in colaboradores.find()
    #                         for key in doc.keys()
    #                         if isinstance(doc.get(key), dict) and "e‑mail" in doc[key]
    #                     ]
    #                 })

    #                 if documento_encontrado:
    #                     usuario_chave = None
    #                     for chave, valor in documento_encontrado.items():
    #                         if isinstance(valor, dict) and valor.get("e‑mail") == email:
    #                             usuario_chave = chave
    #                             break

    #                     if usuario_chave:
    #                         path_email = f"{usuario_chave}.e‑mail"
    #                         path_senha = f"{usuario_chave}.senha"

    #                         try:
    #                             # Atualiza a senha no banco de dados
    #                             result = colaboradores.update_one(
    #                                 {path_email: email},
    #                                 {"$set": {path_senha: nova_senha}}
    #                             )

    #                             if result.matched_count > 0:
    #                                 st.success("Senha redefinida com sucesso!")

    #                                 # Limpa as variáveis da sessão
    #                                 for key in ["codigo_enviado", "codigo_verificacao", "email_verificado", "codigo_validado"]:
    #                                     st.session_state.pop(key, None)

    #                                 # Marca usuário como logado e reinicia o app
    #                                 st.session_state.logged_in = True
    #                                 time.sleep(2)
    #                                 st.rerun()
    #                             else:
    #                                 st.error("Erro ao redefinir a senha. Tente novamente.")
    #                         except Exception as e:
    #                             st.error(f"Erro ao atualizar a senha: {e}")
    #                     else:
    #                         st.error("Usuário não encontrado com o e-mail informado.")
    #                 else:
    #                     st.error("Nenhum documento encontrado com esse e-mail.")
    #             else:
    #                 st.error("As senhas não coincidem ou estão vazias.")


##############################################################################################################
# TELA DE LOGIN
##############################################################################################################

def login():
    # Exibe o logo e título
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
    st.write('')

    st.markdown("<div style='text-align: center;'><h1 style='color: #666;'><strong>Portal do ISPN</strong></h1></div>", unsafe_allow_html=True)
    st.write('')
    st.write('')
    st.write('')
    st.write('')

    # Cria colunas para centralizar o formulário
    col1, col2, col3 = st.columns([2, 3, 2])

    with col2.form("login_form", border=False):
    
        # Pede a senha
        password = st.text_input("Insira a senha", type="password")

        if st.form_submit_button("Entrar"):
            # Busca o documento correspondente à senha
            usuario_encontrado = None
            # tipo_usuario = "desconhecido"

            for doc in colaboradores.find():
                if doc.get("senha") == password:
                    usuario_encontrado = doc
                    tipo_usuario = doc.get("tipo de usuário", "desconhecido")
                    break

            # Se encontrou, loga o usuário
            if usuario_encontrado:
                st.session_state["logged_in"] = True
                st.session_state["tipo_usuario"] = tipo_usuario
                st.rerun()
            else:
                st.error("Senha inválida ou usuário não encontrado!")    
    
    
    
    
    
        # # Pede a senha
        # password = st.text_input("Insira a senha", type="password")

        # if st.form_submit_button("Entrar"):
        #     # Busca o documento correspondente à senha
        #     usuario_encontrado = None
        #     tipo_usuario = "desconhecido"

        #     for doc in colaboradores.find():
        #         for chave, valor in doc.items():
        #             if chave == "_id":
        #                 continue  # Ignora o _id
        #             if isinstance(valor, dict) and valor.get("senha") == password:
        #                 usuario_encontrado = valor
        #                 tipo_usuario_dict = valor.get("tipo de usuário", {})
        #                 tipo_usuario = list(tipo_usuario_dict.values()) 
        #                 break
        #         if usuario_encontrado:
        #             break

        #     # Se encontrou, loga o usuário
        #     if usuario_encontrado:
        #         st.session_state["logged_in"] = True
        #         st.session_state["tipo_usuario"] = tipo_usuario
        #         st.rerun()
        #     else:
        #         st.error("Senha inválida ou usuário não encontrado!")

    # Botão para recuperar senha
    col2.button("Esqueci a senha", key="forgot_password", type="tertiary", on_click=recuperar_senha_dialog)

    # Informação adicional
    col2.markdown("<div style='color: red;'><br>É o seu primeiro acesso?<br>Clique em \"Esqueci a senha\".</div>", unsafe_allow_html=True)


##############################################################################################################
# EXECUÇÃO PRINCIPAL: VERIFICA LOGIN E NAVEGA ENTRE PÁGINAS
##############################################################################################################

# Se o usuário ainda não estiver logado
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login()  # Mostra tela de login

else:
    # Mostra menu de navegação se estiver logado
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
        "Monitor de Notícias.py", 
        "Manuais.py",
    ])

    # Executa a página selecionada
    pg.run()