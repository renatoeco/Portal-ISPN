import streamlit as st
import pandas as pd
from funcoes_auxiliares import conectar_mongo_portal_ispn
from datetime import datetime
import time
from bson import ObjectId
import streamlit_antd_components as sac
from st_rsuite import date_picker

# ##################################################################
# CONFIGURAÇÕES DA INTERFACE
# ##################################################################

st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Insumos")
st.write('')

# ##################################################################
# CONEXÃO COM O BANCO DE DADOS MONGO
# ##################################################################

# BANCO DE DADOS ISPN HUB
db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas
insumos = db["insumos"]
projetos_ispn = db["projetos_ispn"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################

PAGINA_ID = "pagina_insumos"
nome_pagina = "Insumos"

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


###########################################################################################################
# FUNÇÕES AUXILIARES
###########################################################################################################

PERFIS_COM_ACESSO_CRUD = ["admin", "coordenador(a)"]


def usuario_tem_acesso_crud():
    """Verifica se o usuário logado possui um dos perfis autorizados a gerenciar
    as perguntas personalizadas."""
    tipos_usuario = st.session_state.get("tipo_usuario", [])
    if isinstance(tipos_usuario, str):
        tipos_usuario = [tipos_usuario]
    return any(tipo in PERFIS_COM_ACESSO_CRUD for tipo in tipos_usuario)


def obter_rotulo_projeto(projeto):
    """Retorna o rótulo de exibição do projeto: sigla > código > nome."""
    return projeto.get("sigla") or projeto.get("codigo") or projeto.get("nome_do_projeto") or "Sem identificação"


@st.cache_data(ttl=300)
def carregar_projetos():
    """Carrega a lista de projetos (id, sigla, código, nome e perguntas personalizadas),
    já ordenada alfabeticamente pelo rótulo de exibição (sigla > código > nome)."""
    projetos = list(
        projetos_ispn.find(
            {},
            {"nome_do_projeto": 1, "sigla": 1, "codigo": 1, "perguntas_personalizadas_insumos": 1}
        )
    )
    projetos.sort(key=lambda p: obter_rotulo_projeto(p).lower())
    return projetos


def obter_projeto_por_id(projeto_id):
    return projetos_ispn.find_one({"_id": ObjectId(projeto_id)})


def montar_dict_nomes_projetos(projetos):
    """Monta um dicionário {id_str: rótulo} a partir da lista de projetos já carregada."""
    return {str(p["_id"]): obter_rotulo_projeto(p) for p in projetos}


def obter_nome_projeto_por_id(projeto_id, projetos_dict):
    """Resolve o nome/rótulo do projeto a partir do seu id, usando o dicionário
    em cache; se não encontrar (ex.: cache desatualizado), busca direto no banco."""
    if not projeto_id:
        return "—"
    nome = projetos_dict.get(str(projeto_id))
    if nome:
        return nome
    projeto = obter_projeto_por_id(projeto_id)
    return obter_rotulo_projeto(projeto) if projeto else "—"


def carregar_solicitacoes():
    """Carrega todas as solicitações de insumos."""
    solicitacoes = list(insumos.find({}).sort("data_solicitacao", -1))
    return solicitacoes


def parse_data_solicitacao(valor):
    """Converte a string 'dd/mm/aaaa' de data_solicitacao em um objeto date.
    Retorna None se o valor estiver ausente ou for inválido."""
    try:
        return datetime.strptime(valor, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def filtrar_solicitacoes_por_data(solicitacoes, data_inicio, data_fim):
    """Filtra a lista de solicitações pelo intervalo [data_inicio, data_fim],
    com base no campo 'data_solicitacao'. Solicitações com data inválida/ausente
    são descartadas quando um filtro está ativo."""
    if not data_inicio or not data_fim:
        return solicitacoes

    filtradas = []
    for solicitacao in solicitacoes:
        data = parse_data_solicitacao(solicitacao.get("data_solicitacao"))
        if data and data_inicio <= data <= data_fim:
            filtradas.append(solicitacao)
    return filtradas


def numerar_itens(df_itens):
    """Recebe um DataFrame de itens (sem a coluna 'Item'), filtra as linhas
    preenchidas e retorna a lista de registros já numerada em ordem (campo 'Item')."""
    itens_preenchidos = df_itens[
        df_itens["Descrição Material/ Equipamento/ Insumo"].astype(str).str.strip().ne("")
    ].reset_index(drop=True)

    registros = []
    for i, linha in itens_preenchidos.iterrows():
        registro = {"Item": i + 1}
        registro.update(linha.to_dict())
        registros.append(registro)

    return registros


###########################################################################################################
# DIÁLOGO DE DETALHES DA SOLICITAÇÃO
###########################################################################################################

@st.dialog("Detalhes da Solicitação", width="large")
def dialog_detalhes(solicitacao, projetos, projetos_dict):

    with st.container(horizontal=True, horizontal_alignment="right"):
    
        editar = st.toggle("Editar", key=f"insumos_toggle_editar_{solicitacao['_id']}")

    st.write("")
    
    # -------------------- MODO VISUALIZAÇÃO --------------------
    if not editar:
    
        if solicitacao.get("pergunta_personalizada"):
            col1, col2, col3 = st.columns(3)
            
            nome_projeto = obter_nome_projeto_por_id(solicitacao.get("projeto_id"), projetos_dict)
            col1.write(f"**Projeto:** {nome_projeto}")
            
            col2.markdown(f"**Pergunta Personalizada:** {solicitacao['pergunta_personalizada']}")
        
        else:
            nome_projeto = obter_nome_projeto_por_id(solicitacao.get("projeto_id"), projetos_dict)
            st.write(f"**Projeto:** {nome_projeto}")
    
        
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Responsável:** {solicitacao.get('nome_responsavel', '—')}")
        col2.markdown(f"**Data da Solicitação:** {solicitacao.get('data_solicitacao', '—')}")
        col3.markdown(f"**Data Prevista/Desejada de Entrega:** {solicitacao.get('data_prevista_entrega', '—')}")

        

        st.divider()

        comunidade = solicitacao.get("identificacao_comunidade", {})
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Terra Indígena (TI):** {comunidade.get('terra_indigena') or '—'}")
        col2.markdown(f"**Nome da Aldeia:** {comunidade.get('nome_aldeia') or '—'}")
        col3.markdown(f"**Nome do Grupo/Coletivo:** {comunidade.get('nome_grupo_coletivo') or '—'}")
        col1.markdown(f"**Atividade Produtiva Principal:** {comunidade.get('atividade_produtiva_principal') or '—'}")
        col2.markdown(f"**Nome do responsável do grupo:** {comunidade.get('nome_responsavel_grupo') or '—'}")
        col3.markdown(f"**Nº de Famílias Atendidas:** {comunidade.get('numero_familias_atendidas') or '—'}")

        st.divider()

        st.write(f"**Justificativa:** {solicitacao.get("justificativa_objetivos", "—")}")

        st.divider()

        itens = solicitacao.get("itens_demandados", [])
        if itens:
            df_itens = pd.DataFrame(itens)
            # Garante que a coluna "Item" (quando existir) apareça primeiro
            if "Item" in df_itens.columns:
                colunas = ["Item"] + [c for c in df_itens.columns if c != "Item"]
                df_itens = df_itens[colunas]
            st.dataframe(df_itens, hide_index=True, width="stretch")
        else:
            st.write("Nenhum item cadastrado.")

    else:

        # -------------------- MODO EDIÇÃO --------------------
        opcoes_projetos = {str(p["_id"]): obter_rotulo_projeto(p) for p in projetos}
        ids_projetos = list(opcoes_projetos.keys())
        projeto_id_atual = str(solicitacao.get("projeto_id"))
        indice_projeto_atual = ids_projetos.index(projeto_id_atual) if projeto_id_atual in ids_projetos else None

        # Perguntas personalizadas cadastradas para o projeto atual da solicitação.
        # Como o selectbox de projeto fica dentro do form (só reage ao submit),
        # a lista de perguntas exibida aqui é a do projeto já vinculado à
        # solicitação; se o projeto for trocado, a pergunta deve ser conferida
        # novamente após salvar.
        projeto_atual_obj = next((p for p in projetos if str(p["_id"]) == projeto_id_atual), None)
        opcoes_perguntas_editar = sorted(
            (projeto_atual_obj or {}).get("perguntas_personalizadas_insumos", []), key=str.lower
        )
        pergunta_atual = solicitacao.get("pergunta_personalizada")

        with st.form(f"insumos_form_editar_{solicitacao['_id']}", border=False):

            projeto_id_editado = st.selectbox(
                "Projeto*",
                options=ids_projetos,
                format_func=lambda x: opcoes_projetos.get(x, x),
                index=indice_projeto_atual,
                key=f"insumos_editar_projeto_{solicitacao['_id']}"
            )

            if opcoes_perguntas_editar:
                indice_pergunta_atual = (
                    opcoes_perguntas_editar.index(pergunta_atual)
                    if pergunta_atual in opcoes_perguntas_editar else None
                )
                pergunta_personalizada_editada = st.selectbox(
                    "Pergunta Personalizada do Projeto",
                    options=opcoes_perguntas_editar,
                    index=indice_pergunta_atual,
                    placeholder="Selecione uma pergunta personalizada",
                    key=f"insumos_editar_pergunta_{solicitacao['_id']}"
                )
            else:
                pergunta_personalizada_editada = pergunta_atual
                st.caption(
                    f"Pergunta Personalizada: {pergunta_atual}" if pergunta_atual
                    else "Este projeto não possui perguntas personalizadas cadastradas."
                )

            data_prevista_atual = solicitacao.get("data_prevista_entrega", "")
            try:
                valor_data_prevista = datetime.strptime(data_prevista_atual, "%d/%m/%Y").date()
            except (ValueError, TypeError):
                valor_data_prevista = None

            data_prevista_editada = st.date_input(
                "Data Prevista/Desejada para Entrega*",
                value=valor_data_prevista,
                format="DD/MM/YYYY",
                key=f"insumos_editar_data_prevista_{solicitacao['_id']}"
            )

            st.write("")

            comunidade = solicitacao.get("identificacao_comunidade", {})
            col1, col2 = st.columns(2)
            terra_indigena_editada = col1.text_input(
                "Terra Indígena (TI)", value=comunidade.get("terra_indigena", ""),
                key=f"insumos_editar_ti_{solicitacao['_id']}"
            )
            nome_aldeia_editada = col2.text_input(
                "Nome da Aldeia", value=comunidade.get("nome_aldeia", ""),
                key=f"insumos_editar_aldeia_{solicitacao['_id']}"
            )

            col1, col2 = st.columns(2)
            nome_grupo_coletivo_editado = col1.text_input(
                "Nome do Grupo/Coletivo", value=comunidade.get("nome_grupo_coletivo", ""),
                key=f"insumos_editar_grupo_{solicitacao['_id']}"
            )
            atividade_produtiva_editada = col2.text_input(
                "Atividade Produtiva Principal", value=comunidade.get("atividade_produtiva_principal", ""),
                key=f"insumos_editar_atividade_{solicitacao['_id']}"
            )

            col1, col2 = st.columns(2)
            nome_responsavel_grupo_editado = col1.text_input(
                "Nome do responsável do grupo", value=comunidade.get("nome_responsavel_grupo", ""),
                key=f"insumos_editar_resp_grupo_{solicitacao['_id']}"
            )
            numero_familias_editado = col2.text_input(
                "Nº de Famílias Atendidas diretamente", value=comunidade.get("numero_familias_atendidas", ""),
                key=f"insumos_editar_familias_{solicitacao['_id']}"
            )

            st.write("")
            justificativa_editada = st.text_area(
                "Descreva de forma sucinta qual a finalidade deste fomento*",
                value=solicitacao.get("justificativa_objetivos", ""),
                key=f"insumos_editar_justificativa_{solicitacao['_id']}"
            )

            st.write("")

            itens_atuais = solicitacao.get("itens_demandados", [])
            df_itens_atual = pd.DataFrame(itens_atuais) if itens_atuais else pd.DataFrame(
                columns=["Descrição Material/ Equipamento/ Insumo", "Unidade", "Quantidade"]
            )
            if "Item" in df_itens_atual.columns:
                df_itens_atual = df_itens_atual.drop(columns=["Item"])
            for coluna in ["Descrição Material/ Equipamento/ Insumo", "Unidade", "Quantidade"]:
                if coluna not in df_itens_atual.columns:
                    df_itens_atual[coluna] = None

            df_itens_editados = st.data_editor(
                df_itens_atual,
                num_rows="dynamic",
                hide_index=True,
                width="stretch",
                column_config={
                    "Descrição Material/ Equipamento/ Insumo": st.column_config.TextColumn("Descrição Material/ Equipamento/ Insumo"),
                    "Unidade": st.column_config.TextColumn("Unidade"),
                    "Quantidade": st.column_config.NumberColumn("Quantidade"),
                },
                key=f"insumos_editar_data_editor_{solicitacao['_id']}"
            )

            st.write("")
            salvar = st.form_submit_button("Salvar alterações", type="primary", width="content", icon=":material/save:")

        if salvar:
            erros = []

            if not projeto_id_editado:
                erros.append("Selecione o projeto.")

            if not data_prevista_editada:
                erros.append("Informe a Data Prevista/Desejada para Entrega.")

            if not justificativa_editada or not justificativa_editada.strip():
                erros.append("A Justificativa e Objetivos da Demanda é obrigatória.")

            itens_registrados = numerar_itens(df_itens_editados)
            if not itens_registrados:
                erros.append("Informe ao menos um item na tabela de Especificação dos Itens Demandados.")

            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                insumos.update_one(
                    {"_id": solicitacao["_id"]},
                    {"$set": {
                        "projeto_id": ObjectId(projeto_id_editado),
                        "pergunta_personalizada": pergunta_personalizada_editada,
                        "data_prevista_entrega": data_prevista_editada.strftime("%d/%m/%Y"),
                        "identificacao_comunidade": {
                            "terra_indigena": terra_indigena_editada,
                            "nome_aldeia": nome_aldeia_editada,
                            "nome_grupo_coletivo": nome_grupo_coletivo_editado,
                            "atividade_produtiva_principal": atividade_produtiva_editada,
                            "nome_responsavel_grupo": nome_responsavel_grupo_editado,
                            "numero_familias_atendidas": numero_familias_editado,
                        },
                        "justificativa_objetivos": justificativa_editada,
                        "itens_demandados": itens_registrados,
                    }}
                )
                st.success("Solicitação atualizada com sucesso!", icon=":material/check:")
                time.sleep(2)
                st.rerun()


###########################################################################################################
# ABAS PRINCIPAIS
###########################################################################################################


nomes_abas = [":material/list: Solicitações", ":material/add: Nova Solicitação"]
if usuario_tem_acesso_crud():
    nomes_abas.append(":material/quiz: Perguntas Personalizadas")

abas = st.tabs(nomes_abas)


###########################################################################################################
# ABA 1 — LISTAGEM DE SOLICITAÇÕES
###########################################################################################################

with abas[0]:

    solicitacoes = carregar_solicitacoes()
    projetos_lista = carregar_projetos()
    projetos_dict = montar_dict_nomes_projetos(projetos_lista)

    if not solicitacoes:

        st.write("")
        st.write("")
        st.caption("**Nenhuma solicitação de insumos cadastrada até o momento.**")

    else:

        st.write("")
        st.write("")

        col_filtro, _ = st.columns([2, 3])
        intervalo_data_solicitacao = col_filtro.date_input(
            "Data da Solicitação",
            value=(),
            format="DD/MM/YYYY",
            key="insumos_filtro_data_solicitacao"
        )

        data_inicio_filtro = None
        data_fim_filtro = None
        if isinstance(intervalo_data_solicitacao, tuple) and len(intervalo_data_solicitacao) == 2:
            data_inicio_filtro, data_fim_filtro = intervalo_data_solicitacao

        solicitacoes = filtrar_solicitacoes_por_data(solicitacoes, data_inicio_filtro, data_fim_filtro)

        st.write("")
        st.write("")

        if not solicitacoes:
            st.caption("**Nenhuma solicitação encontrada para o período selecionado.**")
        else:
            col_proj, col_resp, col_data_sol, col_data_ent, col_botao = st.columns([3, 2, 2, 2, 2])
            col_proj.markdown("**Projeto**")
            col_resp.markdown("**Responsável**")
            col_data_sol.markdown("**Data da Solicitação**")
            col_data_ent.markdown("**Data Prevista de Entrega**")
            col_botao.markdown("")

            st.divider()

            for solicitacao in solicitacoes:
                col_proj, col_resp, col_data_sol, col_data_ent, col_botao = st.columns([3, 2, 2, 2, 2])
                col_proj.write(obter_nome_projeto_por_id(solicitacao.get("projeto_id"), projetos_dict))
                col_resp.write(solicitacao.get("nome_responsavel", "—"))
                col_data_sol.write(solicitacao.get("data_solicitacao", "—"))
                col_data_ent.write(solicitacao.get("data_prevista_entrega", "—"))

                if col_botao.button("Detalhes", key=f"detalhes_{solicitacao['_id']}", icon=":material/info:"):
                    dialog_detalhes(solicitacao, projetos_lista, projetos_dict)

                st.divider()


###########################################################################################################
# ABA 2 — FORMULÁRIO DE NOVA SOLICITAÇÃO
###########################################################################################################

with abas[1]:

    st.write("")
    st.write("")

    projetos = carregar_projetos()
    opcoes_projetos = {str(p["_id"]): obter_rotulo_projeto(p) for p in projetos}
    

    st.markdown("##### 1. Identificação Geral")
    st.write("")

    projeto_id_selecionado = st.selectbox(
        "Projeto*",
        options=list(opcoes_projetos.keys()),
        format_func=lambda x: opcoes_projetos.get(x, x),
        index=None,
        placeholder="Selecione o projeto",
        key="insumos_projeto_selecionado"
    )

    # Ao selecionar o projeto, exibe um selectbox com as perguntas personalizadas
    # cadastradas para ele (ordenadas alfabeticamente). Caso o projeto não tenha
    # nenhuma pergunta personalizada cadastrada, apenas um aviso é exibido.
    pergunta_personalizada_selecionada = None
    if projeto_id_selecionado:
        projeto_atual = next((p for p in projetos if str(p["_id"]) == projeto_id_selecionado), None)
        opcoes_perguntas = sorted((projeto_atual or {}).get("perguntas_personalizadas_insumos", []), key=str.lower)

        if opcoes_perguntas:
            pergunta_personalizada_selecionada = st.selectbox(
                "Pergunta Personalizada do Projeto",
                options=opcoes_perguntas,
                index=None,
                placeholder="Selecione uma pergunta personalizada",
                key=f"insumos_pergunta_personalizada_{projeto_id_selecionado}"
            )
        else:
            st.caption("Este projeto ainda não possui perguntas personalizadas cadastradas.")

    st.write("")

    with st.form("form_nova_solicitacao_insumos", clear_on_submit=True, border=False):

        

        nome_responsavel = st.session_state.get("nome", "")
        data_solicitacao = datetime.now().strftime("%d/%m/%Y")

        col1, col2 = st.columns(2)
        col1.text_input("Nome do Responsável pela Solicitação", value=nome_responsavel, disabled=True)
        col2.text_input("Data da Solicitação", value=data_solicitacao, disabled=True)

        data_prevista_entrega = date_picker(
            label="Data Prevista/Desejada para Entrega*",
            format="dd/MM/yyyy",
            locale="pt_BR",
            placeholder="dd/mm/aaaa",
            key="insumos_data_prevista_entrega"
        )

        st.divider()
        st.markdown("##### 2. Identificação da Comunidade Beneficiária")
        st.write("")

        col1, col2 = st.columns(2)
        terra_indigena = col1.text_input("Terra Indígena (TI)", key="insumos_terra_indigena")
        nome_aldeia = col2.text_input("Nome da Aldeia", key="insumos_nome_aldeia")

        col1, col2 = st.columns(2)
        nome_grupo_coletivo = col1.text_input("Nome do Grupo/Coletivo", key="insumos_nome_grupo_coletivo")
        atividade_produtiva_principal = col2.text_input("Atividade Produtiva Principal", key="insumos_atividade_produtiva")

        col1, col2 = st.columns(2)
        nome_responsavel_grupo = col1.text_input("Nome do responsável do grupo", key="insumos_nome_responsavel_grupo")
        numero_familias_atendidas = col2.text_input("Nº de Famílias Atendidas diretamente", key="insumos_numero_familias")
       
        st.divider()
        st.markdown("##### 3. Justificativa e Objetivos da Demanda")
        st.write("")
        
        justificativa_objetivos = st.text_area(
            "Descreva de forma sucinta qual a finalidade deste fomento*",
            key="insumos_justificativa"
        )
        
        st.divider()
        st.markdown("##### 4. Especificação dos Itens Demandados")
        st.write("")

        df_itens_vazio = pd.DataFrame(
            [{"Descrição Material/ Equipamento/ Insumo": "", "Unidade": "", "Quantidade": None} for _ in range(6)]
        )

        # st.data_editor com num_rows="dynamic" funciona normalmente dentro de um
        # st.form: é possível adicionar e remover linhas livremente, e o valor
        # final só é enviado ao script quando o formulário é submetido.
        # A coluna "Item" não é editável pelo usuário: o número é atribuído
        # automaticamente, em ordem, no momento de salvar.
        df_itens = st.data_editor(
            df_itens_vazio,
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            column_config={
                "Descrição Material/ Equipamento/ Insumo": st.column_config.TextColumn("Descrição Material/ Equipamento/ Insumo"),
                "Unidade": st.column_config.TextColumn("Unidade"),
                "Quantidade": st.column_config.NumberColumn("Quantidade"),
            },
            key="insumos_data_editor_itens"
        )

        st.write("")
        enviar = st.form_submit_button("Enviar Solicitação", type="primary", width="content", icon=":material/send:")

    if enviar:
        erros = []

        if not projeto_id_selecionado:
            erros.append("Selecione o projeto.")

        if not data_prevista_entrega:
            erros.append("Informe a Data Prevista/Desejada para Entrega.")

        if not justificativa_objetivos or not justificativa_objetivos.strip():
            erros.append("A Justificativa e Objetivos da Demanda é obrigatória.")

        itens_registrados = numerar_itens(df_itens)
        if not itens_registrados:
            erros.append("Informe ao menos um item na tabela de Especificação dos Itens Demandados.")

        if erros:
            for erro in erros:
                st.error(erro)
        else:
            novo_documento = {
                "projeto_id": ObjectId(projeto_id_selecionado),
                "pergunta_personalizada": pergunta_personalizada_selecionada,
                "nome_responsavel": nome_responsavel,
                "data_solicitacao": data_solicitacao,
                "data_prevista_entrega": data_prevista_entrega.strftime("%d/%m/%Y"),
                "identificacao_comunidade": {
                    "terra_indigena": terra_indigena,
                    "nome_aldeia": nome_aldeia,
                    "nome_grupo_coletivo": nome_grupo_coletivo,
                    "atividade_produtiva_principal": atividade_produtiva_principal,
                    "nome_responsavel_grupo": nome_responsavel_grupo,
                    "numero_familias_atendidas": numero_familias_atendidas,
                },
                "justificativa_objetivos": justificativa_objetivos,
                "itens_demandados": itens_registrados,
                "status": "Pendente",
            }

            insumos.insert_one(novo_documento)
            st.success("Solicitação enviada com sucesso!", icon=":material/check:")
            time.sleep(2)
            st.rerun()


###########################################################################################################
# ABA 3 — CRUD DE PERGUNTAS PERSONALIZADAS (restrita a admin e coordenador(a))
###########################################################################################################

if usuario_tem_acesso_crud():
    with abas[2]:

        st.write("")
        st.write("")

        projetos_crud = carregar_projetos()
        opcoes_projetos_crud = {str(p["_id"]): obter_rotulo_projeto(p) for p in projetos_crud}

        projeto_id_crud = st.selectbox(
            "Projeto",
            options=list(opcoes_projetos_crud.keys()),
            format_func=lambda x: opcoes_projetos_crud.get(x, x),
            index=None,
            placeholder="Selecione o projeto para gerenciar as perguntas",
            key="crud_projeto_selecionado"
        )

        if projeto_id_crud:
            projeto_crud = obter_projeto_por_id(projeto_id_crud)
            perguntas_atuais = sorted(projeto_crud.get("perguntas_personalizadas_insumos", []), key=str.lower)

            st.write("")
            st.markdown("**Perguntas cadastradas**")

            if not perguntas_atuais:
                st.caption("Este projeto ainda não possui nenhuma pergunta personalizada. Adicione a primeira na tabela abaixo.")

            # A coluna precisa ser criada explicitamente com dtype "string" (mesmo
            # quando a lista de perguntas está vazia). Sem isso, uma coluna vazia é
            # inferida pelo pandas como float64, o que quebra a edição com
            # TextColumn ao tentar adicionar a primeira linha.
            df_perguntas = pd.DataFrame({"Pergunta": pd.array(perguntas_atuais, dtype="string")})

            df_perguntas_editado = st.data_editor(
                df_perguntas,
                num_rows="dynamic",
                hide_index=True,
                width="stretch",
                column_config={
                    "Pergunta": st.column_config.TextColumn("Pergunta", width="large"),
                },
                key=f"crud_data_editor_{projeto_id_crud}"
            )

            if st.button("Salvar perguntas", type="primary", icon=":material/save:"):
                novas_perguntas = sorted(
                    {
                        p.strip() for p in df_perguntas_editado["Pergunta"].tolist()
                        if isinstance(p, str) and p.strip()
                    },
                    key=str.lower
                )

                projetos_ispn.update_one(
                    {"_id": ObjectId(projeto_id_crud)},
                    {"$set": {"perguntas_personalizadas_insumos": novas_perguntas}}
                )
                
                st.success("Perguntas personalizadas atualizadas com sucesso!", icon=":material/check:")
                time.sleep(2)
                st.cache_data.clear()
                st.rerun()