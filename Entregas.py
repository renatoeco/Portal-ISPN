import streamlit as st
import pandas as pd
from datetime import datetime
from bson import ObjectId
from funcoes_auxiliares import conectar_mongo_portal_ispn, dialog_editar_entregas, altura_dataframe, formatar_nome_legivel
# import streamlit_shadcn_ui as ui
import plotly.express as px
import time
import bson




###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS E CARREGAMENTO
###########################################################################################################


db = conectar_mongo_portal_ispn()
# estrategia = db["estrategia"]  
programas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"]  
indicadores = db["indicadores"]
estatistica = db["estatistica"] 
colecao_lancamentos = db["lancamentos_indicadores"]


# --------------------------------------------------
# ESTADOS DO DIÁLOGO DE REGISTRO DE ENTREGAS
# --------------------------------------------------
if "entrega_selecionada" not in st.session_state:
    st.session_state["entrega_selecionada"] = None

if "entrega_selecionada_tabela_key" not in st.session_state:
    st.session_state["entrega_selecionada_tabela_key"] = None

if "entrega" not in st.session_state:
    st.session_state["entrega"] = False
    
# Mapa id_indicador -> nome
df_indicadores = pd.DataFrame(list(indicadores.find({}, {"nome_indicador": 1})))
df_indicadores["_id"] = df_indicadores["_id"].astype(str)

mapa_indicadores = dict(
    zip(df_indicadores["_id"], df_indicadores["nome_indicador"])
)


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_entregas"
nome_pagina = "Entregas"
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


# ##########################################################
# Funções
# ##########################################################


# Função para renderizar o formulário de novo registro dentro do diálogo de acompanhamento de entrega
@st.fragment
def renderizar_novo_registro(idx):

    st.write("")

    entrega_ctx = st.session_state.get("entrega_selecionada")

    projeto_info = projetos_ispn.find_one(
        {"_id": ObjectId(entrega_ctx["projeto_id"])}
    )

    entregas_existentes = projeto_info.get("entregas", [])
    
    entrega_id = entrega_ctx["entrega_id"]

    entrega = next(
        e for e in entregas_existentes
        if e["_id"] == ObjectId(entrega_id)
    )

    ano_atual = datetime.now().year
    ano_inicial = ano_atual - 1
    ano_final = ano_atual + 6

    anos_disponiveis = list(range(ano_inicial, ano_final + 1))

    # =========================
    # Dados do lançamento
    # =========================

    ano_lancamento = st.selectbox(
        "Ano do registro",
        options=anos_disponiveis,
        index=anos_disponiveis.index(ano_atual) 
    )

    anotacoes_lancamento = st.text_area(
        "Anotações",
        placeholder=""
    )

    st.divider()

    # =========================
    # Lançamentos de indicadores
    # =========================
    st.markdown("### Lançamento de indicadores")
    
    st.write("")

    valores_indicadores = {}

    indicadores_entrega = entrega.get("indicadores_relacionados", [])
    
    # Garantir que todos os IDs sejam string
    indicadores_entrega = [
        str(i) if not isinstance(i, str) else i
        for i in indicadores_entrega
    ]


    for indicador_id in indicadores_entrega:

        indicadores_float = [
            "Área com manejo ecológico do fogo (ha)",
            "Área com manejo agroecológico (ha)",
            "Área com manejo para restauração (ha)",
            "Área com manejo para extrativismo (ha)",
            "Faturamento bruto anual pré-projeto",
            "Faturamento bruto anual pós-projeto",
            "Volume financeiro de vendas institucionais com apoio do Fundo Ecos",
            "Valor da contrapartida financeira projetinhos",
            "Valor da contrapartida não financeira projetinhos",
            "Valor mobilizado de novos recursos"
        ]
        indicador_texto = "Espécies"

        nome_indicador = mapa_indicadores.get(
            indicador_id,
            "Indicador não encontrado"
        )

        nome_legivel = formatar_nome_legivel(nome_indicador)

        st.markdown(f"**{nome_legivel}**")

        col1, col2 = st.columns([2, 3])

        key_base = f"{idx}_{indicador_id}"

        if nome_legivel in indicadores_float:
            valor = col1.number_input(
                "Valor",
                step=0.01,
                key=f"valor_{key_base}"
            )

        elif nome_legivel == indicador_texto:
            valor = col1.text_input(
                "Valor",
                key=f"valor_{key_base}"
            )

        else:
            valor = col1.number_input(
                "Valor",
                step=1,
                key=f"valor_{key_base}"
            )

        observacoes = col2.text_input(
            "Observações",
            key=f"obs_{key_base}"
        )

        valores_indicadores[indicador_id] = {
            "valor": valor,
            "observacoes": observacoes
        }

        st.divider()

    # =========================
    # SALVAR
    # =========================
    if st.button("Salvar lançamento", icon=":material/save:"):

        if not ano_lancamento:
            st.warning("Informe o ano do lançamento.")
            st.stop()

        # -------------------------
        # 1. Salvar lançamento da entrega
        # -------------------------
        novo_lancamento_entrega = {
            "_id": ObjectId(),
            "ano": str(ano_lancamento),
            "anotacoes": anotacoes_lancamento,
            "autor": st.session_state.get("nome")
        }
        
        id_lanc_entrega = novo_lancamento_entrega["_id"]

        for e in entregas_existentes:
            if e["_id"] == ObjectId(entrega_id):
                e.setdefault("lancamentos_entregas", []).append(novo_lancamento_entrega)
                break

        projetos_ispn.update_one(
            {"_id": projeto_info["_id"]},
            {"$set": {"entregas": entregas_existentes}}
        )

        # -------------------------
        # 2. Salvar lançamentos de indicadores
        # -------------------------
        for indicador_id, dados in valores_indicadores.items():

            if dados["valor"] in ["", None] or dados["valor"] == 0:
                continue

            nome_indicador = mapa_indicadores.get(str(indicador_id), "")
            nome_legivel = formatar_nome_legivel(nome_indicador)

            if nome_legivel in indicadores_float:
                valor_final = float(dados["valor"])
            elif nome_legivel == indicador_texto:
                valor_final = str(dados["valor"])
            else:
                valor_final = int(dados["valor"])

            lancamento_indicador = {
                "id_do_indicador": ObjectId(indicador_id),
                "projeto": projeto_info["_id"],
                "data_anotacao": datetime.now(),
                "autor_anotacao": st.session_state.get("nome"),
                "valor": valor_final,
                "ano": str(ano_lancamento),
                "observacoes": dados["observacoes"],
                "tipo": "ispn",
                "id_lanc_entrega": id_lanc_entrega
            }

            colecao_lancamentos.insert_one(lancamento_indicador)

        st.success("Lançamento salvo com sucesso!")
        time.sleep(2)
        st.rerun()


@st.dialog("Acompanhamento de Entrega", width="large")
def dialog_registros_entregas():

    entrega_ctx = st.session_state.get("entrega_selecionada")

    if not entrega_ctx:
        st.warning("Entrega inválida.")
        return

    idx = entrega_ctx.get("indice")
    projeto_id = entrega_ctx.get("projeto_id")

    projeto_info = projetos_ispn.find_one(
        {"_id": ObjectId(projeto_id)}
    )

    if not projeto_info:
        st.error("Projeto não encontrado.")
        return


    if idx is None:
        st.warning("Entrega inválida.")
        return

    # ===============================
    # Dados da entrega
    # ===============================
    nome_entrega = entrega_ctx.get("entrega", "Entrega")
    situacao = df_entregas.loc[idx, "situacao"]

    progresso = df_entregas.loc[idx, "progresso"]
    try:
        progresso = int(progresso)
    except (TypeError, ValueError):
        progresso = 0

    previsao_str = df_entregas.loc[idx, "previsao_da_conclusao_str"]
    responsaveis = df_entregas.loc[idx, "responsaveis"]
    responsaveis_ids = df_entregas.loc[idx, "responsaveis_ids"]

    # ===============================
    # Cabeçalho
    # ===============================
    st.markdown(f"## {nome_entrega}")
    st.write("")

    col1, col2, col3, col4 = st.columns([1, 1, 1.5, 2.5])

    usuarios_coordenadores = set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}





    # ==========================================================
    # Usuários coordenadores (edição habilitada)
    # ==========================================================
    if usuarios_coordenadores:

        situacoes = ["Prevista", "Atrasada", "Concluída"]
        with col1:
            st.selectbox(
                "Situação:",
                options=situacoes,
                index=situacoes.index(situacao) if situacao in situacoes else 0,
                key=f"entrega_situacao_{idx}"
            )

        opcoes_progresso = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        with col2:
            st.selectbox(
                "Progresso:",
                options=opcoes_progresso,
                index=opcoes_progresso.index(progresso) if progresso in opcoes_progresso else 0,
                format_func=lambda x: f"{x}%",
                key=f"entrega_progresso_{idx}"
            )

        data_previsao = None
        if previsao_str:
            try:
                data_previsao = datetime.strptime(previsao_str, "%d/%m/%Y").date()
            except ValueError:
                pass

        with col3:
            st.date_input(
                "Previsão de Conclusão:",
                value=data_previsao,
                format="DD/MM/YYYY",
                key=f"entrega_previsao_{idx}"
            )

        pessoas = list(db["pessoas"].find({}, {"nome_completo": 1}))
        mapa_pessoas = {
            str(p["_id"]): p["nome_completo"]
            for p in sorted(pessoas, key=lambda x: x["nome_completo"])
        }

        with col4:
            st.multiselect(
                "Responsáveis:",
                options=list(mapa_pessoas.keys()),
                default=[str(r) for r in responsaveis_ids],
                format_func=lambda x: mapa_pessoas.get(x, x),
                key=f"entrega_responsaveis_{idx}"
            )

        # st.write("")
        with st.container(horizontal_alignment="right"):
            if st.button("Salvar alterações", icon=":material/save:", width=250):

                nova_situacao = st.session_state[f"entrega_situacao_{idx}"]
                novo_progresso = st.session_state[f"entrega_progresso_{idx}"]
                nova_data = st.session_state[f"entrega_previsao_{idx}"]
                novos_responsaveis = st.session_state[f"entrega_responsaveis_{idx}"]

                nova_data_str = nova_data.strftime("%d/%m/%Y") if nova_data else None

                projetos_ispn.update_one(
                    {"entregas.nome_da_entrega": nome_entrega},
                    {
                        "$set": {
                            "entregas.$.situacao": nova_situacao,
                            "entregas.$.progresso": novo_progresso,
                            "entregas.$.previsao_da_conclusao": nova_data_str,
                            "entregas.$.responsaveis": [ObjectId(r) for r in novos_responsaveis],
                        }
                    }
                )

                df_entregas.at[idx, "situacao"] = nova_situacao
                df_entregas.at[idx, "progresso"] = novo_progresso
                df_entregas.at[idx, "previsao_da_conclusao_str"] = nova_data_str
                df_entregas.at[idx, "responsaveis_ids"] = novos_responsaveis
                df_entregas.at[idx, "responsaveis"] = ", ".join(
                    mapa_pessoas[str(r)]
                    for r in novos_responsaveis
                    if str(r) in mapa_pessoas
                )

                st.success("Alterações salvas com sucesso.")
                time.sleep(3)
                st.rerun()




    # ==========================================================
    # Usuários comuns (somente leitura)
    # ==========================================================

    else:
        with col1:
            st.write(f"**Situação:** {situacao}")
        with col2:
            st.write(f"**Progresso:** {progresso}%")
        with col3:
            st.write(f"**Previsão de Conclusão:** {previsao_str}")
        with col4:
            st.write(f"**Responsáveis:** {responsaveis}")

    # ================================================================================================
    # Registros de entrega
    # ================================================================================================

    st.markdown("### Registros de entrega")

    tab_ver_registros, tab_novo_registro = st.tabs(["Ver registros", "Novo registro"])

    if "editar_lancamento_id" not in st.session_state:
        st.session_state["editar_lancamento_id"] = None

    # Aba de listagem dos registros de entrega
    with tab_ver_registros:

        # Define espaçamentos das colunas UMA VEZ
        colunas = [1, 1, 2, 2, 1]

        lancamentos = df_entregas.loc[idx, "lancamentos_entregas"]

        if not lancamentos:
            st.caption("Nenhum registro nesta entrega.")
        else:

            # --------------------------------
            # Cabeçalho das colunas
            # --------------------------------
            col1, col2, col3, col4, col5 = st.columns(colunas)

            with col1:
                st.markdown("**Ano**")
            with col2:
                st.markdown("**Autor(a)**")
            with col3:
                st.markdown("**Anotações**")
            with col4:
                st.markdown("**Indicadores**")
            with col5:
                st.markdown("")
       
            st.divider()

            # --------------------------------
            # Registros
            # --------------------------------
            for lancamento in lancamentos:
                col1, col2, col3, col4, col5 = st.columns(colunas)

                with col1:
                    st.write(lancamento.get("ano", ""))

                with col2:
                    st.write(lancamento.get("autor", ""))

                with col3:
                    st.write(lancamento.get("anotacoes", ""))

                with col4:
                    with st.popover("Indicadores", type="tertiary"):

                        id_lanc_entrega = lancamento.get("_id")

                        if not id_lanc_entrega:
                            st.caption("Sem indicadores associados.")
                        else:
                            registros_indicadores = list(
                                colecao_lancamentos.find(
                                    {"id_lanc_entrega": ObjectId(id_lanc_entrega)}
                                )
                            )

                            if not registros_indicadores:
                                st.caption("Nenhum indicador lançado.")
                            else:
                                for reg in registros_indicadores:

                                    nome_indicador = mapa_indicadores.get(
                                        str(reg["id_do_indicador"]),
                                        "Indicador não encontrado"
                                    )

                                    st.markdown(f"**{formatar_nome_legivel(nome_indicador)}:** {reg.get('valor')}")
                                    
                                    st.write("")

                with col5:
                    editar = st.toggle(
                        ":material/edit: Editar",
                        value=st.session_state["editar_lancamento_id"] == str(lancamento["_id"]),
                        key=f"toggle_editar_lanc_{lancamento['_id']}"
                    )

                    if editar:
                        st.session_state["editar_lancamento_id"] = str(lancamento["_id"])
                    elif st.session_state["editar_lancamento_id"] == str(lancamento["_id"]):
                        st.session_state["editar_lancamento_id"] = None

                if st.session_state["editar_lancamento_id"] == str(lancamento["_id"]):

                    with st.container(border=True):

                        st.markdown("**Editar registro**")

                        with st.form(f"form_editar_lanc_{lancamento['_id']}", border=False):

                            ano_atual = datetime.now().year
                            ano_inicial = ano_atual - 1
                            ano_final = ano_atual + 6

                            anos_disponiveis = list(range(ano_inicial, ano_final + 1))

                            ano_lancamento = lancamento.get("ano")

                            try:
                                index_ano = anos_disponiveis.index(int(ano_lancamento))
                            except (ValueError, TypeError):
                                index_ano = 0

                            ano = st.selectbox(
                                "Ano do registro",
                                options=anos_disponiveis,
                                index=index_ano
                            )

                            anotacoes = st.text_area(
                                "Anotações",
                                value=lancamento.get("anotacoes", ""),
                                height=120
                            )

                            #col_a, col_b = st.columns(2)
                            with st.container(border=False, horizontal=True):
                                
                                salvar = st.form_submit_button(
                                    "Salvar",
                                    type="primary",
                                    icon=":material/save:"
                                )

                        if salvar:
                            projetos_ispn.update_one(
                                {"entregas.lancamentos_entregas._id": ObjectId(lancamento["_id"])},
                                {
                                    "$set": {
                                        "entregas.$[].lancamentos_entregas.$[l].ano":  str(ano),
                                        "entregas.$[].lancamentos_entregas.$[l].anotacoes": anotacoes
                                    }
                                },
                                array_filters=[{"l._id": ObjectId(lancamento["_id"])}]
                            )

                            # Atualiza o dataframe local
                            lancamento["ano"] = ano
                            lancamento["anotacoes"] = anotacoes

                            st.success("Registro atualizado com sucesso.")
                            st.session_state["editar_lancamento_id"] = None
                            time.sleep(2)
                            st.rerun()

                st.divider()

    with tab_novo_registro:

        renderizar_novo_registro(idx)


def resolver_responsaveis(lista_ids, pessoas_dict):
    nomes = []
    for rid in lista_ids:
        rid = ObjectId(rid)
        if rid in pessoas_dict:
            nomes.append(pessoas_dict[rid])
    return ", ".join(nomes)


def carregar_entregas():
    """
    Retorna DataFrame com TODAS as entregas,
    já resolvendo responsáveis e programa
    """
    pessoas = {
        p["_id"]: p["nome_completo"]
        for p in db["pessoas"].find({}, {"nome_completo": 1})
    }

    programas_dict = {
        p["_id"]: p.get("nome_programa_area", "")
        for p in programas.find({}, {"nome_programa_area": 1})
    }

    registros = []

    for projeto in projetos_ispn.find():
        programa_nome = programas_dict.get(projeto.get("programa"), "")
        nome_projeto = projeto.get("sigla") or projeto.get("sigla", "")

        for entrega in projeto.get("entregas", []):

            data_raw = entrega.get("previsao_da_conclusao")

            if not data_raw:
                continue  # pula entregas sem data

            try:
                data_conclusao = datetime.strptime(data_raw, "%d/%m/%Y")
            except ValueError:
                continue  # pula datas inválidas

            registros.append({
                "projeto_id": projeto["_id"],
                
                "nome_da_entrega": entrega.get("nome_da_entrega"),
                "entrega_id": entrega["_id"],
                
                "sigla": nome_projeto,

                # PARA O GRÁFICO
                "previsao_da_conclusao": data_conclusao,

                # PARA A TABELA (JSON-safe)
                "previsao_da_conclusao_str": data_conclusao.strftime("%d/%m/%Y"),

                "responsaveis": resolver_responsaveis(
                    entrega.get("responsaveis", []),
                    pessoas
                ),
                "situacao": entrega.get("situacao"),
                "anos_de_referencia": ", ".join(entrega.get("anos_de_referencia", [])),
                "programa": programa_nome,
                "responsaveis_ids": [ObjectId(r) for r in entrega.get("responsaveis", [])],

                "lancamentos_entregas": entrega.get("lancamentos_entregas", []),

                "progresso": entrega.get("progresso"),

                "acoes_resultados_medio_prazo": entrega.get("acoes_resultados_medio_prazo", []),
                "resultados_longo_prazo_relacionados": entrega.get("resultados_longo_prazo_relacionados", []),
                "eixos_relacionados": entrega.get("eixos_relacionados", []),
                "acoes_relacionadas": entrega.get("acoes_relacionadas", []),
                "metas_resultados_medio_prazo": entrega.get("metas_resultados_medio_prazo", []),
                "indicadores_relacionados": entrega.get("indicadores_relacionados", []),

            })

        COLUNAS_PADRAO = [
            "projeto_id",
            "nome_da_entrega",
            "entrega_id",
            "sigla",
            "previsao_da_conclusao",
            "previsao_da_conclusao_str",
            "responsaveis",
            "situacao",
            "anos_de_referencia",
            "programa",
            "responsaveis_ids",
            "lancamentos_entregas",
            "progresso",
            "acoes_resultados_medio_prazo",
            "resultados_longo_prazo_relacionados",
            "eixos_relacionados",
            "acoes_relacionadas",
            "metas_resultados_medio_prazo",
            "indicadores_relacionados",

        ]

    df = pd.DataFrame(registros)

    # GARANTIA DE ESQUEMA
    for col in COLUNAS_PADRAO:
        if col not in df.columns:
            df[col] = None

    if df.empty:
        return df[COLUNAS_PADRAO]

    return (
        df[COLUNAS_PADRAO]
        .sort_values("previsao_da_conclusao", ascending=True)
        .reset_index(drop=True)
    )


def grafico_cronograma(df, titulo):

    if df.empty:
        st.info("Nenhuma entrega encontrada.")
        return

    df_plot = df.copy()

    # Considera apenas entregas ativas
    df_plot = df_plot[
        df_plot["situacao"].isin(["Prevista", "Atrasada"])
    ]

    # Remove entregas sem anos de referência
    df_plot = df_plot[
        df_plot["anos_referencia_lista"].apply(lambda x: isinstance(x, list) and len(x) > 0)
    ]

    if df_plot.empty:
        st.info("Nenhuma entrega com anos de referência.")
        return

    # ==================================================
    # CRIA INTERVALOS BASEADOS NOS ANOS DE REFERÊNCIA
    # ==================================================

    df_plot["ano_inicio"] = df_plot["anos_referencia_lista"].apply(min)
    df_plot["ano_fim"] = df_plot["anos_referencia_lista"].apply(max)

    df_plot["Inicio"] = pd.to_datetime(
        df_plot["ano_inicio"].astype(str) + "-01-01"
    )

    df_plot["Fim"] = pd.to_datetime(
        df_plot["ano_fim"].astype(str) + "-12-31"
    )

    # ==================================================
    # LIMITES DO EIXO X (ANO MAIS ANTIGO → MAIS RECENTE)
    # ==================================================

    ano_minimo = df_plot["ano_inicio"].min()
    ano_maximo = df_plot["ano_fim"].max()

    xmin = pd.to_datetime(f"{ano_minimo}-01-01")
    xmax = pd.to_datetime(f"{ano_maximo}-12-31")

    # ==================================================
    # HOVER
    # ==================================================

    df_plot["anos_hover"] = df_plot["anos_referencia_lista"].apply(
        lambda x: ", ".join(str(a) for a in sorted(x))
    )

    # Ordena visualmente
    df_plot = df_plot.sort_values("Inicio", ascending=False)

    altura_total = max(300, len(df_plot) * 45)

    df_plot["previsao_hover"] = df_plot["previsao_da_conclusao_str"]

    fig = px.timeline(
        df_plot,
        x_start="Inicio",
        x_end="Fim",
        y="nome_da_entrega",
        color="situacao",
        custom_data=[
            "nome_da_entrega",
            "sigla",
            "previsao_hover",
            "responsaveis",
            "programa"
        ],
        height=altura_total,
        title=titulo
    )

    fig.update_traces(
        hovertemplate=
        "<b>Entrega:</b> %{customdata[0]}<br>"
        "<b>Projeto:</b> %{customdata[1]}<br>"
        "<b>Previsão de Conclusão:</b> %{customdata[2]}<br>"
        "<b>Responsáveis:</b> %{customdata[3]}<br>"
        "<b>Programa:</b> %{customdata[4]}<br>"
        "<extra></extra>"
    )

    fig.update_yaxes(
        categoryorder="array",
        categoryarray=df_plot["nome_da_entrega"].tolist(),
        title=""
    )

    fig.update_xaxes(
        range=[xmin, xmax],
        tickformat="%Y",
        dtick="M12",
    )

    fig.update_layout(
        margin=dict(l=180, r=40, t=60, b=40)
    )

    st.plotly_chart(fig)


# ==========================================================
# NORMALIZA ANOS DE REFERÊNCIA (lista de int)
# ==========================================================
def extrair_anos_ref(valor):
    if not valor:
        return []
    if isinstance(valor, list):
        return [int(v) for v in valor if str(v).isdigit()]
    return [
        int(v.strip())
        for v in str(valor).split(",")
        if v.strip().isdigit()
    ]


# ##########################################################
# INTERFACE
# ##########################################################


st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


st.header("Entregas")

st.write("")

# Montagem do df_entregas
df_entregas = carregar_entregas()

df_entregas["anos_referencia_lista"] = df_entregas["anos_de_referencia"].apply(extrair_anos_ref)

# Converter as coluans de id para string
df_entregas["responsaveis_ids"] = df_entregas["responsaveis_ids"].apply(lambda x: [str(i) for i in x])


df_entregas_lista = df_entregas.copy()


# Botão de gerenciar entregas somente para admin e coordenadores
if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}:
    with st.container(horizontal_alignment="right"):
        st.write('')    
        if st.button("Gerenciar entregas", icon=":material/edit:", width=300):
            dialog_editar_entregas()

st.write("")
st.write("")
st.write("")

# ==========================================================
# FILTROS
# ==========================================================

with st.form("filtros_entregas", border=False):

    col1, col2, col3, col4 = st.columns(4)

    # -------- Projetos --------
    projetos_opcoes = sorted(
        df_entregas["sigla"]
        .dropna()
        .unique()
        .tolist()
    )

    with col1:
        filtro_projetos = st.multiselect(
            "Projetos",
            options=projetos_opcoes,
            placeholder=""
        )

    # -------- Anos de Referência --------
    anos_opcoes = sorted(
        {
            ano
            for lista in df_entregas["anos_referencia_lista"]
            for ano in lista
        }
    )

    with col2:
        filtro_anos = st.multiselect(
            "Anos de referência",
            options=anos_opcoes,
            placeholder=""
        )

    # -------- Status --------
    status_opcoes = sorted(
        df_entregas["situacao"]
        .dropna()
        .unique()
        .tolist()
    )

    with col3:
        filtro_status = st.multiselect(
            "Situação",
            options=status_opcoes,
            placeholder=""
        )

    # -------- Programas --------
    programas_opcoes = sorted(
        df_entregas["programa"]
        .dropna()
        .unique()
        .tolist()
    )

    with col4:
        filtro_programas = st.multiselect(
            "Programa",
            options=programas_opcoes,
            placeholder=""
        )

    aplicar = st.form_submit_button(
        "Aplicar filtros",
        icon=":material/filter_alt:"
    )

# ==========================================================
# APLICAÇÃO DOS FILTROS
# ==========================================================

df_filtrado = df_entregas.copy()

if filtro_projetos:
    df_filtrado = df_filtrado[
        df_filtrado["sigla"].isin(filtro_projetos)
    ]

if filtro_anos:
    df_filtrado = df_filtrado[
        df_filtrado["anos_referencia_lista"].apply(
            lambda anos: any(a in anos for a in filtro_anos)
        )
    ]

if filtro_status:
    df_filtrado = df_filtrado[
        df_filtrado["situacao"].isin(filtro_status)
    ]

if filtro_programas:
    df_filtrado = df_filtrado[
        df_filtrado["programa"].isin(filtro_programas)
    ]

# DataFrame usado nas abas
df_entregas_filtrado = df_filtrado.copy()

st.write("")


lista_entregas, cronograma_entregas = st.tabs(["Entregas","Cronograma"])

with lista_entregas:

    # Renomeando as colunas
    RENOMEAR = {
        "nome_da_entrega": "Entrega",
        "sigla": "Projeto",
        "previsao_da_conclusao_str": "Previsão de Conclusão",
        "responsaveis": "Responsáveis",
        "situacao": "Situação",
        "anos_de_referencia": "Anos de Referência",
        "programa": "Programa",
        "progresso": "Progresso"
    }

    df_entregas_lista = df_entregas_filtrado.copy()

    df_entregas_lista = df_entregas_lista.rename(columns=RENOMEAR)

    df_entregas_lista = df_entregas_lista[[
        "Entrega",
        "Projeto",
        "Programa",
        "Responsáveis",
        "Anos de Referência",
        "Previsão de Conclusão",
        "Situação",
        "Progresso"
    ]]

    # --------------------------------------------------------------------------
    # INTERFACE DA ABA LISTA
    # --------------------------------------------------------------------------

    st.write('')

    # --------------------------------------------------------------------------
    # CALLBACK PARA ABERTURA DO DIÁLOGO DE REGISTROS DE ENTREGAS
    # --------------------------------------------------------------------------
    def criar_callback_selecao_entrega(df_visivel, df_completo, key_df):

        def handle_selecao_entrega():
            estado = st.session_state.get(key_df, {})
            linhas = estado.get("selection", {}).get("rows", [])

            if not linhas:
                return

            idx = linhas[0]

            linha_visivel = df_visivel.iloc[idx]
            linha_completa = df_completo.iloc[idx]  # AQUI

            st.session_state["entrega_selecionada"] = {
                "entrega": linha_visivel["Entrega"],
                "entrega_id": linha_completa["entrega_id"],
                "indice": idx,
                "projeto_id": linha_completa["projeto_id"]  # EXISTE
            }

            st.session_state["abrir_dialogo_entrega"] = True

        return handle_selecao_entrega


    key_df = f"df_entregas_lista"

    callback_selecao = criar_callback_selecao_entrega(
        df_entregas_lista,
        df_entregas,
        key_df
    )


    altura_dataframe = altura_dataframe(df_entregas_lista, -0)

    st.dataframe(
        df_entregas_lista,
        hide_index=True,
        selection_mode="single-row",
        key=key_df,
        on_select=callback_selecao,
        height=altura_dataframe,
        column_config={
            "Progresso": st.column_config.ProgressColumn(
                format="%d%%"
            )
        }
    )


    # --------------------------------------------------
    # ABRIR DIÁLOGO
    # --------------------------------------------------
    if st.session_state.get("abrir_dialogo_entrega"):
        dialog_registros_entregas()
        st.session_state["abrir_dialogo_entrega"] = False


with cronograma_entregas:

    grafico_cronograma(
        df_entregas_filtrado,
        "Cronograma de Entregas"
    )