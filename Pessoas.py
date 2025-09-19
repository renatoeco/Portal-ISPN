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
# CSS PARA DIALOGO MAIOR
######################################################################################################
st.markdown(
    """
<style>
div[data-testid="stDialog"] div[role="dialog"]:has(.big-dialog) {
    width: 60vw;
    
}
</style>
""",
    unsafe_allow_html=True,
)


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
        "Status": pessoa.get("status", ""),
        "Tipo Contratação": pessoa.get("tipo_contratacao", ""),
        "Escritório": pessoa.get("escritorio", ""),
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


# Define um diálogo (modal) para gerenciar colaboradores
@st.dialog("Gerenciar colaboradores", width='large')
def gerenciar_pessoas():

    # Aumentar largura do diálogo
    st.html("<span class='big-dialog'></span>")

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





    # INÍCIO
    # SelectBox do nome do colaborador ----------------------------------------------------------
    
    with st.container(horizontal=True, horizontal_alignment="center"):
        nome_selecionado = st.selectbox("Selecione o(a) colaborador(a):", nomes_existentes, index=0, width=400)

    st.write('')

    # Editar colaborador
    if nome_selecionado not in ("", "--Adicionar colaborador--"):
        
        # Busca colaborador selecionado no banco
        pessoa = next((p for p in dados_pessoas if p["nome_completo"] == nome_selecionado), None)
        
        
        # Cria abas
        aba_info, aba_contratos, aba_previdencia, aba_anotacoes  = st.tabs([":material/info: Informações gerais", ":material/contract: Contratos", ":material/finance_mode: Previdência", ":material/notes: Anotações"])
    

        # ABA INFORMAÇÕES GERAIS ################################################################
        with aba_info:

            if pessoa:


                # ===============================
                # Formulário principal
                # ===============================


                # ===============================
                # Tipo de contratação (fora do form)
                # ===============================
                lista_tipo_contracao = ["PJ1", "PJ2", "CLT", "Estagiário", ""]
                tipo_contratacao = st.selectbox(
                    "Tipo de contratação:",
                    lista_tipo_contracao,
                    index=lista_tipo_contracao.index(pessoa.get("tipo_contratacao", "")) 
                    if pessoa.get("tipo_contratacao", "") in lista_tipo_contracao else 0,
                    key="tipo_contratacao_edit",
                    width=300
                )


                with st.form("form_editar_colaborador", border=False):




                    # -----------------------------------------------------------------
                    # Nome completo e status
                    # -----------------------------------------------------------------
                    

                    cols = st.columns([3,2])
                    nome = cols[0].text_input("Nome completo:", value=pessoa.get("nome_completo", ""))

                    status_opcoes = ["ativo", "inativo"]
                    status = cols[1].selectbox(
                        "Status do(a) colaborador(a):", 
                        status_opcoes, 
                        index=status_opcoes.index(pessoa.get("status", "ativo")), 
                        key="editar_status"
                    )



                    
                    

                    # -----------------------------------------------------------------
                    # CPF, RG, telefone e email
                    # -----------------------------------------------------------------


                    cols = st.columns(4)

                    cpf = cols[0].text_input("CPF:", value=pessoa.get("CPF", ""))
                    rg = cols[1].text_input("RG e órgão emissor:", value=pessoa.get("RG", ""))

                    telefone = cols[2].text_input("Telefone:", value=pessoa.get("telefone", ""))
                    email = cols[3].text_input("E-mail:", value=pessoa.get("e_mail", ""))




                    # -----------------------------------------------------------------
                    # Gênero, Raça e Data de Nascimento
                    # -----------------------------------------------------------------
                    
                    cols = st.columns(3)
                    
                    lista_generos = ['Masculino', 'Feminino', 'Não binário', 'Outro']
                    genero = cols[0].selectbox(
                        "Gênero:", lista_generos, 
                        index=lista_generos.index(pessoa.get("gênero")), 
                        key="editar_genero"
                    )
                    
                    lista_raca = ["Amarelo", "Branco", "Índigena", "Pardo", "Preto", ""]
                    raca = cols[1].selectbox("Raça:", lista_raca, index=lista_raca.index(pessoa.get("raca")))                    
                    
                    data_nascimento_str = pessoa.get("data_nascimento", "")
                    if data_nascimento_str:
                        data_nascimento = datetime.datetime.strptime(data_nascimento_str, "%d/%m/%Y")
                    else:
                        data_nascimento = None
                    data_nascimento = cols[2].date_input("Data de nascimento:", format="DD/MM/YYYY", value=data_nascimento)
                    




                    # -----------------------------------------------------------------
                    # Escolaridade, escritório, programa
                    # -----------------------------------------------------------------

                    cols = st.columns(3)

                    lista_escolaridade = ["Ensino fundamental", "Ensino médio", "Graduação", "Pós-graduação", "Mestrado", "Doutorado", ""]
                    escolaridade = cols[0].selectbox("Escolaridade:", lista_escolaridade, index=lista_escolaridade.index(pessoa.get("escolaridade")))

                    lista_escritorio = ["Brasília", "Santa Inês", ""]
                    escritorio = cols[1].selectbox("Escritório:", lista_escritorio, index=lista_escritorio.index(pessoa.get("escritorio")))                  


                    # Programa / Área
                    # Pega o ObjectId atual salvo no banco
                    programa_area_atual = pessoa.get("programa_area")
                    # Converte o ObjectId para nome legível
                    programa_area_nome_atual = id_para_nome_programa.get(programa_area_atual, "")

                    # Selectbox mostra nomes dos programas
                    programa_area_nome = cols[2].selectbox(
                        "Programa / Área:",
                        lista_programas_areas,
                        index=lista_programas_areas.index(programa_area_nome_atual) if programa_area_nome_atual in lista_programas_areas else 0,
                        key="editar_programa", 
                    )

                    # Após seleção, pega o ObjectId correspondente ao nome
                    programa_area = nome_para_id_programa.get(programa_area_nome)



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
                        index=opcoes_cargos_com_vazio.index(valor_cargo)
                    )


                    
                    # cargo = cols[0].selectbox("Cargo:", opcoes_cargos, index=opcoes_cargos.index(pessoa.get("cargo")))


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
                        index=nomes_coordenadores.index(nome_coordenador_default) if nome_coordenador_default in nomes_coordenadores else 0,
                        key="editr_nome_coordenador"
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
                        nome_empresa = col1.text_input("Nome da empresa:", value=pessoa.get("nome_empresa", ""))
                        cnpj = col2.text_input("CNPJ:", value=pessoa.get("cnpj", ""), placeholder="00.000.000/0000-00")



                    
                    st.markdown("---")

                    # Dados bancários

                    st.write("**Dados bancários**")


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
                    nome_para_id_projeto.get(nome)
                    for nome in projetos_pagadores_nomes_edit
                    if nome and nome_para_id_projeto.get(nome)
                ]

                # Status do contrato
                status_contrato = cols[1].selectbox("Status do contrato:", status_opcoes)



                cols = st.columns(3)
                inicio_contrato = cols[0].date_input("Data de início do contrato:", format="DD/MM/YYYY", value="today")
                fim_contrato = cols[1].date_input("Data de fim do contrato:", format="DD/MM/YYYY", value=None)
                data_reajuste = cols[2].selectbox("Mês de reajuste:", meses_pt)

                anotacoes_contrato = st.text_area("Anotações sobre contrato:")

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












                        # if st.session_state.get(delete_key, False):
                        #     linha_botoes.warning("Você tem certeza que deseja apagar essa anotação?")
                        #     if linha_botoes.button("Sim, quero apagar", key=f"confirmar_delete_{container_key}", icon=":material/check:"):
                        #         try:
                        #             # Remove do array local
                        #             anotacoes.pop(original_idx)
                        #             # Atualiza no banco
                        #             pessoas.update_one(
                        #                 {"_id": ObjectId(pessoa["_id"])},
                        #                 {"$set": {"anotacoes": anotacoes}}
                        #             )
                        #             st.success("Anotação apagada com sucesso!")
                        #             st.session_state[delete_key] = False
                        #         except Exception as e:
                        #             st.error(f"Erro ao apagar anotação: {e}")
                        #             st.session_state[delete_key] = False

                        #     # Cancelamento da exclusão
                        #     if linha_botoes.button("Não", key=f"cancelar_delete_{container_key}", icon=":material/close:"):
                        #         st.session_state[delete_key] = False    

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






















            # for original_idx, _, anotacao in anotacoes_ordenadas:
            #     container_key = f"anotacao_{pessoa['_id']}_{original_idx}"
            #     toggle_key = f"toggle_edicao_anotacao_{container_key}"

            #     with st.container(border=True):
            #         modo_edicao = st.toggle("Editar", key=toggle_key, value=False)

            #         if modo_edicao:
            #             # Editar data (somente dd/mm/yyyy)
            #             data_valor = anotacao.get("data_anotacao")
            #             data_dt = datetime.date.today()
            #             if isinstance(data_valor, str) and data_valor:
            #                 try:
            #                     # Pega apenas a parte da data, descarta hora
            #                     data_dt = datetime.datetime.strptime(data_valor.split()[0], "%d/%m/%Y").date()
            #                 except:
            #                     pass


            #             # Editar data           
            #             nova_data = st.date_input(
            #                 "Data da anotação",
            #                 value=data_dt,
            #                 format="DD/MM/YYYY",
            #                 key=f"data_{container_key}", 
            #                 width=150
            #             )

            #             # Editar texto
            #             novo_texto = st.text_area(
            #                 "Texto da anotação",
            #                 value=anotacao.get("anotacao", ""),
            #                 key=f"texto_{container_key}"
            #             )

            #             # Botão salvar
            #             if st.button("Salvar alterações", key=f"salvar_{container_key}", icon=":material/save:"):
            #                 anotacoes[original_idx]["data_anotacao"] = nova_data.strftime("%d/%m/%Y")
            #                 anotacoes[original_idx]["anotacao"] = novo_texto.strip()
            #                 pessoas.update_one(
            #                     {"_id": ObjectId(pessoa["_id"])},
            #                     {"$set": {"anotacoes": anotacoes}}
            #                 )
            #                 st.success("Anotação atualizada com sucesso!")

            #         # Modo visualização
            #         else:
            #             data_str = anotacao.get('data_anotacao', '')
            #             if data_str:
            #                 data_str = data_str.split()[0]  # remove hora
            #             col1, col2 = st.columns([1,3])
            #             with col1:
            #                 st.write(f"**Data:** {data_str}")
            #             with col2:
            #                 st.write(f"**Autor:** {anotacao.get('autor', '')}")
            #             st.write(anotacao.get("anotacao", ""))









    #    Adicionar colaborador --------------------------------------------------------------------------------
    elif nome_selecionado == "--Adicionar colaborador--":

         # SelectBox fora do formulário
        tipo_contratacao = st.selectbox(
            "Tipo de contratação:",
            ["","PJ1", "PJ2", "CLT", "Estagiário"],
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

            escolaridade = cols[0].selectbox("Escolaridade:", ["Ensino fundamental", "Ensino médio", "Graduação", "Pós-graduação", 
                                                            "Mestrado", "Doutorado"], index=None, placeholder="")

            escritorio = cols[1].selectbox("Escritório:", ["Brasília", "Santa Inês"], index=None, placeholder="")

            # Programa / Área
            # Lista ordenada dos programas/áreas para seleção
            lista_programas_areas = sorted(nome_para_id_programa.keys())
            programa_area_nome = cols[2].selectbox("Programa / Área:", lista_programas_areas, index=None, placeholder="")
            programa_area = nome_para_id_programa.get(programa_area_nome)



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


            # -------------------------------------------------
            # Férias
            # -------------------------------------------------

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


            # -------------------------------------------------
            # Anotações
            # -------------------------------------------------

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
                        # "data_reajuste": "",  # novo campo
                        # "contratos": [
                        #     {
                        #         "data_inicio": inicio_contrato.strftime("%d/%m/%Y") if inicio_contrato else "",
                        #         "data_fim": fim_contrato.strftime("%d/%m/%Y") if fim_contrato else "",
                        #         "codigo_projeto": "",
                        #         "status_contrato": status_contrato,
                        #         "projeto_pagador": projeto_pagador if projeto_pagador else [],
                        #         "termos_aditivos": [],
                        #     }
                        # ],
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

    # Botão para abrir o diálogo de gerenciamento de colaboradores
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
        use_container_width=True,
        config={'staticPlot': True}
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
        use_container_width=True,
        config={'staticPlot': True}
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
        use_container_width=True,
        config={'staticPlot': True}
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
    fig.update_yaxes(range=[0, cargo_counts['Quantidade'].max() * 1.15])

    # remove legenda
    fig.update_layout(showlegend=False)

    # exibir gráfico estático
    col1.plotly_chart(
        fig,
        use_container_width=True,
        config={'staticPlot': True}
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
        use_container_width=True,
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
        use_container_width=True,
        config={'staticPlot': True}
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
        use_container_width=True,
        # config={'staticPlot': True}
    )




# Roteamento de usuários
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
