import streamlit as st
import pandas as pd
from funcoes_auxiliares import conectar_mongo_portal_ispn
from datetime import datetime
import time
from bson import ObjectId
from pymongo import ReturnDocument
from st_rsuite import date_picker
import io
import smtplib
import re
import unicodedata
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, SimpleDocTemplate,
    Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
)

# ##################################################################
# CONFIGURAÇÕES DA INTERFACE
# ##################################################################

st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Insumos")
st.write('')

# ##################################################################
# CONEXÃO COM O BANCO DE DADOS MONGO
# ##################################################################

# BANCO DE DADOS ISPN HUB
db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas
insumos = db["insumos"]
projetos_ispn = db["projetos_ispn"]
pessoas = db["pessoas"]
contadores = db["contadores"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################

PAGINA_ID = "pagina_insumos"
nome_pagina = "Insumos"

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
# FUNÇÕES AUXILIARES
###########################################################################################################


def obter_rotulo_projeto(projeto):
    """Retorna o rótulo de exibição do projeto: sigla > código > nome."""
    return projeto.get("sigla") or projeto.get("codigo") or projeto.get("nome_do_projeto") or "Sem identificação"


def usuario_id_atual():
    """Retorna o id (string) do usuário logado, ou None se não houver."""
    return st.session_state.get("id_usuario")


def usuario_eh_admin():
    """Verifica se o usuário logado é do tipo 'admin'."""
    tipos_usuario = st.session_state.get("tipo_usuario", [])
    if isinstance(tipos_usuario, str):
        tipos_usuario = [tipos_usuario]
    return "admin" in tipos_usuario


def usuario_eh_gestor_ou_coordenador(projeto):
    """Verifica se o usuário logado é o coordenador ou um dos gestores do
    projeto informado (compara pelo id do usuário logado)."""
    if not projeto:
        return False

    id_usuario = usuario_id_atual()
    if not id_usuario:
        return False

    coordenador = projeto.get("coordenador")
    if coordenador and str(coordenador) == str(id_usuario):
        return True

    gestores = projeto.get("gestores", [])
    return any(str(gestor) == str(id_usuario) for gestor in gestores)


def usuario_pode_gerenciar_perguntas(projeto):
    """Admin, ou o coordenador/gestores do projeto, podem cadastrar e editar
    as perguntas personalizadas daquele projeto."""
    return usuario_eh_admin() or usuario_eh_gestor_ou_coordenador(projeto)


def usuario_pode_editar_solicitacao(solicitacao, projeto):
    """Admin, o responsável pela solicitação, ou o coordenador/gestores do
    projeto ao qual a solicitação pertence, podem editar a solicitação."""
    if usuario_eh_admin():
        return True

    id_usuario = usuario_id_atual()
    responsavel_id = solicitacao.get("responsavel_id")
    if id_usuario and responsavel_id and str(responsavel_id) == str(id_usuario):
        return True

    return usuario_eh_gestor_ou_coordenador(projeto)


def projetos_permitidos_para_perguntas(projetos):
    """Retorna somente os projetos cujas perguntas o usuário logado tem
    permissão de cadastrar/editar (admin vê todos)."""
    if usuario_eh_admin():
        return projetos
    return [p for p in projetos if usuario_eh_gestor_ou_coordenador(p)]


def sanitizar_nome_arquivo(texto):
    """Remove acentos e caracteres não permitidos em nomes de arquivo,
    substituindo espaços por '_'."""
    texto_sem_acento = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    texto_limpo = re.sub(r"[^A-Za-z0-9_-]+", "_", texto_sem_acento.strip())
    return texto_limpo.strip("_") or "solicitacao"


def gerar_codigo_solicitacao():
    """Gera, de forma atômica, um código sequencial de 4 dígitos (iniciando
    em '0001') para uma nova solicitação de insumos, usando um contador
    dedicado na coleção 'contadores' (documento de _id
    'codigo_solicitacao_insumos'). Diferente de basear-se no maior código
    já salvo na coleção 'insumos', os códigos nunca se repetem: mesmo que
    uma solicitação seja excluída, seu código não volta a ser usado."""
    contador_atualizado = contadores.find_one_and_update(
        {"_id": "codigo_solicitacao_insumos"},
        {"$inc": {"sequencia": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    return f"SDI-{contador_atualizado['sequencia']:04d}"


def gerar_pdf_solicitacao(solicitacao, projetos_dict, pessoas_dict):
    """Gera o PDF da solicitação de insumos, seguindo a mesma ordem e formato
    de campos exibidos no diálogo de Detalhes da Solicitação. Retorna os
    bytes do PDF."""

    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )

    # Frame SEM padding interno: assim a largura disponível é exatamente
    # doc.width (17 cm) e tudo (divisores, tabelas, textos) fica alinhado.
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="frame_principal",
    )

    largura_util = doc.width

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloSolicitacao", parent=styles["Title"], alignment=TA_LEFT,
        fontSize=16, leading=20, spaceAfter=4,
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloSolicitacao", parent=styles["Normal"], alignment=TA_LEFT,
        fontSize=11, leading=14, textColor=colors.HexColor("#333333"),
    )
    estilo_normal = ParagraphStyle("NormalSolicitacao", parent=styles["Normal"], fontSize=10, leading=14)

    elementos = []

    def linha(rotulo, valor):
        texto = valor if valor not in (None, "") else "—"
        return Paragraph(f"<b>{rotulo}:</b> {texto}", estilo_normal)

    def divisor():
        return HRFlowable(width="100%", thickness=0.75, color=colors.grey, spaceBefore=10, spaceAfter=10)

    # ---------------------------------------------------------------
    # Cabeçalho: logo à esquerda; à direita, "Solicitação de Insumos"
    # e, logo abaixo, o "Código:". A faixa colorida é desenhada no canvas
    # da página, de ponta a ponta, desde o topo.
    # ---------------------------------------------------------------
    largura_logo = 4 * cm
    separacao_logo_titulo = 5 * cm   # <- aumente/diminua para ajustar o espaço

    caminho_logo = "images/logo_ISPN_horizontal_ass.png"
    try:
        iw, ih = ImageReader(caminho_logo).getSize()
        logo = Image(caminho_logo, width=largura_logo, height=largura_logo * ih / iw)
        logo.hAlign = "LEFT"
    except Exception:
        largura_logo = 0
        logo = ""

    codigo_exibido = obter_codigo_solicitacao_exibido(solicitacao)
    bloco_titulo = [
        Paragraph("Solicitação de Insumos", estilo_titulo),
        Paragraph(f"<b>Código: {codigo_exibido}</b>", estilo_subtitulo),
    ]

    col_logo = largura_logo + separacao_logo_titulo
    tabela_cabecalho = Table(
        [[logo, bloco_titulo]],
        colWidths=[col_logo, largura_util - col_logo],
    )
    tabela_cabecalho.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Altura da faixa = margem superior + altura do cabeçalho + margem inferior
    _, altura_cabecalho = tabela_cabecalho.wrap(largura_util, 0)
    margem_inferior_faixa = 1.5 * cm
    altura_faixa = doc.topMargin + altura_cabecalho + margem_inferior_faixa

    def desenhar_faixa_cabecalho(canvas, doc_):
        # Só na primeira página, pois o cabeçalho aparece apenas nela
        if canvas.getPageNumber() != 1:
            return
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#eaecf9"))
        canvas.rect(0, A4[1] - altura_faixa, A4[0], altura_faixa, stroke=0, fill=1)
        canvas.restoreState()

    doc.addPageTemplates([
        PageTemplate(id="principal", frames=[frame], onPage=desenhar_faixa_cabecalho)
    ])

    elementos.append(tabela_cabecalho)
    # Sai da faixa colorida (margem inferior) + espaço até o restante do PDF
    elementos.append(Spacer(1, margem_inferior_faixa + 30))

    # ---------------------------------------------------------------
    # Bloco 1
    # ---------------------------------------------------------------
    nome_projeto = obter_nome_projeto_por_id(solicitacao.get("projeto_id"), projetos_dict)

    campos_coluna_esquerda = [
        linha("Projeto", nome_projeto),
        linha("Responsável", obter_nome_responsavel_solicitacao(solicitacao, pessoas_dict)),
        linha("Data Prevista/Desejada de Entrega", solicitacao.get("data_prevista_entrega", "—")),
    ]

    campos_coluna_direita = [linha("Data da Solicitação", solicitacao.get("data_solicitacao", "—"))]
    ultima_edicao = solicitacao.get("ultima_edicao")
    if ultima_edicao:
        campos_coluna_direita.append(linha("Editado em", ultima_edicao))

    col_esquerda_bloco1 = 11 * cm
    col_direita_bloco1 = largura_util - col_esquerda_bloco1

    tabela_bloco1 = Table(
        [[campos_coluna_esquerda, campos_coluna_direita]],
        colWidths=[col_esquerda_bloco1, col_direita_bloco1],
    )
    tabela_bloco1.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elementos.append(tabela_bloco1)

    elementos.append(divisor())

    # ---------------------------------------------------------------
    # Bloco 2: Perguntas personalizadas + identificação da comunidade
    # ---------------------------------------------------------------
    respostas_personalizadas = solicitacao.get("respostas_personalizadas_insumos", [])
    for resposta in respostas_personalizadas:
        opcoes_selecionadas = resposta.get("opcoes_selecionadas", [])
        if opcoes_selecionadas:
            titulo = resposta.get("titulo_pergunta_insumos", "—")
            valor_exibido = ", ".join(opcoes_selecionadas)
            elementos.append(linha(titulo, valor_exibido))

    comunidade = solicitacao.get("identificacao_comunidade", {})
    campos_comunidade = [
        ("Terra Indígena (TI)", comunidade.get("terra_indigena")),
        ("Nome da Aldeia", comunidade.get("nome_aldeia")),
        ("Nome do Grupo/Coletivo", comunidade.get("nome_grupo_coletivo")),
        ("Atividade Produtiva Principal", comunidade.get("atividade_produtiva_principal")),
        ("Nome do responsável do grupo", comunidade.get("nome_responsavel_grupo")),
        ("Nº de Famílias Atendidas", comunidade.get("numero_familias_atendidas")),
    ]
    for rotulo, valor in campos_comunidade:
        if valor not in (None, ""):
            elementos.append(linha(rotulo, valor))

    elementos.append(divisor())

    # ---------------------------------------------------------------
    # Bloco 3: Justificativa
    # ---------------------------------------------------------------
    elementos.append(linha("Justificativa", solicitacao.get("justificativa_objetivos", "—")))
    elementos.append(Spacer(1, 25))

    # ---------------------------------------------------------------
    # Tabela de itens demandados
    # ---------------------------------------------------------------
    itens = solicitacao.get("itens_demandados", [])
    if itens:
        estilo_header_tabela = ParagraphStyle(
            "HeaderTabelaItens", parent=estilo_normal, fontName="Helvetica-Bold", fontSize=9.5,
            textColor=colors.HexColor("#1F1F1F"),
        )
        estilo_celula_tabela = ParagraphStyle(
            "CelulaTabelaItens", parent=estilo_normal, fontSize=9.5, textColor=colors.HexColor("#333333"),
        )

        colunas_cabecalho = ["Item", "Descrição Material/ Equipamento/ Insumo", "Unidade", "Quantidade"]
        dados_tabela = [[Paragraph(c, estilo_header_tabela) for c in colunas_cabecalho]]
        for item in itens:
            dados_tabela.append([
                Paragraph(str(item.get("Item", "—")), estilo_celula_tabela),
                Paragraph(str(item.get("Descrição Material/ Equipamento/ Insumo", "—")), estilo_celula_tabela),
                Paragraph(str(item.get("Unidade", "—")), estilo_celula_tabela),
                Paragraph(str(item.get("Quantidade", "—")), estilo_celula_tabela),
            ])

        col_item = 1.8 * cm
        col_unidade = 4 * cm
        col_quantidade = 2.7 * cm
        col_descricao = largura_util - (col_item + col_unidade + col_quantidade)

        tabela = Table(
            dados_tabela,
            colWidths=[col_item, col_descricao, col_unidade, col_quantidade],
            repeatRows=1,
        )
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#D0D0D0")),
            ("LINEBELOW", (0, 1), (-1, -2), 0.5, colors.HexColor("#E5E5E5")),
        ]))
        elementos.append(tabela)
    else:
        elementos.append(Paragraph("Nenhum item cadastrado.", estilo_normal))

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()


def enviar_email(destinatarios, assunto, corpo, anexo_bytes=None, nome_anexo=None):
    """Envia um e-mail via Gmail SMTP (SSL), com anexo opcional em PDF."""
    if not destinatarios:
        return False

    remetente = st.secrets["senhas"]["endereco_email"]
    senha = st.secrets["senhas"]["senha_email"]

    msg = MIMEMultipart()
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = ", ".join(destinatarios)
    msg.attach(MIMEText(corpo, "html", "utf-8"))

    if anexo_bytes:
        parte_anexo = MIMEApplication(anexo_bytes, _subtype="pdf")
        parte_anexo.add_header("Content-Disposition", "attachment", filename=nome_anexo or "solicitacao.pdf")
        msg.attach(parte_anexo)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, destinatarios, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

def obter_email_pessoa_por_id(pessoa_id):
    """Busca o e-mail de uma pessoa a partir do seu id."""
    if not pessoa_id:
        return None
    pessoa = pessoas.find_one({"_id": ObjectId(pessoa_id)}, {"e_mail": 1})
    return (pessoa or {}).get("e_mail")


def obter_destinatarios_adm(solicitacao):
    """Retorna o(s) e-mail(s) administrativo(s) a notificar, com base no
    campo 'escritorio' do responsável ORIGINAL pela solicitação."""
    responsavel_id = solicitacao.get("responsavel_id")
    if not responsavel_id:
        return []

    pessoa = pessoas.find_one({"_id": ObjectId(responsavel_id)}, {"escritorio": 1})
    escritorio = (pessoa or {}).get("escritorio")

    if escritorio == "Brasília":
        chave = "adm_bsb"
    elif escritorio == "Santa Inês":
        chave = "adm_stai"
    else:
        return []

    email = st.secrets.get("emails_adm", {}).get(chave)
    return [email] if email else []


def enviar_notificacao_solicitacao(solicitacao, tipo, projetos_dict, pessoas_dict):
    """Dispara o e-mail de notificação (Enviado/Editado), com o PDF da
    solicitação em anexo, para o e-mail administrativo do escritório do
    responsável pela solicitação."""

    destinatarios = obter_destinatarios_adm(solicitacao)
    if not destinatarios:
        return

    id_usuario_acao = usuario_id_atual()
    nome_usuario_acao = obter_nome_pessoa_por_id(id_usuario_acao, pessoas_dict)
    email_usuario_acao = obter_email_pessoa_por_id(id_usuario_acao) or "—"
    data_hora_acao = datetime.now().strftime("%d/%m/%Y %H:%M")

    nome_projeto = obter_nome_projeto_por_id(solicitacao.get("projeto_id"), projetos_dict)
    nome_responsavel = obter_nome_responsavel_solicitacao(solicitacao, pessoas_dict)
    verbo = "enviada" if tipo == "Enviado" else "editada"

    assunto = f"[Insumos] Solicitação {verbo} — {nome_projeto}"
    corpo = f"""
    <p>Uma solicitação de insumos foi <b>{verbo}</b> pelo Portal Jataí.</p>

    <p><b>Código:</b> {obter_codigo_solicitacao_exibido(solicitacao)}</p>
    <p><b>Projeto:</b> {nome_projeto}</p>
    
    <p>{tipo} por <b>{nome_usuario_acao}</b> ({email_usuario_acao}) em <b>{data_hora_acao}</b></p>
    """

    pdf_bytes = gerar_pdf_solicitacao(solicitacao, projetos_dict, pessoas_dict)
    codigo_solicitacao_exibido = obter_codigo_solicitacao_exibido(solicitacao)
    nome_arquivo = f"{codigo_solicitacao_exibido}_{sanitizar_nome_arquivo(nome_responsavel)}.pdf"

    enviar_email(destinatarios, assunto, corpo, anexo_bytes=pdf_bytes, nome_anexo=nome_arquivo)


def usuario_tem_acesso_crud(projetos):
    """Define se a aba 'Perguntas Personalizadas' deve aparecer: admin, ou
    coordenador/gestor de ao menos um projeto."""
    if usuario_eh_admin():
        return True
    return any(usuario_eh_gestor_ou_coordenador(p) for p in projetos)


@st.cache_data(ttl=300)
def carregar_projetos():
    """Carrega a lista de projetos com status 'Em andamento' ou 'Estratégico'
    (id, sigla, código, nome, perguntas personalizadas, coordenador e
    gestores — usados no controle de permissões), já ordenada
    alfabeticamente pelo rótulo de exibição (sigla > código > nome)."""
    projetos = list(
        projetos_ispn.find(
            {"status": {"$in": ["Em andamento", "Estratégico"]}},
            {
                "nome_do_projeto": 1,
                "sigla": 1,
                "codigo": 1,
                "perguntas_personalizadas_insumos": 1,
                "coordenador": 1,
                "gestores": 1,
            }
        )
    )
    projetos.sort(key=lambda p: obter_rotulo_projeto(p).lower())
    return projetos


def obter_projeto_por_id(projeto_id):
    return projetos_ispn.find_one({"_id": ObjectId(projeto_id)})


def montar_dict_nomes_projetos(projetos):
    """Monta um dicionário {id_str: rótulo} a partir da lista de projetos já carregada."""
    return {str(p["_id"]): obter_rotulo_projeto(p) for p in projetos}


def obter_nome_projeto_por_id(projeto_id, projetos_dict):
    """Resolve o nome/rótulo do projeto a partir do seu id, usando o dicionário
    em cache; se não encontrar (ex.: cache desatualizado), busca direto no banco."""
    if not projeto_id:
        return "—"
    nome = projetos_dict.get(str(projeto_id))
    if nome:
        return nome
    projeto = obter_projeto_por_id(projeto_id)
    return obter_rotulo_projeto(projeto) if projeto else "—"


def obter_nome_pessoa(pessoa):
    return (pessoa or {}).get("nome_completo") or "—"


@st.cache_data(ttl=300)
def carregar_pessoas():
    """Carrega id e nome completo de todas as pessoas, para exibição do responsável."""
    return list(pessoas.find({}, {"nome_completo": 1}))


def montar_dict_nomes_pessoas(pessoas_lista):
    """Monta um dicionário {id_str: nome_completo} a partir da lista de pessoas já carregada."""
    return {str(p["_id"]): obter_nome_pessoa(p) for p in pessoas_lista}


def obter_nome_pessoa_por_id(pessoa_id, pessoas_dict):
    """Resolve o nome completo da pessoa a partir do seu id, usando o
    dicionário em cache; se não encontrar, busca direto no banco."""
    if not pessoa_id:
        return "—"
    nome = pessoas_dict.get(str(pessoa_id))
    if nome:
        return nome
    pessoa = pessoas.find_one({"_id": ObjectId(pessoa_id)}, {"nome_completo": 1})
    return obter_nome_pessoa(pessoa) if pessoa else "—"


def obter_codigo_solicitacao_exibido(solicitacao):
    """Retorna o código da solicitação sempre com a sigla 'SDI-' antes do
    número, mesmo para registros antigos que tenham sido salvos sem o
    prefixo (o padrão a partir de agora é salvar com ele, mas isso garante
    a exibição correta também nesses casos legados)."""
    codigo = solicitacao.get("codigo_solicitacao")
    if not codigo:
        return "—"
    codigo = str(codigo)
    return codigo if codigo.upper().startswith("SDI-") else f"SDI-{codigo}"


def obter_nome_responsavel_solicitacao(solicitacao, pessoas_dict):
    """Retorna o nome de exibição do responsável pela solicitação: resolve
    pelo responsavel_id quando existir (registros novos); para registros
    antigos (sem responsavel_id), usa o campo legado 'nome_responsavel'."""
    responsavel_id = solicitacao.get("responsavel_id")
    if responsavel_id:
        return obter_nome_pessoa_por_id(responsavel_id, pessoas_dict)
    return solicitacao.get("nome_responsavel", "—")


def obter_perguntas_personalizadas_projeto(projeto):
    """Retorna a lista de perguntas personalizadas de um projeto (dicts com
    _id, titulo_pergunta_insumos e opcoes_resposta_insumos), ordenada
    alfabeticamente pelo título."""
    perguntas = (projeto or {}).get("perguntas_personalizadas_insumos", [])
    return sorted(perguntas, key=lambda p: p.get("titulo_pergunta_insumos", "").lower())


def carregar_solicitacoes():
    """Carrega todas as solicitações de insumos."""
    solicitacoes = list(insumos.find({}).sort("data_solicitacao", -1))
    return solicitacoes


def parse_data_solicitacao(valor):
    """Converte a string 'dd/mm/aaaa' de data_solicitacao em um objeto date.
    Retorna None se o valor estiver ausente ou for inválido."""
    try:
        return datetime.strptime(valor, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def filtrar_solicitacoes_por_data(solicitacoes, data_inicio, data_fim):
    """Filtra a lista de solicitações pelo intervalo [data_inicio, data_fim],
    com base no campo 'data_solicitacao'. Solicitações com data inválida/ausente
    são descartadas quando um filtro está ativo."""
    if not data_inicio or not data_fim:
        return solicitacoes

    filtradas = []
    for solicitacao in solicitacoes:
        data = parse_data_solicitacao(solicitacao.get("data_solicitacao"))
        if data and data_inicio <= data <= data_fim:
            filtradas.append(solicitacao)
    return filtradas


def numerar_itens(df_itens):
    """Recebe um DataFrame de itens (sem a coluna 'Item'), filtra as linhas
    preenchidas e retorna a lista de registros já numerada em ordem (campo 'Item')."""
    itens_preenchidos = df_itens[
        df_itens["Descrição Material/ Equipamento/ Insumo"].astype(str).str.strip().ne("")
    ].reset_index(drop=True)

    registros = []
    for i, linha in itens_preenchidos.iterrows():
        registro = {"Item": i + 1}
        registro.update(linha.to_dict())
        registros.append(registro)

    return registros


###########################################################################################################
# DIÁLOGO DE EDIÇÃO DE PERGUNTA PERSONALIZADA
###########################################################################################################

@st.dialog("Editar Pergunta Personalizada", width="medium")
def dialog_editar_pergunta(projeto_id, pergunta):

    titulo_editado = st.text_input(
        "Qual o título da pergunta?",
        value=pergunta.get("titulo_pergunta_insumos", ""),
        key=f"dialog_editar_pergunta_titulo_{pergunta['_id']}"
    )

    opcoes_atuais = pergunta.get("opcoes_resposta_insumos", [])
    df_opcoes_atual = pd.DataFrame({"Opção de Resposta": pd.array(opcoes_atuais, dtype="string")})

    df_opcoes_editadas = st.data_editor(
        df_opcoes_atual,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_config={
            "Opção de Resposta": st.column_config.TextColumn("Opção de Resposta", width="large"),
        },
        key=f"dialog_editar_pergunta_opcoes_{pergunta['_id']}"
    )

    st.write("")
    col1, col2 = st.columns(2)
    salvar = col1.button(
        "Salvar alterações", type="primary", icon=":material/save:", width="stretch",
        key=f"dialog_editar_pergunta_salvar_{pergunta['_id']}"
    )
    excluir = col2.button(
        "Excluir pergunta", icon=":material/delete:", width="stretch",
        key=f"dialog_editar_pergunta_excluir_{pergunta['_id']}"
    )

    key_confirmar_exclusao = f"confirmar_exclusao_pergunta_{pergunta['_id']}"

    if salvar:
        
        if not titulo_editado or not titulo_editado.strip():
            st.error("Informe o título da pergunta.")
        else:
            opcoes_registradas = sorted(
                {
                    o.strip() for o in df_opcoes_editadas["Opção de Resposta"].tolist()
                    if isinstance(o, str) and o.strip()
                },
                key=str.lower
            )
            if not opcoes_registradas:
                st.error("Informe ao menos uma opção de resposta.")
            else:

                projetos_ispn.update_one(
                    {"_id": ObjectId(projeto_id), "perguntas_personalizadas_insumos._id": pergunta["_id"]},
                    {"$set": {
                        "perguntas_personalizadas_insumos.$.titulo_pergunta_insumos": titulo_editado.strip(),
                        "perguntas_personalizadas_insumos.$.opcoes_resposta_insumos": opcoes_registradas,
                    }}
                )
                st.success("Pergunta atualizada com sucesso!", icon=":material/check:")
                time.sleep(2)
                st.cache_data.clear()
                st.rerun()

    if excluir:
        st.session_state[key_confirmar_exclusao] = True

    if st.session_state.get(key_confirmar_exclusao):
        st.write("")
        st.write("")
        
        st.warning("Tem certeza que deseja excluir esta pergunta? Essa ação não pode ser desfeita.")
        if st.button(
            "Confirmar exclusão", icon=":material/delete_forever:", type="primary",
            width="content",
            key=f"dialog_editar_pergunta_confirmar_excluir_{pergunta['_id']}"
        ):
            projetos_ispn.update_one(
                {"_id": ObjectId(projeto_id)},
                {"$pull": {"perguntas_personalizadas_insumos": {"_id": pergunta["_id"]}}}
            )
            
            st.session_state.pop(key_confirmar_exclusao, None)
            
            st.success("Pergunta excluída com sucesso!", icon=":material/check:")
            time.sleep(2)
            st.cache_data.clear()
            st.rerun()


###########################################################################################################
# DIÁLOGO DE DETALHES DA SOLICITAÇÃO
###########################################################################################################

@st.dialog("Detalhes da Solicitação", width="large")
def dialog_detalhes(solicitacao, projetos, projetos_dict, pessoas_dict):

    projeto_da_solicitacao = next(
        (p for p in projetos if str(p["_id"]) == str(solicitacao.get("projeto_id"))), None
    )
    pode_editar = usuario_pode_editar_solicitacao(solicitacao, projeto_da_solicitacao)

    if pode_editar:
        with st.container(horizontal=True, horizontal_alignment="right"):
            editar = st.toggle("Editar", key=f"insumos_toggle_editar_{solicitacao['_id']}")
    else:
        editar = False

    st.write("")

    # -------------------- MODO VISUALIZAÇÃO --------------------
    if not editar:

        st.write("")
        st.write("")

        nome_projeto = obter_nome_projeto_por_id(solicitacao.get("projeto_id"), projetos_dict)

        col1, col2, col3 = st.columns(3)
        col1.write(f"**Código:** {obter_codigo_solicitacao_exibido(solicitacao)}")
        col2.write(f"**Projeto:** {nome_projeto}")
        col3.write(f"**Responsável:** {obter_nome_responsavel_solicitacao(solicitacao, pessoas_dict)}")

        st.divider()

        ultima_edicao = solicitacao.get("ultima_edicao")
        if ultima_edicao:
            col1, col2, col3 = st.columns(3)
            col1.markdown(f"**Data da Solicitação:** {solicitacao.get('data_solicitacao', '—')}")
            col2.markdown(f"**Editado em:** {ultima_edicao}")
            col3.markdown(f"**Data Prevista/Desejada de Entrega:** {solicitacao.get('data_prevista_entrega', '—')}")
        else:
            col1, col2, col3 = st.columns(3)
            col1.markdown(f"**Data da Solicitação:** {solicitacao.get('data_solicitacao', '—')}")
            col2.markdown(f"**Data Prevista/Desejada de Entrega:** {solicitacao.get('data_prevista_entrega', '—')}")

        st.divider()

        comunidade = solicitacao.get("identificacao_comunidade", {})
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Terra Indígena (TI):** {comunidade.get('terra_indigena') or '—'}")
        col2.markdown(f"**Nome da Aldeia:** {comunidade.get('nome_aldeia') or '—'}")
        col3.markdown(f"**Nome do Grupo/Coletivo:** {comunidade.get('nome_grupo_coletivo') or '—'}")
        col1.markdown(f"**Atividade Produtiva Principal:** {comunidade.get('atividade_produtiva_principal') or '—'}")
        col2.markdown(f"**Nome do responsável do grupo:** {comunidade.get('nome_responsavel_grupo') or '—'}")
        col3.markdown(f"**Nº de Famílias Atendidas:** {comunidade.get('numero_familias_atendidas') or '—'}")

        st.divider()

        respostas_personalizadas = solicitacao.get("respostas_personalizadas_insumos", [])
        if respostas_personalizadas:
            for resposta in respostas_personalizadas:
                titulo = resposta.get("titulo_pergunta_insumos", "—")
                opcoes_selecionadas = resposta.get("opcoes_selecionadas", [])
                valor_exibido = ", ".join(opcoes_selecionadas) if opcoes_selecionadas else "—"
                st.markdown(f"**{titulo}:** {valor_exibido}")

            st.divider()

        st.write(f"**Justificativa:** {solicitacao.get('justificativa_objetivos', '—')}")

        st.divider()

        st.write(f"**Especificação dos Itens Demandados:**")
        itens = solicitacao.get("itens_demandados", [])
        if itens:
            df_itens = pd.DataFrame(itens)
            # Garante que a coluna "Item" (quando existir) apareça primeiro
            if "Item" in df_itens.columns:
                colunas = ["Item"] + [c for c in df_itens.columns if c != "Item"]
                df_itens = df_itens[colunas]
            st.dataframe(df_itens, hide_index=True, width="stretch")
        else:
            st.write("Nenhum item cadastrado.")

    else:

        # -------------------- MODO EDIÇÃO --------------------
        # O código da solicitação (codigo_solicitacao) NÃO é exibido nem
        # editável neste formulário — é imutável após a criação da
        # solicitação e nunca é sobrescrito pelo update abaixo, pois não
        # faz parte do $set.
        opcoes_projetos = {str(p["_id"]): obter_rotulo_projeto(p) for p in projetos}
        projetos_dict = montar_dict_nomes_projetos(projetos) 
        ids_projetos = list(opcoes_projetos.keys())
        projeto_id_atual = str(solicitacao.get("projeto_id"))
        indice_projeto_atual = ids_projetos.index(projeto_id_atual) if projeto_id_atual in ids_projetos else None

        # Perguntas personalizadas cadastradas para o projeto atual da solicitação.
        # Como o selectbox de projeto fica dentro do form (só reage ao submit),
        # a lista de perguntas exibida aqui é a do projeto já vinculado à
        # solicitação; se o projeto for trocado, as respostas devem ser conferidas
        # novamente após salvar.
        projeto_atual_obj = next((p for p in projetos if str(p["_id"]) == projeto_id_atual), None)
        perguntas_projeto_editar = obter_perguntas_personalizadas_projeto(projeto_atual_obj)

        # Respostas já registradas na solicitação, indexadas pelo id da pergunta,
        # para pré-preencher os multiselects.
        respostas_atuais_dict = {
            str(r.get("pergunta_id")): r.get("opcoes_selecionadas", [])
            for r in solicitacao.get("respostas_personalizadas_insumos", [])
        }

        with st.form(f"insumos_form_editar_{solicitacao['_id']}", border=False):

            projeto_id_editado = st.selectbox(
                "Projeto*",
                options=ids_projetos,
                format_func=lambda x: opcoes_projetos.get(x, x),
                index=indice_projeto_atual,
                key=f"insumos_editar_projeto_{solicitacao['_id']}"
            )

            respostas_personalizadas_editadas = {}
            if perguntas_projeto_editar:
                for pergunta in perguntas_projeto_editar:
                    
                    pergunta_id_str = str(pergunta["_id"])
                    valor_padrao = [
                        o for o in respostas_atuais_dict.get(pergunta_id_str, [])
                        if o in pergunta.get("opcoes_resposta_insumos", [])
                    ]
                    
                    opcoes_selecionadas_editadas = st.multiselect(
                        pergunta.get("titulo_pergunta_insumos", ""),
                        options=pergunta.get("opcoes_resposta_insumos", []),
                        default=valor_padrao,
                        key=f"insumos_editar_pergunta_{solicitacao['_id']}_{pergunta_id_str}",
                    )
                    
                    respostas_personalizadas_editadas[pergunta_id_str] = {
                        "pergunta_id": pergunta["_id"],
                        "titulo_pergunta_insumos": pergunta.get("titulo_pergunta_insumos", ""),
                        "opcoes_selecionadas": opcoes_selecionadas_editadas,
                    }
            else:
                st.caption("Este projeto não possui perguntas personalizadas cadastradas.")

            data_prevista_atual = solicitacao.get("data_prevista_entrega", "")
            try:
                valor_data_prevista = datetime.strptime(data_prevista_atual, "%d/%m/%Y").date()
            except (ValueError, TypeError):
                valor_data_prevista = None

            data_prevista_editada = st.date_input(
                "Data Prevista/Desejada para Entrega*",
                value=valor_data_prevista,
                format="DD/MM/YYYY",
                key=f"insumos_editar_data_prevista_{solicitacao['_id']}"
            )

            st.write("")

            comunidade = solicitacao.get("identificacao_comunidade", {})
            col1, col2 = st.columns(2)
            terra_indigena_editada = col1.text_input(
                "Terra Indígena (TI)", value=comunidade.get("terra_indigena", ""),
                key=f"insumos_editar_ti_{solicitacao['_id']}"
            )
            nome_aldeia_editada = col2.text_input(
                "Nome da Aldeia", value=comunidade.get("nome_aldeia", ""),
                key=f"insumos_editar_aldeia_{solicitacao['_id']}"
            )

            col1, col2 = st.columns(2)
            nome_grupo_coletivo_editado = col1.text_input(
                "Nome do Grupo/Coletivo", value=comunidade.get("nome_grupo_coletivo", ""),
                key=f"insumos_editar_grupo_{solicitacao['_id']}"
            )
            atividade_produtiva_editada = col2.text_input(
                "Atividade Produtiva Principal", value=comunidade.get("atividade_produtiva_principal", ""),
                key=f"insumos_editar_atividade_{solicitacao['_id']}"
            )

            col1, col2 = st.columns(2)
            nome_responsavel_grupo_editado = col1.text_input(
                "Nome do responsável do grupo", value=comunidade.get("nome_responsavel_grupo", ""),
                key=f"insumos_editar_resp_grupo_{solicitacao['_id']}"
            )
            numero_familias_editado = col2.text_input(
                "Nº de Famílias Atendidas diretamente", value=comunidade.get("numero_familias_atendidas", ""),
                key=f"insumos_editar_familias_{solicitacao['_id']}"
            )

            st.write("")
            justificativa_editada = st.text_area(
                "Descreva de forma sucinta qual a finalidade deste fomento*",
                value=solicitacao.get("justificativa_objetivos", ""),
                key=f"insumos_editar_justificativa_{solicitacao['_id']}"
            )

            st.write("")

            itens_atuais = solicitacao.get("itens_demandados", [])
            df_itens_atual = pd.DataFrame(itens_atuais) if itens_atuais else pd.DataFrame(
                columns=["Descrição Material/ Equipamento/ Insumo", "Unidade", "Quantidade"]
            )
            if "Item" in df_itens_atual.columns:
                df_itens_atual = df_itens_atual.drop(columns=["Item"])
            for coluna in ["Descrição Material/ Equipamento/ Insumo", "Unidade", "Quantidade"]:
                if coluna not in df_itens_atual.columns:
                    df_itens_atual[coluna] = None

            st.write("**Especificação dos Itens Demandados:**")

            df_itens_editados = st.data_editor(
                df_itens_atual,
                num_rows="dynamic",
                hide_index=True,
                width="stretch",
                column_config={
                    "Descrição Material/ Equipamento/ Insumo": st.column_config.TextColumn("Descrição Material/ Equipamento/ Insumo"),
                    "Unidade": st.column_config.TextColumn("Unidade"),
                    "Quantidade": st.column_config.NumberColumn("Quantidade"),
                },
                key=f"insumos_editar_data_editor_{solicitacao['_id']}"
            )

            st.write("")
            salvar = st.form_submit_button("Salvar alterações", type="primary", width="content", icon=":material/save:")

        if salvar:
            erros = []

            if not projeto_id_editado:
                erros.append("Selecione o projeto.")

            if not data_prevista_editada:
                erros.append("Informe a Data Prevista/Desejada para Entrega.")

            if not justificativa_editada or not justificativa_editada.strip():
                erros.append("A Justificativa e Objetivos da Demanda é obrigatória.")

            itens_registrados = numerar_itens(df_itens_editados)
            if not itens_registrados:
                erros.append("Informe ao menos um item na tabela de Especificação dos Itens Demandados.")

            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                # Observação: "codigo_solicitacao" propositalmente não está
                # neste $set — o código é gerado uma única vez, na criação
                # da solicitação, e permanece imutável em edições futuras.
                # "ultima_edicao" registra a data e hora desta edição, para
                # ser exibida como "Editado em:" tanto no diálogo de
                # detalhes quanto no PDF gerado.
                with st.spinner(text="Salvando alterações..."):
                    insumos.update_one(
                        {"_id": solicitacao["_id"]},
                        {"$set": {
                            "projeto_id": ObjectId(projeto_id_editado),
                            "respostas_personalizadas_insumos": list(respostas_personalizadas_editadas.values()),
                            "data_prevista_entrega": data_prevista_editada.strftime("%d/%m/%Y"),
                            "identificacao_comunidade": {
                                "terra_indigena": terra_indigena_editada,
                                "nome_aldeia": nome_aldeia_editada,
                                "nome_grupo_coletivo": nome_grupo_coletivo_editado,
                                "atividade_produtiva_principal": atividade_produtiva_editada,
                                "nome_responsavel_grupo": nome_responsavel_grupo_editado,
                                "numero_familias_atendidas": numero_familias_editado,
                            },
                            "justificativa_objetivos": justificativa_editada,
                            "itens_demandados": itens_registrados,
                            "ultima_edicao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        }}
                    )

                    solicitacao_atualizada = insumos.find_one({"_id": solicitacao["_id"]})
                    enviar_notificacao_solicitacao(solicitacao_atualizada, "Editado", projetos_dict, pessoas_dict)
                    st.success("Solicitação atualizada com sucesso!", icon=":material/check:")
                    time.sleep(2)
                    st.rerun()


###########################################################################################################
# ABAS PRINCIPAIS
###########################################################################################################


projetos_geral = carregar_projetos()

nomes_abas = [":material/list: Solicitações", ":material/add: Nova Solicitação"]
if usuario_tem_acesso_crud(projetos_geral):
    nomes_abas.append(":material/quiz: Perguntas Personalizadas")

abas = st.tabs(nomes_abas)


###########################################################################################################
# ABA 1 — LISTAGEM DE SOLICITAÇÕES
###########################################################################################################

with abas[0]:

    solicitacoes = carregar_solicitacoes()
    projetos_lista = carregar_projetos()
    projetos_dict = montar_dict_nomes_projetos(projetos_lista)
    pessoas_lista = carregar_pessoas()
    pessoas_dict = montar_dict_nomes_pessoas(pessoas_lista)

    if not solicitacoes:

        st.write("")
        st.write("")
        st.caption("**Nenhuma solicitação de insumos cadastrada até o momento.**")

    else:

        st.write("")
        st.write("")

        col_filtro, _ = st.columns([2, 3])
        intervalo_data_solicitacao = col_filtro.date_input(
            "Data da Solicitação",
            value=(),
            format="DD/MM/YYYY",
            key="insumos_filtro_data_solicitacao"
        )

        data_inicio_filtro = None
        data_fim_filtro = None
        if isinstance(intervalo_data_solicitacao, tuple) and len(intervalo_data_solicitacao) == 2:
            data_inicio_filtro, data_fim_filtro = intervalo_data_solicitacao

        solicitacoes = filtrar_solicitacoes_por_data(solicitacoes, data_inicio_filtro, data_fim_filtro)

        st.write("")
        st.write("")

        if not solicitacoes:
            st.caption("**Nenhuma solicitação encontrada para o período selecionado.**")
        else:
            col_codigo, col_proj, col_resp, col_data_sol, col_data_ent, col_botao = st.columns([1, 2, 2, 2, 2, 2])
            col_codigo.markdown("**Código**")
            col_proj.markdown("**Projeto**")
            col_resp.markdown("**Responsável**")
            col_data_sol.markdown("**Data da Solicitação**")
            col_data_ent.markdown("**Data Prevista de Entrega**")
            col_botao.markdown("")

            st.divider()

            for solicitacao in solicitacoes:
                col_codigo, col_proj, col_resp, col_data_sol, col_data_ent, col_botao = st.columns([1, 2, 2, 2, 2, 2])
                col_codigo.write(obter_codigo_solicitacao_exibido(solicitacao))
                col_proj.write(obter_nome_projeto_por_id(solicitacao.get("projeto_id"), projetos_dict))
                col_resp.write(obter_nome_responsavel_solicitacao(solicitacao, pessoas_dict))
                col_data_sol.write(solicitacao.get("data_solicitacao", "—"))
                col_data_ent.write(solicitacao.get("data_prevista_entrega", "—"))

                if col_botao.button("Detalhes", key=f"detalhes_{solicitacao['_id']}", icon=":material/info:"):
                    dialog_detalhes(solicitacao, projetos_lista, projetos_dict, pessoas_dict)

                st.divider()


###########################################################################################################
# ABA 2 — FORMULÁRIO DE NOVA SOLICITAÇÃO
###########################################################################################################

with abas[1]:

    st.write("")
    st.write("")

    projetos = carregar_projetos()
    opcoes_projetos = {str(p["_id"]): obter_rotulo_projeto(p) for p in projetos}
    projetos_dict = montar_dict_nomes_projetos(projetos) 
    pessoas_lista = carregar_pessoas()
    pessoas_dict = montar_dict_nomes_pessoas(pessoas_lista)

    st.markdown("##### 1. Identificação Geral")
    st.write("")
    
    col1, col2 = st.columns(2)

    projeto_id_selecionado = col1.selectbox(
        "Projeto*",
        options=list(opcoes_projetos.keys()),
        format_func=lambda x: opcoes_projetos.get(x, x),
        index=None,
        placeholder="Selecione o projeto",
        key="insumos_projeto_selecionado"
    )

    # Ao selecionar o projeto, exibe um multiselect para cada pergunta
    # personalizada cadastrada para ele (ordenadas alfabeticamente). Caso o
    # projeto não tenha nenhuma pergunta personalizada cadastrada, apenas um
    # aviso é exibido.
    respostas_personalizadas_novas = {}
    if projeto_id_selecionado:
        projeto_atual = next((p for p in projetos if str(p["_id"]) == projeto_id_selecionado), None)
        perguntas_projeto = obter_perguntas_personalizadas_projeto(projeto_atual)

        if perguntas_projeto:
            for pergunta in perguntas_projeto:
                
                pergunta_id_str = str(pergunta["_id"])
                
                opcoes_selecionadas = st.multiselect(
                    pergunta.get("titulo_pergunta_insumos", ""),
                    options=pergunta.get("opcoes_resposta_insumos", []),
                    key=f"insumos_pergunta_{projeto_id_selecionado}_{pergunta_id_str}",
                    placeholder=""
                )
                
                respostas_personalizadas_novas[pergunta_id_str] = {
                    "pergunta_id": pergunta["_id"],
                    "titulo_pergunta_insumos": pergunta.get("titulo_pergunta_insumos", ""),
                    "opcoes_selecionadas": opcoes_selecionadas,
                }
                


    st.write("")

    with st.form("form_nova_solicitacao_insumos", border=False):

        id_usuario_solicitante = usuario_id_atual()
        nome_responsavel_exibido = obter_nome_pessoa_por_id(id_usuario_solicitante, pessoas_dict)
        data_solicitacao = datetime.now().strftime("%d/%m/%Y")

        col1, col2 = st.columns(2)
        col1.text_input("Nome do Responsável pela Solicitação", value=nome_responsavel_exibido, disabled=True)
        col2.text_input("Data da Solicitação", value=data_solicitacao, disabled=True)

        with col1:
            data_prevista_entrega = date_picker(
                label="Data Prevista/Desejada para Entrega*",
                format="dd/MM/yyyy",
                locale="pt_BR",
                placeholder="dd/mm/aaaa",
                one_tap=True,
                key="insumos_data_prevista_entrega"
            )

        st.divider()
        st.markdown("##### 2. Identificação da Comunidade Beneficiária")
        st.write("")

        col1, col2 = st.columns(2)
        terra_indigena = col1.text_input("Terra Indígena (TI)", key="insumos_terra_indigena")
        nome_aldeia = col2.text_input("Nome da Aldeia", key="insumos_nome_aldeia")

        col1, col2 = st.columns(2)
        nome_grupo_coletivo = col1.text_input("Nome do Grupo/Coletivo", key="insumos_nome_grupo_coletivo")
        atividade_produtiva_principal = col2.text_input("Atividade Produtiva Principal", key="insumos_atividade_produtiva")

        col1, col2 = st.columns(2)
        nome_responsavel_grupo = col1.text_input("Nome do responsável do grupo", key="insumos_nome_responsavel_grupo")
        numero_familias_atendidas = col2.text_input("Nº de Famílias Atendidas diretamente", key="insumos_numero_familias")

        st.divider()
        st.markdown("##### 3. Justificativa e Objetivos da Demanda")
        st.write("")

        justificativa_objetivos = st.text_area(
            "Descreva de forma sucinta qual a finalidade deste fomento*",
            key="insumos_justificativa"
        )

        st.divider()
        st.markdown("##### 4. Especificação dos Itens Demandados")
        st.write("")

        df_itens_vazio = pd.DataFrame(
            [{"Descrição Material/ Equipamento/ Insumo": "", "Unidade": "", "Quantidade": None} for _ in range(6)]
        )

        # st.data_editor com num_rows="dynamic" funciona normalmente dentro de um
        # st.form: é possível adicionar e remover linhas livremente, e o valor
        # final só é enviado ao script quando o formulário é submetido.
        # A coluna "Item" não é editável pelo usuário: o número é atribuído
        # automaticamente, em ordem, no momento de salvar.
        df_itens = st.data_editor(
            df_itens_vazio,
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            column_config={
                "Descrição Material/ Equipamento/ Insumo": st.column_config.TextColumn("Descrição Material/ Equipamento/ Insumo"),
                "Unidade": st.column_config.TextColumn("Unidade"),
                "Quantidade": st.column_config.NumberColumn("Quantidade"),
            },
            key="insumos_data_editor_itens"
        )

        st.write("")
        enviar = st.form_submit_button("Enviar Solicitação", type="primary", width="content", icon=":material/send:")


    if enviar:
        with st.spinner(text="Enviando solicitação..."):
            erros = []

            if not projeto_id_selecionado:
                erros.append("Selecione o projeto.")

            if not data_prevista_entrega:
                erros.append("Informe a Data Prevista/Desejada para Entrega.")

            if not justificativa_objetivos or not justificativa_objetivos.strip():
                erros.append("A Justificativa e Objetivos da Demanda é obrigatória.")

            itens_registrados = numerar_itens(df_itens)
            if not itens_registrados:
                erros.append("Informe ao menos um item na tabela de Especificação dos Itens Demandados.")

            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                # O código é gerado de forma atômica (via find_one_and_update
                # sobre o contador dedicado na coleção "contadores") apenas
                # neste momento, no instante do envio — evitando que duas
                # solicitações concorrentes recebam o mesmo código, e
                # garantindo que o código nunca se repita mesmo que
                # solicitações sejam excluídas depois.
                codigo_solicitacao = gerar_codigo_solicitacao()

                novo_documento = {
                    "codigo_solicitacao": codigo_solicitacao,
                    "projeto_id": ObjectId(projeto_id_selecionado),
                    "respostas_personalizadas_insumos": list(respostas_personalizadas_novas.values()),
                    "responsavel_id": ObjectId(id_usuario_solicitante) if id_usuario_solicitante else None,
                    "data_solicitacao": data_solicitacao,
                    "data_prevista_entrega": data_prevista_entrega.strftime("%d/%m/%Y"),
                    "identificacao_comunidade": {
                        "terra_indigena": terra_indigena,
                        "nome_aldeia": nome_aldeia,
                        "nome_grupo_coletivo": nome_grupo_coletivo,
                        "atividade_produtiva_principal": atividade_produtiva_principal,
                        "nome_responsavel_grupo": nome_responsavel_grupo,
                        "numero_familias_atendidas": numero_familias_atendidas,
                    },
                    "justificativa_objetivos": justificativa_objetivos,
                    "itens_demandados": itens_registrados,
                }

                resultado_insercao = insumos.insert_one(novo_documento)
                novo_documento["_id"] = resultado_insercao.inserted_id
                enviar_notificacao_solicitacao(novo_documento, "Enviado", projetos_dict, pessoas_dict)

                st.success("Solicitação enviada com sucesso!", icon=":material/check:")
                time.sleep(2)
                st.cache_data.clear()
                st.rerun()


###########################################################################################################
# ABA 3 — CRUD DE PERGUNTAS PERSONALIZADAS (restrita a admin e coordenador(a))
###########################################################################################################

if usuario_tem_acesso_crud(projetos_geral):
    with abas[2]:

        st.write("")
        st.write("")

        projetos_crud = carregar_projetos()
        projetos_crud_permitidos = projetos_permitidos_para_perguntas(projetos_crud)
        opcoes_projetos_crud = {str(p["_id"]): obter_rotulo_projeto(p) for p in projetos_crud_permitidos}

        projeto_id_crud = st.selectbox(
            "Projeto",
            options=list(opcoes_projetos_crud.keys()),
            format_func=lambda x: opcoes_projetos_crud.get(x, x),
            index=None,
            placeholder="Selecione o projeto",
            key="crud_projeto_selecionado",
            width=400
        )

        if projeto_id_crud:

            projeto_crud = obter_projeto_por_id(projeto_id_crud)

            if not usuario_pode_gerenciar_perguntas(projeto_crud):
                st.error("Você não tem permissão para gerenciar as perguntas deste projeto.")
            else:
                perguntas_atuais = obter_perguntas_personalizadas_projeto(projeto_crud)

            st.write("")

            key_titulo_nova_pergunta = f"crud_titulo_nova_pergunta_{projeto_id_crud}"
            key_data_editor_nova_pergunta = f"crud_data_editor_nova_pergunta_{projeto_id_crud}"

            with st.expander("Cadastrar nova pergunta", expanded=False, icon=":material/add:"):
                

                titulo_nova_pergunta = st.text_input(
                    "Qual o título da pergunta?",
                    key=key_titulo_nova_pergunta
                )

                if titulo_nova_pergunta and titulo_nova_pergunta.strip():

                    df_opcoes_vazio = pd.DataFrame({"Opção de Resposta": pd.array([], dtype="string")})

                    df_opcoes_nova_pergunta = st.data_editor(
                        df_opcoes_vazio,
                        num_rows="dynamic",
                        hide_index=True,
                        width="stretch",
                        column_config={
                            "Opção de Resposta": st.column_config.TextColumn("Opção de Resposta", width="large"),
                        },
                        key=key_data_editor_nova_pergunta
                    )

                    st.write("")
                    if st.button(
                        "Cadastrar pergunta", type="primary", icon=":material/save:",
                        key=f"crud_botao_cadastrar_{projeto_id_crud}"
                    ):
                        opcoes_registradas = sorted(
                            {
                                o.strip() for o in df_opcoes_nova_pergunta["Opção de Resposta"].tolist()
                                if isinstance(o, str) and o.strip()
                            },
                            key=str.lower
                        )

                        if not opcoes_registradas:
                            st.error("Informe ao menos uma opção de resposta.")
                        else:
                            nova_pergunta = {
                                "_id": ObjectId(),
                                "titulo_pergunta_insumos": titulo_nova_pergunta.strip(),
                                "opcoes_resposta_insumos": opcoes_registradas,
                            }
                            projetos_ispn.update_one(
                                {"_id": ObjectId(projeto_id_crud)},
                                {"$push": {"perguntas_personalizadas_insumos": nova_pergunta}}
                            )
                            st.success("Pergunta cadastrada com sucesso!", icon=":material/check:")
                            # Limpa os campos de cadastro antes do rerun, para que o
                            # formulário volte vazio e pronto para uma nova pergunta.
                            st.session_state.pop(key_titulo_nova_pergunta, None)
                            st.session_state.pop(key_data_editor_nova_pergunta, None)
                            time.sleep(2)
                            st.cache_data.clear()
                            st.rerun()

            st.write("")
            st.markdown("**Perguntas cadastradas**")
            st.write("")

            if not perguntas_atuais:
                st.caption("Este projeto ainda não possui nenhuma pergunta personalizada cadastrada.")
            else:
                st.markdown(
                    """
                    <style>
                    /* Container "linha": permite quebrar para a linha de baixo */
                    .st-key-crud_container_perguntas {
                        flex-wrap: wrap !important;
                        row-gap: 1rem;
                    }

                    /* Cada card: largura fixa de 250px, sem esticar nem encolher */
                    .st-key-crud_container_perguntas > div[data-testid="stVerticalBlockBorderWrapper"] {
                        flex: 0 0 250px !important;
                        width: 250px !important;
                        max-width: 250px !important;
                        min-width: 250px !important;
                    }

                    /* Texto das opções de resposta: nunca ultrapassa a largura do card */
                    .st-key-crud_container_perguntas [data-testid="stMarkdownContainer"] p,
                    .st-key-crud_container_perguntas [data-testid="stMarkdownContainer"] li,
                    .st-key-crud_container_perguntas [data-testid="stMarkdownContainer"] ul {
                        overflow-wrap: break-word;
                        word-break: break-word;
                        white-space: normal;
                        max-width: 100%;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                with st.container(horizontal=True, key="crud_container_perguntas"):
                    for pergunta in perguntas_atuais:
                        with st.container(width=250, border=True):
                            col_titulo, col_botao = st.columns([9, 1])
                            col_titulo.markdown(f"**{pergunta.get('titulo_pergunta_insumos', '—')}**")

                            if col_botao.button(
                                "", icon=":material/edit:",
                                key=f"crud_botao_editar_{pergunta['_id']}",
                                type="tertiary",
                                width="content",
                            ):
                                dialog_editar_pergunta(projeto_id_crud, pergunta)

                            opcoes = pergunta.get("opcoes_resposta_insumos", [])
                            if opcoes:
                                st.markdown("\n".join(f"- {opcao}" for opcao in opcoes))
                            else:
                                st.caption("Nenhuma opção de resposta cadastrada.")
