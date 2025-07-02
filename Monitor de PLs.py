import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from dateutil.parser import parse
from funcoes_auxiliares import conectar_mongo_pls, ajustar_altura_dataframe


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Monitor de Proposições Legislativas")
st.write('')
st.write('Os Projetos de Lei que estão cadastrados (Câmara dos Deputados, Senado e Assembléia Legislativa do Maranhão) são monitorados diariamente e as atualizações são enviadas por e-mail para as pessoas cadastradas.')
st.write('')

# Criação de um DataFrame vazio com as colunas finais desejadas, que serão preenchidas mais tarde
colunas = ['Tema', 'Sub-Tema', 'Proposições', 'Ementa', 'Casa', 'Autor', 'UF', 'Partido',
        'Apresentação', 'Situação', 'Data da Última Ação Legislativa', 'Última Ação Legislativa', 'Link']
df_final = pd.DataFrame(columns=colunas)  # Cria o DataFrame com as colunas definidas

# ###################################################################################################
# FUNÇÕES AUXILIARES
# ###################################################################################################


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

colecao = db['pls_camara_senado']
colecao_2 = db['emails']
colecao_3 = db['pls_ma']


# ###################################################################################################
# MAIN
# ###################################################################################################


def main():
   aba1, aba2 = st.tabs(["Gerenciamento de PLs", "Gerenciamento de e-mails"])

# Aba 1 - Proposições ////////////////////////////////////////////////////////////////
   with aba1:

    @st.dialog("Gerenciar PLs", width="large")
    def dial_gerenciar_pls():

        # Cria as abas: Adicionar, Editar e Excluir PLs
        tab1, tab2, tab3 = st.tabs([":material/add: Adicionar", ":material/edit: Editar", ":material/delete: Excluir"])

        # ADICIONAR //////////////////////////////////////////////////////
        with tab1:

            # Junta os temas disponíveis das duas coleções
            temas_camara_senado = list(colecao.distinct("Tema"))
            temas_ma = list(colecao_3.distinct("Tema"))
            temas_disponiveis = sorted(list(set(temas_camara_senado + temas_ma)))

            # Selectbox para o tema
            tema_pl = st.selectbox("Qual o tema do PL?", temas_disponiveis)

            # Junta os subtemas correspondentes ao tema selecionado nas duas coleções
            subtemas_camara_senado = list(colecao.distinct("Sub-Tema", {"Tema": tema_pl}))
            subtemas_ma = list(colecao_3.distinct("Sub-Tema", {"Tema": tema_pl}))
            sub_temas_disponiveis = sorted(list(set(subtemas_camara_senado + subtemas_ma)))

            # Selectbox para o subtema
            sub_tema_pl = st.selectbox("Qual o sub-tema do PL?", sub_temas_disponiveis)

            # Campo de entrada para o link
            link_pl = st.text_input("Qual o link do PL?")

            # Campo de feedback
            feedback = st.empty()

            # Ao clicar no botão
            if st.button("Adicionar PL", icon=":material/add:", type="primary"):
                if tema_pl and sub_tema_pl and link_pl:
                    try:
                        # Identificação da coleção e estrutura apropriada
                        if any(domain in link_pl for domain in ["camara.leg.br", "camara.gov.br", "senado.leg.br"]):
                            colecao_destino = colecao
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
                        elif "sapl.al.ma.leg.br" in link_pl:
                            colecao_destino = colecao_3
                            dados = {
                                'Tema': tema_pl,
                                'Sub-Tema': sub_tema_pl,
                                'Proposição': "Provisório", 
                                'Ementa': "",
                                'Casa': "",
                                'Autor': "",
                                'Apresentação': "",
                                'Situação': "",
                                'Data da Última Ação Legislativa': "",
                                'Última Ação Legislativa': "",
                                'Origem': "",
                                'Destino': "",
                                'Link': link_pl,
                            }

                        else:
                            feedback.error("Link não reconhecido. Use links da Câmara, Senado ou AL-MA.")
                            raise ValueError("Domínio de link inválido")

                        # Verificação de duplicidade
                        link_repetido = colecao_destino.find_one({"Link": link_pl})
                        if link_repetido:
                            feedback.warning("Essa proposição já está cadastrada no banco de dados!")
                        else:
                            colecao_destino.insert_one(dados)
                            feedback.success("PL adicionado com sucesso!")
                            time.sleep(2)
                            feedback.empty()
                            st.rerun()

                    except Exception as e:
                        feedback.error(f"Erro ao adicionar PL: {str(e)}")

                    
        # EDITAR /////////////////////////////////////////////////////////
        with tab2:
            # Carrega os PLs de ambas as coleções com metadado da origem
            pls_1 = list(colecao.find({}, {"Proposições": 1, "Tema": 1, "Sub-Tema": 1, "Link": 1, "Ementa": 1}))
            for pl in pls_1:
                pl['colecao'] = 'pls_camara_senado'

            pls_3 = list(colecao_3.find({}, {"Proposição": 1, "Tema": 1, "Sub-Tema": 1, "Link": 1, "Ementa": 1}))
            for pl in pls_3:
                pl['colecao'] = 'pls_ma'

            pls = pls_1 + pls_3

            if pls:
                pl_selecionado = st.selectbox(
                    "Escolha o PL para editar",
                    pls,
                    format_func=lambda x: x.get("Proposições") or x.get("Proposição") or "Sem título"
                )

                if pl_selecionado:
                    st.write(f"{pl_selecionado.get('Ementa', 'Sem ementa disponível')}")

                    # Determina de qual coleção o PL veio
                    colecao_atual = colecao if pl_selecionado['colecao'] == 'pls_camara_senado' else colecao_3

                    # Unifica os temas de ambas as coleções
                    temas_1 = list(colecao.distinct("Tema"))
                    temas_3 = list(colecao_3.distinct("Tema"))
                    temas_disponiveis = sorted(set(temas_1 + temas_3))

                    tema_selecionado = st.selectbox(
                        "Tema",
                        temas_disponiveis,
                        index=temas_disponiveis.index(pl_selecionado['Tema']) if pl_selecionado['Tema'] in temas_disponiveis else 0
                    )

                    # Unifica sub-temas com base no tema escolhido
                    subtemas_1 = colecao.distinct("Sub-Tema", {"Tema": tema_selecionado})
                    subtemas_3 = colecao_3.distinct("Sub-Tema", {"Tema": tema_selecionado})
                    sub_temas_disponiveis = sorted(set(subtemas_1 + subtemas_3))

                    sub_tema_selecionado = st.selectbox(
                        "Sub-Tema",
                        sub_temas_disponiveis,
                        index=sub_temas_disponiveis.index(pl_selecionado['Sub-Tema']) if pl_selecionado['Sub-Tema'] in sub_temas_disponiveis else 0
                    )

                    if st.button("Salvar alterações", icon=":material/save:", type="primary"):
                        colecao_atual.update_one(
                            {"_id": pl_selecionado['_id']},  
                            {"$set": {
                                "Tema": tema_selecionado,
                                "Sub-Tema": sub_tema_selecionado,
                            }}
                        )
                        st.success(f"'{pl_selecionado.get('Proposições') or pl_selecionado.get('Proposição') or 'PL'}' atualizado com sucesso!")
                        time.sleep(2)
                        st.rerun()
            else:
                st.warning("Nenhuma proposição encontrada no banco de dados.")


        # EXCLUIR ////////////////////////////////////////////////////////
        with tab3:

            pls_1 = list(colecao.find({}, {"Proposições": 1, "Tema": 1, "Sub-Tema": 1, "Link": 1}))
            for pl in pls_1:
                pl['colecao'] = 'pls_camara_senado'

            pls_3 = list(colecao_3.find({}, {"Proposição": 1, "Tema": 1, "Sub-Tema": 1, "Link": 1}))
            for pl in pls_3:
                pl['colecao'] = 'pls_ma'

            pls = pls_1 + pls_3

            if pls:
                pl_selecionado = st.selectbox(
                    "Escolha o PL para excluir",
                    pls,
                    format_func=lambda x: x.get("Proposições") or x.get("Proposição") or "Sem título"
                )

                if st.button("Excluir PL", icon=":material/delete:", type="primary"):
                    colecao_alvo = colecao if pl_selecionado['colecao'] == 'pls_camara_senado' else colecao_3
                    colecao_alvo.delete_one({"_id": pl_selecionado['_id']})
                    st.success(f"'{pl_selecionado.get('Proposições') or pl_selecionado.get('Proposição') or 'PL'}' excluído com sucesso!")
                    time.sleep(2)
                    st.rerun()

            else:
                st.write("Nenhum PL encontrado no banco de dados.")

    col1, col2 = st.columns([4,1])

    contagem_pls = col1.container()

    col2.button("Gerenciar PLs", icon=":material/settings:", use_container_width=True, on_click=dial_gerenciar_pls)


# Aba 2 - Pessoas ////////////////////////////////////////////////////////////////
    with aba2: 
        @st.dialog("Gerenciar e-mails", width="large")
        def dial_gerenciar_pessoas():

            # Cria as abas: Adicionar, Editar e Excluir PLs
            tab1, tab2, tab3 = st.tabs([":material/add: Adicionar", ":material/edit: Editar", ":material/delete: Excluir"])

            # ADICIONAR //////////////////////////////////////////////////////
            # Interface para adicionar novos e-mails e nomes
            with tab1:

                # Caixa de texto para inserir nome e e-mail
                nome = st.text_input("Nome")
                email = st.text_input("E-mail")

                if st.button("Adicionar", icon=":material/add:",type="primary"):
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
                    
                    st.divider()

                    # Buscar os dados da pessoa selecionada
                    pessoa_selecionada = colecao_2.find_one({"Nome": nome_selecionado})
                    
                    # Verifica se a pessoa foi encontrada e garante que 'E-mail' seja uma string válida
                    email_atual = pessoa_selecionada.get("E-mail", "") if pessoa_selecionada else ""

                    # Campo de entrada para editar o nome
                    nome_selecionado = st.text_input("Edite o nome", value=nome_selecionado or "") 
                    
                    # Campo de entrada para editar o e-mail
                    email_selecionado = st.text_input("Edite o e-mail", value=email_atual or "")

                    # Botão para salvar as alterações no banco de dados
                    if st.button("Salvar alterações", icon=":material/save:", type="primary"):
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
                    
                    if st.button("Excluir e-mail", icon=":material/delete:", type="primary"):
                        # Exclui o PL selecionado do banco de dados
                        colecao_2.delete_one({"E-mail": email_para_excluir})
                        
                        st.success("E-mail excluído com sucesso!")  
                        time.sleep(3)
                        st.rerun() 
                        
                else:
                    # Caso não haja PLs para excluir, exibe uma mensagem
                    st.write("Nenhum e-mail encontrado no banco de dados.")

        st.write('')
        st.button("Gerenciar e-mails", icon=":material/mail:", use_container_width=False, on_click=dial_gerenciar_pessoas)
        st.write('')

        st.write('**Pessoas que recebem o e-mail de atualizações:**')

        # Converter para DataFrame 
        df_emails = pd.DataFrame(list(colecao_2.find()))
        df_emails = df_emails.drop(columns=["_id"])
        df_emails = df_emails.reset_index(drop=True)
        df_emails.columns = df_emails.columns.str.strip()

        st.dataframe(df_emails.sort_values(by="Nome"), hide_index=True, use_container_width=False, column_config={
            # configurar a largura da coluna
            "Nome": st.column_config.Column(width="medium"),
            "E-mail": st.column_config.Column(width="medium")
        })


# ###################################################################################################
# EXIBIÇÃO DO DATAFRAME
# ###################################################################################################

    
    # Filtro de data e origem
    colunas = st.columns(3)
    with colunas[0]:
        opcoes_filtro = ["Todos os PLs", "Atualizados no último mês", "Atualizados na última semana"]
        selecionado = st.radio("Filtrar por data da última ação", opcoes_filtro, index=0)

    with colunas[1]:
        origem_opcao = st.radio(
            "Selecione quais PLs deseja visualizar",
            ["PLs Federais (Câmara dos Deputados e Senado)", "PLs Estaduais do Maranhão"],
            index=0
        )

    # Decide qual coleção usar com base na escolha
    colecao_usada = colecao_3 if origem_opcao == "PLs Estaduais do Maranhão" else colecao

    # Carrega os dados da coleção selecionada
    df = pd.DataFrame(list(colecao_usada.find()))
    if df.empty:
        st.warning("Nenhum PL encontrado na coleção selecionada.")
    else:
        df_sem_id = df.drop(columns=['_id'], errors='ignore')

        # Converte a coluna de data, se existir
        if "Data da Última Ação Legislativa" in df_sem_id.columns:
            df_sem_id["Data da Última Ação Legislativa"] = pd.to_datetime(
                df_sem_id["Data da Última Ação Legislativa"], dayfirst=True, errors="coerce"
            )

        # Aplica o filtro de tempo
        hoje = datetime.now()
        if selecionado == "Todos os PLs":
            df_filtrado = df_sem_id.copy()
        elif selecionado == "Atualizados no último mês":
            df_filtrado = df_sem_id[df_sem_id["Data da Última Ação Legislativa"] >= hoje - timedelta(days=30)]
        elif selecionado == "Atualizados na última semana":
            df_filtrado = df_sem_id[df_sem_id["Data da Última Ação Legislativa"] >= hoje - timedelta(days=7)]

        # Ordena por data
        df_filtrado = df_filtrado.sort_values(by="Data da Última Ação Legislativa", ascending=False)

        # Formata a data
        if "Data da Última Ação Legislativa" in df_filtrado.columns:
            df_filtrado["Data da Última Ação Legislativa"] = df_filtrado["Data da Última Ação Legislativa"].dt.strftime("%d/%m/%Y")

        # Define ordem das colunas com base na origem
        if origem_opcao == "PLs Estaduais do Maranhão":
            nova_ordem = [
                'Tema', 'Sub-Tema', 'Data da Última Ação Legislativa', 'Proposição',
                'Ementa', 'Situação', 'Última Ação Legislativa', 'Origem', 'Destino', 'Casa',
                'Autor', 'Apresentação', 'Link'
            ]
        else:
            nova_ordem = [
                'Tema', 'Sub-Tema', 'Data da Última Ação Legislativa', 'Proposições',
                'Ementa', 'Situação', 'Última Ação Legislativa', 'Casa',
                'Autor', 'UF', 'Partido', 'Apresentação', 'Link'
            ]

        # Filtra apenas colunas existentes
        colunas_exibir = [col for col in nova_ordem if col in df_filtrado.columns]
        df_exibir = df_filtrado[colunas_exibir]

        # Renomeia a coluna 'Apresentação'
        df_exibir = df_exibir.rename(columns={"Apresentação": "Data de apresentação"})

        # Exibe resultado
        st.write('')
        contagem_pls.subheader(f'{len(df_exibir)} PLs monitorados')
        ajustar_altura_dataframe(df_exibir, 1)

   
main()