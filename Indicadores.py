import streamlit as st
import pandas as pd
import datetime
import time
from bson import ObjectId
from funcoes_auxiliares import conectar_mongo_portal_ispn, ajustar_altura_dataframe


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
projetos_pj = db["projetos_pj"]
projetos_pf = db["projetos_pf"]
projetos_ispn = db["projetos_ispn"]
indicadores = db["indicadores"]
lancamentos = db["lancamentos_indicadores"]
pessoas = db["pessoas"]
estrategia = db["estrategia"]
estatistica = db["estatistica"] 


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_indicadores"
nome_pagina = "Indicadores"

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
# CSS PARA DIALOGO MAIOR
######################################################################################################


st.markdown(
    """
<style>
div[data-testid="stDialog"] div[role="dialog"]:has(.big-dialog) {
    width: 90vw;
    height: 65vh;
}
</style>
""",
    unsafe_allow_html=True,
)


######################################################################################################
# FUNÇÕES
######################################################################################################


def formatar_brasileiro(valor):
    try:
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip('0').rstrip(',')
    except:
        return valor


@st.cache_data(ttl=300, show_spinner=False)
def somar_indicador_por_nome(nome_indicador, tipo_selecionado=None, _projetos_filtrados=None, anos_filtrados=None, autores_filtrados=None):
    indicador_doc = indicadores.find_one({"nome_indicador": nome_indicador})
    if not indicador_doc:
        return "" if nome_indicador == "especies" else "0"

    indicador_id = indicador_doc["_id"]

    filtro = {"id_do_indicador": indicador_id}
    if tipo_selecionado:
        filtro["tipo"] = {"$in": tipo_selecionado}
    if projetos_filtrados:
        filtro["projeto"] = {"$in": projetos_filtrados}
    if anos_filtrados:
        filtro["ano"] = {"$in": anos_filtrados}
    if autores_filtrados:
        filtro["autor_anotacao"] = {"$in": autores_filtrados}

    # Exceção para espécies: não soma, retorna apenas o valor original (string)
    if nome_indicador == "especies":
        doc = lancamentos.find_one(filtro)
        if doc:
            return doc.get("valor", "")
        else:
            return ""

    # Para os demais indicadores, soma normalmente
    total = 0
    for doc in lancamentos.find(filtro):
        valor = doc.get("valor", "")
        try:
            if isinstance(valor, (int, float)):
                total += valor
            elif isinstance(valor, str) and valor.strip() != "":
                total += float(valor.replace(".", "").replace(",", "."))
        except ValueError:
            pass

    if total == 0:
        return "0"
    return formatar_brasileiro(total)



# --- Função otimizada para pegar siglas de vários projetos ---
def ids_para_siglas(ids_por_tipo):
    """
    Recebe um dicionário {tipo: [lista de ObjectIds]} e retorna um dict {id_str: sigla}
    """
    from bson import ObjectId

    resultado = {}
    for tipo, lista_ids in ids_por_tipo.items():
        if not lista_ids:
            continue

        # Seleciona a coleção correta
        if tipo == "PJ":
            colecao = projetos_pj
        elif tipo == "PF":
            colecao = projetos_pf
        else:
            colecao = projetos_ispn

        # Consulta todos de uma vez
        docs = colecao.find(
            {"_id": {"$in": lista_ids}},
            {"sigla": 1}
        )

        for doc in docs:
            resultado[str(doc["_id"])] = doc.get("sigla", "")

    return resultado


@st.dialog("Lançamentos", width="large")
def mostrar_detalhes(nome_indicador, tipo_selecionado=None, projetos_filtrados=None, anos_filtrados=None, autores_filtrados=None):
    #st.html("<span class='big-dialog'></span>")

    indicador_doc = indicadores.find_one({"nome_indicador": nome_indicador})
    if not indicador_doc:
        st.warning("Indicador não encontrado.")
        return

    st.subheader(f"{nome_indicador}")

    indicador_id = indicador_doc["_id"]

    filtro = {"id_do_indicador": indicador_id}
    if tipo_selecionado:
        filtro["tipo"] = {"$in": tipo_selecionado}
    if projetos_filtrados:
        filtro["projeto"] = {"$in": projetos_filtrados}
    if anos_filtrados:
        filtro["ano"] = {"$in": anos_filtrados}
    if autores_filtrados:
        filtro["autor_anotacao"] = {"$in": autores_filtrados}

    lancs = list(lancamentos.find(filtro))
    if not lancs:
        st.write("")
        st.write("")
        st.caption("**Nenhum lançamento encontrado para este indicador**")

        return

    df = pd.DataFrame(lancs)

    # Guardar o ObjectId original
    df["Projeto_id"] = df["projeto"]
    
    # Converter data_anotacao de datetime para string DD/MM/YYYY
    if "data_anotacao" in df.columns:
        df["data_anotacao"] = pd.to_datetime(df["data_anotacao"], errors="coerce")
        df["data_anotacao"] = df["data_anotacao"].dt.strftime("%d/%m/%Y")
        df["data_anotacao"] = df["data_anotacao"].fillna("")

    # Renomear colunas para exibição
    colunas_mapeadas = {
        "projeto": "Projeto",
        "ano": "Ano",
        "valor": "Valor",
        "autor_anotacao": "Autor",
        "data_anotacao": "Data da Anotação",
        "observacoes": "Observações"
    }
    for col in colunas_mapeadas.keys():
        if col not in df.columns:
            df[col] = ""
    df.rename(columns=colunas_mapeadas, inplace=True)
    
    # ==========================================================
    # Converter coluna "Valor" para float (tratando strings BR)
    # ==========================================================
    if "Valor" in df.columns:

        def converter_para_float(v):
            """
            Converte valores para float tratando:
            - int / float nativos
            - strings no padrão brasileiro (1.234,56)
            - valores vazios ou inválidos
            """
            try:
                if isinstance(v, (int, float)):
                    return float(v)
                
                if isinstance(v, str):
                    v = v.strip()
                    if v == "":
                        return None
                    
                    # remove separador de milhar e troca vírgula por ponto
                    v = v.replace(".", "").replace(",", ".")
                    return float(v)

            except:
                return None

            return None

        df["Valor"] = df["Valor"].apply(converter_para_float)

    # Criar coluna Código
    df["Projeto"] = df["Projeto_id"].astype(str).map(id_para_codigo).fillna("Sem código")

    # Criar coluna Sigla — consulta única por tipo
    ids_por_tipo = {}
    for _, row in df.iterrows():
        tipo = row.get("tipo", "")
        if tipo not in ids_por_tipo:
            ids_por_tipo[tipo] = []
        ids_por_tipo[tipo].append(row["Projeto_id"])

    # Remover duplicados
    for t in ids_por_tipo:
        ids_por_tipo[t] = list(set(ids_por_tipo[t]))

    siglas_dict = ids_para_siglas(ids_por_tipo)
    df["Sigla"] = df["Projeto_id"].astype(str).map(siglas_dict).fillna("Sem sigla")

    df["Observações"] = df["Observações"].fillna("")

    # Reordenar
    colunas_exibir = ["Projeto", "Sigla", "Ano", "Valor", "Autor", "Data da Anotação", "Observações"]
    df = df[colunas_exibir].sort_values("Projeto")

    #st.dataframe(df, hide_index=True, use_container_width=True, height=597)
    ajustar_altura_dataframe(df, 1, 597)
    



def botao_indicador_legivel(titulo, nome_indicador, tipo, projetos, anos, autores):
    valor = somar_indicador_por_nome(nome_indicador, tipo, projetos, anos, autores)
    
    if nome_indicador.lower() == "especies":
        # Exibe o botão apenas se houver algum valor
        if valor:  # verifica se não é vazio ou None
            st.button(
                f"{titulo}",
                on_click=lambda: mostrar_detalhes(nome_indicador, tipo, projetos, anos, autores),
                type="tertiary"
            )
            
    else:
        # Para os demais indicadores, mantém a lógica atual
        if valor != "0":
            st.button(
                f"{titulo}: **{valor}**",
                on_click=lambda: mostrar_detalhes(nome_indicador, tipo, projetos, anos, autores),
                type="tertiary"
            )


def atualizar_filtro_interativo(campo, opcoes, label):
    selecao_antiga = st.session_state.filtros_indicadores[campo]
    selecao_nova = st.multiselect(
        label,
        opcoes,
        default=selecao_antiga,
        key=f"multiselect_{campo}",
        placeholder=""
    )
    if set(selecao_nova) != set(selecao_antiga):
        st.session_state.filtros_indicadores[campo] = selecao_nova
        st.rerun()


@st.cache_data(ttl=600, show_spinner=False)
def carregar_projetos():
    projetos_todos = []
    for coll in [projetos_ispn, projetos_pf, projetos_pj]:
        projetos_todos.extend(list(coll.find({}, {"_id": 1, "bioma": 1, "sigla": 1, "programa": 1,  "edital": 1})))
    return projetos_todos


@st.cache_data(ttl=600, show_spinner=False)
def carregar_lancamentos():
    return list(lancamentos.find())


@st.cache_data(ttl=600, show_spinner=False)
def carregar_programas():
    return list(db["programas_areas"].find({}, {"_id": 1, "nome_programa_area": 1}))

@st.dialog("Gerenciar indicadores", width="large", on_dismiss="rerun")   
def gerenciar_indicadores():

    # =======================================================
    # CARREGAR CATEGORIAS EXISTENTES DO BANCO
    # =======================================================
    categorias_existentes = sorted(list({
        i.get("categoria_indicador", "").strip() 
        for i in indicadores.find({}, {"categoria_indicador": 1}) 
        if i.get("categoria_indicador")
    }))

    # =======================================================
    # FUNÇÃO AUXILIAR: CARREGAR OPÇÕES DINÂMICAS
    # =======================================================
    
    def carregar_opcoes_estrategia():
        estrategia_doc = estrategia.find_one({"estrategia": {"$exists": True}})
        resultados_mp_doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
        resultados_lp_doc = estrategia.find_one({"resultados_longo_prazo": {"$exists": True}})

        mapa_eixos = {}
        mapa_mp = {}
        mapa_lp = {}

        # -------------------------
        # EIXOS DA ESTRATÉGIA
        # -------------------------
        if estrategia_doc:
            for e in estrategia_doc.get("estrategia", {}).get("eixos_da_estrategia", []):
                mapa_eixos[str(e["_id"])] = e.get("titulo", "")

        # -------------------------
        # RESULTADOS MÉDIO PRAZO
        # -------------------------
        if resultados_mp_doc:
            for r in resultados_mp_doc.get("resultados_medio_prazo", {}).get("resultados_mp", []):
                mapa_mp[str(r["_id"])] = r.get("titulo", "")

        # -------------------------
        # RESULTADOS LONGO PRAZO
        # -------------------------
        if resultados_lp_doc:
            for r in resultados_lp_doc.get("resultados_longo_prazo", {}).get("resultados_lp", []):
                mapa_lp[str(r["_id"])] = r.get("titulo", "")

        return mapa_eixos, mapa_mp, mapa_lp

    
    mapa_eixos, mapa_mp, mapa_lp = carregar_opcoes_estrategia()

    opcoes_eixos = list(mapa_eixos.keys())
    opcoes_mp = list(mapa_mp.keys())
    opcoes_lp = list(mapa_lp.keys())


    if set(st.session_state.tipo_usuario) & {"admin"}:

        tab_add, tab_edit = st.tabs([
            ":material/add: Adicionar", 
            ":material/edit: Editar"
        ])

        # =======================================================
        # ABA ADICIONAR
        # =======================================================
        with tab_add:
            st.subheader("Adicionar novo indicador")

            col1, col2, col3 = st.columns([2,1,1])

            nome_indicador = col1.text_input("Nome do indicador")

            categoria_indicador = col2.selectbox(
                "Categoria do indicador",
                options=categorias_existentes,
                index=None,
                placeholder=""
            )

            tipo_variavel = col3.selectbox(
                "Tipo de variável",
                options=["str", "int", "float"],
                index=None,
                placeholder=""
            )

            st.write("")

            if st.button("Adicionar indicador", use_container_width=False, icon=":material/add:"):
                if not nome_indicador.strip():
                    st.warning("Digite um nome para o indicador.")
                elif not tipo_variavel:
                    st.warning("Selecione o tipo de variável.")
                else:
                    novo_indicador = {
                        "nome_indicador": nome_indicador.strip(),
                        "categoria_indicador": categoria_indicador.strip() if categoria_indicador else "",
                        "tipo_variavel": tipo_variavel,
                    }

                    indicadores.insert_one(novo_indicador)
                    st.success(f"Indicador **{nome_indicador}** adicionado com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")

        # =======================================================
        # ABA EDITAR
        # =======================================================
        with tab_edit:
            st.subheader("Editar indicador existente")

            indicadores_lista = list(indicadores.find().sort("nome_indicador", 1))
            nomes_indicadores = [i["nome_indicador"] for i in indicadores_lista]

            if not nomes_indicadores:
                st.warning("Nenhum indicador cadastrado.")
            else:
                col1, col2, col3 = st.columns([2, 1, 1])

                nome_indicador_selecionado = col1.selectbox(
                    "Selecione o indicador para editar:",
                    nomes_indicadores,
                    index=None,
                    placeholder=""
                )

                if nome_indicador_selecionado:
                    indicador_doc = next(i for i in indicadores_lista if i["nome_indicador"] == nome_indicador_selecionado)
                    
                    opcoes_tipo_variavel = ["str", "int", "float"]
                    tipo_variavel_atual = indicador_doc.get("tipo_variavel")
                    categoria = col2.selectbox(
                        "Categoria do indicador",
                        options=categorias_existentes,
                        index=categorias_existentes.index(indicador_doc.get("categoria_indicador"))
                        if indicador_doc.get("categoria_indicador") in categorias_existentes else None,
                        placeholder=""
                    )
                    tipo_variavel = col3.selectbox(
                        "Tipo de variável",
                        options=opcoes_tipo_variavel,
                        index=opcoes_tipo_variavel.index(tipo_variavel_atual)
                        if tipo_variavel_atual in opcoes_tipo_variavel else None,
                        placeholder="",
                        key=f"tipo_variavel_{indicador_doc['_id']}"
                    )

                    def filtrar_valores_validos(valores, opcoes):
                        if not isinstance(valores, list):
                            return []
                        return [v for v in valores if v in opcoes]

                    st.write("")

                    # Botões de ação
                    col1, col2 = st.columns(2)
                
                    if col1.button("Salvar alterações", use_container_width=False, icon=":material/save:"):
                        indicadores.update_one(
                            {"_id": indicador_doc["_id"]},
                            {"$set": {
                                "categoria_indicador": categoria,
                                "tipo_variavel": tipo_variavel,
                            }}
                        )
                        st.success("Indicador atualizado com sucesso!")
                        time.sleep(2)
                        st.rerun(scope="fragment")

    else:
        st.subheader("Editar indicador existente")

        indicadores_lista = list(indicadores.find().sort("nome_indicador", 1))
        nomes_indicadores = [i["nome_indicador"] for i in indicadores_lista]

        if not nomes_indicadores:
            st.warning("Nenhum indicador cadastrado.")
        else:
            col1, col2, col3 = st.columns([2, 1, 1])

            nome_indicador_selecionado = col1.selectbox(
                "Selecione o indicador para editar:",
                nomes_indicadores,
                index=None,
                placeholder=""
            )

            if nome_indicador_selecionado:
                indicador_doc = next(i for i in indicadores_lista if i["nome_indicador"] == nome_indicador_selecionado)

                opcoes_tipo_variavel = ["str", "int", "float"]

                tipo_variavel_atual = indicador_doc.get("tipo_variavel")

                categoria = col2.selectbox(
                    "Categoria do indicador",
                    options=categorias_existentes,
                    index=categorias_existentes.index(indicador_doc.get("categoria_indicador"))
                    if indicador_doc.get("categoria_indicador") in categorias_existentes else None,
                    placeholder=""
                )

                tipo_variavel = col3.selectbox(
                    "Tipo de variável",
                    options=opcoes_tipo_variavel,
                    index=opcoes_tipo_variavel.index(tipo_variavel_atual)
                    if tipo_variavel_atual in opcoes_tipo_variavel else None,
                    placeholder="",
                    key=f"tipo_variavel_nonadmin_{nome_indicador_selecionado}"
                )

                def filtrar_valores_validos(valores, opcoes):
                    if not isinstance(valores, list):
                        return []
                    return [v for v in valores if v in opcoes]

        
                colabora_estrategia = st.multiselect(
                    "Colabora com quais eixos da estratégia?",
                    options=opcoes_eixos,
                    default=filtrar_valores_validos(indicador_doc.get("colabora_estrategia", []), opcoes_eixos),
                    placeholder="",
                    key=f"edit_estrategia_{nome_indicador_selecionado}"
                )

                colabora_resultado_mp = st.multiselect(
                    "Colabora com quais resultados de médio prazo?",
                    options=opcoes_mp,
                    default=filtrar_valores_validos(indicador_doc.get("colabora_resultado_mp", []), opcoes_mp),
                    placeholder="",
                    key=f"edit_mp_{nome_indicador_selecionado}"
                )
        
                colabora_resultado_lp = st.multiselect(
                    "Colabora com quais resultados de longo prazo?",
                    options=opcoes_lp,
                    default=filtrar_valores_validos(indicador_doc.get("colabora_resultado_lp", []), opcoes_lp),
                    placeholder="",
                    key=f"edit_lp_{nome_indicador_selecionado}"
                )

                st.write("")

                # Botões de ação
                col1, col2 = st.columns(2)
            
                if col1.button("Salvar alterações", use_container_width=False, icon=":material/save:"):
                    indicadores.update_one(
                        {"_id": indicador_doc["_id"]},
                        {"$set": {
                            "categoria_indicador": categoria,
                            "tipo_variavel": tipo_variavel,
                            "colabora_estrategia": [ObjectId(i) for i in colabora_estrategia],
                            "colabora_resultado_mp": [ObjectId(i) for i in colabora_resultado_mp],
                            "colabora_resultado_lp": [ObjectId(i) for i in colabora_resultado_lp],
                        }}
                    )

                    st.success("Indicador atualizado com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")
                


@st.dialog("Gerenciar lançamentos", width="large", on_dismiss="rerun")   
def gerenciar_lancamentos():
    tab_add, tab_edit, tab_delete = st.tabs([":material/add: Adicionar", ":material/edit: Editar", ":material/delete: Excluir"])
    
    # Pega o autor do session_state
    autor_nome = st.session_state.get("nome", "")
    
    # ------------------------- ABA ADICIONAR -------------------------
    with tab_add:
        st.subheader("Novo lançamento de indicador")
        tipo_projeto = st.selectbox(
            "Tipo de projeto",
            ["", "Fundo Ecos", "Projetos ISPN"],
            key="tipo_projeto_lanc"
        )

        subtipo = None
        
        if tipo_projeto == "Fundo Ecos":
            subtipo = st.selectbox(
                "Subtipo",
                ["", "PJ", "PF"],
                key="subtipo_projeto_lanc"
            )

        if (tipo_projeto == "Projetos ISPN") or (tipo_projeto == "Fundo Ecos" and subtipo in ["PJ", "PF"]):
            if tipo_projeto == "Projetos ISPN":
                colecao = projetos_ispn
                tipo_salvar = "ispn"
            elif subtipo == "PJ":
                colecao = projetos_pj
                tipo_salvar = "PJ"
            elif subtipo == "PF":
                colecao = projetos_pf
                tipo_salvar = "PF"
            else:
                st.warning("Selecione o subtipo para continuar.")
                st.stop()

            projetos_lista = list(colecao.find({}, {"_id": 1, "codigo": 1, "sigla": 1}))

            if not projetos_lista:
                st.warning("Nenhum projeto encontrado.")
                st.stop()

            projetos_opcoes = {
                f"{p.get('codigo', 'Sem código')} - {p.get('sigla', '')}": p["_id"]
                for p in projetos_lista
            }

            projeto_selecionado = st.selectbox(
                "Projeto",
                [""] + sorted(list(projetos_opcoes.keys()))
            )

            if projeto_selecionado != "":
                projeto_oid = projetos_opcoes[projeto_selecionado]

                indicadores_lista = list(indicadores.find({}, {"_id": 1, "nome_indicador": 1, "tipo_variavel": 1}))

                indicadores_opcoes = {
                    i["nome_indicador"]: i
                    for i in indicadores_lista
                }

                # Cria o selectbox com os nomes direto do banco
                indicador_nome_sel = st.selectbox(
                    "Indicador",
                    [""] + sorted(indicadores_opcoes.keys())
                )

                if indicador_nome_sel != "":
                    indicador_doc = indicadores_opcoes[indicador_nome_sel]
                    indicador_oid = indicador_doc["_id"]
                    tipo_variavel = indicador_doc.get("tipo_variavel")
                    
                    if not tipo_variavel:
                        st.warning("Este indicador não possui um tipo de variável definido. Edite-o em 'Gerenciar indicadores' antes de lançar valores.")
                    else:
                        with st.form(key="form_lancamento_indicador"):

                            col1, col2 = st.columns(2)

                            # lógica de input para valor conforme tipo_variavel
                            if tipo_variavel == "str":
                                valor = col1.text_input("Valor")
                            elif tipo_variavel == "float":
                                valor = col1.number_input("Valor", value=0.00, step=0.01, format="%.2f")
                            else:  # int
                                valor = col1.number_input("Valor", value=0, step=1, format="%d")

                            # Ano
                            ano_atual = datetime.datetime.now().year
                            ano_maximo = ano_atual + 1
                            anos = ["até 2024"] + [str(ano) for ano in range(2025, ano_maximo + 1)]
                            ano = col2.selectbox("Ano", anos)

                            # Observações
                            observacoes = st.text_area("Observações", height=100)
                            submit = st.form_submit_button("Salvar lançamento")

                        if submit:
                            if not autor_nome:
                                st.warning("Nome do autor não encontrado no session_state.")
                                st.stop()

                            # conversão do valor para o tipo correto
                            if tipo_variavel == "float":
                                valor = float(valor)
                            elif tipo_variavel == "int":
                                valor = int(valor)

                            # se for str, mantém como está
                            novo_lancamento = {
                                "id_do_indicador": indicador_oid,
                                "projeto": projeto_oid,
                                "data_anotacao": datetime.datetime.now(),
                                "autor_anotacao": autor_nome,
                                "valor": valor,
                                "ano": str(ano),
                                "observacoes": observacoes,
                                "tipo": tipo_salvar
                            }

                            lancamentos.insert_one(novo_lancamento)
                            st.success("Lançamento salvo com sucesso.")
                            time.sleep(2)
                            st.cache_data.clear()
                            st.rerun(scope="fragment")
                else:
                    st.info("Por favor, selecione as opções acima para prosseguir.")
    
    # ------------------------- ABA EDITAR -------------------------
    with tab_edit:

        st.subheader("Editar lançamento")

        tipo_projeto_edit = st.selectbox(
            "Tipo de projeto",
            ["", "Fundo Ecos", "Projetos ISPN"],
            key="tipo_projeto_edit"
        )

        subtipo_edit = None
        if tipo_projeto_edit == "Fundo Ecos":
            subtipo_edit = st.selectbox(
                "Subtipo",
                ["", "PJ", "PF"],
                key="subtipo_projeto_edit"
            )

        if (tipo_projeto_edit == "Projetos ISPN") or (tipo_projeto_edit == "Fundo Ecos" and subtipo_edit in ["PJ", "PF"]):
            if tipo_projeto_edit == "Projetos ISPN":
                colecao = projetos_ispn
                tipo_salvar = "ispn"
            elif subtipo_edit == "PJ":
                colecao = projetos_pj
                tipo_salvar = "PJ"
            elif subtipo_edit == "PF":
                colecao = projetos_pf
                tipo_salvar = "PF"

            projetos_lista_edit = list(colecao.find({}, {"_id": 1, "codigo": 1, "sigla": 1}))

            projetos_opcoes_edit = {
                f"{p.get('codigo', 'Sem código')} - {p.get('sigla', '')}": p["_id"]
                for p in projetos_lista_edit
            }

            projeto_sel_edit = st.selectbox(
                "Projeto",
                [""] + sorted(list(projetos_opcoes_edit.keys())),
                key="projeto_edit"
            )

            if projeto_sel_edit != "":
                projeto_oid_edit = projetos_opcoes_edit[projeto_sel_edit]

                lancamentos_proj = list(
                    lancamentos.find({
                        "projeto": projeto_oid_edit,
                        "tipo": tipo_salvar,
                        "data_anotacao": {"$exists": True, "$ne": None, "$ne": ""}
                    }).sort("data_anotacao", -1)
                )

                # Filtrar lançamentos pelo autor, exceto para admins
                usuario_atual = st.session_state.get("nome", "")
                tipo_usuario = st.session_state.get("tipo_usuario", [])

                if "admin" not in tipo_usuario:
                    lancamentos_proj = [l for l in lancamentos_proj if l.get("autor_anotacao") == usuario_atual]
                if not lancamentos_proj:
                    st.info("Nenhum lançamento disponível para edição.")
                else:
                    lanc_opcoes_edit = {}

                    for l in lancamentos_proj:
                        indicador_doc = indicadores.find_one({"_id": l["id_do_indicador"]})
                        indicador_nome = indicador_doc["nome_indicador"] if indicador_doc else "Indicador desconhecido"
                        data_str = (
                            l["data_anotacao"].strftime('%d/%m/%Y %H:%M:%S') 
                            if isinstance(l["data_anotacao"], datetime.datetime) 
                            else "Sem data"
                        )

                        autor = l.get("autor_anotacao", "Sem autor")
                        label = f"{data_str} - {autor} - {indicador_nome}"
                        lanc_opcoes_edit[label] = l["_id"]

                    lanc_sel_edit = st.selectbox(
                        "Selecione o lançamento",
                        [""] + list(lanc_opcoes_edit.keys()),
                        key="lanc_sel_edit"
                    )

                    if lanc_sel_edit != "":

                        lanc_id_edit = lanc_opcoes_edit[lanc_sel_edit]
                        doc = lancamentos.find_one({"_id": lanc_id_edit})
                        indicador_doc_edit = indicadores.find_one({"_id": doc["id_do_indicador"]})
                        tipo_variavel_edit = indicador_doc_edit.get("tipo_variavel") if indicador_doc_edit else None
                        
                        col1, col2 = st.columns(2)

                        if tipo_variavel_edit == "str":
                            novo_valor = col1.text_input("Valor", value=str(doc["valor"]))
                        elif tipo_variavel_edit == "float":
                            valor_inicial = float(doc["valor"]) if doc["valor"] != "" else 0.00
                            novo_valor = col1.number_input("Valor", value=valor_inicial, step=0.01, format="%.2f")
                        else:  # int (também cobre indicadores sem tipo_variavel definido, como fallback)
                            valor_inicial = int(doc["valor"]) if str(doc["valor"]).isdigit() else 0
                            novo_valor = col1.number_input("Valor", value=valor_inicial, step=1, format="%d")
                        
                        # Ano
                        ano_atual = datetime.datetime.now().year
                        ano_maximo = ano_atual + 1
                        anos = ["até 2024"] + [str(ano) for ano in range(2025, ano_maximo + 1)]
                        ano_str = doc.get("ano", "2025")

                        if ano_str not in anos:
                            anos.insert(0, ano_str)
                        novo_ano = col2.selectbox("Ano", anos, index=anos.index(ano_str))

                        # Observações
                        novas_obs = st.text_area("Observações", value=doc.get("observacoes", ""))
                        if st.button("Salvar alterações", key="salvar_edit"):

                            if tipo_variavel_edit == "float":
                                novo_valor = float(novo_valor)
                            elif tipo_variavel_edit != "str":
                                novo_valor = int(novo_valor)
                            lancamentos.update_one(
                                {"_id": lanc_id_edit},
                                {"$set": {
                                    "valor": novo_valor,
                                    "ano": str(novo_ano),
                                    "observacoes": novas_obs
                                }}
                            )

                            st.success("Lançamento atualizado com sucesso!")
                            time.sleep(2)
                            st.cache_data.clear()
                            st.rerun(scope="fragment")
    
    # ------------------------- ABA EXCLUIR -------------------------
    with tab_delete:

        st.subheader("Excluir lançamento")

        tipo_projeto_delete = st.selectbox(
            "Tipo de projeto",
            ["", "Fundo Ecos", "Projetos ISPN"],
            key="tipo_projeto_delete"
        )

        subtipo_delete = None
        if tipo_projeto_delete == "Fundo Ecos":
            subtipo_delete = st.selectbox(
                "Subtipo",
                ["", "PJ", "PF"],
                key="subtipo_projeto_delete"
            )

        if (tipo_projeto_delete == "Projetos ISPN") or (tipo_projeto_delete == "Fundo Ecos" and subtipo_delete in ["PJ", "PF"]):
            if tipo_projeto_delete == "Projetos ISPN":
                colecao = projetos_ispn
                tipo_salvar = "ispn"
            elif subtipo_delete == "PJ":
                colecao = projetos_pj
                tipo_salvar = "PJ"
            elif subtipo_delete == "PF":
                colecao = projetos_pf
                tipo_salvar = "PF"

            projetos_lista_delete = list(colecao.find({}, {"_id": 1, "codigo": 1, "sigla": 1}))

            projetos_opcoes_delete = {
                f"{p.get('codigo', 'Sem código')} - {p.get('sigla', '')}": p["_id"]
                for p in projetos_lista_delete
            }

            projeto_sel_delete = st.selectbox(
                "Projeto",
                [""] + sorted(list(projetos_opcoes_delete.keys())),
                key="projeto_delete"
            )

            if projeto_sel_delete != "":

                projeto_oid_delete = projetos_opcoes_delete[projeto_sel_delete]
                lancamentos_proj = list(
                    lancamentos.find({
                        "projeto": projeto_oid_delete,
                        "tipo": tipo_salvar,
                        "data_anotacao": {"$exists": True, "$ne": None, "$ne": ""}
                    }).sort("data_anotacao", -1)
                )

                usuario_atual = st.session_state.get("nome", "")
                tipo_usuario = st.session_state.get("tipo_usuario", [])
                
                if "admin" not in tipo_usuario:
                    lancamentos_proj = [l for l in lancamentos_proj if l.get("autor_anotacao") == usuario_atual]
                if not lancamentos_proj:
                    st.info("Nenhum lançamento disponível para exclusão.")
                else:
                    lanc_opcoes_delete = {}

                    for l in lancamentos_proj:
                        indicador_doc = indicadores.find_one({"_id": l["id_do_indicador"]})
                        indicador_nome = indicador_doc["nome_indicador"] if indicador_doc else "Indicador desconhecido"

                        data_str = (
                            l["data_anotacao"].strftime('%d/%m/%Y %H:%M:%S') 
                            if isinstance(l["data_anotacao"], datetime.datetime) 
                            else "Sem data"
                        )

                        autor = l.get("autor_anotacao", "Sem autor")

                        label = f"{data_str} - {autor} - {indicador_nome}"

                        lanc_opcoes_delete[label] = l["_id"]

                    lanc_sel_delete = st.selectbox(
                        "Selecione o lançamento",
                        [""] + list(lanc_opcoes_delete.keys()),
                        key="lanc_sel_delete"
                    )

                    if lanc_sel_delete != "":

                        lanc_id_delete = lanc_opcoes_delete[lanc_sel_delete]

                        doc = lancamentos.find_one({"_id": lanc_id_delete})

                        indicador_id = doc.get("id_do_indicador") or doc.get("indicador")
                        indicador_nome_conf = "Indicador desconhecido"

                        if indicador_id:
                            indicador_doc_conf = indicadores.find_one({"_id": indicador_id}, {"nome_indicador": 1})

                            if indicador_doc_conf:
                                indicador_nome_conf = indicador_doc_conf.get("nome_indicador", "") or "Indicador"

                        valor_lanc = doc.get("valor", "Sem valor")

                        st.warning(
                            f"Tem certeza que deseja excluir o indicador registrado por "
                            f"{doc['autor_anotacao']} em {doc['data_anotacao'].strftime('%d/%m/%Y')}?\n\n"
                            f"**{indicador_nome_conf}**: {valor_lanc}"
                        )

                        if st.button("Excluir", key="excluir_lanc", icon=":material/delete:"):
                            lancamentos.delete_one({"_id": lanc_id_delete})
                            st.success("Lançamento excluído com sucesso!")
                            st.cache_data.clear()
                            st.rerun(scope="fragment")


def mapear_programas(lista_ids):
    """
    Converte lista de ObjectIds de programas para nomes legíveis.
    Sempre retorna lista (mesmo se vier vazio ou None).
    """
    if isinstance(lista_ids, list):
        return [map_programa_nome.get(i, "") for i in lista_ids if i in map_programa_nome]
    elif lista_ids:  # caso legado (1 valor só)
        return [map_programa_nome.get(lista_ids, "")]
    return []


######################################################################################################
# MAIN
######################################################################################################


st.header("Indicadores")
st.write('')

# Roteamento de tipo de usuário
if set(st.session_state.tipo_usuario) & {"admin", "gestao_fundo_ecos", "coordenador(a)"}:
    col1, col2, col3 = st.columns([3, 1, 1])
    col3.button("Gerenciar lançamentos", on_click=gerenciar_lancamentos, use_container_width=True, icon=":material/stylus_note:")

if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}:
    col2.button("Gerenciar indicadores", on_click=gerenciar_indicadores, use_container_width=True, icon=":material/stylus_note:")


# ===== FILTROS =====

projetos_todos = carregar_projetos()
todos_lancamentos = carregar_lancamentos()
programas = carregar_programas()

df_proj_info = pd.DataFrame(projetos_todos).rename(columns={"_id": "projeto"})
if "programa" not in df_proj_info.columns:
    df_proj_info["programa"] = ""

if "edital" not in df_proj_info.columns:
    df_proj_info["edital"] = ""

map_programa_nome = {p["_id"]: p["nome_programa_area"] for p in programas}

# Aplica corretamente
df_proj_info["programa"] = df_proj_info["programa"].apply(mapear_programas)

# Inicializa session_state se não existir
if "filtros_indicadores" not in st.session_state:
    st.session_state.filtros_indicadores = {}

# Garante que TODAS as chaves existam
for key in ["tipo", "autor_anotacao", "codigo", "ano", "bioma", "sigla", "programa", "edital"]:
    if key not in st.session_state.filtros_indicadores:
        st.session_state.filtros_indicadores[key] = []

# Carregar lançamentos
df_base = pd.DataFrame(todos_lancamentos)

# Cria dicionário id_string ➔ codigo
id_para_codigo = {}
for coll in [projetos_ispn, projetos_pf, projetos_pj]:
    for proj in coll.find({}, {"_id": 1, "codigo": 1}):
        id_para_codigo[str(proj["_id"])] = proj.get("codigo", "Sem código")

df_base["codigo"] = df_base["projeto"].astype(str).map(id_para_codigo)
df_base["autor_anotacao"] = df_base["autor_anotacao"].fillna("")
df_base["ano"] = df_base["ano"].fillna("")
df_base["codigo"] = df_base["codigo"].fillna("")
df_base = df_base.merge(df_proj_info, on="projeto", how="left")

# Preenche valores nulos com string vazia
df_base["bioma"] = df_base["bioma"].fillna("")
# Cria lista de todos os biomas separados por vírgula e remove espaços
todos_biomas = [b.strip() for sublist in df_base["bioma"].str.split(",") for b in sublist if b.strip()]
# Remove duplicatas e ordena
biomas_unicos = sorted(set(todos_biomas))

df_base["sigla"] = df_base["sigla"].fillna("")
df_base["programa"] = df_base["programa"].fillna("")
df_base["edital"] = df_base["edital"].fillna("")

def ordenar_editais(lista_editais):
    """
    Ordena editais numericamente, mesmo estando salvos como string.

    Exemplos:
    1
    2
    10
    13
    13.1
    14
    """

    def chave(valor):
        try:
            return float(str(valor).replace(",", "."))
        except:
            return float("inf")

    return sorted(lista_editais, key=chave)

with st.expander("Filtros", expanded=False, icon=":material/filter_alt:"):
    # ===== FORM DE FILTROS =====
    with st.form("filtros_form", border=False):
        tipo_selecionado = st.pills(
            label="Tipo de projeto",
            options=["PJ", "PF", "ispn"],
            selection_mode="multi",
            key="filtro_tipo",  # <-- chave do session_state
            format_func=lambda x: {"PJ": "PJ", "PF": "PF", "ispn": "ISPN"}.get(x, x),
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            sigla_sel = st.multiselect(
                "Filtrar por sigla / nome",
                sorted(df_base["sigla"].unique()),
                key="filtro_sigla",
                placeholder=""
            )
        with col2:
            codigo_sel = st.multiselect(
                "Filtrar por código",
                sorted(df_base["codigo"].unique()),
                key="filtro_codigo",
                placeholder=""
            )
        with col3:
            autor_sel = st.multiselect(
                "Filtrar por autor",
                sorted(df_base["autor_anotacao"].unique()),
                key="filtro_autor",
                placeholder=""
            )

        col4, col5, col6, col7 = st.columns(4)
        with col4:

            # Explode lista de programas em valores únicos
            todos_programas = sorted({
                prog
                for lista in df_base["programa"]
                for prog in (lista if isinstance(lista, list) else [])
                if prog
            })

            programa_sel = st.multiselect(
                "Filtrar por programa",
                todos_programas,
                key="filtro_programa",
                placeholder=""
            )

        with col5:
            edital_sel = st.multiselect(
                "Filtrar por edital",
                ordenar_editais([e for e in df_base["edital"].unique() if e]),
                key="filtro_edital",
                placeholder=""
            )
            
        with col6:
            bioma_sel = st.multiselect(
                "Filtrar por bioma",
                biomas_unicos,
                key="filtro_bioma",
                placeholder=""
            )
        with col7:
            ano_sel = st.multiselect(
                "Filtrar por ano",
                sorted(df_base["ano"].unique()),
                key="filtro_ano",
                placeholder=""
            )

        aplicar = st.form_submit_button("Aplicar filtros", icon=":material/check:", type="primary")

    # Atualiza session_state só ao clicar
    if aplicar:
        st.session_state.filtros_indicadores = {
            "tipo": st.session_state.filtro_tipo,
            "sigla": st.session_state.filtro_sigla,
            "codigo": st.session_state.filtro_codigo,
            "autor_anotacao": st.session_state.filtro_autor,
            "programa": st.session_state.filtro_programa,
            "bioma": st.session_state.filtro_bioma,
            "ano": st.session_state.filtro_ano,
            "edital": st.session_state.filtro_edital,
        }


    # ===== APLICA FILTROS =====
    df_filtrado = df_base.copy()

    for campo, selecao in st.session_state.filtros_indicadores.items():
        if selecao:
            if campo == "tipo":
                df_filtrado = df_filtrado[df_filtrado["tipo"].isin(selecao)]

            elif campo == "programa":
                df_filtrado = df_filtrado[
                    df_filtrado["programa"].apply(
                        lambda lista: any(p in selecao for p in lista)
                    )
                ]

            else:
                df_filtrado = df_filtrado[df_filtrado[campo].isin(selecao)]

    # Verifica se o filtro retornou algum resultado
    if df_filtrado.empty:
        st.warning("Nenhum resultado encontrado para os filtros selecionados.")
        # Evita continuar o processamento dos indicadores
        st.stop()

    # Extrai listas finais
    autores_filtrados = df_filtrado["autor_anotacao"].dropna().unique().tolist()
    anos_filtrados = df_filtrado["ano"].dropna().unique().tolist()

    # Projetos filtrados como ObjectId
    if st.session_state.filtros_indicadores["codigo"]:
        projetos_filtrados = [
            ObjectId(k) for k, v in id_para_codigo.items() 
            if v in st.session_state.filtros_indicadores["codigo"]
        ]
    else:
        projetos_filtrados = df_filtrado["projeto"].dropna().unique().tolist()


# ##########################################################
# GERAÇÃO AUTOMÁTICA DOS BLOCOS DE INDICADORES
# ##########################################################


# Sequência fixa dos blocos (categoria + coluna onde aparece),
# mantendo exatamente a ordem e distribuição atuais.
BLOCOS_CATEGORIAS = [
    {"categoria": "Alcance", "coluna": 1},
    {"categoria": "Pessoas", "coluna": 2},
    {"categoria": "Capacitações", "coluna": 1},
    {"categoria": "Intercâmbios", "coluna": 1},
    {"categoria": "Território", "coluna": 2},
    {"categoria": "Tecnologia e infra-estrutura", "coluna": 1},
    {"categoria": "Financeiro", "coluna": 1},
    {"categoria": "Comunicação", "coluna": 2},
    {"categoria": "Só projetos Fundo Ecos", "coluna": 1},
    {"categoria": "Incidência política e articulação", "coluna": 2},
]

@st.cache_data(ttl=600, show_spinner=False)
def carregar_indicadores_por_categoria():
    """
    Busca todos os indicadores do banco e agrupa por categoria_indicador,
    já ordenando os nomes alfabeticamente dentro de cada categoria.
    """

    docs = list(indicadores.find({}, {"nome_indicador": 1, "categoria_indicador": 1}))
    por_categoria = {}

    for d in docs:
        nome = d.get("nome_indicador", "")
        if not nome:
            continue
        categoria = (d.get("categoria_indicador") or "").strip() or "Sem categoria"
        por_categoria.setdefault(categoria, []).append(nome)

    for categoria in por_categoria:
        por_categoria[categoria] = sorted(por_categoria[categoria], key=lambda s: s.lower())

    return por_categoria

indicadores_por_categoria = carregar_indicadores_por_categoria()

col1, col2 = st.columns(2)
colunas = {1: col1, 2: col2}

categorias_ja_renderizadas = set()

for bloco in BLOCOS_CATEGORIAS:

    categoria = bloco["categoria"]
    categorias_ja_renderizadas.add(categoria)

    nomes_indicadores = indicadores_por_categoria.get(categoria, [])
    if not nomes_indicadores:
        continue

    # Regra especial: bloco "Projetos Fundo Ecos" só aparece
    # se não houver filtro de tipo ou se PJ/PF estiver selecionado
    if categoria == "Projetos Fundo Ecos":
        if tipo_selecionado and not any(t in ["PJ", "PF"] for t in tipo_selecionado):
            continue

    coluna = colunas[bloco["coluna"]]
    with coluna.container(border=True):
        st.write(f'**{categoria}**')
        for nome_indicador in nomes_indicadores:
            titulo = (
                "Espécies: clique para mais informações"
                if nome_indicador.lower() == "especies"
                else nome_indicador
            )
            botao_indicador_legivel(
                titulo, nome_indicador, tipo_selecionado,
                projetos_filtrados, anos_filtrados, autores_filtrados
            )

# ----------------------------------------------------------------
# Categorias novas que ainda não fazem parte da sequência definida
# acima aparecem ao final, em ordem alfabética de categoria
# ----------------------------------------------------------------

outras_categorias = sorted(
    [c for c in indicadores_por_categoria if c not in categorias_ja_renderizadas],
    key=lambda s: s.lower()
)

for categoria in outras_categorias:

    nomes_indicadores = indicadores_por_categoria[categoria]

    with col1.container(border=True):
        st.write(f'**{categoria}**')
        for nome_indicador in nomes_indicadores:
            botao_indicador_legivel(
                nome_indicador, nome_indicador, tipo_selecionado,
                projetos_filtrados, anos_filtrados, autores_filtrados
            )

