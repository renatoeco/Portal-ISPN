import streamlit as st
import pandas as pd
from funcoes_auxiliares import conectar_mongo_portal_ispn
from pymongo import UpdateOne
from bson import ObjectId
import time
import datetime
import plotly.express as px

st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas

programas_areas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"] 
estrategia = db["estrategia"] 
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


# # Nome da página atual, usado como chave para contagem de acessos
# nome_pagina = "Programas e Áreas"

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

    for doc in dados_estrategia:
        if "resultados_medio_prazo" in doc:
            resultados_medio.extend(
                [r.get("titulo") for r in doc["resultados_medio_prazo"].get("resultados_mp", []) if r.get("titulo")]
            )
        if "resultados_longo_prazo" in doc:
            resultados_longo.extend(
                [r.get("titulo") for r in doc["resultados_longo_prazo"].get("resultados_lp", []) if r.get("titulo")]
            )
        if "estrategia" in doc:
            eixos_da_estrategia.extend(
                [e.get("titulo") for e in doc["estrategia"].get("eixos_da_estrategia", []) if e.get("titulo")]
            )


    # ------------------- Aba principal -------------------
    aba_principal, aba_acoes = st.tabs(["Informações Gerais", "Ações Estratégicas"])

    # ======================================================
    # ABA 1 - INFORMAÇÕES GERAIS
    # ======================================================
    with aba_principal:

        # Lista de coordenadores (sem mostrar ID no selectbox)
        nomes_coordenadores_lista = [
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
                    options=eixos_da_estrategia,
                    key=f"eixo_estrategia_add_{programa['id']}",
                    placeholder=""
                )

                resultados_mp_sel = st.multiselect(
                    "Contribui com quais resultados de médio prazo?",
                    options=resultados_medio,
                    key=f"mp_add_{programa['id']}",
                    placeholder=""
                )

                resultados_lp_sel = st.multiselect(
                    "Contribui com quais resultados de longo prazo?",
                    options=resultados_longo,
                    key=f"lp_add_{programa['id']}",
                    placeholder=""
                )

                st.write("")

                adicionar = st.form_submit_button("Adicionar ação", use_container_width=False)
                if adicionar and nova_acao.strip():
                    nova_entrada = {
                        "acao_estrategica": nova_acao.strip(),
                        "eixo_relacionado": eixo_sel,
                        "resultados_medio_prazo_relacionados": resultados_mp_sel,
                        "resultados_longo_prazo_relacionados": resultados_lp_sel
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

            for idx, acao in enumerate(acoes_estrategicas):
                titulo_atual = acao.get("acao_estrategica", "")
                eixo_atual = acao.get("eixo_da_estrategia", [])
                relacionados_mp = acao.get("resultados_medio_prazo_relacionados", [])
                relacionados_lp = acao.get("resultados_longo_prazo_relacionados", [])

                with st.expander(f"{titulo_atual or 'Sem título'}", expanded=False):
                    toggle_edicao = st.toggle(
                        "Editar ação",
                        key=f"toggle_edicao_acao_{programa['id']}_{idx}",
                        value=False
                    )

                    if toggle_edicao:
                        # ---------------- MODO EDIÇÃO ----------------
                        novo_titulo = st.text_input(
                            "Título da ação estratégica",
                            value=titulo_atual,
                            key=f"titulo_{idx}"
                        )

                        eixo_sel = st.multiselect(
                            "Contribui com quais eixos da estratégia?",
                            options=eixos_da_estrategia,
                            default=eixo_atual,
                            placeholder="",
                            key=f"eixo_estrategia_edit_{idx}",
                        )

                        resultados_mp_sel = st.multiselect(
                            "Contribui com quais resultados de médio prazo?",
                            options=resultados_medio,
                            default=relacionados_mp,
                            placeholder="",
                            key=f"mp_edit_{idx}",
                        )

                        resultados_lp_sel = st.multiselect(
                            "Contribui com quais resultados de longo prazo?",
                            options=resultados_longo,
                            default=relacionados_lp,
                            placeholder="",
                            key=f"lp_edit_{idx}"
                        )

                        st.write("")
                        botoes = st.container(horizontal=True)

                        if botoes.button("Salvar alterações", key=f"salvar_acao_{idx}"):
                            programas_areas.update_one(
                                {
                                    "_id": ObjectId(programa["id"]),
                                    "acoes_estrategicas.acao_estrategica": titulo_atual
                                },
                                {
                                    "$set": {
                                        "acoes_estrategicas.$.acao_estrategica": novo_titulo,
                                        "acoes_estrategicas.$.eixo_relacionado": eixo_sel,
                                        "acoes_estrategicas.$.resultados_medio_prazo_relacionados": resultados_mp_sel,
                                        "acoes_estrategicas.$.resultados_longo_prazo_relacionados": resultados_lp_sel
                                    }
                                }
                            )
                            st.success("Ação estratégica atualizada com sucesso!")
                            time.sleep(2)
                            st.rerun()

                    else:
                        # ---------------- MODO VISUALIZAÇÃO ----------------
                        st.markdown(f"**Ação estratégica:** {titulo_atual}")

                        if eixo_atual:
                            st.markdown(f"**Eixo da estratégia:** {eixo_atual}")

                        st.write("")

                        if relacionados_mp:
                            st.markdown("**Contribui com os seguintes resultados de médio prazo:**")
                            for r in relacionados_mp:
                                st.markdown(f"- {r}")

                        if relacionados_lp:
                            st.markdown("**Contribui com os seguintes resultados de longo prazo:**")
                            for r in relacionados_lp:
                                st.markdown(f"- {r}")



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
                if (
                    pessoa.get("tipo de usuário", "").strip().lower() == "coordenador"
                    and str(pessoa.get("programa_area", "")).strip() == nome_programa.strip()
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
        nome_coordenador = colaborador_id_para_nome.get(str(coordenador_id), "Não encontrado")
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

for colab_doc in colaboradores_raw:
    if colab_doc.get("status", "").lower() != "ativo":
        continue  # Pula quem não for ativo

    nome = colab_doc.get("nome_completo", "Desconhecido")

    # # Ignora coordenadores
    # if nome in nomes_coordenadores:
    #     continue

    genero = colab_doc.get("gênero", "")
    
    programa_area_id = colab_doc.get("programa_area")
    programa_area = mapa_id_para_nome_programa.get(str(programa_area_id), "Não informado")

    # Contratos
    contratos = colab_doc.get("contratos", [])
    if contratos:
        # Pegamos o primeiro contrato para exibição (ou você pode iterar se quiser múltiplos)
        contrato = contratos[0]

        data_inicio_contrato = contrato.get("data_inicio", "")
        data_fim_contrato = contrato.get("data_fim", "")

        # Converte datas string para datetime, se necessário
        if isinstance(data_inicio_contrato, datetime.datetime):
            data_inicio_contrato = data_inicio_contrato.strftime("%d/%m/%Y")
        if isinstance(data_fim_contrato, datetime.datetime):
            data_fim_contrato = data_fim_contrato.strftime("%d/%m/%Y")

        # Projeto pagador
        projeto_pagador_list = contrato.get("projeto_pagador", [])
        if projeto_pagador_list:
            # Pega o primeiro ObjectId do contrato
            projeto_pagador_id = str(projeto_pagador_list[0])  # <-- aqui só convertemos para string
            projeto_pagador_sigla = mapa_id_para_sigla_projeto.get(projeto_pagador_id, "Não informado")
        else:
            projeto_pagador_sigla = "Não informado"
    else:
        data_inicio_contrato = ""
        data_fim_contrato = ""
        projeto_pagador_sigla = "Não informado"

    lista_equipe.append({
        "Nome": nome,
        "Gênero": genero,
        "Programa": programa_area,
        "Projeto": projeto_pagador_sigla,
        "data_inicio_contrato": data_inicio_contrato,
        "data_fim_contrato": data_fim_contrato
    })

# Dataframe de equipe
df_equipe = pd.DataFrame(lista_equipe)

# Ordena em ordem alfabética por nome
df_equipe = df_equipe.sort_values(by="Nome")

# Cria o DataFrame para exibição com coluna "Projetos"
df_equipe_exibir = df_equipe[["Nome", "Gênero", "Projeto", "data_inicio_contrato", "data_fim_contrato"]].copy()

df_equipe_exibir = df_equipe_exibir.rename(columns={
    "data_inicio_contrato": "Início do contrato",
    "data_fim_contrato": "Fim do contrato"
})






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
        df_equipe_filtrado = df_equipe[df_equipe['Programa'] == titulo_programa].copy()

        # Para exibir, pega só as linhas do df_equipe_exibir correspondentes
        df_equipe_exibir_filtrado = df_equipe_exibir.loc[df_equipe_filtrado.index].copy()
        df_equipe_exibir_filtrado.index = range(1, len(df_equipe_exibir_filtrado) + 1)

        # Prepara genero e prefixo só pra pronomes de tratamento na tela
        genero = programa['genero_coordenador']
        prefixo = "Coordenador" if genero == "Masculino" else "Coordenadora" if genero == "Feminino" else "Coordenador(a)"

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
            st.write(f"**{prefixo}:** {programa['coordenador']}")




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

            st.plotly_chart(fig)



        # Tebela de colaboradores
        st.dataframe(df_equipe_exibir_filtrado, hide_index=True)


        # Gráfico timeline de contratos de pessoas

        # Ordenar por ordem decrescente de data_fim_contrato
        df_equipe_exibir_filtrado = df_equipe_exibir_filtrado.sort_values(by='Fim do contrato', ascending=False)

        # Tentando calcular a altura do gráfico dinamicamente
        altura_base = 300  # altura mínima
        altura_extra = sum([10 / (1 + i * 0.01) for i in range(len(df_equipe_exibir_filtrado))])
        altura = int(altura_base + altura_extra)
        
        df_equipe_exibir_filtrado['Início do contrato'] = pd.to_datetime(df_equipe_exibir_filtrado['Início do contrato'], dayfirst=True)
        df_equipe_exibir_filtrado['Fim do contrato'] = pd.to_datetime(df_equipe_exibir_filtrado['Fim do contrato'], dayfirst=True)
        
        # Ordena em ordem decrescente pelo fim do contrato
        df_equipe_exibir_filtrado = df_equipe_exibir_filtrado.sort_values(by='Fim do contrato', ascending=False)
        
        fig = px.timeline(
            df_equipe_exibir_filtrado,
            x_start="Início do contrato",
            x_end="Fim do contrato",
            y="Nome",
            color="Projeto",
            hover_data=["Projeto"],
            height=altura
        )
        fig.update_layout(
            yaxis_title=None,
        )
        fig.add_vline(x=datetime.date.today(), line_width=1, line_dash="dash", line_color="gray")
        st.plotly_chart(fig)

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
            st.info("Nenhum projeto")



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
            st.plotly_chart(fig, key=f"timeline_{i}")



        # st.divider()



        # REDES E ARTICULAÇÕES DO PROGRAMA






        # INDICADORES DO PROGRAMA
        # st.write('')

        # st.write('**Indicadores do Programa:**')
        # st.write('')

        # sel1, sel2, sel3 = st.columns(3)
        
        # sel1.selectbox("Ano", ["2023", "2024", "2025"], key=f"ano_{i}")
        # sel2.selectbox("Projeto", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3"], key=f"projeto_{i}")
        
        # st.write('')
        # st.write('')

        # # Mostrar detalhes
        # # Função principal decorada com dialog
        # @st.dialog("Detalhes dos reportes de indicadores", width="large")
        # def mostrar_detalhes():
        #     df_indicadores = pd.DataFrame({
        #         "Reporte": [
        #             "Organizações do x",
        #             "Projeto x",
        #             "Preparação pra COP do Clima",
        #             "Apoio à Central do Programa 1"
        #         ],
        #         "Valor": [
        #             25,
        #             2,
        #             8,
        #             18,
        #         ],
        #         "Ano": [
        #             2023,
        #             2023,
        #             2023,
        #             2023,
        #         ],"Projeto": [
        #             "x",
        #             "x",
        #             "x",
        #             "x do Programa 1",
        #         ],
        #         "Observações": [
        #             "Contagem manual",
        #             "Por conversa telefônica",
        #             "Se refere ao seminário estadual",
        #             "Contagem manual",
        #         ],
        #         "Autor": [
        #             "João",
        #             "Maria",
        #             "José",
        #             "Pedro",
        #         ]
        #     })
        #     # st.dataframe(df_indicadores, hide_index=True)

        #     ui.table(df_indicadores)


        # # Função handler que será passada para on_click
        # def handler():
        #     def _handler():
        #         mostrar_detalhes()
        #     return _handler


        # col1, col2 = st.columns(2)

        # with col1.container(border=True):
        #     st.write('**Organizações e Comunidades**')
        #     st.button("Indicador X **51**", on_click=handler(), type="tertiary", key=f"org_51_{i}")
        #     st.button("Indicador X **12**", on_click=handler(), type="tertiary", key=f"org_12_{i}")
            



        # with col2.container(border=True):
        
        #     st.write('**Pessoas**')

        #     st.button("Indicador X **1500**", on_click=handler(), type="tertiary", key=f"pessoas_1500_{i}")
        #     st.button("Indicador X **300**", on_click=handler(), type="tertiary", key=f"pessoas_300_{i}")
        #     st.button("Indicador X **500**", on_click=handler(), type="tertiary", key=f"pessoas_500_{i}")
        #     st.button("Indicador X **350**", on_click=handler(), type="tertiary", key=f"pessoas_350_{i}")
        #     st.button("Indicador X **550**", on_click=handler(), type="tertiary", key=f"pessoas_550_{i}")
        #     st.button("Indicador X **200**", on_click=handler(), type="tertiary", key=f"pessoas_200_{i}")
        #     st.button("Indicador X **100**", on_click=handler(), type="tertiary", key=f"pessoas_100_{i}")
        #     st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"pessoas_50_{i}")
        #     st.button("Indicador X **75**", on_click=handler(), type="tertiary", key=f"pessoas_75_{i}")
        #     st.button("Indicador X **25**", on_click=handler(), type="tertiary", key=f"pessoas_25_{i}")

        # with col1.container(border=True):
        #     st.write('**Capacitações**')
        #     st.button("Indicador X **10**", on_click=handler(), type="tertiary", key=f"cap_10_{i}")
        #     st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"cap_50_{i}")
        #     st.button("Indicador X **75**", on_click=handler(), type="tertiary", key=f"cap_75_{i}")
        #     st.button("Indicador X **60**", on_click=handler(), type="tertiary", key=f"cap_60_{i}")
        #     st.button("Indicador X **100**", on_click=handler(), type="tertiary", key=f"cap_100_{i}")


        # with col1.container(border=True):
        #     st.write('**Intercâmbios**')
        #     st.button("Indicador X **10**", on_click=handler(), type="tertiary", key=f"inter_10_{i}")
        #     st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"inter_50_{i}")
        #     st.button("Indicador X **60**", on_click=handler(), type="tertiary", key=f"inter_60_{i}")

        # with col2.container(border=True):
        #     st.write('**Território**')
        #     st.button("Indicador X **25**", on_click=handler(), type="tertiary", key=f"ter_25_{i}")
        #     st.button("Indicador X **235**", on_click=handler(), type="tertiary", key=f"ter_235_{i}")
        #     st.button("Indicador X **321**", on_click=handler(), type="tertiary", key=f"ter_321_{i}")
        #     st.button("Indicador X **58**", on_click=handler(), type="tertiary", key=f"ter_58_{i}")
        #     st.button("Indicador X **147**", on_click=handler(), type="tertiary", key=f"ter_147_{i}")

        # with col1.container(border=True):
        #     st.write('**Tecnologia e Infra-estrutura**')
        #     st.button("Indicador X **20**", on_click=handler(), type="tertiary", key=f"tec_20_{i}")
        #     st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"tec_50_{i}")
        #     st.button("Indicador X **200**", on_click=handler(), type="tertiary", key=f"tec_200_{i}")

        # with col1.container(border=True):
        #     st.write('**Financeiro**')
        #     st.button("Indicador X **25200**", on_click=handler(), type="tertiary", key=f"fin_25200_{i}")
        #     st.button("Indicador X **14000**", on_click=handler(), type="tertiary", key=f"fin_14000_{i}")

        # with col2.container(border=True):
        #     st.write('**Comunicação**')
        #     st.button("Indicador X **25**", on_click=handler(), type="tertiary", key=f"com_25_{i}")
        #     st.button("Indicador X **14**", on_click=handler(), type="tertiary", key=f"com_14_{i}")
        #     st.button("Indicador X **12**", on_click=handler(), type="tertiary", key=f"com_12_{i}")
        #     st.button("Indicador X **35**", on_click=handler(), type="tertiary", key=f"com_35_{i}")
        #     st.button("Indicador X **24**", on_click=handler(), type="tertiary", key=f"com_24_{i}")

        # with col1.container(border=True):
        #     st.write('**Políticas Públicas**')
        #     st.button("Indicador X **5**", on_click=handler(), type="tertiary", key=f"pol_5_{i}")
        #     st.button("Indicador X **2**", on_click=handler(), type="tertiary", key=f"pol_2_{i}")
        #     st.button("Indicador X **6**", on_click=handler(), type="tertiary", key=f"pol_6_{i}")