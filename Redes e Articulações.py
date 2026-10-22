import streamlit as st
import pandas as pd
from datetime import datetime
import time
import re
import unicodedata
from bson import ObjectId

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

                col1, col2 = st.columns(2)

                col1.write(f"**Tema:** {rede_doc.get('tema', '')}")
                col2.write(f"**Tipo de Rede:** {rede_doc.get('tipo_rede', '')}")

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

                programas_opcoes = [
                    "",
                    "Cerrado",
                    "Coordenação",
                    "Iniciativas Comunitárias",
                    "Maranhão",
                    "Povos Indígenas",
                    "Sociobiodiversidade",
                ]

                # Opções fixas para status
                status_opcoes = ["ativa", "inativa"]
                
                tipos_rede_opcoes = [" ","tipo 1", "tipo 2", "tipo 3"]

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


                col1, col2 = st.columns(2)

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
                    if rede_doc.get("tipo_rede") in tipos_rede_opcoes else 0,
                )
                
                col1, col2, col3, col4 = st.columns(4)
                
                programa_edit = col1.selectbox(
                    "Programa",
                    options=programas_opcoes,
                    index=programas_opcoes.index(rede_doc.get("programa")) if rede_doc.get("programa") in programas_opcoes else 0,
                )

                prioridade_edit = col2.selectbox(
                    "Grau de Prioridade",
                    options=prioridades_opcoes,
                    index=prioridades_opcoes.index(rede_doc.get("prioridade")) if rede_doc.get("prioridade") in prioridades_opcoes else 0,
                )

                dedicacao_edit = col3.selectbox(
                    "Dedicação",
                    options=dedicacao_opcoes,
                    index=dedicacao_opcoes.index(rede_doc.get("dedicacao")) if rede_doc.get("dedicacao") in dedicacao_opcoes else 0,
                )


                status_edit = col4.selectbox(
                    "Status",
                    options=status_opcoes,
                    index=status_opcoes.index(rede_doc.get("status", "ativa")) if rede_doc.get("status", "ativa") in status_opcoes else 0,
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

            col1, col2 = st.columns(2)

            col1.write(f"**Tema:** {rede_doc.get('tema', '')}")
            col2.write(f"**Tipo de Rede:** {rede_doc.get('tipo_rede', '')}")

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


@st.dialog("Cadastrar rede", width="medium") 
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

    programas_opcoes = [
        "",
        "ADM Brasília",
        "ADM Santa Inês",
        "Advocacy",
        "Cerrado",
        "Comunicação",
        "Coordenação",
        "Iniciativas Comunitárias",
        "Maranhão",
        "Povos Indígenas",
        "Sociobiodiversidade",
    ]
    
    tipos_rede_opcoes = ["1", "2", "3"]
    
    # =====================
    # Campos do cadastro
    # =====================
    
    rede_edit = st.text_input("Rede/Articulação*")

    descricao_edit = st.text_area("Descrição da rede*")

    col1, col2, col3 = st.columns([1.5, 2, 0.5])
    ponto_focal_edit = col1.multiselect("Ponto Focal*", options=pessoas_opcoes, placeholder="")
    temas_selecionados = col2.multiselect("Temas*", options=temas_opcoes, placeholder="")
    tipo_rede_edit = col3.selectbox(
        "Tipo de Rede*",
        options=tipos_rede_opcoes
    )

    col1, col2, col3 = st.columns(3)
    prioridade_edit = col1.selectbox("Grau de Prioridade*", options=prioridades_opcoes)
    dedicacao_edit = col2.selectbox("Dedicação*", options=dedicacao_opcoes)
    programa_edit = col3.selectbox("Programa*", options=programas_opcoes)

    # =====================
    # Acompanhamento / Memória iniciais
    # =====================
    
    usuario_logado = st.session_state.get("nome", "Desconhecido")
    #nova_anotacao = st.text_area("Acompanhamento", key="anotacao_inicial", height="content")
    st.write("")

    # =====================
    # Botão salvar
    # =====================
    
    if st.button("Adicionar rede", width=200, icon=":material/check:", type="primary"):
        
        # -----------------
        # Validação obrigatórios
        # -----------------
        
        campos_obrigatorios = [
            ("Rede/Articulação", rede_edit.strip()),
            ("Descrição da rede", descricao_edit.strip()),
            ("Ponto Focal", ponto_focal_edit),
            ("Tipo de Rede", tipo_rede_edit),
            ("Temas", temas_selecionados),
            ("Grau de Prioridade", prioridade_edit.strip() if prioridade_edit else ""),
            ("Dedicação", dedicacao_edit.strip() if dedicacao_edit else ""),
            ("Programa", programa_edit.strip() if programa_edit else ""),
        ]

        faltando = [nome for nome, valor in campos_obrigatorios if not valor]
        if faltando:
            st.warning(f"Preencha todos os campos obrigatórios: {', '.join(faltando)}")
            st.stop()

        # -----------------
        # Verificação duplicidade
        # -----------------
        
        existe = redes.find_one({"rede_articulacao": {"$regex": f"^{re.escape(rede_edit.strip())}$", "$options": "i"}})
        if existe:
            st.error("Já existe uma rede cadastrada com esse nome.")
            st.stop()

        # -----------------
        # Monta documento
        # -----------------
        
        nova_rede = {
            "rede_articulacao": rede_edit.strip(),
            "descricao": descricao_edit.strip(),
            "descricao": descricao_edit.strip(),
            "ponto_focal": ", ".join(ponto_focal_edit),
            "tema": ", ".join(temas_selecionados),
            "prioridade": prioridade_edit,
            "dedicacao": dedicacao_edit,
            "programa": programa_edit,
            "status": "ativa",  
            "tipo_rede": tipo_rede_edit,
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


def _chave_ordenacao(texto: str) -> str:
    """Remove acentos para ordenar alfabeticamente (ex: 'Água Boa' junto dos 'A')."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


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
        ("Território", dados_gerais.get("territorio")),
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

        programas = [
            mapa_programas.get(str(pid), "Programa removido")
            for pid in (d.get("programas") or [])
        ]

        envolveu = d.get("envolveu_outras_organizacoes")
        envolveu_txt = "" if envolveu is None else ("Sim" if envolveu else "Não")

        linhas.append({
            "_id": d["_id"],
            "data": pd.to_datetime(d.get("data_atividade"), format="%d/%m/%Y", errors="coerce"),
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

        st.caption(
            f":material/calendar_today: {_data_formatada(reg['data'])} · "
            f":material/location_on: {', '.join(reg['territorio']) or '—'}"
        )
        st.write(_resumo(reg.get("pauta_objetivo", "")))
        st.caption(f":material/person: {reg.get('nome', '')}")


def mostrar_detalhes_registro(reg):
    """Painel com todas as informações de um registro."""
    eh_incidencia = reg["tipo_registro"] == "Incidência política"

    cor = "blue" if eh_incidencia else "orange"
    st.badge(reg["tipo_registro"], color=cor)
    st.subheader(_titulo_registro(reg))
    st.write("")

    col1, col2 = st.columns(2)
    col1.write(f"**Data da atividade:** {_data_formatada(reg['data'])}")
    col2.write(f"**Abrangência:** {reg.get('abrangencia') or '—'}")
    col1.write(f"**Registrado por:** {reg.get('nome') or '—'}")
    col2.write(f"**Registrado em:** {reg.get('data_registro') or '—'}")
    st.write(f"**Território:** {', '.join(reg['territorio']) or '—'}")

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
        status_unicos = ["ativa", "inativa"]  # fallback se não existir no banco

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
            default=["ativa"], 
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
    col_sizes = [4, 1, 4, 1, 1, 2, 2]

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
        if cols[-1].button("Detalhes", key=f"detalhes_{i}", icon=":material/menu:", use_container_width=True):
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
        # =====================
        # Filtros
        # =====================
        colf1, colf2, colf3, colf4 = st.columns(4)

        tipo_sel = colf1.multiselect(
            "Tipo de registro",
            options=sorted(df_registros["tipo_registro"].dropna().unique()),
            placeholder="",
            key="filtro_reg_tipo",
        )

        # Quando só "Articulação" está selecionado, a tabela mostra apenas as colunas de articulação
        somente_articulacao = set(tipo_sel) == {"Articulação"}
        somente_incidencia = set(tipo_sel) == {"Incidência política"}

        abrangencia_sel = colf2.multiselect(
            "Abrangência",
            options=sorted(df_registros["abrangencia"].dropna().unique()),
            placeholder="",
            key="filtro_reg_abrangencia",
        )

        # Programa só existe em incidência política: fica desabilitado quando o filtro é só Articulação
        programa_sel_reg = colf3.multiselect(
            "Programa",
            options=_opcoes_de_listas(df_registros["programas"]),
            placeholder="",
            key="filtro_reg_programa",
            disabled=somente_articulacao,
        )

        pessoa_sel = colf4.multiselect(
            "Registrado por",
            options=sorted(df_registros["nome"].dropna().unique(), key=_chave_ordenacao),
            placeholder="",
            key="filtro_reg_pessoa",
        )

        colf1, colf2, colf3, colf4 = st.columns(4)

        uf_sel = colf1.multiselect(
            "Estado (UF)",
            options=_opcoes_de_listas(df_registros["ufs"]),
            placeholder="",
            key="filtro_reg_uf",
        )

        # Municípios: se houver UF selecionada, mostra só os municípios dessas UFs
        municipios_opcoes = _opcoes_de_listas(df_registros["territorio"])
        if uf_sel:
            municipios_opcoes = [m for m in municipios_opcoes if m.rsplit(" - ", 1)[-1] in uf_sel]

        municipio_sel = colf2.multiselect(
            "Município",
            options=municipios_opcoes,
            placeholder="",
            key="filtro_reg_municipio",
        )

        # Período da atividade
        datas_validas = df_registros["data"].dropna()
        periodo_sel = None
        if not datas_validas.empty:
            periodo_sel = colf3.date_input(
                "Período da atividade",
                value=(datas_validas.min().date(), datas_validas.max().date()),
                format="DD/MM/YYYY",
                key="filtro_reg_periodo",
            )

        busca_texto = colf4.text_input(
            "Buscar por texto",
            placeholder="Pauta, órgão, ator, rede...",
            key="filtro_reg_busca",
        )

        st.write("")
        st.write("")

        # =====================
        # Aplica filtros
        # =====================
        df_filtrado_reg = df_registros.copy()

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
            df_filtrado_reg = df_filtrado_reg[df_filtrado_reg["data"].between(inicio, fim)]

        if busca_texto.strip():
            termo = _chave_ordenacao(busca_texto.strip())
            colunas_busca = [
                "pauta_objetivo", "encaminhamentos", "orgao_incidencia",
                "ator_impactado", "rede_articulacao", "organizacoes_envolvidas",
            ]
            texto_linha = df_filtrado_reg[colunas_busca].fillna("").astype(str).agg(" ".join, axis=1)
            df_filtrado_reg = df_filtrado_reg[texto_linha.apply(_chave_ordenacao).str.contains(termo, regex=False)]

        # =====================
        # Forma de visualização
        # =====================
        visualizacao = st.segmented_control(
            "Visualização",
            options=["Tabela", "Cards"],
            default="Tabela",
            selection_mode="single",
            key="visualizacao_registros",
            label_visibility="collapsed",
        ) or "Tabela"  # se a pessoa desmarcar, volta para Tabela

        st.write("")

        # Contagem
        n_incidencia = (df_filtrado_reg["tipo_registro"] == "Incidência política").sum()
        n_articulacao = (df_filtrado_reg["tipo_registro"] == "Articulação").sum()

        st.subheader(f"{len(df_filtrado_reg)} registros")
        st.caption(f"{n_incidencia} de incidência política · {n_articulacao} de articulação")
        st.write("")

        df_ordenado = df_filtrado_reg.sort_values("data", ascending=False)

        # =====================================================================
        # VISUALIZAÇÃO 1: TABELA
        # =====================================================================
        if visualizacao == "Tabela":

            df_exibir_reg = df_ordenado.copy()

            # Listas viram texto separado por vírgula
            for col in ["territorio", "programas"]:
                df_exibir_reg[col] = df_exibir_reg[col].apply(lambda lista: ", ".join(lista))

            df_exibir_reg = df_exibir_reg.rename(columns={
                "data": "Data",
                "tipo_registro": "Tipo",
                "nome": "Registrado por",
                "abrangencia": "Abrangência",
                "territorio": "Território",
                "programas": "Programas",
                "orgao_incidencia": "Órgão / Espaço",
                "ator_impactado": "Ator / Autoridade",
                "rede_articulacao": "Rede / Articulação",
                "pauta_objetivo": "Pauta / Objetivo",
                "encaminhamentos": "Encaminhamentos",
                "envolveu_outras_organizacoes": "Outras organizações?",
                "organizacoes_envolvidas": "Organizações envolvidas",
                "data_registro": "Registrado em",
            })

            # Colunas por tipo de registro
            COLUNAS_COMUNS_INICIO = ["Data", "Tipo", "Registrado por", "Abrangência", "Território"]
            COLUNAS_INCIDENCIA = [
                "Programas", "Órgão / Espaço", "Ator / Autoridade",
                "Pauta / Objetivo", "Encaminhamentos",
                "Outras organizações?", "Organizações envolvidas",
            ]
            COLUNAS_ARTICULACAO = ["Rede / Articulação", "Pauta / Objetivo", "Encaminhamentos"]
            COLUNAS_COMUNS_FIM = ["Registrado em"]

            if somente_articulacao:
                colunas_exibidas = COLUNAS_COMUNS_INICIO + COLUNAS_ARTICULACAO + COLUNAS_COMUNS_FIM
            elif somente_incidencia:
                colunas_exibidas = COLUNAS_COMUNS_INICIO + COLUNAS_INCIDENCIA + COLUNAS_COMUNS_FIM
            else:
                colunas_exibidas = COLUNAS_COMUNS_INICIO + [
                    "Programas", "Órgão / Espaço", "Ator / Autoridade", "Rede / Articulação",
                    "Pauta / Objetivo", "Encaminhamentos",
                    "Outras organizações?", "Organizações envolvidas",
                ] + COLUNAS_COMUNS_FIM

            st.dataframe(
                df_exibir_reg[colunas_exibidas],
                hide_index=True,
                width="stretch",
                column_config={
                    "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", width="small"),
                    "Tipo": st.column_config.TextColumn("Tipo", width="small"),
                    "Pauta / Objetivo": st.column_config.TextColumn("Pauta / Objetivo", width="large"),
                    "Encaminhamentos": st.column_config.TextColumn("Encaminhamentos", width="large"),
                    "Outras organizações?": st.column_config.TextColumn("Outras organizações?", width="small"),
                },
            )

        # =====================================================================
        # VISUALIZAÇÃO 2: CARDS + PAINEL DE DETALHES
        # =====================================================================
        else:

            ALTURA_PAINEIS = 750

            col_cards, col_detalhes  = st.columns([2, 3], gap="large")

            # ---------- Cards (esquerda) ----------
            with col_cards:
                with st.container(height=ALTURA_PAINEIS, border=False):
                    if df_ordenado.empty:
                        st.caption("Nenhum registro encontrado com os filtros atuais.")
                    for _, reg in df_ordenado.iterrows():
                        mostrar_card_registro(reg)

            # ---------- Detalhes (direita) ----------
            with col_detalhes:
                with st.container(height=ALTURA_PAINEIS, border=True):

                    id_sel = st.session_state.get("registro_selecionado")
                    reg_sel = df_ordenado[df_ordenado["_id"].astype(str) == id_sel] if id_sel else pd.DataFrame()

                    if not id_sel:
                        st.caption(":material/arrow_back: Clique no ícone :material/info: de um card para ver os detalhes do registro.")
                    elif reg_sel.empty:
                        st.caption("O registro selecionado não aparece com os filtros atuais.")
                    else:
                        mostrar_detalhes_registro(reg_sel.iloc[0])


with aba_forms:

    st.write("")
    st.write("")

    # Opções fixas ---------------------------------------------------------------
    OPCOES_ABRANGENCIA = [
        "Nacional (ex: Ministérios, Congresso, Conselhos Nacionais)",
        "Estadual (ex: Secretarias Estaduais, Assembleias Legislativas)",
        "Municipal (ex: Prefeituras, Câmaras de Vereadores)",
        "Internacional (ex: COP, ONU)",
    ]

    OPCOES_TIPO_REGISTRO = ["Incidência política", "Articulação"]

    TERRITORIO_PADRAO_NACIONAL = "Brasília - DF"

    # =================================================================
    # 1. INFORMAÇÕES GERAIS
    # =================================================================
    st.subheader("1. Informações gerais")
    st.write("")

    # =====================================================================
    # TIPO DE REGISTRO (único campo fora do form: define o conteúdo do form)
    # =====================================================================
    tipo_registro = st.selectbox(
        "Tipo de registro*",
        options=OPCOES_TIPO_REGISTRO,
        index=None,
        placeholder="Selecione o tipo de registro",
        key="novo_reg_tipo",
        disabled=usuario_visitante,
        help="**Opção 1 - Incidência política:** Ações direcionadas a influenciar políticas públicas, "
             "tomadores de decisão, proposição legislativa e espaços de governança formais para a "
             "defesa de direitos.  \n\n"
             "**Opção 2 - Articulação:** Eventos de articulação/rede, reuniões ampliadas, reuniões "
             "estratégicas, conferências de articulação específica que o ISPN faz parte, etc.",
        width=250
    )

    if not tipo_registro:
        st.caption("Selecione o tipo de registro para abrir o formulário.")

    else:
        eh_incidencia = tipo_registro == "Incidência política"

        opcoes_territorio = carregar_opcoes_territorio()
        mapa_programas = carregar_opcoes_programas() if eh_incidencia else {}

        with st.form("form_novo_registro", border=False):

            col1, col2 = st.columns(2)

            nome_registro = col1.text_input(
                "Nome",
                value=st.session_state.get("nome", ""),
                disabled=True,
                key="novo_reg_nome",
            )

            data_atividade = col2.date_input(
                "Data em que a atividade ocorreu*",
                value=None,
                max_value=datetime.now().date(),
                format="DD/MM/YYYY",
                key="novo_reg_data",
                disabled=usuario_visitante,
            )

            st.write("")

            col1, col2 = st.columns(2)

            abrangencia = col1.radio(
                "Abrangência / Escopo do Espaço*",
                options=OPCOES_ABRANGENCIA,
                index=None,
                key="novo_reg_abrangencia",
                disabled=usuario_visitante,
            )

            territorio = col2.multiselect(
                "Território (Município/Estado) onde a ação se localiza fisicamente ou politicamente*",
                options=opcoes_territorio,
                placeholder="Digite para buscar o município",
                key="novo_reg_territorio",
                disabled=usuario_visitante,
                help="Se for de âmbito Nacional/Federal, pode preencher como Brasília-DF."
            )

            st.divider()

            # =================================================================
            # 2. DETALHAMENTO - INCIDÊNCIA POLÍTICA
            # =================================================================
            if eh_incidencia:
                st.subheader("2. Detalhamento - Incidência política")
                st.write("")

                col1, col2 = st.columns(2)

                orgao_incidencia = col1.text_input(
                    "Órgão / Instituição / Espaço de Incidência*",
                    key="novo_reg_inc_orgao",
                    disabled=usuario_visitante,
                    help="Nome específico do espaço (ex: Ministério do Meio Ambiente - MMA, Secretaria de Estado de Meio Ambiente e Recursos Naturais do Maranhão, Núcleo Agrário, etc.)."
                )

                ator_impactado = col2.text_input(
                    "Ator / Autoridade Impactada*",
                    key="novo_reg_inc_ator",
                    disabled=usuario_visitante,
                    help="Indique o tomador de decisão, autoridade ou ator político central que foi o foco dessa ação de incidência."
                )

                programas_ids = st.multiselect(
                    "Programa(s) do ISPN relacionado(s)*",
                    options=list(mapa_programas.keys()),
                    format_func=lambda pid: mapa_programas.get(pid, pid),
                    placeholder="",
                    key="novo_reg_inc_programas",
                    disabled=usuario_visitante,
                )

                pauta_objetivo = st.text_area(
                    "Pauta / Objetivo*",
                    key="novo_reg_inc_pauta",
                    disabled=usuario_visitante,
                )

                encaminhamentos = st.text_area(
                    "Encaminhamentos",
                    key="novo_reg_inc_encaminhamentos",
                    disabled=usuario_visitante,
                )

                envolveu_organizacoes = st.radio(
                    "Essa incidência envolveu outras organizações?*",
                    options=["Sim", "Não"],
                    index=None,
                    horizontal=True,
                    key="novo_reg_inc_envolveu_orgs",
                    disabled=usuario_visitante,
                )

                # Sempre visível; opcional e salvo em branco se não for preenchido
                organizacoes_envolvidas = st.text_area(
                    "Quais organizações estiveram envolvidas?",
                    key="novo_reg_inc_orgs",
                    disabled=usuario_visitante,
                )

            # =================================================================
            # 2. DETALHAMENTO - ARTICULAÇÃO / REDES
            # =================================================================
            else:
                st.subheader("2. Detalhamento - Articulação / Redes")
                st.write("")

                rede_referente = st.text_input(
                    "A qual rede/articulação se refere?*",
                    key="novo_reg_art_rede",
                    disabled=usuario_visitante,
                )

                pauta_objetivo_art = st.text_area(
                    "Pauta / Objetivo*",
                    key="novo_reg_art_pauta",
                    disabled=usuario_visitante,
                )

                encaminhamentos_art = st.text_area(
                    "Encaminhamentos",
                    key="novo_reg_art_encaminhamentos",
                    disabled=usuario_visitante,
                )

            st.write("")

            enviado = st.form_submit_button(
                "Salvar registro",
                icon=":material/check:",
                type="primary",
                width=200,
                disabled=usuario_visitante,
            )

            # =================================================================
            # ENVIO
            # =================================================================
            if enviado:

                # Território padrão: se for Nacional e nada for selecionado, assume Brasília - DF
                territorio_final = territorio
                if not territorio and abrangencia and abrangencia.startswith("Nacional"):
                    territorio_final = [TERRITORIO_PADRAO_NACIONAL]

                dados_gerais = {
                    "nome": nome_registro,
                    "data_atividade": data_atividade.strftime("%d/%m/%Y") if data_atividade else None,
                    "abrangencia": abrangencia.split(" (")[0] if abrangencia else None,  # ex: "Nacional"
                    "territorio": territorio_final,
                    "tipo_registro": tipo_registro,
                }

                if eh_incidencia:
                    obrigatorios = [
                        ("Órgão / Instituição / Espaço de Incidência", orgao_incidencia.strip()),
                        ("Ator / Autoridade Impactada", ator_impactado.strip()),
                        ("Programa(s) do ISPN relacionado(s)", programas_ids),
                        ("Pauta / Objetivo", pauta_objetivo.strip()),
                        ("Essa incidência envolveu outras organizações?", envolveu_organizacoes),
                    ]

                    dados_detalhe = {
                        "orgao_incidencia": orgao_incidencia.strip(),
                        "ator_impactado": ator_impactado.strip(),
                        "programas": [ObjectId(pid) for pid in programas_ids],
                        "pauta_objetivo": pauta_objetivo.strip(),
                        "encaminhamentos": encaminhamentos.strip(),
                        "envolveu_outras_organizacoes": envolveu_organizacoes == "Sim",
                        "organizacoes_envolvidas": organizacoes_envolvidas.strip(),  # "" se vazio
                    }
                    mensagem = "Registro de incidência política salvo com sucesso!"

                else:
                    obrigatorios = [
                        ("A qual rede/articulação se refere?", rede_referente.strip()),
                        ("Pauta / Objetivo", pauta_objetivo_art.strip()),
                    ]

                    dados_detalhe = {
                        "rede_articulacao": rede_referente.strip(),
                        "pauta_objetivo": pauta_objetivo_art.strip(),
                        "encaminhamentos": encaminhamentos_art.strip(),
                    }
                    mensagem = "Registro de articulação salvo com sucesso!"

                salvar_registro(dados_gerais, dados_detalhe, obrigatorios, mensagem)
    


