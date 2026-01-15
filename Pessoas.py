import streamlit as st
import pandas as pd 
import plotly.express as px
import datetime
from bson import ObjectId
import time
from funcoes_auxiliares import conectar_mongo_portal_ispn
import smtplib
from email.mime.text import MIMEText
import datetime as dt


# Configura a página do Streamlit para layout mais amplo
st.set_page_config(layout="wide")

# Exibe o logo do ISPN na página
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

# Cabeçalho da página
st.header("Pessoas")
st.write('')  # Espaço vazio



######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################

# Conecta no banco MongoDB usando função auxiliar
db = conectar_mongo_portal_ispn()

# Carrega as coleções
estatistica = db["estatistica"] 
pessoas = db["pessoas"]  
programas_areas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_pessoas"
nome_pagina = "Pessoas"

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
# TRATAMENTO DOS DADOS
######################################################################################################


# Carrega todos os documentos das coleções
dados_pessoas = list(pessoas.find())
dados_programas = list(programas_areas.find())
dados_projetos_ispn = list(projetos_ispn.find())


# PESSOAS

pessoas_lista = []

for pessoa in dados_pessoas:
    # ----------------------
    # Programa/Área
    # ----------------------
    ids_programa_area = pessoa.get("programa_area", [])

    # Compatibilidade caso ainda exista dado antigo (ObjectId único)
    if not isinstance(ids_programa_area, list):
        ids_programa_area = [ids_programa_area] if ids_programa_area else []

    nomes_programas = [
        p.get("nome_programa_area", "")
        for p in dados_programas
        if p["_id"] in ids_programa_area
    ]

    nome_programa_area = ", ".join(sorted(nomes_programas)) if nomes_programas else "Não informado"

    # ----------------------
    # Projetos pagadores (contratos em vigência)
    # ----------------------
    nomes_projetos_pagadores = []
    contratos = pessoa.get("contratos", [])

    for contrato in contratos:
        if contrato.get("status_contrato") == "Em vigência":
            for proj_id in contrato.get("projeto_pagador", []):
                nome_proj = next(
                    (p.get("sigla", "") for p in dados_projetos_ispn if p["_id"] == proj_id),
                    "Não informado"
                )
                nomes_projetos_pagadores.append(nome_proj)


    # ----------------------
    # Montar registro da pessoa
    # ----------------------
    pessoas_lista.append({
        "Nome": pessoa.get("nome_completo", ""),
        "Programa/Área": nome_programa_area,
        "Projeto Pagador": ", ".join(nomes_projetos_pagadores) if nomes_projetos_pagadores else "",
        "Cargo": pessoa.get("cargo", ""),
        "Escolaridade": pessoa.get("escolaridade", ""),
        "E-mail": pessoa.get("e_mail", ""),
        "Telefone": pessoa.get("telefone", ""),
        "Gênero": pessoa.get("gênero", ""),
        "Raça": pessoa.get("raca", ""),
        "Status": pessoa.get("status", ""),
        "Tipo Contratação": pessoa.get("tipo_contratacao", ""),
        "Escritório": pessoa.get("escritorio", ""),
        "Data de nascimento": pessoa.get("data_nascimento", ""),
    })


# Criar DataFrame de Pessoas
df_pessoas = pd.DataFrame(pessoas_lista)


# PROJETOS
# Filtra só os projetos em que a sigla não está vazia
dados_projetos_ispn = [projeto for projeto in dados_projetos_ispn if projeto["sigla"] != ""]



######################################################################################################
# FUNÇÕES
######################################################################################################

# Obter mês atual em português
meses_pt = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]


# Cargo
opcoes_cargos = [
    "Analista de advocacy", "Analista de comunicação", "Analista de dados", "Analista Administrativo/Financeiro",
    "Analista de Recursos Humanos", "Analista socioambiental", "Analista socioambiental pleno", "Analista socioambiental sênior",
    "Assessora de advocacy", "Assessor de Comunicação", "Auxiliar de Serviços Gerais", "Auxiliar Administrativo/financeiro",
    "Assistente Administrativo/financeiro", "Assistente socioambiental", "Coordenador Administrativo/financeiro de escritório",
    "Coordenador Geral administrativo/financeiro", "Coordenador Executivo", "Coordenador de Área", "Coordenador de Programa", "Estagiário",
    "Motorista", "Secretária(o)/Recepcionista", "Técnico de campo", "Técnico em informática"
]


# Função para enviar e-mail de registro da previdência
def enviar_email(destinatario: str, nome: str, valor_contribuicao: float) -> bool:
    """
    Envia um e-mail de notificação de contribuição à previdência.

    Parâmetros:
    - destinatario: e-mail do destinatário
    - nome: nome do beneficiário
    - valor_contribuicao: valor da contribuição (float)

    Retorna:
    - True se enviado com sucesso, False caso ocorra erro
    """

    # Dados de autenticação do secrets.toml
    remetente = st.secrets["senhas"]["endereco_email"]
    senha = st.secrets["senhas"]["senha_email"]

    # Formata o valor da contribuição no padrão brasileiro
    valor_str = format(valor_contribuicao, ",.2f").replace(",", "X").replace(".", ",").replace("X", ".")

    # Assunto do e-mail
    assunto = "Confirmação de Contribuição - Previdência Privada"

    # Corpo HTML do e-mail

    corpo = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Confirmação de Contribuição</title>
    </head>
    <body style="font-size: 16px; font-family: Arial, sans-serif; background-color: #ffffff; padding: 20px; color: #333;">

        <!-- Cabeçalho com Logo -->
        <div style="text-align: center; margin-bottom: 30px;">
            <img src="https://ispn.org.br/site/wp-content/uploads/2021/04/logo_ISPN_2021.png"
                alt="ISPN Logo"
                style="max-width: 150px; margin-bottom: 40px; margin-top: 10px;">
            <h3 style="color: #004d40;">Confirmação de Contribuição à Previdência Privada</h3>
        </div>

        <!-- Conteúdo principal -->
        <br>
        <p>Olá <strong>{nome}</strong>,</p>
        <p>Sua contribuição à previdência privada foi registrada.</p>
        <p>Sua próxima nota fiscal deve ser emitida com o <strong>valor adicional de R$ {valor_str}</strong>.</p>
        <p>Att.</p>
        <p>DP do ISPN</p>

    </body>
    </html>
    """

    # Cria a mensagem MIME
    msg = MIMEText(corpo, "html", "utf-8")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    # Tenta enviar via SMTP SSL
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, destinatario, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False
    

def verificar_contratos_vencidos(pessoa):
    hoje = datetime.date.today()
    contratos_atualizados = False

    for idx, contrato in enumerate(pessoa.get("contratos", [])):
        data_fim = parse_date(contrato.get("data_fim"))
        status_atual = contrato.get("status_contrato", "")

        if data_fim and hoje > data_fim and status_atual != "Encerrado":
            pessoas.update_one(
                {"_id": pessoa["_id"]},
                {"$set": {f"contratos.{idx}.status_contrato": "Encerrado"}}
            )
            contrato["status_contrato"] = "Encerrado"
            contratos_atualizados = True

    return contratos_atualizados


# Define um diálogo (modal) para gerenciar colaboradores
@st.dialog("Gerenciar colaboradores", width='large')
def gerenciar_pessoas():

    # -------------------------------------------------------------------------
    # Inicializações de session_state
    # -------------------------------------------------------------------------
    if "contratos_verificados_por_pessoa" not in st.session_state:
        st.session_state.contratos_verificados_por_pessoa = {}

    if "pessoa_selecionada_anterior" not in st.session_state:
        st.session_state.pessoa_selecionada_anterior = None


    # Mapeia nomes de programa <-> ObjectId
    nome_para_id_programa = {
        p["nome_programa_area"]: p["_id"]
        for p in dados_programas if p.get("nome_programa_area")
    }
    id_para_nome_programa = {
        p["_id"]: p["nome_programa_area"]
        for p in dados_programas if p.get("nome_programa_area")
    }

    # Mapeia codigo de projeto <-> ObjectId
    # nome -> ObjectId
    sigla_para_id_projeto = {
        p.get("sigla"): p["_id"]   # <<< sem str()
        for p in dados_projetos_ispn
        if p.get("sigla") and "_id" in p
    }
  
    lista_programas_areas = sorted(nome_para_id_programa.keys())
    
    # Lista de coordenadores existentes (id, nome, programa)
    coordenadores_possiveis = [
        {
            "id": pessoa["_id"],
            "nome": pessoa.get("nome_completo", ""),
            "programa": pessoa.get("programa_area", "")
        }
        for pessoa in dados_pessoas
        if "coordenador(a)" in pessoa.get("tipo de usuário", "").lower()
    ]
    
    # Lista com nomes dos colaboradores para seleção
    nomes_existentes = [""] + ["--Adicionar colaborador--"] + sorted([
        p["nome_completo"]
        for p in dados_pessoas
        # if "coordenador" in p  # só inclui quem tem o campo 'coordenador'
    ])

    # INÍCIO
    # SelectBox do nome do colaborador
    with st.container(horizontal=True, horizontal_alignment="center"):
        nome_selecionado = st.selectbox(
            "Selecione o(a) colaborador(a):",
            nomes_existentes,
            index=0,
            width=400
        )

    # -------------------------------------------------------------------------
    # Processamento do colaborador selecionado
    # -------------------------------------------------------------------------
    if nome_selecionado not in ("", "--Adicionar colaborador--"):

        pessoa = next(
            (p for p in dados_pessoas if p["nome_completo"] == nome_selecionado),
            None
        )

        if pessoa:
            pessoa_id = str(pessoa["_id"])

            # Detecta troca de pessoa e força nova verificação
            if nome_selecionado != st.session_state.pessoa_selecionada_anterior:
                st.session_state.pessoa_selecionada_anterior = nome_selecionado
                st.session_state.contratos_verificados_por_pessoa.pop(pessoa_id, None)

                # LIMPA ESTADO DA ABA FÉRIAS
                for chave in ("dia_niver", "mes_niver", "dias_residuais"):
                    st.session_state.pop(chave, None)

            # Verificação única por pessoa
            if not st.session_state.contratos_verificados_por_pessoa.get(pessoa_id, False):

                contratos_atualizados = verificar_contratos_vencidos(pessoa)

                if contratos_atualizados:
                    st.toast(
                        "Contratos vencidos foram atualizados para 'Encerrado'",
                        icon=":material/event_busy:",
                        duration=5
                    )

                st.session_state.contratos_verificados_por_pessoa[pessoa_id] = True

    
        # Cria abas
        aba_info, aba_contratos, aba_previdencia, aba_ferias, aba_anotacoes  = st.tabs([":material/info: Informações gerais", ":material/contract: Contratos", ":material/finance_mode: Previdência", ":material/beach_access: Férias", ":material/notes: Anotações"])
    
        # ABA INFORMAÇÕES GERAIS ################################################################
        with aba_info:

            if pessoa:

                # ===============================
                # Formulário principal
                # ===============================

                # ===============================
                # Tipo de contratação (fora do form)
                # ===============================
                lista_tipo_contracao = ["PJ1", "PJ2", "CLT", "Estágio", ""]
                tipo_contratacao = st.selectbox(
                    "Tipo de contratação:",
                    lista_tipo_contracao,
                    index=lista_tipo_contracao.index(pessoa.get("tipo_contratacao", "")) 
                    if pessoa.get("tipo_contratacao", "") in lista_tipo_contracao else 0,
                    key=f"editar_contratacao_{pessoa_id}",
                    width=300
                )


                with st.form("form_editar_colaborador", border=False):

                    # -----------------------------------------------------------------
                    # Nome completo e status
                    # -----------------------------------------------------------------
                    

                    cols = st.columns([3,2])
                    nome = cols[0].text_input("Nome completo:", value=pessoa.get("nome_completo", ""), key=f"editar_nome_{pessoa_id}")

                    status_opcoes = ["ativo", "inativo"]
                    status = cols[1].selectbox(
                        "Status do(a) colaborador(a):", 
                        status_opcoes, 
                        index=status_opcoes.index(pessoa.get("status", "ativo")), 
                        key=f"editar_status_{pessoa_id}"
                    )

                    # -----------------------------------------------------------------
                    # CPF, RG, telefone e email
                    # -----------------------------------------------------------------


                    cols = st.columns(4)

                    cpf = cols[0].text_input("CPF:", value=pessoa.get("CPF", ""), key=f"editar_cpf_{pessoa_id}")
                    rg = cols[1].text_input("RG e órgão emissor:", value=pessoa.get("RG", ""), key=f"editar_rg_{pessoa_id}")

                    telefone = cols[2].text_input("Telefone:", value=pessoa.get("telefone", ""), key=f"editar_telefone_{pessoa_id}")
                    email = cols[3].text_input("E-mail:", value=pessoa.get("e_mail", ""), key=f"editar_email_{pessoa_id}")


                    # -----------------------------------------------------------------
                    # Gênero, Raça e Data de Nascimento
                    # -----------------------------------------------------------------
                    
                    cols = st.columns(3)

                    lista_generos = ["", "Masculino", "Feminino", "Não binário", "Outro"]

                    genero = cols[0].selectbox(
                        "Gênero:",
                        lista_generos,
                        index=lista_generos.index(pessoa.get("gênero")) if pessoa.get("gênero") in lista_generos else 0,
                        key=f"editar_genero_{pessoa_id}"
                    )

                    lista_raca = ["", "Amarelo", "Branco", "Índigena", "Pardo", "Preto"]

                    raca = cols[1].selectbox(
                        "Raça:",
                        lista_raca,
                        index=lista_raca.index(pessoa.get("raca")) if pessoa.get("raca") in lista_raca else 0,
                        key=f"editar_raca_{pessoa_id}"
                    )
                    
                    data_nascimento_str = pessoa.get("data_nascimento", "")
                    if data_nascimento_str:
                        data_nascimento = datetime.datetime.strptime(data_nascimento_str, "%d/%m/%Y")
                    else:
                        data_nascimento = None
                    data_nascimento = cols[2].date_input("Data de nascimento:", format="DD/MM/YYYY", value=data_nascimento, min_value=datetime.date(1920, 1, 1),
                                                         key=f"editar_data_nascimento_{pessoa_id}")

                    # -----------------------------------------------------------------
                    # Escolaridade, escritório, programa
                    # -----------------------------------------------------------------

                    cols = st.columns(3)

                    lista_escolaridade = ["", "Ensino fundamental", "Ensino médio", "Curso técnico", "Graduação", "Pós-graduação", "Mestrado", "Doutorado"]

                    escolaridade = cols[0].selectbox(
                        "Escolaridade:",
                        lista_escolaridade,
                        index=lista_escolaridade.index(pessoa.get("escolaridade")) if pessoa.get("escolaridade") in lista_escolaridade else 0,
                        key=f"editar_escolaridade_{pessoa_id}"
                    )

                    lista_escritorio = ["", "Brasília", "Santa Inês"]

                    escritorio = cols[1].selectbox(
                        "Escritório:",
                        lista_escritorio,
                        index=lista_escritorio.index(pessoa.get("escritorio")) if pessoa.get("escritorio") in lista_escritorio else 0,
                        key=f"editar_escritorio_{pessoa_id}"
                    )


                    # Programa / Área
                    # Pode ser ObjectId único, lista ou vazio (compatibilidade retroativa)
                    programas_atuais_raw = pessoa.get("programa_area", [])

                    if not isinstance(programas_atuais_raw, list):
                        programas_atuais_raw = [programas_atuais_raw] if programas_atuais_raw else []

                    # Converte ObjectId → nomes
                    programas_atuais_nomes = [
                        id_para_nome_programa.get(pid)
                        for pid in programas_atuais_raw
                        if pid in id_para_nome_programa
                    ]

                    # Multiselect
                    programas_selecionados = cols[2].multiselect(
                        "Programa / Área:",
                        options=lista_programas_areas,
                        default=programas_atuais_nomes,
                        key=f"editar_programa_{pessoa_id}"
                    )

                    # Converte nomes → ObjectId
                    programa_area = [
                        nome_para_id_programa[nome]
                        for nome in programas_selecionados
                        if nome in nome_para_id_programa
                    ]

                    # -----------------------------------------------------------------
                    # Cargo e nome do coordenador
                    # -----------------------------------------------------------------

                    cols = st.columns([3, 2])

                    # Garante que a lista tenha um valor vazio como placeholder
                    opcoes_cargos_com_vazio = [""] + opcoes_cargos  

                    valor_cargo = pessoa.get("cargo") or ""  
                    if valor_cargo not in opcoes_cargos_com_vazio:
                        valor_cargo = ""  

                    cargo = cols[0].selectbox(
                        "Cargo:",
                        opcoes_cargos_com_vazio,
                        index=opcoes_cargos_com_vazio.index(valor_cargo),
                        key=f"editar_cargo_{pessoa_id}"
                    )

                    # Coordenador

                    # 1. Lista de nomes (adiciona opção vazia)
                    nomes_coordenadores = [""] + [c["nome"] for c in coordenadores_possiveis]

                    # 2. Tenta encontrar coordenador atual
                    coordenador_atual_id = pessoa.get("coordenador")
                    coordenador_encontrado = next(
                        (c for c in coordenadores_possiveis if str(c["id"]) == str(coordenador_atual_id)),
                        None
                    )

                    # 3. Define valor default (se não achar, fica vazio)
                    nome_coordenador_default = coordenador_encontrado["nome"] if coordenador_encontrado else ""

                    # 4. Selectbox
                    coordenador_nome = cols[1].selectbox(
                        "Nome do(a) coordenador(a):",
                        nomes_coordenadores,
                        index=nomes_coordenadores.index(nome_coordenador_default)
                        if nome_coordenador_default in nomes_coordenadores else 0,
                        key=f"editar_nome_coordenador_{pessoa_id}"
                    )


                    # 5. Pega o ID do coordenador selecionado (se não for vazio)
                    coordenador_id = None
                    if coordenador_nome:
                        coordenador_id = next(
                            c["id"] for c in coordenadores_possiveis if c["nome"] == coordenador_nome
                        )        

                    # ===============================
                    # CAMPOS ADICIONAIS SE FOR PJ
                    # ===============================
                    cnpj, nome_empresa = None, None
                    if tipo_contratacao in ["PJ1", "PJ2"]:
                        col1, col2 = st.columns([3, 2])
                        nome_empresa = col1.text_input("Nome da empresa:", value=pessoa.get("nome_empresa", ""), key=f"editar_nome_empresa_{pessoa_id}")
                        cnpj = col2.text_input("CNPJ:", value=pessoa.get("cnpj", ""), placeholder="00.000.000/0000-00", key=f"editar_cnpj_{pessoa_id}")
                    
                    st.markdown("---")

                    # Dados bancários

                    st.write("**Dados bancários**")


                    col1, col2 = st.columns([1, 1])
                    nome_banco = col1.text_input("Nome do banco:", value=pessoa.get("banco", {}).get("nome_banco", ""), key=f"editar_banco_{pessoa_id}")
                    agencia = col2.text_input("Agência:", value=pessoa.get("banco", {}).get("agencia", ""), key=f"editar_agencia_{pessoa_id}")

                    col1, col2 = st.columns([1, 1])
                    conta = col1.text_input("Conta:", value=pessoa.get("banco", {}).get("conta", ""), key=f"editar_conta_bancaria_{pessoa_id}")


                    opcoes_conta = ["", "Conta Corrente", "Conta Poupança", "Conta Salário"]

                    tipo_conta_atual = pessoa.get("banco", {}).get("tipo_conta", "")

                    # Define o índice com segurança
                    if tipo_conta_atual in opcoes_conta:
                        index_conta = opcoes_conta.index(tipo_conta_atual)
                    else:
                        index_conta = 0  # seleciona a opção vazia

                    tipo_conta = col2.selectbox(
                        "Tipo de conta:",
                        options=opcoes_conta,
                        index=index_conta,
                        key=f"editar_editar_tipo_conta_{pessoa_id}"
                    )
                    
                    st.divider()
                    
                    
                            
                    #st.divider()

                    # Permissões
                    st.write('**Permissões**')


                    # Roteamento de tipo de usuário especial
                    # Só o admin pode atribuir permissão para outro admin
                    if set(st.session_state.tipo_usuario) & {"admin"}:

                        # Opções possíveis para o campo "tipo de usuário"
                        opcoes_tipo_usuario = [
                            "coordenador(a)", "admin", "gestao_pessoas", "gestao_ferias", "supervisao_ferias", 
                            "gestao_noticias", "gestao_pls", "gestao_projetos_doadores", 
                            "gestao_fundo_ecos", "gestao_viagens", "gestao_eventos", "gestao_manuais"
                        ]

                    else: # Se não for admin, não aparece a permissão admin disponível
                        # Opções possíveis para o campo "tipo de usuário"
                        opcoes_tipo_usuario = [
                            "coordenador(a)", "gestao_pessoas", "gestao_ferias", "supervisao_ferias", 
                            "gestao_noticias", "gestao_pls", "gestao_projetos_doadores", 
                            "gestao_fundo_ecos", "gestao_viagens", "gestao_eventos", "gestao_manuais"
                        ]


                    # Recupera o campo "tipo de usuário" do banco (pode ser string ou lista)
                    tipo_usuario_raw = pessoa.get("tipo de usuário", "")

                    # Converte string separada por vírgulas para lista, ou mantém lista se já for
                    if isinstance(tipo_usuario_raw, str):
                        tipo_usuario_list = [item.strip() for item in tipo_usuario_raw.split(",")]
                    elif isinstance(tipo_usuario_raw, list):
                        tipo_usuario_list = [item.strip() for item in tipo_usuario_raw]
                    else:
                        tipo_usuario_list = []

                    # Filtra para garantir que só valores válidos estejam selecionados
                    tipo_usuario_default = [t for t in tipo_usuario_list if t in opcoes_tipo_usuario]

                    # Multiselect para tipo de usuário com valores padrão preenchidos
                    tipo_usuario = st.multiselect(
                        "Tipo de usuário:",
                        options=opcoes_tipo_usuario,
                        default=tipo_usuario_default,
                        key=f"editar_tipo_usuario_{pessoa_id}"
                    )


                    with st.expander("Ver tipos de permissões"):

                        col1, col2 = st.columns([1, 1])


                        # admin
                        col1, col2 = st.columns([1, 2])
                        col1.write("**admin**")
                        col2.write("Tem todas as permissões.")

                        # gestao_pessoas
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_pessoas**")
                        col2.write("Faz a gestão de pessoas.")

                        # gestao_ferias
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_ferias**")
                        col2.write("Faz o registro de férias.")

                        # supervisao_ferias
                        col1, col2 = st.columns([1, 2])
                        col1.write("**supervisao_ferias**")
                        col2.write("Visualiza detalhes das férias de todos(as).")

                        # gestao_noticias
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_noticias**")
                        col2.write("Faz triagem de notícias.")

                        # gestao_pls
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_pls**")
                        col2.write("Faz a gestão dos Projetos de Lei monitorados.")

                        # gestao_projetos_doadores
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_projetos_doadores**")
                        col2.write("Faz a gestão de projetos e doadores.")

                        # gestao_fundo_ecos
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_fundo_ecos**")
                        col2.write("Faz a gestão dos projetos e editais do Fundo Ecos.")

                        # gestao_viagens
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_viagens**")
                        col2.write("Pode ver os dados de todas as viagens.")

                        # gestao_manuais
                        col1, col2 = st.columns([1, 2])
                        col1.write("**gestao_manuais**")
                        col2.write("Faz a gestão da página de manuais.")

                    st.write('')

                    # -------------------------------
                    # Botão salvar
                    # -------------------------------
                    if st.form_submit_button("Salvar alterações", type="secondary", icon=":material/save:"):

                        dados_update = {
                            "nome_completo": nome,
                            "CPF": cpf,
                            "RG": rg,
                            "data_nascimento": data_nascimento.strftime("%d/%m/%Y") if data_nascimento else None,
                            "telefone": telefone,
                            "e_mail": email,
                            "gênero": genero,
                            "raca": raca,
                            "escolaridade": escolaridade,
                            "banco.nome_banco": nome_banco,
                            "banco.agencia": agencia,
                            "banco.conta": conta,
                            "banco.tipo_conta": tipo_conta,
                            "programa_area": programa_area,
                            "coordenador": coordenador_id,
                            "cargo": cargo,
                            "tipo_contratacao": tipo_contratacao,  # vem de fora do form
                            "escritorio": escritorio,
                            "tipo de usuário": ", ".join(tipo_usuario) if tipo_usuario else "",
                            "status": status,
                        }

                        if tipo_contratacao in ["PJ1", "PJ2"]:
                            # adiciona ou atualiza campos extras
                            dados_update["cnpj"] = cnpj
                            dados_update["nome_empresa"] = nome_empresa

                            pessoas.update_one(
                                {"_id": pessoa["_id"]},
                                {"$set": dados_update}  # mantém + adiciona cnpj/nome_empresa
                            )
                        else:
                            # remove campos extras se existirem
                            pessoas.update_one(
                                {"_id": pessoa["_id"]},
                                {
                                    "$set": dados_update,
                                    "$unset": {"cnpj": "", "nome_empresa": ""}
                                }
                            )

                        st.success("Informações atualizadas com sucesso!", icon=":material/check_circle:")
                        time.sleep(2)
                        st.rerun()


        # ABA CONTRATOS ############################################################################### 
        with aba_contratos:

            # PREPARAÇÃO DE VARIÁVEIS ------------------------------------------------------
            # Lista de projetos
            lista_projetos = sorted([
                p["sigla"] for p in dados_projetos_ispn if p.get("sigla", "")
            ])

            # Lista de contratos da pessoa selecionada
            if pessoa:
                contratos = pessoa.get("contratos", [])
            else:
                contratos = []


            # Lista de meses em português
            meses_pt = [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
            ]

            # Opções de status
            status_opcoes = [
                "Em vigência", "Encerrado", "Cancelado", "Fonte de recurso temporária"
            ]


            # Expander de adicionar contrato -------------------------------------------------------

            with st.expander("Adicionar contrato", expanded=False, icon=":material/add_circle:"):
                
                
                # Projeto pagador
                cols = st.columns([3, 1])

                projetos_pagadores_nomes_edit = cols[0].multiselect(
                    "Contratado(a) pelo(s) projeto(s):",
                    lista_projetos
                )
                projetos_pagadores_edit = [
                    sigla_para_id_projeto.get(sigla)
                    for sigla in projetos_pagadores_nomes_edit
                    if sigla and sigla_para_id_projeto.get(sigla)
                ]


                # Status do contrato
                status_contrato = cols[1].selectbox("Status do contrato:", status_opcoes)



                cols = st.columns(3)
                inicio_contrato = cols[0].date_input("Data de início do contrato:", format="DD/MM/YYYY", value="today")
                fim_contrato = cols[1].date_input("Data de fim do contrato:", format="DD/MM/YYYY", value=None)
                data_reajuste = cols[2].selectbox("Mês de reajuste:", meses_pt)

                anotacoes_contrato = st.text_area("Anotações sobre o contrato:")

                # lista_status_contrato = ["Em vigência", "Encerrado", "Cancelado", "Fonte de recurso temporária", ""]

                #data_reajuste = col3.date_input("Data de reajuste:", format="DD/MM/YYYY")

                if st.button("Adicionar contrato", icon=":material/note_add:"):
                    novo_contrato = {
                        "data_inicio": inicio_contrato.strftime("%d/%m/%Y") if inicio_contrato else "",
                        "data_fim": fim_contrato.strftime("%d/%m/%Y") if fim_contrato else "",
                        "status_contrato": status_contrato,
                        "projeto_pagador": projetos_pagadores_edit,
                        "data_reajuste": data_reajuste,                  
                        "anotacoes_contrato": anotacoes_contrato        
                    }

                    contratos.append(novo_contrato)

                    # Atualiza no MongoDB
                    pessoas.update_one(
                        {"_id": ObjectId(pessoa["_id"])},
                        {"$set": {"contratos": contratos}}
                    )

                    st.success("Novo contrato adicionado com sucesso!")

            # CONTRATOS ------------------------------------------------------------

            st.write('')
            st.write('**Contratos:**')

            # CARD DE CADA CONTRATO ------------------------------------------------------------
            for i, contrato in enumerate(contratos):
                contrato_key = f"contrato_{pessoa['_id']}_{i}"
                toggle_key = f"toggle_edicao_contrato_{contrato_key}"

                with st.container(border=True):
                    projetos_ids = contrato.get("projeto_pagador", [])

                    # Toggle para modo edição
                    modo_edicao = st.toggle("Editar", key=toggle_key, value=False)

                    col1, col2 = st.columns([1, 2])

                    # ---------------- COLUNA 1 ----------------
                    with col1:
                        if modo_edicao:
                            contrato["status_contrato"] = st.selectbox(
                                "Status",
                                options=status_opcoes,
                                index=status_opcoes.index(contrato.get("status_contrato", "Em vigência"))
                                if contrato.get("status_contrato") in status_opcoes else 0,
                                key=f"status_{contrato_key}"
                            )

                            # Data início
                            data_inicio_valor = contrato.get("data_inicio")
                            data_inicio_dt = None
                            if isinstance(data_inicio_valor, str) and data_inicio_valor:
                                try:
                                    data_inicio_dt = datetime.datetime.strptime(data_inicio_valor, "%d/%m/%Y").date()
                                except:
                                    pass
                            contrato["data_inicio"] = st.date_input(
                                "Data de início",
                                value=data_inicio_dt or datetime.date.today(),
                                format="DD/MM/YYYY",
                                key=f"inicio_{contrato_key}"
                            ).strftime("%d/%m/%Y")

                            # Data fim
                            data_fim_valor = contrato.get("data_fim")
                            data_fim_dt = None
                            if isinstance(data_fim_valor, str) and data_fim_valor:
                                try:
                                    data_fim_dt = datetime.datetime.strptime(data_fim_valor, "%d/%m/%Y").date()
                                except:
                                    pass
                            contrato["data_fim"] = st.date_input(
                                "Data de fim",
                                value=data_fim_dt or datetime.date.today(),
                                format="DD/MM/YYYY",
                                key=f"fim_{contrato_key}"
                            ).strftime("%d/%m/%Y")

                            # Mês reajuste
                            contrato["data_reajuste"] = st.selectbox(
                                "Mês de reajuste",
                                options=meses_pt,
                                index=meses_pt.index(contrato.get("data_reajuste", "Janeiro"))
                                if contrato.get("data_reajuste") in meses_pt else 0,
                                key=f"reajuste_{contrato_key}"
                            )

                        else:
                            st.write("**Status:**", contrato.get("status_contrato", ""))
                            st.write("**Data de início:**", contrato.get("data_inicio", ""))
                            st.write("**Data de fim:**", contrato.get("data_fim", ""))
                            st.write("**Mês de reajuste:**", contrato.get("data_reajuste", ""))

                    # ---------------- COLUNA 2 ----------------
                    with col2:
                        st.write('**Projeto(s) pagador(es):**')

                        if modo_edicao:
                            siglas_selecionadas = [
                                p["sigla"] for p in dados_projetos_ispn
                                if p["_id"] in projetos_ids and p.get("sigla")
                            ]

                            siglas_escolhidas = st.multiselect(
                                "Selecione os projetos pagadores",
                                options=lista_projetos,
                                default=siglas_selecionadas,
                                key=f"multiselect_{contrato_key}"
                            )

                            contrato["projeto_pagador"] = [
                                p["_id"] for p in dados_projetos_ispn if p.get("sigla") in siglas_escolhidas
                            ]

                            contrato["anotacoes_contrato"] = st.text_area(
                                "Anotações sobre o contrato",
                                value=contrato.get("anotacoes_contrato", ""),
                                key=f"anotacoes_{contrato_key}"
                            )

                        else:
                            if not projetos_ids:
                                st.write("O projeto pagador não foi informado")
                            else:
                                for projeto_id in projetos_ids:
                                    projeto = next(
                                        (p for p in dados_projetos_ispn if p["_id"] == projeto_id),
                                        None
                                    )
                                    if projeto:
                                        st.write(f"{projeto.get('sigla', '')} - {projeto.get('nome_do_projeto', '')}")
                                    else:
                                        st.write(f"Projeto não encontrado para o ID: {projeto_id}")

                            if contrato.get("anotacoes_contrato"):
                                st.write("**Anotações:**")
                                st.write(contrato["anotacoes_contrato"])

                    # ---------------- BOTÃO DE SALVAR ----------------
                    if modo_edicao:
                        if st.button("Salvar alterações", key=f"salvar_{contrato_key}", icon=":material/save:"):
                            try:
                                pessoas.update_one(
                                    {"_id": pessoa["_id"]},
                                    {
                                        "$set": {
                                            f"contratos.{i}": contrato  # substitui só o contrato i
                                        }
                                    }
                                )
                                st.success("Contrato atualizado com sucesso!")
                            except Exception as e:
                                st.error(f"Erro ao salvar no banco: {e}")

        # ABA PREVIDÊNCIA ############################################################################### 
        with aba_previdencia:

            # Obtém a lista de contribuições do banco, ou cria lista vazia se não existir
            previdencia = pessoa.get("previdencia", []) if pessoa else []

            # Expander para adicionar nova contribuição -----------------------------------------------------------
            with st.expander("Adicionar nova contribuição", expanded=True, icon=":material/add_circle:"):

                # Usa colunas para organizar campos lado a lado
                cols = st.columns(2)

                # Campo para escolher data da contribuição, valor padrão é hoje
                nova_data = cols[0].date_input(
                    "Data da contribuição",
                    value=datetime.date.today(),
                    format="DD/MM/YYYY",
                    key="data_nova_contribuicao"
                )

                # Campo para valor da contribuição com duas casas decimais, mínimo 0.0
                valor_contribuicao = cols[1].number_input(
                    "Valor subsidiado pelo ISPN",
                    min_value=0.0,
                    format="%.2f",
                    key="valor_nova_contribuicao"
                )

                # Inicializa flag de controle se não existir
                if "contribuicao_adicionada" not in st.session_state:
                    st.session_state.contribuicao_adicionada = False

                # Botão para adicionar contribuição
                if st.button("Adicionar contribuição", icon=":material/savings:", key="botao_add_contribuicao"):
                    if valor_contribuicao > 0:
                        # Cria dicionário da nova contribuição formatando a data
                        nova_contribuicao = {
                            "data_contribuicao": nova_data.strftime("%d/%m/%Y"),
                            "valor": valor_contribuicao,
                        }
                        previdencia.append(nova_contribuicao)
                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"previdencia": previdencia}}
                        )
                        st.success("Nova contribuição adicionada com sucesso!")
                        st.session_state.contribuicao_adicionada = True  # ativa o botão de enviar e-mail

                # Mostrar quote e botão de enviar e-mail somente se a contribuição foi adicionada
                if st.session_state.contribuicao_adicionada:


                    pessoa_nome = pessoa.get("nome_completo", "Usuário").split()[0]
                    valor_contribuicao_str = format(valor_contribuicao, ",.2f").replace(",", "X").replace(".", ",").replace("X", ".")

                    st.write(f"Deseja enviar um email para **{pessoa_nome}** com a confirmação do registro e do valor?")


                    st.markdown(f"""
                    > Olá {pessoa_nome}. Sua contribuição à previdência privada foi registrada.  
                    > Sua próxima nota fiscal deve ser emitida com o acréscimo de R$ {valor_contribuicao_str}.  
                    > Att.  
                    > DP do ISPN  
                    """)

                    # Botão de enviar e-mail
                    if st.button("Enviar e-mail", key="botao_enviar_email_dialog", icon=":material/email:"):
                        destinatario = pessoa.get("e_mail")
                        nome = pessoa.get("nome_completo", "").split()[0]

                        if not destinatario:
                            st.warning("O e-mail do destinatário não está disponível.")
                        else:
                            try:
                                enviar_email(destinatario, nome, valor_contribuicao)
                                st.success(f"E-mail enviado com sucesso para {destinatario}!")
                                st.session_state.contribuicao_adicionada = False  # opcional: desativa botão após envio
                            except Exception as e:
                                st.error(f"Erro ao enviar e-mail: {e}")

            # LISTA DE CONTRIBUIÇÕES  -------------------------------------------------------------------------------------
            st.write("")
            st.write("**Contribuições registradas:**")

            # Prepara lista de contribuições com datas convertidas para ordenação
            contrib_ordenadas = []
            for idx, c in enumerate(previdencia):
                data_str = c.get("data_contribuicao", "")
                try:
                    # Tenta converter string da data para datetime
                    data_dt = datetime.datetime.strptime(data_str, "%d/%m/%Y")
                except:
                    # Em caso de erro, usa valor mínimo para ordenar no fim
                    data_dt = datetime.datetime.min
                contrib_ordenadas.append((idx, data_dt, c))
            # Ordena contribuições por data da mais recente para a mais antiga
            contrib_ordenadas.sort(key=lambda x: x[1], reverse=True)

            # Para cada contribuição ordenada, cria um container próprio para visualização/edição
            for original_idx, _, contribuicao in contrib_ordenadas:
                # Keys únicas para controle dos widgets (toggle, botões)
                container_key = f"contrib_{pessoa['_id']}_{original_idx}"
                toggle_key = f"toggle_edicao_contribuicao_{container_key}"
                delete_key = f"delete_confirm_{container_key}"

                # Container com borda para destacar a contribuição
                with st.container(border=True):
                    # Toggle para alternar entre modo edição e visualização
                    modo_edicao = st.toggle("Editar", key=toggle_key, value=False)


                    # MODO EDIÇÃO DA CONTRIBUIÇÃO
                    if modo_edicao:
                        # Modo edição: campos editáveis para data e valor

                        # Tenta converter string da data para tipo date, com fallback para hoje
                        data_valor = contribuicao.get("data_contribuicao")
                        data_dt = datetime.date.today()
                        if isinstance(data_valor, str) and data_valor:
                            try:
                                data_dt = datetime.datetime.strptime(data_valor, "%d/%m/%Y").date()
                            except:
                                pass

                        with st.container(horizontal=True):

                            # Campo para editar data da contribuição
                            nova_data = st.date_input(
                                "Data da contribuição",
                                value=data_dt,
                                format="DD/MM/YYYY",
                                key=f"data_{container_key}"
                            )

                            # Campo para editar valor da contribuição, valor inicial do registro atual
                            novo_valor = st.number_input(
                                "Valor subsidiado pelo ISPN",
                                value=float(contribuicao.get("valor", 0)),
                                min_value=0.0,
                                format="%.2f",
                                key=f"valor_{container_key}"
                            )

                        # Container horizontal para botões salvar e deletar
                        linha_botoes = st.container(horizontal=True)

                        # Botão para salvar alterações feitas
                        if linha_botoes.button("Salvar alterações", key=f"salvar_{container_key}", icon=":material/save:"):
                            # Atualiza os dados na lista
                            previdencia[original_idx]["data_contribuicao"] = nova_data.strftime("%d/%m/%Y")
                            previdencia[original_idx]["valor"] = novo_valor
                            # Atualiza o banco de dados com as alterações
                            pessoas.update_one(
                                {"_id": ObjectId(pessoa["_id"])},
                                {"$set": {"previdencia": previdencia}}
                            )
                            st.success("Contribuição atualizada com sucesso!")

                        # Botão para iniciar processo de exclusão
                        if linha_botoes.button("Deletar contribuição", key=f"deletar_{container_key}", icon=":material/delete:"):
                            st.session_state[delete_key] = True

                        # Se o usuário indicou que quer deletar, mostra confirmação
                        if st.session_state.get(delete_key, False):
                            st.warning("Você tem certeza que deseja apagar essa contribuição?")

                            botoes_confirmacao = st.container(horizontal=True)

                            # Botão confirma exclusão
                            if botoes_confirmacao.button("Sim, quero apagar", key=f"confirmar_delete_{container_key}", icon=":material/check:"):
                                try:
                                    # Remove a contribuição da lista
                                    previdencia.pop(original_idx)
                                    # Atualiza o banco removendo-a
                                    pessoas.update_one(
                                        {"_id": ObjectId(pessoa["_id"])},
                                        {"$set": {"previdencia": previdencia}}
                                    )
                                    st.success("Contribuição apagada com sucesso!")
                                    st.session_state[delete_key] = False
                                except Exception as e:
                                    st.error(f"Erro ao apagar contribuição: {e}")
                                    st.session_state[delete_key] = False

                            # Botão cancela exclusão
                            if botoes_confirmacao.button("Não", key=f"cancelar_delete_{container_key}", icon=":material/close:"):
                                st.session_state[delete_key] = False


                    # MODO VISUALIZAÇÃO DA CONTRIBUIÇÃO
                    else:
                        # Modo visualização: exibe data, usuário e valor da contribuição organizados em colunas
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.write(f"**Data:** {contribuicao.get('data_contribuicao', '')}")
                        with col2:
                            st.write(f"**Valor:** R$ {format(contribuicao.get('valor', 0), ',.2f').replace(',', 'X').replace('.', ',').replace('X', '.')}")


        # ABA FÉRIAS ###############################################################################
        with aba_ferias:

            # ------------------------------------------------------------------
            # PRÉ-CARREGA DADOS DO BANCO (SOMENTE SE EXISTIREM)
            # ------------------------------------------------------------------
            ferias_db = pessoa.get("férias", {}) if pessoa else {}

            niver_ferias_db = ferias_db.get("niver_ferias")
            abono_inicial_db = ferias_db.get("abono_inicial")

            # Só inicializa se EXISTIR no banco
            if niver_ferias_db:
                if "dia_niver" not in st.session_state:
                    st.session_state.dia_niver = niver_ferias_db.get("dia", "")

                if "mes_niver" not in st.session_state:
                    mes_num = niver_ferias_db.get("mes")
                    if mes_num:
                        nomes_meses = {
                            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
                        }
                        st.session_state.mes_niver = (mes_num, nomes_meses[mes_num])

            if "dias_residuais" not in st.session_state:
                st.session_state.dias_residuais = abono_inicial_db


            # ------------------------------------------------------------------
            # FORMULÁRIO
            # ------------------------------------------------------------------
            with st.form("form_ferias_colaborador", border=False):

                st.write(
                    '**Dia e mês** do "aniversário das férias" '
                    '(quando o colaborador será abonado com novos dias):'
                )

                # Dia (vazio + 1..31)
                lista_dias = [""] + list(range(1, 32))

                # Mês (vazio + tuplas)
                lista_meses = [""] + [
                    (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"),
                    (4, "Abril"), (5, "Maio"), (6, "Junho"),
                    (7, "Julho"), (8, "Agosto"), (9, "Setembro"),
                    (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
                ]

                with st.container(horizontal=True):

                    # DIA
                    dia = st.selectbox(
                        "Dia",
                        lista_dias,
                        key="dia_niver",
                        width=120
                    )

                    # MÊS
                    mes = st.selectbox(
                        "Mês",
                        lista_meses,
                        format_func=lambda x: "" if x == "" else x[1],
                        key="mes_niver",
                        width=250
                    )




                # with st.container(horizontal=True):
                #     # Dia
                #     dia = st.selectbox(
                #         "Dia",
                #         list(range(1, 32)),
                #         key="dia_niver",
                #         width=120
                #     )

                #     # Mês
                #     mes = st.selectbox(
                #         "Mês",
                #         [
                #             (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"),
                #             (4, "Abril"), (5, "Maio"), (6, "Junho"),
                #             (7, "Julho"), (8, "Agosto"), (9, "Setembro"),
                #             (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
                #         ],
                #         format_func=lambda x: x[1],
                #         key="mes_niver",
                #         width=250
                #     )

                st.write("")
                st.write("")

                st.write(
                    '**Número de dias** que serão abonados no primeiro ciclo:')
                st.caption('O primeiro cico é o período entre o início da contratação e o primeiro aniversário de férias):')
                st.caption('Se o primeiro ciclo corresponde a um ano completo, coloque 22 (PJ) ou 30 (CLT).')


                dias_residuais = st.number_input(
                    "Abono inicial:",
                    min_value=-30,
                    max_value=30,
                    key="dias_residuais",
                    width=120
                )

                st.write("")

                # ------------------------------------------------------------------
                # BOTÃO SALVAR
                # ------------------------------------------------------------------
                if st.form_submit_button("Salvar", type="secondary", icon=":material/save:"):

                    pessoas.update_one(
                        {"_id": pessoa["_id"]},
                        {
                            "$set": {
                                "férias.niver_ferias": {
                                    "dia": dia if dia != "" else None,
                                    "mes": mes[0] if mes != "" else None
                                },
                                "férias.abono_inicial": dias_residuais,
                                "férias.ciclo_1_abonado": False
                            }
                        }
                    )

                    st.success("Informações de férias atualizadas com sucesso!")
                    st.rerun()


        # ABA ANOTAÇÕES ############################################################################### 
        with aba_anotacoes:

            usuario_logado = st.session_state.get("nome", "Desconhecido")
            if pessoa:
                anotacoes = pessoa.get("anotacoes", [])
            else:
                anotacoes = []

            # ---------------- EXPANDER PARA ADICIONAR ANOTAÇÃO ----------------
            with st.expander("Adicionar nova anotação", expanded=False, icon=":material/add_notes:"):
                
                nova_data = st.date_input("Data da anotação", value=datetime.date.today(), format="DD/MM/YYYY", width=150)
                novo_texto = st.text_area("Texto da anotação")

                if st.button("Adicionar anotação", key="add_anotacao", icon=":material/add_notes:"):
                    if novo_texto.strip():
                        nova_anotacao = {
                            "data_anotacao": nova_data.strftime("%d/%m/%Y %H:%M"),
                            "autor": usuario_logado,
                            "anotacao": novo_texto.strip()
                        }
                        anotacoes.append(nova_anotacao)
                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"anotacoes": anotacoes}}
                        )
                        st.success("Nova anotação adicionada com sucesso!")
                        # st.experimental_rerun()
                    else:
                        st.warning("O campo da anotação não pode estar vazio.")




            # ---------------- LISTA DE ANOTAÇÕES EXISTENTES ----------------
            st.write('')
            st.write("**Anotações:**")

            # Ordena as anotações por data decrescente
            anotacoes_ordenadas = []
            for idx, a in enumerate(anotacoes):
                data_str = a.get("data_anotacao", "")
                data_dt = datetime.datetime.min
                if data_str:
                    try:
                        data_dt = datetime.datetime.strptime(data_str.split()[0], "%d/%m/%Y")
                    except:
                        pass
                anotacoes_ordenadas.append((idx, data_dt, a))

            # Ordena decrescente
            anotacoes_ordenadas.sort(key=lambda x: x[1], reverse=True)


            # CARD DE CADA ANOTAÇÃO ---------------------------------------------------------------

            for original_idx, _, anotacao in anotacoes_ordenadas:
                container_key = f"anotacao_{pessoa['_id']}_{original_idx}"
                toggle_key = f"toggle_edicao_anotacao_{container_key}"
                delete_key = f"delete_confirm_{container_key}"

                with st.container(border=True):
                    modo_edicao = st.toggle("Editar", key=toggle_key, value=False)

                    if modo_edicao:
                        # Editar data
                        data_valor = anotacao.get("data_anotacao")
                        data_dt = datetime.date.today()
                        if isinstance(data_valor, str) and data_valor:
                            try:
                                data_dt = datetime.datetime.strptime(data_valor.split()[0], "%d/%m/%Y").date()
                            except:
                                pass

                        nova_data = st.date_input(
                            "Data da anotação",
                            value=data_dt,
                            format="DD/MM/YYYY",
                            key=f"data_{container_key}", 
                            width=150
                        )

                        novo_texto = st.text_area(
                            "Texto da anotação",
                            value=anotacao.get("anotacao", ""),
                            key=f"texto_{container_key}"
                        )


                        # BOTÕES

                        linha_botoes = st.container(horizontal=True)

                        # Botão salvar
                        if linha_botoes.button("Salvar alterações", key=f"salvar_{container_key}", icon=":material/save:"):
                            anotacoes[original_idx]["data_anotacao"] = nova_data.strftime("%d/%m/%Y")
                            anotacoes[original_idx]["anotacao"] = novo_texto.strip()
                            pessoas.update_one(
                                {"_id": ObjectId(pessoa["_id"])},
                                {"$set": {"anotacoes": anotacoes}}
                            )
                            st.success("Anotação atualizada com sucesso!")

                        # Botão deletar
                        if linha_botoes.button("Deletar anotação", key=f"deletar_{container_key}", icon=":material/delete:"):
                            st.session_state[delete_key] = True

                        # Confirmação de exclusão


                        if st.session_state.get(delete_key, False):
                            st.warning("Você tem certeza que deseja apagar essa anotação?")

                            # Container horizontal para os dois botões
                            botoes_confirmacao = st.container(horizontal=True)

                            # Botão "Sim"
                            if botoes_confirmacao.button("Sim, quero apagar", key=f"confirmar_delete_{container_key}", icon=":material/check:"):
                                try:
                                    anotacoes.pop(original_idx)
                                    pessoas.update_one(
                                        {"_id": ObjectId(pessoa["_id"])},
                                        {"$set": {"anotacoes": anotacoes}}
                                    )
                                    st.success("Anotação apagada com sucesso!")
                                    st.session_state[delete_key] = False

                                except Exception as e:
                                    st.error(f"Erro ao apagar anotação: {e}")
                                    st.session_state[delete_key] = False

                            # Botão "Não"
                            if botoes_confirmacao.button("Não", key=f"cancelar_delete_{container_key}", icon=":material/close:"):
                                st.session_state[delete_key] = False


                    else:
                        # Visualização normal
                        data_str = anotacao.get('data_anotacao', '')
                        if data_str:
                            data_str = data_str.split()[0]  # remove hora
                        col1, col2 = st.columns([1,3])
                        with col1:
                            st.write(f"**Data:** {data_str}")
                        with col2:
                            st.write(f"**Autor:** {anotacao.get('autor', '')}")
                        st.write(anotacao.get("anotacao", ""))


    #    Adicionar colaborador --------------------------------------------------------------------------------
    elif nome_selecionado == "--Adicionar colaborador--":

         # SelectBox fora do formulário
        tipo_contratacao = st.selectbox(
            "Tipo de contratação:",
            ["","PJ1", "PJ2", "CLT", "Estágio"],
            index=0,
            width=300
        )


        # Formulário para cadastro
        with st.form("form_cadastro_colaborador", border=False):

            # -------------------------------------------------
            # Nome e status
            # -------------------------------------------------

            # Layout com colunas para inputs lado a lado
            col1, col2 = st.columns([3, 2])
            
            # Nome
            nome = col1.text_input("Nome completo:", key="cadastrar_nome")

            status_opcoes = ["ativo", "inativo"]
            status = col2.selectbox(
                "Status do(a) colaborador(a):", 
                status_opcoes, 
                index=0, 
                key="cadastrar_status"
            )

            # -------------------------------------------------
            # CPF, RG, Telefone e email
            # -------------------------------------------------

            cols = st.columns(4)


            cpf = cols[0].text_input("CPF:", placeholder="000.000.000-00")
            rg = cols[1].text_input("RG e órgão emissor:")
            telefone = cols[2].text_input("Telefone:")
            email = cols[3].text_input("E-mail:")


            # -------------------------------------------------
            # Gênero, raça e data de nascimento
            # -------------------------------------------------
            cols = st.columns(3)

            genero = cols[0].selectbox("Gênero:", ["Masculino", "Feminino", "Não binário", "Outro"], index=None, placeholder="")

            raca = cols[1].selectbox("Raça:", ["Amarelo", "Branco", "Índigena", "Pardo", "Preto"], index=None, placeholder="")

            data_nascimento = cols[2].date_input("Data de nascimento:", format="DD/MM/YYYY", value=None, min_value=datetime.date(1920, 1, 1))

            # -------------------------------------------------
            # Escolaridade, escritório e programa/área
            # -------------------------------------------------

            cols = st.columns(3)

            escolaridade = cols[0].selectbox("Escolaridade:", ["Ensino fundamental", "Ensino médio", "Curso técnico", "Graduação", "Pós-graduação", 
                                                            "Mestrado", "Doutorado"], index=None, placeholder="")

            escritorio = cols[1].selectbox("Escritório:", ["Brasília", "Santa Inês"], index=None, placeholder="")

            # Programa / Área
            # Lista ordenada dos programas/áreas para seleção
            programas_selecionados = cols[2].multiselect(
                "Programa / Área:",
                options=lista_programas_areas,
                default=[],  # novo colaborador começa vazio
                key="novo_programa_area",
                placeholder=""
            )

            # Converte nomes → ObjectId
            programa_area = [
                nome_para_id_programa[nome]
                for nome in programas_selecionados
                if nome in nome_para_id_programa
            ]

            # -------------------------------------------------
            # Cargo e nome do coordenador
            # -------------------------------------------------

            cols = st.columns([3, 2])

            # Cargo
            cargo = cols[0].selectbox("Cargo:", opcoes_cargos, index=None, placeholder="")

            # Coordenador/a
            # Lista de coordenadores existentes (id, nome, programa)
            coordenadores_possiveis = [
                {
                    "id": pessoa["_id"],
                    "nome": pessoa.get("nome_completo", ""),
                    "programa": pessoa.get("programa_area", "")
                }
                for pessoa in dados_pessoas
                if "coordenador(a)" in pessoa.get("tipo de usuário", "").lower()
            ]
            # Extrai nomes únicos dos coordenadores ordenados
            nomes_coordenadores = sorted({c["nome"] for c in coordenadores_possiveis})
            # Seleção do nome do coordenador no formulário
            coordenador = cols[1].selectbox("Nome do(a) coordenador(a):", nomes_coordenadores, index=None, placeholder="")

            # Por fim, pega o id do coordenador
            coordenador_id = None
            for c in coordenadores_possiveis:
                if c["nome"] == coordenador:
                    coordenador_id = c["id"]
                    break

            # ===============================
            # CAMPOS ADICIONAIS SE FOR PJ
            # ===============================
    
            # -------------------------------------------------
            # CNPJ e Nome da empresa
            # -------------------------------------------------
    
            if tipo_contratacao in ["PJ1", "PJ2"]:
                cnpj, nome_empresa = None, None
  
                cols = st.columns([3, 2])

                nome_empresa = cols[0].text_input("Nome da empresa:")
                cnpj = cols[1].text_input("CNPJ:", placeholder="00.000.000/0000-00")


            st.markdown("---")

            # -------------------------------------------------
            # Dados Bancários
            # -------------------------------------------------

            st.markdown("#### Dados bancários")
            
            col1, col2 = st.columns([1, 1])
            nome_banco = col1.text_input("Nome do banco:")
            agencia = col2.text_input("Agência:")
            
            col1, col2 = st.columns([1, 1])
            conta = col1.text_input("Conta:")
            tipo_conta = col2.selectbox("Tipo de conta:", ["Conta Corrente", "Conta Poupança", "Conta Salário"], index=None, placeholder="")


            # # -------------------------------------------------
            # # Férias
            # # -------------------------------------------------

            # st.markdown("---")
            # st.markdown("#### Férias")
            
            # col1, col2 = st.columns([1, 2])
            
            # # Férias
            # a_receber = col1.number_input("Dias de férias a receber:", step=1, min_value=22)

            # Variáveis de férias com valores iniciais
            a_receber = 0
            residual_ano_anterior = 0
            valor_inicial_ano_atual = 0
            total_gozado = 0
            saldo_atual = residual_ano_anterior + valor_inicial_ano_atual


            # -------------------------------------------------
            # Anotações
            # -------------------------------------------------

            st.divider()
            
            st.markdown("#### Anotações")
            
            hoje = datetime.datetime.today().strftime("%d/%m/%Y")

            # st.write(f"Data: {hoje}")
            
            anotacao_texto = st.text_area("Anotação", placeholder="")
            
            st.divider()

            # Permissões
            st.write('**Permissões:**')

            # Roteamento de tipo de usuário especial
            # Só o admin pode atribuir permissão para outro admin
            if set(st.session_state.tipo_usuario) & {"admin"}:

                # Opções possíveis para o campo "tipo de usuário"
                opcoes_tipo_usuario = [
                    "coordenador(a)", "admin", "gestao_pessoas", "gestao_ferias", "supervisao_ferias", 
                    "gestao_noticias", "gestao_pls", "gestao_projetos_doadores", 
                    "gestao_fundo_ecos", "gestao_viagens", "gestao_manuais"
                ]

            else: # Se não for admin, não aparece a permissão admin disponível
                # Opções possíveis para o campo "tipo de usuário"
                opcoes_tipo_usuario = [
                    "coordenador(a)", "gestao_pessoas", "gestao_ferias", "supervisao_ferias", 
                    "gestao_noticias", "gestao_pls", "gestao_projetos_doadores", 
                    "gestao_fundo_ecos", "gestao_viagens", "gestao_manuais"
                ]

            # Multiselect para tipo de usuário com valores padrão preenchidos
            tipo_usuario = st.multiselect(
                "Tipo de usuário:",
                options=opcoes_tipo_usuario,
                # default=tipo_usuario_default,
                key="cadastrar_tipo_usuario",
            )

            with st.expander("Ver tipos de permissões"):

                col1, col2 = st.columns([1, 1])


                # admin
                col1, col2 = st.columns([1, 2])
                col1.write("**admin**")
                col2.write("Tem todas as permissões.")

                # gestao_pessoas
                col1, col2 = st.columns([1, 2])
                col1.write("**gestao_pessoas**")
                col2.write("Faz a gestão de pessoas.")

                # gestao_ferias
                col1, col2 = st.columns([1, 2])
                col1.write("**gestao_ferias**")
                col2.write("Faz o registro de férias.")

                # supervisao_ferias
                col1, col2 = st.columns([1, 2])
                col1.write("**supervisao_ferias**")
                col2.write("Visualiza detalhes das férias de todos(as).")

                # gestao_noticias
                col1, col2 = st.columns([1, 2])
                col1.write("**gestao_noticias**")
                col2.write("Faz triagem de notícias.")

                # gestao_pls
                col1, col2 = st.columns([1, 2])
                col1.write("**gestao_pls**")
                col2.write("Faz a gestão dos Projetos de Lei monitorados.")

                # gestao_projetos_doadores
                col1, col2 = st.columns([1, 2])
                col1.write("**gestao_projetos_doadores**")
                col2.write("Faz a gestão de projetos e doadores.")

                # gestao_fundo_ecos
                col1, col2 = st.columns([1, 2])
                col1.write("**gestao_fundo_ecos**")
                col2.write("Faz a gestão dos projetos e editais do Fundo Ecos.")

                # gestao_viagens
                col1, col2 = st.columns([1, 2])
                col1.write("**gestao_viagens**")
                col2.write("Pode ver os dados de todas as viagens.")

                # gestao_manuais
                col1, col2 = st.columns([1, 2])
                col1.write("**gestao_manuais**")
                col2.write("Faz a gestão da página de manuais.")

            st.write('')

            # Ao submeter o formulário de cadastro -----------------------------------------------------------------
            if st.form_submit_button("Cadastrar", type="secondary", icon=":material/person_add:"):
                
                # Validação de campos obrigatórios
                if not nome or not email or not programa_area or not coordenador:
                    st.warning("Preencha os campos obrigatórios.")
                
                else:

                    # Ano atual para armazenar dados de férias
                    ano_atual = str(datetime.datetime.now().year)

                    # Monta o documento para inserção no MongoDB
                    novo_documento = {
                        "nome_completo": nome,
                        "CPF": cpf,
                        "RG": rg,
                        "telefone": telefone,
                        "data_nascimento": data_nascimento.strftime("%d/%m/%Y") if data_nascimento else None,
                        "gênero": genero,
                        "raca": raca,
                        "escolaridade": escolaridade,
                        "senha": "",
                        "tipo de usuário": ", ".join(tipo_usuario) if tipo_usuario else "",
                        "cargo": cargo,
                        "tipo_contratacao": tipo_contratacao,
                        "escritorio": escritorio,
                        "programa_area": programa_area,
                        "banco": {
                            "nome_banco": nome_banco,
                            "agencia": agencia,
                            "conta": conta,
                            "tipo_conta": tipo_conta
                        },
                        "férias": {
                            "anos": {
                                str(ano_atual): {
                                    "residual_ano_anterior": residual_ano_anterior,
                                    "valor_inicial_ano_atual": valor_inicial_ano_atual,
                                    "total_gozado": total_gozado,
                                    "saldo_atual": saldo_atual,
                                    "solicitacoes": [],
                                    "a_receber": a_receber
                                }
                            }
                        },
                        "status": "ativo",
                        "e_mail": email,
                        "coordenador": coordenador_id,

                        "anotacoes": [
                            {
                                "data_anotacao": datetime.datetime.today().strftime("%d/%m/%Y %H:%M"),
                                "autor": st.session_state.get("nome", "Desconhecido"),
                                "anotacao": anotacao_texto.strip() if anotacao_texto else ""
                            }
                        ]
                    }

                    # Adiciona cnpj e nome_empresa somente se for PJ
                    if tipo_contratacao in ["PJ1", "PJ2"]:
                        novo_documento.update({
                            "cnpj": cnpj,
                            "nome_empresa": nome_empresa
                        })

                    # Insere o novo colaborador no banco
                    pessoas.insert_one(novo_documento)
                    st.success(f"Colaborador(a) **{nome}** cadastrado(a) com sucesso!", icon=":material/thumb_up:")
                    time.sleep(2)
                    st.rerun()  # Recarrega a página para atualizar dados


# Função para converter datas (str -> datetime.date)
def parse_date(data_str):
    if isinstance(data_str, str):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(data_str, fmt).date()
            except ValueError:
                continue
    return None


def contrato_mais_recente(contratos):
    return max(
        contratos,
        key=lambda c: parse_date(c.get("data_inicio")) or datetime.date.min,
        default=None
    )


STATUS_VALIDOS = ["Em vigência", "Fonte de recurso temporária"]

def contratos_por_status(contratos):
    return [c for c in contratos if c.get("status_contrato") in STATUS_VALIDOS]


def contratos_para_aba_contratos(contratos):
    """
    Regra:
    - Se existir contrato 'Em vigência' ou 'Fonte de recurso temporária':
        → retorna TODOS eles
    - Caso contrário:
        → retorna apenas o contrato mais recente
    """
    ativos = contratos_por_status(contratos)

    if ativos:
        return ativos

    contrato_recente = contrato_mais_recente(contratos)
    return [contrato_recente] if contrato_recente else []


def contratos_ativos(contratos):
    """
    Retorna TODOS os contratos:
    - status 'Em vigência' ou 'Fonte de recurso temporária'
    - cuja data atual esteja dentro do período (se datas existirem)
    """
    hoje = datetime.date.today()
    ativos = []

    for c in contratos:
        if c.get("status_contrato") not in ["Em vigência", "Fonte de recurso temporária"]:
            continue

        inicio = parse_date(c.get("data_inicio"))
        fim = parse_date(c.get("data_fim"))

        # Se não tiver datas, assume válido
        if inicio and fim:
            if inicio <= hoje <= fim:
                ativos.append(c)
        else:
            ativos.append(c)

    return ativos


######################################################################################################
# MAIN
######################################################################################################


# Botão de gerenciar colaboradores só para alguns tipos de usuário
# Container horizontal de botões
container_botoes = st.container(horizontal=True, horizontal_alignment="right")
# Roteamento de tipo de usuário
if set(st.session_state.tipo_usuario) & {"admin", "coordenador(a)", "gestao_pessoas"}:

    # Botão para abrir o diálogo de gerenciamento de colaboradores
    container_botoes.button("Gerenciar colaboradores", on_click=gerenciar_pessoas, icon=":material/group:")
    st.write('')


aba_pessoas, aba_contratos, aba_reajustes, aba_aniversariantes = st.tabs([":material/person: Colaboradores", ":material/contract: Contratos", ":material/payments: Reajustes do mês", ":material/cake: Aniversariantes do mês"])


with aba_pessoas:

    st.write('')

    # Programas
    programas = [p["nome_programa_area"] for p in dados_programas]

    # Projetos
    projetos = sorted([p["sigla"] for p in dados_projetos_ispn])

    mapa_projeto_pessoa = {}

    for pessoa in dados_pessoas:
        contratos = pessoa.get("contratos", [])
        contratos_validos = contratos_ativos(contratos)

        projetos_set = set()

        for contrato in contratos_validos:
            for pid in contrato.get("projeto_pagador", []):
                projeto = next(
                    (p for p in dados_projetos_ispn if p["_id"] == pid),
                    None
                )
                if projeto:
                    projetos_set.add(projeto.get("sigla"))

        projeto_str = ", ".join(sorted(projetos_set)) if projetos_set else ""

        mapa_projeto_pessoa[pessoa.get("nome_completo")] = projeto_str

    df_pessoas["Programa/Área"] = df_pessoas["Programa/Área"].fillna("")

    # Organizar o dataframe por ordem alfabética de nome
    df_pessoas = df_pessoas.sort_values(by="Nome")

    #Tipo de contratação
    tipos_contratacao = sorted(df_pessoas["Tipo Contratação"].dropna().unique())

    # Filtros
    with st.container(horizontal=True):
        programa = st.selectbox("Programa / Área", ["Todos"] + programas)
        projeto = st.selectbox("Projeto", ["Todos"] + projetos) 
        tipo_contratacao = st.selectbox("Tipo de contratação", ["Todas"] + list(tipos_contratacao))
        status = st.selectbox("Status", ["ativo", "inativo"], index=0)


    # Copia o DataFrame original
    df_pessoas_filtrado = df_pessoas.copy()


    # Aplica os filtros
    if programa != "Todos":
        df_pessoas_filtrado = df_pessoas_filtrado[
            df_pessoas_filtrado["Programa/Área"].str.contains(programa, na=False)
        ]


    if projeto != "Todos":
        df_pessoas_filtrado = df_pessoas_filtrado[df_pessoas_filtrado["Projeto Pagador"].str.contains(projeto)]

    if tipo_contratacao != "Todas":
        df_pessoas_filtrado = df_pessoas_filtrado[df_pessoas_filtrado["Tipo Contratação"] == tipo_contratacao]

    df_pessoas_filtrado = df_pessoas_filtrado[df_pessoas_filtrado["Status"] == status]


    # Exibir DataFrame --------------------------------------------------
    st.write('')
    st.subheader(f'{len(df_pessoas_filtrado)} colaboradores(as)')
    st.write('')


    # cria um dataframe APENAS para exibição (cópia)
    df_pessoas_exibir = df_pessoas_filtrado.copy()

    # remove colunas indesejadas SOMENTE no dataframe de exibição
    df_pessoas_exibir = df_pessoas_exibir.drop(
        columns=[
            "Status",
            "Gênero",
            "Escolaridade",
            "Raça",
            "Tipo Contratação",
            "Data de nascimento",
        ],
        errors="ignore"
    )

    # exibe sem alterar o dataframe original
    st.dataframe(
        df_pessoas_exibir
            .rename(columns={"Projeto Pagador": "Projeto"})
            .fillna(""),
        hide_index=True
    )



    # Gráficos 
    col1, col2 = st.columns(2)

    # GRÁFICO DE PESSOAS POR PROGRAMA/ÁREA -----------------------------------------------------------

    # Agrupar e ordenar
    df_programas_explodido = df_pessoas_filtrado.assign(
        **{'Programa/Área': df_pessoas_filtrado['Programa/Área'].str.split(r',\s*')}
    ).explode('Programa/Área')

    df_programas_explodido['Programa/Área'] = df_programas_explodido['Programa/Área'].str.strip()

    programa_counts = (
        df_programas_explodido['Programa/Área']
        .value_counts()
        .reset_index()
    )

    programa_counts.columns = ['Programa/Área', 'Quantidade']

    # Criar gráfico ordenado do maior para o menor
    fig = px.bar(
        programa_counts,
        x='Programa/Área',
        y='Quantidade',
        color='Programa/Área',
        text='Quantidade',
        title='Pessoas por Programa/Área',
        labels={"Programa/Área": "", "Quantidade": ""}  # remove os labels dos eixos
    )

    # posiciona os textos acima das barras
    fig.update_traces(textposition='outside')

    # remove os números do eixo Y
    fig.update_yaxes(showticklabels=False)

    # aumenta o limite superior do eixo Y para não cortar os textos
    fig.update_yaxes(range=[0, programa_counts['Quantidade'].max() * 1.15])

    # remove legenda
    fig.update_layout(showlegend=False)

    col1.plotly_chart(fig,
                    config={
                        'staticPlot': False  # desativa pan, zoom e todas as interações
                    })

    # GRÁFICO DE PESSOAS POR ESCRITÓRIO ------------------------------------------------


    # substitui valores vazios ou NaN por "Não informado"
    df_pessoas_filtrado['Escritório_tratado'] = df_pessoas_filtrado['Escritório'].replace("", "Não informado")
    df_pessoas_filtrado['Escritório_tratado'] = df_pessoas_filtrado['Escritório_tratado'].fillna("Não informado")

    # criar gráfico de pizza
    fig = px.pie(
        df_pessoas_filtrado,
        names='Escritório_tratado',
        title='Pessoas por Escritório',
        hole=0
    )

    # adiciona valores dentro das fatias e arredonda percentuais
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        texttemplate='%{percent:.0%} %{label}'
    )

    # remove legenda
    fig.update_layout(showlegend=False)

    # exibir gráfico estático
    col2.plotly_chart(
        fig,
        config={'staticPlot': False}
    )

    # GRÁFICO DE PESSOAS POR PROJETO ------------------------------------------------

    # st.write(df_pessoas_filtrado)

    # Projeto

    # separa os nomes que estão na mesma célula por vírgula e transforma em linhas separadas

    df_explodido = df_pessoas_filtrado.assign(
        **{'Projeto Pagador': df_pessoas_filtrado['Projeto Pagador'].str.split(r',\s*')}
    ).explode('Projeto Pagador')

    # df_explodido = df_pessoas_filtrado.assign(
    #     **{'Projeto Pagador': df_pessoas_filtrado['Projeto Pagador'].str.split(',\s*')}
    # ).explode('Projeto Pagador')

    # remove espaços extras
    df_explodido['Projeto Pagador'] = df_explodido['Projeto Pagador'].str.strip()

    # agora cria o resumo por projeto
    resumo = df_explodido.groupby('Projeto Pagador').size().reset_index(name='Quantidade')

    fig = px.bar(
        resumo,
        x='Projeto Pagador',
        y='Quantidade',
        color='Projeto Pagador',  # cada projeto uma cor
        text='Quantidade',
        title='Pessoas por Projeto',
        labels={"Projeto Pagador": "", "Quantidade": ""}
    )

    # textos acima das barras
    fig.update_traces(textposition='outside')

    # remove números do eixo Y
    fig.update_yaxes(showticklabels=False)

    # aumenta limite superior para não cortar textos
    fig.update_yaxes(range=[0, resumo['Quantidade'].max() * 1.15])

    # remove legenda
    fig.update_layout(showlegend=False)

    # desativa interação
    col1.plotly_chart(
        fig,
        config={'staticPlot': False}
    )

    # GRÁFICO DE PESSOAS POR TIPO DE CONTRATAÇÃO -----------------------------------------------------------

    # substitui valores vazios ou NaN por "Não informado"
    df_pessoas_filtrado['Tipo Contratação_tratado'] = df_pessoas_filtrado['Tipo Contratação'].replace("", "Não informado")
    df_pessoas_filtrado['Tipo Contratação_tratado'] = df_pessoas_filtrado['Tipo Contratação_tratado'].fillna("Não informado")

    # criar gráfico de pizza
    fig = px.pie(
        df_pessoas_filtrado,
        names='Tipo Contratação_tratado',
        title='Pessoas por Tipo de Contratação',
        hole=0
    )

    # adiciona valores dentro das fatias e arredonda percentuais
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        texttemplate='%{percent:.0%} %{label}'
    )

    # remove legenda
    fig.update_layout(showlegend=False)

    # plota gráfico estático
    col2.plotly_chart(
        fig,
        config={'staticPlot': False}
    )

    # Gráfico de pessoas por Cargo ------------------------------------------------

    # Cargo
    # substitui valores vazios ou NaN por "Não informado"
    df_pessoas_filtrado['Cargo_tratado'] = df_pessoas_filtrado['Cargo'].replace("", "Não informado")
    df_pessoas_filtrado['Cargo_tratado'] = df_pessoas_filtrado['Cargo_tratado'].fillna("Não informado")

    # Agrupar e ordenar do maior para o menor
    cargo_counts = df_pessoas_filtrado['Cargo_tratado'].value_counts().reset_index()
    cargo_counts.columns = ['Cargo', 'Quantidade']

    # Criar gráfico de barras
    fig = px.bar(
        cargo_counts,
        x='Cargo',
        y='Quantidade',
        color='Cargo',
        text='Quantidade',
        title='Pessoas por Cargo',
        labels={"Cargo": "", "Quantidade": ""}  # remove labels dos eixos
    )

    # posiciona os textos acima das barras
    fig.update_traces(textposition='outside')

    # remove os números do eixo Y
    fig.update_yaxes(showticklabels=False)

    # aumenta o limite superior do eixo Y para não cortar os textos
    fig.update_yaxes(range=[0, cargo_counts['Quantidade'].max() * 3.15])

    # remove legenda
    fig.update_layout(showlegend=False)

    # exibir gráfico estático
    col1.plotly_chart(
        fig,
        config={'staticPlot': False}
    )

    # Pessoas por Escolaridade -------------------------------------------------------
    df_pessoas_filtrado['Escolaridade_tratado'] = df_pessoas_filtrado['Escolaridade'].replace("", "Não informado")
    df_pessoas_filtrado['Escolaridade_tratado'] = df_pessoas_filtrado['Escolaridade_tratado'].fillna("Não informado")

    fig = px.pie(
        df_pessoas_filtrado,
        names='Escolaridade_tratado',
        title='Pessoas por Escolaridade',
        hole=0
    )

    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        texttemplate='%{percent:.0%} %{label}'
    )

    fig.update_layout(showlegend=False)

    col2.plotly_chart(
        fig,
        # config={'staticPlot': True}
    )

    # Gráfico de pessoas por Gênero ------------------------------------------------

    # define cores com transparência
    cores = {
        'Masculino': 'rgba(76, 120, 168, 0.5)',       # azul 50%
        'Feminino': 'rgba(255, 0, 0, 0.3)',           # vermelho 30%
        'Não binário': 'rgba(255, 255, 0, 0.5)',      # amarelo 50%
        'Outro': 'rgba(128, 128, 128, 1)'             # cinza opaco
    }

    fig = px.pie(
        df_pessoas_filtrado,
        names='Gênero',
        title='Pessoas por Gênero',
        color='Gênero',
        color_discrete_map=cores
    )

    # adiciona valores dentro das fatias e arredonda para inteiro
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        texttemplate='%{percent:.0%} %{label}'  # percent arredondado para inteiro
    )

    # remove legenda
    fig.update_layout(showlegend=False)

    # desativa interação
    col1.plotly_chart(
        fig,
        config={'staticPlot': False}
    )

    # Pessoas por Raça ----------------------------------------------------
    df_pessoas_filtrado['Raça_tratado'] = df_pessoas_filtrado['Raça'].replace("", "Não informado")
    df_pessoas_filtrado['Raça_tratado'] = df_pessoas_filtrado['Raça_tratado'].fillna("Não informado")

    fig = px.pie(
        df_pessoas_filtrado,
        names='Raça_tratado',
        title='Pessoas por Raça',
        hole=0
    )

    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        texttemplate='%{percent:.0%} %{label}'
    )

    fig.update_layout(showlegend=False)

    col2.plotly_chart(
        fig,
        # config={'staticPlot': True}
    )


#  ABA CONTRATOS ---------------------------------------------------------------------------------------

# Roteamento de usuários
# if set(st.session_state.tipo_usuario) & {"admin", "gestao_pessoas"}:
with aba_contratos:

    

    # Função para calcular dias restantes
    def dias_restantes(data_fim):
        if data_fim:
            return (data_fim - datetime.date.today()).days
        return None

    # ----------------- CONTRATOS A VENCER (90 DIAS) -----------------
    contratos_90_dias = []

    for p in dados_pessoas:
        contratos_exibir = contratos_para_aba_contratos(p.get("contratos", []))

        for contrato in contratos_exibir:
            data_fim = parse_date(contrato.get("data_fim"))
            if data_fim and dias_restantes(data_fim) <= 90:
                contratos_90_dias.append({
                    "pessoa": p,
                    "contrato": contrato,
                    "dias_restantes": dias_restantes(data_fim)
                })


    

    # -------------------- Renderizar lista de contratos --------------------
    st.write('')
    st.markdown('<h3 style="font-size: 1.5em;">Contratos com vencimento nos próximos 90 dias:</h3>', unsafe_allow_html=True)
    st.write('')
    st.write('')
    st.write('')

    

    for item in contratos_90_dias:

        col1, col2, col3 = st.columns([1, 1, 3])

        pessoa = item["pessoa"]
        contrato = item["contrato"]

        # with st.container(border=True):
        
        col1.write(f"**{pessoa.get('nome_completo', 'Sem nome')}**")

        col2.write(f"**Data de fim:** {contrato.get('data_fim', '')}")
        col2.write(f"**Data de início:** {contrato.get('data_inicio', '')}")

        # col2.write(f"**Mês de reajuste:** {contrato.get('data_reajuste', '')}")


        projetos_ids = contrato.get("projeto_pagador", [])
        col3.write('**Projeto:**')
        if not projetos_ids:
            col3.write("O projeto pagador não foi informado")
        else:
            for projeto_id in projetos_ids:
                projeto = next(
                    (p for p in dados_projetos_ispn if p["_id"] == projeto_id),
                    None
                )
                if projeto:
                    col3.write(f"{projeto.get('sigla', '')} - {projeto.get('nome_do_projeto', '')}")
                else:
                    col3.write(f"Projeto não encontrado para o ID: {projeto_id}")

        if contrato.get("anotacoes_contrato"):
            col3.write("**Anotações:**")
            col3.write(contrato["anotacoes_contrato"])

        st.divider()




    # -------------------- Preparar e renderizar gráfico de timeline --------------------

    st.write('')
    st.markdown('<h3 style="font-size: 1.5em;">Cronograma dos contratos</h3>', unsafe_allow_html=True)


    lista_tratada = []
    for pessoa in dados_pessoas:
        nome = pessoa.get("nome_completo", "Sem nome")
        contratos = pessoa.get("contratos", [])

        for contrato in contratos_para_aba_contratos(contratos):
            data_inicio = parse_date(contrato.get("data_inicio"))
            data_fim = parse_date(contrato.get("data_fim"))
            if data_inicio and data_fim:
                lista_tratada.append({
                    "Nome": nome,
                    "Início do contrato": data_inicio,
                    "Fim do contrato": data_fim,
                    "Dias restantes": dias_restantes(data_fim)
                })

    if lista_tratada:
        df_equipe = pd.DataFrame(lista_tratada)

        # Definir cor: vermelho se < 90 dias, azul caso contrário
        df_equipe["Cor"] = df_equipe["Dias restantes"].apply(
            lambda x: "rgba(255, 0, 0, 0.5)" if x < 90 else "rgba(76, 120, 168, 0.5)"
        )

        # Ordenar por data de fim (decrescente)
        df_equipe = df_equipe.sort_values(by="Fim do contrato", ascending=False)
        categorias_y = df_equipe["Nome"].tolist()

        # Calcular altura do gráfico dinamicamente
        altura_base = 200
        altura_extra = 40 * len(df_equipe)
        altura = altura_base + altura_extra

        # Criar gráfico de timeline
        fig = px.timeline(
            df_equipe,
            x_start="Início do contrato",
            x_end="Fim do contrato",
            y="Nome",
            color="Cor",
            color_discrete_map="identity",
            height=altura
        )

        fig.update_yaxes(categoryorder="array", categoryarray=categorias_y)

        # Linha vertical de hoje
        hoje = pd.Timestamp(datetime.date.today())
        fig.add_vline(x=hoje, line_width=1, line_dash="dash", line_color="gray")

        fig.update_layout(
            yaxis_title=None,
            xaxis_title="Duração do contrato",
            showlegend=False
        )

        st.plotly_chart(fig)
    else:
        st.caption("Nenhum contrato válido encontrado.")



with aba_reajustes:

    mes_atual_str = meses_pt[datetime.date.today().month - 1]

    st.markdown(f'<h3 style="font-size: 1.5em;">Contratos com reajuste em {mes_atual_str}:</h3>', unsafe_allow_html=True)
    st.write(f"")
    st.write(f"")

    encontrados = False  # Flag para saber se achou algum contrato

    for pessoa in dados_pessoas:
        nome = pessoa.get("nome_completo", "Sem nome")
        contratos = pessoa.get("contratos", [])

        # Filtrar contratos "Em vigência" com reajuste no mês atual
        contratos_reajuste = [
            c for c in contratos
            if c.get("status_contrato") == "Em vigência" and c.get("data_reajuste") == mes_atual_str
        ]

        for contrato in contratos_reajuste:
            projetos_ids = contrato.get("projeto_pagador", [])
            if projetos_ids:
                for projeto_id in projetos_ids:
                    projeto = next(
                        (p for p in dados_projetos_ispn if p["_id"] == projeto_id),
                        None
                    )
                    if projeto:
                        st.write(f"**{nome}** - {projeto.get('sigla', projeto.get('nome_do_projeto',''))}")
                        encontrados = True
            else:
                st.write(f"**{nome}** - Projeto pagador não informado")
                encontrados = True

    if not encontrados:
        st.caption("Nenhum contrato com reajuste no mês atual.")


with aba_aniversariantes:

    # Obter mês atual
    mes_atual = datetime.date.today().month

    st.write("")

    st.markdown(f'<h3 style="font-size: 1.5em;">Aniversariantes do mês de {meses_pt[mes_atual - 1]}:</h3>', unsafe_allow_html=True)
    st.write("")

    encontrados = False  # Flag para saber se achou algum aniversariante

    df_aniversariantes = df_pessoas.copy()



    # Converter Data de nascimento para datetime
    df_aniversariantes["data_nascimento_datetime"] = pd.to_datetime(df_aniversariantes["Data de nascimento"], format="%d/%m/%Y")

    # Filtrar pessoas com data de nascimento no mês atual
    df_aniversariantes = df_aniversariantes[df_aniversariantes["data_nascimento_datetime"].dt.month == mes_atual]

    # Ordenar pelo dia do mês, se quiser ordem crescente
    df_aniversariantes = df_aniversariantes.sort_values(by="Data de nascimento")

    for _, pessoa in df_aniversariantes.iterrows():
        nome = pessoa["Nome"] if pd.notna(pessoa["Nome"]) else "Sem nome"
        data_nascimento = pessoa["data_nascimento_datetime"]

        st.write(f"**{nome}** - {data_nascimento.strftime('%d/%m')}")
        encontrados = True


    if not encontrados:
        st.caption("Nenhum aniversariante encontrado neste mês.")