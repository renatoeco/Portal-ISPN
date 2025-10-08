import streamlit as st
import pandas as pd 
import datetime
import time
from funcoes_auxiliares import conectar_mongo_portal_ispn
import streamlit_shadcn_ui as ui


# Configura a página do Streamlit para layout mais amplo
st.set_page_config(layout="wide")

# Exibe o logo do ISPN na página
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

# Cabeçalho da página
st.header("Meu Perfil")
st.write('')  


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


# Conecta no banco MongoDB usando função auxiliar
db = conectar_mongo_portal_ispn()

pessoas = db["pessoas"]  
programas_areas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"]
estatistica = db["estatistica"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################

# Nome da página atual, usado como chave para contagem de acessos
nome_pagina = "Meu Perfil"

# Cria um timestamp formatado com dia/mês/ano hora:minuto:segundo
timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# Cria o nome do campo dinamicamente baseado na página
campo_timestamp = f"{nome_pagina}.Visitas"

# Atualiza a coleção de estatísticas com o novo acesso, incluindo o timestamp
estatistica.update_one(
    {},
    {"$push": {campo_timestamp: timestamp}},
    upsert=True  # Cria o documento se ele ainda não existir
)


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
    (p for p in dados_pessoas if str(p["_id"]) == str(st.session_state.get("id_usuario"))),
    None
)

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

# # Lista de coordenadores existentes (id, nome, programa)
# coordenadores_possiveis = [
#     {
#         "id": pessoa["_id"],
#         "nome": pessoa.get("nome_completo", ""),
#         "programa": pessoa.get("programa_area", "")
#     }
#     for pessoa in dados_pessoas
#     if "coordenador(a)" in pessoa.get("tipo de usuário", "").lower()
# ]

# PROJETOS
# Filtra só os projetos em que a sigla não está vazia
dados_projetos_ispn = [projeto for projeto in dados_projetos_ispn if projeto["sigla"] != ""]


######################################################################################################
# MAIN
######################################################################################################


if pessoa_logada:
    aba_info, aba_contratos, aba_previdencia, aba_ferias = st.tabs(
        [":material/info: Informações gerais", ":material/contract: Contratos", ":material/finance_mode: Previdência", ":material/beach_access: Minhas férias"]
    )



    # ============ ABA INFORMAÇÕES GERAIS ============
    with aba_info:

        # st.write('')

        # Toggle de editar --------
        st.subheader("Informações gerais")
        with st.container(horizontal=True, horizontal_alignment="right"):
        
            editar = st.toggle(":material/edit: Editar informações", key="editar_perfil")

        st.write('')



        # ---------------- MODO SOMENTE LEITURA ----------------
        if not editar:

            col1, col2, col3 = st.columns(3, gap="large")

            # Pessoais

            with col1:

                sub1, sub2 = st.columns([2,3])

                # Nome completo
                sub1.write(f"**Nome completo:**")
                sub2.write(pessoa_logada.get('nome_completo',''))
            
                # Data de nascimento
                sub1.write(f"**Data de nascimento:**")
                sub2.write(pessoa_logada.get('data_nascimento',''))

                # CPF
                sub1.write(f"**CPF:**")
                sub2.write(pessoa_logada.get('CPF',''))

                # RG
                sub1.write(f"**RG:**")
                sub2.write(pessoa_logada.get('RG',''))

                # Gênero
                sub1.write(f"**Gênero:**")
                sub2.write(pessoa_logada.get('gênero',''))

                # Raça
                sub1.write(f"**Raça:**")
                sub2.write(pessoa_logada.get('raca',''))

                # Escolaridade
                sub1.write(f"**Escolaridade:**")
                sub2.write(pessoa_logada.get('escolaridade',''))

                # Telefone
                sub1.write(f"**Telefone:**")
                sub2.write(pessoa_logada.get('telefone',''))

                # E-mail
                sub1.write(f"**E-mail:**")
                sub2.write(pessoa_logada.get('e_mail',''))


            with col2:

                sub1, sub2 = st.columns([2,3])   

                # Banco
                sub1.write(f"**Banco:**")
                sub2.write(pessoa_logada.get('banco',{}).get('nome_banco',''))

                # Agência
                sub1.write(f"**Agência:**")
                sub2.write(pessoa_logada.get('banco',{}).get('agencia',''))
                
                # Tipo de conta
                sub1.write(f"**Tipo de conta:**")
                sub2.write(pessoa_logada.get('banco',{}).get('tipo_conta',''))
                
                # Conta
                sub1.write(f"**Conta:**")
                sub2.write(pessoa_logada.get('banco',{}).get('conta',''))


            with col3:

                sub1, sub2 = st.columns([2,3])    
                
                # Escritório
                sub1.write(f"**Escritório:**")
                sub2.write(pessoa_logada.get('escritorio',''))

                # Cargo
                sub1.write(f"**Cargo:**")
                sub2.write(pessoa_logada.get('cargo',''))

                # Programa/Área
                sub1.write(f"**Programa/Área:**")
                sub2.write(id_para_nome_programa.get(pessoa_logada.get('programa_area'),''))

                # Coordenador
                sub1.write(f"**Coordenador:**")
                coord_atual = next(
                    (c for c in dados_pessoas if str(c["_id"]) == str(pessoa_logada.get("coordenador"))),
                    None
                )
                sub2.write(coord_atual['nome_completo'] if coord_atual else '')

                # Tipo de contratação
                sub1.write(f"**Tipo de contratação:**")
                sub2.write(pessoa_logada.get('tipo_contratacao',''))

                # ===============================
                # CAMPOS ADICIONAIS SE FOR PJ
                
                if pessoa_logada.get("tipo_contratacao") in ["PJ1", "PJ2"]:
                    
                    # CNPJ
                    sub1.write(f"**CNPJ:**")
                    sub2.write(pessoa_logada.get('cnpj',''))                    
                    
                    # Nome da empresa
                    sub1.write(f"**Nome da empresa:**")
                    sub2.write(pessoa_logada.get('nome_empresa',''))




        # ---------------- MODO EDIÇÃO ----------------
        else:

            col1, col2, col3 = st.columns(3, gap="large")

            # Coluna 1 – Pessoais
            with col1:
                nome = st.text_input("Nome completo", value=pessoa_logada.get("nome_completo", ""))

                data_nascimento_str = pessoa_logada.get("data_nascimento", "")
                data_nascimento_val = datetime.datetime.strptime(data_nascimento_str, "%d/%m/%Y").date() if data_nascimento_str else None
                data_nascimento = st.date_input("Data de nascimento", value=data_nascimento_val, format="DD/MM/YYYY")

                cpf = st.text_input("CPF", value=pessoa_logada.get("CPF", ""))
                rg = st.text_input("RG", value=pessoa_logada.get("RG", ""))

                lista_generos = ['Masculino', 'Feminino', 'Não binário', 'Outro']
                genero_index = lista_generos.index(pessoa_logada.get("gênero", "Masculino")) if pessoa_logada.get("gênero") in lista_generos else 0
                genero = st.selectbox("Gênero", lista_generos, index=genero_index)

                lista_raca = ["Amarelo", "Branco", "Índigena", "Pardo", "Preto", ""]
                valor_raca = pessoa_logada.get("raca", "")
                index_raca = lista_raca.index(valor_raca) if valor_raca in lista_raca else 0
                raca = st.selectbox("Raça", lista_raca, index=index_raca)

                lista_escolaridade = ["Ensino fundamental", "Ensino médio", "Curso técnico", "Graduação", "Pós-graduação", "Mestrado", "Doutorado", ""]
                valor_escolaridade = pessoa_logada.get("escolaridade", "")
                index_escolaridade = lista_escolaridade.index(valor_escolaridade) if valor_escolaridade in lista_escolaridade else 0
                escolaridade = st.selectbox("Escolaridade", lista_escolaridade, index=index_escolaridade)

                telefone = st.text_input("Telefone", value=pessoa_logada.get("telefone", ""))
                email = st.text_input("E-mail", value=pessoa_logada.get("e_mail", ""))

            # Coluna 2 – Dados bancários
            with col2:
                nome_banco = st.text_input("Banco", value=pessoa_logada.get("banco", {}).get("nome_banco", ""))
                agencia = st.text_input("Agência", value=pessoa_logada.get("banco", {}).get("agencia", ""))

                tipo_conta_atual = pessoa_logada.get("banco", {}).get("tipo_conta", "")
                opcoes_conta = ["", "Conta Corrente", "Conta Poupança", "Conta Salário"]
                index_conta = opcoes_conta.index(tipo_conta_atual) if tipo_conta_atual in opcoes_conta else 0
                tipo_conta = st.selectbox("Tipo de conta", options=opcoes_conta, index=index_conta)

                conta = st.text_input("Conta", value=pessoa_logada.get("banco", {}).get("conta", ""))

            # Coluna 3 – Profissionais
            with col3:
                lista_escritorio = ["Brasília", "Santa Inês", ""]
                valor_escritorio = pessoa_logada.get("escritorio", "")
                index_escritorio = lista_escritorio.index(valor_escritorio) if valor_escritorio in lista_escritorio else 0
                escritorio = st.selectbox("Escritório", lista_escritorio, index=index_escritorio, disabled=True)

                cargo = st.text_input("Cargo", value=pessoa_logada.get("cargo", ""), disabled=True)

                programa_area_nome_atual = id_para_nome_programa.get(pessoa_logada.get("programa_area"), "")
                programa_area_nome = st.text_input("Programa / Área", value=programa_area_nome_atual, disabled=True)

                coordenador_atual_id = pessoa_logada.get("coordenador")
                coord_atual = next((c for c in dados_pessoas if str(c["_id"]) == str(coordenador_atual_id)), None)
                nome_coordenador_default = coord_atual['nome_completo'] if coord_atual else ""
                nome_coordenador = st.text_input("Coordenador", value=nome_coordenador_default, disabled=True)

                tipo_contratacao = st.text_input("Tipo de contratação", value=pessoa_logada.get("tipo_contratacao", ""), disabled=True)

                # Campos extras se PJ
                if tipo_contratacao in ["PJ1", "PJ2"]:
                    cnpj = st.text_input("CNPJ", value=pessoa_logada.get("cnpj", ""), disabled=True)
                    nome_empresa = st.text_input("Nome da empresa", value=pessoa_logada.get("nome_empresa", ""), disabled=True)




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



            # Botão de salvar as alterações
            st.write('')
            if st.button("Salvar alterações", icon=":material/save:", type="primary"):

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

                col1, col2 = st.columns([2,3])

                col1.write(f"**Data início:** {contrato.get('data_inicio','')}")
                col1.write(f"**Data fim:** {contrato.get('data_fim','')}")
                col1.write(f"**Status:** {contrato.get('status_contrato','')}")
                col1.write(f"**Mês reajuste:** {contrato.get('data_reajuste','')}")

                for pid in contrato.get("projeto_pagador", []):
                    proj = next((p for p in dados_projetos_ispn if p["_id"] == pid), None)
                    if proj:
                        col2.write(f"**Projeto pagador:** {proj.get('sigla')} - {proj.get('nome_do_projeto')}")




    # ============ ABA PREVIDÊNCIA ============
    with aba_previdencia:

        st.subheader("Contribuições")
        st.write('')

        # Tratamento dos dados ---------------------------------

        contribs = pessoa_logada.get("previdencia", [])

        if contribs:
            # Transforma em DataFrame
            df_contrib = pd.DataFrame(contribs)

            # Renomeia data
            df_contrib = df_contrib.rename(columns={"data_contribuicao": "data"})

            # Converte para float antes de formatar
            if "valor" in df_contrib.columns:
                df_contrib["valor"] = pd.to_numeric(df_contrib["valor"], errors="coerce")
                
                df_contrib["valor"] = df_contrib["valor"].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )

            # Remover o indice de df_contrib
            df_contrib = df_contrib.reset_index(drop=True)



            # Interface #########################################

            # Convertendo data para datetime
            df_contrib['data_datetime'] = pd.to_datetime(df_contrib['data'], dayfirst=True)


            # Extrai o ano em uma nova coluna
            df_contrib['ano'] = df_contrib['data_datetime'].dt.year

            # Container horizontal para as tabelas
            container_tabelas = st.container(horizontal=True, gap="medium")


            # Itera pelos anos únicos, em ordem decrescente
            for ano in sorted(df_contrib['ano'].unique(), reverse=True):
                
                # Bota um container wrap para funcionar o alinhamento horizontal
                with container_tabelas.container(width=300):
                
                    st.write(f"**{ano}**")
                    
                    # Filtra pelo ano e ordena pela data
                    df_ano = df_contrib[df_contrib['ano'] == ano].sort_values('data_datetime')
                    
                    # Exibe a tabela sem índice
                    st.dataframe(df_ano.drop(columns=['ano', 'data_datetime']), hide_index=True)





        # Se não achou contribuições
        else:
            st.warning("Não há contribuições registradas")


    # ============ ABA MINHAS FÉRIAS ============
    with aba_ferias:
        st.write('')


        # Função para montar o dataframe de saldo
        def montar_dataframe_saldo_do_ano(ano_selecionado, ano_dados):
            # Obtém os dados do saldo do ano atual
            df_saldos = {  # Monta o dicionário com informações de saldo
                "Saldos": [
                    f"Residual do Ano Anterior ({int(ano_selecionado) - 1})",  # Saldo que ficou do ano anterior
                    "Férias recebidas no ano",  # Saldo atribuído no início do ano atual
                    "Total gozado",  # Dias de férias já utilizados
                    "Saldo atual"  # Dias de férias ainda disponíveis
                ],
                "Dias": [
                    ano_dados.get("residual_ano_anterior"),  # Valor do saldo residual
                    ano_dados.get("valor_inicial_ano_atual"),  # Valor inicial do saldo no ano
                    ano_dados.get("total_gozado"),  # Quantidade de dias gozados
                    ano_dados.get("saldo_atual")  # Quantidade de dias restantes
                ]
            }

            # Cria um DataFrame com os dados de saldo e o exibe na primeira coluna
            return pd.DataFrame(df_saldos)
        



        colaborador_selecionado = st.session_state.nome

        st.write('')
        st.write(f'Registros de férias e recessos de **{colaborador_selecionado}**')

        # Filtra os dados do colaborador selecionado
        colaborador_dados = next(
            (registro for registro in dados_pessoas if registro["nome_completo"] == colaborador_selecionado),
            None
        )


        if colaborador_dados:

            # Ordena os anos disponíveis nos dados do colaborador, do mais recente para o mais antigo
            anos_disponiveis = sorted(
                colaborador_dados.get("férias", {}).get("anos", {}).keys(),
                reverse=True
            )

            # Itera sobre os anos disponíveis para exibir as informações de saldo e solicitações de cada ano
            for ano in anos_disponiveis:
                
                # Adiciona uma linha divisória para separar os anos exibidos
                # st.divider()
                st.write('')

                st.subheader(ano)  # Exibe o ano como um subtítulo para identificar a seção correspondente

                # Define a estrutura de colunas para layout: coluna 1 (saldo), espaço entre colunas, coluna 2 (solicitações)
                coluna1, espaco_entre, coluna2 = st.columns([12, 1, 30])

                # # Obtém os dados do saldo do ano atual
                ano_dados = colaborador_dados.get("férias", {}).get("anos", {}).get(ano, {})
                # ano_dados = colaborador_dados.get("anos", {}).get(ano, {})

                # Cria um DataFrame com os dados de saldo e o exibe na primeira coluna
                df_saldo = montar_dataframe_saldo_do_ano(ano, ano_dados)
                coluna1.dataframe(df_saldo, hide_index=True, use_container_width=True)
                
                # Mostrar a_receber
                if ano_dados.get("a_receber"):
                    coluna1.write(f'\\* Na virada do ano receberá {ano_dados.get("a_receber")} dias.')

                # Obtém as solicitações de férias do ano atual
                solicitacoes = ano_dados.get("solicitacoes", [])
                solicitacoes_ano = [  # Cria uma lista formatada com os detalhes das solicitações
                    {
                        "Data do registro": solicitacao.get('data_solicitacao', 'Data não disponível'),  # Data da criação da solicitação
                        # "Data da Solicitação": solicitacao.get('data_solicitacao', 'Data não disponível'),  # Data da criação da solicitação
                        "Período solicitado": solicitacao['lista_de_dias'],  # Lista de dias solicitados
                        # "Dias solicitados": solicitacao['lista_de_dias'],  # Lista de dias solicitados
                        "Total de dias úteis": solicitacao.get('numero_dias_uteis', 'Dias não disponíveis'),  # Total de dias úteis na solicitação
                        "Observações": solicitacao.get('observacoes', 'Nenhuma observação')  # Comentários ou notas da solicitação
                    }
                    for solicitacao in solicitacoes
                ]

                # Cria um DataFrame com os dados das solicitações e o exibe na segunda coluna
                global df_solicitacoes
                df_solicitacoes = pd.DataFrame(solicitacoes_ano)

                if not df_solicitacoes.empty:
                    # Calcula a altura necessária para exibir o DataFrame, baseada no número de linhas
                    altura_df_solicitacoes_individual = ((len(df_solicitacoes) + 1) * 35) + 2
                    # Exibe o DataFrame na segunda coluna com a altura ajustada
                    coluna2.dataframe(df_solicitacoes, hide_index=True, use_container_width=True, height=altura_df_solicitacoes_individual)
                else:
                    # Mensagem exibida caso não existam solicitações de férias para o ano
                    coluna2.write(f"Não há solicitações de férias para {ano} até o momento.")

