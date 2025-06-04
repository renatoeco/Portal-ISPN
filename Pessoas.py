import streamlit as st
import pandas as pd 
import streamlit_shadcn_ui as ui
import plotly.express as px
from funcoes_auxiliares import conectar_mongo_portal_ispn


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Pessoas")
st.write('')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"] 
pessoas = db["pessoas"]  

# Obter dados da coleção "pessoas"
dados_pessoas = list(pessoas.find())

######################################################################################################
# FUNÇÕES
######################################################################################################


# Função para cadastrar colaborador
@st.dialog("Cadastrar colaborador(a)", width='medium')
def cadastrar_colaborador():
    with st.form("Cadastrar colaborador(a)", clear_on_submit=True):  # Formulário com limpeza ao enviar
        st.write('**Novo(a) colaborador(a):**')  # Texto explicativo

        # Campo de texto para o nome do novo colaborador
        novo_nome = st.text_input("Nome:", key="novo_nome")  

        # Selectbox para escolher o programa ou setor
        novo_setor = st.selectbox(
            "Programa / Área:",
            lista_programas_areas,
            index=None,
            placeholder="Selecione...",
        )

        # Campo de texto para o e-mail do novo colaborador
        novo_email = st.text_input("E-mail:", key="novo_email")  

        # Campo para inserir quantos dias receberá na virada do ano
        a_receber = st.number_input(  
            "Quantos dias de férias receberá na virada do ano?:", 
            key="a_receber", 
            format="%d", 
            step=1, 
            min_value=0  # Não permite valores negativos
        )

        saldo_inicial = 0  
        # # Campo para inserir o saldo inicial em dias
        # saldo_inicial = st.number_input(  
        #     "Saldo inicial (dias):", 
        #     key="saldo_inicial", 
        #     format="%d", 
        #     step=1, 
        #     min_value=0  # Não permite valores negativos
        # )

        residual_ano_anterior = 0
        # # Campo para inserir o residual do ano anterior
        # residual_ano_anterior = st.number_input(  
        #     "Residual do ano anterior (dias):", 
        #     key="residual_ano_anterior", 
        #     format="%d", 
        #     step=1,
        #     value=0, 
        #     min_value=0  # Não permite valores negativos
        # )

        # Botão de submissão do formulário
        if st.form_submit_button('Cadastrar', type="primary", icon=":material/person_add:"):  # Se o botão for clicado:
            # Verifica se o nome foi preenchido
            if not novo_nome:
                st.warning("Insira o nome.")  # Mostra uma mensagem de alerta se o nome estiver vazio

            # Verifica se o setor foi preenchido
            elif not novo_setor:
                st.warning("Selecione o programa ou setor.")  # Mostra uma mensagem de alerta se o setor estiver vazio

            # Verifica se o email foi preenchido
            elif not novo_email:
                st.warning("Insira o e-mail.")  # Mostra uma mensagem de alerta se o nome estiver vazio

            # Verifica se a receber foi preenchido
            elif a_receber == 0:
                st.warning("Insira um valor a receber maior que zero.")  # Mostra alerta para saldo zero
    
            else:
                # Define o ano atual
                ano_atual = str(datetime.now().year)  # Obtém o ano atual como string
        
                # Cria o novo documento com a estrutura especificada
                novo_colaborador = {
                    novo_nome: {
                        "email": novo_email,
                        "setor": novo_setor,
                        "anos": {  # Adiciona a chave 'anos' que contém o ano atual
                            ano_atual: {
                                "residual_ano_anterior": residual_ano_anterior,  # Residual do ano anterior
                                "valor_inicial_ano_atual": saldo_inicial,  # Saldo inicial do ano atual
                                "total_gozado": 0,  # Total de férias gozadas
                                "saldo_atual": residual_ano_anterior + saldo_inicial,  # Saldo atual de férias
                                "a_receber": a_receber
                            }
                        }
                    }
                }

                # Insere o novo colaborador na coleção MongoDB
                colecao.insert_one(novo_colaborador) 

                # Exibe uma mensagem de confirmação
                st.success(f'Colaborador(a) cadastrado(a) com sucesso: **{novo_nome}**', icon=":material/thumb_up:")

                # Pausa por 3 segundos e recarrega a página
                time.sleep(3)  # Aguarda 3 segundos
                st.rerun()  # Recarrega a aplicação para atualizar os dados

# Botão para abrir o modal de cadastro
st.button("Cadastrar colaborador(a)", on_click=cadastrar_colaborador, use_container_width=True, icon=":material/person_add:")



























# Converter os documentos MongoDB para lista de dicionários
pessoas_lista = []
for pessoa in dados_pessoas:
    pessoas_lista.append({
        "Nome": pessoa.get("nome_completo", "Não informado"),
        "Programa": pessoa.get("programa", "Não informado"),
        "Projeto": pessoa.get("projeto", "Não informado"),
        "Setor": pessoa.get("programa_area", "Não informado"),
        "Cargo": pessoa.get("cargo", "Não informado"),
        "Escolaridade": pessoa.get("escolaridade", "Não informado"),
        "E-mail": pessoa.get("email", "Não informado"),
        "Telefone": pessoa.get("telefone", "Não informado"),
        "Gênero": pessoa.get("gênero", "Não informado"),
        "Raça": pessoa.get("raça", "Não informado")
    })

# Criar DataFrame
pessoas = pd.DataFrame(pessoas_lista)

# Filtros (pode-se popular dinamicamente se quiser)
col1, col2, col3, col4 = st.columns(4)

col1.selectbox("Programa", ["Todos", "Cerrado", "Iniciativas Comunitárias", "Maranhão", "Sociobiodiversidade", "Povos Indígenas"])
col2.selectbox("Setor", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3", "Projeto 4", "Projeto 5"])
col3.selectbox("Doador", ["Todos", "USAID", "GEF", "UE", "Laudes Foundation"])
col4.selectbox("Projeto", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3", "Projeto 4", "Projeto 5"])

# Exibir DataFrame
st.subheader(f'{len(pessoas)} colaboradores(as)')
st.write('')
st.dataframe(pessoas, hide_index=True)

# Gráficos
col1, col2 = st.columns(2)

# Programa
fig = px.bar(pessoas, x='Programa', color='Programa', title='Distribuição de Pessoas por Programa')
col1.plotly_chart(fig)

# Projeto
fig = px.bar(pessoas, x='Projeto', color='Programa', title='Distribuição de Pessoas por Projeto')
col2.plotly_chart(fig)

# Setor
fig = px.pie(pessoas, names='Setor', title='Distribuição de Pessoas por Setor')
col1.plotly_chart(fig)

# Cargo
fig = px.pie(pessoas, names='Cargo', title='Distribuição de Pessoas por Cargo')
col2.plotly_chart(fig)

# Gênero
fig = px.pie(pessoas, names='Gênero', title='Distribuição de Pessoas por Gênero')
col1.plotly_chart(fig)

# Raça
fig = px.pie(pessoas, names='Raça', title='Distribuição de Pessoas por Raça')
col2.plotly_chart(fig)

# Escolaridade
fig = px.pie(pessoas, names='Escolaridade', title='Distribuição de Pessoas por Escolaridade')
col1.plotly_chart(fig)






