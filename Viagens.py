import streamlit as st
import pandas as pd 
from funcoes_auxiliares import conectar_mongo_portal_ispn
from bson import ObjectId
from pymongo import MongoClient
from datetime import date, datetime
import re
import time
from urllib.parse import quote
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials


# ##################################################################
# CONFIGURAÇÕES DA INTERFACE
# ##################################################################


# st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Solicitações de Viagens e Relatórios")
st.write('')





# ##################################################################
# CONEXÃO COM O BANCO DE DADOS MONGO
# ##################################################################


# BANCO DE DADOS ISPN HUB / PORTAL / GESTÃO -----------------

db = conectar_mongo_portal_ispn()
pessoas = db["pessoas"]
estatistica = db["estatistica"]

# BANCO DE DADOS ISPN VIAGENS -----------------

@st.cache_resource
def get_mongo_client():
    MONGODB_URI = st.secrets['senhas']['senha_mongo_portal_viagens']
    return MongoClient(MONGODB_URI)

cliente = get_mongo_client()
banco_de_dados = cliente["plataforma_sav"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_viagens"
nome_pagina = "Viagens"

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


# ##################################################################
# CONEXÃO COM GOOGLE SHEETS
# ##################################################################

# Escopo necessário para acessar os dados do Google Sheets
scope = [
    "https://www.googleapis.com/auth/spreadsheets"
]

# Autenticação usando a conta de serviço

# Ler credenciais do st.secrets
creds_dict = st.secrets["credentials_drive"]
# Criar credenciais do Google usando os dados do st.secrets
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)

client = gspread.authorize(creds)

# ID da planilha
sheet_id = st.secrets.ids.id_planilha_recebimento_viagens



# ##################################################################
# FUNÇÕES AUXILIARES
# ##################################################################

# Faz o encode de valores para URL, pra usar em URL dinâmicas
def encode_params(params):
    return "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())


# Tratamento quando não há todos os dados da pessoa no BD
def safe_get(dicionario, chave, default=""):
    # Obtém o valor da chave no dicionário, ou um valor padrão se a chave não existir
    valor = dicionario.get(chave, default)
    
    # Verifica se o valor é NaN (Not a Number) usando pandas.isna()
    # Se for NaN, retorna uma string vazia
    # Caso contrário, retorna o valor normalmente
    return "" if pd.isna(valor) else valor


# Função para transformar o itinerário em uma lista de dicionários
def parse_itinerario(itinerario_texto):

    viagens = []
    
    # Quebrar o texto pela quebra de linha
    trechos = itinerario_texto.splitlines()


    for trecho in trechos:
        partes = trecho.split(", ")  # Separar cada informação pelo padrão ", "
        viagem = {}

        for parte in partes:
            chave_valor = parte.split(": ", 1)  # Divide apenas na primeira ocorrência de ": "
            if len(chave_valor) == 2:
                chave, valor = chave_valor
                viagem[chave.strip()] = valor.strip()  # Adiciona ao dicionário

        viagens.append(viagem)

    return viagens

# Função para transformar as diarias em uma lista de dicionários
def parse_diarias(diarias_texto):
    diarias = []

    # Quebrar o texto pela quebra de linha
    linhas = diarias_texto.splitlines()

    for linha in linhas:
        partes = linha.split(", ")  # Separar cada informação pelo padrão ", "
        diaria = {}

        for parte in partes:
            chave_valor = parte.split(": ", 1)  # Divide apenas na primeira ocorrência de ": "
            if len(chave_valor) == 2:
                chave, valor = chave_valor
                diaria[chave.strip()] = valor.strip()  # Adiciona ao dicionário

        diarias.append(diaria)

    return diarias


# Busca os dados do usuário no banco de dados de pessoas
def get_usuario_normalizado(pessoas, id_usuario) -> dict:
    """
    Busca o usuário no Mongo e normaliza os campos para uso no app.
    """
    # Se for string, converte. Se já for ObjectId, usa direto.
    if isinstance(id_usuario, str):
        id_usuario = ObjectId(id_usuario.strip("ObjectId()' "))

    usuario_doc = pessoas.find_one({"_id": id_usuario})

    if not usuario_doc:
        return {}

    usuario = {
        "nome_completo": usuario_doc.get("nome_completo"),
        "cpf": usuario_doc.get("CPF"),
        "rg": usuario_doc.get("RG"),
        "telefone": usuario_doc.get("telefone"),
        "data_nascimento": usuario_doc.get("data_nascimento"),
        "genero": usuario_doc.get("gênero"),
        "email": usuario_doc.get("e_mail"),
        "email_coordenador": None,  # pode buscar depois
        "banco": {
            "nome": usuario_doc.get("banco", {}).get("nome_banco"),
            "agencia": usuario_doc.get("banco", {}).get("agencia"),
            "conta": usuario_doc.get("banco", {}).get("conta"),
            "tipo": usuario_doc.get("banco", {}).get("tipo_conta"),
        }
    }

    return usuario




# Função para mostrar os detalhes da SAV no diálogo
@st.dialog("Detalhes da Viagem", width='large')
def mostrar_detalhes_sav(row):

    # Aumentar largura do diálogo com css
    st.html("<span class='big-dialog'></span>")

    # TRATAMENTO DO ITINERÁRIO
    # Transformar o itinerário em uma lista de dicionários
    viagens = parse_itinerario(row["Itinerário:"])
    # Criar um DataFrame a partir do dicionário
    df_trechos = pd.DataFrame(viagens)
    # Substituir os campos com None por ""
    df_trechos.fillna("", inplace=True)
    # Renomear colunas
    df_trechos.rename(columns={"Tipo de transporte": "Transporte", "Horário de preferência": "Horário"}, inplace=True)

    # TRATAMENTO DAS DIÁRIAS
    # Transformar as diárias em uma lista de dicionários
    diarias = parse_diarias(row["Diárias"])
    # Criar um DataFrame a partir da lista de dicionários
    df_diarias = pd.DataFrame(diarias)
    # Substituir os campos com None por ""
    df_diarias.fillna("", inplace=True)

    # TRATAMENTO DO LINK DE EDIÇÃO
    sumbission_id = row["Submission ID"]

    # usuario = st.session_state.usuario

    link_edicao = f"https://www.jotform.com/edit/{sumbission_id}"

    col1, col2, col3 = st.columns([1, 1, 1])

    col3.link_button("Editar a Solicitação", icon=":material/edit:", url=link_edicao)


    # INFORMAÇÕES
    # Se a SAV for para terceiros, mostra o nome do viajante
    if row["Código da viagem:"].startswith("TRC"):
        st.write(f"**Nome do(a) viajante:** {row['Nome do(a) viajante:']}")
    st.write(f"**Código da viagem:** {row['Código da viagem:']}")
    st.write(f"**Data da solicitação:** {row['Submission Date']}")
    st.write(f"**Objetivo:** {row['Descrição do objetivo da viagem:']}")
    st.write(f"**Fonte de recurso:** {row['Qual é a fonte do recurso?']}")

    # Exibir os detalhes do itinerário como tabela
    st.write("**Itinerário:**")
    st.dataframe(df_trechos, hide_index=True)

    # Exibir os detalhes das diárias como tabela
    st.write("**Diárias:**")
    st.dataframe(df_diarias,  hide_index=True)

    st.write(f"**Custo pago pelo anfitrião:** {row['A viagem tem algum custo pago pelo anfitrião?']}")

    st.write(f"**Será necessário um veículo?** {row['Será necessário locação de veículo?']}")

    # Se for necessário um veículo, mostra o container do veículo

    if row.get('Será necessário locação de veículo?') == 'Sim':
        
        # Container para botar uma borda em torno das informações do veículo alugado ou do ISPN
        veiculo = st.container(border=True)

        if row.get('Um veículo alugado ou um veículo do ISPN em Santa Inês?'):
            veiculo.write(row['Um veículo alugado ou um veículo do ISPN em Santa Inês?'])

        # VEÍCULO ALUGADO
        if row.get('Descreva o tipo de veículo desejado:'):
            veiculo.write(row['Descreva o tipo de veículo desejado:'])

        if row.get('Detalhe os locais e horários de retirada e retorno do veículo alugado:'):
            veiculo.write(row['Detalhe os locais e horários de retirada e retorno do veículo alugado:'])

        # VEÍCULO DO ISPN
        if row.get('Escolha o veículo:'):
            veiculo.write(row['Escolha o veículo:'])

        if row.get('Quais são os horários previstos de retirada e retorno do veículo?'):
            veiculo.write(row['Quais são os horários previstos de retirada e retorno do veículo?'])

    # OBSERVAÇÕES
    st.write(f"**Observações:** {row['Observações gerais:']}")

    st.write('')



@st.dialog("Detalhes do Relatório", width='large')
def mostrar_detalhes_rvs(row, df_rvss):

    # Aumentar largura do diálogo com css
    st.html("<span class='big-dialog'></span>")

    # Selecionando o relatório a partir do código da SAV
    relatorio = df_rvss[df_rvss["Código da viagem:"].str.upper() == row["Código da viagem:"].upper()].iloc[0]

    # TRATAMENTO DO LINK DE EDIÇÃO
    sumbission_id = relatorio["Submission ID"]
    link_edicao = f"https://www.jotform.com/edit/{sumbission_id}"


    # Botão para editar o relatório
    col1, col2, col3 = st.columns([1, 1, 1])
    col3.link_button("Editar o Relatório", icon=":material/edit:", url=link_edicao)

    # INFORMAÇÕES
    if row["Código da viagem:"].startswith("TRC"):
        st.write(f"**Nome do(a) viajante:** {row['Nome do(a) viajante:']}")
    st.write(f"**Código da viagem:** {row['Código da viagem:']}")   # Pega o código direto da SAV
    st.write(f"**Data do envio do relatório:** {relatorio['Submission Date']}")
    st.write(f"**Fonte de recurso:** {relatorio['Qual é a fonte do recurso?']}")
    st.write(f"**Período da viagem:** {relatorio['Período da viagem:']}")
    st.write(f"**Cidade(s) de destino:** {relatorio['Cidade(s) de destino:']}")

        
    try: # Não tem no relatório de terceiros.
        st.write(f"**Modalidade:** {relatorio['Modalidade:']}")
    except:
        pass

    try: # Não tem no relatório de terceiros.
        st.write(f"**Modo de transporte até o destino:** {relatorio['Modo de transporte até o destino:']}")
    except:
        pass

    try: # Não tem no relatório de terceiros.
        st.write(f"**Despesas cobertas pelo anfitrião (descrição e valor):** {relatorio['Despesas cobertas pelo anfitrião (descrição e valor):']}")
    except:
        pass

    st.write(f"**Número de pernoites:** {relatorio['Número de pernoites:']}")
    st.write(f"**Valor das diárias recebidas:** {relatorio['Valor das diárias recebidas (R$):']}")
    st.write(f"**Valor gasto com transporte no destino:** {relatorio['Valor gasto com transporte no destino (R$):']}")
    st.write(f"**Atividades realizadas na viagem:** {relatorio['Descreva as atividades realizadas na viagem:']}")
    st.write(f"**Principais Resultados / Produtos:** {relatorio['Principais Resultados / Produtos:']}")

    # Fotos
    st.write("**Fotos da viagem:**")
    # Convertendo a string em uma lista de URLs
    lista_fotos = relatorio['Inclua 2 fotos da viagem:'].split("\n")
    # Criando colunas dinamicamente com base na quantidade de fotos
    num_fotos = len(lista_fotos)
    cols = st.columns(num_fotos)  # Cria colunas iguais ao número de fotos
    # Exibindo cada foto em uma coluna
    for idx, (col, foto) in enumerate(zip(cols, lista_fotos), start=1):
        with col:
            st.image(foto)

    # Anexos
    st.write("**Documentos anexados:**")
    # Fazendo o split nas quebras de linha
    url_list = relatorio['Faça upload dos anexos:'].split("\n")
    for url in reversed(url_list):
        # Obtém o nome do arquivo
        nome_arquivo = url.split("/")[-1]  
        # Mostra o link na página
        st.markdown(f'<a href="{url}" target="_blank">{nome_arquivo}</a><br>', unsafe_allow_html=True)
       
    st.write(f"**Observações:** {relatorio['Observações gerais:']}")

    st.write('')



# Carregar usuários internos no banco de dados ------------------------------
def carregar_internos():
    
    # criar um dataframe com os usuários internos
    df_usuarios_internos = pd.DataFrame(list(banco_de_dados["usuarios_internos"].find()))
    
    # Considerar apenas os números da coluna cpf
    df_usuarios_internos["cpf"] = df_usuarios_internos["cpf"].astype(str).str.replace(r"\D", "", regex=True)

    return df_usuarios_internos



# Cerregar usuários externos no banco de dados ------------------------------
def carregar_externos():
    # criar um dataframe com os usuários externos
    df_usuarios_externos = pd.DataFrame(list(banco_de_dados["usuarios_externos"].find()))
    
    # Considerar apenas os números da coluna cpf
    df_usuarios_externos["cpf"] = df_usuarios_externos["cpf"].astype(str).str.replace(r"\D", "", regex=True)

    return df_usuarios_externos



# Carregar SAVs internas no google sheets ------------------------------
def carregar_savs_int():

    sheet = client.open_by_key(sheet_id)
    
    values_savs = sheet.worksheet("SAVs INTERNAS Portal").get_all_values()

    # Criar DataFrame de SAVs. A primeira linha é usada como cabeçalho
    df_savs = pd.DataFrame(values_savs[1:], columns=values_savs[0])

    # Converter as colunas de data para datetime
    df_savs["Submission Date"] = pd.to_datetime(df_savs["Submission Date"])  # Garantir que é datetime
    df_savs["Submission Date"] = df_savs["Submission Date"].dt.strftime("%d/%m/%Y")  # Converter para string no formato brasileiro

    # Filtar SAVs com o prefixo "SAV-"
    df_savs = df_savs[df_savs['Código da viagem:'].str.upper().str.startswith('SAV-')]

    df_savs = df_savs.replace({r'\$': r'\$'}, regex=True)

    return df_savs



# Carregar RVSs internos no google sheets ------------------------------
def carregar_rvss_int():

    sheet = client.open_by_key(sheet_id)

    # Planilha de recebimento de RVSs internos
    values_rvss = sheet.worksheet("RVSs INTERNOS Portal").get_all_values()

    # Criar DataFrame de RVSs. A primeira linha é usada como cabeçalho
    df_rvss = pd.DataFrame(values_rvss[1:], columns=values_rvss[0])

    # Filtar SAVs com o prefixo "SAV-"
    df_rvss = df_rvss[df_rvss['Código da viagem:'].str.upper().str.startswith('SAV-')]

    # Converter as colunas de data para datetime
    df_rvss["Submission Date"] = pd.to_datetime(df_rvss["Submission Date"])  # Garantir que é datetime
    df_rvss["Submission Date"] = df_rvss["Submission Date"].dt.strftime("%d/%m/%Y")  # Converter para string no formato brasileiro

    df_rvss = df_rvss.replace({r'\$': r'\$'}, regex=True)

    return df_rvss



# Carregar SAVs externas no google sheets ------------------------------
# def carregar_savs_ext():

#     # Abrir a planilha de SAVs externas
#     sheet = client.open_by_key(sheet_id)

#     # Ler todos os valores da planilha
#     values_savs = sheet.worksheet("SAVs EXTERNAS Portal").get_all_values()

#     # Criar DataFrame de SAVs. A primeira linha é usada como cabeçalho
#     df_savs = pd.DataFrame(values_savs[1:], columns=values_savs[0])

#     # Converter as colunas de data para datetime
#     df_savs["Submission Date"] = pd.to_datetime(df_savs["Submission Date"])  # Garantir que é datetime
#     df_savs["Submission Date"] = df_savs["Submission Date"].dt.strftime("%d/%m/%Y")  # Converter para string no formato brasileiro

#     # Filtar SAVs com o prefixo "EXT-"
#     df_savs = df_savs[df_savs['Código da viagem:'].str.upper().str.startswith('EXT-')]
   
#     # Substitui o caractere $ por \$ para que o Streamlit possa exibir corretamente
#     df_savs = df_savs.replace({'\$': '\\$'}, regex=True)

#     # Renomeia as colunas para que tenham nomes mais legíveis
#     df_savs.rename(columns={'Insira aqui os seus deslocamentos. Cada trecho em uma nova linha:': 'Itinerário:',
#                             'Nome do ponto focal no ISPN (a pessoa que está convidando)': 'Ponto focal:'}, inplace=True)

#     return df_savs


# # Carregar RVSs externos no google sheets ------------------------------
# # @st.cache_data(show_spinner=False)
# def carregar_rvss_ext():

#     # Abrir a planilha de RVSs externas
#     sheet = client.open_by_key(sheet_id)

#     # Ler todos os valores da planilha
#     # values_rvss = sheet.worksheet("TESTE RENATO SAVs").get_all_values()
#     values_rvss = sheet.worksheet("RVSs EXTERNOS Portal").get_all_values()

#     # Criar DataFrame de RVSs. A primeira linha é usada como cabeçalho
#     df_rvss = pd.DataFrame(values_rvss[1:], columns=values_rvss[0])

#     # Filtar SAVs com o prefixo "EXT-"
#     df_rvss = df_rvss[df_rvss['Código da viagem:'].str.upper().str.startswith('EXT-')]

#     # Converter as colunas de data para datetime
#     df_rvss["Submission Date"] = pd.to_datetime(df_rvss["Submission Date"])  # Garantir que é datetime
#     df_rvss["Submission Date"] = df_rvss["Submission Date"].dt.strftime("%d/%m/%Y")  # Converter para string no formato brasileiro

#     df_rvss = df_rvss.replace({'\$': '\\$'}, regex=True)

#     return df_rvss


# Carregar SAVs de terceiros no google sheets ------------------------------
# @st.cache_data(show_spinner=False)
def carregar_savs_trc():

    # Abrir a planilha de SAVs de terceiros
    sheet = client.open_by_key(sheet_id)

    # Ler todos os valores da planilha
    values_savs = sheet.worksheet("SAVs TERCEIROS Portal").get_all_values()

    # Criar DataFrame de SAVs. A primeira linha é usada como cabeçalho
    df_savs = pd.DataFrame(values_savs[1:], columns=values_savs[0])

    # Converter as colunas de data para datetime
    df_savs["Submission Date"] = pd.to_datetime(df_savs["Submission Date"])  # Garantir que é datetime
    df_savs["Submission Date"] = df_savs["Submission Date"].dt.strftime("%d/%m/%Y")  # Converter para string no formato brasileiro

    # Filtar SAVs com o prefixo "TRC-"
    df_savs = df_savs[df_savs['Código da viagem:'].str.upper().str.startswith('TRC-')]
   
    # Substitui o caractere $ por \$ para que o Streamlit possa exibir corretamente
    df_savs = df_savs.replace({r'\$': r'\$'}, regex=True)

    # Renomeia as colunas para que tenham nomes mais legíveis
    df_savs.rename(columns={'Insira aqui os deslocamentos considerando IDA e VOLTA. Cada trecho em uma nova linha:': 'Itinerário:'}, inplace=True)

    return df_savs


# Carregar RVSs externos no google sheets ------------------------------
# @st.cache_data(show_spinner=False)
def carregar_rvss_trc():

    # Abrir a planilha de RVSs externas
    sheet = client.open_by_key(sheet_id)

    # Ler todos os valores da planilha
    # values_rvss = sheet.worksheet("TESTE RENATO SAVs").get_all_values()
    values_rvss = sheet.worksheet("RVSs TERCEIROS Portal").get_all_values()

    # Criar DataFrame de RVSs. A primeira linha é usada como cabeçalho
    df_rvss_terceiros = pd.DataFrame(values_rvss[1:], columns=values_rvss[0])

    # Filtar SAVs com o prefixo "TRC-"
    df_rvss_terceiros = df_rvss_terceiros[df_rvss_terceiros['Código da viagem:'].str.upper().str.startswith('TRC-')]

    # Converter as colunas de data para datetime
    df_rvss_terceiros["Submission Date"] = pd.to_datetime(df_rvss_terceiros["Submission Date"])  # Garantir que é datetime
    df_rvss_terceiros["Submission Date"] = df_rvss_terceiros["Submission Date"].dt.strftime("%d/%m/%Y")  # Converter para string no formato brasileiro

    # df_rvss_terceiros = df_rvss_terceiros.replace({'\$': '\\$'}, regex=True)
    df_rvss_terceiros = df_rvss_terceiros.replace({r'\$': r'\$'}, regex=True)


    return df_rvss_terceiros




@st.dialog("Cadastrar viajante externo", width="large")
def cadastrar_externo():
    with st.form("cadastrar_externo"):
        # Criação de duas colunas para organização dos campos no formulário
        col1, espaco, col2 = st.columns([12, 1, 12])

        # COLUNA 1

        # Campo para o nome completo
        nome_input = col1.text_input("Nome Completo")

        # Campo para o CPF
        cpf_input = col1.text_input("CPF")

        # Campo para a data de nascimento
        data_nascimento_input = col1.date_input("Data de Nascimento", value=None, format="DD/MM/YYYY")
        # Converte para string somente se tiver valor
        if data_nascimento_input:
            data_nascimento_str = data_nascimento_input.strftime("%d/%m/%Y")
        else:
            data_nascimento_str = ""
        # Campo para e-mail
        email_input = col1.text_input("E-mail")

        # COLUNA 2

        # Campo para seleção de gênero
        genero_input = col2.selectbox(
            "Gênero",
            ["", "Masculino", "Feminino", "Outro"],
        )

        # Campo para o RG e órgão emissor
        rg_input = col2.text_input("RG e órgão emissor")

        # Campo para o telefone
        telefone_input = col2.text_input("Telefone")

        # Espaço para alinhamento visual com os demais campos
        col2.markdown("<div style='height: 84px'></div>", unsafe_allow_html=True)

        # DADOS BANCÁRIOS

        # Campo para o nome do banco
        banco_nome_input = col1.text_input("Banco", value="")

        # Campo para o número da agência
        banco_agencia_input = col2.text_input("Agência", value="")

        # Campo para o número da conta
        banco_conta_input = col2.text_input("Número da conta", value="")

        # Campo para o tipo de conta
        banco_tipo_input = col1.selectbox(
            "Tipo de Conta",
            [""] + ["Conta Corrente", "Conta Poupança", "Conta Salário"],  # opção vazia no início
            index=0  # seleciona a opção vazia por padrão
        )

        st.write('')


        if st.form_submit_button("Cadastrar viajante externo", icon=":material/person_add:", type="primary"):
            # Verifica se há erros nos campos
            erros = []

            # Verifica se o nome completo foi preenchido
            if not nome_input:
                erros.append("Nome completo é obrigatório.")

            # Verifica se o CPF foi preenchido
            if not cpf_input:
                erros.append("CPF é obrigatório.")

            # Verifica se a data de nascimento está no formato correto
            if not re.match(r"^\d{2}/\d{2}/\d{4}$", data_nascimento_str):
                erros.append("Data de nascimento inválida. Use o formato DD/MM/AAAA.")

            # Verifica se o e-mail é válido
            if not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email_input):
                erros.append("E-mail inválido.")

            # Verifica se o gênero foi selecionado
            if genero_input == "":
                erros.append("Gênero é obrigatório.")

            # Verifica se o RG foi preenchido
            if not rg_input:
                erros.append("RG é obrigatório.")

            # Verifica se o telefone tem o tamanho correto
            if len(telefone_input) < 10 or len(telefone_input) > 11:
                erros.append("Telefone inválido. Use DDD + número.")

            # Verifica se todos os campos bancários foram preenchidos
            if not banco_nome_input or not banco_agencia_input or not banco_conta_input:
                erros.append("Todos os campos bancários devem ser preenchidos.")

            # Se houver erros, exibe-os
            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                # Se não houver erros, grava os dados no banco de dados
                atualizacoes = {
                    "nome_completo": nome_input,
                    "cpf": cpf_input,
                    "email": email_input,
                    "data_nascimento": data_nascimento_str,
                    "genero": genero_input,
                    "rg": rg_input,
                    "telefone": telefone_input,
                    "banco": {
                        "nome": banco_nome_input,
                        "agencia": banco_agencia_input,
                        "conta": banco_conta_input,
                        "tipo": banco_tipo_input,
                    }
                }
                # Insere o novo usuário no banco de dados
                banco_de_dados["usuarios_externos"].insert_one(atualizacoes)
                # Exibe uma mensagem de sucesso
                st.success(":material/check: Viajante cadastrado com sucesso!")
                # Aguarda 3 segundos antes de atualizar a página
                time.sleep(3)
                # Atualiza a página
                st.rerun()



# Usuário interno: 
# carrega SAVs e RVSs internas
df_savs = carregar_savs_int()
df_rvss = carregar_rvss_int()

# carrega SAVs e RVSs de terceiros
df_savs_terceiros = carregar_savs_trc()
df_rvss_terceiros = carregar_rvss_trc()


linha_botoes = st.container(horizontal=True, horizontal_alignment="right")

# Botão para atualizar a página
if linha_botoes.button("Atualizar página", icon=":material/refresh:", width=200):
    # Limpa o session_state e o cache, e recarrega a página
    st.session_state.status_usuario = ""
    st.cache_data.clear()
    st.rerun()  
    
    
st.write("")

# Abas da home
minhas_viagens, nova_sav, terceiros = st.tabs([":material/flight_takeoff: Minhas Viagens", ":material/add: Nova Solicitação de Viagem", ":material/group: Solicitações para Terceiros"])


# ABA MINHAS VIAGENS

with minhas_viagens:

    # TRATAMENTO DO df_savs  ---------------------------------

    # Limpar a coluna CPF: quero apenas os números
    df_savs['CPF:'] = df_savs['CPF:'].str.replace(r'[^\d]+', '', regex=True)

    # Filtar SAVs com o CPF do usuário
    # df_savs = df_savs[df_savs['CPF:'].astype(str) == str(usuario['cpf'])]
    df_savs = df_savs[df_savs['CPF:'].astype(str) == st.session_state.cpf]

    # Capturar a data da viagem
    df_savs['Data da viagem:'] = df_savs['Itinerário:'].str[6:16].replace('-', '/', regex=True)

    destinos = r'Cidade de chegada: (.*?)(?:,|$)'
    
    # Aplicar a regex para cada linha da coluna
    df_savs["Destinos:"] = df_savs["Itinerário:"].apply(lambda x: ' > '.join(re.findall(destinos, x)))

    # -------------------------------------


    # Criar cabeçalho da "tabela"
    col1, col2, col3, col4, col5 = st.columns([2, 2, 7, 3, 3])

    col1.write('**Código da viagem**')
    col2.write('**Data da viagem**')
    col3.write('**Itinerário**')
    col4.write('**Solicitações**')
    col5.write('**Relatórios**')

    # Iniciar a variável na session_state que vai identificar se o usuário está impedido ou não de enviar relatório (se tem algum pendente)
    st.session_state.status_usuario = ""

    # Iterar sobre a lista de viagens
    for index, row in df_savs[::-1].iterrows():

        # Preparar o link personalizado para o relatório -----------------------------------------------------

        # Extrair cidade(s) de destino
        # Transformar o itinerário em uma lista de dicionários
        trechos = parse_itinerario(row["Itinerário:"])

        # Pegando a primeira e a última data
        data_inicial = trechos[0]["Data"]
        data_final = trechos[-1]["Data"]

        # Formata a data do período da viagem para o formato DD/MM/YYYY a DD/MM/YYYY
        periodo_viagem = f"{data_inicial} a {data_final}".replace('-', '/')

        # Extraindo todas as "Cidade de chegada" e concatenando com vírgula
        cidades_chegada = [viagem["Cidade de chegada"] for viagem in trechos]
        
        destinos = ", ".join(cidades_chegada)


        # Prepara as URLs de formulários com alguns campos pré-preenchidos
        # URL do formulário de RVS interno
        params = {
            "codigoDa": row["Código da viagem:"],
            "qualE": row["Qual é a fonte do recurso?"],
            "nomeDo": row["Nome completo:"],
            "email": row["E-mail:"],
            "cidadesDe": destinos,
            "periodoDa": periodo_viagem
        }

        jotform_rvs_url = f"{st.secrets['links']['url_rvs_int']}?{encode_params(params)}"



        # ----------------------------------------------------------------------------------------------------- 

        # Conteúdo da lista de viagens

        col1, col2, col3, col4, col5 = st.columns([2, 2, 7, 3, 3])
        
        col1.write(row['Código da viagem:'])
        col2.write(row['Data da viagem:'])
        col3.write(row['Destinos:'])
        col4.button('Detalhes', key=f"detalhes_{index}", on_click=mostrar_detalhes_sav, args=(row,), width="stretch", icon=":material/info:")
        

        # Botão dinâmico sobre o relatório --------------------------------------------

        # Verificar se o relatório foi entregue. Procura se tem o código da SAV em algum relatório 
        if row['Código da viagem:'].upper() in df_rvss['Código da viagem:'].str.upper().values:
            status_relatorio = "entregue"

        # Se não tem nenhum relatório com esse código de SAV
        else:
            status_relatorio = "pendente"

            # Se a data_final da viagem menor do que hoje, o usuário está impedido
            if pd.to_datetime(data_final, dayfirst=True).timestamp() < pd.to_datetime(date.today()).timestamp():
            
                # Impede o usuário de enviar uma nova solicitação se tiver relatório pendente
                st.session_state.status_usuario = "impedido"
                
        # Se o relatório foi entregue, vê o relatório  
        if status_relatorio == "entregue":
            col5.button('Relatório entregue', key=f"entregue_{index}", on_click=mostrar_detalhes_rvs, args=(row, df_rvss), width="stretch", icon=":material/check:", type="primary")
        
        # Se não foi entregue, botão para enviar
        if status_relatorio == "pendente":
            # Se não foi entregue, botão para enviar
            col5.link_button('Enviar relatório', width="stretch", icon=":material/description:", url=jotform_rvs_url)

        st.divider()  # Separador entre cada linha da tabela



# ABA DE NOVA SOLICITAÇÃO

with nova_sav:

    # Verifica se o usuário está impedido de enviar uma nova solicitação
    if st.session_state.status_usuario == "impedido":
        st.write('')
        st.write('')
        st.write('')

        # Exibe um aviso de impedimento
        st.markdown("""
            <div style="text-align: center;">
                <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded" rel="stylesheet">
                <span class="material-symbols-rounded" style="font-size:58px; color:red;">
                    warning
                </span>
            </div>
        """, unsafe_allow_html=True)

        st.write('')

        st.markdown("<div style='text-align: center; color: red; font-size: 20px;'>Você precisa enviar os <strong>relatórios pendentes</strong> antes de solicitar uma nova viagem.</div>", unsafe_allow_html=True)

    # Usuário não está impedido
    else:

        id_usuario = st.session_state.get("id_usuario")

        if id_usuario:
            usuario = get_usuario_normalizado(pessoas, id_usuario)

            banco_info = safe_get(usuario, 'banco', {}) if isinstance(usuario.get('banco'), dict) else {}

            jotform_sav_url = (
                f"{st.secrets['links']['url_sav_int']}?"
                f"nomeCompleto={safe_get(usuario, 'nome_completo')}&"
                f"dataDe={safe_get(usuario, 'data_nascimento')}&"
                f"genero={safe_get(usuario, 'genero')}&"
                f"rg={safe_get(usuario, 'rg')}&"
                f"cpf={safe_get(usuario, 'cpf')}&"
                f"telefone={safe_get(usuario, 'telefone')}&"
                f"email={safe_get(usuario, 'email')}&"
                f"emailDoa={safe_get(usuario, 'email_coordenador')}&"
                f"banco={safe_get(banco_info, 'nome')}&"
                f"agencia={safe_get(banco_info, 'agencia')}&"
                f"conta={safe_get(banco_info, 'conta')}&"
                f"tipoDeConta={safe_get(banco_info, 'tipo')}"
            )



        # Mensagem de manutenção
        # st.write('')
        # st.subheader(':material/build: Formulário temporariamente fora do ar para manutenção.')


        # Exibe o formulário em um iframe
        with st.container(horizontal=True, horizontal_alignment="center"):
            components.iframe(jotform_sav_url, width=1000, height=5000)

        col1, col2, col3 = st.columns([1,2,1])
        col2.subheader('Após enviar, role a página até o topo :material/keyboard_double_arrow_up:')


with terceiros:

    id_usuario = st.session_state.get("id_usuario")

    usuario = get_usuario_normalizado(pessoas, id_usuario)


    # NOVA SOLICITAÇÃO PARA TERCEIROS

    df_usuarios_externos = carregar_externos()
    df_usuarios_externos = df_usuarios_externos.sort_values(by='nome_completo', ascending=True)

    st.write('**Nova Solicitação para Terceiros**')
    st.write('')

    # Cria as colunas para o formulário
    col1, col2, col3, col4 = st.columns(4)

    # Selecione o(a) viajante:
    viajante_nome = col1.selectbox('Selecione o(a) viajante:', [""] + df_usuarios_externos['nome_completo'].tolist())

    if viajante_nome != "":

        viajante = df_usuarios_externos[df_usuarios_externos['nome_completo'] == viajante_nome].iloc[0].to_dict()

        # Monta a URL do JotForm para solicitação de SAV para Terceiros

        # Separa o dicionário do banco antes
        banco_info_ext = safe_get(viajante, 'banco') or {}

        # Função para formatar o CPF e garantir que seja tratado como string quando cair no google sheets, e assim preservar os zeros à esquerda
        def format_cpf(cpf: str) -> str:
            # Remove tudo que não for número
            digits = ''.join(filter(str.isdigit, cpf or ''))
            # Preenche com zeros à esquerda até ter 11 dígitos
            digits = digits.zfill(11)
            # Aplica a máscara 000.000.000-00
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        cpf_formatado = format_cpf(safe_get(usuario, 'cpf'))


        params = {
            "responsavel": safe_get(usuario, "nome_completo"),
            "email_responsavel": safe_get(usuario, "email"),
            "cpf_responsavel": cpf_formatado,
            "email_coordenador": safe_get(usuario, "email_coordenador"),
            "nome_viajante": safe_get(viajante, "nome_completo"),
            "dataDe": safe_get(viajante, "data_nascimento"),
            "genero": safe_get(viajante, "genero"),
            "rg": safe_get(viajante, "rg"),
            "cpf": safe_get(viajante, "cpf"),
            "telefone": safe_get(viajante, "telefone"),
            "email": safe_get(viajante, "email"),
            "banco": safe_get(banco_info_ext, "nome"),
            "agencia": safe_get(banco_info_ext, "agencia"),
            "conta": safe_get(banco_info_ext, "conta"),
            "tipo_conta": safe_get(banco_info_ext, "tipo"),
        }

        jotform_sav_url = f"{st.secrets['links']['url_sav_trc']}?{encode_params(params)}"

        # Mostra a URL no Streamlit
        col2.write('')
        col2.write('')

        # Mensagem de manutenção.
        # col2.write('Site em manutenção. Tente novamente mais tarde.')

        col2.markdown(f"<a href='{jotform_sav_url}' target='_blank'>>> Clique aqui criar uma nova SAV para Terceiros</a>", unsafe_allow_html=True)

    else:

        # Se o viajante não for selecionado, mostra um aviso
        col3.write('O nome não aparece na lista?')

        # Botão de acesso ao Cadastro de Viajante Externo
        if col3.button("Cadastrar viajante", icon=":material/person_add:"):
            cadastrar_externo()

    st.divider()


    # LISTA DE VIAGENS DE TERCEIROS

    st.write('**Viagens solicitadas por mim**')
    st.write('')

    # Limpar a coluna CPF do responsável pela SAV quero apenas os números
    df_savs_terceiros['CPF do responsável pela SAV:'] = df_savs_terceiros['CPF do responsável pela SAV:'].str.replace(r'[^\d]+', '', regex=True)

    # Filtar SAVs com o CPF do usuário
    df_savs_terceiros = df_savs_terceiros[df_savs_terceiros['CPF do responsável pela SAV:'].astype(str) == str(usuario['cpf'])]

    # Capturar a data da viagem
    df_savs_terceiros['Data da viagem:'] = df_savs_terceiros['Itinerário:'].str[6:16].replace('-', '/', regex=True)

    # Expressão regular para capturar o nome da cidade de chegada
    destinos = r'Cidade de chegada: (.*?)(?:,|$)'
    
    # Aplicar a regex para cada linha da coluna
    df_savs_terceiros["Destinos:"] = df_savs_terceiros["Itinerário:"].apply(lambda x: ' > '.join(re.findall(destinos, x)))


    # Criar cabeçalho da "tabela"
    col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 4, 6, 3, 3])

    col1.write('Código da viagem')
    col2.write('Data da viagem')
    col3.write('Nome do(a) viajante')
    col4.write('Destinos')
    col5.write('Solicitações')
    col6.write('Relatórios')

    # Iterar sobre a lista de viagens
    for index, row in df_savs_terceiros[::-1].iterrows():

        # Preparar o link personalizado para o relatório -----------------------------------------------------

        # Extrair cidade(s) de destino
        # Transformar o itinerário em uma lista de dicionários
        trechos = parse_itinerario(row["Itinerário:"])

        # Pegando a primeira e a última data
        data_inicial = trechos[0]["Data"]
        data_final = trechos[-1]["Data"]

        # Formata a data do período da viagem para o formato DD/MM/YYYY a DD/MM/YYYY
        periodo_viagem = f"{data_inicial} a {data_final}".replace('-', '/')

        cidades_chegada = [viagem["Cidade de chegada"] for viagem in trechos]
        
        destinos = ", ".join(cidades_chegada)


        # Prepara as URLs de formulários com alguns campos pré-preenchidos
        # if st.session_state.tipo_usuario == "interno":
        # URL do formulário de RVS de Terceiros
        params = {
            "codigoDa": row["Código da viagem:"],
            "qualE": row["Qual é a fonte do recurso?"],
            "responsavel": row["Responsável pela SAV:"],
            "nome_viajante": row["Nome do(a) viajante:"],
            "email": row["E-mail:"],
            "cidadesDe": destinos,
            "periodoDa": periodo_viagem
        }

        jotform_rvs_terceiros_url = f"{st.secrets['links']['url_rvs_trc']}?{encode_params(params)}"
        
            

        # ----------------------------------------------------------------------------------------------------- 

        # Conteúdo da lista de viagens

        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 4, 6, 3, 3])
        
        col1.write(row['Código da viagem:'])
        col2.write(row['Data da viagem:'])
        col3.write(row['Nome do(a) viajante:'])
        col4.write(row['Destinos:'])
        col5.button('Detalhes', key=f"detalhes_terc_{index}", on_click=mostrar_detalhes_sav, args=(row,), width="stretch", icon=":material/info:")
        

        # Botão dinâmico sobre o relatório --------------------------------------------

        # Verificar se o relatório foi entregue. Procura se tem o código da SAV em algum relatório 
        if row['Código da viagem:'].upper() in df_rvss_terceiros['Código da viagem:'].str.upper().values:

            status_relatorio = "entregue"

        # Se não tem nenhum relatório com esse código de SAV
        else:
            status_relatorio = "pendente"



        # Se o relatório foi entregue, vê o relatório  
        if status_relatorio == "entregue":
            col6.button('Relatório entregue', key=f"entregue_ter_{index}", on_click=mostrar_detalhes_rvs, args=(row, df_rvss_terceiros), width="stretch", icon=":material/check:", type="primary")
        
        # Se não foi entregue, botão para enviar
        # else:
        elif status_relatorio == "pendente":
            # Se não foi entregue, botão para enviar
            col6.link_button('Enviar relatório', width="stretch", icon=":material/description:", url=jotform_rvs_terceiros_url)

        st.divider()  # Separador entre cada linha da tabela


