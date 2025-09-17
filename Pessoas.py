import streamlit as st
import pandas as pd 
import plotly.express as px
import datetime
from bson import ObjectId
import time
from funcoes_auxiliares import conectar_mongo_portal_ispn

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
    id_programa_area = pessoa.get("programa_area")
    nome_programa_area = next(
        (p.get("nome_programa_area", "") for p in dados_programas if p["_id"] == id_programa_area),
        "Não informado"
    )

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
        "Status": pessoa.get("status", "")
    })

# Criar DataFrame de Pessoas
df_pessoas = pd.DataFrame(pessoas_lista)



# PROJETOS
# Filtra só os projetos em que a sigla não está vazia
dados_projetos_ispn = [projeto for projeto in dados_projetos_ispn if projeto["sigla"] != ""]



######################################################################################################
# FUNÇÕES
######################################################################################################

# Cargo
opcoes_cargos = [
    "Analista de advocacy", "Analista de comunicação", "Analista de dados", "Analista Administrativo/Financeiro",
    "Analista de Recursos Humanos", "Analista socioambiental", "Analista socioambiental pleno", "Analista socioambiental sênior",
    "Assessora de advocacy", "Assessor de Comunicação", "Auxiliar de Serviços Gerais", "Auxiliar Administrativo/financeiro",
    "Assistente Administrativo/financeiro", "Assistente socioambiental", "Coordenador Administrativo/financeiro de escritório",
    "Coordenador Geral administrativo/financeiro", "Coordenador Executivo", "Coordenador de Área", "Coordenador de Programa",
    "Motorista", "Secretária(o)/Recepcionista", "Técnico de campo", "Técnico em informática"
]


# Define um diálogo (modal) para gerenciar colaboradores com abas de cadastro e edição
@st.dialog("Gerenciar colaboradores", width='large')
def gerenciar_pessoas():
    
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
    nome_para_id_projeto = {
        p.get("nome_do_projeto"): p["_id"]   # <<< sem str()
        for p in dados_projetos_ispn
        if p.get("nome_do_projeto") and "_id" in p
    }

    # id (ObjectId) -> nome
    id_para_nome_projeto = {
        p["_id"]: p.get("nome_do_projeto", "")
        for p in dados_projetos_ispn
        if "_id" in p
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
        if "coordenador" in p  # só inclui quem tem o campo 'coordenador'
    ])

   
    nome_selecionado = st.selectbox("Selecione o(a) colaborador(a) para ver informações:", nomes_existentes, index=0)
    
    if nome_selecionado not in ("", "--Adicionar colaborador--"):
        
        # Busca colaborador selecionado no banco
        pessoa = next((p for p in dados_pessoas if p["nome_completo"] == nome_selecionado), None)
        
        # tipo_contratacao_opcoes = ["","PJ1", "PJ2", "CLT", "Estagiário"]
        
        # # SelectBox fora do formulário
        # tipo_contratacao = st.selectbox(
        #     "Tipo de contratação:",
        #     tipo_contratacao_opcoes,
        #     index=tipo_contratacao_opcoes.index(pessoa.get("tipo_contratacao")), key="tipo_contratacao_edit",
        # )
        
        # Cria duas abas: cadastro e edição
        aba_info, aba_contratos, aba_previdencia, aba_anotacoes  = st.tabs([":material/info: Informações gerais", ":material/contract: Contratos", ":material/finance_mode: Previdência", ":material/notes: Anotações"])
    
        with aba_info:

            if pessoa:
                # ===============================
                # Tipo de contratação (fora do form)
                # ===============================
                lista_tipo_contracao = ["PJ1", "PJ2", "CLT", "Estagiário", ""]
                tipo_contratacao = st.selectbox(
                    "Tipo de contratação:",
                    lista_tipo_contracao,
                    index=lista_tipo_contracao.index(pessoa.get("tipo_contratacao", "")) 
                    if pessoa.get("tipo_contratacao", "") in lista_tipo_contracao else 0,
                    key="tipo_contratacao_edit"
                )

                # ===============================
                # Formulário principal
                # ===============================
                with st.form("form_editar_colaborador", border=False):
                    st.write('')

                    # -------------------------------
                    # Status
                    # -------------------------------
                    cols = st.columns([1, 2])
                    status_opcoes = ["ativo", "inativo"]
                    status = cols[0].selectbox(
                        "Status do(a) colaborador(a):", 
                        status_opcoes, 
                        index=status_opcoes.index(pessoa.get("status", "ativo")), 
                        key="editar_status"
                    )

                    st.markdown("---")

                    # -------------------------------
                    # Campos existentes
                    # -------------------------------
                    col1, col2 = st.columns([1, 1])
                    nome = col1.text_input("Nome completo:", value=pessoa.get("nome_completo", ""))
                    lista_generos = ['Masculino', 'Feminino', 'Não binário', 'Outro']
                    genero = col2.selectbox(
                        "Gênero:", lista_generos, 
                        index=lista_generos.index(pessoa.get("gênero")), 
                        key="editar_genero"
                    )
                    
                    col1, col2 = st.columns([1, 1])
                    
                    lista_escolaridade = ["Ensino fundamental", "Ensino médio", "Graduação", "Pós-graduação", "Mestrado", "Doutorado", ""]
            
                    escolaridade = col1.selectbox("Escolaridade:", lista_escolaridade, index=lista_escolaridade.index(pessoa.get("escolaridade")))
                    
                    lista_raca = ["Amarelo", "Branco", "Índigena", "Pardo", "Preto", ""]
                    
                    raca = col2.selectbox("Raça:", lista_raca, index=lista_raca.index(pessoa.get("raca")))

                    col1, col2 = st.columns([1, 1])

                    # CPF e RG 
                    cpf = col1.text_input("CPF:", value=pessoa.get("CPF", ""))
                    rg = col2.text_input("RG e órgão emissor:", value=pessoa.get("RG", ""))
                    
                    # ===============================
                    # CAMPOS ADICIONAIS SE FOR PJ
                    # ===============================
                    cnpj, nome_empresa = None, None
                    if tipo_contratacao in ["PJ1", "PJ2"]:
                        col1, col2 = st.columns([1,1])
                        cnpj = col1.text_input("CNPJ:", value=pessoa.get("cnpj", ""), placeholder="00.000.000/0000-00")
                        nome_empresa = col2.text_input("Nome da empresa:", value=pessoa.get("nome_empresa", ""))

                    col1, col2, col3 = st.columns([1, 2, 2])
                    
                    # Data de nascimento, telefone e e-mail
                    data_nascimento_str = pessoa.get("data_nascimento", "")
                    if data_nascimento_str:
                        data_nascimento = datetime.datetime.strptime(data_nascimento_str, "%d/%m/%Y")
                    else:
                        data_nascimento = None
                    data_nascimento = col1.date_input("Data de nascimento:", format="DD/MM/YYYY", value=data_nascimento)
                    telefone = col2.text_input("Telefone:", value=pessoa.get("telefone", ""))
                    email = col3.text_input("E-mail:", value=pessoa.get("e_mail", ""))
                    
                    lista_escritorio = ["Brasília", "Santa Inês", ""]
                    
                    escritorio = st.selectbox("Escritório:", lista_escritorio, index=lista_escritorio.index(pessoa.get("escritorio")))                  
                    
                    lista_tipo_contracao = ["PJ1", "PJ2", "CLT", "Estagiário", ""]
                    
                    col1, col2, col3 = st.columns([1, 1, 1])
                    
                    lista_cargos = ["Analista de advocacy", "Analista de comunicação", "Analista de dados", "Analista Administrativo/Financeiro",
                    "Analista de Recursos Humanos", "Analista socioambiental", "Analista socioambiental pleno", "Analista socioambiental sênior",
                    "Assessora de advocacy", "Assessor de Comunicação", "Auxiliar de Serviços Gerais", "Auxiliar Administrativo/financeiro",
                    "Assistente Administrativo/financeiro", "Assistente socioambiental", "Coordenador Administrativo/financeiro de escritório",
                    "Coordenador Geral administrativo/financeiro", "Coordenador Executivo", "Coordenador de Área", "Coordenador de Programa",
                    "Motorista", "Secretária(o)/Recepcionista", "Técnico de campo", "Técnico em informática", ""]
                    
                    cargo = col1.selectbox("Cargo:", lista_cargos, index=lista_cargos.index(pessoa.get("cargo")))

                    # Programa / Área
                    # Pega o ObjectId atual salvo no banco
                    programa_area_atual = pessoa.get("programa_area")
                    # Converte o ObjectId para nome legível
                    programa_area_nome_atual = id_para_nome_programa.get(programa_area_atual, "")

                    # Selectbox mostra nomes dos programas
                    programa_area_nome = col2.selectbox(
                        "Programa / Área:",
                        lista_programas_areas,
                        index=lista_programas_areas.index(programa_area_nome_atual) if programa_area_nome_atual in lista_programas_areas else 0,
                        key="editar_programa", 
                    )

                    # Após seleção, pega o ObjectId correspondente ao nome
                    programa_area = nome_para_id_programa.get(programa_area_nome)
                    
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
                    coordenador_nome = col3.selectbox(
                        "Nome do(a) coordenador(a):",
                        nomes_coordenadores,
                        index=nomes_coordenadores.index(nome_coordenador_default) if nome_coordenador_default in nomes_coordenadores else 0,
                        key="editr_nome_coordenador"
                    )

                    # 5. Pega o ID do coordenador selecionado (se não for vazio)
                    coordenador_id = None
                    if coordenador_nome:
                        coordenador_id = next(
                            c["id"] for c in coordenadores_possiveis if c["nome"] == coordenador_nome
                        )         

                    
                    st.markdown("---")

                    # Dados bancários
                    col1, col2 = st.columns([1, 1])
                    nome_banco = col1.text_input("Nome do banco:", value=pessoa.get("banco", {}).get("nome_banco", ""))
                    agencia = col2.text_input("Agência:", value=pessoa.get("banco", {}).get("agencia", ""))

                    col1, col2 = st.columns([1, 1])
                    conta = col1.text_input("Conta:", value=pessoa.get("banco", {}).get("conta", ""))


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
                        key="editar_tipo_conta"
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
                            "gestao_fundo_ecos", "gestao_viagens", "gestao_manuais"
                        ]

                    else: # Se não for admin, não aparece a permissão admin disponível
                        # Opções possíveis para o campo "tipo de usuário"
                        opcoes_tipo_usuario = [
                            "coordenador(a)", "gestao_pessoas", "gestao_ferias", "supervisao_ferias", 
                            "gestao_noticias", "gestao_pls", "gestao_projetos_doadores", 
                            "gestao_fundo_ecos", "gestao_viagens", "gestao_manuais"
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
                        key="editar_tipo_usuario"
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
                        

        with aba_contratos:

            # ==============================
            # Lista de projetos disponíveis (para multiselect)
            # ==============================
            lista_projetos = sorted([
                p["nome_do_projeto"] for p in dados_projetos_ispn if p.get("nome_do_projeto", "")
            ])

            if pessoa:
                contratos = pessoa.get("contratos", [])
            else:
                contratos = []


            # Opções de contratos já existentes (exibindo data de início como rótulo)
            opcoes_contratos = [
                f'{c.get("data_inicio", "")} - {c.get("data_fim", "")} - {c.get("status_contrato", "")}'
                for c in contratos
            ]

            # Adiciona sempre a opção de adicionar
            opcoes_contratos = ["", "--Adicionar contrato--"] + opcoes_contratos

            # Selecionar contrato existente ou adicionar
            contrato_selecionado = st.selectbox(
                "Selecione ou adicione um contrato",
                options=opcoes_contratos,
                index=0
            )

            # ==============================
            # Adicionar novo contrato
            # ==============================
            if contrato_selecionado == "--Adicionar contrato--":

                projetos_pagadores_nomes_edit = st.multiselect(
                    "Contratado(a) pelo(s) projeto(s):",
                    lista_projetos
                )
                projetos_pagadores_edit = [
                    nome_para_id_projeto.get(nome)
                    for nome in projetos_pagadores_nomes_edit
                    if nome and nome_para_id_projeto.get(nome)
                ]

                col1, col2 = st.columns([1,1])
                inicio_contrato = col1.date_input("Data de início do contrato:", format="DD/MM/YYYY", value="today")
                fim_contrato = col2.date_input("Data de fim do contrato:", format="DD/MM/YYYY", value=None)

                lista_status_contrato = ["Em vigência", "Encerrado", "Cancelado", "Fonte de recurso temporária", ""]
                status_contrato = st.selectbox("Status do contrato:", lista_status_contrato)

                #data_reajuste = col3.date_input("Data de reajuste:", format="DD/MM/YYYY")

                if st.button("Adicionar contrato"):
                    novo_contrato = {
                        "data_inicio": inicio_contrato.strftime("%d/%m/%Y") if inicio_contrato else "",
                        "data_fim": fim_contrato.strftime("%d/%m/%Y") if fim_contrato else "",
                        "codigo_projeto": "",
                        "status_contrato": status_contrato,
                        "projeto_pagador": projetos_pagadores_edit,
                        "data_reajuste": "",
                        "termos_aditivos": [],
                    }

                    contratos.append(novo_contrato)

                    pessoas.update_one(
                        {"_id": ObjectId(pessoa["_id"])},
                        {"$set": {"contratos": contratos}}
                    )

                    st.success("Novo contrato adicionado com sucesso!")
                    time.sleep(2)
                    st.rerun()

            # ==============================
            # Editar contrato existente
            # ==============================
            elif contrato_selecionado:
                index = opcoes_contratos.index(contrato_selecionado) - 2  # ajusta porque tem "" e "--Adicionar contrato--"
                contrato_atual = contratos[index]

                # ------------------------------
                # Projetos pagadores atuais
                # ------------------------------
                projetos_pagadores_ids_atuais = []
                for pid in contrato_atual.get("projeto_pagador", []):
                    if isinstance(pid, dict) and "$oid" in pid:
                        projetos_pagadores_ids_atuais.append(ObjectId(pid["$oid"]))
                    elif isinstance(pid, ObjectId):
                        projetos_pagadores_ids_atuais.append(pid)

                projetos_pagadores_nomes_atuais = [
                    id_para_nome_projeto.get(pid, "")
                    for pid in projetos_pagadores_ids_atuais
                    if pid in id_para_nome_projeto
                ]

                projetos_pagadores_nomes_edit = st.multiselect(
                    "Contratado(a) pelo(s) projeto(s):",
                    lista_projetos,
                    default=projetos_pagadores_nomes_atuais,
                )
                projetos_pagadores_edit = [
                    nome_para_id_projeto.get(nome)
                    for nome in projetos_pagadores_nomes_edit
                    if nome and nome_para_id_projeto.get(nome)
                ]

                def str_para_date(data_str):
                    if not data_str:
                        return None
                    if isinstance(data_str, datetime.date):
                        return data_str
                    try:
                        return datetime.datetime.strptime(data_str, "%d/%m/%Y").date()
                    except Exception:
                        return None

                col1, col2, col3 = st.columns([1,1,1])
                inicio_contrato = col1.date_input(
                    "Data de início do contrato:",
                    value=str_para_date(contrato_atual.get("data_inicio")),
                    format="DD/MM/YYYY",
                    key=f"inicio_{index}"
                )
                fim_contrato = col2.date_input(
                    "Data de fim do contrato:",
                    value=str_para_date(contrato_atual.get("data_fim")),
                    format="DD/MM/YYYY",
                    key=f"fim_{index}"
                )

                lista_status_contrato = ["Em vigência", "Encerrado", "Cancelado", "Fonte de recurso temporária", ""]
                status_contrato_valor_inicial = contrato_atual.get("status_contrato", "")
                if status_contrato_valor_inicial not in lista_status_contrato:
                    status_contrato_valor_inicial = ""
                status_contrato = st.selectbox(
                    "Status do contrato:",
                    lista_status_contrato,
                    index=lista_status_contrato.index(status_contrato_valor_inicial),
                    key=f"status_{index}"
                )

                data_reajuste_inicial = str_para_date(contrato_atual.get("data_reajuste"))
                data_reajuste = col3.date_input(
                    "Data de reajuste:",
                    value=data_reajuste_inicial,
                    format="DD/MM/YYYY",
                    key=f"reajuste_{index}"
                )

                col1b, col2b = st.columns([4,1])
                with col1b:
                    if st.button("Salvar edição", key=f"salvar_{index}"):
                        contratos[index].update({
                            "data_inicio": inicio_contrato.strftime("%d/%m/%Y") if inicio_contrato else "",
                            "data_fim": fim_contrato.strftime("%d/%m/%Y") if fim_contrato else "",
                            "status_contrato": status_contrato,
                            "projeto_pagador": projetos_pagadores_edit,
                            "data_reajuste": data_reajuste.strftime("%d/%m/%Y") if data_reajuste else ""
                        })

                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"contratos": contratos}}
                        )
                        st.success("Contrato atualizado com sucesso!")
                        time.sleep(2)
                        st.rerun()

                with col2b:
                    if st.button("Excluir contrato", type="secondary", key=f"excluir_{index}"):
                        contratos.pop(index)
                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"contratos": contratos}}
                        )
                        st.success("Contrato excluído com sucesso!")
                        time.sleep(2)
                        st.rerun()
        

        with aba_previdencia:

            if pessoa:
                previdencia = pessoa.get("previdencia", [])
            else:
                previdencia = []

            # Criar lista de opções com apenas anotações do próprio usuário
            opcoes = [
                f'{p["data_contribuicao"].strftime("%d/%m/%Y") if isinstance(p["data_contribuicao"], datetime.datetime) else p["data_contribuicao"]} - {p["valor"]}'
                for p in previdencia
            ]

            # Sempre terá a opção de adicionar
            opcoes_com_vazio = ["", "--Adicionar contribuição--"] + opcoes if opcoes else ["", "--Adicionar contribuição--"]

            # Selecionar contribuição existente ou opção de adicionar
            selecionada = st.selectbox(
                "Selecione uma contribuição",
                options=opcoes_com_vazio,
                index=0,
                key="select_box_previdencia"
            )

            # ============================
            # Adicionar nova contribuição
            # ============================
            if selecionada == "--Adicionar contribuição--":
                
                valor_contribuicao = st.number_input("Valor da contribuição:", step=50, min_value=0)

                if st.button("Adicionar contribuição", icon=":material/check:"):
                    if valor_contribuicao:
                        nova_contribuicao = {
                            "data_contribuicao": datetime.datetime.today().strftime("%d/%m/%Y"),
                            "valor": valor_contribuicao,
                        }

                        # Adiciona a nova contribuição à lista existente
                        previdencia.append(nova_contribuicao)

                        # Atualiza no Mongo
                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"previdencia": previdencia}}
                        )

                        st.success("Nova contribuição adicionada com sucesso!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.warning("O campo do valor deve ser preenchido.")

            # ============================
            # Edição de contribuição existente
            # ============================
            elif selecionada:
                index = opcoes.index(selecionada)  # posição na lista
                contribuicao_atual = previdencia[index]

                # Editar campos
                data_atual = contribuicao_atual.get("data_contribuicao")
                if isinstance(data_atual, str):
                    try:
                        data_atual = datetime.datetime.strptime(data_atual, "%d/%m/%Y")
                    except:
                        data_atual = datetime.datetime.today()

                #st.divider()

                novo_valor = st.number_input("Valor da contribuição", value=int(contribuicao_atual.get("valor", 0)), step=50, min_value=0)

                col1, col2 = st.columns([2,1])

                with col1:
                    if st.button("Salvar edição", icon=":material/edit:", key="contribuicao_previdencia"):
                        previdencia[index]["valor"] = novo_valor

                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"previdencia": previdencia}}
                        )

                        st.success("Contribuição atualizada com sucesso!")
                        time.sleep(2)
                        st.rerun()

                with col2:
                    if st.button("Excluir contribuição", icon=":material/delete:"):
                        previdencia.pop(index)
                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"previdencia": previdencia}}
                        )

                        st.success("Contribuição excluída com sucesso!")
                        time.sleep(2)
                        st.rerun()

        with aba_anotacoes:
            
            if pessoa:
                anotacoes = pessoa.get("anotacoes", [])
            else:
                anotacoes = []
                
            usuario_logado = st.session_state.get("nome", "Desconhecido")

            # Criar lista de opções com apenas anotações do próprio usuário
            opcoes = [
                f'{a["data_anotacao"].strftime("%d/%m/%Y") if isinstance(a["data_anotacao"], datetime.datetime) else a["data_anotacao"]} - {a["autor"][:30]}'
                for a in anotacoes if a.get("autor") == usuario_logado
            ]

            # Sempre terá a opção de adicionar
            opcoes_com_vazio = ["", "--Adicionar anotação--"] + opcoes if opcoes else ["", "--Adicionar anotação--"]

            # Selecionar anotação existente ou opção de adicionar
            selecionada = st.selectbox(
                "Selecione uma anotação",
                options=opcoes_com_vazio,
                index=0
            )

            # ============================
            # Adicionar nova anotação
            # ============================
            if selecionada == "--Adicionar anotação--":
                
                anotacao_texto = st.text_area("Digite a anotação", key="nova_anotacao_texto")

                if st.button("Adicionar anotação", icon=":material/check:"):
                    if anotacao_texto.strip():
                        nova_anotacao = {
                            "data_anotacao": datetime.datetime.today().strftime("%d/%m/%Y %H:%M"),
                            "autor": usuario_logado,
                            "anotacao": anotacao_texto.strip()
                        }

                        # Adiciona a nova anotação à lista existente
                        anotacoes.append(nova_anotacao)

                        # Atualiza no Mongo
                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"anotacoes": anotacoes}}
                        )

                        st.success("Nova anotação adicionada com sucesso!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.warning("O campo da anotação não pode estar vazio.")

            # ============================
            # Edição de anotação existente
            # ============================
            elif selecionada:
                # Índice real dentro da lista completa de anotações
                index = [i for i, a in enumerate(anotacoes) if a.get("autor") == usuario_logado][opcoes.index(selecionada)]
                anotacao_atual = anotacoes[index]["anotacao"]

                nova_texto = st.text_area("Editar anotação", value=anotacao_atual or "")

                col1, col2 = st.columns([3,1])

                with col1:
                    if st.button("Salvar edição", icon=":material/edit:"):
                        anotacoes[index]["anotacao"] = nova_texto.strip()
                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"anotacoes": anotacoes}}
                        )
                        st.success("Anotação atualizada com sucesso!")
                        time.sleep(2)
                        st.rerun()

                with col2:
                    if st.button("Excluir anotação", icon=":material/delete:"):
                        # Remove a anotação selecionada
                        anotacoes.pop(index)
                        pessoas.update_one(
                            {"_id": ObjectId(pessoa["_id"])},
                            {"$set": {"anotacoes": anotacoes}}
                        )
                        st.success("Anotação excluída com sucesso!")
                        time.sleep(2)
                        st.rerun()

       
    elif nome_selecionado == "--Adicionar colaborador--":

         # SelectBox fora do formulário
        tipo_contratacao = st.selectbox(
            "Tipo de contratação:",
            ["","PJ1", "PJ2", "CLT", "Estagiário"],
            index=0,
        )

        if tipo_contratacao in ["PJ1", "PJ2"]:

            # Formulário para cadastro, limpa os campos após envio
            with st.form("form_cadastro_colaborador", clear_on_submit=True, border=False):
            
                st.markdown("#### Informações Gerais")

                # Layout com colunas para inputs lado a lado
                col1, col2 = st.columns([1, 1])
                
                # Nome
                nome = col1.text_input("Nome completo:")
                
                # Gênero
                genero = col2.selectbox("Gênero:", ["Masculino", "Feminino", "Não binário", "Outro"], index=None, placeholder="")

                col1, col2 = st.columns([1, 1])
                
                escolaridade = col1.selectbox("Escolaridade:", ["Ensino fundamental", "Ensino médio", "Graduação", "Pós-graduação", 
                                                                "Mestrado", "Doutorado"], index=None, placeholder="")
                
                raca = col2.selectbox("Raça:", ["Amarelo", "Branco", "Índigena", "Pardo", "Preto"], index=None, placeholder="")

                col1, col2 = st.columns([1, 1])
                
                # CPF e RG
                cpf = col1.text_input("CPF:", placeholder="000.000.000-00")
                rg = col2.text_input("RG e órgão emissor:")

                col1, col2 = st.columns([1, 1])

                cnpj = col1.text_input("CNPJ:", placeholder="00.000.000/0000-00")
                nome_empresa = col2.text_input("Nome da empresa:")

                col1, col2, col3 = st.columns([1, 2, 2])
                
                # Data de nascimento
                data_nascimento = col1.date_input("Data de nascimento:", format="DD/MM/YYYY", value=None)
                
                # Telefone
                telefone = col2.text_input("Telefone:")
                
                # E-mail
                email = col3.text_input("E-mail:")
                
                col1, col2 = st.columns([1,1])
                
                escritorio = col1.selectbox("Escritório:", ["Brasília", "Santa Inês"], index=None, placeholder="")
                
                #tipo_contratacao = col2.selectbox("Tipo de contratação:", ["PJ1", "PJ2", "CLT", "Estagiário"], index=None, placeholder="")
                
                # if tipo_contratacao == ["PJ1", "PJ2"]:
                #     col1, col2 = st.columns([1,1])
                    
                #     cnpj = col1.text_input("CNPJ", placeholder="00.000.000/0000-00")
                #     nome_empresa = col2.text_input("Nome da empresa", placeholder="")

            col1, col2 = st.columns(2)
            


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
            coordenador = col1.selectbox("Nome do(a) coordenador(a):", nomes_coordenadores, index=None, placeholder="")

            # Por fim, pega o id do coordenador
            coordenador_id = None
            for c in coordenadores_possiveis:
                if c["nome"] == coordenador:
                    coordenador_id = c["id"]
                    break


            # Programa / Área
            # Lista ordenada dos programas/áreas para seleção
            lista_programas_areas = sorted(nome_para_id_programa.keys())
            programa_area_nome = col2.selectbox("Programa / Área:", lista_programas_areas, index=None, placeholder="")
            programa_area = nome_para_id_programa.get(programa_area_nome)


            col1, col2 = st.columns([3, 2])

            # Cargo
            cargo = col1.selectbox("Cargo:", opcoes_cargos, index=None, placeholder="")

            # Programa / Área
            # Lista ordenada dos programas/áreas para seleção
            lista_programas_areas = sorted(nome_para_id_programa.keys())
            programa_area_nome = col2.selectbox("Programa / Área:", lista_programas_areas, index=None, placeholder="")
            programa_area = nome_para_id_programa.get(programa_area_nome)


            col1, col2 = st.columns([3, 2])

            # Cargo
            cargo = col1.selectbox("Cargo:", opcoes_cargos, index=None, placeholder="")

            st.divider()

            st.markdown("#### Contrato")

            # Projeto pagador (lista de nomes para exibir)
            lista_projetos = sorted({
                p["nome_do_projeto"]
                for p in dados_projetos_ispn
                if p.get("nome_do_projeto", "") != ""
            })

            # Exibe multiselect com nomes
            projeto_pagador_nome = st.multiselect(
                "Contratado(a) pelo projeto:",
                lista_projetos,
                key="cadastrar_projeto_pagador",
            )

            # Converte os nomes escolhidos de volta para ObjectId
            projeto_pagador = [nome_para_id_projeto.get(nome) for nome in projeto_pagador_nome]

            # Datas de início e fim de contrato
            with st.container(horizontal=True):
                inicio_contrato = st.date_input("Data de início do contrato:", format="DD/MM/YYYY", value=None)
                fim_contrato = st.date_input("Data de fim do contrato:", format="DD/MM/YYYY", value=None)
                
            status_contrato = st.selectbox("Status do contrato:", ["Em vigência", "Encerrado", "Cancelado", "Fonte de recurso temporária"], index=0, placeholder="")

            st.markdown("---")
            
            # Dados Bancários
            st.markdown("#### Dados bancários")
            
            col1, col2 = st.columns([1, 1])
            nome_banco = col1.text_input("Nome do banco:")
            agencia = col2.text_input("Agência:")
            
            col1, col2 = st.columns([1, 1])
            conta = col1.text_input("Conta:")
            tipo_conta = col2.selectbox("Tipo de conta:", ["Conta Corrente", "Conta Poupança", "Conta Salário"], index=None, placeholder="")

            st.markdown("---")
            st.markdown("#### Férias")
            
            col1, col2 = st.columns([1, 2])
            
            # Férias
            a_receber = col1.number_input("Dias de férias a receber:", step=1, min_value=22)

            # Variáveis de férias com valores iniciais
            residual_ano_anterior = 0
            valor_inicial_ano_atual = 0
            total_gozado = 0
            saldo_atual = residual_ano_anterior + valor_inicial_ano_atual
            
            st.divider()
            
            st.markdown("#### Anotações")
            
            hoje = datetime.datetime.today().strftime("%d/%m/%Y")

            st.write(f"Data: {hoje}")
            
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
                    
                    # nova_anotacao = {
                    #     "data_anotacao": datetime.datetime.today(),
                    #     "autor": st.session_state.get("nome", "Desconhecido"),
                    #     "anotacao": anotacao_texto.strip()
                    # }

                    # Monta o documento para inserção no MongoDB
                    novo_documento = {
                        "nome_completo": nome,
                        "CPF": cpf,
                        "RG": rg,
                        "cnpj": cnpj,
                        "nome_empresa": nome_empresa,
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
                        "data_reajuste": "",  # novo campo
                        "contratos": [
                            {
                                "data_inicio": inicio_contrato.strftime("%d/%m/%Y") if inicio_contrato else "",
                                "data_fim": fim_contrato.strftime("%d/%m/%Y") if fim_contrato else "",
                                "codigo_projeto": "",
                                "status_contrato": status_contrato,
                                "projeto_pagador": projeto_pagador if projeto_pagador else [],
                                "termos_aditivos": [],
                            }
                        ],
                        "anotacoes": [
                            {
                                "data_anotacao": datetime.datetime.today().strftime("%d/%m/%Y %H:%M"),
                                "autor": st.session_state.get("nome", "Desconhecido"),
                                "anotacao": anotacao_texto.strip() if anotacao_texto else ""
                            }
                        ]
                    }

                    # Insere o novo colaborador no banco
                    pessoas.insert_one(novo_documento)
                    st.success(f"Colaborador(a) **{nome}** cadastrado(a) com sucesso!", icon=":material/thumb_up:")
                    time.sleep(2)
                    st.rerun()  # Recarrega a página para atualizar dados

        
        elif tipo_contratacao in ["CLT", "Estagiário"]:
            # Formulário para cadastro, limpa os campos após envio
            with st.form("form_cadastro_colaborador", clear_on_submit=True, border=False):
            
                st.markdown("#### Informações Gerais")

                # Layout com colunas para inputs lado a lado
                col1, col2 = st.columns([1, 1])
                
                # Nome
                nome = col1.text_input("Nome completo:")
                
                # Gênero
                genero = col2.selectbox("Gênero:", ["Masculino", "Feminino", "Não binário", "Outro"], index=None, placeholder="")

                col1, col2 = st.columns([1, 1])
                
                escolaridade = col1.selectbox("Escolaridade:", ["Ensino fundamental", "Ensino médio", "Graduação", "Pós-graduação", 
                                                                "Mestrado", "Doutorado"], index=None, placeholder="")
                
                raca = col2.selectbox("Raça:", ["Amarelo", "Branco", "Índigena", "Pardo", "Preto"], index=None, placeholder="")

                col1, col2 = st.columns([1, 1])
                
                # CPF e RG
                cpf = col1.text_input("CPF:", placeholder="000.000.000-00")
                rg = col2.text_input("RG e órgão emissor:")

                col1, col2, col3 = st.columns([1, 2, 2])
                
                # Data de nascimento, telefone e e-mail
                data_nascimento_str = pessoa.get("data_nascimento", "")
                if data_nascimento_str:
                    data_nascimento = datetime.strptime(data_nascimento_str, "%d/%m/%Y")
                else:
                    data_nascimento = None
                data_nascimento = col1.date_input("Data de nascimento:", format="DD/MM/YYYY", value=data_nascimento, disabled=desabilitar)
                telefone = col2.text_input("Telefone:", value=pessoa.get("telefone", ""), disabled=desabilitar)
                email = col3.text_input("E-mail:", value=pessoa.get("e_mail", ""), disabled=desabilitar)
                



                col1, col2 = st.columns([1, 1])



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
                coordenador_nome = col1.selectbox(
                    "Nome do(a) coordenador(a):",
                    nomes_coordenadores,
                    index=nomes_coordenadores.index(nome_coordenador_default) if nome_coordenador_default in nomes_coordenadores else 0,
                    key="editr_nome_coordenador",
                    disabled=desabilitar
                )

                # 5. Pega o ID do coordenador selecionado (se não for vazio)
                coordenador_id = None
                if coordenador_nome:
                    coordenador_id = next(
                        c["id"] for c in coordenadores_possiveis if c["nome"] == coordenador_nome
                    )         





                # Programa / Área
                # Pega o ObjectId atual salvo no banco
                programa_area_atual = pessoa.get("programa_area")
                # Converte o ObjectId para nome legível
                programa_area_nome_atual = id_para_nome_programa.get(programa_area_atual, "")

                # Selectbox mostra nomes dos programas
                programa_area_nome = col2.selectbox(
                    "Programa / Área:",
                    lista_programas_areas,
                    index=lista_programas_areas.index(programa_area_nome_atual) if programa_area_nome_atual in lista_programas_areas else 0,
                    key="editar_programa", 
                    disabled=desabilitar
                )

                # Após seleção, pega o ObjectId correspondente ao nome
                programa_area = nome_para_id_programa.get(programa_area_nome)




                col1, col2 = st.columns([3, 2])


                # Lista de cargos com opção vazia no início
                opcoes_cargos_com_vazio = [""] + opcoes_cargos

                # Valor vindo do banco de dados
                cargo_salvo = pessoa.get("cargo", "")

                # Tenta encontrar o índice do cargo na lista
                try:
                    index_cargo = opcoes_cargos_com_vazio.index(cargo_salvo)
                except ValueError:
                    index_cargo = 0  # seleciona a opção vazia

                # Selectbox com o valor padrão
                cargo = col1.selectbox("Cargo:", opcoes_cargos_com_vazio, index=index_cargo)




                # # Cargo

                # # Valor vindo do banco de dados
                # cargo_salvo = pessoa.get("cargo", "")  # por exemplo, "Analista de dados"

                # # Tenta encontrar o índice do cargo na lista
                # try:
                #     index_cargo = opcoes_cargos.index(cargo_salvo)
                # except ValueError:
                #     index_cargo = 0  # se não encontrar, seleciona o primeiro item

                # # Selectbox com o valor padrão
                # cargo = col1.selectbox("Cargo:", opcoes_cargos, index=index_cargo)



                # cargo = col1.selectbox("Cargo:", opcoes_cargos, index=None, placeholder="")



                # Projeto pagador
                # Lista de projetos (com opção vazia no início, se quiser)
                lista_projetos = [""] + sorted([p["nome_do_projeto"] for p in dados_projetos_ispn if p.get("nome_do_projeto", "")])
                # Nome atual do projeto pagador
                projeto_pagador_nome_atual = pessoa.get("projeto_pagador", "")
                projeto_pagador_nome_atual = id_para_nome_projeto.get(projeto_pagador_nome_atual, "")
                # Seleção com valor padrão
                index_padrao = lista_projetos.index(projeto_pagador_nome_atual) if projeto_pagador_nome_atual in lista_projetos else 0
                projeto_pagador_nome_edit = st.selectbox(
                    "Contratado(a) pelo projeto:",
                    lista_projetos,
                    index=index_padrao,
                    # disabled=desabilitar
                )
                # ID correspondente ao projeto selecionado
                projeto_pagador_edit = nome_para_id_projeto.get(projeto_pagador_nome_edit)

                # Converte os nomes escolhidos de volta para ObjectId
                projeto_pagador = [nome_para_id_projeto.get(nome) for nome in projeto_pagador_nome]

                # Datas de início e fim de contrato
                with st.container(horizontal=True):
                    inicio_contrato = st.date_input("Data de início do contrato:", format="DD/MM/YYYY", value=None)
                    fim_contrato = st.date_input("Data de fim do contrato:", format="DD/MM/YYYY", value=None)
                    
                status_contrato = st.selectbox("Status do contrato:", ["Em vigência", "Encerrado", "Cancelado", "Fonte de recurso temporária"], index=0, placeholder="")

                st.markdown("---")
                
                # Dados Bancários
                st.markdown("#### Dados bancários")
                
                col1, col2 = st.columns([1, 1])
                nome_banco = col1.text_input("Nome do banco:")
                agencia = col2.text_input("Agência:")
                
                col1, col2 = st.columns([1, 1])
                conta = col1.text_input("Conta:")
                tipo_conta = col2.selectbox("Tipo de conta:", ["Conta Corrente", "Conta Poupança", "Conta Salário"], index=None, placeholder="")

                st.markdown("---")
                st.markdown("#### Férias")
                
                col1, col2 = st.columns([1, 2])
                
                # Férias
                a_receber = col1.number_input("Dias de férias a receber:", step=1, min_value=22)

                # Variáveis de férias com valores iniciais
                residual_ano_anterior = 0
                valor_inicial_ano_atual = 0
                total_gozado = 0
                saldo_atual = residual_ano_anterior + valor_inicial_ano_atual
                
                st.divider()
                
                st.markdown("#### Anotações")
                
                hoje = datetime.datetime.today().strftime("%d/%m/%Y")

                st.write(f"Data: {hoje}")
                
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
                            "data_reajuste": "",  # novo campo
                            "contratos": [
                                {
                                    "data_inicio": inicio_contrato.strftime("%d/%m/%Y") if inicio_contrato else "",
                                    "data_fim": fim_contrato.strftime("%d/%m/%Y") if fim_contrato else "",
                                    "codigo_projeto": "",
                                    "status_contrato": status_contrato,
                                    "projeto_pagador": projeto_pagador if projeto_pagador else [],
                                    "termos_aditivos": [],
                                }
                            ],
                            "anotacoes": [
                                {
                                    "data_anotacao": datetime.datetime.today().strftime("%d/%m/%Y %H:%M"),
                                    "autor": st.session_state.get("nome", "Desconhecido"),
                                    "anotacao": anotacao_texto.strip() if anotacao_texto else ""
                                }
                            ]
                        }

                        # Insere o novo colaborador no banco
                        pessoas.insert_one(novo_documento)
                        st.success(f"Colaborador(a) **{nome}** cadastrado(a) com sucesso!", icon=":material/thumb_up:")
                        time.sleep(2)
                        st.rerun()  # Recarrega a página para atualizar dados
   

######################################################################################################
# MAIN
######################################################################################################

# Botão de gerenciar colaboradores só para alguns tipos de usuário
# Container horizontal de botões
container_botoes = st.container(horizontal=True, horizontal_alignment="right")
# Roteamento de tipo de usuário
if set(st.session_state.tipo_usuario) & {"admin", "gestao_pessoas"}:

    # Botão para abrir o modal de cadastro
    container_botoes.button("Gerenciar colaboradores", on_click=gerenciar_pessoas, icon=":material/group:")
    st.write('')

aba_pessoas, aba_contratos = st.tabs([":material/person: Colaboradores", ":material/contract: Contratos"])

with aba_pessoas:

    st.write('')

    # Programas
    programas = [p["nome_programa_area"] for p in dados_programas]

    # Projetos
    projetos = sorted([p["sigla"] for p in dados_projetos_ispn])

    # Organizar o dataframe por ordem alfabética de nome
    df_pessoas = df_pessoas.sort_values(by="Nome")


    # Filtros
    with st.container(horizontal=True):
        programa = st.selectbox("Programa / Área", ["Todos"] + programas)
        projeto = st.selectbox("Projeto", ["Todos"] + projetos) 
        status = st.selectbox("Status", ["ativo", "inativo"], index=0)


    # Copia o DataFrame original
    df_pessoas_filtrado = df_pessoas.copy()


    # Aplica os filtros
    if programa != "Todos":
        df_pessoas_filtrado = df_pessoas_filtrado[df_pessoas_filtrado["Programa/Área"] == programa]

    if projeto != "Todos":
        df_pessoas_filtrado = df_pessoas_filtrado[df_pessoas_filtrado["Projeto Pagador"].str.contains(projeto)]

    df_pessoas_filtrado = df_pessoas_filtrado[df_pessoas_filtrado["Status"] == status]


    # Exibir DataFrame --------------------------------------------------
    st.write('')
    st.subheader(f'{len(df_pessoas_filtrado)} colaboradores(as)')
    st.write('')

    # Remove as colunas indesejadas
    # df_pessoas_filtrado = df_pessoas_filtrado.drop(columns=["Status", "Gênero"], errors="ignore")

    st.dataframe(
        df_pessoas_filtrado.rename(columns={"Projeto Pagador": "Projeto"}), 
        hide_index=True)




    # Gráficos 
    col1, col2 = st.columns(2)

    # GRÁFICO DE PESSOAS POR PROGRAMA/ÁREA -----------------------------------------------------------

    # Agrupar e ordenar
    programa_counts = df_pessoas_filtrado['Programa/Área'].value_counts().reset_index()
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
                        'staticPlot': True  # desativa pan, zoom e todas as interações
                    })




    # GRÁFICO DE PESSOAS POR PROJETO ------------------------------------------------

    # st.write(df_pessoas_filtrado)

    # Projeto


    # separa os nomes que estão na mesma célula por vírgula e transforma em linhas separadas
    df_explodido = df_pessoas_filtrado.assign(
        **{'Projeto Pagador': df_pessoas_filtrado['Projeto Pagador'].str.split(',\s*')}
    ).explode('Projeto Pagador')

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
        title='Distribuição de Pessoas por Projeto',
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
    col2.plotly_chart(
        fig,
        use_container_width=True,
        config={'staticPlot': True}
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
        use_container_width=True,
        config={'staticPlot': True}
    )








    # Gráfico de pessoas por Cargo ------------------------------------------------

    # Cargo


    # substitui valores vazios ou NaN por "Não informado"
    df_pessoas_filtrado['Cargo_tratado'] = df_pessoas_filtrado['Cargo'].replace("", "Não informado")
    df_pessoas_filtrado['Cargo_tratado'] = df_pessoas_filtrado['Cargo_tratado'].fillna("Não informado")

    fig = px.pie(
        df_pessoas_filtrado,
        names='Cargo_tratado',  # usa a coluna tratada
        title='Pessoas por Cargo',
        hole=0
    )

    # adiciona valores dentro das fatias
    fig.update_traces(textposition='inside', textinfo='percent+label', texttemplate='%{percent:.0%} %{label}')

    # remove legenda
    fig.update_layout(showlegend=False)

    # desativa interação
    col2.plotly_chart(
        fig,
        use_container_width=True,
        config={'staticPlot': True}
    )





    # --- Raça ---
    df_pessoas_filtrado['Raça_tratado'] = df_pessoas_filtrado['Raça'].replace("", "Não informado")
    df_pessoas_filtrado['Raça_tratado'] = df_pessoas_filtrado['Raça_tratado'].fillna("Não informado")

    fig = px.pie(
        df_pessoas_filtrado,
        names='Raça_tratado',
        title='Distribuição de Pessoas por Raça',
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
        use_container_width=True,
        # config={'staticPlot': True}
    )


    # --- Escolaridade ---
    df_pessoas_filtrado['Escolaridade_tratado'] = df_pessoas_filtrado['Escolaridade'].replace("", "Não informado")
    df_pessoas_filtrado['Escolaridade_tratado'] = df_pessoas_filtrado['Escolaridade_tratado'].fillna("Não informado")

    fig = px.pie(
        df_pessoas_filtrado,
        names='Escolaridade_tratado',
        title='Distribuição de Pessoas por Escolaridade',
        hole=0
    )

    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        texttemplate='%{percent:.0%} %{label}'
    )

    fig.update_layout(showlegend=False)

    col1.plotly_chart(
        fig,
        use_container_width=True,
        # config={'staticPlot': True}
    )






if set(st.session_state.tipo_usuario) & {"admin", "gestao_pessoas"}:
    with aba_contratos:

        # Transformar para a nova estrutura (pega o primeiro contrato válido da lista)
        lista_tratada = []
        for pessoa in dados_pessoas:
            nome = pessoa.get("nome_completo", "Sem nome")
            contratos = pessoa.get("contratos", [])

            if contratos:
                contrato = contratos[0]  

                lista_tratada.append({
                    "Nome": nome,
                    "Início do contrato": contrato.get("data_inicio"),
                    "Fim do contrato": contrato.get("data_fim")
                })

        # Criar dataframe com os dados
        df_equipe = pd.DataFrame(lista_tratada)

        if not df_equipe.empty:
            # Converter para datetime (aceitando strings no formato brasileiro ou ISO)
            df_equipe["Início do contrato"] = pd.to_datetime(
                df_equipe["Início do contrato"], dayfirst=True, errors="coerce"
            )
            df_equipe["Fim do contrato"] = pd.to_datetime(
                df_equipe["Fim do contrato"], dayfirst=True, errors="coerce"
            )

            # 🔹 Manter apenas quem tem início e fim preenchidos
            df_equipe = df_equipe[
                df_equipe["Início do contrato"].notna() & df_equipe["Fim do contrato"].notna()
            ]

            # Calcular dias restantes
            hoje = pd.Timestamp(datetime.date.today())  # garante formato datetime64
            df_equipe["Dias restantes"] = (df_equipe["Fim do contrato"] - hoje).dt.days


            # Criar coluna de cor: vermelho se < 90 dias, azul caso contrário
            df_equipe["Cor"] = df_equipe["Dias restantes"].apply(
                lambda x: "red" if x < 90 else "#4C78A8"
            )

            # Ordenar por data de fim (decrescente)
            df_equipe = df_equipe.sort_values(by="Fim do contrato", ascending=False)

            # Definir ordem do eixo Y de acordo com a ordenação
            categorias_y = df_equipe["Nome"].tolist()

            # Calcular altura do gráfico dinamicamente
            altura_base = 200
            altura_extra = 40 * len(df_equipe)  # 40px por colaborador
            altura = altura_base + altura_extra

            # Criar gráfico de timeline
            fig = px.timeline(
                df_equipe,
                x_start="Início do contrato",
                x_end="Fim do contrato",
                y="Nome",
                color="Cor",  # 🔹 Agora usa a coluna de cor
                color_discrete_map="identity",  # Mantém as cores exatas que definimos
                height=altura
            )

            # Forçar a ordem no eixo Y
            fig.update_yaxes(categoryorder="array", categoryarray=categorias_y)

            # Linha vertical de hoje
            fig.add_vline(
                x=hoje,
                line_width=1,
                line_dash="dash",
                line_color="gray"
            )

            # Layout do gráfico
            fig.update_layout(
                yaxis_title=None,
                xaxis_title="Duração do contrato",
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum contrato válido encontrado.")
