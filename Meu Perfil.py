import streamlit as st
import pandas as pd 
import datetime
import time
from funcoes_auxiliares import conectar_mongo_portal_ispn


# Configura a página do Streamlit para layout mais amplo
st.set_page_config(layout="wide")

# Exibe o logo do ISPN na página
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

# Cabeçalho da página
st.header("Meu Perfil")
st.write('')  
st.write('') 


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################

# Conecta no banco MongoDB usando função auxiliar
db = conectar_mongo_portal_ispn()

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

# PESSOA

# Buscar a pessoa logada
pessoa_logada = next(
    (p for p in dados_pessoas if p["nome_completo"] == st.session_state.get("nome")), None
)

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
            "Status": pessoa.get("status", ""),
            "Tipo Contratação": pessoa.get("tipo_contratacao", ""),
            "Escritório": pessoa.get("escritorio", ""),
        })

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

# PROJETOS
# Filtra só os projetos em que a sigla não está vazia
dados_projetos_ispn = [projeto for projeto in dados_projetos_ispn if projeto["sigla"] != ""]


######################################################################################################
# MAIN
######################################################################################################


if pessoa_logada:
    aba_info, aba_contratos, aba_previdencia = st.tabs(
        [":material/info: Informações gerais", ":material/contract: Contratos", ":material/finance_mode: Previdência"]
    )

    # ============ ABA INFORMAÇÕES GERAIS ============
    with aba_info:
        st.subheader("Informações gerais")

        col1, col2, col3 = st.columns([3,1,1])

        editar = col3.toggle("Habilitar edição")

        st.write("")

        if not editar:

            # ---------------- MODO SOMENTE LEITURA ----------------

            col1, col2, col3, col4 = st.columns([2,2,1,2])

            col1.write(f"**Nome completo:** {pessoa_logada.get('nome_completo','')}")
            col1.write(f"**Tipo de contratação:** {pessoa_logada.get('tipo_contratacao','')}")
            col1.write(f"**CPF:** {pessoa_logada.get('CPF','')}")
            col1.write(f"**RG:** {pessoa_logada.get('RG','')}")

            col2.write(f"**Telefone:** {pessoa_logada.get('telefone','')}")
            col2.write(f"**E-mail:** {pessoa_logada.get('e_mail','')}")
            col2.write(f"**Data de nascimento:** {pessoa_logada.get('data_nascimento','')}")
            col2.write(f"**Escolaridade:** {pessoa_logada.get('escolaridade','')}")

            col3.write(f"**Gênero:** {pessoa_logada.get('gênero','')}")
            col3.write(f"**Raça:** {pessoa_logada.get('raca','')}")
            col3.write(f"**Escritório:** {pessoa_logada.get('escritorio','')}")
            col3.write(f"**Cargo:** {pessoa_logada.get('cargo','')}")
            
            col4.write(f"**Programa/Área:** {id_para_nome_programa.get(pessoa_logada.get('programa_area'),'')}")
            # se não tiver coordenador mostra vazio
            coord_atual = next((c for c in coordenadores_possiveis
                                if str(c["id"]) == str(pessoa_logada.get("coordenador"))), None)
            col4.write(f"**Coordenador:** {coord_atual['nome'] if coord_atual else ''}")

            # ===============================
            # CAMPOS ADICIONAIS SE FOR PJ
            # ===============================
            if pessoa_logada.get("tipo_contratacao") in ["PJ1", "PJ2"]:
                col4.write(f"**Nome da empresa:** {pessoa_logada.get('nome_empresa','')}")
                col4.write(f"**CNPJ:** {pessoa_logada.get('cnpj','')}")

            st.subheader("Dados bancários")

            st.write("")

            col1, col2, col3, col4 = st.columns(4)

            col1.write(f"**Banco:** {pessoa_logada.get('banco',{}).get('nome_banco','')}")
            col1.write(f"**Agência:** {pessoa_logada.get('banco',{}).get('agencia','')}")
            col1.write(f"**Conta:** {pessoa_logada.get('banco',{}).get('conta','')}")
            col1.write(f"**Tipo de conta:** {pessoa_logada.get('banco',{}).get('tipo_conta','')}")

        else:
            # ---------------- MODO EDIÇÃO ----------------

            col1, col2 = st.columns(2)

            tipo_contratacao = col1.text_input(
                "Tipo de contratação",
                value=pessoa_logada.get("tipo_contratacao", ""), 
                disabled=True
            )

            nome = col2.text_input(
                "Nome completo",
                value=pessoa_logada.get("nome_completo", "")
            )

            col1, col2, col3, col4 = st.columns(4)
            cpf = col1.text_input("CPF", value=pessoa_logada.get("CPF", ""))
            rg = col2.text_input("RG", value=pessoa_logada.get("RG", ""))
            telefone = col3.text_input("Telefone", value=pessoa_logada.get("telefone", ""))
            email = col4.text_input("E-mail", value=pessoa_logada.get("e_mail", ""))

            # ===============================
            # CAMPOS ADICIONAIS SE FOR PJ
            # ===============================
            cnpj, nome_empresa = None, None
            if tipo_contratacao in ["PJ1", "PJ2"]:
                col1, col2 = st.columns([3, 2])
                nome_empresa = col1.text_input(
                    "Nome da empresa:",
                    value=pessoa_logada.get("nome_empresa", "")
                )
                cnpj = col2.text_input(
                    "CNPJ:",
                    value=pessoa_logada.get("cnpj", ""),
                    placeholder="00.000.000/0000-00"
                )

            col1, col2, col3 = st.columns(3)
            
            lista_generos = ['Masculino', 'Feminino', 'Não binário', 'Outro']
            genero_index = lista_generos.index(pessoa_logada.get("gênero", "Masculino")) if pessoa_logada.get("gênero") in lista_generos else 0
            genero = col1.selectbox("Gênero", lista_generos, index=genero_index)

            lista_raca = ["Amarelo", "Branco", "Índigena", "Pardo", "Preto", ""]
            valor_raca = pessoa_logada.get("raca", "")
            index_raca = lista_raca.index(valor_raca) if valor_raca in lista_raca else 0

            raca = col2.selectbox("Raça", lista_raca, index=index_raca)

            data_nascimento_str = pessoa_logada.get("data_nascimento", "")
            data_nascimento_val = datetime.datetime.strptime(data_nascimento_str, "%d/%m/%Y").date() if data_nascimento_str else None
            data_nascimento = col3.date_input(
                "Data de nascimento",
                value=data_nascimento_val,
                format="DD/MM/YYYY"
            )

            col1, col2, col3 = st.columns(3)

            lista_escolaridade = ["Ensino fundamental", "Ensino médio", "Curso técnico", "Graduação", "Pós-graduação", "Mestrado", "Doutorado", ""]
            valor_escolaridade = pessoa_logada.get("escolaridade", "")
            index_escolaridade= lista_escolaridade.index(valor_escolaridade) if valor_escolaridade in lista_escolaridade else 0
            escolaridade = col1.selectbox("Escolaridade", lista_escolaridade, index=index_escolaridade)
            
            cargo = col2.text_input("Cargo", value=pessoa_logada.get("cargo", ""), disabled=True)

            lista_escritorio = ["Brasília", "Santa Inês", ""]
            valor_escritorio = pessoa_logada.get("escritorio", "")
            index_escritorio= lista_escritorio.index(valor_escritorio) if valor_escritorio in lista_escritorio else 0
            escritorio = col3.selectbox("Escritório", lista_escritorio, index=index_escritorio)

            col1, col2 = st.columns(2)
            
            # Programa/Área
            programa_area_nome_atual = id_para_nome_programa.get(
                pessoa_logada.get("programa_area"), ""
            )
            programa_area_nome = col1.text_input(
                "Programa / Área",
                value=programa_area_nome_atual,  # aqui é value e não index
                key="editar_programa",
                disabled=True
            )

            # Coordenador
            coordenador_atual_id = pessoa_logada.get("coordenador")
            coordenador_encontrado = next(
                (c for c in coordenadores_possiveis if str(c["id"]) == str(coordenador_atual_id)),
                None
            )
            nome_coordenador_default = coordenador_encontrado["nome"] if coordenador_encontrado else ""

            nome_coordenador = col2.text_input(
                "Coordenador",
                value=nome_coordenador_default,
                key="editar_coordenador",
                disabled=True
            )

            col1, col2 = st.columns(2)

            nome_banco = col1.text_input("Nome do banco:", value=pessoa_logada.get("banco", {}).get("nome_banco", ""))
            agencia = col2.text_input("Agência:", value=pessoa_logada.get("banco", {}).get("agencia", ""))

            col1, col2 = st.columns(2)
            conta = col1.text_input("Conta:", value=pessoa_logada.get("banco", {}).get("conta", ""))

            opcoes_conta = ["", "Conta Corrente", "Conta Poupança", "Conta Salário"]

            tipo_conta_atual = pessoa_logada.get("banco", {}).get("tipo_conta", "")

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

            st.write("")

            # Prepara o dicionário de atualização
            update_dict = {
                "tipo_contratacao": tipo_contratacao,
                "nome_completo": nome,
                "telefone": telefone,
                "e_mail": email,
                "CPF": cpf,
                "RG": rg,
                "gênero": genero,
                "raca": raca,
                "data_nascimento": data_nascimento.strftime("%d/%m/%Y") if data_nascimento else None,
                "escolaridade": escolaridade,
                "cargo": cargo,
                "escritorio": escritorio,
                "banco.nome_banco": nome_banco,
                "banco.agencia": agencia,
                "banco.conta": conta,
                "banco.tipo_conta": tipo_conta
            }

            if st.button("Salvar alterações"):

                # Só adiciona CNPJ e nome da empresa se for PJ1 ou PJ2
                if tipo_contratacao in ["PJ1", "PJ2"]:
                    update_dict["cnpj"] = cnpj
                    update_dict["nome_empresa"] = nome_empresa

                # Atualiza no MongoDB
                pessoas.update_one({"_id": pessoa_logada["_id"]}, {"$set": update_dict})

                st.success("Alterações salvas com sucesso!")
                time.sleep(2)
                st.rerun()


    # ============ ABA CONTRATOS ============
    with aba_contratos:
        st.subheader("Contratos")
        for contrato in pessoa_logada.get("contratos", []):
            with st.container(border=True):

                col1, col2, col3 = st.columns(3)

                col1.write(f"**Data início:** {contrato.get('data_inicio','')}")
                col1.write(f"**Data fim:** {contrato.get('data_fim','')}")
                col1.write(f"**Status:** {contrato.get('status_contrato','')}")
                col1.write(f"**Mês reajuste:** {contrato.get('data_reajuste','')}")

                for pid in contrato.get("projeto_pagador", []):
                    proj = next((p for p in dados_projetos_ispn if p["_id"] == pid), None)
                    if proj:
                        col2.write(f"**Projetos pagadores:** {proj.get('sigla')} - {proj.get('nome_do_projeto')}")


    # ============ ABA PREVIDÊNCIA ============
    with aba_previdencia:
        st.subheader("Contribuições")
        contribs = pessoa_logada.get("previdencia", [])
        
        if contribs:
            for c in contribs:
                st.write(f"- {c.get('data_contribuicao')} | R$ {c.get('valor',0):.2f}")
        else:
            st.warning("Não há contribuições registradas")

