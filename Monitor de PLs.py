import streamlit as st
import pandas as pd
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
from funcoes_auxiliares import conectar_mongo_pls

st.set_page_config(layout="wide")

st.logo("https://ispn.org.br/site/wp-content/uploads/2021/04/logo_ISPN_2021.png", size="large")

st.write("")
st.write("")
st.write("")
st.write("")
st.write("")
st.write("")

# Criação de um DataFrame vazio com as colunas finais desejadas, que serão preenchidas mais tarde
colunas = ['Tema', 'Sub-Tema', 'Proposições', 'Ementa', 'Casa', 'Autor', 'UF', 'Partido',
        'Apresentação', 'Situação', 'Data da Última Ação Legislativa', 'Última Ação Legislativa', 'Link']
df_final = pd.DataFrame(columns=colunas)  # Cria o DataFrame com as colunas definidas

# ###################################################################################################
# FUNÇÕES AUXILIARES
# ###################################################################################################

# Função para ajustar a altura do dataframe automaticamente no Streamlit
def ajustar_altura_dataframe(df_nao_atualizado, linhas_adicionais=0, use_container_width=True, hide_index=True, column_config={
        "Link": st.column_config.Column(
            # label="Link",
            width="medium"  # Ajusta a largura da coluna "Link", pode ser alterado para "100px" ou outros valores
        ),
        "Data da Última Ação Legislativa": st.column_config.Column(
            label="Última ação",  # Ajusta o nome da coluna para "Última ação"
            # width="medium"  # Ajusta a largura da coluna, pode ser configurado para "100px" ou outros valores
        )
    }):
    """
    Ajusta a altura da exibição de um DataFrame no Streamlit com base no número de linhas e outros parâmetros.
    
    Args:
        df_nao_atualizado (pd.DataFrame): O DataFrame a ser exibido.
        linhas_adicionais int): Número adicional de linhas para ajustar a altura. (padrão é 0)
        use_container_width (bool): Se True, usa a largura do container. (padrão é True)
        hide_index (bool): Se True, oculta o índice do DataFrame. (padrão é True)
        column_config (dict): Configurações adicionais das colunas, se necessário. (padrão é None)
    """
    
    # Define a altura em pixels de cada linha
    altura_por_linha = 35  
    # Calcula a altura total necessária para exibir o DataFrame, considerando as linhas adicionais e uma margem extra
    altura_total = ((df_nao_atualizado.shape[0] + linhas_adicionais) * altura_por_linha) + 2
    
    # Exibe o DataFrame no Streamlit com a altura ajustada
    st.dataframe(
        df_nao_atualizado,
        height=altura_total,  # Define a altura do DataFrame no Streamlit
        use_container_width=use_container_width,  # Define se deve usar a largura do container
        hide_index=hide_index,  # Define se o índice do DataFrame deve ser oculto
        column_config=column_config  # Configurações adicionais para as colunas, como largura personalizada
    )

# Função para excluir um item da coleção
def excluir_pls(numero_pl):
    # Exclui um item com o número da proposição fornecido
    colecao.delete_one({"Proposições": numero_pl})

    # Exibe uma mensagem de sucesso
    st.success(f"{numero_pl} excluído com sucesso!")  

    # Aguarda 3 segundos antes de reiniciar o aplicativo Streamlit
    time.sleep(3)
    # Recarrega o app
    st.rerun()  


# ###################################################################################################
# CONEXÃO MONGO DB
# ###################################################################################################

db = conectar_mongo_pls()

colecao = db['PLS']
colecao_2 = db['emails']

# ###################################################################################################
# MAIN
# ###################################################################################################

def main():
   aba1, aba2 = st.tabs(["Gerenciamento de PLs", "Gerenciamento de pessoas"])

# Aba 1 - Proposições ////////////////////////////////////////////////////////////////
   with aba1:

    @st.dialog("Gerenciar PLs", width="large")
    def dial_gerenciar_pls():

        # Cria as abas: Adicionar, Editar e Excluir PLs
        tab1, tab2, tab3 = st.tabs([":material/add: Adicionar", ":material/edit: Editar", ":material/delete: Excluir"])

        # ADICIONAR //////////////////////////////////////////////////////
        # Interface para adicionar novos PLs
        with tab1:
            
            # Conecta ao banco de dados e busca os temas disponíveis
            temas_disponiveis = sorted(list(colecao.distinct("Tema")))

            # Cria selectbox para escolher o tema do PL
            tema_pl = st.selectbox("Qual o tema do PL?", temas_disponiveis)

            # Busca subtemas relacionados ao tema selecionado
            sub_temas_disponiveis = sorted(list(colecao.distinct("Sub-Tema", {"Tema": tema_pl})))

            # Cria selectbox para escolher o sub-tema do PL
            sub_tema_pl = st.selectbox("Qual o sub-tema do PL?", sub_temas_disponiveis)

            # Cria campo de entrada para o link do PL
            link_pl = st.text_input("Qual o link do PL?")

            dados = {
                'Tema': tema_pl,
                'Sub-Tema': sub_tema_pl,
                'Proposições': "Provisório",
                'Ementa': "",
                'Casa': "",
                'Autor': "",
                'UF': "",
                'Partido': "",
                'Apresentação': "",
                'Situação': "",
                'Data da Última Ação Legislativa': "",
                'Última Ação Legislativa': "",
                'Link': link_pl,
            }
            
            # Variável de feedback temporário
            feedback = st.empty()

            # Verifica se o botão de adicionar foi pressionado
            if st.button("Adicionar PL", use_container_width=True, icon=":material/add:", type="primary"):
                if tema_pl and sub_tema_pl and link_pl:  
                    try:

                        # Verifica se o link já existe no banco de dados
                        link_repetido = colecao.find_one({"Link": link_pl})

                        if link_repetido:
                            feedback.warning("Essa proposição já está cadastrada no banco de dados!")
                        
                        else:
                            colecao.insert_one(dados)
                            feedback.success("PL adicionado com sucesso!")  # Só exibe essa mensagem se for inserido
                            
                            time.sleep(6)  
                            feedback.empty()
                            st.rerun()

                    except Exception as e:
                        feedback.error(f"Erro ao adicionar PL: {str(e)}")
                    
        # EDITAR /////////////////////////////////////////////////////////
        # Interface para editar um PL existente
        with tab2:
            # Carrega as proposições do banco de dados
            pls = list(colecao.find({}, {"Proposições": 1, "Tema": 1, "Sub-Tema": 1, "Link": 1, "Ementa": 1}))

            if pls:
                # Cria selectbox para selecionar qual PL editar
                pl_selecionado = st.selectbox(
                    "Escolha o PL para editar", 
                    pls, 
                    format_func=lambda x: f"{x['Proposições']}"
                )

                # Se um PL for selecionado, exibe os detalhes para edição
                if pl_selecionado:
                    st.write(f"{pl_selecionado.get('Ementa', 'Sem ementa disponível')}")

                    # Consulta para buscar os temas únicos no banco
                    temas_unicos = list(colecao.distinct("Tema"))
                    
                    # Cria selectbox para selecionar o novo tema
                    tema_selecionado = st.selectbox(
                        "Tema",
                        temas_unicos,
                        index=temas_unicos.index(pl_selecionado['Tema']) if pl_selecionado['Tema'] in temas_unicos else 0
                    )

                    # Consulta para buscar subtemas relacionados ao tema selecionado
                    sub_tema_opcoes = list(colecao.find({"Tema": tema_selecionado}, {"Sub-Tema": 1}))
                    sub_tema_opcoes = [st.get("Sub-Tema") for st in sub_tema_opcoes]  # Obtém apenas os subtemas

                    # Cria selectbox para selecionar o sub-tema
                    sub_tema_selecionado = st.selectbox(
                        "Sub-Tema",
                        sub_tema_opcoes,
                        index=sub_tema_opcoes.index(pl_selecionado['Sub-Tema']) if pl_selecionado['Sub-Tema'] in sub_tema_opcoes else 0
                    )

                    # Botão para salvar as alterações no banco de dados
                    if st.button("Salvar alterações", use_container_width=True, icon=":material/save:", type="primary"):
                        # Atualiza o banco de dados com os novos valores
                        colecao.update_one(
                            {"_id": pl_selecionado['_id']},  
                            {"$set": {
                                "Tema": tema_selecionado,
                                "Sub-Tema": sub_tema_selecionado,
                            }}
                        )
                        st.success(f"'{pl_selecionado['Proposições']}' atualizada com sucesso!")

                        # Aguarda e atualiza a interface
                        time.sleep(2)
                        st.rerun()

            else:
                # Caso não haja PLs cadastrados, exibe um aviso
                st.warning("Nenhuma proposição encontrada no banco de dados.")

        # EXCLUIR ////////////////////////////////////////////////////////
        # Interface para excluir um PL existente
        with tab3:
            # Carrega as proposições do banco de dados
            pls = list(colecao.find({}, {"Proposições": 1, "Tema": 1, "Sub-Tema": 1, "Link": 1}))

            # Exibe os itens em um formato de lista
            if pls:
                # Cria selectbox para escolher qual PL excluir
                pls = st.selectbox("Escolha o PL para excluir", pls, format_func=lambda x: f"{x['Proposições']}")
                
                if st.button("Excluir PL", icon=":material/delete:", use_container_width=True, type="primary"):
                    # Exclui o PL selecionado do banco de dados
                    excluir_pls(pls["Proposições"])
            else:
                # Caso não haja PLs para excluir, exibe uma mensagem
                st.write("Nenhum PL encontrado no banco de dados.")

    col1, col2 = st.columns([4,1])

    contagem_pls = col1.container()

    col2.button("Gerenciar PLs", icon=":material/settings:", use_container_width=True, on_click=dial_gerenciar_pls)

    # Consulta todos os documentos da coleção
    #documentos = colecao.find()  # Você pode adicionar filtros no find() se necessário

    # Converter para DataFrame 
    df = pd.DataFrame(list(colecao.find()))
    df_sem_id = df.drop(columns=['_id'])  # Remove a coluna _id, se necessário

    # Converte a coluna 'Data da Última Ação Legislativa' para o formato datetime
    df_sem_id["Data da Última Ação Legislativa"] = pd.to_datetime(
        df_sem_id["Data da Última Ação Legislativa"], dayfirst=True, errors="coerce"
    )

    # Cria opções de filtro para o usuário
    opcoes_filtro = ["Todos os PLs", "Atualizados no último mês", "Atualizados na última semana"]
    selecionado = st.radio("Teste", opcoes_filtro, index=0, label_visibility="collapsed")

    # Aplica o filtro selecionado pelo usuário
    hoje = datetime.now()
    if selecionado == "Todos os PLs":
        df_filtrado_nao_atualizado = df_sem_id.copy()
        
    elif selecionado == "Atualizados no último mês":
        inicio_mes = hoje - timedelta(days=30)
        df_filtrado_nao_atualizado = df_sem_id[df_sem_id["Data da Última Ação Legislativa"] >= inicio_mes]
        
    elif selecionado == "Atualizados na última semana":
        inicio_semana = hoje - timedelta(days=7)
        df_filtrado_nao_atualizado = df_sem_id[df_sem_id["Data da Última Ação Legislativa"] >= inicio_semana]

    # Ordena os dados pela data da última ação
    df_nao_atualizado = df_filtrado_nao_atualizado.sort_values(by="Data da Última Ação Legislativa", ascending=False)

    # Formata as datas para exibição no formato desejado
    df_nao_atualizado["Data da Última Ação Legislativa"] = df_filtrado_nao_atualizado["Data da Última Ação Legislativa"].dt.strftime("%d/%m/%Y")

    # Definindo a nova ordem das colunas
    nova_ordem = [
        'Tema', 'Sub-Tema', 'Data da Última Ação Legislativa', 'Proposições',
        'Ementa', 'Situação', 'Última Ação Legislativa', 'Casa',
        'Autor', 'UF', 'Partido', 'Apresentação', 'Link'
    ]

    # Reorganizando as colunas do DataFrame
    df_nao_atualizado = df_nao_atualizado[nova_ordem]

    # Renomear a coluna Apresentação para Data de apresentação
    df_nao_atualizado = df_nao_atualizado.rename(columns={"Apresentação": "Data de apresentação"})

    contagem_pls.subheader(f'{len(df_nao_atualizado)} PLs monitorados')

    ajustar_altura_dataframe(df_nao_atualizado, 1)

# Aba 2 - Pessoas ////////////////////////////////////////////////////////////////
    with aba2: 
        @st.dialog("Gerenciar pessoas", width="large")
        def dial_gerenciar_pessoas():

            # Cria as abas: Adicionar, Editar e Excluir PLs
            tab1, tab2, tab3 = st.tabs([":material/add: Adicionar", ":material/edit: Editar", ":material/delete: Excluir"])

            # ADICIONAR //////////////////////////////////////////////////////
            # Interface para adicionar novos e-mails e nomes
            with tab1:

                # Caixa de texto para inserir nome e e-mail
                nome = st.text_input("Nome")
                email = st.text_input("E-mail")

                if st.button("Adicionar"):
                    if nome and email:
                        
                        try:
                            
                            # Verifica se o e-mail já está cadastrado
                            email_existente = colecao_2.find_one({"E-mail": email})

                            if email_existente:
                                st.warning("Este e-mail já está cadastrado!")
                                
                            else:
                                # Adiciona ao banco de dados
                                colecao_2.insert_one({"Nome": nome, "E-mail": email})
                                st.success("E-mail cadastrado com sucesso!")
                                
                                time.sleep(6)  
                                st.rerun()
                                
                        except Exception as e:
                            f"Erro ao adicionar PL: {str(e)}"
                                
                    else:
                        st.error("Por favor, preencha todos os campos!")
                        
            # EDITAR //////////////////////////////////////////////////////    
            # Interface para editar os nomes e emails existentes
            with tab2:
                nomes_disponiveis = sorted(list(colecao_2.distinct("Nome")))
                
                if nomes_disponiveis:
                    nome_selecionado = st.selectbox(
                        "Escolha o nome da pessoa que deseja editar as informações", 
                        nomes_disponiveis, 
                        format_func=str  # Exibir o nome corretamente
                    )
                    
                    # Buscar os dados da pessoa selecionada
                    pessoa_selecionada = colecao_2.find_one({"Nome": nome_selecionado})
                    
                    # Verifica se a pessoa foi encontrada e garante que 'E-mail' seja uma string válida
                    email_atual = pessoa_selecionada.get("E-mail", "") if pessoa_selecionada else ""

                    # Campo de entrada para editar o nome
                    nome_selecionado = st.text_input("Edite o nome", value=nome_selecionado or "") 
                    
                    # Campo de entrada para editar o e-mail
                    email_selecionado = st.text_input("Edite o e-mail", value=email_atual or "")

                    # Botão para salvar as alterações no banco de dados
                    if st.button("Salvar alterações", use_container_width=True, icon=":material/save:", type="primary"):
                        if email_selecionado.strip():  # Evita salvar um e-mail vazio
                            colecao_2.update_one(
                                {"Nome": pessoa_selecionada["Nome"]},  # Filtro para encontrar o documento correto
                                {"$set": {"E-mail": email_selecionado, "Nome": nome_selecionado}}
                            )

                            st.success("E-mail atualizado com sucesso!")

                            # Aguarda e atualiza a interface
                            time.sleep(2)
                            st.rerun()
                            
                        else:
                            st.warning("O campo de e-mail não pode estar vazio!")
                            
            # EXCLUIR ////////////////////////////////////////////////////////
            # Interface para excluir um PL existente
            with tab3:
                # Carrega as pessoas do banco de dados
                email_para_excluir = sorted(list(colecao_2.distinct("E-mail")))

                # Exibe os itens em um formato de lista
                if email_para_excluir:
                    # Cria selectbox para escolher qual PL excluir
                    email_para_excluir = st.selectbox("Escolha o e-mail para excluir", email_para_excluir, format_func=str)
                    
                    if st.button("Excluir e-mail", icon=":material/delete:", use_container_width=True, type="primary"):
                        # Exclui o PL selecionado do banco de dados
                        colecao_2.delete_one({"E-mail": email_para_excluir})
                        
                        st.success("E-mail excluído com sucesso!")  
                        time.sleep(3)
                        st.rerun() 
                        
                else:
                    # Caso não haja PLs para excluir, exibe uma mensagem
                    st.write("Nenhum e-mail encontrado no banco de dados.")

        
        st.button("Gerenciar pessoas", icon=":material/person:", use_container_width=False, on_click=dial_gerenciar_pessoas)

        # Converter para DataFrame 
        df_emails = pd.DataFrame(list(colecao_2.find()))
        df_emails = df_emails.drop(columns=["_id"])
        df_emails = df_emails.reset_index(drop=True)
        df_emails.columns = df_emails.columns.str.strip()

        st.dataframe(df_emails.sort_values(by="Nome"), hide_index=True)
           
            
main()