import streamlit as st
from pymongo import MongoClient
import time
import pandas as pd
from datetime import datetime
from bson import ObjectId
import bson

@st.cache_resource
def conectar_mongo_portal_ispn():
    cliente = MongoClient(
    st.secrets["senhas"]["senha_mongo_portal_ispn"])
    db_portal_ispn = cliente["ISPN_Hub"]                   
    return db_portal_ispn


@st.cache_resource
def conectar_mongo_pls():
    cliente_2 = MongoClient(
    st.secrets["senhas"]["senha_mongo_pls"])
    db_pls = cliente_2["db_pls"]
    return db_pls



# VERSÃO NOVA
def altura_dataframe(df, linhas_adicionais=1):
    """
    Calcula a altura ideal para st.dataframe,
    garantindo que todas as linhas fiquem visíveis
    sem barra de rolagem.

    Parâmetros:
    - df: DataFrame exibido no dataframe
    - linhas_adicionais: linhas extras de folga (default=1)

    Retorna:
    - altura em pixels (int)
    """

    ALTURA_LINHA = 35      # altura média de cada linha
    ALTURA_HEADER = 38    # cabeçalho do dataframe

    try:
        total_linhas = len(df) + linhas_adicionais
    except Exception:
        total_linhas = linhas_adicionais

    altura = (total_linhas * ALTURA_LINHA) + ALTURA_HEADER

    return altura



# VERSÃO ANTIGA
def ajustar_altura_dataframe(
    df_nao_atualizado,
    linhas_adicionais=0,
    altura_maxima=None,  # Se None, não aplica limite
    #width="stretch",
    hide_index=True,
    column_config={
        "Link": st.column_config.Column(
            width="medium"  
        ),
        "Data da Última Ação Legislativa": st.column_config.Column(
            label="Última ação",  
        )
    }
):
    """
    Ajusta a altura da exibição de um DataFrame no Streamlit com base no número de linhas.
    Se 'altura_maxima' for informado, limita a altura até esse valor.
    """

    # Define a altura em pixels de cada linha
    altura_por_linha = 35  

    # Calcula a altura total necessária
    altura_total = ((df_nao_atualizado.shape[0] + linhas_adicionais) * altura_por_linha) + 2

    # Se altura_maxima foi informada, aplica o limite
    if altura_maxima is not None:
        altura_total = min(altura_total, altura_maxima)

    # Exibe o DataFrame no Streamlit
    st.dataframe(
        df_nao_atualizado,
        height=altura_total,
        #width=width,
        hide_index=hide_index,
        column_config=column_config
    )



# --- Conversor string brasileira -> float ---
def br_to_float(valor_str: str) -> float:
    """
    Converte string no formato brasileiro (1.234,56) para float (1234.56).
    """
    if not valor_str or not isinstance(valor_str, str):
        return 0.00
    # Remove pontos (milhares) e troca vírgula por ponto
    valor_str = valor_str.replace(".", "").replace(",", ".")
    try:
        return round(float(valor_str), 2)
    except ValueError:
        return 0.00


# --- Conversor float -> string brasileira ---
def float_to_br(valor_float: float) -> str:
    """
    Converte float (1234.56) para string no formato brasileiro (1.234,56).
    """
    if valor_float is None:
        return "0,00"
    return f"{valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Mapa de nomes legíveis dos indicadores
def formatar_nome_legivel(nome):
    
    NOMES_INDICADORES_LEGIVEIS = {
        "numero_de_organizacoes_apoiadas": "Número de organizações apoiadas",
        "numero_de_comunidades_fortalecidas": "Número de comunidades fortalecidas",
        "numero_de_familias": "Número de famílias",
        "numero_de_homens_jovens": "Número de homens jovens (até 29 anos)",
        "numero_de_homens_adultos": "Número de homens adultos",
        "numero_de_mulheres_jovens": "Número de mulheres jovens (até 29 anos)",
        "numero_de_mulheres_adultas": "Número de mulheres adultas",
        "numero_de_indigenas": "Número de indígenas",
        "numero_de_liderancas_comunitarias_fortalecidas": "Número de lideranças comunitárias fortalecidas",
        "numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_fundo_ecos": "Número de famílias comercializando produtos da sociobio com apoio do Fundo Ecos",
        "numero_de_familias_acessando_vendas_institucionais_com_apoio_do_fundo_ecos": "Número de famílias acessando vendas institucionais com apoio do Fundo Ecos",
        "numero_de_estudantes_recebendo_bolsa": "Número de estudantes recebendo bolsa",
        "numero_de_capacitacoes_realizadas": "Número de capacitações realizadas",
        "numero_de_homens_jovens_capacitados": "Número de homens jovens capacitados (até 29 anos)",
        "numero_de_homens_adultos_capacitados": "Número de homens adultos capacitados",
        "numero_de_mulheres_jovens_capacitadas": "Número de mulheres jovens capacitadas (até 29 anos)",
        "numero_de_mulheres_adultas_capacitadas": "Número de mulheres adultas capacitadas",
        "numero_de_intercambios_realizados": "Número de intercâmbios realizados",
        "numero_de_homens_em_intercambios": "Número de homens em intercâmbios",
        "numero_de_mulheres_em_intercambios": "Número de mulheres em intercâmbios",
        "numero_de_iniciativas_de_gestao_territorial_implantadas": "Número de iniciativas de Gestão Territorial implantadas",
        "area_com_manejo_ecologico_do_fogo_ha": "Área com manejo ecológico do fogo (ha)",
        "area_com_manejo_agroecologico_ha": "Área com manejo agroecológico (ha)",
        "area_com_manejo_para_restauracao_ha": "Área com manejo para restauração (ha)",
        "area_com_manejo_para_extrativismo_ha": "Área com manejo para extrativismo (ha)",
        "numero_de_agroindustiras_implementadas_ou_reformadas": "Número de agroindústrias implementadas/reformadas",
        "numero_de_tecnologias_instaladas": "Número de tecnologias instaladas",
        "numero_de_pessoas_beneficiadas_com_tecnologias": "Número de pessoas beneficiadas com tecnologias",
        "numero_de_videos_produzidos": "Número de vídeos produzidos",
        "numero_de_aparicoes_na_midia": "Número de aparições na mídia",
        "numero_de_publicacoes_de_carater_tecnico": "Número de publicações de caráter técnico",
        "numero_de_artigos_academicos_produzidos_e_publicados": "Número de artigos acadêmicos produzidos e publicados",
        "numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn": "Número de comunicadores comunitários contribuindo na execução das ações do ISPN",
        "faturamento_bruto_anual_pre_projeto": "Faturamento bruto anual pré-projeto",
        "faturamento_bruto_anual_pos_projeto": "Faturamento bruto anual pós-projeto",
        "volume_financeiro_de_vendas_institucionais_com_apoio_do_fundo_ecos": "Volume financeiro de vendas institucionais com apoio do Fundo Ecos",
        "numero_de_visitas_de_monitoramento_realizadas_ao_projeto_apoiado": "Número de visitas de monitoramento realizadas ao projeto apoiado",
        "valor_da_contrapartida_financeira_projetinhos": "Valor da contrapartida financeira projetinhos",
        "valor_da_contrapartida_nao_financeira_projetinhos": "Valor da contrapartida não financeira projetinhos",
        "especies": "Espécies",
        "numero_de_organizacoes_apoiadas_que_alavancaram_recursos": "Número de organizações apoiadas que alavancaram recursos",
        "valor_mobilizado_de_novos_recursos": "Valor mobilizado de novos recursos",
        "numero_de_politicas_publicas_monitoradas_pelo_ispn": "Número de políticas públicas monitoradas pelo ISPN",
        "numero_de_proposicoes_legislativas_acompanhadas_pelo_ispn": "Número de proposições legislativas acompanhadas pelo ISPN",
        "numero_de_contribuicoes_notas_tecnicas_participacoes_e_ou_documentos_que_apoiam_a_construcao_e_aprimoramento_de_politicas_publicas": "Número de contribuições (notas técnicas, participações e/ou documentos) que apoiam a construção e aprimoramento de políticas públicas"
    }
  
    return NOMES_INDICADORES_LEGIVEIS.get(nome, nome.replace("_", " ").capitalize())

def normalizar_texto(txt):
    if not txt:
        return None
    return " ".join(txt.split())

# Converter objectid para string
def convert_objectid(obj):
    if isinstance(obj, bson.ObjectId):
        return str(obj)
    elif isinstance(obj, list):
        return [convert_objectid(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    else:
        return obj





# Função do diálogo para gerenciar entregas
@st.dialog("Editar Entregas", width="large")
def dialog_editar_entregas():

    pagina_atual = st.session_state.get("pagina_anterior")
    mostrar_lancamentos = (pagina_atual == "pagina_projetos")
    
    db = conectar_mongo_portal_ispn()
    estrategia = db["estrategia"]  
    programas = db["programas_areas"]
    projetos_ispn = db["projetos_ispn"]  
    indicadores = db["indicadores"]
    colecao_lancamentos = db["lancamentos_indicadores"]
    
    df_projetos_ispn = pd.DataFrame(list(projetos_ispn.find()))
    df_pessoas = pd.DataFrame(list(db["pessoas"].find()))
    df_indicadores = pd.DataFrame(list(indicadores.find()))
    
    # Garantir string do ObjectId (Streamlit trabalha melhor)
    df_indicadores["_id"] = df_indicadores["_id"].astype(str)

    # Mapa: id -> nome legível
    mapa_indicadores = dict(
        zip(df_indicadores["_id"], df_indicadores["nome_indicador"])
    )

    # Lista de IDs (o que será salvo)
    indicadores_options = sorted(mapa_indicadores.keys(), key=lambda x: mapa_indicadores[x])

    
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
    
    # --- 2. Criar dicionários de mapeamento ---
    mapa_doador = {d["_id"]: d["nome_doador"] for d in db["doadores"].find()}
    mapa_programa = {p["_id"]: p["nome_programa_area"] for p in db["programas_areas"].find()}

    # --- 3. Aplicar os mapeamentos ao df_projetos_ispn ---
    df_projetos_ispn["doador_nome"] = df_projetos_ispn["doador"].apply(
        lambda x: mapa_doador.get(x, "não informado")
    )
    df_projetos_ispn["programa_nome"] = df_projetos_ispn["programa"].apply(
        lambda x: mapa_programa.get(x, "não informado")
    )

    # --- 4. Converter datas para datetime
    df_projetos_ispn['data_inicio_contrato'] = pd.to_datetime(
        df_projetos_ispn['data_inicio_contrato'], format="%d/%m/%Y", errors="coerce"
    )
    df_projetos_ispn['data_fim_contrato'] = pd.to_datetime(
        df_projetos_ispn['data_fim_contrato'], format="%d/%m/%Y", errors="coerce"
    )

    # PESSOAS
    # Converter objectid para string em df_pessoas
    df_pessoas = df_pessoas.map(convert_objectid)

    # Criar mapa de _id -> nome_programa_area (como string)
    mapa_programa = {str(p["_id"]): p["nome_programa_area"] for p in db["programas_areas"].find()}

    # Criar mapa de _id -> nome_completo (coordenador)
    mapa_coordenador = {str(p["_id"]): p["nome_completo"] for p in db["pessoas"].find()}

    # Aplicar mapeamento no df_pessoas
    df_pessoas["programa_area_nome"] = df_pessoas["programa_area"].map(mapa_programa)
    df_pessoas["coordenador_nome"] = df_pessoas["coordenador"].map(mapa_coordenador)
    df_pessoas = df_pessoas.sort_values(by="nome_completo", ascending=True).reset_index(drop=True)
    
    st.write("")

    # =========================
    # RESOLVER PROJETO
    # =========================

    projeto_sigla = st.session_state.get("projeto_selecionado")

    if projeto_sigla is None:
        projetos_options = sorted(df_projetos_ispn["sigla"].dropna().unique().tolist())

        projeto_sigla = st.selectbox(
            "Selecione o projeto",
            options=[""] + projetos_options,
            index=0
        )

        if not projeto_sigla:
            st.info("Selecione um projeto para gerenciar as entregas.")
            st.stop()

        st.session_state["projeto_selecionado"] = projeto_sigla

    # Projeto já definido (veio da página)
    projeto_info = df_projetos_ispn.loc[
        df_projetos_ispn["sigla"] == projeto_sigla
    ].iloc[0]


    entregas_existentes = projeto_info.get("entregas", [])
    # Garante que entregas_existentes seja sempre uma lista
    if not isinstance(entregas_existentes, list):
        entregas_existentes = []
        
    dados_estrategia = list(estrategia.find({}))
    dados_programas = list(programas.find({}))
    programa_do_projeto = projeto_info.get("programa")
    
    resultados_longo = []
    eixos_da_estrategia = []
    acoes_estrategicas_dict = {}

    for doc in dados_programas:
        # Só entra se for o programa do projeto
        if doc["_id"] == programa_do_projeto:

            if "acoes_estrategicas" in doc:
                for a in doc["acoes_estrategicas"]:
                    acao = a.get("acao_estrategica")

                    if acao:
                        texto_exibido = f"{acao}"
                        acoes_estrategicas_dict[texto_exibido] = acao

    acoes_por_resultado_mp = {}
    acoes_medio_prazo = []
    metas_mp = []
    
    resultados_longo_set = set()

    for doc in dados_estrategia:
        if "resultados_medio_prazo" in doc:

            for resultado in doc["resultados_medio_prazo"].get("resultados_mp", []):

                titulo = resultado.get("titulo")

                acoes = [
                    a.get("nome_acao_estrategica")
                    for a in resultado.get("acoes_estrategicas", [])
                    if a.get("nome_acao_estrategica")
                ]

                if titulo and acoes:
                    acoes_por_resultado_mp[titulo] = acoes
                    acoes_medio_prazo.extend(acoes)
                
                for meta in resultado.get("metas", []):
                    nome_meta = meta.get("nome_meta_mp")
                    if nome_meta:
                        metas_mp.append(f"{nome_meta}")
    

        rlp = doc.get("resultados_longo_prazo", {})
        for r in rlp.get("resultados_lp", []):
            titulo = normalizar_texto(r.get("titulo"))
            if titulo:
                resultados_longo_set.add(titulo)
                
        if "estrategia" in doc:
            eixos_da_estrategia.extend(
                [e.get("titulo") for e in doc["estrategia"].get("eixos_da_estrategia", []) if e.get("titulo")]
            )
            
    metas_mp = sorted(list(set(metas_mp)))
    resultados_longo = sorted(resultados_longo_set)
    acoes_medio_prazo = sorted(list(set(acoes_medio_prazo)))
        
    #  Criar lista de opções (nome + _id) ordenadas alfabeticamente
    df_pessoas_ordenado = df_pessoas.sort_values("nome_completo", ascending=True)
    responsaveis_dict = {
        str(row["_id"]): row["nome_completo"]
        for _, row in df_pessoas_ordenado.iterrows()
    }
    responsaveis_options = list(responsaveis_dict.keys())
    
    if mostrar_lancamentos:
        aba_entregas, aba_lancamentos_entregas = st.tabs(
            [
                ":material/package_2: Gerenciar entregas",
                ":material/rocket_launch: Registros de entregas"
            ]
        )
    else:
        aba_entregas = st.container()
        st.write("")

    with aba_entregas:

        with st.expander("Adicionar entrega", expanded=False):
            with st.form("form_nova_entrega", border=False):
                
                nome_da_entrega = st.text_input("Nome da entrega")
                
                col1, col2 = st.columns(2)
                
                previsao_da_conclusao = col1.date_input("Previsão de conclusão", format="DD/MM/YYYY")
                
                ano_atual = datetime.now().year
                ano_inicial = ano_atual - 1
                ano_final = ano_atual + 6

                anos_disponiveis = list(range(ano_inicial, ano_final + 1))

                anos_de_referencia = col2.multiselect(
                    "Anos de referência",
                    options=anos_disponiveis,
                    #default=[ano_atual],
                    placeholder=""
                )
                
                col1, col2 = st.columns(2)
                
                situacao = col1.selectbox("Situação", ["Prevista", "Atrasada", "Concluída"])
                
                opcoes_progresso = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
                
                progresso_nova_entrega = col2.selectbox(
                    "Progresso",
                    options=opcoes_progresso,
                    format_func=lambda x: f"{x}%",
                    key="progresso_nova_entrega"
                )
                
                responsaveis_selecionados = st.multiselect(
                    "Responsáveis",
                    options=responsaveis_options,
                    format_func=lambda x: responsaveis_dict.get(x, "Desconhecido"),
                    placeholder=""
                )
                
                acoes_medio_prazo_relacionadas = st.multiselect(
                    "Contribui com quais ações estratégicas dos resultados de médio prazo?",
                    options=acoes_medio_prazo,
                    placeholder=""
                )
                
                metas_mp_relacionadas = st.multiselect(
                    "Contribui com quais metas dos resultados de médio prazo?",
                    options=metas_mp,
                    placeholder=""
                )

                resultados_longo_prazo_relacionados = st.multiselect(
                    "Contribui com quais resultados de longo prazo?",
                    options=resultados_longo,
                    placeholder=""
                )
                
                eixos_relacionados = st.multiselect(
                    "Contribui com quais eixos da estratégia PPP-ECOS?",
                    options=eixos_da_estrategia,
                    placeholder=""
                )
                
                acoes_relacionados = st.multiselect(
                    "Contribui com quais ações estratégicas do programa?",
                    options=list(acoes_estrategicas_dict.keys()),
                    placeholder=""
                )
                
                indicadores_relacionados = st.multiselect(
                    "Contribui com quais indicadores?",
                    options=indicadores_options, 
                    format_func=lambda x: formatar_nome_legivel(mapa_indicadores.get(x, "")),
                    placeholder=""
                )

                st.write("")
                
                salvar_nova = st.form_submit_button("Salvar entrega", icon=":material/save:")
                if salvar_nova:
                    
                    if not nome_da_entrega:
                        st.warning("Por favor preencha o nome da entrega.")
                    
                    else:
                        
                        acoes_puras = [acoes_estrategicas_dict[a] for a in acoes_relacionados]
                    
                        nova_entrega = {
                            "_id": ObjectId(),
                            "nome_da_entrega": nome_da_entrega,
                            "previsao_da_conclusao": previsao_da_conclusao.strftime("%d/%m/%Y"),
                            "responsaveis": [ObjectId(r) for r in responsaveis_selecionados],
                            "situacao": situacao,
                            "progresso": int(progresso_nova_entrega),
                            "anos_de_referencia": [str(a) for a in anos_de_referencia],
                            "acoes_resultados_medio_prazo": acoes_medio_prazo_relacionadas,
                            "resultados_longo_prazo_relacionados": resultados_longo_prazo_relacionados,
                            "eixos_relacionados": eixos_relacionados,
                            "acoes_relacionadas": acoes_puras,
                            "metas_resultados_medio_prazo": metas_mp_relacionadas,
                            "indicadores_relacionados": [ObjectId(i) for i in indicadores_relacionados]
                        }

                        # adiciona ao array existente
                        projetos_ispn.update_one(
                            {"_id": projeto_info["_id"]},
                            {"$push": {"entregas": nova_entrega}}
                        )

                        st.success("Entrega adicionada com sucesso!")
                        time.sleep(2)
                        st.rerun()
        

        # ============================
        # EXIBIR ENTREGAS EXISTENTES
        # ============================
        if entregas_existentes:
            st.write("### Entregas cadastradas:")
            
            for i, entrega in enumerate(entregas_existentes):
                with st.expander(f"{entrega.get('nome_da_entrega', 'Sem nome')}"):
                    # Mostrar nomes reais dos responsáveis
                    responsaveis_ids = entrega.get("responsaveis", [])
                    responsaveis_nomes = [
                        responsaveis_dict.get(str(r), "Desconhecido") for r in responsaveis_ids
                    ]
                    responsaveis_formatados = ", ".join(responsaveis_nomes) if responsaveis_nomes else "-"

                    # Alternar entre visualização e edição
                    modo_edicao = st.toggle("Modo de edição", key=f"toggle_edit_{i}")

                    if not modo_edicao:
                        # --- Modo de visualização ---
                        st.write(f"**Previsão:** {entrega.get('previsao_da_conclusao', '-')}")
                        st.write(f"**Responsáveis:** {responsaveis_formatados}")
                        st.write(f"**Anos de referência:** {', '.join(entrega.get('anos_de_referencia', []))}")
                        st.write(f"**Situação:** {entrega.get('situacao', '-')}")
                        
                        progresso = entrega.get("progresso", 0)
                        try:
                            progresso = int(progresso)
                        except (TypeError, ValueError):
                            progresso = 0
                        st.write(f"**Progresso:** {progresso}%")
                        
                        st.write("")

                        # Resultados de médio prazo
                        acoes_medio = entrega.get("acoes_resultados_medio_prazo", [])
                        if acoes_medio:
                            st.markdown("**Ações estratégicas dos resultados de médio prazo:**")
                            for a in acoes_medio:
                                st.markdown(f"- {a}")
                        else:
                            st.markdown("**Ações estratégicas dos resultados de médio prazo:** -")
                        
                        # Metas dos resultados de médio prazo
                        metas_entrega = entrega.get("metas_resultados_medio_prazo", [])
                        if metas_entrega:
                            st.markdown("**Metas dos resultados de médio prazo:**")
                            for m in metas_entrega:
                                st.markdown(f"- {m}")
                        else:
                            st.markdown("**Metas dos resultados de médio prazo:** -")

                        st.write("")

                        # Resultados de longo prazo
                        resultados_longo_entrega = entrega.get("resultados_longo_prazo_relacionados", [])
                        if resultados_longo_entrega:
                            st.markdown("**Resultados de longo prazo:**")
                            for r in resultados_longo_entrega:
                                st.markdown(f"- {r}")
                        else:
                            st.markdown("**Resultados de longo prazo:** -")


                        st.write("")

                        # Eixos estratégicos
                        eixos = entrega.get("eixos_relacionados", [])
                        if eixos:
                            st.markdown("**Eixos estratégicos:**")
                            for e in eixos:
                                st.markdown(f"- {e}")
                        else:
                            st.markdown("**Eixos estratégicos:** -")
                            
                        st.write("")

                        # Ações estratégicas
                        acoes = entrega.get("acoes_relacionadas", [])
                        if acoes:
                            st.markdown("**Ações estratégicas do programa:**")
                            for a in acoes:
                                st.markdown(f"- {a}")
                        else:
                            st.markdown("**Ações estratégicas do programa:** -")
                        
                        st.write("")
                        
                        indicadores_entrega = entrega.get("indicadores_relacionados", [])

                        if indicadores_entrega:
                            st.markdown("**Indicadores:**")
                            for i in indicadores_entrega:
                                nome = mapa_indicadores.get(str(i), "Indicador não encontrado")
                                st.markdown(f"- {formatar_nome_legivel(nome)}")

                        else:
                            st.markdown("**Indicadores:** -")

                        st.write("")
                        
                    else:
                        # --- Modo de edição ---
                        with st.form(f"form_edit_entrega_{i}", border=False):
                            entrega_editada = {**entrega}

                            entrega_editada["nome_da_entrega"] = st.text_input(
                                "Nome da entrega", entrega.get("nome_da_entrega", "")
                            )
                            
                            col1, col2 = st.columns(2)

                            entrega_editada["previsao_da_conclusao"] = col1.date_input(
                                "Previsão de conclusão",
                                pd.to_datetime(entrega.get("previsao_da_conclusao"), format="%d/%m/%Y").date()
                                if entrega.get("previsao_da_conclusao") else datetime.today(),
                                format="DD/MM/YYYY"
                            )
                            entrega_editada["previsao_da_conclusao"] = entrega_editada["previsao_da_conclusao"].strftime("%d/%m/%Y")

                            anos_salvos = [
                                int(a) for a in entrega.get("anos_de_referencia", [])
                                if str(a).isdigit()
                            ]

                            entrega_editada["anos_de_referencia"] = col2.multiselect(
                                "Anos de referência",
                                options=anos_disponiveis,
                                default=anos_salvos,
                                placeholder=""
                            )

                            col1, col2 = st.columns(2)

                            entrega_editada["situacao"] = col1.selectbox(
                                "Situação",
                                ["Prevista", "Atrasada", "Concluída"],
                                index=["Prevista", "Atrasada", "Concluída"].index(
                                    entrega.get("situacao", "Prevista")
                                )
                            )
                            
                            progresso_atual = entrega.get("progresso", 0)
                            try:
                                progresso_atual = int(progresso_atual)
                            except (TypeError, ValueError):
                                progresso_atual = 0
                                
                            entrega_editada["progresso"] = col2.selectbox(
                                "Progresso",
                                options=opcoes_progresso,
                                index=opcoes_progresso.index(progresso_atual) if progresso_atual in opcoes_progresso else 0,
                                format_func=lambda x: f"{x}%",
                                key=f"entrega_progresso_{i}"
                            )

                            responsaveis_existentes = [str(r) for r in entrega.get("responsaveis", [])]
                            entrega_editada["responsaveis"] = st.multiselect(
                                "Responsáveis",
                                options=list(responsaveis_dict.keys()),
                                default=responsaveis_existentes,
                                format_func=lambda x: responsaveis_dict.get(x, "Desconhecido"),
                                placeholder="Selecione os responsáveis"
                            )

                            entrega_editada["acoes_resultados_medio_prazo"] = st.multiselect(
                                "Contribui com quais ações estratégicas dos resultados de médio prazo?",
                                options=acoes_medio_prazo,
                                default=entrega.get("acoes_resultados_medio_prazo", []),
                                placeholder=""
                            )
                            
                            entrega_editada["metas_resultados_medio_prazo"] = st.multiselect(
                                "Contribui com quais metas dos resultados de médio prazo?",
                                options=metas_mp,
                                default=entrega.get("metas_resultados_medio_prazo", []),
                                placeholder=""
                            )

                            
                            valores_salvos = [
                                normalizar_texto(v)
                                for v in entrega.get("resultados_longo_prazo_relacionados", [])
                                if normalizar_texto(v) in resultados_longo
                            ]

                            entrega_editada["resultados_longo_prazo_relacionados"] = st.multiselect(
                                "Contribui com quais resultados de longo prazo?",
                                options=resultados_longo,
                                default=valores_salvos,
                                placeholder=""
                            )

                            entrega_editada["eixos_relacionados"] = st.multiselect(
                                "Contribui com quais eixos da estratégia PPP-ECOS?",
                                options=eixos_da_estrategia,
                                default=entrega.get("eixos_relacionados", []),
                                placeholder=""
                            )

                            acoes_selecionadas_labels = [
                                label for label, valor in acoes_estrategicas_dict.items()
                                if valor in entrega.get("acoes_relacionadas", [])
                            ]

                            acoes_selecionadas_labels = st.multiselect(
                                "Contribui com quais ações estratégicas dos programas?",
                                options=list(acoes_estrategicas_dict.keys()),
                                default=acoes_selecionadas_labels,
                                placeholder=""
                            )

                            # Converter de volta para o valor puro (sem o nome do programa)
                            entrega_editada["acoes_relacionadas"] = [
                                acoes_estrategicas_dict[label] for label in acoes_selecionadas_labels
                            ]
                            
                            default_ids = [str(i) for i in entrega.get("indicadores_relacionados", [])]

                            entrega_editada["indicadores_relacionados"] = st.multiselect(
                                "Contribui com quais indicadores?",
                                options=indicadores_options,
                                default=default_ids,
                                format_func=lambda x: formatar_nome_legivel(mapa_indicadores.get(x, "")),
                                placeholder=""
                            )
                            
                            entrega_editada["indicadores_relacionados"] = [
                                ObjectId(i) for i in entrega_editada["indicadores_relacionados"]
                            ]
                            
                            st.write("")

                            salvar_edicao = st.form_submit_button("Salvar alterações", icon=":material/save:")
                            if salvar_edicao:
                                entrega_editada["anos_de_referencia"] = [
                                    str(a) for a in entrega_editada["anos_de_referencia"]
                                ]

                                entrega_editada["responsaveis"] = [ObjectId(r) for r in entrega_editada["responsaveis"]]

                                entregas_existentes[i] = entrega_editada
                                projetos_ispn.update_one(
                                    {"_id": projeto_info["_id"]},
                                    {"$set": {"entregas": entregas_existentes}}
                                )
                                st.success("Entrega atualizada!")
                                time.sleep(2)
                                st.rerun()

    if mostrar_lancamentos:
        with aba_lancamentos_entregas:

            #st.subheader("Lançamentos de entregas")

            if not entregas_existentes:
                st.info("Este projeto ainda não possui entregas cadastradas.")
                st.stop()

            with st.expander("Adicionar registro", expanded=False):

                # =========================
                # Selecionar entrega
                # =========================
                nomes_entregas = [e["nome_da_entrega"] for e in entregas_existentes]

                entrega_selecionada_nome = st.selectbox(
                    "Selecione a entrega",
                    options=nomes_entregas
                )

                entrega_idx = nomes_entregas.index(entrega_selecionada_nome)
                entrega = entregas_existentes[entrega_idx]

                # =========================
                # Dados do lançamento
                # =========================

                ano_lancamento = st.selectbox(
                    "Ano do lançamento",
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

                for indicador in indicadores_entrega:

                    nome_indicador = mapa_indicadores.get(str(indicador), "Indicador não encontrado")
                    st.markdown(f"**{formatar_nome_legivel(nome_indicador)}**")
                    
                    col1, col2 = st.columns([2, 3])

                    # Campo dinâmico
                    if formatar_nome_legivel(nome_indicador) in indicadores_float:
                        valor = col1.number_input(
                            "Valor",
                            step=0.01,
                            key=f"valor_{indicador}"
                        )
                    elif formatar_nome_legivel(nome_indicador) == indicador_texto:
                        valor = col1.text_input(
                            "Valor",
                            key=f"valor_{indicador}"
                        )
                    else:
                        valor = col1.number_input(
                            "Valor",
                            step=1,
                            key=f"valor_{indicador}"
                        )

                    observacoes = col2.text_input(
                        "Observações",
                        key=f"obs_{indicador}"
                    )

                    valores_indicadores[indicador] = {
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

                    entregas_existentes[entrega_idx].setdefault(
                        "lancamentos_entregas", []
                    ).append(novo_lancamento_entrega)

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
                    
            st.markdown("### Registros cadastrados:")
            for entrega_idx, entrega in enumerate(entregas_existentes):

                lancamentos = entrega.get("lancamentos_entregas", [])
                nome_entrega = entrega.get("nome_da_entrega", "Entrega")

                if not lancamentos:
                    continue

                for idx, lanc in enumerate(lancamentos):

                    key_base = f"entrega_{entrega_idx}_lanc_{idx}"

                    autor = lanc.get("autor", "Autor não informado")
                    ano = lanc.get("ano", "-")

                    with st.expander(
                        f"{nome_entrega} - {autor} - {ano}",
                        expanded=False
                    ):
                        modo_edicao = st.toggle(
                            "Modo de edição",
                            key=f"toggle_{key_base}"
                        )

                        if not modo_edicao:
                            st.write(f"**Ano:** {lanc.get('ano', '-')}")
                            st.write(
                                f"**Anotações:** {lanc.get('anotacoes', '-') or '-'}"
                            )

                        else:
                            novo_ano = st.selectbox(
                                "Ano do lançamento",
                                options=anos_disponiveis,
                                index=anos_disponiveis.index(int(lanc.get("ano"))),
                                key=f"edit_ano_{key_base}"
                            )

                            novas_anotacoes = st.text_area(
                                "Anotações do lançamento",
                                value=lanc.get("anotacoes", ""),
                                key=f"edit_anot_{key_base}"
                            )

                            salvar_edicao = st.button(
                                "Salvar alterações",
                                icon=":material/save:",
                                key=f"salvar_{key_base}"
                            )

                            if salvar_edicao:
                                lanc["ano"] = str(novo_ano)
                                lanc["anotacoes"] = novas_anotacoes

                                entregas_existentes[entrega_idx]["lancamentos_entregas"][idx] = lanc

                                projetos_ispn.update_one(
                                    {"_id": projeto_info["_id"]},
                                    {"$set": {"entregas": entregas_existentes}}
                                )

                                st.success("Lançamento atualizado!")
                                time.sleep(2)
                                st.rerun()
