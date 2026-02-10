import streamlit as st
import pandas as pd 
from funcoes_auxiliares import conectar_mongo_portal_ispn
# from bson import ObjectId
from streamlit_calendar import calendar
from datetime import datetime
import re
import time
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

STATUS_EVENTOS = ["Previsto", "Confirmado", "Cancelado"]
CORES_STATUS = {
    "Previsto": "#F4D03F",     # amarelo
    "Confirmado": "#2ECC71",   # verde
}



# ##################################################################
# CONEXÃO COM O BANCO DE DADOS MONGO
# ##################################################################


# BANCO DE DADOS ISPN HUB / PORTAL / GESTÃO -----------------

db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas
eventos = db["eventos"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_eventos"
nome_pagina = "Eventos"

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


# Função para criar o cliente do Google Sheets
@st.cache_resource(show_spinner=False)
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
@st.cache_data(show_spinner=False)
def carregar_eventos():

    sheet = client.open_by_key(sheet_id)
    
    values_eventos = sheet.worksheet("Jotform - Solicitações de Eventos").get_all_values()

    # Criar DataFrame de Eventos. A primeira linha é usada como cabeçalho
    df_eventos = pd.DataFrame(values_eventos[1:], columns=values_eventos[0])

    # --------------------------------------------------
    # NORMALIZAR CPF (garantir 11 dígitos com zeros à esquerda)
    # --------------------------------------------------

    df_eventos["CPF"] = (
        df_eventos["CPF"]
        .astype(str)
        .str.replace(r"\D", "", regex=True)  # remove pontos e traços
        .str.zfill(11)                       # garante 11 dígitos
    )

    # Converter as colunas de data para datetime
    df_eventos["Submission Date"] = pd.to_datetime(df_eventos["Submission Date"])  # Garantir que é datetime

    # Ordenar em ordem decrescente
    df_eventos = df_eventos.sort_values(by="Submission Date", ascending=False)

    # Converter para string no formato brasileiro
    df_eventos["Submission Date"] = df_eventos["Submission Date"].dt.strftime("%d/%m/%Y")  

    df_eventos = df_eventos.replace({r'\$': r'\$'}, regex=True)

    return df_eventos


def montar_eventos_calendario(df_eventos):
    eventos_cal = []

    for _, row in df_eventos.iterrows():
        status = row["Status"]

        # Ignorar eventos cancelados
        if status == "Cancelado":
            continue

        data_str = row["Data do evento"]
        if not data_str or " a " not in data_str:
            continue

        try:
            # Datas estão no formato “DD-MM-YYYY a DD-MM-YYYY”
            inicio_str, fim_str = data_str.split(" a ")
            inicio_date = datetime.strptime(inicio_str, "%d-%m-%Y").date()
            fim_date = datetime.strptime(fim_str, "%d-%m-%Y").date()

            # FullCalendar usa end EXCLUSIVO → somar 1 dia
            fim_date = fim_date + pd.Timedelta(days=1)

            inicio_iso = inicio_date.isoformat()
            fim_iso = fim_date.isoformat()

        except:
            continue

        eventos_cal.append({
            "title": f"{row['Atividade:']} ({row['Código do evento:']})",
            "start": inicio_iso,
            "end": fim_iso,
            "allDay": True,
            "backgroundColor": CORES_STATUS.get(status, "#95A5A6"),
            "borderColor": CORES_STATUS.get(status, "#95A5A6"),
        })

    return eventos_cal


def sincronizar_status_evento(codigo_evento, key_status):
    novo_status = st.session_state.get(key_status)

    if not novo_status:
        return

    codigo_evento = str(codigo_evento).strip()

    # Atualiza MongoDB
    eventos.update_one(
        {"codigo": codigo_evento},
        {"$set": {"status": novo_status}}
    )

    # Atualiza DataFrame em memória
    df_eventos.loc[
        df_eventos["Código do evento:"].astype(str).str.strip() == codigo_evento,
        "Status"
    ] = novo_status

    st.session_state["status_atualizado"] = True


def calendario_eventos():

    eventos_cal = montar_eventos_calendario(df_eventos)

    if not eventos_cal:
        st.info("Nenhum evento previsto ou confirmado para exibir.")
        return

    calendar_options = {
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,dayGridWeek,listWeek"
        },
        "initialView": "dayGridMonth",  # vista mensal padrão
        "selectable": False,    # não precisa selecionar datas aqui
        "editable": False,
    }

    with st.container():
        calendar(
            events=eventos_cal,
            options=calendar_options,
        )


def sincronizar_eventos_novos(df_eventos, eventos_collection):
    """
    Verifica se existem códigos de eventos no Google Sheets
    que ainda não estão cadastrados no MongoDB.
    Se existirem, cadastra com status = 'previsto'.
    """

    # 1. Códigos vindos do Google Sheets
    codigos_sheet = set(
        df_eventos["Código do evento:"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    if not codigos_sheet:
        return

    # 2. Códigos já existentes no MongoDB
    codigos_mongo = set(
        eventos_collection.distinct("codigo")
    )

    # 3. Descobrir códigos novos
    codigos_novos = codigos_sheet - codigos_mongo

    if not codigos_novos:
        return  # Não há eventos novos → não faz nada

    # 4. Montar documentos para inserção
    documentos = [
        {
            "codigo": codigo,
            "status": "Previsto",
        }
        for codigo in codigos_novos
    ]

    # 5. Inserir de uma vez (mais performático)
    eventos_collection.insert_many(documentos)


def pode_editar_status(evento_cpf):
    cpf_usuario = (
        str(st.session_state.get("cpf", ""))
        .replace(".", "")
        .replace("-", "")
        .zfill(11)
    )

    tipos_usuario = set(st.session_state.get("tipo_usuario", []))

    # Admin ou gestão → sempre pode
    if tipos_usuario & {"admin", "gestao_eventos"}:
        return True

    # Solicitante → se tiver pelo menos um evento
    if cpf_usuario and cpf_usuario in set(df_eventos["CPF"]):
        return True

    return False


def atualizar_status_evento(codigo_evento, novo_status):
    result = eventos.update_one(
        {"codigo": str(codigo_evento).strip()},
        {"$set": {"status": novo_status}}
    )

    if result.matched_count == 0:
        st.error("Evento não encontrado no banco.")


# FUNÇÃO PARA O DIÁLOGO DE DETALHES DO EVENTO  ---------------------------------------------


@st.dialog("Detalhes do evento", width='large')
def detalhes_evento(codigo):
    evento = df_eventos[df_eventos["Código do evento:"] == codigo].iloc[0]

    with st.container(horizontal=True, horizontal_alignment="distribute"):
    
        # Código do evento
        st.subheader(f"**Código:** {evento["Código do evento:"]}")

        cpf_usuario = (
            str(st.session_state.get("cpf", ""))
            .replace(".", "")
            .replace("-", "")
            .zfill(11)
        )

        # Botão de editar
        if evento['CPF'] == cpf_usuario:
                

            url = f"https://jotform.com/edit/{evento['Submission ID']}"

            st.link_button(
                label="Editar solicitação",
                url=url,
                icon=":material/edit:",
                type="secondary"
            )

    # Data da solicitação
    st.write(f"**Data da solicitação:** {evento['Data da solicitação:']}")

    st.divider()


    # Função auxiliar para exibir apenas campos com valor (e esconder se o valor for "Não")
    def mostrar_campo(label, valor, col=None):
        if valor not in [None, "", [], {}, "Não"]:  # inclui "Não" na lista de exclusões
            alvo = col if col else st  # se col for None, usa st diretamente
            alvo.write(f"**{label}** {valor}")


    # Criar colunas
    col1, col2 = st.columns([2, 1])

    mostrar_campo("Datas e horário do evento:", evento.get("Datas e horário do evento:"), col1)

    mostrar_campo("Local:", evento.get("Local"), col1)


    mostrar_campo("Técnico(a) responsável:", evento.get("Técnico(a) responsável:"), col2)

    mostrar_campo("Fonte de recurso:", evento.get("Fonte de recurso:"), col1)
    mostrar_campo("Escritório responsável pelo evento:", evento.get("Escritório responsável pelo evento:"), col2)

    st.divider()

    # Campos seguintes (sem colunas)
    mostrar_campo("Atividade:", evento.get("Atividade:"))
    mostrar_campo("Objetivo da atividade:", evento.get("Objetivo da atividade:"))
    mostrar_campo("Número de participantes:", evento.get("Número de participantes"))
    mostrar_campo("Consultores:", evento.get("Consultores"))

    st.divider()

    mostrar_campo("1) Serão necessários materiais de papelaria como pastas, canetas, xerox, entre outros?", 
                evento.get("1) Serão necessários materiais de papelaria como pastas, canetas, xerox, entre outros?"))
    
    mostrar_campo("Detalhe os materiais de papelaria:", evento.get("Detalhe os materiais de papelaria:"))

    mostrar_campo("2) Será necessária hospedagem para os(as) participantes?", 
                evento.get("2) Será necessária hospedagem para os(as) participantes?"))
    
    mostrar_campo("Quantos participantes precisarão de hospedagem?", evento.get("Quantos participantes precisarão de hospedagem?"))

    mostrar_campo("3) Será necessário transporte para os(as) participantes?", 
                evento.get("3) Será necessário transporte para os(as) participantes?"))
    
    mostrar_campo("Detalhe o transporte dos(as) participantes:", evento.get("Detalhe o transporte dos(as) participantes:"))

    mostrar_campo("4) Será necessário o pagamento de diárias para Participantes? (Elaborar SAV de Terceiros)", 
                evento.get("4) Será necessário o pagamento de diárias para Participantes? (Elaborar SAV de Terceiros)"))
    
    mostrar_campo("Quantos participantes precisam receber diárias?", evento.get("Quantos participantes precisam receber diárias?"))

    mostrar_campo("5) Será necessário o pagamento de diárias para cozinheiras?", 
                evento.get("5) Será necessário o pagamento de diárias para cozinheiras?"))
    
    mostrar_campo("Informações para pagamento de apoio (cozinha e outros):", evento.get("Informações para pagamento de apoio (cozinha e outros):"))

    mostrar_campo("6) Será necessário o pagamento de alimentação?", evento.get("6) Será necessário o pagamento de alimentação?"))
    
    mostrar_campo("Detalhe a alimentação necessária (café da manhã, almoço e janta):", evento.get("Detalhe a alimentação necessária (café da manhã, almoço e janta):"))

    mostrar_campo("7) Será necessário transporte para o(a) consultor(a)?", evento.get("7) Será necessário transporte para o(a) consultor(a)?"))
    
    mostrar_campo("Detalhe o transporte de consultor(a):", evento.get("Detalhe o transporte de consultor(a):"))

    mostrar_campo("8) Será necessário adiantamento para pagamento de despesas da atividade?", evento.get("8) Será necessário adiantamento para pagamento de despesas da atividade?"))
    
    mostrar_campo("Descreva o(s) adiantamento(s) necessário(s):", evento.get("Descreva o(s) adiantamento(s) necessário(s):"))

    mostrar_campo("9) Será necessário aluguel de veículo(s)?", evento.get("9) Será necessário aluguel de veículo(s)?"))
    
    mostrar_campo("Detalhes sobre a locação de veículo(s):", evento.get("Detalhes sobre a locação de veículo(s):"))

    mostrar_campo("10) Será necessária a compra de combustível?", evento.get("10) Será necessária a compra de combustível?"))
    
    mostrar_campo("Descreva os tipos, locais, quantidades e demais informações relevantes sobre a compra de combustível:", 
                evento.get("Descreva os tipos, locais, quantidades e demais informações relevantes sobre a compra de combustível:"))

    st.divider()

    mostrar_campo("Informações adicionais sobre o evento (caso seja necessário):", evento.get("Informações adicionais sobre o evento (caso seja necessário):"))
    mostrar_campo("Última edição da solicitação:", evento.get("Last Update Date"))


# FUNÇÕES PARA RENDERIZAR AS ABAS DE EVENTOS  ---------------------------------------------

def todos_os_eventos():

    st.write('')

    largura_colunas = [2, 2, 5, 3, 3, 3, 3]

    # Cabeçalho das colunas

    col1, col2, col3, col4, col5, col6, col7 = st.columns(largura_colunas)

    col1.write('**Código:**')
    col2.write('**Solicitado em:**')
    col3.write('**Atividade**:')
    col4.write('**Nome do(a) solicitante**:')
    col5.write('**Data do evento:**')
    col6.write('**Status:**')
    col7.write('')

    st.write('')

    # Para cada linha da tabela, lança 6 colunas, com um botão de detalhes na última coluna
    for index, row in df_eventos.iterrows():
        col1, col2, col3, col4, col5, col6, col7 = st.columns(largura_colunas)

        col1.write(row['Código do evento:'])
        col2.write(row['Data da solicitação:'])
        col3.write(row['Atividade:'])
        col4.write(row['Técnico(a) responsável:'])
        col5.write(row['Data do evento'])

        pode_editar = pode_editar_status(row["CPF"])

        status_atual = row["Status"]
        key_status = f"status_todos_{row['Código do evento:']}"

        modo_edicao = st.session_state.get("modo_edicao", False)

        if pode_editar and modo_edicao:
            col6.selectbox(
                label="Status do evento",
                options=STATUS_EVENTOS,
                index=STATUS_EVENTOS.index(status_atual),
                key=key_status,
                label_visibility="collapsed",
                on_change=sincronizar_status_evento,
                args=(row["Código do evento:"], key_status)
            )
        else:
            col6.write(status_atual)

        col7.button(
            "Detalhes",
            key=f"detalhes_todos_{index}",
            icon=":material/list:",
            width="stretch",
            on_click=detalhes_evento,
            args=(row["Código do evento:"],)
        )


def meus_eventos():
    st.write('')

    cpf_usuario = (
        str(st.session_state.get("cpf", ""))
        .replace(".", "")
        .replace("-", "")
        .zfill(11)
    )

    # Filtrar somente os eventos do usuário
    df_meus_eventos = df_eventos[df_eventos["CPF"] == cpf_usuario]

    largura_colunas = [2, 2, 5, 3, 3, 3, 3]

    # Cabeçalho das colunas

    col1, col2, col3, col4, col5, col6, col7 = st.columns(largura_colunas)

    col1.write('**Código:**')
    col2.write('**Solicitado em:**')
    col3.write('**Atividade**:')
    col4.write('**Nome do(a) solicitante**:')
    col5.write('**Data do evento:**')
    col6.write('**Status:**')
    col7.write('')
    st.write('')

    # Para cada linha da tabela, lança 6 colunas, com um botão de detalhes na última coluna
    for index, row in df_meus_eventos.iterrows():
        col1, col2, col3, col4, col5, col6, col7 = st.columns(largura_colunas)

        col1.write(row['Código do evento:'])
        col2.write(row['Data da solicitação:'])
        col3.write(row['Atividade:'])
        col4.write(row['Técnico(a) responsável:'])
        col5.write(row['Data do evento'])
        pode_editar = pode_editar_status(row["CPF"])

        status_atual = row["Status"]
        key_status = f"status_meus_{row['Código do evento:']}"

        modo_edicao = st.session_state.get("modo_edicao", False)

        if pode_editar and modo_edicao:
            col6.selectbox(
                label="Status do evento",
                options=STATUS_EVENTOS,
                index=STATUS_EVENTOS.index(status_atual),
                key=key_status,
                label_visibility="collapsed",
                on_change=sincronizar_status_evento,
                args=(row["Código do evento:"], key_status)
            )
        else:
            col6.write(status_atual)

        col7.button(
            "Detalhes",
            key=f"detalhes_meus_{index}",
            icon=":material/list:",
            width="stretch",
            on_click=detalhes_evento,
            args=(row["Código do evento:"],)
        )


def nova_solicitacao():
    st.write('')

    # Garante que o CPF está disponível
    cpf = st.session_state.get("cpf", "")

    # Monta a URL com o parâmetro cpf
    base_url = st.secrets.links.url_eventos_jotform
    url_com_parametro = f"{base_url}?cpf={cpf}"

    st.link_button(
        label="Clique aqui para enviar uma nova solicitação",
        url=url_com_parametro,
        type="secondary",
        icon=":material/docs:"
    )


# ##################################################################
# CARREGAMENTO E TRATAMENTO DOS DADOS
# ##################################################################


df_eventos = carregar_eventos()

sincronizar_eventos_novos(df_eventos, eventos)

# --------------------------------------------------
# BUSCAR STATUS DOS EVENTOS NO MONGODB
# --------------------------------------------------

# Criar um dicionário {codigo: status}
mapa_status = {
    doc["codigo"]: doc.get("status")
    for doc in eventos.find({}, {"codigo": 1, "status": 1, "_id": 0})
}

# Criar coluna Status no dataframe
df_eventos["Status"] = (
    df_eventos["Código do evento:"]
    .astype(str)
    .str.strip()
    .map(mapa_status)
    .fillna("Previsto")
)

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


with st.container(horizontal=True, horizontal_alignment="right"):

    if st.button("Atualizar página", type="secondary", icon=":material/refresh:"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

st.write("")

# --------------------------------------------------
# CONTROLE DE MODO DE EDIÇÃO
# --------------------------------------------------

if "modo_edicao" not in st.session_state:
    st.session_state["modo_edicao"] = False

usuario_pode_ver_toggle = pode_editar_status(df_eventos)

container_toggle = st.container(horizontal=True, horizontal_alignment="right")

if usuario_pode_ver_toggle:
    st.write("")
    container_toggle.toggle(
        "Modo de edição",
        key="modo_edicao",
    )
else:
    st.session_state["modo_edicao"] = False

# Roteamento de tipo de usuário. admin e gestao_eventos podem ver a aba Todos os eventos
if set(st.session_state.tipo_usuario) & {"admin", "gestao_eventos"}:

    tabs = st.tabs(["Calendário", "Todos os eventos", "Minhas solicitações", "Nova Solicitação"])

    # Aba Calendário
    with tabs[0]:
        calendario_eventos()

    # Aba Todos os eventos
    with tabs[1]:
        todos_os_eventos()

    # Aba Meus eventos
    with tabs[2]:
        meus_eventos()

    # Aba Nova Solicitação
    with tabs[3]:
        nova_solicitacao()

else:
    tabs = st.tabs(["Meus eventos", "Calendário", "Nova Solicitação"])

    # Aba Calendário
    with tabs[0]:
        calendario_eventos()

    # Aba Meus eventos
    with tabs[1]:
        meus_eventos()

    # Aba Nova Solicitação
    with tabs[2]:
        st.write("Nova Solicitação")
        
if st.session_state.get("status_atualizado"):
    placeholder = st.empty()

    placeholder.success(
        "Status atualizado",
        icon=":material/check:"
    )

    time.sleep(2)

    placeholder.empty()
    st.session_state["status_atualizado"] = False