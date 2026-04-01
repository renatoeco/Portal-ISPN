import streamlit as st
import pandas as pd
from funcoes_auxiliares import conectar_mongo_portal_ispn, float_to_br, br_to_float
from pymongo import UpdateOne
from bson import ObjectId
import bson
import time
import datetime
import plotly.express as px
import streamlit_shadcn_ui as ui
import smtplib
from email.mime.text import MIMEText

st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
#estatistica = db["estatistica"]  # Coleção de estatísticas

programas_areas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"] 
estrategia = db["estrategia"] 
estatistica = db["estatistica"] 
doadores = db["doadores"]
pessoas = db["pessoas"] 
colaboradores_raw = list(db["pessoas"].find())

# Carrega todos os projetos ISPN
dados_projetos_ispn = list(projetos_ispn.find())

# Carrega todos os programas
dados_programas = list(programas_areas.find())

# Carrega todos os doadores
dados_doadores = list(doadores.find())


######################################################################################################
# FUNÇÃO PARA NORMALIZAR LISTAS DE OBJECT IDS
######################################################################################################


def normalizar_lista_ids(lista):
    """
    Converte lista com ObjectId, dict {'$oid': ...} ou str
    para lista de strings
    """
    ids = []
    for item in lista or []:
        if isinstance(item, ObjectId):
            ids.append(str(item))
        elif isinstance(item, dict) and "$oid" in item:
            ids.append(str(item["$oid"]))
        else:
            ids.append(str(item))
    return ids


# ----------------------------------------------------
# BASE GLOBAL DE ENTREGAS (somente ações estratégicas)
# ----------------------------------------------------

entregas_base = []

for proj in dados_projetos_ispn:

    codigo_projeto = proj.get("codigo", "")
    sigla_projeto = proj.get("sigla", "")
    # Agora um projeto pode ter vários programas
    programas_ids = normalizar_lista_ids(proj.get("programas", []))

    for entrega in proj.get("entregas", []):

        if not entrega.get("acoes_relacionadas"):
            continue

        anos_ref = entrega.get("anos_de_referencia", []) or []

        entregas_base.append({
            "projeto_codigo": codigo_projeto,
            "projeto_sigla": sigla_projeto,
            "programas_ids": programas_ids,  # <-- lista agora
            "situacao": entrega.get("situacao", ""),
            "anos_referencia": anos_ref,
            "entrega": entrega
        })


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_programas_e_areas"
nome_pagina = "Programas e Áreas"

hoje = datetime.datetime.now().strftime("%d/%m/%Y")

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
# FUNÇÕES
######################################################################################################


# Função para limpar e formatar o valor
def formatar_valor(valor_bruto, moeda_bruta):
    moeda = moedas.get(str(moeda_bruta).lower(), "R$")
    try:
        if valor_bruto is None:
            valor_num = 0
        else:
            valor_str = str(valor_bruto).replace(".", "").replace(",", ".")
            valor_num = float(valor_str)
        valor_formatado = f"{valor_num:,.0f}".replace(",", ".")
        return f"{moeda} {valor_formatado}"
    except Exception:
        return f"{moeda} 0"
    


# id para nome de programa
mapa_id_para_nome_programa = {
    str(p["_id"]): p.get("nome_programa_area", "Não informado")
    for p in dados_programas
}

# colaborador id para nome
colaborador_id_para_nome = {
    str(col["_id"]): col.get("nome_completo", "Não encontrado")
    for col in colaboradores_raw
}

# id para sigla de projeto
mapa_id_para_sigla_projeto = {
    str(p["_id"]): p.get("sigla", "Não informado")
    for p in dados_projetos_ispn
}

# doador id para nome
mapa_doador_id_para_nome = {
    str(d["_id"]): d.get("nome_doador", "Não informado")
    for d in dados_doadores
}

# Dicionário de símbolos por moeda
moedas = {
    "reais": "R$",
    "real": "R$",
    "dólares": "US$",
    "dólar": "US$",
    "euros": "€",
    "euro": "€"
}


@st.dialog("Gerenciar programa", width="large", on_dismiss="rerun")
def gerenciar_programa_dialog(programa):

    # Busca o documento completo do programa
    programa_doc = programas_areas.find_one({"_id": ObjectId(programa["id"])})
    nome_atual = programa_doc.get("nome_programa_area", "")
    coordenador_id_atual = str(programa_doc.get("coordenador_id", ""))
    acoes_estrategicas = programa_doc.get("acoes_estrategicas", [])

    dados_estrategia = list(estrategia.find({}))

    resultados_medio = []
    resultados_longo = []
    eixos_da_estrategia = []

    # ===============================
    # MAPAS ID -> NOME
    # ===============================

    mapa_eixos = {}
    mapa_mp = {}
    mapa_lp = {}

    for doc in dados_estrategia:

        # Eixos
        for e in doc.get("estrategia", {}).get("eixos_da_estrategia", []):
            mapa_eixos[str(e["_id"])] = e["titulo"]

        # Resultados MP
        for r in doc.get("resultados_medio_prazo", {}).get("resultados_mp", []):
            mapa_mp[str(r["_id"])] = r["titulo"]

        # Resultados LP
        for r in doc.get("resultados_longo_prazo", {}).get("resultados_lp", []):
            mapa_lp[str(r["_id"])] = r["titulo"]
            
    opcoes_eixos = list(mapa_eixos.keys())
    opcoes_mp = list(mapa_mp.keys())
    opcoes_lp = list(mapa_lp.keys())



    # ------------------- Aba principal -------------------
    aba_principal, aba_acoes = st.tabs(["Informações Gerais", "Ações Estratégicas"])

    # ======================================================
    # ABA 1 - INFORMAÇÕES GERAIS
    # ======================================================
    with aba_principal:

        # Lista de coordenadores (sem mostrar ID no selectbox)
        nomes_coordenadores_lista = [""] + [
            c.get("nome_completo", "")
            for c in colaboradores_raw
            if c.get("status", "").lower() == "ativo"
        ]

        # Obter nome do coordenador atual (se houver)
        nome_coordenador_atual = colaborador_id_para_nome.get(coordenador_id_atual, "")

        modo_edicao = st.toggle("Editar", value=False)

        st.write("")

        if not modo_edicao:

            col1, col2 = st.columns(2)

            col1.write(f"**Nome do programa**: {nome_atual}")
            col2.write(f"**Coordenador**: {nome_coordenador_atual}")

        else:

            with st.form(key=f"form_programa_{programa['id']}", clear_on_submit=False, border=False):
                #st.markdown("### Informações do Programa")

                novo_nome = st.text_input("Nome do programa", value=nome_atual)
                
                nome_coordenador_atual = colaborador_id_para_nome.get(coordenador_id_atual) or ""

                # Selecionar coordenador pelo nome
                coordenador_selecionado = st.selectbox(
                    "Coordenador(a)",
                    nomes_coordenadores_lista,
                    index=nomes_coordenadores_lista.index(nome_coordenador_atual)
                    if nome_coordenador_atual in nomes_coordenadores_lista
                    else 0,
                    key=f"coord_{programa['id']}"
                )

                # Descobrir o _id do coordenador selecionado
                coordenador_id_novo = next(
                    (
                        str(c["_id"])
                        for c in colaboradores_raw
                        if c.get("nome_completo", "") == coordenador_selecionado
                    ),
                    ""
                )

                st.write("")

                # Botão salvar
                salvar = st.form_submit_button("Salvar alterações", use_container_width=False)

                if salvar:
                    programas_areas.update_one(
                        {"_id": ObjectId(programa["id"])},
                        {"$set": {
                            "nome_programa_area": novo_nome,
                            "coordenador_id": ObjectId(coordenador_id_novo) if coordenador_id_novo else None
                        }}
                    )
                    st.success("Informações atualizadas com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")

    # ======================================================
    # ABA 2 - AÇÕES ESTRATÉGICAS
    # ======================================================
    with aba_acoes:

        # ---------------- EXPANDER PARA ADICIONAR AÇÃO ----------------
        with st.expander("Adicionar nova ação estratégica", expanded=False, icon=":material/add_notes:"):

            with st.form(key=f"form_add_acao_{programa['id']}", clear_on_submit=True, border=False):
                nova_acao = st.text_input("Título da nova ação estratégica")

                eixo_sel = st.multiselect(
                    "Contribui com quais eixos da estratégia?",
                    options=opcoes_eixos,
                    format_func=lambda x: mapa_eixos.get(x, ""),
                    placeholder=""
                )

                resultados_mp_sel = st.multiselect(
                    "Contribui com quais resultados de médio prazo?",
                    options=opcoes_mp,
                    format_func=lambda x: mapa_mp.get(x, ""),
                    placeholder=""
                )

                resultados_lp_sel = st.multiselect(
                    "Contribui com quais resultados de longo prazo?",
                    options=opcoes_lp,
                    format_func=lambda x: mapa_lp.get(x, ""),
                    placeholder=""
                )


                st.write("")

                adicionar = st.form_submit_button("Adicionar ação", use_container_width=False)
                if adicionar and nova_acao.strip():
                    nova_entrada = {
                        "_id": ObjectId(),
                        "acao_estrategica": nova_acao.strip(),
                        "eixo_relacionado": [ObjectId(i) for i in eixo_sel],
                        "resultados_medio_prazo_relacionados": [ObjectId(i) for i in resultados_mp_sel],
                        "resultados_longo_prazo_relacionados": [ObjectId(i) for i in resultados_lp_sel],
                    }

                    programas_areas.update_one(
                        {"_id": ObjectId(programa["id"])},
                        {"$push": {"acoes_estrategicas": nova_entrada}}
                    )

                    st.success("Nova ação adicionada com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")

        # ---------------- EDITAR AÇÃO EXISTENTE ----------------
        if acoes_estrategicas:

            st.write("")
            st.write("**Ações estratégicas registradas:**")

            for acao in acoes_estrategicas:

                acao_id = str(acao["_id"])
                titulo_atual = acao.get("acao_estrategica", "")

                eixo_atual = [str(i) for i in acao.get("eixo_relacionado", [])]
                mp_atual = [str(i) for i in acao.get("resultados_medio_prazo_relacionados", [])]
                lp_atual = [str(i) for i in acao.get("resultados_longo_prazo_relacionados", [])]

                with st.expander(titulo_atual or "Sem título", expanded=False):

                    toggle_edicao = st.toggle(
                        "Editar ação",
                        key=f"toggle_edicao_acao_{acao_id}",
                        value=False
                    )
                    
                    st.write("")

                    if toggle_edicao:
                        # ---------------- MODO EDIÇÃO ----------------

                        novo_titulo = titulo_atual
                        if "admin" in st.session_state.tipo_usuario:
                            novo_titulo = st.text_area(
                                "Título da ação estratégica",
                                value=titulo_atual,
                                key=f"titulo_{acao_id}"
                            )

                        eixo_sel = st.multiselect(
                            "Eixos da estratégia",
                            options=opcoes_eixos,
                            default=eixo_atual,
                            format_func=lambda x: mapa_eixos.get(x, ""),
                            key=f"eixo_edit_{acao_id}",
                            placeholder=""
                        )

                        resultados_mp_sel = st.multiselect(
                            "Resultados de médio prazo",
                            options=opcoes_mp,
                            default=mp_atual,
                            format_func=lambda x: mapa_mp.get(x, ""),
                            key=f"mp_edit_{acao_id}",
                            placeholder=""
                        )

                        resultados_lp_sel = st.multiselect(
                            "Resultados de longo prazo",
                            options=opcoes_lp,
                            default=lp_atual,
                            format_func=lambda x: mapa_lp.get(x, ""),
                            key=f"lp_edit_{acao_id}",
                            placeholder=""
                        )

                        if st.button("Salvar alterações", key=f"salvar_acao_{acao_id}"):

                            programas_areas.update_one(
                                {
                                    "_id": ObjectId(programa["id"]),
                                    "acoes_estrategicas._id": ObjectId(acao_id)
                                },
                                {
                                    "$set": {
                                        "acoes_estrategicas.$.acao_estrategica": novo_titulo,
                                        "acoes_estrategicas.$.eixo_relacionado": [ObjectId(i) for i in eixo_sel],
                                        "acoes_estrategicas.$.resultados_medio_prazo_relacionados": [ObjectId(i) for i in resultados_mp_sel],
                                        "acoes_estrategicas.$.resultados_longo_prazo_relacionados": [ObjectId(i) for i in resultados_lp_sel],
                                    }
                                }
                            )

                            st.success("Ação estratégica atualizada com sucesso!")
                            time.sleep(2)
                            st.rerun(scope="fragment")

                    else:
                        # ---------------- MODO VISUALIZAÇÃO ----------------

                        if eixo_atual:
                            st.markdown("**Contribui com os eixos estratégicos:**")
                            for e in eixo_atual:
                                st.markdown(f"- {mapa_eixos.get(e, '')}")
                                
                        st.write("")
                                
                        if mp_atual:
                            st.markdown("**Contribui com os resultados de médio prazo:**")
                            for r in mp_atual:
                                st.markdown(f"- {mapa_mp.get(r, '')}")
                                
                        st.write("")
                        
                        if lp_atual:
                            st.markdown("**Contribui com os resultados de longo prazo:**")
                            for r in lp_atual:
                                st.markdown(f"- {mapa_lp.get(r, '')}")


def gerar_anos_intervalo(data_inicio, data_fim):
    """
    Retorna lista de anos entre duas datas (inclusive).
    """
    if not data_inicio or not data_fim:
        return []
    
    ano_inicio = data_inicio.year
    ano_fim = data_fim.year
    
    return list(range(ano_inicio, ano_fim + 1))


# Função para converter datas (str -> datetime.date)
def parse_date(data_str):
    if isinstance(data_str, str):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(data_str, fmt).date()
            except ValueError:
                continue
    return None


# Função do diálogo para gerenciar projeto
@st.dialog("Editar Projeto", width="large")
def dialog_editar_projeto():
    

    ######################################################################
    # CARREGAR DADOS DA COLEÇÃO ufs_municipios
    ######################################################################

    colecao_ufs = db["ufs_municipios"]

    # ---- Buscar todos os documentos ----
    docs = list(colecao_ufs.find({}))

    # Inicializar variáveis
    dados_ufs = []
    dados_municipios = []
    dados_biomas = []
    dados_assentamentos = []
    dados_ti = []
    dados_quilombos = []
    dados_uc = []


    # Encontrar o documento que tem o campo bacias_hidrograficas
    doc_bacias = next((d for d in docs if "bacias_hidrograficas" in d), None)
    bacias = doc_bacias.get("bacias_hidrograficas", []) if doc_bacias else []

    # Normalizar os dados das bacias (criar dict padronizado)
    dados_bacias_macro = [
        {"codigo": b["codigo_bacia_nivel_2"], "label": b["nome_bacia_nivel_2"]}
        for b in bacias if "nome_bacia_nivel_2" in b
    ]

    dados_bacias_meso = [
        {"codigo": b["codigo_bacia_nivel_3"], "label": b["nome_bacia_nivel_3"]}
        for b in bacias if "nome_bacia_nivel_3" in b
    ]

    dados_bacias_micro = [
        {"codigo": b["codigo_bacia_nivel_4"], "label": b["nome_bacia_nivel_4"]}
        for b in bacias if "nome_bacia_nivel_4" in b
    ]
    

    # ---- Identificar cada documento pela chave existente ----
    for doc in docs:
        if "ufs" in doc:
            dados_ufs = doc["ufs"]

        elif "municipios" in doc:
            dados_municipios = doc["municipios"]
        
        elif "biomas" in doc:
            dados_biomas = doc["biomas"]

        elif "assentamentos" in doc:
            dados_assentamentos = doc["assentamentos"]

        elif "tis" in doc:
            dados_ti = doc["tis"]

        elif "quilombos" in doc:
            dados_quilombos = doc["quilombos"]

        elif "ucs" in doc:
            dados_uc = doc["ucs"]

    # DataFrame de projetos
    df_projetos_ispn = pd.DataFrame(dados_projetos_ispn)

    # Garante que _id é string (importante para comparações)
    if not df_projetos_ispn.empty:
        df_projetos_ispn["_id"] = df_projetos_ispn["_id"].astype(str)

    df_filtrado = df_projetos_ispn[df_projetos_ispn["sigla"] == projeto_selecionado]

    if df_filtrado.empty:
        st.error("Projeto não encontrado.")
        st.stop()  

    projeto_info = df_filtrado.iloc[0]

    orcamento_existente = projeto_info.get("orcamento_por_ano", {})

    # Se vier None, float, NaN, etc → vira dict vazio
    if not isinstance(orcamento_existente, dict):
        orcamento_existente = {}

    # ==============================================================
    # INTERFACE DO DIÁLOGO DE EDITAR PROJETO
    # ==============================================================

        
    st.write("")

    with st.form("form_editar_projeto", border=False):
        
        #######################################################################
        # DADOS DO PROJETO
        #######################################################################
        
        st.subheader("Dados do projeto")
        st.write("")

        col1, col2 = st.columns(2)
        
        # Código
        codigo = col1.text_input("Código", value=projeto_info.get("codigo", ""))
        
        # Sigla
        sigla = col2.text_input("Sigla", value=projeto_info.get("sigla", ""))
        
        # Nome do projeto
        nome_do_projeto = st.text_input("Nome do Projeto", value=projeto_info.get("nome_do_projeto", ""))

        col1, col2, col3 = st.columns(3)

        # Status
        status_options = ["", "Em andamento", "Finalizado", "Cancelado"]

        status_atual = projeto_info.get("status", "")
        index_status = status_options.index(status_atual) if status_atual in status_options else 0

        status = col1.selectbox(
            "Status",
            options=status_options,
            index=index_status
        )

        # Datas
        data_inicio_raw = projeto_info.get("data_inicio_contrato")

        data_inicio = col2.date_input(
            "Data de início",
            value=(
                pd.to_datetime(data_inicio_raw, errors="coerce", dayfirst=True).date()
                if data_inicio_raw and not pd.isna(pd.to_datetime(data_inicio_raw, errors="coerce", dayfirst=True))
                else None
            ),
            format="DD/MM/YYYY"
        )

        data_fim_raw = projeto_info.get("data_fim_contrato")

        data_fim = col3.date_input(
            "Data de fim",
            value=(
                pd.to_datetime(data_fim_raw, format="%d/%m/%Y", errors="coerce").date()
                if data_fim_raw and not pd.isna(pd.to_datetime(data_fim_raw, format="%d/%m/%Y", errors="coerce"))
                else None
            ),
            format="DD/MM/YYYY"
        )
        
        # -----------------------------------
        # Pessoas ativas (base para selects)
        # -----------------------------------
        # DataFrame de pessoas
        df_pessoas = pd.DataFrame(colaboradores_raw)

        if not df_pessoas.empty:
            df_pessoas["_id"] = df_pessoas["_id"].astype(str)
            
        df_pessoas_ativas = df_pessoas[df_pessoas["status"] == "ativo"].copy()

        pessoas_ativas_options = df_pessoas_ativas["_id"].astype(str).tolist()

        # Coordenador atual
        coordenador_atual_obj = projeto_info.get("coordenador")
        coordenador_atual_str = str(coordenador_atual_obj) if coordenador_atual_obj else ""

        # Opções: pessoas ativas + coordenador atual (se não estiver ativo)
        coordenador_options = pessoas_ativas_options.copy()

        if coordenador_atual_str and coordenador_atual_str not in coordenador_options:
            coordenador_options.insert(0, coordenador_atual_str)

        coordenador_options = [""] + coordenador_options

        index_coordenador = (
            coordenador_options.index(coordenador_atual_str)
            if coordenador_atual_str in coordenador_options
            else 0
        )

        coordenador = col1.selectbox(
            "Coordenador",
            options=coordenador_options,
            format_func=lambda x: "" if x == "" else df_pessoas
                .loc[df_pessoas["_id"].astype(str) == x, "nome_completo"]
                .values[0],
            index=index_coordenador
        )

        # Programa / Área
        mapa_programa = {
            str(p["_id"]): p.get("nome_programa_area", "Não informado")
            for p in dados_programas
        }
        
        mapa_programa_str = {str(k): v for k, v in mapa_programa.items()}

        programa_options = list(mapa_programa_str.keys())
        programas_atuais = projeto_info.get("programas", [])

        # Garante lista
        if not isinstance(programas_atuais, list):
            programas_atuais = [programas_atuais] if programas_atuais else []

        # Converte para string e remove inválidos
        programas_atuais_str = [
            str(p) for p in programas_atuais
            if p and str(p) != "nan"
        ]

        # Mantém apenas os que existem nas opções
        programas_atuais_str = [
            p for p in programas_atuais_str
            if p in programa_options
        ]

        programa_options = list(mapa_programa_str.keys())

        programas_selecionados = col2.multiselect(
            "Programa / Área",
            options=programa_options,
            default=programas_atuais_str,
            format_func=lambda x: mapa_programa_str[x],
            placeholder=""
        )
        
        # Doador
        mapa_doador = {
            str(d["_id"]): d.get("nome_doador", "Não informado")
            for d in dados_doadores
        }
        
        doador_options = list(mapa_doador.keys())
        doador_atual = projeto_info.get("doador", "")
        index_doador = doador_options.index(doador_atual) if doador_atual in doador_options else 0
        doador = col3.selectbox(
            "Doador",
            options=doador_options,
            format_func=lambda x: mapa_doador[x],
            index=index_doador
        )
        
        # -----------------------------------
        # Gestores atuais (normalização segura)
        # -----------------------------------
        gestores_raw = projeto_info.get("gestores", [])

        if not isinstance(gestores_raw, list):
            gestores_raw = []

        gestores_atuais = [str(g) for g in gestores_raw if g]
        
        gestores_options = pessoas_ativas_options.copy()

        for g in gestores_atuais:
            if g not in gestores_options:
                gestores_options.append(g)
                
        gestores = st.multiselect(
            "Gestores(as) do projeto",
            options=gestores_options,
            default=gestores_atuais,
            format_func=lambda x: df_pessoas
                .loc[df_pessoas["_id"].astype(str) == x, "nome_completo"]
                .values[0],
            placeholder=""
        )

        # Objetivo geral
        objetivo_geral = st.text_area(
            "Objetivo Geral",
            value=str(projeto_info.get("objetivo_geral", "")) if pd.notna(projeto_info.get("objetivo_geral")) else ""
        )

        #######################################################################
        # INFORMAÇÕES FINANCEIRAS
        #######################################################################
        
        st.divider()
        
        st.subheader("Informações Financeiras")
        st.write("")

        col1, col2, col3 = st.columns(3)

        # Moeda
        moeda_options = ["", "Dólares", "Reais", "Euros"]
        moeda_atual = projeto_info.get("moeda", "")
        index_atual = moeda_options.index(moeda_atual) if moeda_atual in moeda_options else 0

        moeda = col1.selectbox(
            "Moeda",
            options=moeda_options,
            index=index_atual
        )

        # Valor
        valor_atual = br_to_float(projeto_info.get("valor", "0"))

        valor = col2.number_input(
            "Valor",
            value=valor_atual,
            step=0.01,
            min_value=0.0,
            format="%.2f"
        )

        # Contrapartida
        contrapartida_atual = br_to_float(
            projeto_info.get("valor_da_contrapartida_em_r$", "0")
        )

        contrapartida = col3.number_input(
            "Contrapartida em R$",
            value=contrapartida_atual,
            step=0.01,
            min_value=0.0,
            format="%.2f"
        )
        anos_projeto = gerar_anos_intervalo(data_inicio, data_fim)

        orcamento_por_ano = {}

        if anos_projeto:
            cols = st.columns(len(anos_projeto))

            for i, ano in enumerate(anos_projeto):
                valor_inicial = br_to_float(orcamento_existente.get(str(ano), "0"))

                valor_ano = cols[i].number_input(
                    f"Orçamento de {ano}",
                    min_value=0.0,
                    value=valor_inicial,
                    step=0.01,
                    format="%.2f",
                    key=f"edit_orcamento_{ano}"
                )

                orcamento_por_ano[str(ano)] = valor_ano

        ######################################################################
        # REGIÕES DE ATUAÇÃO
        ######################################################################

        st.divider()

        # --- Carrega dados do Mongo ---
        doc_ufs = colecao_ufs.find_one({"ufs": {"$exists": True}})
        doc_municipios = colecao_ufs.find_one({"municipios": {"$exists": True}})

        dados_ufs = doc_ufs.get("ufs", []) if doc_ufs else []
        dados_municipios = doc_municipios.get("municipios", []) if doc_municipios else []

        # Criar dicionário código_uf -> sigla
        codigo_uf_para_sigla = {
            '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
            '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA',
            '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP',
            '41': 'PR', '42': 'SC', '43': 'RS',
            '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'
        }
        
        uf_codigo_para_label = {
            uf["codigo_uf"]: f"{uf['nome_uf']} ({uf['codigo_uf']})"
            for uf in dados_ufs
        }


        # Criar mapeamento código -> "Município - UF"
        municipios_codigo_para_label = {
            int(m["codigo_municipio"]): f"{m['nome_municipio']} - {codigo_uf_para_sigla[str(m['codigo_municipio'])[:2]]}"
            for m in dados_municipios
        }
        
        biomas_codigo_para_label = {
            b["codigo_bioma"]: f"{b['nome_bioma']} ({b['codigo_bioma']})"
            for b in dados_biomas
        }

        assent_codigo_para_label = {
            a["codigo_assentamento"]: f"{a['nome_assentamento']} ({a['codigo_assentamento']})"
            for a in dados_assentamentos
        }

        quilombo_codigo_para_label = {
            q["codigo_quilombo"]: f"{q['nome_quilombo']} ({q['codigo_quilombo']})"
            for q in dados_quilombos
        }

        ti_codigo_para_label = {
            ti["codigo_ti"]: f"{ti['nome_ti']} ({ti['codigo_ti']})"
            for ti in dados_ti
        }

        uc_codigo_para_label = {
            u["codigo_uc"]: f"{u['nome_uc']} ({u['codigo_uc']})"
            for u in dados_uc
        }

        bacia_macro_codigo_para_label = {
            b["codigo"]: f"{b['label']} ({b['codigo']})" 
            for b in dados_bacias_macro
        }

        bacia_meso_codigo_para_label = {
            b["codigo"]: f"{b['label']} ({b['codigo']})" 
            for b in dados_bacias_meso
        }

        bacia_micro_codigo_para_label = {
            b["codigo"]: f"{b['label']} ({b['codigo']})" 
            for b in dados_bacias_micro
        }

        # -------------------- VALORES PADRÃO (REGIÕES JÁ CADASTRADAS) --------------------
        regioes = projeto_info.get("regioes_atuacao", [])

        # Garante que sempre seja lista (evita float, NaN, None, etc)
        if not isinstance(regioes, list):
            regioes = []

        ufs_default = [r["codigo"] for r in regioes if r["tipo"] == "uf"]
        muni_default = [r["codigo"] for r in regioes if r["tipo"] == "municipio"]
        biomas_default = [r["codigo"] for r in regioes if r["tipo"] == "bioma"]
        ti_default = [r["codigo"] for r in regioes if r["tipo"] == "terra_indigena"]
        uc_default = [r["codigo"] for r in regioes if r["tipo"] == "uc"]
        assent_default = [r["codigo"] for r in regioes if r["tipo"] == "assentamento"]
        quilombo_default = [r["codigo"] for r in regioes if r["tipo"] == "quilombo"]
        bacia_micro_default = [r["codigo"] for r in regioes if r["tipo"] == "bacia_micro"]
        bacia_meso_default = [r["codigo"] for r in regioes if r["tipo"] == "bacia_meso"]
        bacia_macro_default = [r["codigo"] for r in regioes if r["tipo"] == "bacia_macro"]
        
        st.subheader("Regiões de atuação")
        st.write("")

        # ----------------------- ESTADOS, MUNICÍPIOS E BIOMAS -----------------------
        col1, col2, col3 = st.columns(3)

        ufs_selecionadas = col1.multiselect(
            "Estados",
            options=sorted(uf_codigo_para_label.values()),
            default=[uf_codigo_para_label[c] for c in ufs_default if c in uf_codigo_para_label],
            placeholder=""
        )

        municipios_selecionadas = col2.multiselect(
            "Municípios",
            options=sorted(municipios_codigo_para_label.values()),
            default=[municipios_codigo_para_label[c] for c in muni_default if c in municipios_codigo_para_label],
            placeholder=""
        )

        biomas_selecionados = col3.multiselect(
            "Biomas",
            options=sorted(biomas_codigo_para_label.values()),
            default=[biomas_codigo_para_label[c] for c in biomas_default if c in biomas_codigo_para_label],
            placeholder=""
        )

        # ----------------------- UNIDADES DE CONSERVAÇÃO -----------------------

        col1, col2 = st.columns(2)

        ucs_selecionadas = col1.multiselect(
            "Unidades de Conservação",
            options=sorted(uc_codigo_para_label.values()),
            default=[uc_codigo_para_label[c] for c in uc_default if c in uc_codigo_para_label],
            placeholder=""
        )

        # ----------------------- TERRAS INDÍGENAS -----------------------
        
        tis_selecionadas = col2.multiselect(
            "Terras Indígenas",
            options=sorted(ti_codigo_para_label.values()),  # lista de labels
            default=[ti_codigo_para_label[c] for c in ti_default if c in ti_codigo_para_label],
            placeholder=""
        )

        # ----------------------- ASSENTAMENTOS -----------------------
        
        col1, col2 = st.columns(2)
        
        assentamentos_selecionados = col1.multiselect(
            "Assentamentos",
            options=sorted(assent_codigo_para_label.values()),
            default=[assent_codigo_para_label[c] for c in assent_default],
            placeholder=""
        )

        # ----------------------- QUILOMBOS -----------------------
        quilombos_selecionados = col2.multiselect(
            "Quilombos",
            options=sorted(quilombo_codigo_para_label.values()),
            default=[quilombo_codigo_para_label[c] for c in quilombo_default],
            placeholder=""
        )

        # ----------------------- BACIAS HIDROGRÁFICAS -----------------------
        col1, col2, col3 = st.columns(3)
        
        bacias_macro_sel = col1.multiselect(
            "Bacias Hidrográficas - Nível 2",
            options=sorted(bacia_macro_codigo_para_label.values()),
            default=[bacia_macro_codigo_para_label[c] for c in bacia_macro_default],
            placeholder=""
        )
        

        bacias_meso_sel = col2.multiselect(
            "Bacias Hidrográficas - Nível 3",
            options=sorted(bacia_meso_codigo_para_label.values()),
            default=[bacia_meso_codigo_para_label[c] for c in bacia_meso_default],
            placeholder=""
        )
        
        bacias_micro_sel = col3.multiselect(
            "Bacias Hidrográficas - Nível 4",
            options=sorted(bacia_micro_codigo_para_label.values()),
            default=[bacia_micro_codigo_para_label[c] for c in bacia_micro_default],
            placeholder=""
        )

        st.write('')
        
        # Botão de salvar
        submit = st.form_submit_button("Salvar", icon=":material/save:", type="primary", width=200)
        if submit:
            # Converter coordenador, doador e programa para ObjectId antes de salvar
            coordenador_objid = bson.ObjectId(coordenador) if coordenador else None
            gestores_objids = [bson.ObjectId(g) for g in gestores] if gestores else []
            doador_objid = bson.ObjectId(doador) if doador else None
            programas_objids = [bson.ObjectId(p) for p in programas_selecionados] if programas_selecionados else []


            # Checar duplicidade de sigla
            sigla_existente = ((df_projetos_ispn["sigla"] == sigla) & (df_projetos_ispn["_id"] != projeto_info["_id"])).any()

            # Checar duplicidade de código
            codigo_existente = ((df_projetos_ispn["codigo"] == codigo) & (df_projetos_ispn["_id"] != projeto_info["_id"])).any()

            if sigla_existente:
                st.warning(f"A sigla '{sigla}' já está cadastrada em outro projeto. Escolha outra.")
            elif codigo_existente:
                st.warning(f"O código '{codigo}' já está cadastrado em outro projeto. Escolha outro.")
                
            # Validação: pelo menos um ano preenchido
            elif all(v == 0 for v in orcamento_por_ano.values()):
                st.warning("Preencha pelo menos um ano no orçamento.")

            # Validação: soma dos anos igual ao valor total
            elif round(sum(orcamento_por_ano.values()), 2) != round(valor, 2):
                st.warning(
                    f"A soma dos orçamentos ({float_to_br(sum(orcamento_por_ano.values()))}) "
                    f"deve ser igual ao valor total ({float_to_br(valor)})."
                )
                
            else:

                # Função auxiliar
                def get_codigo_por_label(dicionario, valor):
                    return next((codigo for codigo, label in dicionario.items() if label == valor), None)

                regioes_atuacao = []

                # Tipos simples com lookup
                for tipo, selecionados, dicionario in [
                    ("uf", ufs_selecionadas, uf_codigo_para_label),
                    ("municipio", municipios_selecionadas, municipios_codigo_para_label),
                    ("bioma", biomas_selecionados, biomas_codigo_para_label),
                    ("terra_indigena", tis_selecionadas, ti_codigo_para_label),
                    ("uc", ucs_selecionadas, uc_codigo_para_label),
                    ("assentamento", assentamentos_selecionados, assent_codigo_para_label),
                    ("quilombo", quilombos_selecionados, quilombo_codigo_para_label),
                    ("bacia_micro", bacias_micro_sel, bacia_micro_codigo_para_label),
                    ("bacia_meso", bacias_meso_sel, bacia_meso_codigo_para_label),
                    ("bacia_macro", bacias_macro_sel, bacia_macro_codigo_para_label),
                ]:
                    for item in selecionados:
                        codigo_atuacao = get_codigo_por_label(dicionario, item)
                        if codigo_atuacao:
                            regioes_atuacao.append({"tipo": tipo, "codigo": codigo_atuacao})

                # Agora salva no MongoDB
                update_doc = {
                    "codigo": codigo,
                    "sigla": sigla,
                    "nome_do_projeto": nome_do_projeto,
                    "moeda": moeda,
                    "valor": float_to_br(valor),
                    "valor_da_contrapartida_em_r$": float_to_br(contrapartida),
                    "coordenador": coordenador_objid,
                    "doador": doador_objid,
                    "programas": programas_objids,
                    "gestores": gestores_objids,
                    "status": status,
                    "data_inicio_contrato": data_inicio.strftime("%d/%m/%Y"),
                    "data_fim_contrato": data_fim.strftime("%d/%m/%Y"),
                    "objetivo_geral": objetivo_geral,
                    "regioes_atuacao": regioes_atuacao,
                    "orcamento_por_ano": {
                        ano: float_to_br(v)
                        for ano, v in orcamento_por_ano.items()
                        if v > 0
                    },
                }

                projetos_ispn.update_one({"_id": ObjectId(projeto_info["_id"])}, {"$set": update_doc})
                st.success("Projeto atualizado com sucesso!")
                time.sleep(2)
                st.rerun()


def verificar_contratos_vencidos(pessoa):
    hoje = datetime.date.today()
    contratos_atualizados = False

    for idx, contrato in enumerate(pessoa.get("contratos", [])):
        data_fim = parse_date(contrato.get("data_fim"))
        status_atual = contrato.get("status_contrato", "")

        if data_fim and hoje > data_fim and status_atual != "Encerrado":
            pessoas.update_one(
                {"_id": pessoa["_id"]},
                {"$set": {f"contratos.{idx}.status_contrato": "Encerrado"}}
            )
            contrato["status_contrato"] = "Encerrado"
            contratos_atualizados = True

    return contratos_atualizados


# Função para enviar e-mail de registro da previdência
def enviar_email(destinatario: str, nome: str, valor_contribuicao: float) -> bool:
    """
    Envia um e-mail de notificação de contribuição à previdência.

    Parâmetros:
    - destinatario: e-mail do destinatário
    - nome: nome do beneficiário
    - valor_contribuicao: valor da contribuição (float)

    Retorna:
    - True se enviado com sucesso, False caso ocorra erro
    """

    # Dados de autenticação do secrets.toml
    remetente = st.secrets["senhas"]["endereco_email"]
    senha = st.secrets["senhas"]["senha_email"]

    # Formata o valor da contribuição no padrão brasileiro
    valor_str = format(valor_contribuicao, ",.2f").replace(",", "X").replace(".", ",").replace("X", ".")

    # Assunto do e-mail
    assunto = "Confirmação de Contribuição - Previdência Privada"

    # Corpo HTML do e-mail

    corpo = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Confirmação de Contribuição</title>
    </head>
    <body style="font-size: 16px; font-family: Arial, sans-serif; background-color: #ffffff; padding: 20px; color: #333;">

        <!-- Cabeçalho com Logo -->
        <div style="text-align: center; margin-bottom: 30px;">
            <img src="https://ispn.org.br/site/wp-content/uploads/2021/04/logo_ISPN_2021.png"
                alt="ISPN Logo"
                style="max-width: 150px; margin-bottom: 40px; margin-top: 10px;">
            <h3 style="color: #004d40;">Confirmação de Contribuição à Previdência Privada</h3>
        </div>

        <!-- Conteúdo principal -->
        <br>
        <p>Olá <strong>{nome}</strong>,</p>
        <p>Sua contribuição à previdência privada foi registrada.</p>
        <p>Sua próxima nota fiscal deve ser emitida com o <strong>valor adicional de R$ {valor_str}</strong>.</p>
        <p>Att.</p>
        <p>DP do ISPN</p>

    </body>
    </html>
    """

    # Cria a mensagem MIME
    msg = MIMEText(corpo, "html", "utf-8")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    # Tenta enviar via SMTP SSL
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, destinatario, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False
    
    
# Define um diálogo (modal) para gerenciar colaboradores
@st.dialog("Gerenciar colaboradores", width='large', on_dismiss="rerun")
def gerenciar_pessoas(pessoa_sel):

    dados_pessoas = list(pessoas.find())
    
    # -------------------------------------------------------------------------
    # Inicializações de session_state
    # -------------------------------------------------------------------------
    if "contratos_verificados_por_pessoa" not in st.session_state:
        st.session_state.contratos_verificados_por_pessoa = {}

    if "pessoa_selecionada_anterior" not in st.session_state:
        st.session_state.pessoa_selecionada_anterior = None


    # Mapeia nomes de programa <-> ObjectId
    nome_para_id_programa = {
        p["nome_programa_area"]: p["_id"]
        for p in dados_programas if p.get("nome_programa_area")
    }
    id_para_nome_programa = {
        p["_id"]: p["nome_programa_area"]
        for p in dados_programas if p.get("nome_programa_area")
    }

    # Mapeia codigo de projeto <-> ObjectId
    # nome -> ObjectId
    sigla_para_id_projeto = {
        p.get("sigla"): p["_id"]   # <<< sem str()
        for p in dados_projetos_ispn
        if p.get("sigla") and "_id" in p
    }
  
    lista_programas_areas = sorted(nome_para_id_programa.keys())
    
    # Lista de coordenadores existentes (id, nome, programa)
    coordenadores_possiveis = [
        {
            "id": pessoa["_id"],
            "nome": pessoa.get("nome_completo", ""),
            "programa": pessoa.get("programa_area", "")
        }
        for pessoa in dados_pessoas
        if "coordenador(a)" in pessoa.get("tipo de usuário", "").lower() and pessoa.get("status") == "ativo"
    ]
    
    # Lista com nomes dos colaboradores para seleção
    nomes_existentes = [""] + ["--Adicionar colaborador--"] + sorted([
        p["nome_completo"]
        for p in dados_pessoas
        # if "coordenador" in p  # só inclui quem tem o campo 'coordenador'
    ])
    
    # Recebe diretamente o colaborador vindo do dataframe
    nome_selecionado = pessoa_sel

    # -------------------------------------------------------------------------
    # Processamento do colaborador selecionado
    # -------------------------------------------------------------------------
    if nome_selecionado:

        pessoa = next(
            (p for p in dados_pessoas if str(p["_id"]) == nome_selecionado),
            None
        )

        if pessoa:
            pessoa_id = str(pessoa["_id"])

            # Detecta troca de pessoa e força nova verificação
            if nome_selecionado != st.session_state.pessoa_selecionada_anterior:
                st.session_state.pessoa_selecionada_anterior = nome_selecionado
                st.session_state.contratos_verificados_por_pessoa.pop(pessoa_id, None)

                # LIMPA ESTADO DA ABA FÉRIAS
                for chave in ("dia_niver", "mes_niver", "dias_residuais"):
                    st.session_state.pop(chave, None)

            # Verificação única por pessoa
            if not st.session_state.contratos_verificados_por_pessoa.get(pessoa_id, False):

                contratos_atualizados = verificar_contratos_vencidos(pessoa)

                if contratos_atualizados:
                    st.toast(
                        "Contratos vencidos foram atualizados para 'Encerrado'",
                        icon=":material/event_busy:",
                        duration=5
                    )

                st.session_state.contratos_verificados_por_pessoa[pessoa_id] = True

    
        # Cria abas
        aba_info, aba_contratos, aba_anotacoes  = st.tabs([":material/info: Informações gerais", ":material/contract: Projetos e Contratos", ":material/notes: Anotações"])
    
        # ABA INFORMAÇÕES GERAIS ################################################################
        with aba_info:

            if pessoa:

                # ===============================
                # Formulário principal
                # ===============================

                # ===============================
                # Tipo de contratação (fora do form)
                # ===============================
                lista_tipo_contracao = ["PJ1", "PJ2", "CLT", "Estágio", ""]
                tipo_contratacao = st.selectbox(
                    "Tipo de contratação:",
                    lista_tipo_contracao,
                    index=lista_tipo_contracao.index(pessoa.get("tipo_contratacao", "")) 
                    if pessoa.get("tipo_contratacao", "") in lista_tipo_contracao else 0,
                    key=f"editar_contratacao_{pessoa_id}",
                    width=300
                )


                with st.form("form_editar_colaborador", border=False):

                    # -----------------------------------------------------------------
                    # Nome completo e status
                    # -----------------------------------------------------------------
                    

                    cols = st.columns([3,2])
                    nome = cols[0].text_input("Nome completo:", value=pessoa.get("nome_completo", ""), key=f"editar_nome_{pessoa_id}")

                    status_opcoes = ["ativo", "inativo"]
                    status = cols[1].selectbox(
                        "Status do(a) colaborador(a):", 
                        status_opcoes, 
                        index=status_opcoes.index(pessoa.get("status", "ativo")), 
                        key=f"editar_status_{pessoa_id}"
                    )

                    # -----------------------------------------------------------------
                    # CPF, RG, telefone e email
                    # -----------------------------------------------------------------


                    cols = st.columns(4)

                    cpf = cols[0].text_input("CPF:", value=pessoa.get("CPF", ""), key=f"editar_cpf_{pessoa_id}")
                    rg = cols[1].text_input("RG e órgão emissor:", value=pessoa.get("RG", ""), key=f"editar_rg_{pessoa_id}")

                    telefone = cols[2].text_input("Telefone:", value=pessoa.get("telefone", ""), key=f"editar_telefone_{pessoa_id}")
                    email = cols[3].text_input("E-mail:", value=pessoa.get("e_mail", ""), key=f"editar_email_{pessoa_id}")


                    # -----------------------------------------------------------------
                    # Gênero, Raça e Data de Nascimento
                    # -----------------------------------------------------------------
                    
                    cols = st.columns(3)

                    lista_generos = ["", "Masculino", "Feminino", "Não binário", "Outro"]

                    genero = cols[0].selectbox(
                        "Gênero:",
                        lista_generos,
                        index=lista_generos.index(pessoa.get("gênero")) if pessoa.get("gênero") in lista_generos else 0,
                        key=f"editar_genero_{pessoa_id}"
                    )

                    lista_raca = ["", "Amarelo", "Branco", "Índigena", "Pardo", "Preto"]

                    raca = cols[1].selectbox(
                        "Raça:",
                        lista_raca,
                        index=lista_raca.index(pessoa.get("raca")) if pessoa.get("raca") in lista_raca else 0,
                        key=f"editar_raca_{pessoa_id}"
                    )
                    
                    data_nascimento_str = pessoa.get("data_nascimento", "")
                    if data_nascimento_str:
                        data_nascimento = datetime.datetime.strptime(data_nascimento_str, "%d/%m/%Y")
                    else:
                        data_nascimento = None
                    data_nascimento = cols[2].date_input("Data de nascimento:", format="DD/MM/YYYY", value=data_nascimento, min_value=datetime.date(1920, 1, 1),
                                                         key=f"editar_data_nascimento_{pessoa_id}")

                    # -----------------------------------------------------------------
                    # Escolaridade, escritório, programa
                    # -----------------------------------------------------------------

                    cols = st.columns(3)

                    lista_escolaridade = ["", "Ensino fundamental", "Ensino médio", "Curso técnico", "Graduação", "Pós-graduação", "Mestrado", "Doutorado"]

                    escolaridade = cols[0].selectbox(
                        "Escolaridade:",
                        lista_escolaridade,
                        index=lista_escolaridade.index(pessoa.get("escolaridade")) if pessoa.get("escolaridade") in lista_escolaridade else 0,
                        key=f"editar_escolaridade_{pessoa_id}"
                    )

                    lista_escritorio = ["", "Brasília", "Santa Inês"]

                    escritorio = cols[1].selectbox(
                        "Escritório:",
                        lista_escritorio,
                        index=lista_escritorio.index(pessoa.get("escritorio")) if pessoa.get("escritorio") in lista_escritorio else 0,
                        key=f"editar_escritorio_{pessoa_id}"
                    )


                    # Programa / Área
                    # Pode ser ObjectId único, lista ou vazio (compatibilidade retroativa)
                    programas_atuais_raw = pessoa.get("programa_area", [])

                    if not isinstance(programas_atuais_raw, list):
                        programas_atuais_raw = [programas_atuais_raw] if programas_atuais_raw else []

                    # Converte ObjectId → nomes
                    programas_atuais_nomes = [
                        id_para_nome_programa.get(pid)
                        for pid in programas_atuais_raw
                        if pid in id_para_nome_programa
                    ]

                    # Multiselect
                    programas_selecionados = cols[2].multiselect(
                        "Programa / Área:",
                        options=lista_programas_areas,
                        default=programas_atuais_nomes,
                        key=f"editar_programa_{pessoa_id}"
                    )

                    # Converte nomes → ObjectId
                    programa_area = [
                        nome_para_id_programa[nome]
                        for nome in programas_selecionados
                        if nome in nome_para_id_programa
                    ]

                    # -----------------------------------------------------------------
                    # Cargo e nome do coordenador
                    # -----------------------------------------------------------------

                    cols = st.columns([3, 2])
                    
                    opcoes_cargos = [
                        "Analista de advocacy", "Analista de comunicação", "Analista de dados", "Analista Administrativo/Financeiro",
                        "Analista de Recursos Humanos", "Analista socioambiental", "Analista socioambiental pleno", "Analista socioambiental sênior",
                        "Assessora de advocacy", "Assessor de Comunicação", "Auxiliar de Serviços Gerais", "Auxiliar Administrativo/financeiro",
                        "Assistente Administrativo/financeiro", "Assistente socioambiental", "Coordenador Administrativo/financeiro de escritório",
                        "Coordenador Geral administrativo/financeiro", "Coordenador Executivo", "Coordenador de Área", "Coordenador de Programa", "Estagiário",
                        "Motorista", "Secretária(o)/Recepcionista", "Técnico de campo", "Técnico em informática"
                    ]

                    # Garante que a lista tenha um valor vazio como placeholder
                    opcoes_cargos_com_vazio = [""] + opcoes_cargos  

                    valor_cargo = pessoa.get("cargo") or ""  
                    if valor_cargo not in opcoes_cargos_com_vazio:
                        valor_cargo = ""  

                    cargo = cols[0].selectbox(
                        "Cargo:",
                        opcoes_cargos_com_vazio,
                        index=opcoes_cargos_com_vazio.index(valor_cargo),
                        key=f"editar_cargo_{pessoa_id}"
                    )

                    # Coordenador

                    # 1. Lista de nomes (adiciona opção vazia)
                    nomes_coordenadores = [""] + [c["nome"] for c in coordenadores_possiveis]

                    # 2. Tenta encontrar coordenador atual
                    coordenador_atual_id = pessoa.get("coordenador")
                    coordenador_encontrado = next(
                        (c for c in coordenadores_possiveis if str(c["id"]) == str(coordenador_atual_id)),
                        None
                    )

                    # 3. Define valor default (se não achar, fica vazio)
                    nome_coordenador_default = coordenador_encontrado["nome"] if coordenador_encontrado else ""

                    # 4. Selectbox
                    coordenador_nome = cols[1].selectbox(
                        "Nome do(a) coordenador(a):",
                        nomes_coordenadores,
                        index=nomes_coordenadores.index(nome_coordenador_default)
                        if nome_coordenador_default in nomes_coordenadores else 0,
                        key=f"editar_nome_coordenador_{pessoa_id}"
                    )


                    # 5. Pega o ID do coordenador selecionado (se não for vazio)
                    coordenador_id = None
                    if coordenador_nome:
                        coordenador_id = next(
                            c["id"] for c in coordenadores_possiveis if c["nome"] == coordenador_nome
                        )        

                    # ===============================
                    # CAMPOS ADICIONAIS SE FOR PJ
                    # ===============================
                    cnpj, nome_empresa = None, None
                    if tipo_contratacao in ["PJ1", "PJ2"]:
                        col1, col2 = st.columns([3, 2])
                        nome_empresa = col1.text_input("Nome da empresa:", value=pessoa.get("nome_empresa", ""), key=f"editar_nome_empresa_{pessoa_id}")
                        cnpj = col2.text_input("CNPJ:", value=pessoa.get("cnpj", ""), placeholder="00.000.000/0000-00", key=f"editar_cnpj_{pessoa_id}")
                    
                    st.markdown("---")

                    opcoes_conta = ["", "Conta Corrente", "Conta Poupança", "Conta Salário"]

                    # Dados bancários

                    st.markdown("#### **Dados bancários**")
                    st.write("")

                    if tipo_contratacao in ["PJ1", "PJ2"]:

                        st.markdown("##### **Conta Pessoa Jurídica (PJ)**")

                        col1, col2 = st.columns(2)
                        banco_pj_nome = col1.text_input("Banco PJ:", value=pessoa.get("banco_pj", {}).get("nome_banco", ""))
                        banco_pj_agencia = col2.text_input("Agência PJ:", value=pessoa.get("banco_pj", {}).get("agencia", ""))

                        col1, col2 = st.columns(2)
                        banco_pj_conta = col1.text_input("Conta PJ:", value=pessoa.get("banco_pj", {}).get("conta", ""))
                        banco_pj_tipo = col2.selectbox(
                            "Tipo conta PJ:",
                            opcoes_conta,
                            index=opcoes_conta.index(pessoa.get("banco_pj", {}).get("tipo_conta", "")) 
                            if pessoa.get("banco_pj", {}).get("tipo_conta", "") in opcoes_conta else 0
                        )

                        st.write("")
                        st.write("")

                        st.markdown("##### **Conta Pessoa Física (PF)**")

                        col1, col2 = st.columns(2)
                        banco_pf_nome = col1.text_input("Banco PF:", value=pessoa.get("banco_pf", {}).get("nome_banco", ""))
                        banco_pf_agencia = col2.text_input("Agência PF:", value=pessoa.get("banco_pf", {}).get("agencia", ""))

                        col1, col2 = st.columns(2)
                        banco_pf_conta = col1.text_input("Conta PF:", value=pessoa.get("banco_pf", {}).get("conta", ""))
                        banco_pf_tipo = col2.selectbox(
                            "Tipo conta PF:",
                            opcoes_conta,
                            index=opcoes_conta.index(pessoa.get("banco_pf", {}).get("tipo_conta", "")) 
                            if pessoa.get("banco_pf", {}).get("tipo_conta", "") in opcoes_conta else 0
                        )

                    else:
                        # comportamento atual (CLT, estágio etc)
                        col1, col2 = st.columns(2)
                        nome_banco = col1.text_input("Nome do banco:", value=pessoa.get("banco", {}).get("nome_banco", ""))
                        agencia = col2.text_input("Agência:", value=pessoa.get("banco", {}).get("agencia", ""))

                        col1, col2 = st.columns(2)
                        conta = col1.text_input("Conta:", value=pessoa.get("banco", {}).get("conta", ""))
                        tipo_conta = col2.selectbox(
                            "Tipo de conta:",
                            opcoes_conta,
                            index=opcoes_conta.index(pessoa.get("banco", {}).get("tipo_conta", "")) 
                            if pessoa.get("banco", {}).get("tipo_conta", "") in opcoes_conta else 0
                        )
                    
                    st.divider()

                    # Permissões
                    st.write('**Permissões**')

                    # Roteamento de tipo de usuário especial
                    # Só o admin pode atribuir permissão para outro admin
                    if set(st.session_state.tipo_usuario) & {"admin"}:

                        # Opções possíveis para o campo "tipo de usuário"
                        opcoes_tipo_usuario = [
                            "coordenador(a)", "admin", "gestao_pessoas", "gestao_ferias", "supervisao_ferias", 
                            "gestao_pls", "gestao_doadores", "gestao_fundo_ecos", "gestao_viagens", "gestao_eventos"
                        ]

                    else: # Se não for admin, não aparece a permissão admin disponível
                        # Opções possíveis para o campo "tipo de usuário"
                        opcoes_tipo_usuario = [
                            "coordenador(a)", "gestao_pessoas", "gestao_ferias", "supervisao_ferias", 
                            "gestao_pls", "gestao_doadores", "gestao_fundo_ecos", "gestao_viagens", "gestao_eventos"
                        ]


                    # Recupera o campo "tipo de usuário" do banco (pode ser string ou lista)
                    tipo_usuario_raw = pessoa.get("tipo de usuário", "")

                    # Converte string separada por vírgulas para lista, ou mantém lista se já for
                    if isinstance(tipo_usuario_raw, str):
                        tipo_usuario_list = [item.strip() for item in tipo_usuario_raw.split(",")]
                    elif isinstance(tipo_usuario_raw, list):
                        tipo_usuario_list = [item.strip() for item in tipo_usuario_raw]
                    else:
                        tipo_usuario_list = []

                    # Filtra para garantir que só valores válidos estejam selecionados
                    tipo_usuario_default = [t for t in tipo_usuario_list if t in opcoes_tipo_usuario]

                    # Multiselect para tipo de usuário com valores padrão preenchidos
                    tipo_usuario = st.multiselect(
                        "Tipo de usuário:",
                        options=opcoes_tipo_usuario,
                        default=tipo_usuario_default,
                        key=f"editar_tipo_usuario_{pessoa_id}"
                    )


                    with st.expander("Ver tipos de permissões"):

                        col1, col2 = st.columns([1, 1])


                        # admin
                        col1, col2 = st.columns([1, 2])
                        col1.write("**admin**")
                        col2.write("Tem todas as permissões.")

                        # gestao_pessoas
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_pessoas**")
                        col2.write("Faz a gestão de pessoas.")

                        # gestao_ferias
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_ferias**")
                        col2.write("Faz o registro de férias.")

                        # supervisao_ferias
                        col1, col2 = st.columns([1, 2])
                        col1.write("**supervisao_ferias**")
                        col2.write("Visualiza detalhes das férias de todos(as).")

                        # gestao_noticias
                        # col1, col2 = st.columns([1, 2])
                        # col1.write("**gestao_noticias**")
                        # col2.write("Faz triagem de notícias.")

                        # gestao_pls
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_pls**")
                        col2.write("Faz a gestão dos Projetos de Lei monitorados.")

                        # gestao_doadores
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_doadores**")
                        col2.write("Faz a gestão de doadores.")

                        # gestao_fundo_ecos
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_fundo_ecos**")
                        col2.write("Faz a gestão dos projetos e editais do Fundo Ecos.")

                        # gestao_viagens
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_viagens**")
                        col2.write("Pode ver os dados de todas as viagens.")

                    st.write('')

                    # -------------------------------
                    # Botão salvar
                    # -------------------------------
                    if st.form_submit_button(
                        "Salvar alterações",
                        type="secondary",
                        icon=":material/save:"
                    ):

                        dados_update = {
                            "nome_completo": nome,
                            "CPF": cpf,
                            "RG": rg,
                            "data_nascimento": data_nascimento.strftime("%d/%m/%Y") if data_nascimento else None,
                            "telefone": telefone,
                            "e_mail": email,
                            "gênero": genero,
                            "raca": raca,
                            "escolaridade": escolaridade,
                            "programa_area": programa_area,
                            "coordenador": coordenador_id,
                            "cargo": cargo,
                            "tipo_contratacao": tipo_contratacao,
                            "escritorio": escritorio,
                            "tipo de usuário": ", ".join(tipo_usuario) if tipo_usuario else "",
                            "status": status,
                        }

                        if tipo_contratacao in ["PJ1", "PJ2"]:

                            dados_update["cnpj"] = cnpj
                            dados_update["nome_empresa"] = nome_empresa

                            dados_update["banco_pj"] = {
                                "nome_banco": banco_pj_nome,
                                "agencia": banco_pj_agencia,
                                "conta": banco_pj_conta,
                                "tipo_conta": banco_pj_tipo
                            }

                            dados_update["banco_pf"] = {
                                "nome_banco": banco_pf_nome,
                                "agencia": banco_pf_agencia,
                                "conta": banco_pf_conta,
                                "tipo_conta": banco_pf_tipo
                            }

                            # remove banco antigo
                            dados_update["banco"] = None

                            pessoas.update_one(
                                {"_id": pessoa["_id"]},
                                {"$set": dados_update}
                            )

                        else:

                            dados_update["banco"] = {
                                "nome_banco": nome_banco,
                                "agencia": agencia,
                                "conta": conta,
                                "tipo_conta": tipo_conta
                            }

                            pessoas.update_one(
                                {"_id": pessoa["_id"]},
                                {
                                    "$set": dados_update,
                                    "$unset": {"cnpj": "", "nome_empresa": "", "banco_pj": "", "banco_pf": ""}
                                }
                            )

                        st.success("Informações atualizadas com sucesso!", icon=":material/check_circle:")
                        time.sleep(2)
                        st.rerun(scope="fragment")


        # ABA CONTRATOS ###############################################################################
        
        with aba_contratos:

            # PREPARAÇÃO DE VARIÁVEIS ------------------------------------------------------
            # Lista de projetos
            lista_projetos = sorted([
                p["sigla"] for p in dados_projetos_ispn if p.get("sigla", "")
            ])

            # Lista de contratos da pessoa selecionada
            if pessoa:
                contratos = pessoa.get("contratos", [])
            else:
                contratos = []


            # Lista de meses em português
            meses_pt = [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
            ]

            # Opções de status
            status_opcoes = [
                "Em vigência", "Encerrado", "Cancelado", "Fonte de recurso temporária"
            ]
            
            # ---------------- RECURSO GARANTIDO ATÉ ----------------

            data_recurso_db = pessoa.get("recurso_garantido_ate") if pessoa else None

            data_recurso_dt = None
            if isinstance(data_recurso_db, str) and data_recurso_db:
                try:
                    data_recurso_dt = datetime.datetime.strptime(
                        data_recurso_db, "%d/%m/%Y"
                    ).date()
                except:
                    data_recurso_dt = None
                    
            with st.container(border=False, horizontal=False):

                nova_data_recurso = st.date_input(
                    "Recurso garantido até:",
                    value=data_recurso_dt,   # None → campo vazio
                    format="DD/MM/YYYY",
                    key=f"recurso_garantido_{pessoa_id}",
                    width=250
                )

                if st.button(
                    "Salvar",
                    icon=":material/save:",
                    key=f"salvar_recurso_{pessoa_id}",
                ):
                    pessoas.update_one(
                        {"_id": pessoa["_id"]},
                        {
                            "$set": {
                                "recurso_garantido_ate": (
                                    nova_data_recurso.strftime("%d/%m/%Y")
                                    if nova_data_recurso
                                    else None
                                )
                            }
                        }
                    )
                    st.success("Data atualizada!", width=250, icon=":material/check:")
                    time.sleep(2)
                    st.rerun(scope="fragment")
                    
            st.write("")
            st.write("")

            # Expander de adicionar contrato -------------------------------------------------------

            with st.expander("Adicionar contrato", expanded=False, icon=":material/add_circle:"):
                
                
                # Projeto pagador
                cols = st.columns([3, 1])

                projetos_pagadores_nomes_edit = cols[0].multiselect(
                    "Contratado(a) pelo(s) projeto(s):",
                    lista_projetos
                )
                projetos_pagadores_edit = [
                    sigla_para_id_projeto.get(sigla)
                    for sigla in projetos_pagadores_nomes_edit
                    if sigla and sigla_para_id_projeto.get(sigla)
                ]


                # Status do contrato
                status_contrato = cols[1].selectbox("Status do contrato:", status_opcoes)



                cols = st.columns(3)
                inicio_contrato = cols[0].date_input("Data de início do contrato:", format="DD/MM/YYYY", value="today")
                fim_contrato = cols[1].date_input("Data de fim do contrato:", format="DD/MM/YYYY", value=None)
                data_reajuste = cols[2].selectbox("Mês de reajuste:", meses_pt)

                anotacoes_contrato = st.text_area("Anotações sobre o contrato:")

                # lista_status_contrato = ["Em vigência", "Encerrado", "Cancelado", "Fonte de recurso temporária", ""]

                #data_reajuste = col3.date_input("Data de reajuste:", format="DD/MM/YYYY")

                if st.button("Adicionar contrato", icon=":material/note_add:"):
                    novo_contrato = {
                        "data_inicio": inicio_contrato.strftime("%d/%m/%Y") if inicio_contrato else "",
                        "data_fim": fim_contrato.strftime("%d/%m/%Y") if fim_contrato else "",
                        "status_contrato": status_contrato,
                        "projeto_pagador": projetos_pagadores_edit,
                        "data_reajuste": data_reajuste,                  
                        "anotacoes_contrato": anotacoes_contrato        
                    }

                    contratos.append(novo_contrato)

                    # Atualiza no MongoDB
                    pessoas.update_one(
                        {"_id": ObjectId(pessoa["_id"])},
                        {"$set": {"contratos": contratos}}
                    )

                    st.success("Novo contrato adicionado com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")

            # CONTRATOS ------------------------------------------------------------

            st.write('')
            st.write('**Contratos:**')

            # CARD DE CADA CONTRATO ------------------------------------------------------------
            for i, contrato in enumerate(contratos):
                contrato_key = f"contrato_{pessoa['_id']}_{i}"
                toggle_key = f"toggle_edicao_contrato_{contrato_key}"

                with st.container(border=True):
                    projetos_ids = contrato.get("projeto_pagador", [])

                    # Toggle para modo edição
                    modo_edicao = st.toggle("Editar", key=toggle_key, value=False)

                    col1, col2 = st.columns([1, 2])

                    # ---------------- COLUNA 1 ----------------
                    with col1:
                        if modo_edicao:
                            contrato["status_contrato"] = st.selectbox(
                                "Status",
                                options=status_opcoes,
                                index=status_opcoes.index(contrato.get("status_contrato", "Em vigência"))
                                if contrato.get("status_contrato") in status_opcoes else 0,
                                key=f"status_{contrato_key}"
                            )

                            # Data início
                            data_inicio_valor = contrato.get("data_inicio")
                            data_inicio_dt = None
                            if isinstance(data_inicio_valor, str) and data_inicio_valor:
                                try:
                                    data_inicio_dt = datetime.datetime.strptime(data_inicio_valor, "%d/%m/%Y").date()
                                except:
                                    pass
                            contrato["data_inicio"] = st.date_input(
                                "Data de início",
                                value=data_inicio_dt or datetime.date.today(),
                                format="DD/MM/YYYY",
                                key=f"inicio_{contrato_key}"
                            ).strftime("%d/%m/%Y")

                            # Data fim
                            data_fim_valor = contrato.get("data_fim")
                            data_fim_dt = None
                            if isinstance(data_fim_valor, str) and data_fim_valor:
                                try:
                                    data_fim_dt = datetime.datetime.strptime(data_fim_valor, "%d/%m/%Y").date()
                                except:
                                    pass
                            contrato["data_fim"] = st.date_input(
                                "Data de fim",
                                value=data_fim_dt or datetime.date.today(),
                                format="DD/MM/YYYY",
                                key=f"fim_{contrato_key}"
                            ).strftime("%d/%m/%Y")

                            # Mês reajuste
                            contrato["data_reajuste"] = st.selectbox(
                                "Mês de reajuste",
                                options=meses_pt,
                                index=meses_pt.index(contrato.get("data_reajuste", "Janeiro"))
                                if contrato.get("data_reajuste") in meses_pt else 0,
                                key=f"reajuste_{contrato_key}"
                            )

                        else:
                            st.write("**Status:**", contrato.get("status_contrato", ""))
                            st.write("**Data de início:**", contrato.get("data_inicio", ""))
                            st.write("**Data de fim:**", contrato.get("data_fim", ""))
                            st.write("**Mês de reajuste:**", contrato.get("data_reajuste", ""))

                    # ---------------- COLUNA 2 ----------------
                    with col2:
                        st.write('**Projeto(s) pagador(es):**')

                        if modo_edicao:
                            siglas_selecionadas = [
                                p["sigla"] for p in dados_projetos_ispn
                                if p["_id"] in projetos_ids and p.get("sigla")
                            ]

                            siglas_escolhidas = st.multiselect(
                                "Selecione os projetos pagadores",
                                options=lista_projetos,
                                default=siglas_selecionadas,
                                key=f"multiselect_{contrato_key}"
                            )

                            contrato["projeto_pagador"] = [
                                p["_id"] for p in dados_projetos_ispn if p.get("sigla") in siglas_escolhidas
                            ]

                            contrato["anotacoes_contrato"] = st.text_area(
                                "Anotações sobre o contrato",
                                value=contrato.get("anotacoes_contrato", ""),
                                key=f"anotacoes_{contrato_key}"
                            )

                        else:
                            if not projetos_ids:
                                st.write("O projeto pagador não foi informado")
                            else:
                                for projeto_id in projetos_ids:
                                    projeto = next(
                                        (p for p in dados_projetos_ispn if p["_id"] == projeto_id),
                                        None
                                    )
                                    if projeto:
                                        st.write(f"{projeto.get('sigla', '')} - {projeto.get('nome_do_projeto', '')}")
                                    else:
                                        st.write(f"Projeto não encontrado para o ID: {projeto_id}")

                            if contrato.get("anotacoes_contrato"):
                                st.write("**Anotações:**")
                                st.write(contrato["anotacoes_contrato"])

                    # ---------------- BOTÃO DE SALVAR ----------------
                    if modo_edicao:
                        if st.button("Salvar alterações", key=f"salvar_{contrato_key}", icon=":material/save:"):
                            try:
                                pessoas.update_one(
                                    {"_id": pessoa["_id"]},
                                    {
                                        "$set": {
                                            f"contratos.{i}": contrato  # substitui só o contrato i
                                        }
                                    }
                                )
                                st.success("Contrato atualizado com sucesso!")
                                time.sleep(2)
                                st.rerun(scope="fragment")
                            except Exception as e:
                                st.error(f"Erro ao salvar no banco: {e}")


        # ABA ANOTAÇÕES ############################################################################### 
        with aba_anotacoes:

            usuario_logado = st.session_state.get("nome", "Desconhecido")
            if pessoa:
                anotacoes = pessoa.get("anotacoes", [])
            else:
                anotacoes = []

            # ---------------- EXPANDER PARA ADICIONAR ANOTAÇÃO ----------------
            with st.expander("Adicionar nova anotação", expanded=False, icon=":material/add_notes:"):
                
                nova_data = st.date_input("Data da anotação", value=datetime.date.today(), format="DD/MM/YYYY", width=150)
                novo_texto = st.text_area("Texto da anotação")

                if st.button("Adicionar anotação", key="add_anotacao", icon=":material/add_notes:"):
                    if novo_texto.strip():
                        nova_anotacao = {
                            "data_anotacao": nova_data.strftime("%d/%m/%Y %H:%M"),
                            "autor": usuario_logado,
                            "anotacao": novo_texto.strip()
                        }
                        anotacoes.append(nova_anotacao)
                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"anotacoes": anotacoes}}
                        )
                        st.success("Nova anotação adicionada com sucesso!")
                        time.sleep(2)
                        st.rerun(scope="fragment")
                    else:
                        st.warning("O campo da anotação não pode estar vazio.")




            # ---------------- LISTA DE ANOTAÇÕES EXISTENTES ----------------
            st.write('')
            st.write("**Anotações:**")

            # Ordena as anotações por data decrescente
            anotacoes_ordenadas = []
            for idx, a in enumerate(anotacoes):
                data_str = a.get("data_anotacao", "")
                data_dt = datetime.datetime.min
                if data_str:
                    try:
                        data_dt = datetime.datetime.strptime(data_str.split()[0], "%d/%m/%Y")
                    except:
                        pass
                anotacoes_ordenadas.append((idx, data_dt, a))

            # Ordena decrescente
            anotacoes_ordenadas.sort(key=lambda x: x[1], reverse=True)


            # CARD DE CADA ANOTAÇÃO ---------------------------------------------------------------

            for original_idx, _, anotacao in anotacoes_ordenadas:
                container_key = f"anotacao_{pessoa['_id']}_{original_idx}"
                toggle_key = f"toggle_edicao_anotacao_{container_key}"
                delete_key = f"delete_confirm_{container_key}"

                with st.container(border=True):
                    modo_edicao = st.toggle("Editar", key=toggle_key, value=False)

                    if modo_edicao:
                        # Editar data
                        data_valor = anotacao.get("data_anotacao")
                        data_dt = datetime.date.today()
                        if isinstance(data_valor, str) and data_valor:
                            try:
                                data_dt = datetime.datetime.strptime(data_valor.split()[0], "%d/%m/%Y").date()
                            except:
                                pass

                        nova_data = st.date_input(
                            "Data da anotação",
                            value=data_dt,
                            format="DD/MM/YYYY",
                            key=f"data_{container_key}", 
                            width=150
                        )

                        novo_texto = st.text_area(
                            "Texto da anotação",
                            value=anotacao.get("anotacao", ""),
                            key=f"texto_{container_key}"
                        )


                        # BOTÕES

                        linha_botoes = st.container(horizontal=True)

                        # Botão salvar
                        if linha_botoes.button("Salvar alterações", key=f"salvar_{container_key}", icon=":material/save:"):
                            anotacoes[original_idx]["data_anotacao"] = nova_data.strftime("%d/%m/%Y")
                            anotacoes[original_idx]["anotacao"] = novo_texto.strip()
                            pessoas.update_one(
                                {"_id": ObjectId(pessoa["_id"])},
                                {"$set": {"anotacoes": anotacoes}}
                            )
                            st.success("Anotação atualizada com sucesso!")
                            time.sleep(2)
                            st.rerun(scope="fragment")

                        # Botão deletar
                        if linha_botoes.button("Deletar anotação", key=f"deletar_{container_key}", icon=":material/delete:"):
                            st.session_state[delete_key] = True

                        # Confirmação de exclusão


                        if st.session_state.get(delete_key, False):
                            st.warning("Você tem certeza que deseja apagar essa anotação?")

                            # Container horizontal para os dois botões
                            botoes_confirmacao = st.container(horizontal=True)

                            # Botão "Sim"
                            if botoes_confirmacao.button("Sim, quero apagar", key=f"confirmar_delete_{container_key}", icon=":material/check:"):
                                try:
                                    anotacoes.pop(original_idx)
                                    pessoas.update_one(
                                        {"_id": ObjectId(pessoa["_id"])},
                                        {"$set": {"anotacoes": anotacoes}}
                                    )
                                    st.success("Anotação apagada com sucesso!")
                                    st.session_state[delete_key] = False
                                    time.sleep(2)
                                    st.rerun(scope="fragment")

                                except Exception as e:
                                    st.error(f"Erro ao apagar anotação: {e}")
                                    st.session_state[delete_key] = False

                            # Botão "Não"
                            if botoes_confirmacao.button("Não", key=f"cancelar_delete_{container_key}", icon=":material/close:"):
                                st.session_state[delete_key] = False
                                time.sleep(2)
                                st.rerun(scope="fragment")


                    else:
                        # Visualização normal
                        data_str = anotacao.get('data_anotacao', '')
                        if data_str:
                            data_str = data_str.split()[0]  # remove hora
                        col1, col2 = st.columns([1,3])
                        with col1:
                            st.write(f"**Data:** {data_str}")
                        with col2:
                            st.write(f"**Autor:** {anotacao.get('autor', '')}")
                        st.write(anotacao.get("anotacao", ""))


######################################################################################################
# TRATAMENTO DOS DADOS
######################################################################################################


# Verifica se há programas sem coordenador e completa ---------------------------------

programas_sem_coordenador = [
    prog for prog in dados_programas if not prog.get("coordenador_id")
]

if programas_sem_coordenador:
    atualizacoes = []

    for programa in programas_sem_coordenador:
        nome_programa = programa.get("nome_programa_area")
        coordenador_id = programa.get("coordenador_id")

        if not coordenador_id:
            # Busca coordenador correspondente ao programa
            for pessoa in colaboradores_raw:
                programas_ids = pessoa.get("programa_area", [])

                if not isinstance(programas_ids, list):
                    programas_ids = [programas_ids] if programas_ids else []

                nomes_programas_pessoa = [
                    mapa_id_para_nome_programa.get(str(pid), "")
                    for pid in programas_ids
                ]

                if (
                    pessoa.get("tipo de usuário", "").strip().lower() == "coordenador"
                    and nome_programa in nomes_programas_pessoa
                ):

                    novo_id = pessoa["_id"]
                    atualizacoes.append(UpdateOne(
                        {"_id": programa["_id"]},
                        {"$set": {"coordenador_id": novo_id}}
                    ))
                    break  # Parar no primeiro coordenador compatível encontrado

    # Executa as atualizações em lote
    if atualizacoes:
        resultado = programas_areas.bulk_write(atualizacoes)

# PREPARAÇÃO DOS DADOS PARA MONTAR AS ABAS

# Lista com nomes dos coordenadores, para filtrar da equipe
nomes_coordenadores = set()

lista_programas = []

for doc in dados_programas:
    # Verifica se o documento é um programa simples ou tem subprogramas embutidos
    programas_embutidos = doc.get("nome_programa_area")
    if not isinstance(programas_embutidos, list):
        programas_embutidos = [doc] if isinstance(doc, dict) else []

    for programa in programas_embutidos:
        if not isinstance(programa, dict):
            continue

        coordenador_id = programa.get("coordenador_id")
        nome_coordenador = colaborador_id_para_nome.get(str(coordenador_id)) or ""
        nomes_coordenadores.add(nome_coordenador)

        genero_coordenador = "Não informado"
        for colab_doc in colaboradores_raw:
            if str(colab_doc.get("_id")) == str(coordenador_id):
                genero_coordenador = colab_doc.get("gênero", "Não informado")
                break

        lista_programas.append({
            "titulo": programa.get("nome_programa_area", "Sem título"),
            "coordenador": nome_coordenador,
            "genero_coordenador": genero_coordenador,
            "id": str(programa.get("_id", ""))
        })

# Remove "Anterior aos programas"
lista_programas = [item for item in lista_programas if item["titulo"] != "Anterior aos programas"]

# Move "Coordenação" para o início, se existir
lista_programas.sort(key=lambda x: 0 if x["titulo"] == "Coordenação" else 1)

titulos_abas = [p['titulo'] for p in lista_programas if p.get('titulo')]


# PREPARAÇÃO DOS DADOS PARA MONTAR A EQUIPE

lista_equipe = []

STATUS_CONTRATOS_VALIDOS = [
    "Em vigência",
    "Fonte de recurso temporária"
]

for colab_doc in colaboradores_raw:

    if colab_doc.get("status", "").lower() != "ativo":
        continue

    nome = colab_doc.get("nome_completo", "Desconhecido")
    genero = colab_doc.get("gênero", "Não informado")
    cargo = colab_doc.get("cargo", "Não informado")

    programa_area_ids = colab_doc.get("programa_area", [])

    # compatibilidade com dados antigos
    if not isinstance(programa_area_ids, list):
        programa_area_ids = [programa_area_ids] if programa_area_ids else []

    programa_area = ", ".join(
        sorted([
            mapa_id_para_nome_programa.get(str(pid), "")
            for pid in programa_area_ids
            if str(pid) in mapa_id_para_nome_programa
        ])
    ) or "Não informado"

    contratos = colab_doc.get("contratos", [])

    projetos_lista = []
    datas_inicio_lista = []
    datas_fim_lista = []

    for contrato in contratos:

        if contrato.get("status_contrato") not in STATUS_CONTRATOS_VALIDOS:
            continue

        # Datas do contrato
        try:
            di = datetime.datetime.strptime(contrato.get("data_inicio", ""), "%d/%m/%Y")
            df = datetime.datetime.strptime(contrato.get("data_fim", ""), "%d/%m/%Y")
        except:
            continue

        # Projetos do contrato (na ordem)
        siglas_contrato = []
        for pid in contrato.get("projeto_pagador", []):
            sigla = mapa_id_para_sigla_projeto.get(str(pid))
            if sigla:
                siglas_contrato.append(sigla)

        if not siglas_contrato:
            continue

        # Junta os projetos do contrato
        projetos_lista.extend(siglas_contrato)

        # Datas entram UMA ÚNICA VEZ por contrato
        datas_inicio_lista.append(di.strftime("%d/%m/%Y"))
        datas_fim_lista.append(df.strftime("%d/%m/%Y"))


    # Strings finais (mesma ordem)
    projeto_str = ", ".join(projetos_lista)
    data_inicio_final = ", ".join(datas_inicio_lista) if datas_inicio_lista else None
    data_fim_final = ", ".join(datas_fim_lista) if datas_fim_lista else None



    lista_equipe.append({
        "Nome": nome,
        "Gênero": genero,
        "Cargo": cargo,
        "Programa": programa_area,
        "Projeto": projeto_str,
        "Início do contrato": data_inicio_final,
        "Fim do contrato": data_fim_final
    })


# Dataframe de equipe
df_equipe = pd.DataFrame(lista_equipe)

df_equipe = pd.DataFrame(lista_equipe).sort_values("Nome")

df_equipe_exibir = df_equipe.copy()

if set(st.session_state.get("tipo_usuario", [])) & {"admin", "coordenador(a)", "gestao_pessoas"}:

    # Dataframe completo    
    df_equipe_exibir = df_equipe[
        ["Nome", "Gênero", "Cargo", "Projeto", "Início do contrato", "Fim do contrato"]
    ].copy()

else:
    # Dataframe sem datas de contrato
    df_equipe_exibir = df_equipe[
        ["Nome", "Gênero", "Cargo", "Projeto"]
    ].copy()


# #############################################
# Início da Interface
# #############################################


st.header("Programas e Áreas")

st.write("")
st.write("")

abas = st.tabs(titulos_abas)


# Cria a aba para cada programa ------------------------------
for i, aba in enumerate(abas):
    with aba:

        programa = lista_programas[i]
        titulo_programa = programa['titulo']
        id_programa = programa['id'] 

        

        # Filtra o df_equipe para o programa atual

        # Filtra no df original (que tem a coluna 'Programa')
        df_equipe_filtrado = df_equipe[
            df_equipe['Programa'].str.contains(titulo_programa, na=False)
        ].copy()

        # Para exibir, pega só as linhas do df_equipe_exibir correspondentes
        df_equipe_exibir_filtrado = df_equipe_exibir.loc[df_equipe_filtrado.index].copy()
        df_equipe_exibir_filtrado.index = range(1, len(df_equipe_exibir_filtrado) + 1)

        # Prepara genero e prefixo só pra pronomes de tratamento na tela
        if not programa["coordenador"]:
            prefixo = ""
        else:
            genero = programa['genero_coordenador']
            prefixo = (
                "Coordenador" if genero == "Masculino"
                else "Coordenadora" if genero == "Feminino"
                else "Coordenador(a)"
            )

        st.write("")

        programas_dialog = list(programas_areas.find({}))

        # ---------------------------------------------
        # CONTROLE DE PERMISSÃO
        # ---------------------------------------------

        usuario_id = str(st.session_state.get("id_usuario"))
        tipos_usuario = set(st.session_state.get("tipo_usuario", []))

        # Busca o programa no banco (para garantir coordenador atualizado)
        programa_doc = programas_areas.find_one({"_id": ObjectId(id_programa)})
        coordenador_programa_id = str(programa_doc.get("coordenador_id", ""))

        # Regra de permissão
        pode_gerenciar = (
            usuario_id == coordenador_programa_id
            or "admin" in tipos_usuario
        )

        # ---------------------------------------------
        # BOTÃO
        # ---------------------------------------------

        if pode_gerenciar:

            container_botoes = st.container(horizontal=True, horizontal_alignment="right")

            container_botoes.button(
                "Gerenciar programa",
                key=f"btn_gerenciar_{programa['id']}",
                on_click=lambda prog=programa: gerenciar_programa_dialog(prog),
                width=260,
                icon=":material/contract_edit:"
            )


        col1, col2 = st.columns([2, 1])

        with col1:
            
            # Nome do programa
            st.subheader(f"{titulo_programa}")
            
            # Coordenador(a)
            if programa["coordenador"]:
                st.write(f"**{prefixo}:** {programa['coordenador']}")
            else:
                st.write("")
                st.write("")

            # Equipe --------------------------------------------------------------------------
            st.write('')
            st.markdown('#### **Equipe**')
            st.write(f'{len(df_equipe_exibir_filtrado)} colaboradores(as):')

        with col2:

            # Gráfico de pizza por gênero
            cores = {
                "Masculino": "#ADD8E6",    # azul claro
                "Feminino": "#FFC0CB",     # rosa claro
                "Não binário": "#C6F4D6",  # verde claro
                "Outro": "#F5F5DC",        # bege claro
            }

            fig = px.pie(
                df_equipe_exibir_filtrado,
                names='Gênero',
                values=None,        # opcional, pode usar contagem automática
                color='Gênero',     # <-- necessário para que color_discrete_map funcione
                color_discrete_map=cores,
                # diminuir o tamanho do gráfico
                width=250,
                height=250
            )

            st.plotly_chart(fig, key=f"pizza_genero_{i}")


        # Tabela de colaboradores
        df_tabela = df_equipe_exibir_filtrado.copy()

        colunas_contrato = {"Início do contrato", "Fim do contrato"}

        colunas_existentes = colunas_contrato & set(df_tabela.columns)

        if colunas_existentes:
            df_tabela[list(colunas_existentes)] = (
                df_tabela[list(colunas_existentes)].fillna("")
            )

        def criar_callback_equipe(df_visivel, key_df):

            def handle_selecao():
                estado = st.session_state.get(key_df, {})
                linhas = estado.get("selection", {}).get("rows", [])

                if not linhas:
                    st.session_state["pessoa_selecionada"] = None
                    return

                idx = linhas[0]

                nome = df_visivel.iloc[idx]["Nome"]

                pessoa_encontrada = next(
                    (p for p in colaboradores_raw if p.get("nome_completo") == nome),
                    None
                )

                if pessoa_encontrada:
                    st.session_state["pessoa_selecionada"] = str(pessoa_encontrada["_id"])
                    st.session_state["abrir_dialog_pessoa"] = True

            return handle_selecao
        
        usuario_id = str(st.session_state.get("id_usuario"))
        tipos_usuario = set(st.session_state.get("tipo_usuario", []))

        programa_doc = programas_areas.find_one({"_id": ObjectId(id_programa)})
        coordenador_programa_id = str(programa_doc.get("coordenador_id", ""))

        pode_editar_pessoas = (
            usuario_id == coordenador_programa_id
            or "admin" in tipos_usuario
            or "gestao_pessoas" in tipos_usuario
        )
        
        # Cria uma key única para o dataframe da equipe
        key_df = f"df_equipe_programa_{id_programa}"
        
        if pode_editar_pessoas:

            callback = criar_callback_equipe(df_tabela, key_df)

            st.dataframe(
                df_tabela,
                hide_index=True,
                selection_mode="single-row",
                on_select=callback,
                key=key_df
            )

        else:
            # Somente visualização
            st.dataframe(
                df_tabela,
                hide_index=True
            )
        
        pessoa_sel = st.session_state.get("pessoa_selecionada")

        if st.session_state.get("abrir_dialog_pessoa") and pessoa_sel:

            gerenciar_pessoas(pessoa_sel)

            st.session_state["abrir_dialog_pessoa"] = False

        # Gráfico timeline de contratos de pessoas
        
        if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)", "gestao_pessoas"}:

            linhas_timeline = []

            for colab_doc in colaboradores_raw:

                if colab_doc.get("status", "").lower() != "ativo":
                    continue

                nome = colab_doc.get("nome_completo", "Desconhecido")
                
                programa_area_ids = colab_doc.get("programa_area", [])

                if not isinstance(programa_area_ids, list):
                    programa_area_ids = [programa_area_ids] if programa_area_ids else []

                nomes_programas = [
                    mapa_id_para_nome_programa.get(str(pid), "")
                    for pid in programa_area_ids
                ]

                if titulo_programa not in nomes_programas:
                    continue

                for contrato in colab_doc.get("contratos", []):

                    if contrato.get("status_contrato") not in STATUS_CONTRATOS_VALIDOS:
                        continue

                    try:
                        data_inicio = datetime.datetime.strptime(
                            contrato.get("data_inicio", ""), "%d/%m/%Y"
                        )
                        data_fim = datetime.datetime.strptime(
                            contrato.get("data_fim", ""), "%d/%m/%Y"
                        )
                    except:
                        continue

                    projetos = []
                    for pid in contrato.get("projeto_pagador", []):
                        sigla = mapa_id_para_sigla_projeto.get(str(pid))
                        if sigla:
                            projetos.append(sigla)

                    projeto_str = ", ".join(projetos) if projetos else "Sem projeto"

                    linhas_timeline.append({
                        "Nome": nome,
                        "Projeto": projeto_str,
                        "Início do contrato": data_inicio,
                        "Fim do contrato": data_fim
                    })
            

            # Ordenar por ordem decrescente de data_fim_contrato
            if "Fim do contrato" in df_equipe_exibir_filtrado.columns:
                df_equipe_exibir_filtrado = df_equipe_exibir_filtrado.sort_values(
                    by="Fim do contrato",
                    ascending=False
                )

            # Tentando calcular a altura do gráfico dinamicamente
            altura_base = 300  # altura mínima
            altura_extra = sum([10 / (1 + i * 0.01) for i in range(len(df_equipe_exibir_filtrado))])
            altura = int(altura_base + altura_extra)
        
            
            df_timeline = pd.DataFrame(linhas_timeline)

            if df_timeline.empty:
                st.caption("Nenhum contrato ativo para exibir no timeline.")
            else:
                # Ordena pelo fim do contrato
                df_timeline = df_timeline.sort_values(
                    by="Fim do contrato",
                    ascending=False
                )

                # Altura dinâmica
                altura_base = 300
                altura = altura_base + len(df_timeline) * 20

                fig = px.timeline(
                    df_timeline,
                    x_start="Início do contrato",
                    x_end="Fim do contrato",
                    y="Nome",
                    color="Projeto",
                    hover_data=["Projeto"],
                    height=altura
                )

                fig.update_traces(
                    opacity=0.6,
                )

                fig.update_layout(yaxis_title=None)
                fig.add_vline(
                    x=datetime.date.today(),
                    line_width=1,
                    line_dash="dash",
                    line_color="gray"
                )

                st.plotly_chart(fig, key=f"timeline_pessoas_{i}")

        st.divider()

        # PROJETOS #################################################################################################

        st.write('')
        st.markdown("#### **Projetos**")

        col1, col2, col3 = st.columns(3)
        situacao_filtro = col1.selectbox(
            "Situação",
            ["Todos", "Em andamento", "Finalizado", ""],
            index=1,
            key=f"situacao_{i}"
        )

        projetos_do_programa = [
            p for p in dados_projetos_ispn
            if str(id_programa) in normalizar_lista_ids(p.get("programas", []))
        ]

        # Ordena por código
        projetos_do_programa_ordenados = sorted(
            projetos_do_programa,
            key=lambda p: p.get("codigo", "")
        )

        # Aplica o filtro de situação
        if situacao_filtro != "Todos":
            projetos_do_programa_ordenados = [
                p for p in projetos_do_programa_ordenados
                if p.get("status", "Não informado") == situacao_filtro
            ]

        if projetos_do_programa_ordenados:
            dados_projetos = {
                "Sigla": [],
                "Nome do projeto": [],
                "Início": [],
                "Fim": [],
                "Valor": [],
                "Doador": [],
                "Situação": []
            }

            for projeto in projetos_do_programa_ordenados:
                # Usa a sigla como identificador principal (resolve problema de busca)
                dados_projetos["Sigla"].append(projeto.get("sigla", ""))
                dados_projetos["Nome do projeto"].append(projeto.get("nome_do_projeto", "Sem nome"))
                dados_projetos["Início"].append(projeto.get("data_inicio_contrato", "Não informado"))
                dados_projetos["Fim"].append(projeto.get("data_fim_contrato", "Não informado"))

                valor_bruto = projeto.get("valor", 0) or 0
                moeda_bruta = projeto.get("moeda", "reais")  # padrão "reais" caso não exista
                valor_formatado = formatar_valor(valor_bruto, moeda_bruta)
                dados_projetos["Valor"].append(valor_formatado)

                id_doador = projeto.get("doador")
                nome_doador = mapa_doador_id_para_nome.get(str(id_doador), "Não informado")
                dados_projetos["Doador"].append(nome_doador)

                dados_projetos["Situação"].append(projeto.get("status", "Não informado"))

            df_projetos = pd.DataFrame(dados_projetos)
            df_projetos.index += 1
            quantidade = len(df_projetos)
            plural = "projetos vinculados" if quantidade != 1 else "projeto vinculado"

            areas = ["Comunicação", "ADM Brasília", "ADM Santa Inês", "Advocacy", "Coordenação"]

            if titulo_programa in areas:
                st.write(f"{quantidade} {plural} à área **{titulo_programa}**:")
            else:
                st.write(f"{quantidade} {plural} ao programa **{titulo_programa}**:")
                
            
            def criar_callback_projeto_programa(df_visivel, key_df):

                def handle_selecao():
                    estado = st.session_state.get(key_df, {})
                    linhas = estado.get("selection", {}).get("rows", [])

                    # Se desmarcar → limpa
                    if not linhas:
                        st.session_state["projeto_selecionado"] = None
                        return

                    idx = linhas[0]

                    # Aqui usamos o código (ou sigla)
                    sigla = df_visivel.iloc[idx]["Sigla"]

                    st.session_state["projeto_selecionado"] = sigla
                    st.session_state["abrir_dialog_projeto"] = True

                return handle_selecao
            
            usuario_id = str(st.session_state.get("id_usuario"))
            tipos_usuario = set(st.session_state.get("tipo_usuario", []))

            programa_doc = programas_areas.find_one({"_id": ObjectId(id_programa)})
            coordenador_programa_id = str(programa_doc.get("coordenador_id", ""))

            pode_editar = (
                usuario_id == coordenador_programa_id
                or "admin" in tipos_usuario
            )

            df_original = df_projetos.copy()

            key_df = f"df_projetos_programa_{id_programa}"

            if pode_editar:

                callback = criar_callback_projeto_programa(
                    df_projetos,
                    key_df
                )

                st.dataframe(
                    df_projetos,
                    hide_index=True,
                    selection_mode="single-row",
                    on_select=callback,
                    key=key_df
                )

            else:
                # Usuário comum → somente visualização
                st.dataframe(
                    df_projetos,
                    hide_index=True
                )
            
            projeto_selecionado = st.session_state.get("projeto_selecionado")

            if st.session_state.get("abrir_dialog_projeto") and projeto_selecionado:

                dialog_editar_projeto()

                st.session_state["abrir_dialog_projeto"] = False
                
        else:
            # cria o df_projetos vazio
            df_projetos = pd.DataFrame({
                "Código": [],
                "Nome do projeto": [],
                "Início": [],
                "Fim": [],
                "Valor": [],
                "Doador": [],
                "Situação": []
            })
            st.caption("Nenhum projeto")



        if not df_projetos.empty:
            # Gráfico timeline com plotly express, com um projeto por linha

            # Tentando calcular a altura do gráfico dinamicamente
            altura_base = 300  # altura mínima
            altura_extra = sum([10 / (1 + i * 0.01) for i in range(len(df_projetos))])
            altura = int(altura_base + altura_extra)

            # Converte para datetime
            df_projetos['Início'] = pd.to_datetime(df_projetos['Início'], dayfirst=True)
            df_projetos['Fim'] = pd.to_datetime(df_projetos['Fim'], dayfirst=True)

            # Ordena os projetos em ordem decrescente da data de fim do contrato
            df_projetos = df_projetos.sort_values(by='Fim', ascending=False)

            fig = px.timeline(
                df_projetos,
                x_start="Início",
                x_end="Fim",
                y="Sigla",
                color="Situação",
                hover_data=["Sigla"],
                height=altura
            )

            fig.update_layout(
                yaxis_title=None,
            )
            fig.add_vline(x=datetime.date.today(), line_width=1, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, key=f"timeline_projetos_{i}")

        st.divider()

        # AÇÕES ESTRATÉGICAS DO PROGRAMA ################################################################
        
        st.markdown("#### **Ações Estratégicas do Programa**")

        # ===============================
        # FILTROS DE ENTREGAS DO PROGRAMA
        # ===============================

        with st.form(f"filtros_entregas_programa_{id_programa}", border=False):

            col1, col2, col3 = st.columns(3)

            # Projetos (siglas) — apenas do programa
            siglas_programa = sorted({
                e["projeto_sigla"]
                for e in entregas_base
                if str(id_programa) in e["programas_ids"] and e["projeto_sigla"]
            })

            with col1:
                filtro_entregas_projetos = st.multiselect(
                    "Projeto",
                    options=siglas_programa,
                    default=st.session_state.get(f"filtro_entregas_projetos_{id_programa}", []),
                    placeholder=""
                )

            # Situação
            situacoes_programa = sorted({
                e["situacao"]
                for e in entregas_base
                if str(id_programa) in e["programas_ids"] and e["situacao"]
            })

            with col2:
                filtro_entregas_situacoes = st.multiselect(
                    "Situação",
                    options=situacoes_programa,
                    default=st.session_state.get(f"filtro_entregas_situacoes_{id_programa}", []),
                    placeholder=""
                )

            # Ano de referência
            anos_programa = sorted({
                ano
                for e in entregas_base
                if str(id_programa) in e["programas_ids"]
                for ano in e["anos_referencia"]
            })

            with col3:
                filtro_entregas_anos = st.multiselect(
                    "Ano",
                    options=anos_programa,
                    default=st.session_state.get(f"filtro_entregas_anos_{id_programa}", []),
                    placeholder=""
                )

            aplicar = st.form_submit_button(
                "Aplicar filtros",
                icon=":material/filter_alt:"
            )

        if aplicar:
            st.session_state[f"filtro_entregas_projetos_{id_programa}"] = filtro_entregas_projetos
            st.session_state[f"filtro_entregas_situacoes_{id_programa}"] = filtro_entregas_situacoes
            st.session_state[f"filtro_entregas_anos_{id_programa}"] = filtro_entregas_anos
            st.rerun()

        # ===============================
        # FILTROS DE ENTREGAS (ISOLADOS)
        # ===============================

        filtro_entregas_projetos = st.session_state.get(
            f"filtro_entregas_projetos_{id_programa}", []
        )

        filtro_entregas_situacoes = st.session_state.get(
            f"filtro_entregas_situacoes_{id_programa}", []
        )

        filtro_entregas_anos = st.session_state.get(
            f"filtro_entregas_anos_{id_programa}", []
        )


        # 1. Busca a estratégia do programa atual
        estrategia_programa = db.programas_areas.find_one({
            "nome_programa_area": titulo_programa
        })

        if not estrategia_programa or not estrategia_programa.get("acoes_estrategicas"):
            st.caption("Nenhuma ação estratégica cadastrada para este programa.")
  
        else:

            st.write("")

            acoes_estrategicas = estrategia_programa["acoes_estrategicas"]

            # 2. Buscar todos os projetos do programa novamente (coleção projetos_ispn)
            programa_id = ObjectId(programa.get("id"))

            projetos_com_entregas = []

            for p in db.projetos_ispn.find({"programas": programa_id}):

                sigla_proj = p.get("sigla", "")

                # -----------------------------
                # FILTRO DE PROJETOS (SIGLA)
                # -----------------------------
                if filtro_entregas_projetos and sigla_proj not in filtro_entregas_projetos:
                    continue

                projetos_com_entregas.append(p)

            # 3. Loop pelas ações estratégicas
            for i, acao in enumerate(acoes_estrategicas):
                nome_acao = acao["acao_estrategica"]

                with st.expander(nome_acao, expanded=True):

                    entregas_relacionadas = []

                    for projeto_doc in projetos_com_entregas:

                        sigla_projeto = projeto_doc.get("sigla", "")
                        codigo_projeto = projeto_doc.get("codigo", "")
                        nome_projeto = projeto_doc.get("nome_do_projeto", "")

                        for entrega_doc in projeto_doc.get("entregas", []):

                            acao_id = str(acao["_id"])

                            ids_acoes_da_entrega = normalizar_lista_ids(
                                entrega_doc.get("acoes_relacionadas", [])
                            )

                            if acao_id not in ids_acoes_da_entrega:
                                continue

                            # -----------------------------
                            # APLICA FILTROS DE ENTREGA
                            # -----------------------------

                            # Filtro por projeto
                            if filtro_entregas_projetos and sigla_projeto not in filtro_entregas_projetos:
                                continue

                            # Filtro por situação
                            if filtro_entregas_situacoes:
                                if entrega_doc.get("situacao") not in filtro_entregas_situacoes:
                                    continue

                            # Filtro por ano
                            if filtro_entregas_anos:
                                anos_entrega = entrega_doc.get("anos_de_referencia", []) or []
                                if not set(anos_entrega) & set(filtro_entregas_anos):
                                    continue
                            
                            progresso = entrega_doc.get("progresso")
                            progresso_formatado = (
                                f"{progresso}%" if progresso not in [None, ""] else ""
                            )

                            # -----------------------------
                            # ENTREGA VÁLIDA → EXIBE
                            # -----------------------------

                            entregas_relacionadas.append({
                                "Projeto": sigla_projeto,
                                "Entrega": entrega_doc.get("nome_da_entrega", ""),
                                "Situação": entrega_doc.get("situacao", ""),
                                "Previsão": entrega_doc.get("previsao_da_conclusao", ""),
                                "Ano(s) de Referência": ", ".join(map(str, sorted(entrega_doc.get("anos_de_referencia", [])))),
                                "Progresso": progresso_formatado
                            })

                    if entregas_relacionadas:

                        st.markdown("**Entregas:**")

                        df_entregas = pd.DataFrame(entregas_relacionadas)

                        ui.table(
                            data=df_entregas,
                            maxHeight=400,
                            key=f"tabela_entregas_{id_programa}_{acao_id}"   # key só aqui
                        )

                    else:
                        st.caption("Nenhuma entrega vinculada a esta ação estratégica do programa.")