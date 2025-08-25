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

# Busca todos os documentos da coleção "pessoas"
dados_pessoas = list(pessoas.find())

dados_programas = list(programas_areas.find())

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
        "Status": pessoa.get("status", "")
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

    
    # Cria duas abas: cadastro e edição
    aba_cadastrar, aba_editar = st.tabs([":material/person_add: Cadastrar novo(a)", ":material/edit: Editar"])

    # Aba para cadastrar novo colaborador
    with aba_cadastrar:
        # Formulário para cadastro, limpa os campos após envio
        with st.form("form_cadastro_colaborador", clear_on_submit=True):
            st.write('**Novo(a) colaborador(a):**')

            # Layout com colunas para inputs lado a lado
            col1, col2 = st.columns([1, 1])
            
            nome = col1.text_input("Nome completo:")
            genero = col2.selectbox("Gênero:", ["Masculino", "Feminino", "Outro"], index=None, placeholder="")

            col1, col2 = st.columns([1, 1])
            
            cpf = col1.text_input("CPF:", placeholder="000.000.000-00")
            rg = col2.text_input("RG e órgão emissor:")

            col1, col2, col3 = st.columns([1, 2, 2])
            
            data_nascimento = col1.text_input("Data de nascimento:", placeholder="dd/mm/aaaa")
            telefone = col2.text_input("Telefone:")
            email = col3.text_input("E-mail:")

            col1, col2 = st.columns([1, 1])

            # Lista de coordenadores existentes (id, nome, programa)
            coordenadores_possiveis = [
                {
                    "id": pessoa["_id"],
                    "nome": pessoa.get("nome_completo", ""),
                    "programa": pessoa.get("programa_area", "")
                }
                for pessoa in dados_pessoas
                if pessoa.get("tipo de usuário", "").lower() == "coordenador"
            ]
            
            # Extrai nomes únicos dos coordenadores ordenados
            nomes_coordenadores = sorted({c["nome"] for c in coordenadores_possiveis})

            # Seleção do nome do coordenador no formulário
            nome_coordenador = col1.selectbox("Nome do(a) coordenador(a):", nomes_coordenadores, index=None, placeholder="")

            # Lista ordenada dos programas/áreas para seleção
            lista_programas_areas = sorted(nome_para_id_programa.keys())
            programa_area_nome = col2.selectbox("Programa / Área:", lista_programas_areas, index=None, placeholder="")
            programa_area = nome_para_id_programa.get(programa_area_nome)

            st.markdown("---")
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
            
            a_receber = col1.number_input("Dias de férias a receber:", step=1, min_value=0)

            # Variáveis de férias com valores iniciais
            residual_ano_anterior = 0
            valor_inicial_ano_atual = 0
            total_gozado = 0
            saldo_atual = residual_ano_anterior + valor_inicial_ano_atual
            
            st.write("")

            # Ao submeter o formulário de cadastro
            if st.form_submit_button("Cadastrar", type="secondary", icon=":material/person_add:"):
                # Validação de campos obrigatórios
                if not nome or not email or not programa_area or not nome_coordenador:
                    st.warning("Preencha os campos obrigatórios.")
                else:
                    # Busca coordenador pelo nome e programa selecionados
                    coordenador = next((
                        c for c in coordenadores_possiveis
                        if c["nome"] == nome_coordenador and c["programa"] == programa_area
                    ), None)

                    # Se coordenador não encontrado, mostra aviso
                    if not coordenador:
                        st.warning("Coordenador não encontrado para o nome e programa selecionados.")
                        return

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
                        "e_mail_coordenador": coordenador["id"],
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
        nome_selecionado = st.selectbox("Selecione o(a) colaborador(a) para editar:", nomes_existentes, index=None, placeholder="")

        if nome_selecionado:
            # Busca colaborador selecionado no banco
            pessoa = next((p for p in dados_pessoas if p["nome_completo"] == nome_selecionado), None)

            if pessoa:
                # Formulário para edição dos dados
                with st.form("form_editar_colaborador"):
                    st.write(f"Editando informações de **{pessoa['nome_completo']}**")

                    col1, col2 = st.columns([1, 1])
                    
                    nome = col1.text_input("Nome completo:", value=pessoa.get("nome_completo", ""))
                    
                    # Gera lista única e ordenada de gêneros para seleção
                    lista_generos = sorted({pessoa["Gênero"] for pessoa in pessoas_lista if pessoa["Gênero"]})
                    genero = col2.selectbox("Gênero:", lista_generos, key="editar_genero")

                    col1, col2 = st.columns([1, 1])
                    
                    cpf = col1.text_input("CPF:", value=pessoa.get("CPF", ""))
                    rg = col2.text_input("RG e órgão emissor:", value=pessoa.get("RG", ""))

                    col1, col2, col3 = st.columns([1, 2, 2])
                    
                    data_nascimento = col1.text_input("Data de nascimento:", value=pessoa.get("data_nascimento", ""))
                    telefone = col2.text_input("Telefone:", value=pessoa.get("telefone", ""))
                    email = col3.text_input("E-mail:", value=pessoa.get("e_mail", ""))
                    
                    col1, col2 = st.columns([1, 1])
                    
                    # Busca coordenador associado para selecionar valor padrão
                    coordenador_encontrado = next(
                        (c for c in coordenadores_possiveis if c["id"] == pessoa.get("coordenador", "")),
                        None
                    )
                    nome_coordenador_default = coordenador_encontrado["nome"] if coordenador_encontrado else None

                    # Seleção do coordenador com valor padrão
                    nome_coordenador = col1.selectbox(
                        "Nome do(a) coordenador(a):",
                        nomes_coordenadores,
                        index=nomes_coordenadores.index(nome_coordenador_default) if nome_coordenador_default in nomes_coordenadores else 0,
                        key="editar_nome_coordenador"
                    )

                    # Pega o ObjectId atual salvo no banco
                    programa_area_atual = pessoa.get("programa_area")
                    # Converte o ObjectId para nome legível
                    programa_area_nome_atual = id_para_nome_programa.get(programa_area_atual, "")

                    # Selectbox mostra nomes dos programas
                    programa_area_nome = col2.selectbox(
                        "Programa / Área:",
                        lista_programas_areas,
                        index=lista_programas_areas.index(programa_area_nome_atual) if programa_area_nome_atual in lista_programas_areas else 0,
                        key="editar_programa"
                    )

                    # Após seleção, pega o ObjectId correspondente ao nome
                    programa_area = nome_para_id_programa.get(programa_area_nome)

                    
                    col1, col2 = st.columns([1, 1])
                    
                    # Opções possíveis para o campo "tipo de usuário"
                    opcoes_tipo_usuario = [
                        "gestao_pessoas", "gestao_ferias", "supervisao_ferias", 
                        "gestao_noticias", "gestao_pls", "gestao_projetos_doadores", 
                        "gestao_fundo_ecos", "gestao_viagens", "gestao_manuais", "coordenador"
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
                    tipo_usuario = col1.multiselect(
                        "Tipo de usuário:",
                        options=opcoes_tipo_usuario,
                        default=tipo_usuario_default,
                        key="editar_tipo_usuario"
                    )
                    
                    # Seleção do status do colaborador
                    status_opcoes = ["ativo", "inativo"]
                    status = col2.selectbox("Status do colaborador:", status_opcoes, index=status_opcoes.index(pessoa.get("status", "ativo")), key="editar_status")

                    st.markdown("---")

                    # Campos bancários para edição
                    col1, col2 = st.columns([1, 1])
                    nome_banco = col1.text_input("Nome do banco:", value=pessoa.get("banco", {}).get("nome_banco", ""))
                    agencia = col2.text_input("Agência:", value=pessoa.get("banco", {}).get("agencia", ""))

                    col1, col2 = st.columns([1, 1])
                    conta = col1.text_input("Conta:", value=pessoa.get("banco", {}).get("conta", ""))
                    tipo_conta = col2.text_input("Tipo de conta:", value=pessoa.get("banco", {}).get("tipo_conta")),


                    st.write("")
                    
                    # Busca o coordenador selecionado com base no nome e programa selecionado nos campos do formulário
                    coordenador = next((
                        c for c in coordenadores_possiveis
                        if c["nome"] == nome_coordenador and c["programa"] == programa_area
                    ), None)

                    # Se nenhum coordenador for encontrado com os critérios acima, exibe um aviso e interrompe a função
                    if not coordenador:
                        st.warning("Coordenador não encontrado para o nome e programa selecionados.")
                        return

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
                                "e_mail_coordenador": coordenador["id"],
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
container_botoes = st.container(horizontal=True)

# Botão de cadastro de novos colaboradores só para alguns tipos de usuário
if set(st.session_state.tipo_usuario) & {"admin", "gestao_pessoas"}:

    # Botão para abrir o modal de cadastro
    container_botoes.button("Gerenciar colaboradores", on_click=gerenciar_pessoas, icon=":material/group:")
    st.write('')

# Criar DataFrame
df_pessoas = pd.DataFrame(pessoas_lista)

# Filtra apenas os ativos para exibir
df_pessoas = df_pessoas[df_pessoas["Status"].str.lower() == "ativo"]

# Remove colunas indesejadas
df_pessoas = df_pessoas.drop(columns=["Tipo de usuário", "Status"])


# Filtros (pode-se popular dinamicamente se quiser)
col1, col2, col3= st.columns(3)

col1.selectbox("Programa", ["Todos", "Cerrado", "Iniciativas Comunitárias", "Maranhão", "Sociobiodiversidade", "Povos Indígenas"])
col2.selectbox("Doador", ["Todos", "USAID", "GEF", "UE", "Laudes Foundation"])
col3.selectbox("Projeto", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3", "Projeto 4", "Projeto 5"])

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