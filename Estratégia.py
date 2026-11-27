import streamlit as st
import pandas as pd
import time
import streamlit_shadcn_ui as ui
from datetime import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn, br_to_float, float_to_br
from bson import ObjectId
import re


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
###########################################################################################################


# Conecta-se ao banco de dados MongoDB (usa cache automático para melhorar performance)
db = conectar_mongo_portal_ispn()

# Define as coleções específicas que serão utilizadas a partir do banco
estatistica = db["estatistica"]
colaboradores = db["colaboradores"]
estrategia = db["estrategia"]
projetos_ispn = db["projetos_ispn"]
indicadores = db["indicadores"]
lancamentos_indicadores = db["lancamentos_indicadores"]
programas_areas = db["programas_areas"]

# Indicadores dos Objetivos Estratégicos Organizacionais (OEO).
# Cada documento: {_id, id_objetivo, nome_indicador, tipo_dado}
indicadores_oeo = db["indicadores_oeo"]

# Lançamentos dos indicadores OEO, feitos no registro de entregas.
lancamentos_indicadores_oeo = db["lancamentos_indicadores_oeo"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_estrategia"
nome_pagina = "Estratégia"
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
# FUNÇÕES
###########################################################################################################


# Função para comparar dataframes e detectar se tem mudanças, para fazer a gravação automática ao editar o data_editor
def df_tem_mudancas(df_novo: pd.DataFrame, df_antigo: pd.DataFrame) -> bool:
    """
    Compara dois DataFrames e retorna True se houver qualquer diferença.
    Considera tanto os valores quanto a ordem das colunas e linhas.
    Args:
        df_novo (pd.DataFrame): DataFrame novo editado.
        df_antigo (pd.DataFrame): DataFrame original para comparar.
    Returns:
        bool: True se os DataFrames forem diferentes, False se iguais.
    """

    return not df_novo.equals(df_antigo)


# Editar Teoria da Mudança
@st.dialog("Editar Teoria da Mudança", width="large", on_dismiss="rerun")
def editar_info_teoria_mudanca_dialog():

    # Pega o documento da coleção estratégia com a teoria da mudança
    teoria_doc = estrategia.find_one({"teoria da mudança": {"$exists": True}})

    # Cria lista com os valores atuais da teoria da mudança
    lista_tm = teoria_doc["teoria da mudança"] if teoria_doc else []

    # Valores padrões
    problema_atual = ""
    proposito_atual = ""
    impacto_atual = ""

    # Percorre a lista e extrai os valores atuais
    for item in lista_tm:
        if "problema" in item:
            problema_atual = item["problema"]
        if "proposito" in item:
            proposito_atual = item["proposito"]
        if "impacto" in item:
            impacto_atual = item["impacto"]

    # Input para novos valores
    novo_problema = st.text_area("Problema", value=problema_atual, height="content")
    novo_proposito = st.text_area("Propósito", value=proposito_atual, height="content")
    novo_impacto = st.text_area("Impacto", value=impacto_atual, height="content")

    # Botão para salvar alterações
    if st.button("Salvar alterações", key="salvar_teoria_mudanca", icon=":material/save:"):
        # Cria lista com os novos valores
        novos_dados = [
            {"problema": novo_problema},
            {"proposito": novo_proposito},
            {"impacto": novo_impacto}
        ]

        # Verifica se o documento existe
        if teoria_doc:
            # Atualiza o documento
            estrategia.update_one(
                {"_id": teoria_doc["_id"]},
                {"$set": {"teoria da mudança": novos_dados}}
            )
            st.success("Teoria da mudança atualizada com sucesso!")

        else:
            # Cria um novo documento
            estrategia.insert_one({"teoria da mudança": novos_dados})
            st.success("Teoria da mudança criada com sucesso!")

        # Espera 2 segundos e recarrega a página
        time.sleep(2)
        st.rerun()


def ids_indicadores_normalizados(lista):
    """
    Normaliza a lista de IDs dos indicadores.
    A função aceita:
    - ObjectId
    - string
    - dicionário no formato {"$oid": "..."}
    - valores nulos
    O retorno sempre será uma lista de strings.
    """

    ids = []
    for item in lista or []:
        if isinstance(item, ObjectId):
            ids.append(str(item))

        elif isinstance(item, dict) and "$oid" in item:
            ids.append(str(item["$oid"]))

        elif item is not None:
            ids.append(str(item))

    return ids


###########################################################################################################
# BLOCO ÚNICO DE METAS (Indicador / Objetivo / Alcançado)
###########################################################################################################


# Este bloco substitui, em toda a página, o antigo bloco de "Indicadores
# relacionados" (somente leitura) por um único bloco de "Metas", com as
# colunas Indicador, Objetivo / meta e Alcançado. No modo de edição, vira
# um data_editor com todas as colunas editáveis (a coluna Indicador é um
# seletor vinculado à coleção de indicadores) e permite adicionar linhas.
def mapa_nome_para_id_indicadores(mapa_nomes_indicadores):
    """
    Inverte o mapa {id: nome} de indicadores para {nome: id}, permitindo
    localizar o ID do indicador a partir do nome escolhido no seletor.
    """
    return {
        nome: id_indicador
        for id_indicador, nome in mapa_nomes_indicadores.items()
    }


def montar_df_metas(metas, mapa_nomes_indicadores):
    """
    Converte a lista de metas salva no banco em um DataFrame com as
    colunas Indicador, Objetivo / meta e Alcançado.
    A coluna Indicador é resolvida a partir do ID do indicador
    vinculado (id_indicador); quando não há vínculo com a coleção de
    indicadores (dados legados), usa o texto livre salvo anteriormente.
    """

    linhas = []

    for m in metas:
        id_indicador = normalizar_id(m.get("id_indicador"))
        if id_indicador and id_indicador in mapa_nomes_indicadores:
            nome_indicador = mapa_nomes_indicadores[id_indicador]

        else:
            nome_indicador = (
                m.get("nome_indicador_texto")
                or m.get("nome_meta_mp")
                or m.get("meta_obj")
                or ""
            )

        linhas.append({
            "Indicador": nome_indicador,
            "Objetivo / meta": m.get("objetivo", ""),
            "Alcançado": m.get("alcancado", "")
        })

    return pd.DataFrame(
        linhas,
        columns=["Indicador", "Objetivo / meta", "Alcançado"]
    )


def metas_com_seed_de_indicadores(item):
    """
    Retorna a lista de metas de um eixo/resultado. Caso ainda não
    exista nenhuma meta cadastrada, aproveita os indicadores já
    vinculados (campo legado 'indicadores') como linhas iniciais da
    tabela de metas.
    """

    metas = item.get("metas")
    if metas:
        return metas
    ids_legado = ids_indicadores_normalizados(item.get("indicadores", []))

    return [
        {"id_indicador": id_indicador, "objetivo": "", "alcancado": ""}
        for id_indicador in ids_legado
    ]


def df_metas_para_lista(df_editado, nome_para_id_indicadores):
    """
    Converte o DataFrame editado de volta em uma lista de dicionários
    para salvar no banco. Quando o nome do indicador escolhido
    corresponde a um indicador cadastrado, salva o vínculo por ID;
    caso contrário, mantém o texto digitado.
    """

    nova_lista = []
    for _, linha in df_editado.iterrows():

        nome_indicador = str(linha.get("Indicador") or "").strip()

        if not nome_indicador or nome_indicador.lower() == "none":
            continue

        id_indicador = nome_para_id_indicadores.get(nome_indicador)

        item_meta = {
            "objetivo": linha.get("Objetivo / meta", "") or "",
            "alcancado": linha.get("Alcançado", "") or ""
        }

        if id_indicador:
            item_meta["id_indicador"] = id_indicador

        else:
            item_meta["nome_indicador_texto"] = nome_indicador

        nova_lista.append(item_meta)

    return nova_lista


@st.fragment
def bloco_metas(
    *,
    metas_atual,
    mapa_nomes_indicadores,
    nome_para_id_indicadores,
    chave,
    campo_mongo,
    doc_id,
    colecao,
    array_filters=None
):
    """
    Exibe o bloco de Metas (Indicador / Objetivo / meta / Alcançado).
    No modo de edição, vira um data_editor com todas as colunas
    editáveis — a coluna Indicador é um seletor vinculado à coleção
    de indicadores — e permite adicionar novas linhas.
    """

    st.markdown("##### :material/target: Metas:")
    st.write("")

    if not metas_atual and not st.session_state.modo_edicao:
        st.caption("**Nenhuma meta cadastrada.**")

        return

    df_metas = montar_df_metas(metas_atual, mapa_nomes_indicadores)

    # As opções do seletor são os indicadores cadastrados na coleção,
    # somadas a eventuais nomes legados já salvos (para não quebrar
    # dados antigos que não estejam vinculados à coleção).
    opcoes_indicadores = sorted(
        {
            nome
            for nome in (
                list(mapa_nomes_indicadores.values())
                + df_metas["Indicador"].tolist()
            )
            if nome
        },
        key=lambda n: n.casefold()
    )

    if st.session_state.modo_edicao:

        df_editado = st.data_editor(
            df_metas,
            hide_index=True,
            key=f"editor_metas_{chave}_{len(metas_atual)}",
            column_config={
                "Indicador": st.column_config.SelectboxColumn(
                    "Indicador",
                    options=opcoes_indicadores,
                    required=True
                ),
                "Objetivo / meta": st.column_config.TextColumn(
                    "Objetivo / meta"
                ),
                "Alcançado": st.column_config.TextColumn("Alcançado"),
            },
            num_rows="dynamic"
        )

        if not df_editado.equals(df_metas):
            if st.button(
                "Salvar alterações",
                key=f"salvar_metas_{chave}",
                icon=":material/save:"
            ):
                nova_lista = df_metas_para_lista(
                    df_editado, nome_para_id_indicadores
                )

                colecao.update_one(
                    {"_id": doc_id},
                    {"$set": {campo_mongo: nova_lista}},
                    array_filters=array_filters
                )

                st.success("Metas atualizadas!")
                time.sleep(2)
                st.cache_data.clear()
                st.rerun()

    else:
        st.dataframe(df_metas, hide_index=True)


###########################################################################################################
# METAS DOS OBJETIVOS ESTRATÉGICOS ORGANIZACIONAIS
###########################################################################################################


def _texto_celula(valor):
    """Converte o valor de uma célula do data_editor em texto (None/NaN viram "")."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return str(valor).strip()


def _valor_valido_para_tipo(valor, tipo):
    """
    Verifica se o valor digitado na meta é compatível com o tipo do
    indicador ("int" / "float"). Valores vazios são aceitos.
    Aceita o formato brasileiro (1.234,56).
    """
    valor = _texto_celula(valor)
    tipo = normalizar_tipo_indicador(tipo)

    if not valor or tipo not in TIPOS_INDICADOR:
        return True

    normalizado = valor.replace(".", "").replace(",", ".")

    if tipo == "int":
        return re.fullmatch(r"-?\d+", normalizado) is not None

    try:
        float(normalizado)
        return True
    except ValueError:
        return False


def _numero_do_lancamento(valor):
    """Converte o valor salvo no lançamento em número (aceita int, float ou texto no formato brasileiro)."""
    if isinstance(valor, bool):
        return 0
    if isinstance(valor, (int, float)):
        return valor
    return br_to_float(str(valor or ""))


def calcular_alcancado_oeo(lancamentos, tipo_por_indicador):
    """
    Monta o texto da coluna "Alcançado" de cada indicador OEO a partir
    dos lançamentos feitos no registro de entregas:
        - "Número inteiro": soma, exibida sem casas decimais;
        - "Número decimal": soma, exibida no formato brasileiro (1.234,56);
        - "Texto": lançamentos separados por ", ", em ordem de lançamento.
    Retorna {id_indicador (str): texto}.
    """

    lancamentos = sorted(
        lancamentos,
        key=lambda l: l.get("data_anotacao") or datetime.min
    )

    somas = {}
    textos = {}

    for lanc in lancamentos:
        id_ind = str(lanc.get("id_do_indicador"))
        tipo = normalizar_tipo_indicador(tipo_por_indicador.get(id_ind))
        valor = lanc.get("valor")

        # "Texto" não é mais uma opção, mas fica aqui para indicadores antigos
        if tipo == "Texto":
            texto = str(valor).strip() if valor is not None else ""
            if texto:
                textos.setdefault(id_ind, []).append(texto)
        else:
            somas[id_ind] = somas.get(id_ind, 0) + _numero_do_lancamento(valor)

    alcancado = {}

    for id_ind, soma in somas.items():
        if normalizar_tipo_indicador(tipo_por_indicador.get(id_ind)) == "float":
            alcancado[id_ind] = float_to_br(float(soma))
        else:
            alcancado[id_ind] = f"{int(round(soma)):,}".replace(",", ".")

    return alcancado


@st.fragment
def bloco_metas_objetivo(*, objetivo, indicadores_obj, obj_idx, doc_id, alcancado_por_indicador):
    """
    Bloco de Metas dos Objetivos Estratégicos Organizacionais.
    As linhas vêm dos indicadores do objetivo, salvos na coleção
    'indicadores_oeo'. Só a coluna "Objetivo / meta" é editável.
    "Alcançado" é calculado automaticamente a partir dos lançamentos
    feitos no registro de entregas (soma para números, lançamentos
    separados por vírgula para texto) e não é editável.
    """

    st.markdown("##### :material/target: Metas:")
    st.write("")

    if not indicadores_obj:
        st.caption("**Nenhum indicador cadastrado para este objetivo.**")
        return

    # Ordena os indicadores pelo nome
    indicadores_obj = sorted(
        indicadores_obj,
        key=lambda ind: ind.get("nome_indicador", "").casefold()
    )

    # Metas já salvas, indexadas pelo ID do indicador e, para dados
    # legados, pelo nome do indicador.
    metas_por_id = {}
    metas_por_nome = {}

    for m in objetivo.get("metas", []):
        id_ind = normalizar_id(m.get("id_indicador"))
        if id_ind:
            metas_por_id[id_ind] = m

        nome_legado = (m.get("nome_indicador_texto") or "").strip().casefold()
        if nome_legado:
            metas_por_nome[nome_legado] = m

    linhas = []
    ids_linhas = []
    tipos_linhas = []
    alcancados_salvos = []

    for ind in indicadores_obj:
        id_ind = str(ind["_id"])
        nome_ind = ind.get("nome_indicador", "Indicador sem nome")

        meta = (
            metas_por_id.get(id_ind)
            or metas_por_nome.get(nome_ind.strip().casefold())
            or {}
        )

        linhas.append({
            "Indicador": nome_ind,
            "Objetivo / meta": meta.get("objetivo", "") or "",
            # Soma automática dos lançamentos do registro de entregas
            "Alcançado": alcancado_por_indicador.get(id_ind, "")
        })
        ids_linhas.append(id_ind)
        tipos_linhas.append(normalizar_tipo_indicador(ind.get("tipo_dado")))
        alcancados_salvos.append(meta.get("alcancado", "") or "")

    df_metas = pd.DataFrame(
        linhas,
        columns=["Indicador", "Objetivo / meta", "Alcançado"]
    )

    # Fora do modo de edição: apenas exibe
    if not st.session_state.modo_edicao:
        st.dataframe(df_metas, hide_index=True)
        return

    df_editado = st.data_editor(
        df_metas,
        hide_index=True,
        key=f"editor_metas_obj_{obj_idx}_{len(indicadores_obj)}",
        column_config={
            "Indicador": st.column_config.TextColumn("Indicador"),
            "Objetivo / meta": st.column_config.TextColumn("Objetivo / meta"),
            "Alcançado": st.column_config.TextColumn("Alcançado"),
        },
        disabled=["Indicador", "Alcançado"],
        num_rows="fixed"
    )

    if df_editado.equals(df_metas):
        return

    if st.button(
        "Salvar alterações",
        key=f"salvar_metas_obj_{obj_idx}",
        icon=":material/save:"
    ):
        # Valida o valor da meta conforme o tipo do indicador
        invalidos = [
            f"{df_metas.at[i, 'Indicador']} "
            f"({ROTULOS_TIPO_INDICADOR.get(tipos_linhas[i], tipos_linhas[i])})"
            for i in range(len(df_editado))
            if not _valor_valido_para_tipo(
                df_editado.at[i, "Objetivo / meta"], tipos_linhas[i]
            )
        ]

        if invalidos:
            st.warning(
                "Valor incompatível com o tipo do indicador: "
                + "; ".join(invalidos)
            )
            return

        nova_lista = [
            {
                "id_indicador": ids_linhas[i],
                "objetivo": _texto_celula(df_editado.at[i, "Objetivo / meta"]),
                # "Alcançado" é calculado na tela: mantém o que já estava salvo
                "alcancado": alcancados_salvos[i]
            }
            for i in range(len(df_editado))
        ]

        estrategia.update_one(
            {"_id": doc_id},
            {"$set": {
                f"objetivos_estrategicos_institucionais.obj_estrat_inst.{obj_idx}.metas": nova_lista
            }}
        )

        st.success("Metas atualizadas!")
        time.sleep(2)
        st.cache_data.clear()
        st.rerun()


def migrar_objetivos_estrategicos(doc):
    """
    Ajusta os Objetivos Estratégicos Organizacionais à nova estrutura
    (roda só uma vez, quando ainda houver dados no formato antigo):
      - garante um _id em cada objetivo (usado como 'id_objetivo'
        na coleção 'indicadores_oeo');
      - move os indicadores da chave 'indicadores' de cada objetivo
        para a coleção 'indicadores_oeo', preservando o _id (para não
        perder o vínculo com as metas já salvas) e apaga a chave;
      - apaga 'indicadores_relacionados' das ações estratégicas.
    Retorna a lista de objetivos já ajustada.
    """

    objetivos = doc["objetivos_estrategicos_institucionais"]["obj_estrat_inst"]
    alterou = False

    for obj in objetivos:

        if "_id" not in obj:
            obj["_id"] = str(ObjectId())
            alterou = True

        id_objetivo = str(obj["_id"])

        if "indicadores" in obj:
            for ind in obj.pop("indicadores") or []:
                id_antigo = ind.get("_id")

                id_ind = (
                    ObjectId(str(id_antigo))
                    if id_antigo and ObjectId.is_valid(str(id_antigo))
                    else ObjectId()
                )

                indicadores_oeo.update_one(
                    {"_id": id_ind},
                    {"$set": {
                        "id_objetivo": id_objetivo,
                        "nome_indicador": ind.get("nome_indicador", ""),
                        "tipo_dado": normalizar_tipo_indicador(ind.get("tipo_dado"))
                    }},
                    upsert=True
                )

            alterou = True

        for acao in obj.get("acoes_estrategicas", []):
            if "indicadores_relacionados" in acao:
                acao.pop("indicadores_relacionados")
                alterou = True

    # Converte o tipo_dado antigo dos indicadores OEO para "int"/"float"
    for antigo, novo in TIPOS_INDICADOR_LEGADOS.items():
        indicadores_oeo.update_many(
            {"tipo_dado": antigo},
            {"$set": {"tipo_dado": novo}}
        )

    # Garante uma meta (vazia) para cada indicador do objetivo, inclusive
    # os cadastrados antes desta regra, para que apareçam no registro de entregas.
    ids_por_objetivo = {}
    for ind in indicadores_oeo.find({}, {"id_objetivo": 1}):
        ids_por_objetivo.setdefault(
            str(ind.get("id_objetivo")), []
        ).append(str(ind["_id"]))

    for obj in objetivos:
        metas = obj.setdefault("metas", [])

        ids_com_meta = {
            normalizar_id(m.get("id_indicador"))
            for m in metas
            if isinstance(m, dict)
        }

        for id_ind in ids_por_objetivo.get(str(obj["_id"]), []):
            if id_ind not in ids_com_meta:
                metas.append({
                    "id_indicador": id_ind,
                    "objetivo": "",
                    "alcancado": ""
                })
                alterou = True

    if alterou:
        estrategia.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "objetivos_estrategicos_institucionais.obj_estrat_inst": objetivos
            }}
        )
        st.cache_data.clear()

    return objetivos


###########################################################################################################
# PERMISSÃO: USUÁRIO DO PROGRAMA / ÁREA "MONITORAMENTO"
###########################################################################################################


@st.cache_data(ttl=300, show_spinner=False)
def id_programa_monitoramento():
    """Retorna o ID (str) do programa/área "Monitoramento"."""
    prog = programas_areas.find_one(
        {"nome_programa_area": "Monitoramento"},
        {"_id": 1}
    )
    return str(prog["_id"]) if prog else None


def usuario_e_do_monitoramento():
    """
    True se o usuário logado pertence ao programa/área "Monitoramento".
    AJUSTE os nomes abaixo se forem diferentes no portal:
      - st.session_state["id_usuario"]  -> _id da pessoa logada
      - campo "programa_area" na coleção "pessoas"
    """
    id_mon = id_programa_monitoramento()
    id_usuario = st.session_state.get("id_usuario")

    if not id_mon or not id_usuario:
        return False

    try:
        filtro_id = ObjectId(str(id_usuario))
    except Exception:
        filtro_id = id_usuario

    pessoa = db["pessoas"].find_one({"_id": filtro_id}, {"programa_area": 1})

    if not pessoa:
        return False

    valor = pessoa.get("programa_area")
    programas_usuario = normalizar_lista_ids(
        valor if isinstance(valor, list) else [valor]
    )

    return id_mon in programas_usuario


# Editar Estratégia
@st.dialog("Editar Estratégia", width="large", on_dismiss="rerun")
def editar_estrategia_dialog():

    # Busca o documento da estratégia que possui a chave "estrategia"
    estrategia_doc = estrategia.find_one({"estrategia": {"$exists": True}})

    # Obtém o título atual da página de estratégias, se existir
    titulo_pagina_atual = estrategia_doc.get("estrategia", {}).get("titulo_pagina_estrategia", "") if estrategia_doc else ""

    # Campo de entrada para um novo título da página de estratégias
    novo_titulo_pagina = st.text_input("Título da página de estratégias", value=titulo_pagina_atual)

    # Botão para atualizar o título da página
    if st.button("Atualizar título da página", key="atualizar_titulo_pagina_estrategias", icon=":material/save:"):
        if estrategia_doc:
            estrategia.update_one(
                {"_id": estrategia_doc["_id"]},
                {"$set": {"estrategia.titulo_pagina_estrategia": novo_titulo_pagina}}
            )

            st.success("Título da página atualizado com sucesso!")
            time.sleep(2)
            st.cache_data.clear()
            st.rerun(scope="fragment")

        else:
            st.error("Documento não encontrado.")


# Função do diálogo para editar ou adicionar resultados de médio prazo
@st.dialog("Editar Título da Página", width="large", on_dismiss="rerun")
def editar_titulo_pagina_resultados_mp_dialog():

    # Recupera os dados atuais do banco
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {}) if doc else {}

    # Título da aba principal de Resultados de Médio Prazo
    titulo_atual = resultados_data.get("titulo_pagina_resultados_mp", "")

    # Campo para editar o título da aba
    novo_titulo = st.text_input("Título da página de Resultados de Médio Prazo", value=titulo_atual)

    if st.button("Atualizar", key="atualizar_titulo_mp", icon=":material/save:"):
        estrategia.update_one(
            {"_id": doc["_id"]},
            {"$set": {"resultados_medio_prazo.titulo_pagina_resultados_mp": novo_titulo}}
        )

        st.success("Título da página atualizado com sucesso!")
        time.sleep(2)
        st.cache_data.clear()
        st.rerun(scope="fragment")


# Função do diálogo para editar resultados de médio prazo
@st.dialog("Editar Informações do Resultado", width="large", on_dismiss="rerun")
def editar_titulo_de_cada_resultado_mp_dialog(resultado_idx):

    # Recupera os dados do banco
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {})
    resultados = resultados_data.get("resultados_mp", [])

    # Verifica se o índice é válido
    if resultado_idx < 0 or resultado_idx >= len(resultados):
        st.error("Índice de resultado inválido.")
        return

    resultado = resultados[resultado_idx]

    if "admin" in st.session_state.tipo_usuario:

        # Tab para editar o título
        aba1, aba2 = st.tabs(["Título", "Ações Estratégicas"])
        # Aba de Título
        with aba1:

            st.subheader("Editar Título do Resultado")
            st.write("")
            titulo_atual = resultado.get(
                "titulo",
                ""
            )

            novo_titulo = st.text_input(
                "Novo título",
                value=titulo_atual
            )

            st.write("")

            if st.button(
                "Salvar",
                key=f"salvar_titulo_{resultado_idx}",
                icon=":material/save:"
            ):
                # Atualiza o título.
                resultados[resultado_idx]["titulo"] = novo_titulo
                estrategia.update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "resultados_medio_prazo.resultados_mp":
                                resultados
                        }
                    }
                )

                st.success("Resultado atualizado com sucesso!")
                time.sleep(2)
                st.cache_data.clear()
                st.rerun(scope="fragment")

        # -------------------------- #
        # ABA 2 - AÇÕES ESTRATÉGICAS
        # -------------------------- #
        with aba2:
            acoes = resultado.get("acoes_estrategicas", [])

            # Expander para adicionar nova ação estratégica (com atividades e anotações)
            with st.expander("Adicionar nova ação estratégica", expanded=False, icon=":material/add_notes:"):

                novo_titulo_acao = st.text_area("Título da nova ação estratégica", key=f"nova_acao_titulo_{resultado_idx}")

                if st.button("Adicionar ação estratégica", key=f"btn_add_acao_{resultado_idx}", icon=":material/add:"):
                    nova_acao = {
                        "_id": str(ObjectId()),
                        "nome_acao_estrategica": novo_titulo_acao,
                    }

                    resultados[resultado_idx].setdefault("acoes_estrategicas", []).append(nova_acao)

                    estrategia.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                    )

                    st.success("Nova ação estratégica adicionada com sucesso!")
                    time.sleep(2)
                    st.cache_data.clear()
                    st.rerun(scope="fragment")

            st.write("")

            # Edição das ações estratégicas existentes
            for a_idx, acao in enumerate(acoes):
                titulo_acao = acao.get("nome_acao_estrategica", f"Ação Estratégica {a_idx + 1}")
                with st.expander(f"{titulo_acao}"):

                    novo_nome_acao = st.text_area(
                        "Título da ação estratégica",
                        value=titulo_acao,
                        height="content",
                        key=f"acao_estrat_{resultado_idx}_{a_idx}"
                    )

                    if st.button(f"Salvar", key=f"salvar_acao_{resultado_idx}_{a_idx}", icon=":material/save:"):
                        resultados[resultado_idx]["acoes_estrategicas"][a_idx].update({
                            "nome_acao_estrategica": novo_nome_acao,
                        })

                        estrategia.update_one(
                            {"_id": doc["_id"]},
                            {"$set": {"resultados_medio_prazo.resultados_mp": resultados}}
                        )

                        st.success("Ação estratégica atualizada com sucesso!")
                        time.sleep(2)
                        st.cache_data.clear()
                        st.rerun(scope="fragment")

    else:
        acoes = resultado.get("acoes_estrategicas", [])
        st.caption("Utilize o bloco de Metas na página principal para editar as metas deste resultado.")


@st.dialog("Editar eixo da estratégia", width="large", on_dismiss="rerun")
def editar_eixos_da_estrategia_dialog(
    estrategia_item,
    estrategia_doc,
    estrategia
):
    """
    Permite editar o título do eixo. O vínculo com indicadores agora é
    feito diretamente no bloco de Metas da página principal.
    """

    # ---------------------------------------------------------
    # CAMPOS ATUAIS DO EIXO
    # ---------------------------------------------------------
    novo_titulo = st.text_input(
        "Eixo da estratégia:",
        value=estrategia_item.get("titulo", "")
    )

    st.write("")

    col1, col2 = st.columns(2)

    if col1.button(
        "Salvar",
        use_container_width=False,
        icon=":material/save:"
    ):

        # -----------------------------------------------------
        # LOCALIZAR O EIXO ORIGINAL
        # -----------------------------------------------------
        for eixo in estrategia_doc["estrategia"]["eixos_da_estrategia"]:
            if str(eixo.get("_id")) == str(
                estrategia_item.get("_id")
            ):

                eixo["titulo"] = novo_titulo

                # Garante que o eixo tenha um ID.
                if "_id" not in eixo:
                    eixo["_id"] = str(ObjectId())
                break

        # -----------------------------------------------------
        # SALVAR NO MONGODB
        # -----------------------------------------------------
        estrategia.update_one(
            {"_id": estrategia_doc["_id"]},
            {
                "$set": {
                    "estrategia.eixos_da_estrategia":
                        estrategia_doc["estrategia"]["eixos_da_estrategia"]
                }
            }
        )

        st.success("Eixo atualizado com sucesso!")
        time.sleep(2)
        st.cache_data.clear()
        st.rerun(scope="fragment")


@st.dialog("Editar título da página", on_dismiss="rerun")
def editar_titulo_pagina_resultados_lp_dialog():

    # Buscar documento
    doc = estrategia.find_one({"resultados_longo_prazo": {"$exists": True}})

    if not doc:
        st.error("Nenhum documento encontrado com 'resultados_longo_prazo'.")
        return

    dados_lp = doc.get("resultados_longo_prazo", {})

    titulo_atual = dados_lp.get("titulo_pagina_resultados_lp", "")

    # Campos editáveis
    novo_titulo = st.text_input("Título da página", value=titulo_atual)

    # Botão de salvar
    if st.button("Salvar alterações", icon=":material/save:", use_container_width=False):
        estrategia.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "resultados_longo_prazo.titulo_pagina_resultados_lp": novo_titulo,
            }}
        )

        st.success("Título da página atualizado com sucesso!")
        time.sleep(2)
        st.cache_data.clear()
        st.rerun(scope="fragment")


@st.dialog("Editar resultado de longo prazo", width="large", on_dismiss="rerun")
def editar_titulo_de_cada_resultado_lp_dialog(resultado_idx):

    # ----------------------------------------------------
    # BUSCAR DOCUMENTO
    # ----------------------------------------------------
    doc = estrategia.find_one({"resultados_longo_prazo": {"$exists": True}})

    if not doc:
        st.error("Nenhum documento encontrado com 'resultados_longo_prazo'.")
        return

    resultados_lp = doc.get("resultados_longo_prazo", {}).get("resultados_lp", [])

    if resultado_idx is None or resultado_idx >= len(resultados_lp):
        st.error("Índice de resultado inválido.")
        return

    resultado = resultados_lp[resultado_idx]

    # ----------------------------------------------------
    # ABAS (MESMA ESTRUTURA DO MP)
    # ----------------------------------------------------

    aba1, aba2 = st.tabs(["Título", "Ações Estratégicas"])

    # ====================================================
    # ABA 1 - TÍTULO
    # ====================================================
    with aba1:
        st.subheader("Editar Título do Resultado")

        novo_titulo = st.text_area(
            "Título do resultado",
            value=resultado.get("titulo", ""),
            height="content"
        )

        if st.button(
            "Salvar Título",
            key=f"salvar_titulo_lp_{resultado_idx}",
            icon=":material/save:"
        ):
            # Atualiza o título do RLP.
            resultados_lp[resultado_idx]["titulo"] = novo_titulo

            # Garante que o RLP tenha um ID.
            if "_id" not in resultados_lp[resultado_idx]:
                resultados_lp[resultado_idx]["_id"] = str(ObjectId())

            estrategia.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "resultados_longo_prazo.resultados_lp":
                            resultados_lp
                    }
                }
            )

            st.success("Resultado atualizado com sucesso!")
            time.sleep(2)
            st.cache_data.clear()
            st.rerun(scope="fragment")

    # ====================================================
    # ABA 2 - AÇÕES ESTRATÉGICAS
    # ====================================================
    with aba2:
        acoes = resultado.get("acoes_estrategicas", [])

        # --------------------------
        # ADICIONAR NOVA AÇÃO
        # --------------------------
        with st.expander(
            "Adicionar nova ação estratégica",
            expanded=False,
            icon=":material/add_notes:"
        ):

            novo_titulo_acao = st.text_area(
                "Título da nova ação estratégica",
                key=f"nova_acao_lp_{resultado_idx}"
            )

            if st.button(
                "Adicionar ação estratégica",
                key=f"btn_add_acao_lp_{resultado_idx}",
                icon=":material/add:"
            ):

                nova_acao = {
                    "_id": str(ObjectId()),
                    "nome_acao_estrategica": novo_titulo_acao,
                }

                resultados_lp[resultado_idx].setdefault(
                    "acoes_estrategicas", []
                ).append(nova_acao)

                estrategia.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"resultados_longo_prazo.resultados_lp": resultados_lp}}
                )

                st.success("Nova ação estratégica adicionada!")
                time.sleep(2)
                st.cache_data.clear()
                st.rerun(scope="fragment")

        st.write("")

        # --------------------------
        # EDITAR AÇÕES EXISTENTES
        # --------------------------
        for a_idx, acao in enumerate(acoes):

            titulo_acao = acao.get(
                "nome_acao_estrategica",
                f"Ação Estratégica {a_idx + 1}"
            )

            with st.expander(titulo_acao):

                novo_nome_acao = st.text_area(
                    "Título da ação estratégica",
                    value=titulo_acao,
                    key=f"acao_lp_{resultado_idx}_{a_idx}"
                )

                if st.button(
                    "Salvar",
                    key=f"salvar_acao_lp_{resultado_idx}_{a_idx}",
                    icon=":material/save:"
                ):

                    resultados_lp[resultado_idx]["acoes_estrategicas"][a_idx].update({
                        "nome_acao_estrategica": novo_nome_acao
                    })

                    estrategia.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"resultados_longo_prazo.resultados_lp": resultados_lp}}
                    )

                    st.success("Ação estratégica atualizada!")
                    time.sleep(2)
                    st.cache_data.clear()
                    st.rerun(scope="fragment")


# Tipos de dado dos indicadores OEO
TIPOS_INDICADOR = ["int", "float"]

# Rótulos exibidos na tela para cada tipo
ROTULOS_TIPO_INDICADOR = {
    "int": "Número inteiro",
    "float": "Número decimal",
}

# Valores antigos ainda salvos no banco -> novo formato
TIPOS_INDICADOR_LEGADOS = {
    "Número inteiro": "int",
    "Número decimal": "float",
}

OPCAO_CADASTRAR_INDICADOR = "--Cadastrar indicador--"

def normalizar_tipo_indicador(tipo):
    """Converte o tipo antigo ("Número inteiro"/"Número decimal") para "int"/"float"."""
    return TIPOS_INDICADOR_LEGADOS.get(tipo, tipo)

@st.dialog("Editar objetivo estratégico", width="large", on_dismiss="rerun")
def editar_objetivo_estrategico_dialog(obj_idx):

    doc = estrategia.find_one(
        {"objetivos_estrategicos_institucionais": {"$exists": True}}
    )

    objetivos = doc["objetivos_estrategicos_institucionais"]["obj_estrat_inst"]

    objetivo = objetivos[obj_idx]


    def salvar_objetivos():
        """Grava a lista completa de objetivos no MongoDB."""
        estrategia.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "objetivos_estrategicos_institucionais.obj_estrat_inst": objetivos
            }}
        )


    # Garante que o objetivo tenha um _id (usado como 'id_objetivo'
    # na coleção 'indicadores_oeo').
    if "_id" not in objetivo:
        objetivo["_id"] = str(ObjectId())
        salvar_objetivos()

    id_objetivo = str(objetivo["_id"])

    pode_editar_indicadores = usuario_e_do_monitoramento()

    nomes_abas = ["Título", "Ações Estratégicas"]
    if pode_editar_indicadores:
        nomes_abas.append("Indicadores")

    abas = st.tabs(nomes_abas)
    aba1, aba2 = abas[0], abas[1]

    # =================================================
    # ABA 1 - TÍTULO
    # =================================================
    with aba1:
        titulo_atual = objetivo.get("titulo", "")

        novo_titulo = st.text_area(
            "Título do objetivo",
            value=titulo_atual,
            height="content"
        )

        if st.button("Salvar", icon=":material/save:"):
            objetivos[obj_idx]["titulo"] = novo_titulo
            salvar_objetivos()

            st.success("Título atualizado com sucesso!")
            time.sleep(2)
            st.cache_data.clear()
            st.rerun(scope="fragment")

    # =================================================
    # ABA 2 - AÇÕES ESTRATÉGICAS
    # =================================================
    with aba2:
        acoes = objetivo.get("acoes_estrategicas", [])

        # -------------------------------------------------
        # ADICIONAR NOVA AÇÃO
        # -------------------------------------------------
        with st.expander("Adicionar ação estratégica"):
            nova_acao = st.text_area(
                "Título da ação estratégica",
                key=f"nova_acao_obj_{obj_idx}"
            )

            if st.button(
                "Adicionar ação",
                icon=":material/add:",
                key=f"add_acao_obj_{obj_idx}"
            ):

                nova = {
                    "_id": str(ObjectId()),
                    "acao_estrategica_obj": nova_acao
                }

                objetivo.setdefault("acoes_estrategicas", []).append(nova)
                salvar_objetivos()

                st.success("Ação estratégica adicionada com sucesso!")
                time.sleep(2)
                st.cache_data.clear()
                st.rerun(scope="fragment")

        st.write("")

        # -------------------------------------------------
        # EDITAR AÇÕES EXISTENTES
        # -------------------------------------------------
        for i, acao in enumerate(acoes):

            titulo = acao.get("acao_estrategica_obj", f"Ação {i+1}")

            with st.expander(titulo):
                novo_nome = st.text_area(
                    "Título da ação estratégica",
                    value=titulo,
                    key=f"acao_nome_{obj_idx}_{i}"
                )

                if st.button(
                    "Salvar",
                    key=f"salvar_acao_{obj_idx}_{i}",
                    icon=":material/save:"
                ):
                    objetivos[obj_idx]["acoes_estrategicas"][i]["acao_estrategica_obj"] = novo_nome
                    salvar_objetivos()

                    st.success("Ação estratégica atualizada com sucesso!")
                    time.sleep(2)
                    st.cache_data.clear()
                    st.rerun(scope="fragment")

    # =================================================
    # ABA 3 - INDICADORES (somente programa/área Monitoramento)
    # =================================================
    if not pode_editar_indicadores:
        return

    aba3 = abas[2]

    with aba3:

        # Indicadores deste objetivo, salvos na coleção 'indicadores_oeo'
        indicadores_obj = list(
            indicadores_oeo.find({"id_objetivo": id_objetivo})
        )

        mapa_ind_obj = {
            str(ind["_id"]): ind.get("nome_indicador", "Indicador sem nome")
            for ind in indicadores_obj
        }

        # Versão do formulário: incrementada após salvar, para
        # limpar o selectbox e os campos (as keys mudam).
        ver_key = f"ver_form_ind_obj_{obj_idx}"
        st.session_state.setdefault(ver_key, 0)
        ver = st.session_state[ver_key]

        ids_ordenados = sorted(
            mapa_ind_obj,
            key=lambda id_ind: mapa_ind_obj[id_ind].casefold()
        )

        selecao = st.selectbox(
            "Indicador",
            options=["", OPCAO_CADASTRAR_INDICADOR, *ids_ordenados],
            format_func=lambda op: mapa_ind_obj.get(op, op),
            key=f"sel_ind_obj_{obj_idx}_{ver}",
            width=400
        )

        if selecao:
            cadastrando = selecao == OPCAO_CADASTRAR_INDICADOR

            ind_atual = {} if cadastrando else next(
                ind for ind in indicadores_obj
                if str(ind["_id"]) == selecao
            )

            with st.container(horizontal=True):

                nome_ind = st.text_input(
                    "Nome do indicador",
                    value=ind_atual.get("nome_indicador", ""),
                    key=f"nome_ind_obj_{obj_idx}_{selecao}_{ver}",
                )

                tipo_atual = normalizar_tipo_indicador(ind_atual.get("tipo_dado"))

                tipo_ind = st.selectbox(
                    "Tipo",
                    options=TIPOS_INDICADOR,
                    format_func=lambda t: ROTULOS_TIPO_INDICADOR.get(t, t),
                    index=(
                        TIPOS_INDICADOR.index(tipo_atual)
                        if tipo_atual in TIPOS_INDICADOR
                        else None
                    ),
                    placeholder="",
                    key=f"tipo_ind_obj_{obj_idx}_{selecao}_{ver}",
                )

            st.write("")

            if st.button(
                "Cadastrar indicador" if cadastrando else "Salvar",
                icon=":material/add:" if cadastrando else ":material/save:",
                key=f"btn_ind_obj_{obj_idx}_{ver}"
            ):
                nome_ind = nome_ind.strip()

                duplicado = any(
                    ind.get("nome_indicador", "").strip().casefold()
                    == nome_ind.casefold()
                    and str(ind["_id"]) != selecao
                    for ind in indicadores_obj
                )

                if not nome_ind:
                    st.warning("Informe o nome do indicador.")

                elif tipo_ind is None:
                    st.warning("Selecione o tipo de dado.")

                elif duplicado:
                    st.warning("Já existe um indicador com esse nome neste objetivo.")

                else:
                    if cadastrando:
                        resultado = indicadores_oeo.insert_one({
                            "id_objetivo": id_objetivo,
                            "nome_indicador": nome_ind,
                            "tipo_dado": tipo_ind
                        })

                        # Cria a meta vazia do novo indicador no objetivo,
                        # para que ele apareça no registro de entregas.
                        estrategia.update_one(
                            {"_id": doc["_id"]},
                            {"$push": {
                                f"objetivos_estrategicos_institucionais.obj_estrat_inst.{obj_idx}.metas": {
                                    "id_indicador": str(resultado.inserted_id),
                                    "objetivo": "",
                                    "alcancado": ""
                                }
                            }}
                        )

                    else:
                        indicadores_oeo.update_one(
                            {"_id": ind_atual["_id"]},
                            {"$set": {
                                "nome_indicador": nome_ind,
                                "tipo_dado": tipo_ind
                            }}
                        )

                    st.session_state[ver_key] += 1

                    st.success(
                        "Indicador cadastrado com sucesso!" if cadastrando
                        else "Indicador atualizado com sucesso!"
                    )
                    time.sleep(2)
                    st.cache_data.clear()
                    st.rerun(scope="fragment")


def _safe_key(text):
    """Gera uma chave segura para Streamlit a partir de um texto (sem chars especiais)."""

    if text is None:
        return "none"

    return re.sub(r"\W+", "_", str(text)).strip("_").lower()


def _format_responsaveis_list(responsaveis_list, responsaveis_dict):
    """
    Recebe lista de responsáveis (pode conter dicts com {'$oid': '...'} ou ObjectId/str)
    e retorna string formatada com nomes.
    """

    nomes = []

    for r in responsaveis_list:
        if isinstance(r, dict) and "$oid" in r:
            key = str(r["$oid"])

        else:
            key = str(r)
        nomes.append(responsaveis_dict.get(key, "Desconhecido"))

    return ", ".join(nomes) if nomes else "-"


def normalizar_lista_ids(lista):
    """
    Converte uma lista que pode conter ObjectId, dict {'$oid': ...} ou str
    para uma lista de strings.
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


def buscar_entregas_relacionadas_por_id(
    *,
    projetos_db,
    responsaveis_dict,
    acoes_programa_ids=None,
    programas=None,
    anos_referencia=None,
    projetos=None
):
    """
    Retorna as entregas relacionadas a um conjunto de ações estratégicas
    de programas/áreas (acoes_programa_ids). O vínculo com eixos,
    resultados de médio/longo prazo e objetivos estratégicos agora é
    indireto: passa pela ação estratégica do programa vinculada à entrega
    (campo 'acoes_estrat_programa').
    """

    entregas_filtradas = []

    if not acoes_programa_ids:
        return entregas_filtradas

    acoes_programa_ids = set(acoes_programa_ids)

    for projeto in projetos_db:
        sigla = projeto.get("sigla", "-")

        if projetos and sigla not in projetos:
            continue

        for entrega in projeto.get("entregas", []):
            acoes_entrega_ids = normalizar_lista_ids(
                entrega.get("acoes_estrat_programa", [])
            )

            if not acoes_programa_ids.intersection(acoes_entrega_ids):
                continue

            if programas:
                programas_projeto = normalizar_lista_ids(projeto.get("programas", []))
                if not any(p in programas for p in programas_projeto):
                    continue

            if anos_referencia:
                anos_entrega = set(entrega.get("anos_de_referencia", []) or [])
                if not anos_entrega.intersection(set(anos_referencia)):
                    continue

            progresso = entrega.get("progresso")
            progresso_formatado = (
                f"{progresso}%" if progresso not in [None, ""] else ""
            )

            entregas_filtradas.append({
                "Projeto": sigla,
                "Entrega": entrega.get("nome_da_entrega", "-"),
                "Previsão de Conclusão": entrega.get("previsao_da_conclusao", "-"),
                "Responsáveis": _format_responsaveis_list(
                    entrega.get("responsaveis", []),
                    responsaveis_dict
                ),
                "Situação": entrega.get("situacao", "-"),
                "Ano(s) de Referência": ", ".join(
                    entrega.get("anos_de_referencia", []) or []
                ),
                "Progresso": progresso_formatado
            })

    return entregas_filtradas


def exibir_entregas_como_tabela(entregas_list, key_prefix="tabela", key_suffix=None):
    """
    Recebe a lista de entregas (lista de dicts) e exibe como ui.table com key única.
    Faz parsing da coluna 'Previsão de Conclusão' para ordenar corretamente (DD/MM/YYYY).
    """
    if not entregas_list:
        return None

    df = pd.DataFrame(entregas_list)

    # Parse para datetime considerando dia/mês/ano; mantém strings inválidas como NaT
    if "Previsão de Conclusão" in df.columns:
        df["_dt_previsao"] = pd.to_datetime(df["Previsão de Conclusão"], dayfirst=True, errors="coerce")
        df = df.sort_values(by="_dt_previsao", ascending=True).drop(columns=["_dt_previsao"])

    # montar key única
    if key_suffix is None:
        key_suffix = pd.util.hash_pandas_object(df).sum()  # fallback (não muito legível, mas único)
    key = f"{key_prefix}_{_safe_key(key_suffix)}"

    # exibir
    ui.table(data=df, key=key)
    return df


def buscar_entregas_por_acao(nome_acao):
    entregas_relacionadas = []

    projetos = projetos_ispn.find(
        {"entregas.acoes_resultados_medio_prazo": nome_acao},
        {"sigla": 1, "entregas": 1}
    )

    for projeto in projetos:
        sigla = projeto.get("sigla", "")

        for entrega in projeto.get("entregas", []):

            if nome_acao in entrega.get("acoes_resultados_medio_prazo", []):

                progresso = entrega.get("progresso")
                progresso_formatado = (
                    f"{progresso}%" if progresso not in [None, ""] else ""
                )

                entregas_relacionadas.append({
                    "Projeto": sigla,
                    "Entrega": entrega.get("nome_da_entrega", ""),
                    "Situação": entrega.get("situacao", ""),
                    "Previsão": entrega.get("previsao_da_conclusao", ""),
                    "Ano(s) de Referência": ", ".join(map(str, sorted(entrega.get("anos_de_referencia", [])))),
                    "Progresso": progresso_formatado
                })

    return entregas_relacionadas


@st.cache_data(ttl=300, show_spinner=False)
def carregar_estrategia():
    return estrategia.find_one(
        {"estrategia.eixos_da_estrategia": {"$exists": True}}
    )


@st.cache_data(ttl=300, show_spinner=False)
def carregar_indicadores():
    return list(indicadores.find())


@st.cache_data(ttl=300, show_spinner=False)
def carregar_indicadores_oeo():
    """Carrega os indicadores dos Objetivos Estratégicos Organizacionais."""
    return list(indicadores_oeo.find())


@st.cache_data(ttl=300, show_spinner=False)
def carregar_lancamentos(filtro=None):
    return list(lancamentos_indicadores.find(filtro or {}))


@st.cache_data(ttl=300, show_spinner=False)
def carregar_projetos_com_entregas():
    return list(
        projetos_ispn.find(
            {"entregas": {"$exists": True, "$ne": []}},
            {
                "entregas": 1,
                "sigla": 1,
                "programas": 1
            }
        )
    )


@st.cache_data(ttl=300, show_spinner=False)
def carregar_pessoas():
    return list(db["pessoas"].find({}, {"nome_completo": 1}))


@st.cache_data(ttl=300, show_spinner=False)
def calcular_mapa_soma_indicadores(_lancamentos):
    mapa = {}
    for lanc in _lancamentos:
        id_ind = str(lanc.get("id_do_indicador"))
        valor = br_to_float(lanc.get("valor"))
        mapa[id_ind] = mapa.get(id_ind, 0) + valor
    return mapa


@st.cache_data(ttl=300, show_spinner=False)
def carregar_programas():
    return list(
        programas_areas.find(
            {},
            {"nome_programa_area": 1}
        )
    )


@st.cache_data(ttl=300, show_spinner=False)
def carregar_acoes_estrategicas_programas():
    """
    Carrega todas as ações estratégicas de todos os programas/áreas,
    já achatadas em uma lista única, cada uma trazendo os
    relacionamentos com eixos, resultados de médio/longo prazo e
    objetivos estratégicos organizacionais.
    """
    programas_db = programas_areas.find(
        {"acoes_estrategicas": {"$exists": True, "$ne": []}},
        {"nome_programa_area": 1, "acoes_estrategicas": 1}
    )

    acoes_flat = []

    for programa in programas_db:
        programa_id = str(programa["_id"])
        programa_nome = programa.get("nome_programa_area", "-")

        for acao in programa.get("acoes_estrategicas", []):
            acoes_flat.append({
                "id": str(acao["_id"]),
                "nome": acao.get("acao_estrategica", "Ação sem nome"),
                "programa_id": programa_id,
                "programa_nome": programa_nome,
                "eixo_relacionado": normalizar_lista_ids(acao.get("eixo_relacionado", [])),
                "resultados_medio_prazo_relacionados": normalizar_lista_ids(acao.get("resultados_medio_prazo_relacionados", [])),
                "resultados_longo_prazo_relacionados": normalizar_lista_ids(acao.get("resultados_longo_prazo_relacionados", [])),
                "objetivos_estrategicos_relacionados": normalizar_lista_ids(acao.get("objetivos_estrategicos_relacionados", [])),
            })

    return acoes_flat


def acoes_programa_relacionadas(todas_acoes_programa, campo, elemento_id):
    """
    Retorna as ações estratégicas de programas/áreas relacionadas a um
    eixo, resultado de médio/longo prazo ou objetivo estratégico
    organizacional específico. 'campo' é o nome do campo de
    relacionamento dentro de cada ação (ex.: 'eixo_relacionado',
    'resultados_medio_prazo_relacionados', 'resultados_longo_prazo_relacionados',
    'objetivos_estrategicos_relacionados').
    """
    return [
        acao for acao in todas_acoes_programa
        if elemento_id in acao.get(campo, [])
    ]


def normalizar_id(valor):
    """
    Converte ObjectId, dict {'$oid': ...} ou str em str limpa.
    """

    if isinstance(valor, ObjectId):
        return str(valor)

    if isinstance(valor, dict) and "$oid" in valor:
        return str(valor["$oid"])

    if valor is None:
        return None

    return str(valor)


###########################################################################################################
# INTERFACE PRINCIPAL
###########################################################################################################


st.header("Planejamento Estratégico")
st.write('')

# ----------------------------------------------------
# FILTROS — APENAS PARA ENTREGAS
# ----------------------------------------------------
with st.form("filtros_entregas", border=False):
    col1, col2, col3 = st.columns(3)

    # ----------------------------------
    # PROJETO
    # ----------------------------------
    projetos_disponiveis = sorted(
        {
            proj.get("sigla")
            for proj in projetos_ispn.find(
                {
                    "entregas": {
                        "$exists": True,
                        "$ne": []
                    }
                },
                {"sigla": 1}
            )
            if proj.get("sigla")
        }
    )

    with col1:
        projetos_selecionados = st.multiselect(
            "Projeto",
            options=projetos_disponiveis,
            default=st.session_state.get("filtro_projetos", []),
            placeholder=""
        )

    # ----------------------------------
    # PROGRAMA
    # ----------------------------------
    lista_programas = carregar_programas()
    mapa_programas = {
        str(p["_id"]): p["nome_programa_area"]
        for p in lista_programas
    }

    programas_ids_com_entregas = set()
    for proj in projetos_ispn.find(
        {
            "entregas": {"$exists": True, "$ne": []},
            "programas": {"$exists": True, "$ne": []}
        },
        {"programas": 1}
    ):
        for p in proj.get("programas", []):
            programas_ids_com_entregas.add(str(p))

    programas_opcoes = {
        mapa_programas[pid]: pid
        for pid in programas_ids_com_entregas
        if pid in mapa_programas
    }

    with col2:
        programas_selecionados_nomes = st.multiselect(
            "Programa",
            options=sorted(programas_opcoes.keys()),
            default=[],
            placeholder=""
        )

    programas_selecionados = [
        programas_opcoes[nome]
        for nome in programas_selecionados_nomes
    ]

    # ----------------------------------
    # ANOS DE REFERÊNCIA
    # ----------------------------------
    anos_ref_disponiveis = sorted({
        ano
        for proj in projetos_ispn.find(
            {},
            {"entregas.anos_de_referencia": 1}
        )
        for ent in proj.get("entregas", []) or []
        for ano in ent.get("anos_de_referencia", []) or []
    })

    with col3:
        anos_ref_selecionados = st.multiselect(
            "Ano(s) de referência",
            options=anos_ref_disponiveis,
            default=st.session_state.get("filtro_anos_referencia", []),
            placeholder=""
        )

    aplicar = st.form_submit_button(
        "Aplicar filtros",
        icon=":material/filter_alt:"
    )


# ------------------------------------------------
# APLICAÇÃO DOS FILTROS (SESSION_STATE)
# ------------------------------------------------
if aplicar:
    st.session_state["filtro_projetos"] = projetos_selecionados
    st.session_state["filtro_programas"] = programas_selecionados
    st.session_state["filtro_anos_referencia"] = anos_ref_selecionados

    st.success("Filtros aplicados com sucesso")
    time.sleep(2)
    st.rerun()

st.write("")
st.write("")

projetos_com_entregas = carregar_projetos_com_entregas()
pessoas = carregar_pessoas()
responsaveis_dict = {
    str(p["_id"]): p["nome_completo"]
    for p in pessoas
}


# ------------------------------------------------
# MAPAS DE INDICADORES (usados pelo bloco único de Metas)
# ------------------------------------------------
todos_indicadores = carregar_indicadores()
mapa_indicadores = {
    str(ind["_id"]): ind
    for ind in todos_indicadores
}

mapa_nomes_indicadores = {
    ind_id: ind.get("nome_indicador", "Indicador sem nome")
    for ind_id, ind in mapa_indicadores.items()
}

nome_para_id_indicadores = mapa_nome_para_id_indicadores(mapa_nomes_indicadores)

todas_acoes_programa = carregar_acoes_estrategicas_programas()

# ------------------------------------------------
# MODO DE EDIÇÃO GLOBAL
# ------------------------------------------------
if "modo_edicao" not in st.session_state:
    st.session_state.modo_edicao = False

if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}:
    col1, col2 = st.columns([5,1])
    with col2:
        st.toggle(
            "Modo de edição",
            key="modo_edicao"
        )

st.write("")


# aba_tm, aba_est, aba_res_mp, aba_res_lp, aba_ebj_est_ins = st.tabs(['Teoria da mudança', 'Estratégia', 'Resultados de Médio Prazo', 'Resultados de Longo Prazo', 'Objetivos Estratégicos Institucionais'])
aba_est, aba_res_mp, aba_res_lp, aba_ebj_est_ins = st.tabs(['Estratégia', 'Resultados de Médio Prazo', 'Resultados de Longo Prazo', 'Objetivos Estratégicos Organizacionais'])

# ---------------------------
# ABA ESTRATÉGIA
# ---------------------------
with aba_est:
    # ----------------------------------------------------
    # CARREGAR ESTRATÉGIA
    # ----------------------------------------------------
    estrategia_doc = carregar_estrategia()

    titulo_pagina_atual = (
        estrategia_doc.get("estrategia", {}).get("titulo_pagina_estrategia", "")
        if estrategia_doc else ""
    )

    lista_estrategias_atual = (
        estrategia_doc.get("estrategia", {}).get("eixos_da_estrategia", [])
        if estrategia_doc else []
    )

    # ----------------------------------------------------
    # MODO EDIÇÃO
    # ----------------------------------------------------
    col1, col2 = st.columns([4, 1])
    if st.session_state.modo_edicao:
        with col2:
            st.button(
                "Editar aba",
                icon=":material/edit:",
                key="editar_titulo_estrategia",
                on_click=editar_estrategia_dialog,
                use_container_width=True
            )

    st.write("")

    st.subheader(
        titulo_pagina_atual
        if titulo_pagina_atual
        else "Promoção de Paisagens Produtivas Ecossociais"
    )

    st.write("")

    # ----------------------------------------------------
    # ORDENAR EIXOS
    # ----------------------------------------------------
    def extrair_numero(item):
        try:
            return int(item["titulo"].split(" - ")[0])
        except:
            return float("inf")
    lista_estrategias_ordenada = sorted(
        lista_estrategias_atual,
        key=extrair_numero
    )

    # ----------------------------------------------------
    # LOOP DOS EIXOS
    # ----------------------------------------------------
    for eixo in lista_estrategias_ordenada:
        eixo_id = str(eixo["_id"])
        titulo_eixo = eixo.get("titulo", "Título não definido")

        with st.expander(f"**{titulo_eixo}**"):

            # --------------------------------------------
            # BOTÃO EDITAR EIXO
            # --------------------------------------------
            if st.session_state.modo_edicao:
                col1, col2 = st.columns([4, 1])
                col2.button(
                    "Editar eixo",
                    key=f"editar_{_safe_key(titulo_eixo)}",
                    on_click=editar_eixos_da_estrategia_dialog,
                    args=(eixo, estrategia_doc, estrategia),
                    use_container_width=True,
                    icon=":material/edit:"
                )

            # --------------------------------------------
            # METAS DO EIXO (Indicador / Objetivo / Alcançado)
            # --------------------------------------------
            bloco_metas(
                metas_atual=metas_com_seed_de_indicadores(eixo),
                mapa_nomes_indicadores=mapa_nomes_indicadores,
                nome_para_id_indicadores=nome_para_id_indicadores,
                chave=f"eixo_{eixo_id}",
                campo_mongo="estrategia.eixos_da_estrategia.$[elem].metas",
                doc_id=estrategia_doc["_id"],
                colecao=estrategia,
                array_filters=[{"elem._id": eixo["_id"]}]
            )

            # --------------------------------------------
            # ENTREGAS DO EIXO
            # --------------------------------------------
            st.divider()

            st.markdown("##### **:material/package_2: Entregas Planejadas / Realizadas:**")

            st.write("")

            acoes_prog_eixo = acoes_programa_relacionadas(
                todas_acoes_programa, "eixo_relacionado", eixo_id
            )

            entregas_filtradas = buscar_entregas_relacionadas_por_id(
                projetos_db=projetos_com_entregas,
                responsaveis_dict=responsaveis_dict,
                acoes_programa_ids=[a["id"] for a in acoes_prog_eixo],
                programas=st.session_state.get("filtro_programas", []),
                anos_referencia=st.session_state.get("filtro_anos_referencia", []),
                projetos=st.session_state.get("filtro_projetos", [])
            )

            if entregas_filtradas:
                exibir_entregas_como_tabela(
                    entregas_filtradas,
                    key_prefix="tabela_entregas_eixo",
                    key_suffix=_safe_key(titulo_eixo)
                )

            else:
                st.caption("**Nenhuma entrega registrada para este eixo.**")

# ---------------------------
# ABA RESULTADOS DE MÉDIO PRAZO
# ---------------------------
with aba_res_mp:

    # ----------------------------------------------------
    # CARREGAR DOCUMENTO DE RESULTADOS MP
    # ----------------------------------------------------
    doc = estrategia.find_one({"resultados_medio_prazo": {"$exists": True}})
    resultados_data = doc.get("resultados_medio_prazo", {}) if doc else {}

    titulo_pagina = resultados_data.get(
        "titulo_pagina_resultados_mp",
        "Resultados de Médio Prazo"
    )

    lista_resultados = resultados_data.get("resultados_mp", [])

    # ----------------------------------------------------
    # MODO EDIÇÃO
    # ----------------------------------------------------
    col1, col2 = st.columns([4, 1])

    if st.session_state.modo_edicao:
        with col2:
            st.button(
                "Editar aba",
                icon=":material/edit:",
                key="editar_titulo_result_mp",
                on_click=editar_titulo_pagina_resultados_mp_dialog,
                use_container_width=True
            )

    st.write("")
    st.subheader(titulo_pagina)
    st.write("")

    # ----------------------------------------------------
    # LOOP PELOS RESULTADOS DE MÉDIO PRAZO
    # ----------------------------------------------------
    for idx, resultado in enumerate(lista_resultados):
        titulo_result = resultado.get("titulo", f"Resultado {idx + 1}")

        with st.expander(titulo_result):

            # --------------------------------------------
            # BOTÃO EDITAR RESULTADO
            # --------------------------------------------
            if st.session_state.modo_edicao:
                col1, col2 = st.columns([4, 1])
                col2.button(
                    "Editar resultado",
                    icon=":material/edit:",
                    key=f"editar_resultado_mp_{idx}",
                    on_click=lambda i=idx: editar_titulo_de_cada_resultado_mp_dialog(i),
                    use_container_width=True
                )

            # --------------------------------------------
            # METAS DO RESULTADO (Indicador / Objetivo / Alcançado)
            # --------------------------------------------
            bloco_metas(
                metas_atual=resultado.get("metas", []),
                mapa_nomes_indicadores=mapa_nomes_indicadores,
                nome_para_id_indicadores=nome_para_id_indicadores,
                chave=f"rmp_{idx}",
                campo_mongo=f"resultados_medio_prazo.resultados_mp.{idx}.metas",
                doc_id=doc["_id"],
                colecao=estrategia
            )

            st.divider()

            # --------------------------------------------
            # AÇÕES ESTRATÉGICAS / ENTREGAS
            # --------------------------------------------
            st.markdown("##### :material/package_2: Entregas por ação estratégica:")
            st.write("")

            acoes_estrategicas = resultado.get("acoes_estrategicas", [])

            if not acoes_estrategicas:
                st.caption("Nenhuma ação estratégica cadastrada para este resultado.")

            else:
                for idx_acao, acao in enumerate(acoes_estrategicas):
                    nome_acao = acao.get(
                        "nome_acao_estrategica",
                        f"Ação {idx_acao + 1}"
                    )
                    acao_id = str(acao.get("_id", ""))

                    st.write(f"**{nome_acao}**")

                    # Ações de programa vinculadas a esta ação estratégica específica
                    acoes_prog_relacionadas = acoes_programa_relacionadas(
                        todas_acoes_programa,
                        "resultados_medio_prazo_relacionados",
                        acao_id
                    )

                    entregas_vinculadas = buscar_entregas_relacionadas_por_id(
                        projetos_db=projetos_com_entregas,
                        responsaveis_dict=responsaveis_dict,
                        acoes_programa_ids=[a["id"] for a in acoes_prog_relacionadas],
                        programas=st.session_state.get("filtro_programas", []),
                        anos_referencia=st.session_state.get("filtro_anos_referencia", []),
                        projetos=st.session_state.get("filtro_projetos", [])
                    )

                    if entregas_vinculadas:
                        exibir_entregas_como_tabela(
                            entregas_vinculadas,
                            key_prefix="tabela_entrega_por_acao",
                            key_suffix=f"{idx}_{idx_acao}"
                        )

                    else:
                        st.write("")
                        st.caption("**Nenhuma entrega vinculada a esta ação estratégica.**")

                    st.divider()

# ---------------------------
# ABA RESULTADOS DE LONGO PRAZO
# ---------------------------
with aba_res_lp:

    # ----------------------------------------------------
    # CARREGAR DOCUMENTO DE RESULTADOS DE LONGO PRAZO
    # ----------------------------------------------------
    doc = estrategia.find_one({"resultados_longo_prazo": {"$exists": True}})
    resultados_lp_data = doc.get("resultados_longo_prazo", {}) if doc else {}

    titulo_pagina_lp = resultados_lp_data.get(
        "titulo_pagina_resultados_lp",
        "Resultados de Longo Prazo - 2030"
    )

    lista_resultados_lp = resultados_lp_data.get("resultados_lp", [])

    # ----------------------------------------------------
    # MODO DE EDIÇÃO
    # ----------------------------------------------------
    col1, col2 = st.columns([4, 1])

    if st.session_state.modo_edicao:
        with col2:
            st.button(
                "Editar aba",
                icon=":material/edit:",
                key="editar_titulo_result_lp",
                on_click=editar_titulo_pagina_resultados_lp_dialog,
                use_container_width=True
            )

    st.write("")
    st.subheader(titulo_pagina_lp)
    st.write("")

    # ----------------------------------------------------
    # LOOP DOS RESULTADOS DE LONGO PRAZO
    # ----------------------------------------------------
    if lista_resultados_lp:
        for idx, resultado in enumerate(lista_resultados_lp):

            resultado_lp_id = str(resultado["_id"])
            titulo_result_lp = resultado.get("titulo", f"Resultado {idx + 1}")

            with st.expander(titulo_result_lp):
                # --------------------------------------------
                # BOTÃO EDITAR RESULTADO
                # --------------------------------------------
                if st.session_state.modo_edicao:
                    col1, col2 = st.columns([4, 1])
                    col2.button(
                        "Editar resultado",
                        icon=":material/edit:",
                        key=f"editar_resultado_lp_{idx}",
                        on_click=lambda i=idx: editar_titulo_de_cada_resultado_lp_dialog(i),
                        use_container_width=True
                    )

                # ====================================================
                # METAS DO RESULTADO (Indicador / Objetivo / Alcançado)
                # ====================================================
                bloco_metas(
                    metas_atual=metas_com_seed_de_indicadores(resultado),
                    mapa_nomes_indicadores=mapa_nomes_indicadores,
                    nome_para_id_indicadores=nome_para_id_indicadores,
                    chave=f"rlp_{idx}",
                    campo_mongo=f"resultados_longo_prazo.resultados_lp.{idx}.metas",
                    doc_id=doc["_id"],
                    colecao=estrategia
                )

                st.divider()

                # ====================================================
                # AÇÕES ESTRATÉGICAS / ENTREGAS (IGUAL AO MP)
                # ====================================================
                st.markdown("##### :material/package_2: Entregas por ação estratégica:")
                st.write("")

                acoes_estrategicas = resultado.get("acoes_estrategicas", [])

                if not acoes_estrategicas:
                    st.caption("Nenhuma ação estratégica cadastrada para este resultado.")

                else:
                    for idx_acao, acao in enumerate(acoes_estrategicas):
                        nome_acao = acao.get(
                            "nome_acao_estrategica",
                            f"Ação {idx_acao + 1}"
                        )
                        acao_id = str(acao.get("_id", ""))

                        st.write(f"**{nome_acao}**")

                        acoes_prog_relacionadas = acoes_programa_relacionadas(
                            todas_acoes_programa,
                            "resultados_longo_prazo_relacionados",
                            acao_id
                        )

                        entregas_vinculadas = buscar_entregas_relacionadas_por_id(
                            projetos_db=projetos_com_entregas,
                            responsaveis_dict=responsaveis_dict,
                            acoes_programa_ids=[a["id"] for a in acoes_prog_relacionadas],
                            programas=st.session_state.get("filtro_programas", []),
                            anos_referencia=st.session_state.get("filtro_anos_referencia", []),
                            projetos=st.session_state.get("filtro_projetos", [])
                        )

                        if entregas_vinculadas:
                            exibir_entregas_como_tabela(
                                entregas_vinculadas,
                                key_prefix="tabela_entrega_lp_por_acao",
                                key_suffix=f"{idx}_{idx_acao}"
                            )

                        else:
                            st.write("")
                            st.caption("**Nenhuma entrega vinculada a esta ação estratégica.**")

                        st.divider()

    else:
        st.caption("Nenhum resultado de longo prazo encontrado no banco de dados.")


# -----------------------------------------------------------
# ABA OBJETIVOS ESTRATEGICOS INSTITUCIONAIS
# -----------------------------------------------------------
with aba_ebj_est_ins:

    doc = estrategia.find_one(
        {"objetivos_estrategicos_institucionais": {"$exists": True}}
    )

    # Migra dados do formato antigo (indicadores dentro dos objetivos)
    # para a coleção 'indicadores_oeo' e apaga as chaves antigas.
    objetivos = migrar_objetivos_estrategicos(doc)

    # Indicadores agrupados por objetivo: {id_objetivo: [indicadores]}
    indicadores_por_objetivo = {}
    tipo_por_indicador_oeo = {}

    for ind in carregar_indicadores_oeo():
        indicadores_por_objetivo.setdefault(
            str(ind.get("id_objetivo")), []
        ).append(ind)

        tipo_por_indicador_oeo[str(ind["_id"])] = ind.get("tipo_dado")

    # "Alcançado" de cada indicador, somando os lançamentos do registro
    # de entregas (sem cache, para refletir os lançamentos mais recentes).
    alcancado_por_indicador = calcular_alcancado_oeo(
        list(
            lancamentos_indicadores_oeo.find(
                {},
                {"id_do_indicador": 1, "valor": 1, "data_anotacao": 1}
            )
        ),
        tipo_por_indicador_oeo
    )

    st.write('')
    st.subheader(doc["objetivos_estrategicos_institucionais"]["titulo_pagina_obj_estrat_inst"])
    st.write('')

    for idx, objetivo in enumerate(objetivos):
        with st.expander(f"**Objetivo {idx+1} - {objetivo['titulo']}**"):
            # --------------------------------------------
            # BOTÃO EDITAR
            # --------------------------------------------
            if st.session_state.modo_edicao:
                with st.container(horizontal=True, horizontal_alignment="right"):
                    st.button(
                        "Editar objetivo",
                        icon=":material/edit:",
                        key=f"editar_obj_{idx}",
                        on_click=lambda i=idx: editar_objetivo_estrategico_dialog(i)
                    )

            st.write("")
            st.write("")

            # ====================================================
            # METAS (Indicador / Objetivo / Alcançado)
            # ====================================================
            bloco_metas_objetivo(
                objetivo=objetivo,
                indicadores_obj=indicadores_por_objetivo.get(
                    str(objetivo["_id"]), []
                ),
                obj_idx=idx,
                doc_id=doc["_id"],
                alcancado_por_indicador=alcancado_por_indicador
            )

            st.divider()

            # ====================================================
            # AÇÕES ESTRATÉGICAS
            # ====================================================
            st.markdown("##### :material/package_2: Entregas por ação estratégica:")
            st.write("")

            acoes = objetivo.get("acoes_estrategicas", [])

            if not acoes:
                st.caption("Nenhuma ação estratégica cadastrada.")

            else:
                for idx_acao, acao in enumerate(acoes):
                    nome_acao = acao.get(
                        "acao_estrategica_obj",
                        f"Ação {idx_acao + 1}"
                    )
                    acao_id = str(acao.get("_id", ""))

                    st.write(f"**{nome_acao}**")

                    acoes_prog_relacionadas = acoes_programa_relacionadas(
                        todas_acoes_programa,
                        "objetivos_estrategicos_relacionados",
                        acao_id
                    )

                    entregas_vinculadas = buscar_entregas_relacionadas_por_id(
                        projetos_db=projetos_com_entregas,
                        responsaveis_dict=responsaveis_dict,
                        acoes_programa_ids=[a["id"] for a in acoes_prog_relacionadas],
                        programas=st.session_state.get("filtro_programas", []),
                        anos_referencia=st.session_state.get("filtro_anos_referencia", []),
                        projetos=st.session_state.get("filtro_projetos", [])
                    )

                    if entregas_vinculadas:
                        exibir_entregas_como_tabela(
                            entregas_vinculadas,
                            key_prefix="tabela_entrega_obj",
                            key_suffix=f"{idx}_{idx_acao}"
                        )

                    else:
                        st.write("")
                        st.caption("**Nenhuma entrega vinculada a esta ação estratégica.**")

                    st.divider()
                    
                    