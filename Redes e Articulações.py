import streamlit as st
import pandas as pd
from datetime import datetime
import time
import re
import unicodedata
from bson import ObjectId
import plotly.graph_objects as go

from funcoes_auxiliares import (
    conectar_mongo_portal_ispn,
    obter_servico_drive,
    enviar_arquivo_drive,
    obter_pasta_rede,
    gerar_link_drive
)

import smtplib
from email.mime.text import MIMEText




###########################################################################################################
# CONFIGURAÇÕES DO STREAMLIT
###########################################################################################################


st.set_page_config(layout="wide", page_title="Redes e Articulações")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')



# Traduzindo o texto do st.file_uploader
# Texto interno
st.markdown("""
<style>
/* Esconde o texto padrão */
[data-testid="stFileUploaderDropzone"] div div::before {
    content: "Arraste e solte os arquivos aqui";
    color: rgba(49, 51, 63, 0.7);
    font-size: 0.9rem;
    font-weight: 400;
    position: absolute;
    top: 50px;              /* fixa no topo */
    left: 50%;
    transform: translate(-50%, 10%);
    pointer-events: none;
}
/* Esconde o texto original */
[data-testid="stFileUploaderDropzone"] div div span {
    visibility: hidden !important;
}
</style>
""", unsafe_allow_html=True)

# Traduzindo Botão do file_uploader
st.markdown("""
<style>
/* Alvo: apenas o botão dentro do componente de upload */
section[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"] {
    font-size: 0px !important;   /* esconde o texto original */
    padding-left: 14px !important;
    padding-right: 14px !important;
    min-width: 160px !important;
}
/* Insere o texto traduzido */
section[data-testid="stFileUploaderDropzone"] button[data-testid="stBaseButton-secondary"]::after {
    content: "Selecionar arquivo";
    font-size: 14px !important;
    color: inherit;
}
</style>
""", unsafe_allow_html=True)






######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
redes = db["redes_articulacoes"]
pessoas = db["pessoas"]
estatistica = db["estatistica"]
ufs_municipios = db["ufs_municipios"]
programas_areas = db["programas_areas"]

# Cria a coleção de registros caso ainda não exista
if "registros_incidencia_politica" not in db.list_collection_names():
    db.create_collection("registros_incidencia_politica")

registros_incidencia = db["registros_incidencia_politica"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_redes"
nome_pagina = "Redes e Articulações"

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
# FUNÇÕES
######################################################################################################


def _chave_ordenacao(texto: str) -> str:
    """Remove acentos para ordenar alfabeticamente (ex: 'Água Boa' junto dos 'A')."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


TIPO_INCIDENCIA = "Incidência política"
TIPO_ARTICULACAO = "Articulação"
OPCOES_TIPO_REGISTRO = [TIPO_INCIDENCIA, TIPO_ARTICULACAO]

OPCOES_ABRANGENCIA = [
    "Nacional (ex: Ministérios, Congresso, Conselhos Nacionais)",
    "Estadual (ex: Secretarias Estaduais, Assembleias Legislativas)",
    "Municipal (ex: Prefeituras, Câmaras de Vereadores)",
    "Internacional (ex: COP, ONU)",
]

HELP_TIPO_REGISTRO = (
    "**Opção 1 - Incidência política:** Ações direcionadas a influenciar políticas públicas, "
    "tomadores de decisão, proposição legislativa e espaços de governança formais para a "
    "defesa de direitos.  \n\n"
    "**Opção 2 - Articulação:** Eventos de articulação/rede, reuniões ampliadas, reuniões "
    "estratégicas, conferências de articulação específica que o ISPN faz parte, etc."
)

# Campos exclusivos de cada tipo (usados para limpar o documento quando o tipo muda na edição)
CAMPOS_INCIDENCIA = [
    "orgao_incidencia", "ator_impactado", "programas",
    "envolveu_outras_organizacoes", "organizacoes_envolvidas",
]
CAMPOS_ARTICULACAO = ["rede_articulacao"]


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_opcoes_programas() -> dict[str, str]:
    """
    Retorna {id_programa (str): nome_programa_area}, ordenado pelo nome.
    Os ids vão como string porque o cache e o multiselect lidam melhor com tipos simples.
    """
    programas = {
        str(p["_id"]): p["nome_programa_area"].strip()
        for p in programas_areas.find({}, {"nome_programa_area": 1})
        if p.get("nome_programa_area")
    }
    return dict(sorted(programas.items(), key=lambda item: _chave_ordenacao(item[1])))


# Opções fixas para status
status_opcoes = ["Ativa", "Em análise", "Inativa"]

tipos_rede_opcoes = ["Articulação","Conselho / Câmara Técnica", "Espaço de Incidência", "Outro"]

tipos_abrangencia = ["Nacional","Sub-nacional", "Internacional"]

# Nomes vindos da coleção programas_areas (sem repetição, em ordem alfabética)
programas_opcoes = list(dict.fromkeys(carregar_opcoes_programas().values()))


@st.dialog("Detalhes da rede", width="large", on_dismiss="rerun")
def mostrar_detalhes(rede_doc):
    st.subheader(rede_doc.get("rede_articulacao", ""))
    st.write("")
    tabs = st.tabs([":material/info: Informações gerais", ":material/notes: Acompanhamentos"])

    # =====================
    # Aba 1: Informações gerais
    # =====================
    with tabs[0]:

        # Nome do usuário logado
        usuario_logado = st.session_state.get("nome", "")

        # Lista de pontos focais da rede
        pontos_focais_rede = [
            p.strip()
            for p in rede_doc.get("ponto_focal", "").split(",")
            if p.strip()
        ]

        # Permissão de edição
        pode_editar_rede = (
            set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}
            or usuario_logado in pontos_focais_rede
        )

        if pode_editar_rede:
            modo_edicao = st.toggle("Editar", value=False, disabled=usuario_visitante)

            if not modo_edicao:
                # Exibição simples

                st.write(f"**Rede/Articulação:** {rede_doc.get('rede_articulacao', '')}")
                st.write(f"**Descrição da rede:** {rede_doc.get('descricao', '')}")
                st.write(f"**Ponto(s) Focal(is):** {rede_doc.get('ponto_focal', '')}")

                col1, col2, col3 = st.columns(3)

                col1.write(f"**Tema:** {rede_doc.get('tema', '')}")
                col2.write(f"**Tipo de Rede:** {rede_doc.get('tipo_rede', '')}")
                col3.write(f"**Abrangência:** {rede_doc.get('abrangencia', '')}")

                col1, col2, col3, col4 = st.columns(4)

                col1.write(f"**Programa:** {rede_doc.get('programa', '')}")
                col2.write(f"**Grau de Prioridade:** {rede_doc.get('prioridade', '')}")
                col3.write(f"**Dedicação:** {rede_doc.get('dedicacao', '')}")
                col4.write(f"**Status:** {rede_doc.get('status', 'ativa')}")


            else:
                # =====================
                # Opções dinâmicas do banco
                # =====================
                prioridades_opcoes = sorted({r.get("prioridade") for r in redes.find() if r.get("prioridade")})
                dedicacao_opcoes = sorted({r.get("dedicacao") for r in redes.find() if r.get("dedicacao")})

                temas_opcoes = sorted({
                    t.strip()
                    for r in redes.find()
                    if r.get("tema")
                    for t in re.split(r",|;", r.get("tema"))
                    if t.strip()
                })

                pessoas_opcoes = sorted({p.get("nome_completo") for p in pessoas.find() if p.get("nome_completo")})

                # =====================
                # Campos editáveis
                # =====================
                
                rede_edit = st.text_input("Rede/Articulação", value=rede_doc.get("rede_articulacao", ""))

                descricao_edit = st.text_area("Descrição da rede", value=rede_doc.get("descricao", ""))

                ponto_focal_str = rede_doc.get("ponto_focal", "")
                ponto_focal_list = [p.strip() for p in ponto_focal_str.split(",")] if ponto_focal_str else []

                ponto_focal_edit = st.multiselect(
                    "Ponto(s) Focal(is)",
                    options=pessoas_opcoes,
                    default=[p for p in ponto_focal_list if p in pessoas_opcoes]
                )


                col1, col2, col3 = st.columns(3)

                temas_default = [
                    t.strip()
                    for t in re.split(r",|;", rede_doc.get("tema", ""))
                    if t.strip() and t.strip() in temas_opcoes
                ]

                temas_selecionados = col1.multiselect(
                    "Temas",
                    options=temas_opcoes,
                    default=temas_default,
                )
                
                tipo_rede_edit = col2.selectbox(
                    "Tipo de Rede",
                    options=tipos_rede_opcoes,
                    index=tipos_rede_opcoes.index(rede_doc.get("tipo_rede")) 
                    if rede_doc.get("tipo_rede") in tipos_rede_opcoes else None,
                    placeholder=""
                )

                abrangencia_edit = col3.selectbox(
                    "Abrangência",
                    options=tipos_abrangencia,
                    index=tipos_abrangencia.index(rede_doc.get("abrangencia")) 
                    if rede_doc.get("abrangencia") in tipos_abrangencia else None,
                    placeholder=""
                )
                
                col1, col2, col3, col4 = st.columns(4)
                
                programa_edit = col1.selectbox(
                    "Programa",
                    options=programas_opcoes,
                    index=programas_opcoes.index(rede_doc.get("programa"))
                    if rede_doc.get("programa") in programas_opcoes else None,
                    placeholder=""
                )

                prioridade_edit = col2.selectbox(
                    "Grau de Prioridade",
                    options=prioridades_opcoes,
                    index=prioridades_opcoes.index(rede_doc.get("prioridade")) if rede_doc.get("prioridade") in prioridades_opcoes else None,
                )

                dedicacao_edit = col3.selectbox(
                    "Dedicação",
                    options=dedicacao_opcoes,
                    index=dedicacao_opcoes.index(rede_doc.get("dedicacao")) if rede_doc.get("dedicacao") in dedicacao_opcoes else None,
                )


                status_edit = col4.selectbox(
                    "Status",
                    options=status_opcoes,
                    index=status_opcoes.index(rede_doc.get("status", "Ativa")) if rede_doc.get("status", "Ativa") in status_opcoes else None,
                )


                st.write("")

                if st.button("Salvar alterações", icon=":material/check:", type="primary"):
                    redes.update_one(
                        {"_id": rede_doc["_id"]},
                        {
                            "$set": {
                                "rede_articulacao": rede_edit,
                                "descricao": descricao_edit,
                                "descricao": descricao_edit,
                                "tema": ", ".join(temas_selecionados),
                                "ponto_focal": ", ".join(ponto_focal_edit),
                                "prioridade": prioridade_edit,
                                "dedicacao": dedicacao_edit,
                                "programa": programa_edit,
                                "status": status_edit, 
                                "tipo_rede": tipo_rede_edit,
                                "abrangencia": abrangencia_edit
                            }
                        },
                    )

                    st.success("Alterações salvas com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")

        else:
            # Exibição simples
            st.write("")
            st.write(f"**Rede/Articulação:** {rede_doc.get('rede_articulacao', '')}")
            st.write(f"**Descrição da rede:** {rede_doc.get('descricao', '')}")
            st.write(f"**Ponto(s) Focal(is):** {rede_doc.get('ponto_focal', '')}")

            col1, col2, col3 = st.columns(3)

            col1.write(f"**Tema:** {rede_doc.get('tema', '')}")
            col2.write(f"**Tipo de Rede:** {rede_doc.get('tipo_rede', '')}")
            col3.write(f"**Abrangência:** {rede_doc.get('abrangencia', '')}")

            col1, col2, col3, col4 = st.columns(4)

            col1.write(f"**Programa:** {rede_doc.get('programa', '')}")
            col2.write(f"**Grau de Prioridade:** {rede_doc.get('prioridade', '')}")
            col3.write(f"**Dedicação:** {rede_doc.get('dedicacao', '')}")
            col4.write(f"**Status:** {rede_doc.get('status', 'ativa')}")


    # Aba 2: Acompanhamento / Memória
    with tabs[1]:
        usuario_logado = st.session_state.get("nome", "Desconhecido")

        # Recarrega documento atualizado do Mongo
        rede_doc = redes.find_one({"_id": rede_doc["_id"]})

        # Obtém anotações atualizadas
        anotacoes = rede_doc.get("anotacoes") or []

        # ---------------- EXPANDER PARA ADICIONAR ANOTAÇÃO ----------------
        with st.expander("Adicionar novo acompanhamento", expanded=False, icon=":material/add_notes:"):

            with st.form(key=f"form_acompanhamento_{rede_doc['_id']}"):

                nova_data = datetime.now().date()
                
                # Campo de texto ------------------------------------------------------------
                novo_texto = st.text_area(
                    "Texto do acompanhamento",
                    key="nova_anotacao",
                    height="content",
                    disabled=usuario_visitante
                )

                # Upload de arquivos ------------------------------------------------------------
                arquivos = st.file_uploader(
                    "Arquivos anexos",
                    accept_multiple_files=True,
                    type=["jpg", "png", "pdf", "jpeg", "webp", "docx"],
                    key=f"upload_rede_{rede_doc['_id']}"
                )

                # Lista de nomes ------------------------------------------------------------
                pessoas_opcoes = sorted({
                    p.get("nome_completo")
                    for p in pessoas.find()
                    if p.get("nome_completo")
                })

                pessoas_dict = {
                    p.get("nome_completo"): p.get("e_mail")
                    for p in pessoas.find()
                    if p.get("nome_completo")
                }

                ponto_focal_str = rede_doc.get("ponto_focal", "")
                ponto_focal_list = [p.strip() for p in ponto_focal_str.split(",")] if ponto_focal_str else []

                default_destinatarios = [p for p in ponto_focal_list if p in pessoas_opcoes]

                destinatarios_sel = st.multiselect(
                    "Notificar pessoas por e-mail",
                    options=pessoas_opcoes,
                    default=default_destinatarios,
                    disabled=usuario_visitante,
                    placeholder=""
                )

                # Controle de execução única
                flag_upload_key = f"upload_executado_{rede_doc['_id']}"

                if flag_upload_key not in st.session_state:
                    st.session_state[flag_upload_key] = False

                # BOTÃO DO FORM
                submitted = st.form_submit_button(
                    "Adicionar acompanhamento",
                    icon=":material/add_notes:",
                    disabled=usuario_visitante,
                )

                if submitted:

                    if novo_texto.strip():

                        with st.spinner("Salvando..."):

                            anexos_upload = []

                            if arquivos and not st.session_state[flag_upload_key]:

                                st.session_state[flag_upload_key] = True

                                servico = obter_servico_drive()

                                pasta_rede = obter_pasta_rede(
                                    servico,
                                    rede_doc["_id"],
                                    rede_doc.get("rede_articulacao", "")
                                )

                                for arq in arquivos:
                                    id_drive = enviar_arquivo_drive(
                                        servico,
                                        pasta_rede,
                                        arq
                                    )

                                    if id_drive:
                                        anexos_upload.append({
                                            "nome_anexo_rede": arq.name,
                                            "url_anexo_rede": gerar_link_drive(id_drive)
                                        })

                            nova_entry = {
                                "data_anotacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "autor_anotacao": usuario_logado,
                                "anotacao": novo_texto.strip(),
                                "anexos": anexos_upload
                            }

                            redes.update_one(
                                {"_id": rede_doc["_id"]},
                                {"$push": {"anotacoes": nova_entry}}
                            )

                            st.session_state[flag_upload_key] = False

                        st.success("Acompanhamento salvo com sucesso.")
                        time.sleep(3)
                        st.rerun(scope="fragment")

                    else:
                        st.warning("O campo do acompanhamento não pode estar vazio.")

        # # ---------------- EXPANDER PARA ADICIONAR ANOTAÇÃO ----------------
        # with st.expander("Adicionar novo acompanhamento", expanded=False, icon=":material/add_notes:"):
        #     nova_data = datetime.now().date()
            
        #     # Campo de texto ------------------------------------------------------------
        #     novo_texto = st.text_area("Texto do acompanhamento", key="nova_anotacao", height="content", disabled=usuario_visitante)

        #     # Upload de arquivos ------------------------------------------------------------

        #     arquivos = st.file_uploader(
        #         "Arquivos anexos",
        #         accept_multiple_files=True,
        #         type=["jpg", "png", "pdf", "jpeg", "webp", "docx"],
        #         key=f"upload_rede_{rede_doc['_id']}"
        #     )

        #     # Lista de nomes ------------------------------------------------------------
        #     pessoas_opcoes = sorted({
        #         p.get("nome_completo")
        #         for p in pessoas.find()
        #         if p.get("nome_completo")
        #     })

        #     # Dicionário nome -> email
        #     pessoas_dict = {
        #         p.get("nome_completo"): p.get("e_mail")
        #         for p in pessoas.find()
        #         if p.get("nome_completo")
        #     }

        #     # Recupera os pontos focais da rede
        #     ponto_focal_str = rede_doc.get("ponto_focal", "")
        #     ponto_focal_list = [p.strip() for p in ponto_focal_str.split(",")] if ponto_focal_str else []

        #     # Garante que só entram valores válidos (existentes nas opções)
        #     default_destinatarios = [p for p in ponto_focal_list if p in pessoas_opcoes]

        #     destinatarios_sel = st.multiselect(
        #         "Notificar pessoas por e-mail",
        #         options=pessoas_opcoes,
        #         default=default_destinatarios, 
        #         disabled=usuario_visitante,
        #         placeholder=""
        #     )



        #     flag_upload_key = f"upload_executado_{rede_doc['_id']}"

        #     if flag_upload_key not in st.session_state:
        #         st.session_state[flag_upload_key] = False



        #     if st.button("Adicionar acompanhamento", 
        #                     key="btn_add_anotacao", 
        #                     icon=":material/add_notes:", 
        #                     disabled=usuario_visitante,
        #                     type="primary"
        #                     ):

        #         if novo_texto.strip():

        #             with st.spinner("Salvando..."):

        #                 anexos_upload = []

        #                 # Executa apenas uma vez por clique
        #                 if arquivos and not st.session_state[flag_upload_key]:

        #                     # Marca antes para evitar duplicação
        #                     st.session_state[flag_upload_key] = True

        #                     servico = obter_servico_drive()

        #                     pasta_rede = obter_pasta_rede(
        #                         servico,
        #                         rede_doc["_id"],
        #                         rede_doc.get("rede_articulacao", "")
        #                     )

        #                     for arq in arquivos:
        #                         id_drive = enviar_arquivo_drive(
        #                             servico,
        #                             pasta_rede,
        #                             arq
        #                         )

        #                         if id_drive:
        #                             anexos_upload.append({
        #                                 "nome_anexo_rede": arq.name,
        #                                 "url_anexo_rede": gerar_link_drive(id_drive)
        #                             })



        #                 # Monta entrada com anexos
        #                 nova_entry = {
        #                     "data_anotacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
        #                     "autor_anotacao": usuario_logado,
        #                     "anotacao": novo_texto.strip(),
        #                     "anexos": anexos_upload
        #                 }

        #                 redes.update_one(
        #                     {"_id": rede_doc["_id"]},
        #                     {"$push": {"anotacoes": nova_entry}}
        #                 )

        #                 # Reset da flag para próxima operação
        #                 st.session_state[flag_upload_key] = False

        #             st.success("Acompanhamento salvo com sucesso.")
        #             time.sleep(3)
        #             st.rerun(scope="fragment")

        #         else:
        #             st.warning("O campo do acompanhamento não pode estar vazio.")

        st.write("")
        st.write("**Acompanhamentos registrados:**")

        # ---------------- LISTA DE Acompanhamento / Memória ----------------
        # Ordena por data (decrescente)
        anotacoes_ordenadas = []
        for idx, a in enumerate(anotacoes):
            data_str = a.get("data_anotacao", "")
            data_dt = datetime.min
            if data_str:
                try:
                    data_dt = datetime.strptime(data_str.split()[0], "%d/%m/%Y")
                except:
                    pass
            anotacoes_ordenadas.append((idx, data_dt, a))

        anotacoes_ordenadas.sort(key=lambda x: x[1], reverse=True)

        # ---------------- RENDERIZA CADA ANOTAÇÃO ----------------
        for original_idx, _, anotacao in anotacoes_ordenadas:
            container_key = f"anotacao_{rede_doc['_id']}_{original_idx}"
            toggle_key = f"toggle_edicao_{container_key}"
            delete_key = f"delete_confirm_{container_key}"

            with st.container(border=True):
                # Só mostra o toggle "Editar" se for autor OU admin
                pode_editar = (
                    anotacao.get("autor_anotacao") == usuario_logado
                )


                if pode_editar:
                    modo_edicao = st.toggle("Editar", key=toggle_key, value=False)
                else:
                    modo_edicao = False  # força visualização para outros usuários

                if modo_edicao:
                    # Data (apenas exibe já formatada)
                    data_valor = anotacao.get("data_anotacao", "")
                    data_formatada = data_valor.split()[0] if data_valor else datetime.now().strftime("%d/%m/%Y")

                    st.write(f"**Data:** {data_formatada}")
                    st.write(f"**Autor:** {anotacao.get('autor_anotacao', '')}")

                    novo_texto = st.text_area(
                        "Texto do acompanhamento",
                        value=anotacao.get("anotacao", ""),
                        key=f"texto_{container_key}", height="content"
                    )

                    botoes = st.container(horizontal=True)

                    if botoes.button("Salvar alterações", key=f"salvar_{container_key}", icon=":material/save:", type="primary"):
                        anotacoes[original_idx]["anotacao"] = novo_texto.strip()
                        redes.update_one(
                            {"_id": rede_doc["_id"]},
                            {"$set": {"anotacoes": anotacoes}}
                        )
                        st.success("Acompanhamento atualizado.")
                        time.sleep(2)
                        st.rerun(scope="fragment")

                    if botoes.button("Deletar acompanhamento", key=f"deletar_{container_key}", icon=":material/delete:"):
                        st.session_state[delete_key] = True

                    if st.session_state.get(delete_key, False):
                        st.warning("Tem certeza que deseja apagar este acompanhamento?")

                        botoes_confirmacao = st.container(horizontal=True)

                        if botoes_confirmacao.button("Sim", key=f"confirmar_delete_{container_key}", icon=":material/check:"):
                            anotacoes.pop(original_idx)
                            redes.update_one(
                                {"_id": rede_doc["_id"]},
                                {"$set": {"anotacoes": anotacoes}}
                            )
                            st.success("Acompanhamento apagado com sucesso.")
                            time.sleep(2)
                            st.rerun(scope="fragment")
                            st.session_state[delete_key] = False

                        if botoes_confirmacao.button("Não", key=f"cancelar_delete_{container_key}", icon=":material/close:"):
                            st.session_state[delete_key] = False

                else:
                    # Modo visualização
                    data_str = anotacao.get("data_anotacao", "")
                    if data_str:
                        data_str = data_str.split()[0]
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.write(f"**Data:** {data_str}")
                    with col2:
                        st.write(f"**Autor:** {anotacao.get('autor_anotacao', '')}")
                    st.write(anotacao.get("anotacao", ""))

                    # Renderização dos anexos vinculados ao acompanhamento
                    anexos = anotacao.get("anexos", [])

                    if anexos:
                        st.write("**Anexos:**")

                        for anexo in anexos:
                            url = anexo.get("url_anexo_rede")

                            if url:
                                nome = anexo.get("nome_anexo_rede", "Abrir anexo")
                                st.markdown(f"- [{nome}]({url})")


@st.dialog("Cadastrar rede", width="large") 
def cadastro_rede():
    
    # =====================
    # Opções dinâmicas do banco
    # =====================
    prioridades_opcoes = sorted({r.get("prioridade") for r in redes.find() if r.get("prioridade")})
    dedicacao_opcoes = sorted({r.get("dedicacao") for r in redes.find() if r.get("dedicacao")})

    temas_opcoes = sorted({
        t.strip()
        for r in redes.find()
        if r.get("tema")
        for t in re.split(r",|;", r.get("tema"))
        if t.strip()
    })

    pessoas_opcoes = sorted({p.get("nome_completo") for p in pessoas.find() if p.get("nome_completo")})

    
    
    # =====================
    # Formulário de cadastro
    # =====================
    # Chave própria: "form_novo_registro" já é usada no formulário da aba "Novo registro"
    with st.form("form_cadastro_rede", border=False):

        rede_edit = st.text_input("Rede/Articulação*")

        descricao_edit = st.text_area("Descrição da rede*")

        col1, col2 = st.columns(2)
        ponto_focal_edit = col1.multiselect("Ponto Focal*", options=pessoas_opcoes, placeholder="")
        temas_selecionados = col2.multiselect("Temas*", options=temas_opcoes, placeholder="")

        col1, col2, col3 = st.columns(3)

        tipo_rede_edit = col1.selectbox(
            "Tipo de Rede*",
            options=tipos_rede_opcoes,
            index=None, 
            placeholder=""
        )

        abrangencia_cadastro = col2.selectbox(
            "Abrangência",
            options=tipos_abrangencia,
            index=None, 
            placeholder=""
        )

        status_cadastro = col3.selectbox(
            "Status*",
            options=status_opcoes,
            index=None, 
            placeholder=""
        )

        col1, col2, col3 = st.columns(3)
        prioridade_edit = col1.selectbox("Grau de Prioridade*", options=prioridades_opcoes, index=None, placeholder="")
        dedicacao_edit = col2.selectbox("Dedicação*", options=dedicacao_opcoes, index=None, placeholder="")
        programa_edit = col3.selectbox("Programa*", options=programas_opcoes, index=None, placeholder="")

        st.write("")

        # =====================
        # Botão salvar (submit do form)
        # =====================
        enviado = st.form_submit_button(
            "Adicionar rede",
            width=200,
            icon=":material/check:",
            type="primary",
        )

    # =====================
    # Envio
    # =====================
    if enviado:

        # -----------------
        # Validação obrigatórios
        # -----------------
        campos_obrigatorios = [
            ("Rede/Articulação", rede_edit.strip()),
            ("Descrição da rede", descricao_edit.strip()),
            ("Ponto Focal", ponto_focal_edit),
            ("Tipo de Rede", tipo_rede_edit),
            ("Status", status_cadastro),
            ("Temas", temas_selecionados),
            ("Grau de Prioridade", prioridade_edit.strip() if prioridade_edit else ""),
            ("Dedicação", dedicacao_edit.strip() if dedicacao_edit else ""),
            ("Programa", programa_edit.strip() if programa_edit else ""),
        ]

        faltando = [nome for nome, valor in campos_obrigatorios if not valor]

        # -----------------
        # Verificação duplicidade
        # -----------------
        existe = None
        if not faltando:
            existe = redes.find_one({
                "rede_articulacao": {
                    "$regex": f"^{re.escape(rede_edit.strip())}$",
                    "$options": "i"
                }
            })

        if faltando:
            st.warning(f"Preencha todos os campos obrigatórios: {', '.join(faltando)}")

        elif existe:
            st.error("Já existe uma rede cadastrada com esse nome.")

        else:
            # -----------------
            # Monta documento
            # -----------------
            nova_rede = {
                "rede_articulacao": rede_edit.strip(),
                "descricao": descricao_edit.strip(),
                "ponto_focal": ", ".join(ponto_focal_edit),
                "tema": ", ".join(temas_selecionados),
                "prioridade": prioridade_edit,
                "dedicacao": dedicacao_edit,
                "programa": programa_edit,
                "status": status_cadastro,
                "tipo_rede": tipo_rede_edit,
                "abrangencia": abrangencia_cadastro,
                "anotacoes": [],
            }

            # -----------------
            # Inserção no banco
            # -----------------
            redes.insert_one(nova_rede)

            st.success("Rede cadastrada com sucesso!")
            time.sleep(2)
            st.rerun()


def enviar_email_acompanhamento(destinatario: str, nome_destinatario: str, rede_nome: str, descricao: str, texto: str, autor: str) -> bool:
    """
    Envia e-mail notificando um novo acompanhamento de rede.

    Parâmetros:
    - destinatario: email da pessoa
    - nome_destinatario: nome da pessoa
    - rede_nome: nome da rede
    - descricao: descrição da rede
    - texto: texto do acompanhamento
    - autor: quem registrou

    Retorna:
    - True se sucesso, False caso erro
    """

    remetente = st.secrets["senhas"]["endereco_email"]
    senha = st.secrets["senhas"]["senha_email"]

    assunto = f"Novo acompanhamento - Redes/Articulações Jataí - {rede_nome}"

    corpo = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial; font-size: 15px; color: #333; padding: 20px;">

        <div style="text-align:center;">
            <img src="https://ispn.org.br/wp-content/uploads/2024/10/logo_ISPN_vertical_ass.png"
                 style="max-width:120px;">
            <h3>Novo acompanhamento registrado</h3>
        </div>

        <p>Um novo acompanhamento foi registrado na rede abaixo:</p>

        <p><strong>Rede:</strong> {rede_nome}</p>
        <p><strong>Descrição:</strong> {descricao}</p>

        <hr>

        <p><strong>Acompanhamento:</strong></p>
        <p>{texto}</p>

        <hr>

        <p><strong>Registrado por:</strong> {autor}</p>

        <br>
        <p>Att.<br>ISPN</p>

    </body>
    </html>
    """

    msg = MIMEText(corpo, "html", "utf-8")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, destinatario, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_opcoes_territorio() -> list[str]:
    """
    Monta a lista de opções 'Município - UF' a partir da coleção ufs_municipios.
    O código da UF corresponde aos 2 primeiros dígitos do código IBGE do município.
    """
    doc_ufs = ufs_municipios.find_one({"ufs": {"$exists": True}}) or {}
    doc_munis = ufs_municipios.find_one({"municipios": {"$exists": True}}) or {}

    # codigo_uf -> sigla_uf
    mapa_ufs = {
        int(uf["codigo_uf"]): uf["sigla_uf"]
        for uf in doc_ufs.get("ufs", [])
        if uf.get("codigo_uf") and uf.get("sigla_uf")
    }

    opcoes = []
    for muni in doc_munis.get("municipios", []):
        nome = muni.get("nome_municipio")
        codigo = muni.get("codigo_municipio")
        if not nome or not codigo:
            continue

        sigla = mapa_ufs.get(int(str(codigo)[:2]))
        if sigla:
            opcoes.append(f"{nome} - {sigla}")

    return sorted(set(opcoes), key=_chave_ordenacao)


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_opcoes_ufs() -> dict[str, str]:
    """Retorna {sigla_uf: nome_uf}, ordenado pelo nome do estado."""
    doc = ufs_municipios.find_one({"ufs": {"$exists": True}}) or {}
    ufs = {
        uf["sigla_uf"]: uf["nome_uf"]
        for uf in doc.get("ufs", [])
        if uf.get("sigla_uf") and uf.get("nome_uf")
    }
    return dict(sorted(ufs.items(), key=lambda item: _chave_ordenacao(item[1])))


def _para_date(valor):
    """'dd/mm/aaaa' -> date (ou None)."""
    try:
        return datetime.strptime(valor, "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None


def _valor_periodo(inicio_str, fim_str):
    """Converte as datas salvas no valor inicial do date_input de intervalo."""
    inicio = _para_date(inicio_str)
    fim = _para_date(fim_str)
    if not inicio:
        return ()
    if fim and fim != inicio:
        return (inicio, fim)
    return (inicio,)


def _normalizar_periodo(valor):
    """
    date_input de intervalo -> (inicio, fim).
    Se só um dia foi escolhido, fim = inicio. Sem seleção -> (None, None).
    """
    if not valor:
        return None, None
    if isinstance(valor, (tuple, list)):
        if len(valor) == 0:
            return None, None
        inicio = valor[0]
        fim = valor[1] if len(valor) > 1 else valor[0]
        return inicio, fim
    return valor, valor  # segurança, caso venha uma data simples


def _indice_abrangencia(valor):
    """Posição da abrangência salva ('Nacional') nas opções longas do radio."""
    if not valor:
        return None
    for i, opcao in enumerate(OPCOES_ABRANGENCIA):
        if opcao.startswith(valor):
            return i
    return None


def campos_formulario_registro(eh_incidencia: bool, prefixo: str, valores: dict | None = None,
                               desabilitado: bool = False) -> dict:
    """
    Desenha os campos do registro (usar DENTRO de um st.form) e devolve um dict com os valores.
    - prefixo: diferencia as chaves dos widgets (novo registro x edição)
    - valores: documento do Mongo para pré-preencher os campos (edição)
    """
    v = valores or {}

    mapa_ufs = carregar_opcoes_ufs()
    mapa_programas = carregar_opcoes_programas()
    opcoes_territorio = carregar_opcoes_territorio()

    # Municípios já salvos que não estão na lista oficial (ex.: importados) continuam como opção
    territorio_salvo = list(v.get("territorio") or [])
    conjunto_oficial = set(opcoes_territorio)
    opcoes_municipios = opcoes_territorio + [t for t in territorio_salvo if t not in conjunto_oficial]

    # =================================================================
    # 1. INFORMAÇÕES GERAIS
    # =================================================================
    col1, col2 = st.columns(2)

    col1.text_input(
        "Nome",
        value=v.get("nome") or st.session_state.get("nome", ""),
        disabled=True,
        key=f"{prefixo}_nome",
    )

    data_atividade = col2.date_input(
        "Data ou período em que a atividade ocorreu*",
        value=_valor_periodo(v.get("data_atividade"), v.get("data_atividade_fim")),
        max_value=datetime.now().date(),
        format="DD/MM/YYYY",
        key=f"{prefixo}_data",
        disabled=desabilitado,
        help="Para um único dia, clique só na data. Para um período, clique na data inicial e depois na final.",
    )

    st.write("")

    col1, col2 = st.columns(2)

    abrangencia = col1.radio(
        "Abrangência / Escopo do Espaço*",
        options=OPCOES_ABRANGENCIA,
        index=_indice_abrangencia(v.get("abrangencia")),
        key=f"{prefixo}_abrangencia",
        disabled=desabilitado,
    )

    ufs = col2.multiselect(
        "Estado(s) (UF) onde a ação se localiza fisicamente ou politicamente",
        options=list(mapa_ufs.keys()),
        format_func=lambda sigla: f"{mapa_ufs.get(sigla, sigla)} - {sigla}",
        default=[u for u in (v.get("ufs") or []) if u in mapa_ufs],
        placeholder="Digite para buscar o estado",
        key=f"{prefixo}_ufs",
        disabled=desabilitado,
    )

    territorio = col2.multiselect(
        "Município(s) onde a ação se localiza fisicamente ou politicamente",
        options=opcoes_municipios,
        default=territorio_salvo,
        placeholder="Digite para buscar o município",
        key=f"{prefixo}_territorio",
        disabled=desabilitado,
        help="Se for de âmbito Nacional/Federal, pode preencher como Brasília - DF.",
    )

    st.divider()

    resultado = {
        "data_atividade": data_atividade,
        "abrangencia": abrangencia,
        "ufs": ufs,
        "territorio": territorio,
    }

    # =================================================================
    # 2. DETALHAMENTO - INCIDÊNCIA POLÍTICA
    # =================================================================
    if eh_incidencia:
        st.subheader("2. Detalhamento - Incidência política")
        st.write("")

        col1, col2 = st.columns(2)

        orgao_incidencia = col1.text_input(
            "Órgão / Instituição / Espaço de Incidência*",
            value=v.get("orgao_incidencia", ""),
            key=f"{prefixo}_inc_orgao",
            disabled=desabilitado,
            help="Nome específico do espaço (ex: Ministério do Meio Ambiente - MMA, Secretaria de Estado de Meio Ambiente e Recursos Naturais do Maranhão, Núcleo Agrário, etc.).",
        )

        ator_impactado = col2.text_input(
            "Ator / Autoridade Impactada*",
            value=v.get("ator_impactado", ""),
            key=f"{prefixo}_inc_ator",
            disabled=desabilitado,
            help="Indique o tomador de decisão, autoridade ou ator político central que foi o foco dessa ação de incidência.",
        )

        programas_salvos = [str(p) for p in (v.get("programas") or [])]
        programas_ids = st.multiselect(
            "Programa(s) do ISPN relacionado(s)*",
            options=list(mapa_programas.keys()),
            format_func=lambda pid: mapa_programas.get(pid, pid),
            default=[p for p in programas_salvos if p in mapa_programas],
            placeholder="",
            key=f"{prefixo}_inc_programas",
            disabled=desabilitado,
        )

        pauta_objetivo = st.text_area(
            "Pauta / Objetivo*",
            value=v.get("pauta_objetivo", ""),
            key=f"{prefixo}_inc_pauta",
            disabled=desabilitado,
        )

        encaminhamentos = st.text_area(
            "Encaminhamentos",
            value=v.get("encaminhamentos", ""),
            key=f"{prefixo}_inc_encaminhamentos",
            disabled=desabilitado,
        )

        envolveu_salvo = v.get("envolveu_outras_organizacoes")
        envolveu_organizacoes = st.radio(
            "Essa incidência envolveu outras organizações?*",
            options=["Sim", "Não"],
            index=None if envolveu_salvo is None else (0 if envolveu_salvo else 1),
            horizontal=True,
            key=f"{prefixo}_inc_envolveu_orgs",
            disabled=desabilitado,
        )

        organizacoes_envolvidas = st.text_area(
            "Quais organizações estiveram envolvidas?",
            value=v.get("organizacoes_envolvidas", ""),
            key=f"{prefixo}_inc_orgs",
            disabled=desabilitado,
        )

        resultado.update({
            "orgao_incidencia": orgao_incidencia,
            "ator_impactado": ator_impactado,
            "programas_ids": programas_ids,
            "pauta_objetivo": pauta_objetivo,
            "encaminhamentos": encaminhamentos,
            "envolveu_organizacoes": envolveu_organizacoes,
            "organizacoes_envolvidas": organizacoes_envolvidas,
        })

    # =================================================================
    # 2. DETALHAMENTO - ARTICULAÇÃO / REDES
    # =================================================================
    else:
        st.subheader("2. Detalhamento - Articulação / Redes")
        st.write("")

        rede_referente = st.text_input(
            "A qual rede/articulação se refere?*",
            value=v.get("rede_articulacao", ""),
            key=f"{prefixo}_art_rede",
            disabled=desabilitado,
        )

        pauta_objetivo = st.text_area(
            "Pauta / Objetivo*",
            value=v.get("pauta_objetivo", ""),
            key=f"{prefixo}_art_pauta",
            disabled=desabilitado,
        )

        encaminhamentos = st.text_area(
            "Encaminhamentos",
            value=v.get("encaminhamentos", ""),
            key=f"{prefixo}_art_encaminhamentos",
            disabled=desabilitado,
        )

        resultado.update({
            "rede_articulacao": rede_referente,
            "pauta_objetivo": pauta_objetivo,
            "encaminhamentos": encaminhamentos,
        })

    return resultado


def montar_dados_registro(valores: dict, tipo_registro: str, nome: str):
    """Converte os valores do formulário em (dados_gerais, dados_detalhe, obrigatorios)."""
    inicio, fim = _normalizar_periodo(valores["data_atividade"])

    dados_gerais = {
        "nome": nome,
        "data_atividade": inicio.strftime("%d/%m/%Y") if inicio else None,
        "data_atividade_fim": fim.strftime("%d/%m/%Y") if fim else None,
        "abrangencia": valores["abrangencia"].split(" (")[0] if valores["abrangencia"] else None,
        "ufs": valores["ufs"],
        "territorio": valores["territorio"],
        "tipo_registro": tipo_registro,
    }
    # ... resto igual

    if tipo_registro == TIPO_INCIDENCIA:
        obrigatorios = [
            ("Órgão / Instituição / Espaço de Incidência", valores["orgao_incidencia"].strip()),
            ("Ator / Autoridade Impactada", valores["ator_impactado"].strip()),
            ("Programa(s) do ISPN relacionado(s)", valores["programas_ids"]),
            ("Pauta / Objetivo", valores["pauta_objetivo"].strip()),
            ("Essa incidência envolveu outras organizações?", valores["envolveu_organizacoes"]),
        ]
        dados_detalhe = {
            "orgao_incidencia": valores["orgao_incidencia"].strip(),
            "ator_impactado": valores["ator_impactado"].strip(),
            "programas": [ObjectId(pid) for pid in valores["programas_ids"]],
            "pauta_objetivo": valores["pauta_objetivo"].strip(),
            "encaminhamentos": valores["encaminhamentos"].strip(),
            "envolveu_outras_organizacoes": valores["envolveu_organizacoes"] == "Sim",
            "organizacoes_envolvidas": valores["organizacoes_envolvidas"].strip(),
        }
    else:
        obrigatorios = [
            ("A qual rede/articulação se refere?", valores["rede_articulacao"].strip()),
            ("Pauta / Objetivo", valores["pauta_objetivo"].strip()),
        ]
        dados_detalhe = {
            "rede_articulacao": valores["rede_articulacao"].strip(),
            "pauta_objetivo": valores["pauta_objetivo"].strip(),
            "encaminhamentos": valores["encaminhamentos"].strip(),
        }

    return dados_gerais, dados_detalhe, obrigatorios


def pode_editar_registro(reg) -> bool:
    """Só quem fez o registro e usuários admin podem editar. Visitantes nunca."""
    if usuario_visitante:
        return False

    eh_admin = "admin" in st.session_state.get("tipo_usuario", [])
    eh_autor = reg.get("nome") == st.session_state.get("nome")

    return eh_admin or eh_autor


@st.dialog("Editar registro", width="large")
def editar_registro(id_reg: str):
    doc = registros_incidencia.find_one({"_id": ObjectId(id_reg)})
    if not doc:
        st.error("Registro não encontrado.")
        return

    prefixo = f"edit_reg_{id_reg}"

    # Tipo fora do form: ao trocar, os campos do detalhamento mudam na hora
    tipo_registro = st.selectbox(
        "Tipo de registro*",
        options=OPCOES_TIPO_REGISTRO,
        index=OPCOES_TIPO_REGISTRO.index(doc["tipo_registro"]) if doc.get("tipo_registro") in OPCOES_TIPO_REGISTRO else 0,
        key=f"{prefixo}_tipo",
        help=HELP_TIPO_REGISTRO,
        width=250,
    )
    eh_incidencia = tipo_registro == TIPO_INCIDENCIA

    with st.form(f"form_{prefixo}", border=False):
        valores = campos_formulario_registro(eh_incidencia, prefixo, valores=doc)
        st.write("")
        salvar = st.form_submit_button(
            "Salvar alterações",
            icon=":material/check:",
            type="primary",
            width=200,
        )

    if salvar:
        dados_gerais, dados_detalhe, obrigatorios = montar_dados_registro(
            valores, tipo_registro, nome=doc.get("nome", "")
        )

        faltando = validar_informacoes_gerais(dados_gerais)
        faltando += [nome for nome, valor in obrigatorios if not valor]
        if faltando:
            st.warning(f"Preencha todos os campos obrigatórios: {', '.join(faltando)}")
            return

        dados_gerais.pop("nome")  # quem registrou não muda na edição

        # Se o tipo mudou, remove os campos que só existem no outro tipo
        campos_outro_tipo = CAMPOS_ARTICULACAO if eh_incidencia else CAMPOS_INCIDENCIA

        registros_incidencia.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    **dados_gerais,
                    **dados_detalhe,
                    "data_ultima_edicao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "editado_por": st.session_state.get("nome", ""),
                },
                "$unset": {campo: "" for campo in campos_outro_tipo},
            },
        )

        st.success("Registro atualizado com sucesso!")
        time.sleep(2)
        st.rerun()


def salvar_registro(dados_gerais: dict, dados_detalhe: dict, obrigatorios_detalhe: list, mensagem_sucesso: str):
    """
    Valida as seções 1 e 2, grava o registro em registros_incidencia_politica
    e limpa o formulário.
    """
    faltando = validar_informacoes_gerais(dados_gerais)
    faltando += [nome for nome, valor in obrigatorios_detalhe if not valor]

    if faltando:
        st.warning(f"Preencha todos os campos obrigatórios: {', '.join(faltando)}")
        st.stop()

    novo_registro = {
        **dados_gerais,
        **dados_detalhe,
        "data_registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }

    registros_incidencia.insert_one(novo_registro)

    st.success(mensagem_sucesso)
    time.sleep(2)

    st.rerun()


def validar_informacoes_gerais(dados_gerais: dict) -> list[str]:
    """Retorna os campos obrigatórios da seção 1 que não foram preenchidos."""
    obrigatorios = [
        ("Data em que a atividade ocorreu", dados_gerais.get("data_atividade")),
        ("Abrangência / Escopo do Espaço", dados_gerais.get("abrangencia")),
        ("Tipo de registro", dados_gerais.get("tipo_registro")),
    ]
    return [nome for nome, valor in obrigatorios if not valor]


def carregar_registros() -> pd.DataFrame:
    """
    Lê a coleção registros_incidencia_politica e devolve um DataFrame pronto para
    filtrar e exibir. Programas são traduzidos de _id para nome. Território,
    UFs e programas ficam como listas, para os filtros funcionarem por item.
    """
    docs = list(registros_incidencia.find())
    if not docs:
        return pd.DataFrame()

    mapa_programas = carregar_opcoes_programas()  # {id (str): nome}

    linhas = []
    for d in docs:
        territorio = d.get("territorio") or []
        if isinstance(territorio, str):
            territorio = [territorio]
            
        ufs_registro = list(d.get("ufs") or [])

        programas = [
            mapa_programas.get(str(pid), "Programa removido")
            for pid in (d.get("programas") or [])
        ]

        envolveu = d.get("envolveu_outras_organizacoes")
        envolveu_txt = "" if envolveu is None else ("Sim" if envolveu else "Não")

        linhas.append({
            "_id": d["_id"],
            "data": pd.to_datetime(d.get("data_atividade"), format="%d/%m/%Y", errors="coerce"),
            "data_fim": pd.to_datetime(
                d.get("data_atividade_fim") or d.get("data_atividade"),
                format="%d/%m/%Y", errors="coerce",
            ),
            "tipo_registro": d.get("tipo_registro", ""),
            "nome": d.get("nome", ""),
            "abrangencia": d.get("abrangencia", ""),
            "territorio": territorio,
            "ufs": sorted({t.rsplit(" - ", 1)[-1] for t in territorio if " - " in t}),
            "programas": programas,
            "orgao_incidencia": d.get("orgao_incidencia", ""),
            "ator_impactado": d.get("ator_impactado", ""),
            "rede_articulacao": d.get("rede_articulacao", ""),
            "pauta_objetivo": d.get("pauta_objetivo", ""),
            "encaminhamentos": d.get("encaminhamentos", ""),
            "envolveu_outras_organizacoes": envolveu_txt,
            "organizacoes_envolvidas": d.get("organizacoes_envolvidas", ""),
            "data_registro": d.get("data_registro", ""),
            "ufs_registro": ufs_registro,
            "ufs": sorted(set(ufs_registro) | {t.rsplit(" - ", 1)[-1] for t in territorio if " - " in t}),
        })

    return pd.DataFrame(linhas)


def _opcoes_de_listas(serie: pd.Series) -> list[str]:
    """Valores únicos de uma coluna de listas, em ordem alfabética sem acento."""
    valores = {v for lista in serie for v in lista if v}
    return sorted(valores, key=_chave_ordenacao)


def _titulo_registro(reg) -> str:
    """Título do card: órgão (incidência) ou rede (articulação)."""
    if reg["tipo_registro"] == "Incidência política":
        return reg.get("orgao_incidencia") or "Incidência política"
    return reg.get("rede_articulacao") or "Articulação"


def _data_formatada(valor) -> str:
    return valor.strftime("%d/%m/%Y") if pd.notna(valor) else "—"


def _periodo_formatado(reg) -> str:
    """'dd/mm/aaaa' para um dia só, 'dd/mm/aaaa a dd/mm/aaaa' para período."""
    inicio, fim = reg.get("data"), reg.get("data_fim")
    if pd.isna(inicio):
        return "—"
    if pd.isna(fim) or fim == inicio:
        return _data_formatada(inicio)
    return f"{_data_formatada(inicio)} a {_data_formatada(fim)}"


def _resumo(texto: str, limite: int = 160) -> str:
    texto = (texto or "").strip()
    return texto if len(texto) <= limite else texto[:limite].rsplit(" ", 1)[0] + "…"


def _selecionar_card(id_reg: str):
    """
    Callback do botão de info de cada card.
    Clicar abre o registro no painel de detalhes; clicar de novo no mesmo card fecha.
    """
    if st.session_state.get("registro_selecionado") == id_reg:
        st.session_state["registro_selecionado"] = None
    else:
        st.session_state["registro_selecionado"] = id_reg


def mostrar_card_registro(reg):
    """Card com as informações básicas de um registro."""
    id_reg = str(reg["_id"])
    selecionado = st.session_state.get("registro_selecionado") == id_reg

    with st.container(border=True):

        col_titulo, col_btn = st.columns([5, 1], vertical_alignment="top")

        with col_titulo:
            cor = "blue" if reg["tipo_registro"] == "Incidência política" else "orange"
            st.badge(reg["tipo_registro"], color=cor)
            st.markdown(f"**{_titulo_registro(reg)}**")

        with col_btn:
            with st.container(horizontal=True, horizontal_alignment="right"):
                st.button(
                    "",
                    icon=":material/info:",
                    type="tertiary",
                    key=f"btn_card_{id_reg}",
                    on_click=_selecionar_card,
                    args=(id_reg,),
                    help="Fechar detalhes" if selecionado else "Ver detalhes",
                )

        local = ", ".join(reg["territorio"]) or ", ".join(reg["ufs_registro"]) or "—"
        st.caption(
            f":material/calendar_today: {_periodo_formatado(reg)} · "
            f":material/location_on: {local}"
        )
        st.write(_resumo(reg.get("pauta_objetivo", "")))
        st.caption(f":material/person: {reg.get('nome', '')}")


def mostrar_detalhes_registro(reg):
    """Painel com todas as informações de um registro."""
    eh_incidencia = reg["tipo_registro"] == TIPO_INCIDENCIA
    mapa_ufs = carregar_opcoes_ufs()

    # Cabeçalho: badge à esquerda, botão de edição no canto superior direito
    col_badge, col_btn = st.columns([6, 1], vertical_alignment="top")
    col_badge.badge(reg["tipo_registro"], color="blue" if eh_incidencia else "orange")

    if pode_editar_registro(reg):
        with col_btn:
            with st.container(horizontal=True, horizontal_alignment="right"):
                if st.button(
                    "",
                    icon=":material/edit:",
                    type="tertiary",
                    key=f"btn_editar_{reg['_id']}",
                    help="Editar registro",
                ):
                    editar_registro(str(reg["_id"]))

    st.subheader(_titulo_registro(reg))
    st.write("")

    col1, col2 = st.columns(2)
    col1.write(f"**Data da atividade:** {_periodo_formatado(reg)}")
    col2.write(f"**Abrangência:** {reg.get('abrangencia') or '—'}")
    col1.write(f"**Registrado por:** {reg.get('nome') or '—'}")
    col2.write(f"**Registrado em:** {reg.get('data_registro') or '—'}")

    estados = [f"{mapa_ufs.get(s, s)} - {s}" for s in reg.get("ufs_registro") or []]
    st.write(f"**Estado(s):** {', '.join(estados) or '—'}")
    st.write(f"**Município(s):** {', '.join(reg['territorio']) or '—'}")

    st.divider()

    if eh_incidencia:
        col1, col2 = st.columns(2)
        col1.write(f"**Órgão / Instituição / Espaço:** {reg.get('orgao_incidencia') or '—'}")
        col2.write(f"**Ator / Autoridade impactada:** {reg.get('ator_impactado') or '—'}")
        st.write(f"**Programa(s) do ISPN:** {', '.join(reg['programas']) or '—'}")
    else:
        st.write(f"**Rede / Articulação:** {reg.get('rede_articulacao') or '—'}")

    st.write("")
    st.write("**Pauta / Objetivo:**")
    st.write(reg.get("pauta_objetivo") or "—")

    st.write("**Encaminhamentos:**")
    st.write(reg.get("encaminhamentos") or "—")

    if eh_incidencia:
        st.write("")
        st.write(f"**Envolveu outras organizações?** {reg.get('envolveu_outras_organizacoes') or '—'}")
        if reg.get("organizacoes_envolvidas"):
            st.write(f"**Organizações envolvidas:** {reg['organizacoes_envolvidas']}")


ORDEM_ABRANGENCIA = ["Nacional", "Estadual", "Municipal", "Internacional"]
CORES_ABRANGENCIA = ["#9ecae1", "#a8d8a8", "#fdd0a2", "#cbb8e3"]  # azul, verde, pêssego, lilás

ORDEM_TIPOS = ["Incidência política", "Articulação"]
CORES_TIPOS = ["#9ecae1", "#fdd0a2"]  # azul e pêssego, combinando com os badges dos cards

ALTURA_GRAFICOS = 240  # altura comum para pizzas e mapa

CONFIG_PLOTLY = {"displayModeBar": False}  # esconde a barra de ferramentas do plotly


def grafico_pizza(serie: pd.Series, categorias: list[str], cores: list[str]) -> go.Figure:
    """
    Gráfico de pizza com o percentual de cada categoria dentro das fatias
    e legenda à direita, centralizada verticalmente.
    A legenda mostra sempre todas as categorias (com cores fixas);
    fatias com 0 registros não são desenhadas.
    """
    # Inclui categorias inesperadas que existam nos dados, no fim da lista
    categorias = categorias + [c for c in serie.dropna().unique() if c and c not in categorias]
    cores = (cores + ["#d9d9d9"] * len(categorias))[:len(categorias)]

    contagem = serie.value_counts().reindex(categorias, fill_value=0)
    total = contagem.sum()

    # Fatias muito pequenas ficam sem rótulo (o valor continua no tooltip)
    rotulos = [
        f"{q / total:.1%}".replace(".", ",") if total and q / total >= 0.05 else ""
        for q in contagem.values
    ]

    fig = go.Figure(
        go.Pie(
            labels=categorias,
            values=contagem.values,
            marker=dict(colors=cores, line=dict(width=0)),   # sem borda entre as fatias
            sort=False,                 # mantém a ordem definida em categorias
            direction="clockwise",
            text=rotulos,
            textinfo="text",
            textposition="inside",
            insidetextfont=dict(color="black", size=12),
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Registros: %{value}<br>"
                "Percentual: %{percent:.1%}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        height=ALTURA_GRAFICOS,
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="v",
            x=1.02,
            y=0.5,
            yanchor="middle",
            font=dict(size=13),
        ),
    )

    return fig


######################################################################################################
# MAIN
######################################################################################################


# Verifica se o usuário é visitante
usuario_visitante = "visitante" in st.session_state.get("tipo_usuario", [])

st.header("Redes e Articulações")
st.write("")
st.write("")
st.write("")


aba_redes, aba_registros, aba_forms  = st.tabs([":material/network_node: Redes e Articulações", ":material/menu_book: Registros de Incidências e Articulações", ":material/add: Novo registro",])

with aba_redes:

    

    # Container horizontal de botões
    container_botoes = st.container(horizontal=True, horizontal_alignment="right")

    # Roteamento de tipo de usuário
    if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)"}:

        # Botão para abrir o diálogo de gerenciamento de colaboradores
        container_botoes.button("Cadastrar rede", on_click=cadastro_rede, icon=":material/network_node:", width=300)
        st.write('')


    # --- Carrega dados do MongoDB ---
    dados_redes = list(redes.find())

    df_redes = pd.DataFrame(dados_redes)
    df_redes = df_redes.rename(columns={
        "rede_articulacao": "Nome",
        "tipo_rede": "Tipo de Rede",
        "ponto_focal": "Ponto Focal",
        "prioridade": "Prioridade",
        "dedicacao": "Dedicação",
        "programa": "Programa",
        "status": "Status",
        "tema": "Tema"  
    })

    # Garante existência da coluna mesmo em documentos antigos
    if "Tipo de Rede" not in df_redes.columns:
        df_redes["Tipo de Rede"] = ""

    # Preenche valores nulos
    df_redes["Tipo de Rede"] = df_redes["Tipo de Rede"].fillna("")

    df_redes = df_redes[["Nome", "Tipo de Rede", "Ponto Focal", "Tema", "Prioridade", "Dedicação", "Programa", "Status"]]

    # --- Preparar listas únicas para filtros ---
    pontos_unicos = (
        df_redes["Ponto Focal"]
        .dropna()
        .astype(str)
        .str.split(",")
        .explode()
        .str.strip()
        .unique()
        .tolist()
    )

    programas_unicos = (
        df_redes["Programa"]
        .dropna()
        .astype(str)
        .str.split(",")
        .explode()
        .str.strip()
        .unique()
        .tolist()
    )

    temas_unicos = (
        df_redes["Tema"]
        .dropna()
        .astype(str)
        .str.split(",")
        .explode()
        .str.strip()
        .unique()
        .tolist()
    )

    status_unicos = df_redes["Status"].dropna().unique().tolist()
    if not status_unicos:
        status_unicos = ["Ativa", "Inativa"]  # fallback se não existir no banco

    # --- Filtros ---
    with st.expander("Filtros", expanded=False, icon=":material/filter_alt:"):
        colf1, colf2, colf3, colf4 = st.columns(4)
        
        rede_sel = colf1.multiselect(
            "Rede",
            options=sorted(df_redes["Nome"].dropna().unique().tolist()), placeholder=""
        )
        tipo_rede_sel = colf4.multiselect(
            "Tipo de Rede",
            options=["1", "2", "3"],
            placeholder=""
        )
        ponto_sel = colf2.multiselect(
            "Ponto Focal",
            options=sorted(pontos_unicos), placeholder=""
        )
        tema_sel = colf3.multiselect(  
            "Tema",
            options=sorted(temas_unicos), placeholder=""
        )
        
        colf1, colf2, colf3, colf4 = st.columns(4)

        prioridade_sel = colf1.multiselect(
            "Grau de Prioridade",
            options=["Estratégico", "Médio", "Baixo"], placeholder=""
        )
        dedicacao_sel = colf2.multiselect(
            "Dedicação",
            options=sorted(df_redes["Dedicação"].dropna().unique().tolist()), placeholder=""
        )
        programa_sel = colf3.multiselect(
            "Programa",
            options=sorted(programas_unicos), placeholder=""
        )
        status_sel = colf4.multiselect(
            "Status",
            options=sorted(status_unicos),
            default=["Ativa"], 
            placeholder=""
        )

    st.write("")

    # --- Aplica filtros ---
    df_filtrado = df_redes.copy()

    if rede_sel:
        df_filtrado = df_filtrado[df_filtrado["Nome"].isin(rede_sel)]

    if prioridade_sel:
        df_filtrado = df_filtrado[df_filtrado["Prioridade"].isin(prioridade_sel)]

    if dedicacao_sel:
        df_filtrado = df_filtrado[df_filtrado["Dedicação"].isin(dedicacao_sel)]

    if ponto_sel:
        df_filtrado = df_filtrado[
            df_filtrado["Ponto Focal"]
            .astype(str)
            .apply(lambda x: any(p in x for p in ponto_sel))
        ]

    if programa_sel:
        df_filtrado = df_filtrado[
            df_filtrado["Programa"]
            .astype(str)
            .apply(lambda x: any(p in x for p in programa_sel))
        ]

    if tema_sel:
        df_filtrado = df_filtrado[
            df_filtrado["Tema"]
            .astype(str)
            .apply(lambda x: any(t in x for t in tema_sel))
        ]

    # Filtro Status
    if status_sel:
        df_filtrado = df_filtrado[df_filtrado["Status"].isin(status_sel)]

    # Filtro tipo de rede 
    if tipo_rede_sel:
        df_filtrado = df_filtrado[
            df_filtrado["Tipo de Rede"].isin(tipo_rede_sel)
        ]

    # --- Ordenação customizada pelo Grau de Prioridade ---
    ordem_prioridade = ["Estratégico", "Médio", "Baixo"]
    df_filtrado["Prioridade"] = pd.Categorical(
        df_filtrado["Prioridade"],
        categories=ordem_prioridade,
        ordered=True
    )

    df_exibir = (
        df_filtrado
        .sort_values(by=["Nome"])
        .reset_index(drop=True)
    )

    # SUBHEADER DE CONTAGEM
    st.subheader(f"{len(df_exibir)} Redes e Articulações")
    st.write('')

    # --- Layout da tabela customizada ---
    colunas_visiveis = ["Nome", "Tipo de Rede", "Ponto Focal", "Prioridade", "Dedicação", "Programa"]
    headers = colunas_visiveis + ["Detalhes"]

    # Ajuste dos tamanhos de coluna (ponto focal mais estreito)
    col_sizes = [2, 1, 3, 1, 1, 2, 2]

    # Cabeçalho
    header_cols = st.columns(col_sizes)
    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.divider()

    # Linhas
    for i, row in df_exibir.iterrows():
        cols = st.columns(col_sizes)
        for j, key in enumerate(colunas_visiveis):
            cols[j].write(row[key])
        if cols[-1].button("Detalhes", key=f"detalhes_{i}", icon=":material/menu:", width="content"):
            # Busca documento original no Mongo
            rede_doc = redes.find_one({"rede_articulacao": row["Nome"]})
            if rede_doc:
                mostrar_detalhes(rede_doc)
        st.divider()


with aba_registros:

    st.write("")

    df_registros = carregar_registros()

    if df_registros.empty:
        st.caption("**Nenhum registro de incidência política ou articulação foi cadastrado ainda.**")

    else:
        # Coluna auxiliar com o ano da atividade
        df_registros["ano"] = df_registros["data"].dt.year
        
        with st.expander("Filtros", icon=":material/filter_alt:"):

            # =====================
            # Filtros
            # =====================
            colf0, colf1 = st.columns([1,3])

            tipo_sel = colf0.multiselect(
                "Tipo de registro",
                options=sorted(df_registros["tipo_registro"].dropna().unique()),
                placeholder="",
                key="filtro_reg_tipo",
            )
            
            busca_texto = colf1.text_input(
                "Buscar por texto",
                placeholder="Pauta, órgão, ator, rede...",
                key="filtro_reg_busca",
            )
            
            col1, col2, col3, col4 = st.columns(4)

            somente_articulacao = set(tipo_sel) == {"Articulação"}

            # Programa só existe em incidência política: fica desabilitado quando o filtro é só Articulação
            programa_sel_reg = col1.multiselect(
                "Programa",
                options=_opcoes_de_listas(df_registros["programas"]),
                placeholder="",
                key="filtro_reg_programa",
                disabled=somente_articulacao,
            )

            pessoa_sel = col2.multiselect(
                "Registrado por",
                options=sorted(df_registros["nome"].dropna().unique(), key=_chave_ordenacao),
                placeholder="",
                key="filtro_reg_pessoa",
            )
            
            anos_opcoes = sorted(df_registros["ano"].dropna().astype(int).unique(), reverse=True)
            
            ano_sel = col3.multiselect(
                "Ano",
                options=anos_opcoes,
                placeholder="",
                key="filtro_reg_ano",
            )

            # Período da atividade
            datas_validas = df_registros["data"].dropna()
            periodo_sel = None
            if not datas_validas.empty:
                periodo_sel = col4.date_input(
                    "Período da atividade",
                    value=(datas_validas.min().date(), df_registros["data_fim"].max().date()),
                    format="DD/MM/YYYY",
                    key="filtro_reg_periodo",
                )

            colf1, colf2, colf3 = st.columns(3)
            
            abrangencia_sel = colf1.multiselect(
                "Abrangência",
                options=sorted(df_registros["abrangencia"].dropna().unique()),
                placeholder="",
                key="filtro_reg_abrangencia",
            )

            uf_sel = colf2.multiselect(
                "Estado (UF)",
                options=_opcoes_de_listas(df_registros["ufs"]),
                placeholder="",
                key="filtro_reg_uf",
            )

            # Municípios: se houver UF selecionada, mostra só os municípios dessas UFs
            municipios_opcoes = _opcoes_de_listas(df_registros["territorio"])
            if uf_sel:
                municipios_opcoes = [m for m in municipios_opcoes if m.rsplit(" - ", 1)[-1] in uf_sel]

            municipio_sel = colf3.multiselect(
                "Município",
                options=municipios_opcoes,
                placeholder="",
                key="filtro_reg_municipio",
            )
        
        st.write("")

        # =====================
        # Aplica filtros
        # =====================
        df_filtrado_reg = df_registros.copy()

        if ano_sel:
            df_filtrado_reg = df_filtrado_reg[df_filtrado_reg["ano"].isin(ano_sel)]

        if tipo_sel:
            df_filtrado_reg = df_filtrado_reg[df_filtrado_reg["tipo_registro"].isin(tipo_sel)]

        if abrangencia_sel:
            df_filtrado_reg = df_filtrado_reg[df_filtrado_reg["abrangencia"].isin(abrangencia_sel)]

        if pessoa_sel:
            df_filtrado_reg = df_filtrado_reg[df_filtrado_reg["nome"].isin(pessoa_sel)]

        if programa_sel_reg and not somente_articulacao:
            df_filtrado_reg = df_filtrado_reg[
                df_filtrado_reg["programas"].apply(lambda lista: any(p in lista for p in programa_sel_reg))
            ]

        if uf_sel:
            df_filtrado_reg = df_filtrado_reg[
                df_filtrado_reg["ufs"].apply(lambda lista: any(uf in lista for uf in uf_sel))
            ]

        if municipio_sel:
            df_filtrado_reg = df_filtrado_reg[
                df_filtrado_reg["territorio"].apply(lambda lista: any(m in lista for m in municipio_sel))
            ]

        # O date_input de intervalo devolve 1 data enquanto a pessoa ainda está escolhendo a segunda
        if periodo_sel and isinstance(periodo_sel, (tuple, list)) and len(periodo_sel) == 2:
            inicio, fim = pd.Timestamp(periodo_sel[0]), pd.Timestamp(periodo_sel[1])
            df_filtrado_reg = df_filtrado_reg[
                (df_filtrado_reg["data"] <= fim) & (df_filtrado_reg["data_fim"] >= inicio)
            ]

        if busca_texto.strip():
            termo = _chave_ordenacao(busca_texto.strip())
            colunas_busca = [
                "pauta_objetivo", "encaminhamentos", "orgao_incidencia",
                "ator_impactado", "rede_articulacao", "organizacoes_envolvidas",
            ]
            texto_linha = df_filtrado_reg[colunas_busca].fillna("").astype(str).agg(" ".join, axis=1)
            df_filtrado_reg = df_filtrado_reg[texto_linha.apply(_chave_ordenacao).str.contains(termo, regex=False)]

        # =====================
        # Contagem
        # =====================
        n_incidencia = (df_filtrado_reg["tipo_registro"] == "Incidência política").sum()
        n_articulacao = (df_filtrado_reg["tipo_registro"] == "Articulação").sum()

        st.subheader(f"{len(df_filtrado_reg)} registros")
        st.caption(f"{n_incidencia} de incidência política · {n_articulacao} de articulação")
        st.write("")

        # =====================
        # Gráficos
        # =====================
        if not df_filtrado_reg.empty:

            LARGURA_GRAFICO = 400      # pizza + legenda
            LARGURA_GRAFICO_UF = 360   # mapa + barra de cores

            st.write("")

            with st.container(horizontal=True, gap="large"):

                

                with st.container(width=LARGURA_GRAFICO):
                    st.markdown("**Registros por tipo**")
                    st.plotly_chart(
                        grafico_pizza(df_filtrado_reg["tipo_registro"], ORDEM_TIPOS, CORES_TIPOS),
                        width="stretch",
                        config=CONFIG_PLOTLY,
                        key="grafico_tipo",
                    )

                with st.container(width=LARGURA_GRAFICO):
                    st.markdown("**Registros por abrangência**")
                    st.plotly_chart(
                        grafico_pizza(df_filtrado_reg["abrangencia"], ORDEM_ABRANGENCIA, CORES_ABRANGENCIA),
                        width="stretch",
                        config=CONFIG_PLOTLY,
                        key="grafico_abrangencia",
                    )

            st.write("")
            st.write("")


        # =====================================================================
        # VISUALIZAÇÃO: CARDS + PAINEL DE DETALHES
        # =====================================================================
        ALTURA_PAINEIS = 750
        LARGURA_CARDS = 500

        df_ordenado = df_filtrado_reg.sort_values("data", ascending=False)

        # Registro selecionado (só vale se ainda estiver entre os filtrados)
        id_sel = st.session_state.get("registro_selecionado")
        reg_sel = (
            df_ordenado[df_ordenado["_id"].astype(str) == id_sel]
            if id_sel else pd.DataFrame()
        )
        tem_selecao = not reg_sel.empty

        with st.container(horizontal=True, gap="medium"):

            # ---------- Cards (largura fixa, colados no painel) ----------
            with st.container(width=LARGURA_CARDS, height="content", border=False):
                if df_ordenado.empty:
                    st.caption("Nenhum registro encontrado com os filtros atuais.")
                for _, reg in df_ordenado.iterrows():
                    mostrar_card_registro(reg)

            # ---------- Detalhes (ocupa o resto da largura) ----------
            with st.container(width="stretch"):
                if tem_selecao:
                    reg_detalhe = reg_sel.iloc[0]

                    with st.container(height="content", border=True):
                        mostrar_detalhes_registro(reg_detalhe)
                        
                else:
                    st.caption("***Selecione um registro para ver os detalhes***")


with aba_forms:

    st.write("")
    st.write("")

    st.subheader("1. Informações gerais")
    st.write("")

    # Único campo fora do form: define o conteúdo do form
    tipo_registro = st.selectbox(
        "Tipo de registro*",
        options=OPCOES_TIPO_REGISTRO,
        index=None,
        placeholder="Selecione o tipo de registro",
        key="novo_reg_tipo",
        disabled=usuario_visitante,
        help=HELP_TIPO_REGISTRO,
        width=250,
    )

    if not tipo_registro:
        st.caption("Selecione o tipo de registro para abrir o formulário.")

    else:
        eh_incidencia = tipo_registro == TIPO_INCIDENCIA

        with st.form("form_novo_registro", border=False):

            valores = campos_formulario_registro(eh_incidencia, "novo_reg", desabilitado=usuario_visitante)

            st.write("")

            enviado = st.form_submit_button(
                "Salvar registro",
                icon=":material/check:",
                type="primary",
                width=200,
                disabled=usuario_visitante,
            )

            if enviado:
                dados_gerais, dados_detalhe, obrigatorios = montar_dados_registro(
                    valores, tipo_registro, nome=st.session_state.get("nome", "")
                )
                mensagem = (
                    "Registro de incidência política salvo com sucesso!"
                    if eh_incidencia else
                    "Registro de articulação salvo com sucesso!"
                )
                salvar_registro(dados_gerais, dados_detalhe, obrigatorios, mensagem)
    


