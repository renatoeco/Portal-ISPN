import streamlit as st
import pandas as pd
from funcoes_auxiliares import conectar_mongo_portal_ispn
from pymongo import UpdateOne
from bson import ObjectId
import time
import datetime
import plotly.express as px
import streamlit_shadcn_ui as ui

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
colaboradores_raw = list(db["pessoas"].find())

# Carrega todos os projetos ISPN
dados_projetos_ispn = list(projetos_ispn.find())

# Carrega todos os programas
dados_programas = list(programas_areas.find())

# Carrega todos os doadores
dados_doadores = list(doadores.find())


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


@st.dialog("Gerenciar programa", width="large")
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
                    st.rerun()

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
                    st.rerun()

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
                            time.sleep(1)
                            st.rerun()

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
    #     st.success(f"{resultado.modified_count} programa(s) atualizado(s) com coordenador_id.")
    # else:
    #     st.info("Programas sem coordenador encontrados, mas nenhum coordenador correspondente foi localizado.")





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
        "Programa": programa_area,
        "Projeto": projeto_str,
        "Início do contrato": data_inicio_final,
        "Fim do contrato": data_fim_final
    })


# Dataframe de equipe
df_equipe = pd.DataFrame(lista_equipe)

df_equipe = pd.DataFrame(lista_equipe).sort_values("Nome")

df_equipe_exibir = df_equipe.copy()

df_equipe_exibir = df_equipe[
    ["Nome", "Gênero", "Projeto", "Início do contrato", "Fim do contrato"]
].copy()


# #############################################
# Início da Interface
# #############################################


st.header("Programas e Áreas")

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

        if set(st.session_state.get("tipo_usuario", [])) & {"admin", "coordenador(a)"}:
        
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
                st.write(f"**{prefixo}**")





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

        # Substitui None / NaN por string vazia
        df_tabela[["Início do contrato", "Fim do contrato"]] = (
            df_tabela[["Início do contrato", "Fim do contrato"]]
            .fillna("")
        )

        st.dataframe(df_tabela, hide_index=True)

        # Gráfico timeline de contratos de pessoas

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
        df_equipe_exibir_filtrado = df_equipe_exibir_filtrado.sort_values(by='Fim do contrato', ascending=False)

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

        # Filtra os projetos ligados ao programa atual pelo ID do programa
        projetos_do_programa = [
            p for p in dados_projetos_ispn
            if str(p.get("programa")) == str(id_programa)
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
                "Código": [],
                "Nome do projeto": [],
                "Início": [],
                "Fim": [],
                "Valor": [],
                "Doador": [],
                "Situação": []
            }

            for projeto in projetos_do_programa_ordenados:
                dados_projetos["Código"].append(projeto.get("codigo", ""))
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


            st.dataframe(df_projetos, hide_index=True)
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
                y="Código",
                color="Situação",
                hover_data=["Código"],
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

        # 1. Busca a estratégia do programa atual
        estrategia_programa = db.programas_areas.find_one({
            "nome_programa_area": titulo_programa
        })

        if not estrategia_programa or not estrategia_programa.get("acoes_estrategicas"):
            # st.info("Nenhuma ação estratégica cadastrada para este programa.")
            st.caption("Nenhuma ação estratégica cadastrada para este programa.")
  
        else:

            st.write("")

            acoes_estrategicas = estrategia_programa["acoes_estrategicas"]

            # 2. Buscar todos os projetos do programa novamente (coleção projetos_ispn)
            programa_id = ObjectId(programa.get("id"))

            projetos_com_entregas = list(db.projetos_ispn.find({
                "programa": programa_id
            }))


            # 3. Loop pelas ações estratégicas
            for i, acao in enumerate(acoes_estrategicas):
                nome_acao = acao["acao_estrategica"]

                with st.expander(nome_acao, expanded=True):

                    entregas_relacionadas = []

                    for proj in projetos_com_entregas:

                        codigo_proj = proj.get("codigo", "")
                        nome_proj = proj.get("nome_do_projeto", "")

                        for entrega in proj.get("entregas", []):

                            if nome_acao in entrega.get("acoes_relacionadas", []):

                                entregas_relacionadas.append({
                                    "Projeto": codigo_proj,
                                    "Nome da entrega": entrega.get("nome_da_entrega", ""),
                                    "Previsão de conclusão": entrega.get("previsao_da_conclusao", ""),
                                    "Situação": entrega.get("situacao", ""),
                                    "Anotações": entrega.get("anotacoes", "")
                                })

                    if entregas_relacionadas:

                        st.markdown("**Entregas:**")

                        df_entregas = pd.DataFrame(entregas_relacionadas)

                        ui.table(
                            data=df_entregas,
                            maxHeight=400,
                            key=f"tabela_entregas_{i}"   # key só aqui
                        )

                    else:
                        st.caption("Nenhuma entrega vinculada a esta ação estratégica do programa.")