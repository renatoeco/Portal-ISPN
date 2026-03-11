import streamlit as st
from bson import ObjectId
from datetime import datetime

from funcoes_auxiliares import conectar_mongo_portal_ispn
from streamlit_kanban_os import kanban_board


st.set_page_config(layout="wide")



# Exibe o logo do ISPN na página
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

# Cabeçalho da página
st.header("Kanban")
st.write('')








######################################################################################################
# CONEXÃO COM O BANCO
######################################################################################################

# Conecta no MongoDB
db = conectar_mongo_portal_ispn()

# Coleções
pessoas = db["pessoas"]
kanban_boards = db["kanban_boards"]
kanban_pistas = db["kanban_pistas"]
kanban_cards = db["kanban_cards"]


######################################################################################################
# IDENTIFICA USUÁRIO LOGADO
######################################################################################################

# Recupera id do usuário logado
id_usuario = st.session_state["id_usuario"]






######################################################################################################
# FUNÇÕES AUXILIARES
######################################################################################################





######################################################################################################
# CRIAR NOVO BOARD
######################################################################################################

# DIÁLOGO CRIAR BOARD

@st.dialog("Criar novo board")
def dialog_criar_board():

    nome_board = st.text_input("Nome do board")

    if st.button("Criar board", use_container_width=True):

        if nome_board != "":

            kanban_boards.insert_one({
                "nome": nome_board,
                "criador": id_usuario,
                "membros": [id_usuario],
                "data_criacao": datetime.now()
            })

            st.rerun()





######################################################################################################
# DIÁLOGO CRIAR COLUNA
######################################################################################################

@st.dialog("Criar coluna")
def dialog_criar_pista(board_id):

    nome_pista = st.text_input("Nome da coluna")

    if st.button("Criar coluna", icon=":material/add:"):

        if nome_pista != "":

            total = kanban_pistas.count_documents({"board_id": board_id})

            kanban_pistas.insert_one({
                "board_id": board_id,
                "nome": nome_pista,
                "ordem": total
            })

            st.rerun()






######################################################################################################
# DIÁLOGO CRIAR ATIVIDADE
######################################################################################################

@st.dialog("Criar atividade")
def dialog_criar_card(board_id):

    pistas_board = list(
        kanban_pistas.find({"board_id": board_id}).sort("ordem", 1)
    )

    if len(pistas_board) == 0:
        st.warning("Crie ao menos uma pista.")
        return

    dict_pistas = {p["nome"]: p["_id"] for p in pistas_board}

    atividade = st.text_input("Atividade")

    descricao = st.text_area("Descrição")

    pista_escolhida = st.selectbox(
        "Pista",
        list(dict_pistas.keys())
    )

    data_fim_input = st.date_input(
        "Data fim",
        format="DD/MM/YYYY"
    )

    pessoas_lista = list(pessoas.find({}))

    dict_pessoas = {
        p["nome_completo"]: p["_id"] for p in pessoas_lista
    }

    responsaveis = st.multiselect(
        "Responsáveis",
        list(dict_pessoas.keys())
    )

    if st.button("Criar atividade", use_container_width=True):

        data_fim = data_fim_input.strftime("%d/%m/%Y")

        lista_responsaveis = [
            dict_pessoas[nome] for nome in responsaveis
        ]

        total_cards = kanban_cards.count_documents({
            "board_id": board_id,
            "pista_id": dict_pistas[pista_escolhida]
        })

        kanban_cards.insert_one({

            "atividade": atividade,
            "descricao_ativ": descricao,

            "criador": id_usuario,

            "data_criacao": datetime.now().strftime("%d/%m/%Y %H:%M"),

            "data_fim": data_fim,

            "responsaveis": lista_responsaveis,

            "board_id": board_id,
            "pista_id": dict_pistas[pista_escolhida],

            "ordem": total_cards
        })

        st.rerun()







######################################################################################################
# INÍCIO DA INTERFACE
######################################################################################################



# BARRA SUPERIOR COM BOTÃO DE NOVO BOARD


with st.container(horizontal=True, horizontal_alignment="right"):

    if st.button(
        "Novo painel",
        type="secondary",
        icon=":material/add:",
        width=200
    ):
        dialog_criar_board()

st.divider()

######################################################################################################
# LISTA BOARDS DO USUÁRIO
######################################################################################################

boards_usuario = list(
    kanban_boards.find({
        "membros": id_usuario
    })
)

if len(boards_usuario) == 0:
    st.warning("Nenhum board criado.")
    st.stop()


# Cria dicionário nome → id
dict_boards = {
    board["nome"]: board["_id"]
    for board in boards_usuario
}


######################################################################################################
# SELEÇÃO DE BOARD
######################################################################################################

board_nome = st.segmented_control(
    "Meus Painéis",
    options=list(dict_boards.keys()),
    default=list(dict_boards.keys())[0],
)

board_id = dict_boards[board_nome]






######################################################################################################
# BARRA DE AÇÕES
######################################################################################################


with st.container(horizontal=True, horizontal_alignment="right"):



    if st.button("Nova coluna", icon=":material/add_column_right:", width=200):
        dialog_criar_pista(board_id)


    if st.button(" Nova Atividade", icon=":material/task:",type="primary", width=200):
        dialog_criar_card(board_id)


######################################################################################################
# INÍCIO DO KANBAN
######################################################################################################




@st.fragment
def renderizar_kanban(board_id):

    ##################################################################################################
    # CARREGAR PISTAS
    ##################################################################################################

    pistas = list(
        kanban_pistas.find({"board_id": board_id}).sort("ordem", 1)
    )

    ##################################################################################################
    # CARREGAR CARDS
    ##################################################################################################

    cards = list(
        kanban_cards.find({"board_id": board_id}).sort("ordem", 1)
    )

    pessoas_dict = {
        p["_id"]: p["nome_completo"]
        for p in pessoas.find({})
    }

    ##################################################################################################
    # MONTAR COLUNAS
    ##################################################################################################

    columns = []

    for pista in pistas:

        cards_pista = []

        for card in cards:

            if card["pista_id"] == pista["_id"]:

                nomes_responsaveis = []

                for resp in card.get("responsaveis", []):
                    pessoa = pessoas_dict.get(resp)
                    if pessoa:
                        nomes_responsaveis.append(pessoa.split()[0])

                cards_pista.append({
                    "id": str(card["_id"]),
                    "title": (
                        f"{card['atividade']}\n"
                        f"Data fim: {card.get('data_fim','')}\n"
                        f"Responsáveis: {', '.join(nomes_responsaveis)}"
                    )
                })


        columns.append({
            "title": pista["nome"],
            "cards": cards_pista
        })

    ##################################################################################################
    # RENDERIZAR KANBAN
    ##################################################################################################





    # CONFIGURAÇÃO DE LARGURA DAS COLUNAS
    # Slider para definir largura mínima das pistas
    min_width_colunas = st.slider(
        "Largura das colunas",
        min_value=120,
        max_value=600,
        value=210,
        step=10,
        width=300
    )


    board = kanban_board(
        columns,

        horizontal=True,

        width="stretch",
        height="content",

        horizontal_alignment="distribute",

        min_width=min_width_colunas,

        stacked=False,

        gap="small",
        border=False
    )

    ##################################################################################################
    # SALVAR MOVIMENTAÇÃO
    ##################################################################################################

    mudou = False

    if board and "columns" in board:

        for coluna in board["columns"]:

            pista_atual = None

            for pista in pistas:
                if pista["nome"] == coluna["title"]:
                    pista_atual = pista
                    break

            if pista_atual is None:
                continue

            pista_id = pista_atual["_id"]

            for ordem_card, card in enumerate(coluna["cards"]):

                card_id = ObjectId(card["id"])

                card_db = kanban_cards.find_one({"_id": card_id})

                if card_db["pista_id"] != pista_id or card_db["ordem"] != ordem_card:

                    kanban_cards.update_one(
                        {"_id": card_id},
                        {
                            "$set": {
                                "pista_id": pista_id,
                                "ordem": ordem_card
                            }
                        }
                    )

                    mudou = True

    if mudou:
        st.rerun(scope="fragment")



renderizar_kanban(board_id)








