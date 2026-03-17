import streamlit as st
from bson import ObjectId
from datetime import datetime

from funcoes_auxiliares import conectar_mongo_portal_ispn

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
# EDITAR CARD
######################################################################################################



######################################################################################################
# EDITAR CARD COM TAGS (SEM FECHAR O DIALOG)
######################################################################################################

@st.dialog("Editar atividade")
def dialog_editar_card(card):

    ##################################################################################################
    # CARREGA PISTAS
    ##################################################################################################

    pistas_board = list(
        kanban_pistas.find({"board_id": card["board_id"]}).sort("ordem", 1)
    )

    dict_pistas = {p["nome"]: p["_id"] for p in pistas_board}

    ##################################################################################################
    # CAMPOS PRINCIPAIS
    ##################################################################################################

    atividade = st.text_input("Atividade", value=card.get("atividade", ""))

    descricao = st.text_area("Descrição", value=card.get("descricao_ativ", ""))

    # Descobre pista atual
    pista_atual_nome = next(
        (p["nome"] for p in pistas_board if p["_id"] == card["pista_id"]),
        None
    )

    pista_escolhida = st.selectbox(
        "Pista",
        options=list(dict_pistas.keys()),
        index=list(dict_pistas.keys()).index(pista_atual_nome) if pista_atual_nome else 0
    )

    ##################################################################################################
    # DATA
    ##################################################################################################

    data_fim_inicial = datetime.strptime(
        card.get("data_fim", "01/01/2000"),
        "%d/%m/%Y"
    )

    data_fim_input = st.date_input(
        "Data fim",
        value=data_fim_inicial,
        format="DD/MM/YYYY"
    )

    ##################################################################################################
    # PESSOAS
    ##################################################################################################

    # Busca pessoas já ordenadas alfabeticamente
    pessoas_lista = list(
        pessoas.find({}).sort("nome_completo", 1)
    )

    # Cria dicionário mantendo a ordem
    dict_pessoas = {
        p["nome_completo"]: p["_id"] for p in pessoas_lista
    }

    # Responsáveis atuais
    responsaveis_atuais = [
        nome for nome, _id in dict_pessoas.items()
        if _id in card.get("responsaveis", [])
    ]

    # Multiselect já ordenado
    responsaveis = st.multiselect(
        "Responsáveis",
        options=list(dict_pessoas.keys()),
        default=responsaveis_atuais
    )



    ##################################################################################################
    # TAGS - ESTADO LOCAL
    ##################################################################################################

    if "tags_board_local" not in st.session_state:
        board = kanban_boards.find_one({"_id": card["board_id"]})
        st.session_state["tags_board_local"] = board.get("tags", [])

    tags_board = st.session_state["tags_board_local"]

    dict_tags = {
        tag["nome"]: tag for tag in tags_board
    }

    opcoes_tags = ["+ Nova tag"] + sorted(dict_tags.keys())

    # Tags atuais do card
    tags_card_atuais = [
        tag["nome"] for tag in card.get("tags", [])
    ]

    tags_selecionadas = st.multiselect(
        "Tags",
        options=opcoes_tags,
        default=tags_card_atuais
    )

    ##################################################################################################
    # CONTROLE DE CRIAÇÃO DE TAG
    ##################################################################################################

    if "criar_tag" not in st.session_state:
        st.session_state["criar_tag"] = False

    if "+ Nova tag" in tags_selecionadas:
        st.session_state["criar_tag"] = True

    ##################################################################################################
    # FORM NOVA TAG
    ##################################################################################################

    if st.session_state["criar_tag"]:

        with st.container(border=True):

            st.subheader("Nova tag")

            nome_tag = st.text_input("Nome da tag")
            cor_tag = st.color_picker("Cor", "#007ad3")

            col1, col2 = st.columns(2)

            # Salvar tag
            with col1:
                if st.button("Salvar tag", use_container_width=True):

                    if nome_tag != "":

                        nomes_existentes = [
                            t["nome"] for t in tags_board
                        ]

                        if nome_tag not in nomes_existentes:

                            nova_tag = {
                                "nome": nome_tag,
                                "cor": cor_tag
                            }

                            # Salva no banco
                            kanban_boards.update_one(
                                {"_id": card["board_id"]},
                                {"$push": {"tags": nova_tag}}
                            )

                            # Atualiza estado local
                            st.session_state["tags_board_local"].append(nova_tag)

                        st.session_state["criar_tag"] = False

            # Cancelar
            with col2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state["criar_tag"] = False

    ##################################################################################################
    # SALVAR ALTERAÇÕES
    ##################################################################################################

    st.divider()

    if st.button("Salvar alterações", icon=":material/save:", type="primary"):

        # Responsáveis
        lista_responsaveis = [
            dict_pessoas[nome] for nome in responsaveis
        ]

        # Tags válidas
        tags_validas = [
            t for t in tags_selecionadas if t != "+ Nova tag"
        ]

        lista_tags = [
            dict_tags[nome] for nome in tags_validas
        ]

        # Pista
        nova_pista_id = dict_pistas[pista_escolhida]

        # Ordem
        if nova_pista_id != card["pista_id"]:

            total_destino = kanban_cards.count_documents({
                "board_id": card["board_id"],
                "pista_id": nova_pista_id
            })

            nova_ordem = total_destino

        else:
            nova_ordem = card["ordem"]

        # Atualiza card
        kanban_cards.update_one(
            {"_id": card["_id"]},
            {
                "$set": {
                    "atividade": atividade,
                    "descricao_ativ": descricao,
                    "data_fim": data_fim_input.strftime("%d/%m/%Y"),
                    "responsaveis": lista_responsaveis,
                    "tags": lista_tags,
                    "pista_id": nova_pista_id,
                    "ordem": nova_ordem
                }
            }
        )

        # Limpa estado local (evita conflito entre dialogs)
        if "tags_board_local" in st.session_state:
            del st.session_state["tags_board_local"]

        st.rerun()






######################################################################################################
# CRIAR NOVO BOARD
######################################################################################################

@st.dialog("Criar novo board")
def dialog_criar_board():

    nome_board = st.text_input("Nome do board")

    # Busca apenas pessoas ativas já ordenadas alfabeticamente
    pessoas_ativas = list(
        pessoas.find({"status": "ativo"}).sort("nome_completo", 1)
    )


    # # Busca apenas pessoas ativas
    # pessoas_ativas = list(
    #     pessoas.find({"status": "ativo"})
    # )

    # Dicionário nome -> id
    dict_pessoas = {
        p["nome_completo"]: p["_id"]
        for p in pessoas_ativas
    }

    # Multiselect de membros
    membros_selecionados = st.multiselect(
        "Membros do board",
        options=list(dict_pessoas.keys())
    )

    if st.button("Criar board", use_container_width=True):

        if nome_board != "":

            # Converte nomes selecionados em IDs
            lista_membros = [
                dict_pessoas[nome]
                for nome in membros_selecionados
            ]

            # Garante que o criador está na lista
            if id_usuario not in lista_membros:
                lista_membros.append(id_usuario)

            kanban_boards.insert_one({
                "nome": nome_board,
                "criador": id_usuario,
                "membros": lista_membros,
                "data_criacao": datetime.now()
            })

            st.rerun()




######################################################################################################
# CRIAR COLUNA
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
# CRIAR CARD COM TAGS (SEM FECHAR O DIALOG AO CRIAR TAG)
######################################################################################################

@st.dialog("Criar atividade")
def dialog_criar_card(board_id):

    ##################################################################################################
    # CARREGA PISTAS
    ##################################################################################################

    pistas_board = list(
        kanban_pistas.find({"board_id": board_id}).sort("ordem", 1)
    )

    if len(pistas_board) == 0:
        st.warning("Crie ao menos uma pista.")
        return

    dict_pistas = {p["nome"]: p["_id"] for p in pistas_board}

    ##################################################################################################
    # CAMPOS PRINCIPAIS
    ##################################################################################################

    atividade = st.text_input("Atividade")
    descricao = st.text_area("Descrição")

    pista_escolhida = st.selectbox(
        "Pista",
        list(dict_pistas.keys())
    )

    data_fim_input = st.date_input("Data fim", format="DD/MM/YYYY")

    ##################################################################################################
    # PESSOAS
    ##################################################################################################

    pessoas_lista = list(pessoas.find({}))
    dict_pessoas = {
        p["nome_completo"]: p["_id"] for p in pessoas_lista
    }

    responsaveis = st.multiselect(
        "Responsáveis",
        list(dict_pessoas.keys())
    )

    ##################################################################################################
    # TAGS - ESTADO LOCAL (EVITA FECHAR O DIALOG)
    ##################################################################################################

    # Inicializa estado local das tags apenas uma vez
    if "tags_board_local" not in st.session_state:
        board = kanban_boards.find_one({"_id": board_id})
        st.session_state["tags_board_local"] = board.get("tags", [])

    tags_board = st.session_state["tags_board_local"]

    # Mapeia nome -> objeto tag
    dict_tags = {
        tag["nome"]: tag for tag in tags_board
    }

    # Opções com "+ Nova tag"
    opcoes_tags = ["+ Nova tag"] + sorted(dict_tags.keys())

    tags_selecionadas = st.multiselect(
        "Tags",
        options=opcoes_tags
    )

    ##################################################################################################
    # CONTROLE DE EXIBIÇÃO DO FORM DE NOVA TAG
    ##################################################################################################

    if "criar_tag" not in st.session_state:
        st.session_state["criar_tag"] = False

    if "+ Nova tag" in tags_selecionadas:
        st.session_state["criar_tag"] = True

    ##################################################################################################
    # FORM DE CRIAÇÃO DE TAG (SEM RERUN)
    ##################################################################################################

    if st.session_state["criar_tag"]:

        with st.container(border=True):

            st.subheader("Nova tag")

            nome_tag = st.text_input("Nome da tag")
            cor_tag = st.color_picker("Cor", "#3642ad")

            col1, col2 = st.columns(2)

            # BOTÃO SALVAR TAG
            with col1:
                if st.button("Salvar tag", use_container_width=True):

                    if nome_tag != "":

                        # Evita duplicação
                        nomes_existentes = [
                            t["nome"] for t in tags_board
                        ]

                        if nome_tag not in nomes_existentes:

                            nova_tag = {
                                "nome": nome_tag,
                                "cor": cor_tag
                            }

                            # Salva no banco
                            kanban_boards.update_one(
                                {"_id": board_id},
                                {"$push": {"tags": nova_tag}}
                            )

                            # Atualiza estado local (SEM rerun)
                            st.session_state["tags_board_local"].append(nova_tag)

                        # Fecha form de criação
                        st.session_state["criar_tag"] = False

            # BOTÃO CANCELAR
            with col2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state["criar_tag"] = False

    ##################################################################################################
    # SALVAR CARD
    ##################################################################################################

    if st.button("Criar atividade", use_container_width=True):

        # Converte responsáveis para IDs
        lista_responsaveis = [
            dict_pessoas[n] for n in responsaveis
        ]

        # Remove opção "+ Nova tag"
        tags_validas = [
            t for t in tags_selecionadas if t != "+ Nova tag"
        ]

        # Converte para objetos completos de tag
        lista_tags = [
            dict_tags[n] for n in tags_validas
        ]

        # Calcula ordem
        total = kanban_cards.count_documents({
            "board_id": board_id,
            "pista_id": dict_pistas[pista_escolhida]
        })

        # Insere card
        kanban_cards.insert_one({
            "atividade": atividade,
            "descricao_ativ": descricao,
            "criador": id_usuario,
            "data_criacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "data_fim": data_fim_input.strftime("%d/%m/%Y"),
            "responsaveis": lista_responsaveis,
            "tags": lista_tags,
            "board_id": board_id,
            "pista_id": dict_pistas[pista_escolhida],
            "ordem": total
        })

        # Limpa estado de tags (opcional, evita “vazar” para outro board)
        if "tags_board_local" in st.session_state:
            del st.session_state["tags_board_local"]

        st.rerun()







######################################################################################################
# BARRA SUPERIOR
######################################################################################################

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
# LISTA BOARDS
######################################################################################################

boards_usuario = list(
    kanban_boards.find({"membros": id_usuario})
)

if len(boards_usuario) == 0:
    st.warning("Nenhum board criado.")
    st.stop()

dict_boards = {
    board["nome"]: board["_id"]
    for board in boards_usuario
}

######################################################################################################
# SELEÇÃO BOARD
######################################################################################################

board_nome = st.segmented_control(
    "Meus Painéis",
    options=list(dict_boards.keys()),
    default=list(dict_boards.keys())[0],
)

board_id = dict_boards[board_nome]

######################################################################################################
# AÇÕES
######################################################################################################

with st.container(horizontal=True, horizontal_alignment="right"):

    if st.button("Nova coluna", icon=":material/add_column_right:", width=200):
        dialog_criar_pista(board_id)

    if st.button(" Nova Atividade", icon=":material/assignment_turned_in:", type="primary", width=200):
        dialog_criar_card(board_id)

######################################################################################################
# RENDERIZAÇÃO KANBAN 
######################################################################################################




@st.fragment
def renderizar_kanban(board_id):

    # Carrega pistas
    pistas = list(
        kanban_pistas.find({"board_id": board_id}).sort("ordem", 1)
    )

    # Carrega cards
    cards = list(
        kanban_cards.find({"board_id": board_id}).sort("ordem", 1)
    )

    # Dicionário de pessoas
    pessoas_dict = {
        p["_id"]: p["nome_completo"]
        for p in pessoas.find({})
    }

    st.write('')
    st.write('')
    st.write('')

    # Evita erro quando não há pistas
    if len(pistas) == 0:
        st.warning("Este painel ainda não possui colunas. Crie a primeira coluna.")
        return

    # Cria colunas
    cols = st.columns(len(pistas), gap="small")

    # Itera sobre pistas
    for idx, pista in enumerate(pistas):

        with cols[idx]:
            st.subheader(pista["nome"])

            cards_pista = [
                c for c in cards if c["pista_id"] == pista["_id"]
            ]

            cards_pista = sorted(cards_pista, key=lambda x: x["ordem"])

            for card in cards_pista:

                nomes_responsaveis = []

                for resp in card.get("responsaveis", []):
                    pessoa = pessoas_dict.get(resp)
                    if pessoa:
                        nomes_responsaveis.append(pessoa.split()[0])



                # ########################
                # CARD
                # ########################

                with st.container(border=True):

                                        



                    with st.container(horizontal=True, horizontal_alignment="right"):

                        with st.container():

                            # ########################
                            # BADGES DE TAGS
                            # ########################

                            tags_card = card.get("tags", [])

                            if tags_card:

                                badges_html = """
                                <div style="
                                    display:flex;
                                    flex-wrap:wrap;
                                    gap:6px;
                                    margin-bottom:6px;
                                ">
                                """

                                for tag in tags_card:
                                    badges_html += f"""
                                    <div style="
                                        background-color:{tag['cor']};
                                        color:white;
                                        padding:2px 8px;
                                        border-radius:8px;
                                        font-size:13px;
                                        display:inline-block;
                                    ">
                                        {tag['nome']}
                                    </div>
                                    """

                                badges_html += "</div>"

                                st.html(badges_html)


                        # ########################
                        # POPOVER menu do card
                        # ########################

                        with st.popover(
                            "",
                            icon=":material/more_vert:",
                            type="tertiary"
                        ):

                            # Botão editar card
                            if st.button(
                                "Editar card",
                                icon=":material/edit:",
                                key=f"editar_{card['_id']}",
                                use_container_width=True,
                                type="secondary"
                            ):
                                dialog_editar_card(card)


                            st.caption("Mover para:")

                            # Itera sobre todas as pistas
                            for pista_destino in pistas:

                                # Ignora a pista atual
                                if pista_destino["_id"] == pista["_id"]:
                                    continue

                                # Botão para mover card ----------------------------------------------
                                if st.button(
                                    pista_destino["nome"],
                                    key=f"mover_{card['_id']}_{pista_destino['_id']}",
                                    use_container_width=True,
                                    type="secondary",
                                    width=400,
                                ):

                                    # Calcula nova ordem (último da lista da pista destino)
                                    total_destino = kanban_cards.count_documents({
                                        "board_id": board_id,
                                        "pista_id": pista_destino["_id"]
                                    })

                                    # Atualiza card no banco
                                    kanban_cards.update_one(
                                        {"_id": card["_id"]},
                                        {
                                            "$set": {
                                                "pista_id": pista_destino["_id"],
                                                "ordem": total_destino
                                            }
                                        }
                                    )

                                    # Recarrega interface
                                    st.rerun(scope="fragment")



                    st.markdown(f"**{card['atividade']}**")

                    if card.get("descricao_ativ"):
                        st.caption(card["descricao_ativ"])

                    st.write(f":material/event: {card.get('data_fim','')}")
                    st.write(f":material/group: {', '.join(nomes_responsaveis)}")




renderizar_kanban(board_id)












