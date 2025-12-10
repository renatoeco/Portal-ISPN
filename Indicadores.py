import streamlit as st
import pandas as pd
import datetime
import time
from bson import ObjectId
from funcoes_auxiliares import conectar_mongo_portal_ispn, ajustar_altura_dataframe, formatar_nome_legivel


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


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


# # Nome da página atual, usado como chave para contagem de acessos
# nome_pagina = "Indicadores"

# # Cria um timestamp formatado com dia/mês/ano hora:minuto:segundo
# timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# # Cria o nome do campo dinamicamente baseado na página
# campo_timestamp = f"{nome_pagina}.Visitas"

# # Atualiza a coleção de estatísticas com o novo acesso, incluindo o timestamp
# estatistica.update_one(
#     {},
#     {"$push": {campo_timestamp: timestamp}},
#     upsert=True  # Cria o documento se ele ainda não existir
# )


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

    st.subheader(f"{formatar_nome_legivel(nome_indicador)}")

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
        st.info("Nenhum lançamento encontrado para este indicador.")
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
        projetos_todos.extend(list(coll.find({}, {"_id": 1, "bioma": 1, "sigla": 1, "programa": 1})))
    return projetos_todos


@st.cache_data(ttl=600, show_spinner=False)
def carregar_lancamentos():
    return list(lancamentos.find())


@st.cache_data(ttl=600, show_spinner=False)
def carregar_programas():
    return list(db["programas_areas"].find({}, {"_id": 1, "nome_programa_area": 1}))

@st.dialog("Gerenciar indicadores", width="large")   
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

        eixos = estrategia_doc.get("estrategia", {}).get("eixos_da_estrategia", []) if estrategia_doc else []
        opcoes_estrategia = [e["titulo"] for e in eixos]

        resultados_mp = resultados_mp_doc.get("resultados_medio_prazo", {}).get("resultados_mp", []) if resultados_mp_doc else []
        opcoes_mp = [r["titulo"] for r in resultados_mp]

        resultados_lp = resultados_lp_doc.get("resultados_longo_prazo", {}).get("resultados_lp", []) if resultados_lp_doc else []
        opcoes_lp = [r["titulo"] for r in resultados_lp]

        return opcoes_estrategia, opcoes_mp, opcoes_lp

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

            col1, col2 = st.columns([2,1])

            nome_indicador = col1.text_input("Nome do indicador (interno, sem acento)")

            categoria_indicador = col2.selectbox(
                "Categoria do indicador",
                options=categorias_existentes,
                index=None,
                placeholder=""
            )

            opcoes_estrategia, opcoes_mp, opcoes_lp = carregar_opcoes_estrategia()
            
            colabora_estrategia = st.multiselect(
                "Colabora com quais eixos da estratégia?",
                options=opcoes_estrategia,
                placeholder=""
            )

            colabora_resultado_mp = st.multiselect(
                "Colabora com quais resultados de médio prazo?",
                options=opcoes_mp,
                placeholder=""
            )

            colabora_resultado_lp = st.multiselect(
                "Colabora com quais resultados de longo prazo?",
                options=opcoes_lp,
                placeholder=""
            )

            st.write("")

            if st.button("Adicionar indicador", use_container_width=False, icon=":material/add:"):
                if not nome_indicador.strip():
                    st.warning("Digite um nome para o indicador.")
                else:
                    novo_indicador = {
                        "nome_indicador": nome_indicador.strip(),
                        "categoria_indicador": categoria_indicador.strip() if categoria_indicador else "",
                        "colabora_estrategia": colabora_estrategia,
                        "colabora_resultado_mp": colabora_resultado_mp,
                        "colabora_resultado_lp": colabora_resultado_lp
                    }
                    indicadores.insert_one(novo_indicador)
                    st.success(f"Indicador **{nome_indicador}** adicionado com sucesso!")
                    time.sleep(2)
                    st.rerun()

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
                col1, col2 = st.columns([2, 1])

                nome_indicador_selecionado = col1.selectbox(
                    "Selecione o indicador para editar:",
                    nomes_indicadores,
                    index=None,
                    placeholder=""
                )

                if nome_indicador_selecionado:
                    indicador_doc = next(i for i in indicadores_lista if i["nome_indicador"] == nome_indicador_selecionado)

                    categoria = col2.selectbox(
                        "Categoria do indicador",
                        options=categorias_existentes,
                        index=categorias_existentes.index(indicador_doc.get("categoria_indicador"))
                        if indicador_doc.get("categoria_indicador") in categorias_existentes else None,
                        placeholder=""
                    )

                    opcoes_estrategia, opcoes_mp, opcoes_lp = carregar_opcoes_estrategia()

                    def filtrar_valores_validos(valores, opcoes):
                        if not isinstance(valores, list):
                            return []
                        return [v for v in valores if v in opcoes]

            
                    colabora_estrategia = st.multiselect(
                        "Colabora com quais eixos da estratégia?",
                        options=opcoes_estrategia,
                        default=filtrar_valores_validos(indicador_doc.get("colabora_estrategia", []), opcoes_estrategia),
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
                                "colabora_estrategia": colabora_estrategia,
                                "colabora_resultado_mp": colabora_resultado_mp,
                                "colabora_resultado_lp": colabora_resultado_lp
                            }}
                        )
                        st.success("Indicador atualizado com sucesso!")
                        time.sleep(2)
                        st.rerun()

    else:
        st.subheader("Editar indicador existente")

        indicadores_lista = list(indicadores.find().sort("nome_indicador", 1))
        nomes_indicadores = [i["nome_indicador"] for i in indicadores_lista]

        if not nomes_indicadores:
            st.warning("Nenhum indicador cadastrado.")
        else:
            col1, col2 = st.columns([2, 1])

            nome_indicador_selecionado = col1.selectbox(
                "Selecione o indicador para editar:",
                nomes_indicadores,
                index=None,
                placeholder=""
            )

            if nome_indicador_selecionado:
                indicador_doc = next(i for i in indicadores_lista if i["nome_indicador"] == nome_indicador_selecionado)

                categoria = col2.selectbox(
                    "Categoria do indicador",
                    options=categorias_existentes,
                    index=categorias_existentes.index(indicador_doc.get("categoria_indicador"))
                    if indicador_doc.get("categoria_indicador") in categorias_existentes else None,
                    placeholder=""
                )

                opcoes_estrategia, opcoes_mp, opcoes_lp = carregar_opcoes_estrategia()

                def filtrar_valores_validos(valores, opcoes):
                    if not isinstance(valores, list):
                        return []
                    return [v for v in valores if v in opcoes]

        
                colabora_estrategia = st.multiselect(
                    "Colabora com quais eixos da estratégia?",
                    options=opcoes_estrategia,
                    default=filtrar_valores_validos(indicador_doc.get("colabora_estrategia", []), opcoes_estrategia),
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
                            "colabora_estrategia": colabora_estrategia,
                            "colabora_resultado_mp": colabora_resultado_mp,
                            "colabora_resultado_lp": colabora_resultado_lp
                        }}
                    )
                    st.success("Indicador atualizado com sucesso!")
                    time.sleep(2)
                    st.rerun()
                


@st.dialog("Gerenciar lançamentos", width="large")   
def gerenciar_lancamentos():
    tab_add, tab_edit, tab_delete = st.tabs([":material/add: Adicionar", ":material/edit: Editar", ":material/delete: Excluir"])

    # listas de controle
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
    
    # Lista de nomes legíveis na ordem definida
    ordem_indicadores = [
        "Número de organizações apoiadas",
        "Número de comunidades fortalecidas",
        "Número de famílias",
        "Número de homens jovens (até 29 anos)",
        "Número de homens adultos",
        "Número de mulheres jovens (até 29 anos)",
        "Número de mulheres adultas",
        "Número de indígenas",
        "Número de lideranças comunitárias fortalecidas",
        "Número de famílias comercializando produtos da sociobio com apoio do Fundo Ecos",
        "Número de famílias acessando vendas institucionais com apoio do Fundo Ecos",
        "Número de estudantes recebendo bolsa",
        "Número de capacitações realizadas",
        "Número de homens jovens capacitados (até 29 anos)",
        "Número de homens adultos capacitados",
        "Número de mulheres jovens capacitadas (até 29 anos)",
        "Número de mulheres adultas capacitadas",
        "Número de intercâmbios realizados",
        "Número de homens em intercâmbios",
        "Número de mulheres em intercâmbios",
        "Número de iniciativas de Gestão Territorial implantadas",
        "Área com manejo ecológico do fogo (ha)",
        "Área com manejo agroecológico (ha)",
        "Área com manejo para restauração (ha)",
        "Área com manejo para extrativismo (ha)",
        "Número de agroindústrias implementadas/reformadas",
        "Número de tecnologias instaladas",
        "Número de pessoas beneficiadas com tecnologias",
        "Número de vídeos produzidos",
        "Número de aparições na mídia",
        "Número de publicações de caráter técnico",
        "Número de artigos acadêmicos produzidos e publicados",
        "Número de comunicadores comunitários contribuindo na execução das ações do ISPN",
        "Faturamento bruto anual pré-projeto",
        "Faturamento bruto anual pós-projeto",
        "Volume financeiro de vendas institucionais com apoio do Fundo Ecos",
        "Número de visitas de monitoramento realizadas ao projeto apoiado",
        "Valor da contrapartida financeira projetinhos",
        "Valor da contrapartida não financeira projetinhos",
        "Espécies",
        "Número de organizações apoiadas que alavancaram recursos",
        "Valor mobilizado de novos recursos",
        "Número de políticas públicas monitoradas pelo ISPN",
        "Número de proposições legislativas acompanhadas pelo ISPN",
        "Número de contribuições (notas técnicas, participações e/ou documentos) que apoiam a construção e aprimoramento de políticas públicas"
    ]
    
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

                indicadores_lista = list(indicadores.find({}, {"_id": 1, "nome_indicador": 1}))
                indicadores_opcoes = {
                    formatar_nome_legivel(i["nome_indicador"]): i
                    for i in indicadores_lista
                }

                # Cria o selectbox mantendo a ordem
                indicador_legivel = st.selectbox(
                    "Indicador",
                    [""] + [i for i in ordem_indicadores if i in indicadores_opcoes]
                )

                if indicador_legivel != "":
                    indicador_doc = indicadores_opcoes[indicador_legivel]
                    indicador_oid = indicador_doc["_id"]

                    

                    with st.form(key="form_lancamento_indicador"):
                        col1, col2 = st.columns(2)

                        # lógica de input para valor
                        if indicador_legivel == indicador_texto:
                            valor = col1.text_input("Espécies")  # salva como str
                            tipo_valor = "texto"

                        elif indicador_legivel in indicadores_float:
                            valor = col1.number_input("Valor", value=0.00, step=0.01, format="%.2f")
                            tipo_valor = "float"

                        else:
                            valor = col1.number_input("Valor", value=0, step=1, format="%d")
                            tipo_valor = "int"


                        # Ano
                        ano_atual = datetime.datetime.now().year
                        ano_maximo = ano_atual + 1

                        # cria lista de opções, todas como string
                        anos = ["até 2024"] + [str(ano) for ano in range(2025, ano_maximo + 1)]

                        ano = col2.selectbox("Ano", anos)

                        # ano = col2.number_input("Ano", min_value=2024, step=1)

                        # Observações
                        observacoes = st.text_area("Observações", height=100)

                        submit = st.form_submit_button("Salvar lançamento")

                    if submit:
                        if not autor_nome:
                            st.warning("Nome do autor não encontrado no session_state.")
                            st.stop()

                        # conversão do valor para o tipo correto
                        if tipo_valor == "float":
                            valor = float(valor)
                        elif tipo_valor == "int":
                            valor = int(valor)
                        # se for texto, mantém como está

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
                        st.rerun()

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
                        indicador_nome = formatar_nome_legivel(indicador_doc["nome_indicador"]) if indicador_doc else "Indicador desconhecido"


                        data_str = (
                            l["data_anotacao"].strftime('%d/%m/%Y %H:%M:%S') 
                            if isinstance(l["data_anotacao"], datetime.datetime) 
                            else "Sem data"
                        )

                        # data_str = l["data_anotacao"].strftime('%d/%m/%Y') if isinstance(l["data_anotacao"], datetime.datetime) else "Sem data"
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
                        indicador_nome_edit = formatar_nome_legivel(indicador_doc_edit["nome_indicador"]) if indicador_doc_edit else ""

                        col1, col2 = st.columns(2)

                        if indicador_nome_edit == indicador_texto:
                            novo_valor = col1.text_input("Espécies", value=str(doc["valor"]))
                            tipo_valor = "texto"
                        elif indicador_nome_edit in indicadores_float:
                            valor_inicial = float(doc["valor"]) if doc["valor"] != "" else 0.00
                            novo_valor = col1.number_input("Valor", value=valor_inicial, step=0.01, format="%.2f")
                            tipo_valor = "float"
                        else:
                            valor_inicial = int(doc["valor"]) if str(doc["valor"]).isdigit() else 0
                            novo_valor = col1.number_input("Valor", value=valor_inicial, step=1, format="%d")
                            tipo_valor = "int"


                        # Ano

                        # pega ano atual e define limite
                        ano_atual = datetime.datetime.now().year
                        ano_maximo = ano_atual + 1

                        # gera lista de opções como string
                        anos = ["até 2024"] + [str(ano) for ano in range(2025, ano_maximo + 1)]

                        # pega valor já cadastrado, default "2025"
                        ano_str = doc.get("ano", "2025")

                        # garante que o valor já cadastrado esteja nas opções
                        if ano_str not in anos:
                            anos.insert(0, ano_str)  # adiciona no início se não estiver

                        # cria o selectbox
                        novo_ano = col2.selectbox("Ano", anos, index=anos.index(ano_str))



                        # ano_str = doc.get("ano", "2025")
                        # try:
                        #     ano_int = int(ano_str)
                        # except ValueError:
                        #     ano_int = 2025
                        # novo_ano = col2.number_input("Ano", value=ano_int, min_value=2025, step=1)

                        # Observações
                        novas_obs = st.text_area("Observações", value=doc.get("observacoes", ""))

                        if st.button("Salvar alterações", key="salvar_edit"):
                            if tipo_valor == "float":
                                novo_valor = float(novo_valor)
                            elif tipo_valor == "int":
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
                            st.cache_data.clear()
                            st.rerun()

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

                # Filtrar lançamentos pelo autor, exceto para admins
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
                        indicador_nome = formatar_nome_legivel(indicador_doc["nome_indicador"]) if indicador_doc else "Indicador desconhecido"

                        data_str = (
                            l["data_anotacao"].strftime('%d/%m/%Y %H:%M:%S') 
                            if isinstance(l["data_anotacao"], datetime.datetime) 
                            else "Sem data"
                        )

                        # data_str = l["data_anotacao"].strftime('%d/%m/%Y') if isinstance(l["data_anotacao"], datetime.datetime) else "Sem data"
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
                                indicador_nome_conf = formatar_nome_legivel(
                                    indicador_doc_conf.get("nome_indicador", "")
                                ) or "Indicador"

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
                            st.rerun()


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

map_programa_nome = {p["_id"]: p["nome_programa_area"] for p in programas}
df_proj_info["programa"] = df_proj_info["programa"].map(map_programa_nome).fillna("")

# Inicializa session_state se não existir
if "filtros_indicadores" not in st.session_state:
    st.session_state.filtros_indicadores = {}

# Garante que TODAS as chaves existam
for key in ["tipo", "autor_anotacao", "codigo", "ano", "bioma", "sigla", "programa"]:
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

        col4, col5, col6 = st.columns(3)
        with col4:
            programa_sel = st.multiselect(
                "Filtrar por programa",
                sorted(df_base["programa"].unique()),
                key="filtro_programa",
                placeholder=""
            )
        with col5:
            bioma_sel = st.multiselect(
                "Filtrar por bioma",
                biomas_unicos,
                key="filtro_bioma",
                placeholder=""
            )
        with col6:
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
        }


    # ===== APLICA FILTROS =====
    df_filtrado = df_base.copy()

    for campo, selecao in st.session_state.filtros_indicadores.items():
        if selecao:
            if campo == "tipo":
                df_filtrado = df_filtrado[df_filtrado["tipo"].isin(selecao)]
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



# ---------------------- ORGANIZAÇÕES E COMUNIDADES ----------------------


# @st.fragment
# def fragmento_botoes():
col1, col2 = st.columns(2)

with col1.container(border=True):
    st.write('**Organizações e Comunidades**')
    botao_indicador_legivel("Número de organizações apoiadas", "numero_de_organizacoes_apoiadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de comunidades fortalecidas", "numero_de_comunidades_fortalecidas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)



# ---------------------- PESSOAS ----------------------


with col2.container(border=True):
    st.write('**Pessoas**')
    botao_indicador_legivel("Número de famílias", "numero_de_familias", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de homens jovens (até 29 anos)", "numero_de_homens_jovens", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de homens adultos", "numero_de_homens_adultos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de mulheres jovens (até 29 anos)", "numero_de_mulheres_jovens", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de mulheres adultas", "numero_de_mulheres_adultas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de Indígenas", "numero_de_indigenas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de lideranças comunitárias fortalecidas", "numero_de_liderancas_comunitarias_fortalecidas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de famílias comercializando produtos da sociobio", "numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_fundo_ecos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de famílias acessando vendas institucionais", "numero_de_familias_acessando_vendas_institucionais_com_apoio_do_fundo_ecos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de estudantes recebendo bolsa", "numero_de_estudantes_recebendo_bolsa", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- CAPACITAÇÕES ----------------------


with col1.container(border=True):
    st.write('**Capacitações**')
    botao_indicador_legivel("Número de capacitações realizadas", "numero_de_capacitacoes_realizadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de homens jovens capacitados (até 29 anos)", "numero_de_homens_jovens_capacitados", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de homens adultos capacitados", "numero_de_homens_adultos_capacitados", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de mulheres jovens capacitadas (até 29 anos)", "numero_de_mulheres_jovens_capacitadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de mulheres adultas capacitadas", "numero_de_mulheres_adultas_capacitadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- INTERCÂMBIOS ----------------------


with col1.container(border=True):
    st.write('**Intercâmbios**')
    botao_indicador_legivel("Número de intercâmbios realizados", "numero_de_intercambios_realizados", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de homens em intercâmbios", "numero_de_homens_em_intercambios", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de mulheres em intercâmbios", "numero_de_mulheres_em_intercambios", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- TERRITÓRIO ----------------------


with col2.container(border=True):
    st.write('**Território**')
    botao_indicador_legivel("Número de iniciativas de Gestão Territorial implantadas", "numero_de_iniciativas_de_gestao_territorial_implantadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Área com manejo ecológico do fogo (ha)", "area_com_manejo_ecologico_do_fogo_ha", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Área com manejo agroecológico (ha)", "area_com_manejo_agroecologico_ha", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Área com manejo para restauração (ha)", "area_com_manejo_para_restauracao_ha", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Área com manejo para extrativismo (ha)", "area_com_manejo_para_extrativismo_ha", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- TECNOLOGIA E INFRA ----------------------


with col1.container(border=True):
    st.write('**Tecnologia e Infra-estrutura**')
    botao_indicador_legivel("Número de agroindústrias implementadas/reformadas", "numero_de_agroindustiras_implementadas_ou_reformadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de tecnologias instaladas", "numero_de_tecnologias_instaladas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de pessoas beneficiadas com tecnologias", "numero_de_pessoas_beneficiadas_com_tecnologias", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- FINANCEIRO ----------------------


with col1.container(border=True):
    st.write('**Financeiro**')
    botao_indicador_legivel("Faturamento bruto anual pré-projeto (R$)", "faturamento_bruto_anual_pre_projeto", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Faturamento bruto anual pós-projeto (R$)", "faturamento_bruto_anual_pos_projeto", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Volume financeiro de vendas institucionais com apoio do Fundo Ecos", "volume_financeiro_de_vendas_institucionais_com_apoio_do_fundo_ecos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- COMUNICAÇÃO ----------------------


with col2.container(border=True):
    st.write('**Comunicação**')
    botao_indicador_legivel("Número de vídeos produzidos", "numero_de_videos_produzidos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de aparições na mídia", "numero_de_aparicoes_na_midia", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de publicações de caráter técnico", "numero_de_publicacoes_de_carater_tecnico", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de artigos acadêmicos produzidos e publicados", "numero_de_artigos_academicos_produzidos_e_publicados", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de comunicadores comunitários contribuindo na execução das ações do ISPN", "numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- PROJETOS FUNDO ECOS ----------------------


if not tipo_selecionado or any(tipo in ["PJ", "PF"] for tipo in tipo_selecionado):
    with col1.container(border=True):
        st.write('**Projetos Fundo Ecos**')
        botao_indicador_legivel("Número de visitas de monitoramento realizadas ao projeto apoiado", "numero_de_visitas_de_monitoramento_realizadas_ao_projeto_apoiado", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
        botao_indicador_legivel("Valor da Contrapartidas Financeira (R$)", "valor_da_contrapartida_financeira_projetinhos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
        botao_indicador_legivel("Valor da Contrapartida Não-Financeira (R$)", "valor_da_contrapartida_nao_financeira_projetinhos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
        botao_indicador_legivel("Espécies: clique para mais informações", "especies", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
        botao_indicador_legivel("Número de organizações apoiadas que alavancaram recursos", "numero_de_organizacoes_apoiadas_que_alavancaram_recursos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
        botao_indicador_legivel("Valor mobilizado de novos recursos (R$)", "valor_mobilizado_de_novos_recursos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)

#fragmento_botoes()