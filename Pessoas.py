import streamlit as st
import pandas as pd 
import plotly.express as px
from datetime import datetime
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

# Define variáveis para as coleções usadas
estatistica = db["estatistica"] 
pessoas = db["pessoas"]  
programas_areas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"]


# Busca todos os documentos das coleções
dados_pessoas = list(pessoas.find())
dados_programas = list(programas_areas.find())
dados_projetos_ispn = list(projetos_ispn.find())


# Converte documentos MongoDB em lista de dicionários para facilitar manipulação
pessoas_lista = []
for pessoa in dados_pessoas:
    id_programa_area = pessoa.get("programa_area")
    nome_programa_area = next(
        (p.get("nome_programa_area", "") for p in dados_programas if p["_id"] == id_programa_area),
        "Não informado"
    )

    pessoas_lista.append({
        "Nome": pessoa.get("nome_completo", ""),
        "Programa/Área": nome_programa_area,
        "Projeto": pessoa.get("projeto", ""),
        "Cargo": pessoa.get("cargo", ""),
        "Escolaridade": pessoa.get("escolaridade", ""),
        "E-mail": pessoa.get("e_mail", ""),
        "Telefone": pessoa.get("telefone", ""),
        "Gênero": pessoa.get("gênero", ""),
        "Raça": pessoa.get("raça", ""),
        "Tipo de usuário": pessoa.get("tipo de usuário", ""),
        "Status": pessoa.get("status", ""),

    })


######################################################################################################
# FUNÇÕES
######################################################################################################




# Define um diálogo (modal) para gerenciar colaboradores com abas de cadastro e edição
@st.dialog("Gerenciar colaboradores", width='large')
def gerenciar_pessoas():
    
    # Mapeia nomes de programa <-> ObjectId
    nome_para_id_programa = {p["nome_programa_area"]: p["_id"] for p in dados_programas}
    id_para_nome_programa = {p["_id"]: p["nome_programa_area"] for p in dados_programas}

    # Mapeia nomes de projeto <-> ObjectId
    nome_para_id_projeto = {p["codigo"]: p["_id"] for p in dados_projetos_ispn}
    id_para_nome_projeto = {p["_id"]: p["codigo"] for p in dados_projetos_ispn}
    
    # Cria duas abas: cadastro e edição
    aba_cadastrar, aba_editar = st.tabs([":material/person_add: Cadastrar novo(a)", ":material/edit: Editar"])

    # Aba para cadastrar novo colaborador
    with aba_cadastrar:
        # Formulário para cadastro, limpa os campos após envio
        with st.form("form_cadastro_colaborador", clear_on_submit=True):
            st.write('**Novo(a) colaborador(a):**')

            # Layout com colunas para inputs lado a lado
            col1, col2 = st.columns([1, 1])
            
            # Nome
            nome = col1.text_input("Nome completo:")
            
            # Gênero
            genero = col2.selectbox("Gênero:", ["Masculino", "Feminino", "Não binário", "Outro"], index=None, placeholder="")

            col1, col2 = st.columns([1, 1])
            
            # CPF e RG
            cpf = col1.text_input("CPF:", placeholder="000.000.000-00")
            rg = col2.text_input("RG e órgão emissor:")

            col1, col2, col3 = st.columns([1, 2, 2])
            
            # Data de nascimento
            data_nascimento = col1.text_input("Data de nascimento:", placeholder="dd/mm/aaaa")
            
            # Telefone
            telefone = col2.text_input("Telefone:")
            
            # E-mail
            email = col3.text_input("E-mail:")

            col1, col2 = st.columns([1, 1])

            # Programa / Área
            # Lista ordenada dos programas/áreas para seleção
            lista_programas_areas = sorted(nome_para_id_programa.keys())
            programa_area_nome = col1.selectbox("Programa / Área:", lista_programas_areas, index=None, placeholder="")
            programa_area = nome_para_id_programa.get(programa_area_nome)


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
            coordenador = col2.selectbox("Nome do(a) coordenador(a):", nomes_coordenadores, index=None, placeholder="")

            # Por fim, pega o id do coordenador
            coordenador_id = None
            for c in coordenadores_possiveis:
                if c["nome"] == coordenador:
                    coordenador_id = c["id"]
                    break



            # Projeto pagador
            lista_projetos = sorted({p["nome_do_projeto"] for p in dados_projetos_ispn if p.get("nome_do_projeto", "") != ""})
            projeto_pagador_nome = st.selectbox("Contratado(a) pelo projeto:", lista_projetos, index=None)
            projeto_pagador = nome_para_id_projeto.get(projeto_pagador_nome)

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
            a_receber = col1.number_input("Dias de férias a receber:", step=1, min_value=0)

            # Variáveis de férias com valores iniciais
            residual_ano_anterior = 0
            valor_inicial_ano_atual = 0
            total_gozado = 0
            saldo_atual = residual_ano_anterior + valor_inicial_ano_atual
            
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
                # disabled=desabilitar
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
                    # # Busca coordenador pelo nome e programa selecionados
                    # coordenador = next((
                    #     c for c in coordenadores_possiveis
                    #     if c["nome"] == nome_coordenador and c["programa"] == programa_area
                    # ), None)

                    # # Se coordenador não encontrado, mostra aviso
                    # if not coordenador:
                    #     st.warning("Coordenador não encontrado para o nome e programa selecionados.")
                    #     # return

                    # Ano atual para armazenar dados de férias
                    ano_atual = str(datetime.now().year)

                    # Monta o documento para inserção no MongoDB
                    novo_documento = {
                        "nome_completo": nome,
                        "CPF": cpf,
                        "RG": rg,
                        "telefone": telefone,
                        "data_nascimento": data_nascimento,
                        "gênero": genero,
                        "senha": "",
                        "tipo de usuário": "",
                        "programa_area": programa_area,
                        "banco": {
                            "nome_banco": nome_banco,
                            "agencia": agencia,
                            "conta": conta,
                            "tipo_conta": tipo_conta
                        },
                        "férias": {
                            "anos": {
                                ano_atual: {
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
                        # "e_mail_coordenador": coordenador["id"],
                        "coordenador": coordenador["id"],
                        "projeto_pagador": projeto_pagador
                    }

                    # Insere o novo colaborador no banco
                    pessoas.insert_one(novo_documento)
                    st.success(f"Colaborador(a) **{nome}** cadastrado(a) com sucesso!", icon=":material/thumb_up:")
                    time.sleep(2)
                    st.rerun()  # Recarrega a página para atualizar dados

    # Aba para editar colaborador existente
    with aba_editar:
        # Lista com nomes dos colaboradores para seleção
        nomes_existentes = sorted([
            p["nome_completo"]
            for p in dados_pessoas
            if "coordenador" in p  # só inclui quem tem o campo 'coordenador'
        ])

        cols = st.columns([3, 2])
        nome_selecionado = cols[0].selectbox("Selecione o(a) colaborador(a) para editar:", nomes_existentes, index=None, placeholder="")

        if nome_selecionado:
            # Busca colaborador selecionado no banco
            pessoa = next((p for p in dados_pessoas if p["nome_completo"] == nome_selecionado), None)

            if pessoa:
                # Formulário para edição dos dados
                with st.form("form_editar_colaborador"):
                    # st.write(f"Editando informações de **{pessoa['nome_completo']}**")
                    st.write('')


                    # Começando com o status do colaborador
                    cols = st.columns([1, 2])

                    status_opcoes = ["ativo", "inativo"]
                    status = cols[0].selectbox("Status do(a) colaborador(a):", status_opcoes, index=status_opcoes.index(pessoa.get("status", "ativo")), key="editar_status")

                    if status == "ativo":
                        desabilitar = False
                    else:
                        desabilitar = True

                    st.markdown("---")


                    col1, col2 = st.columns([1, 1])
                    
                    # Nome completo
                    nome = col1.text_input("Nome completo:", value=pessoa.get("nome_completo", ""), disabled=desabilitar)
                    
                    # Gênero
                    # Gera lista única e ordenada de gêneros para seleção
                    lista_generos = ['Masculino', 'Feminino', 'Não binário', 'Outro']
                    genero = col2.selectbox("Gênero:", lista_generos, key="editar_genero", disabled=desabilitar)

                    col1, col2 = st.columns([1, 1])

                    # CPF e RG 
                    cpf = col1.text_input("CPF:", value=pessoa.get("CPF", ""), disabled=desabilitar)
                    rg = col2.text_input("RG e órgão emissor:", value=pessoa.get("RG", ""), disabled=desabilitar)

                    col1, col2, col3 = st.columns([1, 2, 2])
                    
                    # Data de nascimento, telefone e e-mail
                    data_nascimento = col1.text_input("Data de nascimento:", value=pessoa.get("data_nascimento", ""), disabled=desabilitar)
                    telefone = col2.text_input("Telefone:", value=pessoa.get("telefone", ""), disabled=desabilitar)
                    email = col3.text_input("E-mail:", value=pessoa.get("e_mail", ""), disabled=desabilitar)
                    
                    col1, col2 = st.columns([1, 1])

                     # Programa / Área
                    # Pega o ObjectId atual salvo no banco
                    programa_area_atual = pessoa.get("programa_area")
                    # Converte o ObjectId para nome legível
                    programa_area_nome_atual = id_para_nome_programa.get(programa_area_atual, "")

                    # Selectbox mostra nomes dos programas
                    programa_area_nome = col1.selectbox(
                        "Programa / Área:",
                        lista_programas_areas,
                        index=lista_programas_areas.index(programa_area_nome_atual) if programa_area_nome_atual in lista_programas_areas else 0,
                        key="editar_programa", 
                        disabled=desabilitar
                    )

                    # Após seleção, pega o ObjectId correspondente ao nome
                    programa_area = nome_para_id_programa.get(programa_area_nome)




                    # Coordenador
                    # Busca coordenador associado para selecionar valor padrão
                    coordenador_encontrado = next(
                        (c for c in coordenadores_possiveis if c["id"] == pessoa.get("coordenador", "")),
                        None
                    )
                    nome_coordenador_default = coordenador_encontrado["nome"] if coordenador_encontrado else None

                    # Seleção do coordenador com valor padrão
                    coordenador = col2.selectbox(
                        "Nome do(a) coordenador(a):",
                        nomes_coordenadores,
                        index=coordenadores_possiveis.index(nome_coordenador_default) if nome_coordenador_default in coordenadores_possiveis else 0,
                        key="editr_nome_coordenador", 
                        disabled=desabilitar
                    )

                    # Por fim guarda o ObjectId correspondente ao nome

                    # st.write(coordenadores_possiveis)
                    coordenador_id = next(
                        c["id"] for c in coordenadores_possiveis if c["nome"] == "Renato Farias de Araujo"
                    )
                    # coordenador_id = coordenadores_possiveis[coordenadores_possiveis.index(coordenador)]["id"]

                   

                    

                    

                    st.markdown("---")

                    # Dados bancários
                    col1, col2 = st.columns([1, 1])
                    nome_banco = col1.text_input("Nome do banco:", value=pessoa.get("banco", {}).get("nome_banco", ""), disabled=desabilitar)
                    agencia = col2.text_input("Agência:", value=pessoa.get("banco", {}).get("agencia", ""), disabled=desabilitar)

                    col1, col2 = st.columns([1, 1])
                    conta = col1.text_input("Conta:", value=pessoa.get("banco", {}).get("conta", ""), disabled=desabilitar)


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
                        disabled=desabilitar,
                        key="editar_tipo_conta"
                    )


                    st.write("")
                    
                    # # Busca o coordenador selecionado com base no nome e programa selecionado nos campos do formulário
                    # coordenador = next((
                    #     c for c in coordenadores_possiveis
                    #     if c["nome"] == nome_coordenador and c["programa"] == programa_area
                    # ), None)

                    # # Se nenhum coordenador for encontrado com os critérios acima, exibe um aviso e interrompe a função
                    # if not coordenador:
                    #     st.warning("Coordenador não encontrado para o nome e programa selecionados.")
                    #     return

                    st.divider()

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
                        key="editar_tipo_usuario",
                        disabled=desabilitar
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




                    # Quando o botão "Salvar alterações" for pressionado
                    if st.form_submit_button("Salvar alterações", type="secondary", icon=":material/save:"):
                        # Atualiza o documento da pessoa no banco de dados MongoDB com os novos valores do formulário
                        pessoas.update_one(
                            {"_id": pessoa["_id"]},
                            {"$set": {
                                "nome_completo": nome,
                                "CPF": cpf,
                                "RG": rg,
                                "data_nascimento": data_nascimento,
                                "telefone": telefone,
                                "e_mail": email,
                                "gênero": genero,
                                "banco.nome_banco": nome_banco,
                                "banco.agencia": agencia,
                                "banco.conta": conta,
                                "banco.tipo_conta": tipo_conta,
                                "programa_area": programa_area,
                                "tipo de usuário": ", ".join(tipo_usuario) if tipo_usuario else "",
                                # "e_mail_coordenador": coordenador["id"],
                                "coordenador": coordenador_id,
                                "status": status
                            }}
                        )





                        # Exibe mensagem de sucesso, aguarda 2 segundos e atualiza a página
                        st.success("Informações atualizadas com sucesso!", icon=":material/check_circle:")
                        time.sleep(2)
                        st.rerun()


######################################################################################################
# MAIN
######################################################################################################

# Container horizontal de botões
container_botoes = st.container(horizontal=True, horizontal_alignment="right")

# Botão de cadastro de novos colaboradores só para alguns tipos de usuário
# Roteamento de tipo de usuário
if set(st.session_state.tipo_usuario) & {"admin", "gestao_pessoas"}:

    # Botão para abrir o modal de cadastro
    container_botoes.button("Gerenciar colaboradores", on_click=gerenciar_pessoas, icon=":material/group:")
    st.write('')

# Criar DataFrame
df_pessoas = pd.DataFrame(pessoas_lista)

# Filtra apenas os ativos para exibir
# df_pessoas = df_pessoas[df_pessoas["Status"].str.lower() == "ativo"]

# Remove colunas indesejadas
df_pessoas = df_pessoas.drop(columns=["Tipo de usuário"])



# ????????????????????????????????????????????
# st.write(df_pessoas)

programas = [p["nome_programa_area"] for p in dados_programas]

# Organizar o dataframe por ordem alfabética de nome
df_pessoas = df_pessoas.sort_values(by="Nome")


# Filtros
with st.container(horizontal=True):

    programa = st.selectbox("Programa / Área", ["Todos"] + programas)
    # doador = st.selectbox("Doador", ["Todos", "USAID", "GEF", "UE", "Laudes Foundation"])
    projeto = st.selectbox("Projeto", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3", "Projeto 4", "Projeto 5"])
    status = st.selectbox("Status", ["ativo", "inativo"], index=0)


# Filtrar DataFrame
if programa == "Todos":
    df_pessoas = df_pessoas[df_pessoas["Status"] == status]
else:
    df_pessoas = df_pessoas[(df_pessoas["Programa/Área"] == programa)& (df_pessoas["Status"] == status)]


# Exibir DataFrame
st.subheader(f'{len(df_pessoas)} colaboradores(as)')
st.write('')
st.dataframe(df_pessoas, hide_index=True)

# Gráficos
col1, col2 = st.columns(2)

# Agrupar e ordenar
programa_counts = df_pessoas['Programa/Área'].value_counts().reset_index()
programa_counts.columns = ['Programa/Área', 'Quantidade']

# Criar gráfico ordenado do maior para o menor
fig = px.bar(
    programa_counts,
    x='Programa/Área',
    y='Quantidade',
    color='Programa/Área',
    title='Distribuição de Pessoas por Programa/Área'
)
col1.plotly_chart(fig)

# Projeto
fig = px.bar(df_pessoas, x='Projeto', color='Projeto', title='Distribuição de Pessoas por Projeto')
col2.plotly_chart(fig)

# Cargo
fig = px.pie(df_pessoas, names='Cargo', title='Distribuição de Pessoas por Cargo')
col2.plotly_chart(fig)

# Gênero
fig = px.pie(df_pessoas, names='Gênero', title='Distribuição de Pessoas por Gênero')
col1.plotly_chart(fig)

# Raça
fig = px.pie(df_pessoas, names='Raça', title='Distribuição de Pessoas por Raça')
col2.plotly_chart(fig)

# Escolaridade
fig = px.pie(df_pessoas, names='Escolaridade', title='Distribuição de Pessoas por Escolaridade')
col1.plotly_chart(fig)