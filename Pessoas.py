import streamlit as st
import pandas as pd 
import plotly.express as px
from datetime import datetime
import time
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


# Converter os documentos MongoDB para lista de dicionários
pessoas_lista = []
for pessoa in dados_pessoas:
    pessoas_lista.append({
        "Nome": pessoa.get("nome_completo", ""),
        "Programa/Área": pessoa.get("programa_area", ""),
        "Projeto": pessoa.get("projeto", ""),
        "Setor": pessoa.get("setor", ""),
        "Cargo": pessoa.get("cargo", ""),
        "Escolaridade": pessoa.get("escolaridade", ""),
        "E-mail": pessoa.get("e‑mail", ""),
        "Telefone": pessoa.get("telefone", ""),
        "Gênero": pessoa.get("gênero", ""),
        "Raça": pessoa.get("raça", "")
    })


######################################################################################################
# FUNÇÕES
######################################################################################################


@st.dialog("Cadastrar colaborador(a)", width='large')
def cadastrar_colaborador():
    with st.form("form_cadastro_colaborador", clear_on_submit=True):
        st.write('**Novo(a) colaborador(a):**')

        col1, col2 = st.columns([1,1])

        nome = col1.text_input("Nome completo:")
        genero = col2.selectbox("Gênero:", ["Masculino", "Feminino", "Outro"], index=None, placeholder="")

        col1, col2 = st.columns([1,1])

        cpf = col1.text_input("CPF:", placeholder="000.000.000-00")
        rg = col2.text_input("RG e órgão emissor:")


        col1, col2, col3 = st.columns([1,2,2])

        data_nascimento = col1.text_input("Data de nascimento:", placeholder="dd/mm/aaaa")
        telefone = col2.text_input("Telefone:")
        
        email = col3.text_input("E-mail:")

        col1, col2 = st.columns([1,1])

        email_coord = col1.text_input("Nome do(a) coordenador(a):")
        lista_programas_areas = sorted({pessoa["Programa/Área"] for pessoa in pessoas_lista if pessoa["Programa/Área"]})
        programa_area = col2.selectbox("Programa / Área:", lista_programas_areas, index=None, placeholder="")


        st.markdown("---")

        # Banco
        st.markdown("#### Dados bancários")
        st.write("")

        col1, col2 = st.columns([1,1])

        nome_banco = col1.text_input("Nome do banco:")
        agencia = col2.text_input("Agência:")

        col1, col2 = st.columns([1,1])

        conta = col1.text_input("Conta:")
        tipo_conta = col2.selectbox("Tipo de conta:", ["Conta Corrente", "Conta Poupança", "Conta Salário"], index=None, placeholder="")

        st.markdown("---")

        # Férias
        st.markdown("#### Férias")

        col1, col2 = st.columns([1,2])

        a_receber = col1.number_input("Dias de férias a receber:", step=1, min_value=0)
        residual_ano_anterior = 0
        valor_inicial_ano_atual = 0
        total_gozado = 0
        saldo_atual = residual_ano_anterior + valor_inicial_ano_atual

        st.write("")

        if st.form_submit_button("Cadastrar", type="secondary", icon=":material/person_add:"):
            if not nome or not email or not programa_area:
                st.warning("Preencha os campos obrigatórios: Nome, E-mail e Programa/Área.")
            else:
                ano_atual = str(datetime.now().year)

                novo_documento = {
                    "nome_completo": nome,
                    "CPF": cpf,
                    "RG": rg,
                    "e‑mail": email,
                    "telefone": telefone,
                    "data_nascimento": data_nascimento,
                    "gênero": genero,
                    "senha": "",
                    "tipo de usuário": "",
                    "programa_area": programa_area,
                    "e‑mail_coordenador": email_coord,
                    "status": "ativo",
                    "banco": {
                        "nome_banco": nome_banco,
                        "agencia": agencia,
                        "conta": conta,
                        "tipo_conta": tipo_conta
                    },
                    "férias": {
                        "anos": {
                            ano_atual: {
                                "residual_ano_anterior": residual_ano_anterior,
                                "valor_inicial_ano_atual": valor_inicial_ano_atual,
                                "total_gozado": total_gozado,
                                "saldo_atual": saldo_atual,
                                "solicitacoes": [],
                                "a_receber": a_receber
                            }
                        }
                    }
                }

                # Inserir no MongoDB
                pessoas.insert_one(novo_documento)

                st.success(f"Colaborador(a) **{nome}** cadastrado(a) com sucesso!", icon=":material/thumb_up:")
                time.sleep(2)
                st.rerun()


######################################################################################################
# MAIN
######################################################################################################


# Botão de cadastro de novos colaboradores só para alguns tipos de usuário
tipos_usuario = st.session_state.get("tipo_usuario", [])
if "admin" in tipos_usuario:

    # Botão para abrir o modal de cadastro
    st.button("Cadastrar colaborador(a)", on_click=cadastrar_colaborador, use_container_width=True, icon=":material/person_add:")

# Criar DataFrame
df_pessoas = pd.DataFrame(pessoas_lista)

# Filtros (pode-se popular dinamicamente se quiser)
col1, col2, col3, col4 = st.columns(4)

col1.selectbox("Programa", ["Todos", "Cerrado", "Iniciativas Comunitárias", "Maranhão", "Sociobiodiversidade", "Povos Indígenas"])
col2.selectbox("Setor", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3", "Projeto 4", "Projeto 5"])
col3.selectbox("Doador", ["Todos", "USAID", "GEF", "UE", "Laudes Foundation"])
col4.selectbox("Projeto", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3", "Projeto 4", "Projeto 5"])

# Exibir DataFrame
st.subheader(f'{len(df_pessoas)} colaboradores(as)')
st.write('')
st.dataframe(df_pessoas, hide_index=True)

# Gráficos
col1, col2 = st.columns(2)

# Agrupar e ordenar
programa_counts = df_pessoas['Programa/Área'].value_counts().reset_index()
programa_counts.columns = ['Programa/Área', 'Quantidade']

# Criar gráfico ordenado do maior para o menor
fig = px.bar(
    programa_counts,
    x='Programa/Área',
    y='Quantidade',
    color='Programa/Área',
    title='Distribuição de Pessoas por Programa/Área'
)
col1.plotly_chart(fig)

# Projeto
fig = px.bar(df_pessoas, x='Projeto', color='Projeto', title='Distribuição de Pessoas por Projeto')
col2.plotly_chart(fig)

# Setor
fig = px.pie(df_pessoas, names='Setor', title='Distribuição de Pessoas por Setor')
col1.plotly_chart(fig)

# Cargo
fig = px.pie(df_pessoas, names='Cargo', title='Distribuição de Pessoas por Cargo')
col2.plotly_chart(fig)

# Gênero
fig = px.pie(df_pessoas, names='Gênero', title='Distribuição de Pessoas por Gênero')
col1.plotly_chart(fig)

# Raça
fig = px.pie(df_pessoas, names='Raça', title='Distribuição de Pessoas por Raça')
col2.plotly_chart(fig)

# Escolaridade
fig = px.pie(df_pessoas, names='Escolaridade', title='Distribuição de Pessoas por Escolaridade')
col1.plotly_chart(fig)






