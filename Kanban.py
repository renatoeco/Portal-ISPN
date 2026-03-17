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
estatistica = db["estatistica"]  # Coleção de estatísticas


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_kanban"
nome_pagina = "Kanban"

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


######################################################################################################
# IDENTIFICA USUÁRIO LOGADO
######################################################################################################

# Recupera id do usuário logado
id_usuario = st.session_state["id_usuario"]






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
# DIÁLOGO DE CRIAR E EDITAR CARD DE ATIVIDADE
######################################################################################################

@st.dialog("Atividade")
def dialog_card(board_id, card=None):

    modo_edicao = card is not None

    ##################################################################################################
    # CARREGA DADOS
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

    atividade = st.text_input(
        "Atividade",
        value=card.get("atividade", "") if modo_edicao else ""
    )

    descricao = st.text_area(
        "Descrição",
        value=card.get("descricao_ativ", "") if modo_edicao else ""
    )

    # Pista atual
    if modo_edicao:
        pista_atual_nome = next(
            (p["nome"] for p in pistas_board if p["_id"] == card["pista_id"]),
            None
        )
        index_pista = list(dict_pistas.keys()).index(pista_atual_nome)
    else:
        index_pista = 0

    pista_escolhida = st.selectbox(
        "Pista",
        list(dict_pistas.keys()),
        index=index_pista
    )

    ##################################################################################################
    # DATA
    ##################################################################################################

    if modo_edicao:
        data_inicial = datetime.strptime(card.get("data_fim"), "%d/%m/%Y")
    else:
        data_inicial = datetime.today()

    data_fim_input = st.date_input("Data fim", value=data_inicial)

    ##################################################################################################
    # PESSOAS
    ##################################################################################################

    pessoas_lista = list(
        pessoas.find({}).sort("nome_completo", 1)
    )

    dict_pessoas = {
        p["nome_completo"]: p["_id"] for p in pessoas_lista
    }

    if modo_edicao:
        responsaveis_atuais = [
            nome for nome, _id in dict_pessoas.items()
            if _id in card.get("responsaveis", [])
        ]
    else:
        responsaveis_atuais = []

    responsaveis = st.multiselect(
        "Responsáveis",
        options=list(dict_pessoas.keys()),
        default=responsaveis_atuais
    )

    ##################################################################################################
    # TAGS (ESTADO ÚNICO)
    ##################################################################################################

    key_tags = f"tags_board_local_{board_id}"

    if key_tags not in st.session_state:
        board = kanban_boards.find_one({"_id": board_id})
        st.session_state[key_tags] = board.get("tags", [])

    tags_board = st.session_state[key_tags]

    dict_tags = {t["nome"]: t for t in tags_board}

    opcoes_tags = ["+ Nova tag"] + sorted(dict_tags.keys())

    if modo_edicao:
        tags_card = [t["nome"] for t in card.get("tags", [])]
        tags_card = [t for t in tags_card if t in dict_tags]
    else:
        tags_card = []

    tags_selecionadas = st.multiselect(
        "Tags",
        options=opcoes_tags,
        default=tags_card
    )

    ##################################################################################################
    # NOVA TAG
    ##################################################################################################

    if "criar_tag" not in st.session_state:
        st.session_state["criar_tag"] = False

    if "+ Nova tag" in tags_selecionadas:
        st.session_state["criar_tag"] = True

    if st.session_state["criar_tag"]:

        with st.container(border=True):

            with st.container(horizontal=True):

                nome_tag = st.text_input("Nome da tag")
                cor_tag = st.color_picker("Cor", "#007ad3")

            with st.container(horizontal=True):

                if st.button("Salvar tag", width="stretch"):

                    if nome_tag and nome_tag not in dict_tags:

                        nova_tag = {"nome": nome_tag, "cor": cor_tag}

                        kanban_boards.update_one(
                            {"_id": board_id},
                            {"$push": {"tags": nova_tag}}
                        )

                        st.session_state[key_tags].append(nova_tag)
                        st.session_state["criar_tag"] = False

                if st.button("Cancelar", width="stretch"):
                    st.session_state["criar_tag"] = False

    ##################################################################################################
    # SALVAR
    ##################################################################################################

    st.divider()

    if st.button(
        "Salvar alterações" if modo_edicao else "Criar atividade",
        type="primary"
    ):

        lista_responsaveis = [
            dict_pessoas[n] for n in responsaveis
        ]

        tags_validas = [
            t for t in tags_selecionadas if t != "+ Nova tag"
        ]

        lista_tags = [
            dict_tags[n] for n in tags_validas
        ]

        pista_id = dict_pistas[pista_escolhida]

        if modo_edicao:

            if pista_id != card["pista_id"]:
                ordem = kanban_cards.count_documents({
                    "board_id": board_id,
                    "pista_id": pista_id
                })
            else:
                ordem = card["ordem"]

            kanban_cards.update_one(
                {"_id": card["_id"]},
                {
                    "$set": {
                        "atividade": atividade,
                        "descricao_ativ": descricao,
                        "data_fim": data_fim_input.strftime("%d/%m/%Y"),
                        "responsaveis": lista_responsaveis,
                        "tags": lista_tags,
                        "pista_id": pista_id,
                        "ordem": ordem
                    }
                }
            )

        else:

            ordem = kanban_cards.count_documents({
                "board_id": board_id,
                "pista_id": pista_id
            })

            kanban_cards.insert_one({
                "atividade": atividade,
                "descricao_ativ": descricao,
                "criador": id_usuario,
                "data_criacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "data_fim": data_fim_input.strftime("%d/%m/%Y"),
                "responsaveis": lista_responsaveis,
                "tags": lista_tags,
                "board_id": board_id,
                "pista_id": pista_id,
                "ordem": ordem
            })

        # limpa estado
        if key_tags in st.session_state:
            del st.session_state[key_tags]

        st.rerun()







######################################################################################################
# DIÁLOGO DE GERENCIAR BOARD
######################################################################################################

@st.dialog("Gerenciar painel", width="small")
def dialog_gerenciar_board(board_id):

    # Carrega board
    board = kanban_boards.find_one({"_id": board_id})

    ##################################################################################################
    # ABAS
    ##################################################################################################

    tab_painel, tab_colunas, tab_tags = st.tabs(
        ["Painel", "Colunas", "Tags"]
    )


    ######################################################################################################
    # ABA PAINEL
    ######################################################################################################

    with tab_painel:

        st.subheader("Configurações do painel")

        # Nome do board
        nome = st.text_input("Nome do painel", value=board.get("nome", ""))

        ##################################################################################################
        # MEMBROS
        ##################################################################################################

        # Busca pessoas ativas ordenadas alfabeticamente
        pessoas_ativas = list(
            pessoas.find({"status": "ativo"}).sort("nome_completo", 1)
        )

        # Nome -> ID
        dict_pessoas = {
            p["nome_completo"]: p["_id"]
            for p in pessoas_ativas
        }

        # IDs atuais do board
        membros_ids = board.get("membros", [])

        # Converte IDs → nomes (para default do multiselect)
        membros_atuais = [
            nome for nome, _id in dict_pessoas.items()
            if _id in membros_ids
        ]

        membros_selecionados = st.multiselect(
            "Membros do painel",
            options=list(dict_pessoas.keys()),
            default=membros_atuais
        )

        ##################################################################################################
        # SALVAR
        ##################################################################################################

        st.write('')

        if st.button("Salvar alterações", width=200, type="primary", icon=":material/save:"):

            # Converte nomes selecionados → IDs
            lista_membros = [
                dict_pessoas[nome] for nome in membros_selecionados
            ]

            # Garante que o criador continua no board
            if board["criador"] not in lista_membros:
                lista_membros.append(board["criador"])

            kanban_boards.update_one(
                {"_id": board_id},
                {
                    "$set": {
                        "nome": nome,
                        "membros": lista_membros
                    }
                }
            )

            st.rerun()



    ##################################################################################################
    # ABA COLUNAS
    ##################################################################################################

    with tab_colunas:

        st.subheader("Colunas")

        pistas = list(
            kanban_pistas.find({"board_id": board_id}).sort("ordem", 1)
        )

        for pista in pistas:

            with st.container(border=True, horizontal=True):


                # Nome editável
                novo_nome = st.text_input(
                    "Nome",
                    value=pista["nome"],
                    key=f"coluna_nome_{pista['_id']}"
                )

                # Botões

                # Salvar
                if st.button(
                    "",
                    icon=":material/save:",
                    key=f"salvar_coluna_{pista['_id']}"
                ):
                    kanban_pistas.update_one(
                        {"_id": pista["_id"]},
                        {"$set": {"nome": novo_nome}}
                    )
                    st.rerun()


                # Excluir
                if st.button(
                    "",
                    icon=":material/delete:",
                    key=f"delete_coluna_{pista['_id']}"
                ):

                    # Verifica se existem cards na coluna
                    total_cards = kanban_cards.count_documents({
                        "pista_id": pista["_id"]
                    })

                    if total_cards > 0:
                        st.warning("Não é possível excluir uma coluna que possui atividades.")
                    else:
                        kanban_pistas.delete_one({"_id": pista["_id"]})
                        st.rerun()

    ##################################################################################################
    # ABA TAGS
    ##################################################################################################

    with tab_tags:

        st.subheader("Tags")

        tags = board.get("tags", [])


        # Selecionar a ação
        acao_escolhida = st.radio(
            "O que deseja fazer?",
            [
                "Adicionar tag",
                "Editar tags",
            ],
            horizontal=True
        )

        if acao_escolhida == "Adicionar tag":

            ##################################################################################################
            # NOVA TAG
            ##################################################################################################

            st.subheader("Nova tag")

            with st.container(horizontal=True):

                nome_nova = st.text_input("Nome da nova tag")
                cor_nova = st.color_picker("Cor", "#007ad3")

            st.write('')

            if st.button("Adicionar tag", width=200, type="primary", icon=":material/add:"):

                if nome_nova != "":

                    nova_tag = {
                        "nome": nome_nova,
                        "cor": cor_nova
                    }

                    kanban_boards.update_one(
                        {"_id": board_id},
                        {"$push": {"tags": nova_tag}}
                    )

                    st.rerun()


        elif acao_escolhida == "Editar tags":



            # LISTA DE TAGS
            for idx, tag in enumerate(tags):

                with st.container(border=True):

                    with st.container(horizontal=True): 

                        nome_tag = st.text_input(
                            "Nome",
                            value=tag["nome"],
                            key=f"tag_nome_{idx}"
                        )

                        cor_tag = st.color_picker(
                            "Cor",
                            value=tag["cor"],
                            key=f"tag_cor_{idx}"
                        )



                        # Salvar alteração
                        if st.button(
                            "",
                            icon=":material/save:",
                            key=f"salvar_tag_{idx}"
                        ):

                            tag_antiga = tags[idx].copy()

                            tags[idx]["nome"] = nome_tag
                            tags[idx]["cor"] = cor_tag

                            # Atualiza board
                            kanban_boards.update_one(
                                {"_id": board_id},
                                {"$set": {"tags": tags}}
                            )

                            # Atualiza TODOS os cards que usam essa tag
                            kanban_cards.update_many(
                                {
                                    "board_id": board_id,
                                    "tags.nome": tag_antiga["nome"]
                                },
                                {
                                    "$set": {
                                        "tags.$.nome": nome_tag,
                                        "tags.$.cor": cor_tag
                                    }
                                }
                            )

                            st.rerun()



                        # Excluir tag
                        if st.button(
                            "",
                            icon=":material/delete:",
                            key=f"delete_tag_{idx}"
                        ):

                            tag_remover = tags[idx]["nome"]

                            tags.pop(idx)

                            # Atualiza board
                            kanban_boards.update_one(
                                {"_id": board_id},
                                {"$set": {"tags": tags}}
                            )

                            # Remove tag dos cards
                            kanban_cards.update_many(
                                {"board_id": board_id},
                                {
                                    "$pull": {
                                        "tags": {"nome": tag_remover}
                                    }
                                }
                            )

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

    if st.button(
        "Configurações", icon=":material/settings:", type="secondary", width=200):
        dialog_gerenciar_board(board_id)

    if st.button("Nova coluna", icon=":material/add_column_right:", width=200):
        dialog_criar_pista(board_id)

    if st.button("Nova Atividade", icon=":material/assignment_turned_in:", type="primary", width=200):
        dialog_card(board_id)

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
                                        font-weight:bold;
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
                                dialog_card(board_id, card)


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












