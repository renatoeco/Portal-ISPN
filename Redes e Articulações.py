import streamlit as st
import pandas as pd
from datetime import datetime
import time
import re
from funcoes_auxiliares import conectar_mongo_portal_ispn
import smtplib
from email.mime.text import MIMEText


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
redes = db["redes_articulacoes"]
pessoas = db["pessoas"]
estatistica = db["estatistica"]


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


@st.dialog("Detalhes da rede", width="medium")
def mostrar_detalhes(rede_doc):
    st.subheader(rede_doc.get("rede_articulacao", ""))
    st.write("")
    tabs = st.tabs([":material/info: Informações gerais", ":material/notes: Acompanhamentos"])

    # =====================
    # Aba 1: Informações gerais
    # =====================
    with tabs[0]:
        modo_edicao = st.toggle("Editar", value=False, disabled=usuario_visitante)

        if not modo_edicao:
            # Exibição simples
            col1, col2, col3 = st.columns(3)

            col1.write(f"**Rede/Articulação:** {rede_doc.get('rede_articulacao', '')}")
            col2.write(f"**Ponto(s) Focal(is):** {rede_doc.get('ponto_focal', '')}")
            col3.write(f"**Tema:** {rede_doc.get('tema', '')}")

            col1.write(f"**Rede/Articulação:** {rede_doc.get('rede_articulacao', '')}")
            col2.write(f"**Ponto(s) Focal(is):** {rede_doc.get('ponto_focal', '')}")
            col3.write(f"**Tema:** {rede_doc.get('tema', '')}")

            col1, col2, col3 = st.columns(3)

            col1.write(f"**Programa:** {rede_doc.get('programa', '')}")
            col2.write(f"**Grau de Prioridade:** {rede_doc.get('prioridade', '')}")
            col3.write(f"**Dedicação:** {rede_doc.get('dedicacao', '')}")

            st.write(f"**Status:** {rede_doc.get('status', 'ativa')}")

            st.write(f"**Descrição da rede:** {rede_doc.get('descricao', '')}")


            col1.write(f"**Programa:** {rede_doc.get('programa', '')}")
            col2.write(f"**Grau de Prioridade:** {rede_doc.get('prioridade', '')}")
            col3.write(f"**Dedicação:** {rede_doc.get('dedicacao', '')}")

            st.write(f"**Status:** {rede_doc.get('status', 'ativa')}")

            st.write(f"**Descrição da rede:** {rede_doc.get('descricao', '')}")


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

            # =====================
            # Campos editáveis
            # =====================
            
            rede_edit = st.text_input("Rede/Articulação", value=rede_doc.get("rede_articulacao", ""))

            col1, col2 = st.columns([1.5, 2])

            ponto_focal_str = rede_doc.get("ponto_focal", "")
            ponto_focal_list = [p.strip() for p in ponto_focal_str.split(",")] if ponto_focal_str else []

            ponto_focal_edit = col1.multiselect(
                "Ponto Focal",
                options=pessoas_opcoes,
                default=[p for p in ponto_focal_list if p in pessoas_opcoes]
            )

            temas_default = [
                t.strip()
                for t in re.split(r",|;", rede_doc.get("tema", ""))
                if t.strip() and t.strip() in temas_opcoes
            ]

            temas_selecionados = col2.multiselect(
                "Temas",
                options=temas_opcoes,
                default=temas_default,
            )

            col1, col2, col3, col4 = st.columns(4)

            prioridade_edit = col1.selectbox(
                "Grau de Prioridade",
                options=prioridades_opcoes,
                index=prioridades_opcoes.index(rede_doc.get("prioridade")) if rede_doc.get("prioridade") in prioridades_opcoes else 0,
            )

            dedicacao_edit = col2.selectbox(
                "Dedicação",
                options=dedicacao_opcoes,
                index=dedicacao_opcoes.index(rede_doc.get("dedicacao")) if rede_doc.get("dedicacao") in dedicacao_opcoes else 0,
            )

            programa_edit = col3.selectbox(
                "Programa",
                options=programas_opcoes,
                index=programas_opcoes.index(rede_doc.get("programa")) if rede_doc.get("programa") in programas_opcoes else 0,
            )

            status_edit = col4.selectbox(
                "Status",
                options=status_opcoes,
                index=status_opcoes.index(rede_doc.get("status", "ativa")) if rede_doc.get("status", "ativa") in status_opcoes else 0,
            )

            descricao_edit = st.text_area("Descrição da rede", value=rede_doc.get("descricao", ""))

            descricao_edit = st.text_area("Descrição da rede", value=rede_doc.get("descricao", ""))

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
                            "status": status_edit,  # <-- salva o status
                        }
                    },
                )

                st.success("Alterações salvas com sucesso!")
                time.sleep(2)
                st.rerun()


    # Aba 2: Acompanhamento / Memória
    # Aba 2: Acompanhamento / Memória
    with tabs[1]:
        usuario_logado = st.session_state.get("nome", "Desconhecido")
        tipo_usuario = st.session_state.get("tipo_usuario", "")
        anotacoes = rede_doc.get("anotacoes") or []

        # ---------------- EXPANDER PARA ADICIONAR ANOTAÇÃO ----------------
        with st.expander("Adicionar novo acompanhamento", expanded=False, icon=":material/add_notes:"):
            nova_data = datetime.now().date()
            novo_texto = st.text_area("Texto do acompanhamento", key="nova_anotacao", height="content", disabled=usuario_visitante)

            # Lista de nomes (igual ponto focal)
            pessoas_opcoes = sorted({
                p.get("nome_completo")
                for p in pessoas.find()
                if p.get("nome_completo")
            })

            # Dicionário nome -> email
            pessoas_dict = {
                p.get("nome_completo"): p.get("e_mail")
                for p in pessoas.find()
                if p.get("nome_completo")
            }

            # Recupera os pontos focais da rede
            ponto_focal_str = rede_doc.get("ponto_focal", "")
            ponto_focal_list = [p.strip() for p in ponto_focal_str.split(",")] if ponto_focal_str else []

            # Garante que só entram valores válidos (existentes nas opções)
            default_destinatarios = [p for p in ponto_focal_list if p in pessoas_opcoes]

            destinatarios_sel = st.multiselect(
                "Notificar pessoas por e-mail",
                options=pessoas_opcoes,
                default=default_destinatarios, 
                disabled=usuario_visitante,
                placeholder=""
            )

            if st.button("Adicionar acompanhamento", key="btn_add_anotacao", icon=":material/add_notes:", disabled=usuario_visitante):

                if novo_texto.strip():

                    nova_entry = {
                        "data_anotacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "autor_anotacao": usuario_logado,
                        "anotacao": novo_texto.strip()
                    }

                    redes.update_one(
                        {"_id": rede_doc["_id"]},
                        {"$push": {"anotacoes": nova_entry}}
                    )

                    # =========================
                    # ENVIO DE EMAILS
                    # =========================
                    erros_email = []
                    sem_email = []

                    for nome in destinatarios_sel:
                        email = pessoas_dict.get(nome)

                        if not email:
                            sem_email.append(nome)
                            continue

                        sucesso = enviar_email_acompanhamento(
                            destinatario=email,
                            nome_destinatario=nome,
                            rede_nome=rede_doc.get("rede_articulacao", ""),
                            descricao=rede_doc.get("descricao", ""),
                            texto=novo_texto.strip(),
                            autor=usuario_logado
                        )

                        if not sucesso:
                            erros_email.append(nome)

                    # Feedback
                    if destinatarios_sel:
                        if erros_email:
                            st.warning(f"E-mails não enviados para: {', '.join(erros_email)}")

                    st.success("Acompanhamento salvo com sucesso.")
                    time.sleep(2)
                    st.rerun(scope="fragment")

                else:
                    st.warning("O campo do acompanhamento não pode estar vazio.")
                    st.warning("O campo do acompanhamento não pode estar vazio.")

        st.write("")
        st.write("**Acompanhamentos registrados:**")
        st.write("**Acompanhamentos registrados:**")

        # ---------------- LISTA DE Acompanhamento / Memória ----------------
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
                        st.success("Acompanhamento atualizado.")

                    if botoes.button("Deletar acompanhamento", key=f"deletar_{container_key}", icon=":material/delete:"):
                        st.session_state[delete_key] = True

                    if st.session_state.get(delete_key, False):
                        st.warning("Tem certeza que deseja apagar este acompanhamento?")
                        st.warning("Tem certeza que deseja apagar este acompanhamento?")

                        botoes_confirmacao = st.container(horizontal=True)

                        if botoes_confirmacao.button("Sim", key=f"confirmar_delete_{container_key}", icon=":material/check:"):
                            anotacoes.pop(original_idx)
                            redes.update_one(
                                {"_id": rede_doc["_id"]},
                                {"$set": {"anotacoes": anotacoes}}
                            )
                            st.success("Acompanhamento apagado com sucesso.")
                            st.success("Acompanhamento apagado com sucesso.")
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

    # =====================
    # Campos do cadastro
    # =====================
    
    rede_edit = st.text_input("Rede/Articulação*")

    descricao_edit = st.text_area("Descrição da rede*")

    descricao_edit = st.text_area("Descrição da rede*")

    col1, col2 = st.columns([1.5, 2])
    ponto_focal_edit = col1.multiselect("Ponto Focal*", options=pessoas_opcoes, placeholder="")
    temas_selecionados = col2.multiselect("Temas*", options=temas_opcoes, placeholder="")

    col1, col2, col3 = st.columns(3)
    prioridade_edit = col1.selectbox("Grau de Prioridade*", options=prioridades_opcoes)
    dedicacao_edit = col2.selectbox("Dedicação*", options=dedicacao_opcoes)
    programa_edit = col3.selectbox("Programa*", options=programas_opcoes)

    # =====================
    # Acompanhamento / Memória iniciais
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
            ("Descrição da rede", descricao_edit.strip()),
            ("Ponto Focal", ponto_focal_edit),
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
            "status": "ativa",  # fixo por padrão
            "anotacoes": [],
        }

        # if nova_anotacao.strip():
        #     nova_rede["anotacoes"].append({
        #         "data_anotacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
        #         "autor_anotacao": usuario_logado,
        #         "anotacao": nova_anotacao.strip()
        #     })

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
    

######################################################################################################
# MAIN
######################################################################################################


# Verifica se o usuário é visitante
usuario_visitante = "visitante" in st.session_state.get("tipo_usuario", [])



st.header("Redes e Articulações")
st.write("")
st.write("")
st.write("")

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
    "ponto_focal": "Ponto Focal",
    "prioridade": "Prioridade",
    "dedicacao": "Dedicação",
    "programa": "Programa",
    "status": "Status",
    "tema": "Tema"  
})

df_redes = df_redes[["Nome", "Ponto Focal", "Tema", "Prioridade", "Dedicação", "Programa", "Status"]]

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
    colf1, colf2, colf3 = st.columns(3)
    
    rede_sel = colf1.multiselect(
        "Rede",
        options=sorted(df_redes["Nome"].dropna().unique().tolist()), placeholder=""
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
colunas_visiveis = ["Nome", "Ponto Focal", "Prioridade", "Dedicação", "Programa"]
headers = colunas_visiveis + ["Detalhes"]

# Ajuste dos tamanhos de coluna (ponto focal mais estreito)
col_sizes = [4, 4, 1, 1, 2, 2]

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





# # TESTE DE CAIXA DE ANOTAÇÕES COM LIMITE DE CARACTERES

# MAX_CARACTERES = 2000

# texto = st.text_area("Digite seu texto (máx. 2000 caracteres):", height=400)
# num_caracteres = len(texto)
# caracteres_restantes = MAX_CARACTERES - num_caracteres

# if caracteres_restantes < 0:
#     st.markdown(f"<span style='color:red'>{num_caracteres} / {MAX_CARACTERES} - Você ultrapassou o limite em {-caracteres_restantes} caracteres!</span>", unsafe_allow_html=True)
# else:
#     st.write(f"{num_caracteres} / {MAX_CARACTERES}")
# st.write(f"*Clique fora da caixa de texto para atualizar o contador")