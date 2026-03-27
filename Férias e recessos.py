import pandas as pd
import streamlit as st
import plotly.express as px
import time
from pymongo import MongoClient
from datetime import datetime, timedelta, date
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bson import ObjectId

from funcoes_auxiliares import conectar_mongo_portal_ispn  # Função personalizada para conectar ao MongoDB



st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


st.header("Férias e recessos")
st.write('')


# st.subheader('Sistema em manutenção...')


# ###########################################################################
# CONEXÃO COM O BANCO DE DADOS MONGO
# ###########################################################################

# Conecta ao banco de dados MongoDB usando função importada (com cache para otimizar desempenho)
db = conectar_mongo_portal_ispn()

# Função para carregar / recarregar a coleção do banco de dados de colaboradores
@st.cache_resource
def carregar_colaboradores():
    # banco_dados = cliente['ISPN_ferias']  # Seleciona o banco de dados chamado 'ISPN_ferias'
    # colecao = banco_dados['colaboradores']  # Seleciona a coleção 'colaboradores' dentro do banco de dados

    # Define a coleção a ser utilizada, neste caso chamada "teste"
    colecao = db["pessoas"]

    return colecao


# Carregar programas_areas //////////////////////////////////
bd_programas_areas = db["programas_areas"]
# Buscando todos os 'nome_programa_area' e ordenando alfabeticamente
colecao_programas_areas = bd_programas_areas.find({}, {"_id": 0, "nome_programa_area": 1}).sort("nome_programa_area", 1)
# Convertendo para uma lista simples
lista_programas_areas = [doc['nome_programa_area'] for doc in colecao_programas_areas]

# Mapa para identificar o nome do programa_area pelo id
mapa_programas_areas = {str(doc["_id"]): doc["nome_programa_area"] for doc in colecao_programas_areas}


# Criar um dicionário {id: nome}
mapa_programas_areas = {
    str(doc["_id"]): doc["nome_programa_area"]
    for doc in bd_programas_areas.find({}, {"nome_programa_area": 1})
}

estatistica = db["estatistica"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_ferias"
nome_pagina = "Férias e Recessos"

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


# ###########################################################################
# FUNÇÕES AUXILIARES
# ###########################################################################



# Função para enviar e-mail
def enviar_email(destinatario, assunto, corpo, html=False):
   
    # Carrega configurações do e-mail a partir do st.secrets
    smtp_server = st.secrets["senhas"]["smtp_server"]
    port = st.secrets["senhas"]["port"]
    sender_email = st.secrets["senhas"]["endereco_email"]
    password = st.secrets["senhas"]["senha_email"]

    # Criar a mensagem
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = destinatario
    message['Subject'] = assunto

    # Cópia para o DP
    message['Cc'] = 'dp@ispn.org.br'


    # Determina o tipo de conteúdo (HTML ou texto simples)
    if html:
        message.attach(MIMEText(corpo, 'html'))  # Corpo em HTML
    else:
        message.attach(MIMEText(corpo, 'plain'))  # Corpo em texto simples

    try:
        # Conectar ao servidor SMTP
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()  # Inicia a conexão TLS
        server.login(sender_email, password)  # Login no servidor
        server.send_message(message)  # Envia o e-mail
    except Exception as e:
        st.error("Erro ao enviar e-mail. Tente novamente mais tarde.")
    finally:
        server.quit()  # Fecha a conexão com o servidor


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




# Função para atualizar o total_gozado e o saldo_atual sempre que cadastrar uma nova solicitação, editar uma solicitação ou deletar uma solicitação
def atualizar_dados_colaborador():
    # Carrega a coleção de colaboradores
    colecao = carregar_colaboradores()

    # Recupera todos os documentos da coleção
    colaboradores = list(colecao.find())

    colaborador_selecionado = st.session_state.colaborador_selecionado

    # Filtra os dados do colaborador selecionado pelo nome
    colaborador_dados = next(
        (registro for registro in colaboradores if registro.get("nome_completo") == colaborador_selecionado),
        None
    )

    if not colaborador_dados:
        st.warning("Colaborador não encontrado.")
        return

    # Acessa os dados de anos dentro de férias
    colaborador_dados_anos = colaborador_dados.get("férias", {}).get("anos", {})

    if not colaborador_dados_anos:
        st.warning("Nenhum dado de anos encontrado para o colaborador.")
        return

    # Ordena os anos
    anos_ordenados = sorted(colaborador_dados_anos.keys())

    for i, ano in enumerate(anos_ordenados):
        dados_ano = colaborador_dados_anos[ano]

        if 'solicitacoes' in dados_ano and dados_ano['solicitacoes']:
            total_gozado = sum(
                solicitacao.get('numero_dias_uteis', 0) for solicitacao in dados_ano.get('solicitacoes', [])
            )

            # Calcula o residual do ano anterior
            if i > 0:
                ano_anterior = anos_ordenados[i - 1]
                residual_ano_anterior = min(
                    colaborador_dados_anos[ano_anterior].get('saldo_atual', 0), 11
                )
            else:
                residual_ano_anterior = min(dados_ano.get('residual_ano_anterior', 0), 11)

            valor_inicial_ano_atual = dados_ano.get('valor_inicial_ano_atual', 0)
            saldo_atual = residual_ano_anterior + valor_inicial_ano_atual - total_gozado

            # Atualiza no banco
            filtro = {
                "_id": colaborador_dados["_id"],
                f"férias.anos.{ano}": {"$exists": True}
            }

            novos_valores = {
                f"férias.anos.{ano}.total_gozado": total_gozado,
                f"férias.anos.{ano}.saldo_atual": saldo_atual,
                f"férias.anos.{ano}.residual_ano_anterior": residual_ano_anterior,
                f"férias.anos.{ano}.valor_inicial_ano_atual": valor_inicial_ano_atual,
            }

            colecao.update_one(filtro, {"$set": novos_valores})

            colaborador_dados_anos[ano]["saldo_atual"] = saldo_atual

        else:
            total_gozado = 0
            ano_anterior = str(int(ano) - 1)

            if ano_anterior in colaborador_dados_anos:
                residual_ano_anterior = min(
                    colaborador_dados_anos.get(ano_anterior, {}).get('saldo_atual', 0), 11
                )
            else:
                residual_ano_anterior = min(dados_ano.get('residual_ano_anterior', 0), 11)

            valor_inicial_ano_atual = dados_ano.get('valor_inicial_ano_atual', 0)
            saldo_atual = residual_ano_anterior + valor_inicial_ano_atual - total_gozado

            filtro = {
                "_id": colaborador_dados["_id"],
                f"férias.anos.{ano}": {"$exists": True}
            }

            novos_valores = {
                f"férias.anos.{ano}.total_gozado": total_gozado,
                f"férias.anos.{ano}.residual_ano_anterior": residual_ano_anterior,
                f"férias.anos.{ano}.saldo_atual": saldo_atual,
                f"férias.anos.{ano}.valor_inicial_ano_atual": valor_inicial_ano_atual
            }

            colecao.update_one(filtro, {"$set": novos_valores})



# Função para gerar o gráfico e a tabela, usado para todo tipo de usuário
def gerar_grafico_tabela(colaborador_selecionado):
    # Container que vai receber a parte que responde ao filtro de mês e ano
    container_mês = st.container(border=True)  # Cria um container para os filtros de mês e ano


    # ###########################################################################
    # GRÁFICO DE GANTT
    # ###########################################################################

    # Listas para armazenar dados do gráfico de Gantt e solicitações
    gantt_data = []  # Lista que armazenará os dados para o gráfico de Gantt
    # solicitacoes_data = []  # Lista para armazenar todas as solicitações

    # Inicializando a lista para armazenar as informações do Gantt e o set de anos disponíveis
    anos_disponiveis = set()  # Conjunto para armazenar os anos disponíveis

    # Inicialização das variáveis de filtros
    setor_selecionado = "Todos"  # Inicializa com o valor padrão

    # Obtém o ano e o mês atuais
    ano_atual = str(datetime.now().year)  # Obtém o ano atual como string
    mes_atual = datetime.now().month  # Obtém o mês atual como inteiro

    # Recupera todos os documentos da coleção
    colaboradores = list(colecao.find())

    gantt_data = []
    anos_disponiveis = set()

    # Iteração para capturar a lista de anos e criar o dataframe para o gráfico de Gantt
    for colaborador in colaboradores:
        nome = colaborador.get("nome_completo", "Desconhecido")

        programas_ids = colaborador.get("programa_area", [])

        # Garante lista
        if not isinstance(programas_ids, list):
            programas_ids = [programas_ids]

        setores = [
            mapa_programas_areas.get(str(pid), "Desconhecido")
            for pid in programas_ids
        ]


        anos = colaborador.get("férias", {}).get("anos", {})

        for ano, dados_ano in anos.items():
            solicitacoes = dados_ano.get("solicitacoes", [])

            for solicitacao in solicitacoes:
                lista_de_dias = solicitacao.get("lista_de_dias", [])

                # Verifica se há pares de datas (início e fim)
                for i in range(0, len(lista_de_dias) - 1, 2):
                    try:
                        inicio = datetime.strptime(lista_de_dias[i], "%d/%m/%Y")
                        fim = datetime.strptime(lista_de_dias[i + 1], "%d/%m/%Y")

                        num_programas = len(setores)
                        duracao_total = (fim - inicio).days + 1
                        dias_por_programa = duracao_total / num_programas

                        for idx, setor in enumerate(setores):
                            inicio_prog = inicio + timedelta(days=int(idx * dias_por_programa))
                            fim_prog = (
                                inicio + timedelta(days=int((idx + 1) * dias_por_programa))
                                if idx < num_programas - 1
                                else fim
                            )

                            gantt_data.append({
                                "Colaborador": nome,
                                "Início": inicio_prog,
                                "Fim": fim_prog,
                                "Inicio_real": inicio,   
                                "Fim_real": fim,         
                                "Setor": setor
                            })


                        anos_disponiveis.add(inicio.year)
                        anos_disponiveis.add(fim.year)

                    except (ValueError, IndexError) as e:
                        print(f"Erro ao processar datas para {nome} no ano {ano}: {e}")




    # Cria o DataFrame com as colunas Colaborador, Início e Fim
    df_gantt = pd.DataFrame(gantt_data)

    df_gantt["Inicio_hover"] = df_gantt["Inicio_real"]
    df_gantt["Fim_hover"] = df_gantt["Fim_real"]

    # Converte o conjunto anos_disponiveis para uma lista e ordena
    anos_disponiveis = sorted(list(anos_disponiveis), reverse=True)

    # Lista de meses em português
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]

    # Cria as colunas para os filtros
    col1, col2, col3, col4, col5 = container_mês.columns([6, 2, 1, 2, 2])  # Define a proporção das colunas

    # Nome do colaborador no início da página
    with col1:
        titulo_mes = st.container()  # Cria um container para o título do mês
        titulo_mes.write('')  # Adiciona um espaçamento

    # Selectbox para os setores, com o Todos como padrão
    # Mostra somente se o colaborador selecionado for igual a Todos(as)
    if colaborador_selecionado == "Todos(as)":
        with col2:
            st.write('')
            setor_selecionado = st.selectbox("Programa / Área", options=["Todos"] + lista_programas_areas, index=0)

    # Selectbox para os meses, com o mês atual como padrão
    with col4:
        st.write('')
        mes_selecionado = st.selectbox("Selecione o mês", options=meses, index=mes_atual - 1)

    # Selectbox para os anos, com o ano atual como padrão
    with col5:
        st.write('')

        # Encontrar o índice do ano atual na lista de anos disponíveis
        if int(ano_atual) in anos_disponiveis:
            # Encontrar o índice do ano atual
            index_ano_atual = anos_disponiveis.index(int(ano_atual))
        else:
            # Definir índice padrão como 0
            index_ano_atual = 0

        # Criar o selectbox com o ano atual selecionado por padrão
        ano_selecionado = st.selectbox("Selecione o ano", options=anos_disponiveis, index=index_ano_atual)

    # Escrevendo o mês e ano na col1
    if ano_selecionado != None:
        titulo_mes.subheader(f'{mes_selecionado} de {ano_selecionado}')  # Exibe o mês e ano selecionados

    # Mapeia o nome do mês para seu número (1-12)
    mes_numero = meses.index(mes_selecionado) + 1


    # Define a data de referência para o mês e ano selecionados
    data_inicio_mes = datetime(int(ano_selecionado), mes_numero, 1)  # Primeiro dia do mês selecionado
    if mes_numero == 12:  # Caso seja dezembro, calcula o último dia do mês
        data_fim_mes = datetime(int(ano_selecionado) + 1, 1, 1) - pd.Timedelta(days=1)
    else:  # Para outros meses, calcula o último dia normalmente
        data_fim_mes = datetime(int(ano_selecionado), mes_numero + 1, 1) - pd.Timedelta(days=1)

    # Filtra o DataFrame para incluir somente os registros do mês e ano selecionados
    df_gantt = df_gantt[
        ((df_gantt["Início"].dt.year == int(ano_selecionado)) & 
        (df_gantt["Início"].dt.month == mes_numero)) |
        ((df_gantt["Fim"].dt.year == int(ano_selecionado)) & 
        (df_gantt["Fim"].dt.month == mes_numero)) |
        ((df_gantt["Início"] <= data_fim_mes) & 
        (df_gantt["Fim"] >= data_inicio_mes))
    ]

    # Verifica se há registros para o gráfico
    if df_gantt.empty:
        st.write('')
        container_mês.write(f"Não há férias programadas para o mês de {mes_selecionado.lower()}.")  # Mensagem de ausência de dados

    # Tem registros
    else:
        # Filtra os dados se um colaborador específico estiver selecionado
        if colaborador_selecionado != "Todos(as)":
            df_gantt = df_gantt[df_gantt["Colaborador"] == colaborador_selecionado]

        # Se o colaborador for Todos(as),Filtra os dados se um setor específico estiver selecionado
        elif setor_selecionado != "Todos":
            df_gantt = df_gantt[df_gantt["Setor"] == setor_selecionado]  # Assumindo que há uma coluna 'Setor' no DataFrame

        # Verifica novamente se há dados após o filtro por colaborador
        if df_gantt.empty:
            container_mês.write(f"Não há férias programadas para o mês de {mes_selecionado.lower()}.")  # Mensagem após o filtro
        else:

            # Define a altura do gráfico com base na seleção
            if colaborador_selecionado == "Todos(as)":
                if len(df_gantt) < 10:
                    altura_grafico = 300
                elif len(df_gantt) < 20:
                    altura_grafico = 600  # Altura padrão para todos
                elif len(df_gantt) < 30:
                    altura_grafico = 700
                else:
                    altura_grafico = 900
            else:
                altura_grafico = 130  # Altura menor para um colaborador específico

            # Define o primeiro e o último dia do mês selecionado
            primeiro_dia = datetime(int(ano_selecionado), mes_numero, 1)
            ultimo_dia = (primeiro_dia + timedelta(days=31)).replace(day=1)

            # Adiciona 1 dia ao valor da coluna "Fim" para ajustar visualmente o gráfico
            df_gantt["Final"] = df_gantt["Fim"] + pd.Timedelta(days=1)

            # Adiciona a menor data de "Início" por colaborador
            df_gantt['Menor_Início'] = df_gantt.groupby('Colaborador')['Início'].transform('min')

            # Ordena o DataFrame com base na menor data de "Início" e depois pela data "Início"
            df_gantt = df_gantt.sort_values(by=['Menor_Início', 'Início'], ascending=False)

            # Definindo a paleta de cores divergente
            cores_setores = {
                "Advocacy": "rgba(255, 127, 14, 0.55)",              # Laranja brilhante
                "Adm. Brasília": "rgba(44, 160, 44, 0.55)",          # Verde
                "Adm. Santa Inês": "rgba(227, 119, 194, 0.55)",       # Azul
                "Comunicação": "rgba(148, 103, 189, 0.55)",          # Roxo
                "Coordenação": "rgba(214, 39, 40, 0.55)",            # Vermelho
                "Estagiário(a)": "rgba(255, 187, 120, 0.55)",        # Laranja claro
                "Programa Cerrado": "rgba(140, 86, 75, 0.55)",       # Marrom
                "Programa Iniciativas Comunitárias": "rgba(31, 119, 180, 0.55)", # Rosa
                "Programa Maranhão": "rgba(188, 189, 34, 0.55)",     # Verde amarelado
                "Programa Povos Indígenas": "rgba(23, 190, 207, 0.55)", # Ciano
                "Programa Sociobiodiversidade": "rgba(127, 127, 127, 0.55)" # Cinza
            }


            # Se setor_selecionado for "Todos(as)", utilizamos a paleta de cores
            if setor_selecionado == "Todos":
                # Cria o gráfico de Gantt com as cores baseadas no setor
                fig = px.timeline(
                    df_gantt,
                    x_start="Início",
                    x_end="Final",
                    y="Colaborador",
                    color="Setor",
                    color_discrete_map=cores_setores,
                    custom_data=["Inicio_hover", "Fim_hover", "Setor"]
                )

                fig.update_traces(
                    hovertemplate=
                    "<b>%{y}</b><br>" +
                    "Início: %{customdata[0]|%d/%m/%Y}<br>" +
                    "Fim: %{customdata[1]|%d/%m/%Y}<br>" +
                    "Programa: %{customdata[2]}<extra></extra>"
                )

            else:
                # Cria o gráfico de Gantt com o setor selecionado, usando a cor do setor selecionado
                fig = px.timeline(
                    df_gantt,
                    x_start="Início",
                    x_end="Final",
                    y="Colaborador",
                    color="Setor",
                    color_discrete_map=cores_setores,
                    hover_data={
                        "Início": False,
                        "Fim": False,
                        "Inicio_real": "|%d/%m/%Y",
                        "Fim_real": "|%d/%m/%Y",
                        "Setor": True
                    }
                )

            # Mapeia rótulos reais (remove o sufixo __idx)
            labels_y = {
                v: v.split("__")[0]
                for v in df_gantt["Colaborador"].unique()
            }

            fig.update_yaxes(
                tickmode="array",
                tickvals=list(labels_y.keys()),
                ticktext=list(labels_y.values())
            )

            # Adiciona uma linha vertical vermelha para marcar o dia de hoje
            hoje = datetime.now().date()  # Multiplicado por 1000 para obter o timestamp em milissegundos
            fig.add_vline(
                x=hoje,  # Posição da linha vertical (data de hoje)
                line_width=2,  # Espessura da linha
                # line_dash="dash",  # Estilo da linha (tracejada)
                line_color="red",  # Cor da linha
            )


            # Estilo do gráfico
            fig.update_layout(
                yaxis=dict(tickfont=dict(size=15)),  # Ajusta o tamanho da fonte do eixo Y
                height=altura_grafico,  # Define a altura do gráfico
                margin=dict(l=20, r=20, t=50, b=50),  # Define margens
                xaxis=dict(side="top"),  # Move os rótulos do eixo X para o topo
                legend=dict(
                    orientation="h",  # Define a orientação da legenda como horizontal
                    y=-0.2,  # Move a legenda para baixo do gráfico
                    x=0.5,  # Centraliza a legenda horizontalmente
                    xanchor="center",  # Define o ponto de ancoragem da legenda
                    title=None
                )
            )

            # Remove o título do eixo Y
            fig.update_yaxes(title_text='')  

            # Configura o eixo X para mostrar todos os dias do mês selecionado
            fig.update_xaxes(
                range=[primeiro_dia, ultimo_dia], 
                dtick="D1", 
                tickformat="%d/%m", 
                showgrid=True, 
                gridwidth=0.5, 
                gridcolor="lightgrey"
            )


            # Exibe o gráfico no container
            container_mês.plotly_chart(fig)

    # except:
    #     st.warning('Cadastre um(a) colaborador(a) e ao menos uma solicitação de férias.')


    st.write('')


    # ###########################################################################
    # TODOS(AS) - somente para admim, gestao_ferias e supervisao_ferias
    # ###########################################################################

    # Roteamento de tipo de usuário especial
    if set(st.session_state.tipo_usuario) & {"admin", "gestao_ferias", "supervisao_ferias"}:

        if colaborador_selecionado == "Todos(as)":
            # Inicializa uma lista para armazenar as solicitações de todos os colaboradores
            todas_solicitacoes = []

            # Itera sobre todos os registros de colaboradores
            for registro in colaboradores:
                nome = registro.get("nome_completo", "Não informado")

                programas_ids = registro.get("programa_area", [])

                if not isinstance(programas_ids, list):
                    programas_ids = [programas_ids]

                setores = [
                    mapa_programas_areas.get(str(pid), "Não informado")
                    for pid in programas_ids
                ]

                setor_formatado = ", ".join(setores)



                # setor = registro.get("programa_area", "Não informado")

                # Obtém os dados dos anos dentro de "férias"
                dados_anos = registro.get("férias", {}).get("anos", {})

                # Obtém os dados para o ano selecionado e o ano anterior
                ano_dados_atual = dados_anos.get(str(ano_selecionado), {})
                ano_dados_anterior = dados_anos.get(str(int(ano_selecionado) - 1), {})

                # Combina os dados dos dois anos em uma lista
                todos_anos_dados = [ano_dados_atual, ano_dados_anterior]

                # Itera sobre os dados combinados
                for ano_dados in todos_anos_dados:
                    if not ano_dados:
                        continue  # Pula se não houver dados para o ano

                    # Obtém as solicitações de férias
                    solicitacoes = ano_dados.get("solicitacoes", [])

                    for solicitacao in solicitacoes:
                        lista_de_dias = solicitacao.get('lista_de_dias', [])

                        # Verifica se há datas na solicitação
                        if not lista_de_dias:
                            continue

                        # Converte as datas para objetos datetime
                        lista_de_dias_timestamp = pd.to_datetime(lista_de_dias, dayfirst=True)
                        lista_de_dias_timestamp = sorted(lista_de_dias_timestamp)

                        inicio_periodo = lista_de_dias_timestamp[0]
                        fim_periodo = lista_de_dias_timestamp[-1]

                        # Define o intervalo do mês selecionado
                        data_referencia_inicio = pd.to_datetime(f"{ano_selecionado}-{mes_numero}-01")
                        data_referencia_fim = data_referencia_inicio + pd.offsets.MonthEnd(0)

                        # Verifica sobreposição com o mês selecionado
                        if (inicio_periodo <= data_referencia_fim) and (fim_periodo >= data_referencia_inicio):
                            todas_solicitacoes.append({
                                "Nome": nome,
                                "Setor": setor_formatado,
                                "Data do registro": solicitacao.get('data_solicitacao', 'Data não disponível'),
                                "Período solicitado": lista_de_dias,
                                "Total de dias úteis": solicitacao.get('numero_dias_uteis', 'Não disponível'),
                                "Observações": solicitacao.get('observacoes', 'Nenhuma observação')
                            })

            # Cria o DataFrame
            df_todas_solicitacoes = pd.DataFrame(todas_solicitacoes)

            if not df_todas_solicitacoes.empty:
                # Ordena por nome
                df_todas_solicitacoes.sort_values(by='Nome', inplace=True)

                # Filtro por setor, se aplicável
                if setor_selecionado != "Todos":
                    df_todas_solicitacoes = df_todas_solicitacoes[
                        df_todas_solicitacoes["Setor"].str.contains(
                            setor_selecionado,
                            regex=False,
                            na=False
                        )
                    ]

                # Subtítulo
                container_mês.subheader("**Solicitações de férias no mês**")

                # Altura dinâmica do DataFrame
                altura_df_solicitacoes = ((len(df_todas_solicitacoes) + 1) * 35) + 2

                # Exibição
                container_mês.dataframe(
                    df_todas_solicitacoes,
                    hide_index=True,
                    width="stretch",
                    height=altura_df_solicitacoes,
                    column_config={
                        "Setor": "Programa / Setor"
                    },
                )


        # ###########################################################################
        # INDIVIDUAL
        # ###########################################################################

        else:
            
            st.write('\n' * 3)  # Insere espaços vazios para separação visual

            # Filtra os dados do colaborador selecionado
            colaborador_dados = next(
                (registro for registro in colaboradores if registro["nome_completo"] == colaborador_selecionado),
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
                    st.divider()

                    st.subheader(ano)  # Exibe o ano como um subtítulo para identificar a seção correspondente

                    # Define a estrutura de colunas para layout: coluna 1 (saldo), espaço entre colunas, coluna 2 (solicitações)
                    coluna1, espaco_entre, coluna2 = st.columns([12, 1, 30])

                    # # Obtém os dados do saldo do ano atual
                    ano_dados = colaborador_dados.get("férias", {}).get("anos", {}).get(ano, {})
                    # ano_dados = colaborador_dados.get("anos", {}).get(ano, {})

                    # Cria um DataFrame com os dados de saldo e o exibe na primeira coluna
                    df_saldo = montar_dataframe_saldo_do_ano(ano, ano_dados)
                    coluna1.dataframe(df_saldo, hide_index=True, width="stretch")
                    
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
                        coluna2.dataframe(df_solicitacoes, hide_index=True, width="stretch", height=altura_df_solicitacoes_individual)
                    else:
                        # Mensagem exibida caso não existam solicitações de férias para o ano
                        coluna2.write(f"Não há solicitações de férias para {ano} até o momento.")




# ###########################################################################
# CARREGAMENTO DA COLEÇÃO DE COLABORADORES
# ###########################################################################

colecao = carregar_colaboradores()

# Buscar todos os documentos da coleção de colaboradores
colaboradores = list(colecao.find())  # Recupera todos os documentos da coleção e os transforma em uma lista






# ######################################################################################################
# INÍCIO DA PÁGINA ======================== 
# ######################################################################################################



# Roteamento de tipo de usuário especial
if set(st.session_state.tipo_usuario) & {"admin", "gestao_ferias", "supervisao_ferias"}:

    # Função da interface de Férias para admin, gestao_ferias e supervisao_ferias
    def ferias_admin_gestaoFerias_supervisaoFerias():
        
        st.write('')

        # Linha para o botão de lista de colaboradores com saldo
        colunas_botoes = st.columns([4, 3, 3, 3, 4])


        # 1 - BOTÃO DE LISTA DE COLABORADORES COM SALDO
        
        @st.dialog("Lista de colaboradores por ano", width="large")
        def lista_colaboradores():

            if not colaboradores:
                st.write("Não há colaboradores cadastrados.")
                return

            # Inicializa o set para armazenar todos os anos disponíveis
            todos_os_anos = set()

            # Dicionário para mapear colaboradores e saldos por ano
            saldos_por_colaborador = {}

            # Itera sobre cada colaborador para coletar os anos e preencher os saldos
            for colaborador in colaboradores:
                colaborador_nome = colaborador.get("nome_completo", "Não informado")

                programa_id = colaborador.get("programa_area")
                setor = mapa_programas_areas.get(str(programa_id), "Não informado")

                # setor = colaborador.get("programa_area", "Não informado")

                # Acessa os dados de férias → anos
                dados_anos = colaborador.get("férias", {}).get("anos", {})

                # Adiciona os anos deste colaborador ao set de anos disponíveis
                todos_os_anos.update(dados_anos.keys())

                # Salva os saldos atuais do colaborador por ano
                for ano, dados in dados_anos.items():
                    saldo_atual = dados.get("saldo_atual", 0)

                    if ano not in saldos_por_colaborador:
                        saldos_por_colaborador[ano] = []

                    saldos_por_colaborador[ano].append({
                        "Nome": colaborador_nome,
                        "Setor": setor,
                        "Saldo Atual": saldo_atual
                    })

            # Ordena os anos de forma decrescente
            anos_disponiveis = sorted(todos_os_anos, reverse=True)

            # Coluna para diminuir a largura do dropdown
            col_dropdown, col_vazia = st.columns([1, 2])

            # Dropdown para seleção de ano
            ano_selecionado = col_dropdown.selectbox(
                "Selecione o ano:",
                anos_disponiveis,
                key="ano_selecionado_saldo"
            )

            # Prepara o DataFrame apenas para o ano selecionado
            if ano_selecionado in saldos_por_colaborador:
                df_saldos = pd.DataFrame(saldos_por_colaborador[ano_selecionado])
            else:
                df_saldos = pd.DataFrame(columns=["Nome", "Setor", "Saldo Atual"])

            df_saldos = df_saldos.reset_index(drop=True)

            # Renomeações e formatações
            df_saldos = df_saldos.rename(columns={'Saldo Atual': 'Saldo do ano'})
            df_saldos['Saldo do ano'] = df_saldos['Saldo do ano'].astype(int)

            df_saldos = df_saldos.sort_values(by='Saldo do ano', ascending=False)
            df_saldos = df_saldos[['Nome', 'Saldo do ano', 'Setor']]
            df_saldos = df_saldos.rename(columns={'Setor': 'Programa / Área'})

            # Exibe o DataFrame formatado
            st.dataframe(df_saldos, hide_index=True, width="stretch")

        # Botão para abrir o diálogo de lista de colaboradores
        colunas_botoes[4].write('')
        
        colunas_botoes[4].button(
            "Colaboradores e saldos",
            on_click=lista_colaboradores,
            icon=":material/groups:",
            width=300
        )




        # DROPDOWN DE SELEÇÃO DE COLABORADOR
        # Cria a lista de colaboradores e adiciona "Todos(as)" como o primeiro item, para o dropdown
        lista_nomes = [item.get("nome_completo", "Desconhecido") for item in colaboradores]
        # lista_nomes = [list(item.keys())[1] for item in colaboradores]  # Extrai os nomes dos colaboradores (chave do segundo item)
        lista_nomes.sort()  # Ordena os nomes em ordem alfabética
        lista_nomes.insert(0, "Todos(as)")  # Insere a opção "Todos(as)" no início da lista

        st.write('')
        colunas_botoes[0].write("**Selecione o(a) colaborador(a):**")  # Exibe um subtítulo no menu lateral

        colaborador_selecionado = colunas_botoes[0].selectbox(  # Cria um dropdown para selecionar um colaborador
            "Selecione o(a) colaborador(a)", 
            options=lista_nomes, 
            label_visibility="collapsed",  # Oculta o rótulo padrão do dropdown
            index=0,  # Define "Todos(as)" como opção selecionada por padrão
        )

        # Sobe o colaborador_selecionado pro session_state
        st.session_state.colaborador_selecionado = colaborador_selecionado

        # NOME DA PESSOA NO TOPO
        st.write("")
        st.subheader(f"{colaborador_selecionado}")  # Exibe o nome do colaborador selecionado no topo da página
        st.write("")




        # Linha de botões -------------------------------
        colunas_botoes = st.columns(5)

        st.write('')

        # 1 - BOTÃO DE NOVA SOLICITAÇÃO

        # Roteamento de tipo de usuário - somente para gestao_ferias
        if set(st.session_state.tipo_usuario) & {"admin","gestao_ferias"}:

            if colaborador_selecionado != "Todos(as)":

                # Função para abrir o diálogo "Nova solicitação"
                @st.dialog("Nova solicitação")
                def nova_solicitacao():
                    # Inicia um formulário para registrar uma nova solicitação de férias
                    with st.form("Nova solicitação", clear_on_submit=True):
                        
                        # Exibe o nome do colaborador como título centralizado no modal
                        st.write('')
                        st.markdown(f"<p style='text-align: center;'>{colaborador_selecionado.upper()}</p>", unsafe_allow_html=True)
                        st.write('')

                        # Subtítulo indicando a ação de criar uma nova solicitação
                        st.write(f'**Nova solicitação de férias:**')

                        # Captura a data atual como a data da solicitação
                        data_solicitacao = datetime.now().strftime("%d/%m/%Y")

                        # Campo para selecionar o período de férias, com valor padrão de hoje até amanhã
                        periodo_solicitado = st.date_input(
                            "Qual é o período?",
                            value=(date.today(), date.today() + timedelta(days=1)),  # Período padrão
                            format="DD/MM/YYYY"  # Formato de exibição
                        )

                        # Campo para inserir o total de dias úteis, com valor mínimo de 0 e incremento de 1
                        total_dias_uteis = st.number_input("Total de dias úteis:", min_value=0, step=1)

                        # Campo opcional para adicionar observações sobre a solicitação
                        observacoes = st.text_input("Observações: (opcional)")

                        # Botão para enviar o formulário e registrar a solicitação
                        st.write('')
                        if st.form_submit_button('Registrar férias', width=200, icon=":material/check:", type="primary"):
                        
                            # Verifica se o total de dias úteis foi informado
                            if total_dias_uteis < 1:
                        
                                # Exibe uma mensagem de aviso caso o campo esteja vazio ou com valor 0
                                st.warning("Informe o total de dias úteis.")
                        
                            else:
                                # Extrai o ano do início do período solicitado
                                ano_solicitacao = str(periodo_solicitado[0].year)

                                # Formata a lista de dias selecionados no período para o formato "dd/mm/yyyy"
                                lista_de_dias = [dia.strftime("%d/%m/%Y") for dia in periodo_solicitado]

                                # Verifica se a lista contém apenas 1 item e duplica o valor
                                if len(lista_de_dias) == 1:
                                    lista_de_dias.append(lista_de_dias[0])

                                # Cria o objeto representando a nova solicitação
                                nova_solicitacao = {
                                    "data_solicitacao": data_solicitacao,  # Data de registro
                                    "lista_de_dias": lista_de_dias,  # Período solicitado
                                    "numero_dias_uteis": total_dias_uteis,  # Total de dias úteis
                                    "observacoes": observacoes  # Observações fornecidas pelo usuário
                                }

                                # Adiciona a nova solicitação ao ano correspondente no banco de dados
                                colecao.update_one(
                                    { "nome_completo": colaborador_selecionado },  # Filtra o colaborador pelo nome
                                    {
                                        "$push": {
                                            f"férias.anos.{ano_solicitacao}.solicitacoes": nova_solicitacao
                                        }
                                    }
                                )

                                # Função para atualizar os dados do colaborador (substitua com a lógica do seu sistema)
                                atualizar_dados_colaborador()

                                # Exibe uma mensagem de sucesso após o registro
                                st.success("Período de férias registrado!", icon=":material/thumb_up:")

                                # Aguarda 3 segundos antes de recarregar a página para atualizar os dados
                                time.sleep(3)
                                st.rerun()  # Recarrega a aplicação

                # Botão para abrir o modal de nova solicitação
                colunas_botoes[0].button("Nova solicitação", on_click=nova_solicitacao, width=300, icon=":material/calendar_add_on:")



        # 2 - BOTÃO DE EDITAR SOLICITAÇÃO

        # Roteamento de tipo de usuário - somente para gestao_ferias
        if set(st.session_state.tipo_usuario) & {"admin","gestao_ferias"}:

            if colaborador_selecionado != "Todos(as)":

                # Função para abrir o modal "Editar solicitação"
                @st.dialog("Editar solicitação")
                def editar_solicitacao():

                    colaborador_dados = next(
                        (registro for registro in colaboradores if registro.get("nome_completo") == colaborador_selecionado),
                        None
                    )

                    # Verifica se há dados do colaborador selecionado
                    if colaborador_dados:
                        
                        # Obtém uma lista de todos os anos disponíveis na chave "anos"
                        # anos_disponiveis = reversed(list(colaborador_dados["anos"].keys()))
                        anos_disponiveis = sorted(
                            colaborador_dados.get("férias", {}).get("anos", {}).keys(),
                            reverse=True
                        )

                        # Primeiro selectbox para o ano
                        ano_selecionado = st.selectbox("Selecione o ano", anos_disponiveis, format_func=str, key="ano_selecionado")

                        # Obter as solicitações do ano selecionado
                        solicitacoes_ano = colaborador_dados.get("férias", {}).get("anos", {}).get(ano_selecionado, {}).get("solicitacoes", [])

                        # Verifica se há solicitações disponíveis no ano selecionado
                        if solicitacoes_ano:
                            # Define o rótulo e as opções para seleção de uma solicitação específica
                            def formatar_opcao(indice):
                                # Exibe o período da solicitação selecionada (início e fim)
                                return f"{solicitacoes_ano[indice]['lista_de_dias'][0]} a {solicitacoes_ano[indice]['lista_de_dias'][-1]}"

                            solicitacao_selecionada_indice = st.selectbox(
                                "Selecione uma solicitação:",
                                range(len(solicitacoes_ano)),
                                format_func=formatar_opcao,
                                key="solicitacao_selecionada_indice"
                            )
                            
                            # Recupera os dados da solicitação selecionada usando o índice retornado pelo `selectbox`
                            solicitacao_editar = solicitacoes_ano[solicitacao_selecionada_indice]
                            
                            st.write('')
                            # Cria abas para permitir edição ou exclusão da solicitação
                            tab1, tab2 = st.tabs([":material/edit: EDITAR", ":material/delete: EXCLUIR"])
                            
                            # Aba para EDITAR a solicitação ===================
                            with tab1.form(key=f'form_editar_solicitacao_{solicitacao_selecionada_indice}'):
                                
                                # Exibe campos para edição dos dados da solicitação
                                data_solicitacao = st.text_input("Data da solicitação", value=solicitacao_editar.get('data_solicitacao', ''))
                                dias_solicitados = st.text_input(
                                    "Período solicitado",
                                    value=", ".join(map(str, solicitacao_editar.get('lista_de_dias', [])))
                                )
                                dias_uteis = st.number_input(
                                    "Dias úteis",
                                    value=int(solicitacao_editar.get('numero_dias_uteis', 0)),
                                    min_value=0,
                                    step=1
                                )
                                observacoes = st.text_input("Observações (opcional)", value=solicitacao_editar.get('observacoes', ''))

                                # Botão para salvar as alterações realizadas
                                st.write('')
                                if st.form_submit_button("Salvar alterações", width=200, icon=":material/save:", type="primary"):
                                    # Atualiza a solicitação específica na lista local
                                    solicitacoes_ano[solicitacao_selecionada_indice] = {
                                        'data_solicitacao': data_solicitacao,
                                        'lista_de_dias': [dia.strip() for dia in dias_solicitados.split(',')],
                                        'numero_dias_uteis': dias_uteis,
                                        'observacoes': observacoes
                                    }

                                    # Monta o filtro para encontrar o colaborador correto no banco
                                    filtro = { "nome_completo": colaborador_selecionado }

                                    # Monta a operação de atualização no caminho correto
                                    novo_valor = {
                                        "$set": {
                                            f"férias.anos.{ano_selecionado}.solicitacoes": solicitacoes_ano
                                        }
                                    }

                                    # Executa a atualização no MongoDB
                                    colecao.update_one(filtro, novo_valor)

                                    # Atualiza os dados locais após a alteração
                                    atualizar_dados_colaborador()
                                    
                                    # Mensagem de sucesso e recarregamento da página
                                    st.success("Período atualizado com sucesso!", icon=":material/thumb_up:")
                                    time.sleep(4)
                                    st.rerun()



                            # Aba para DELETAR a solicitação ===================
                            with tab2:
                                st.write('Você tem certeza que deseja EXCLUIR esse período de férias?')
                                st.write(f'**{formatar_opcao(solicitacao_selecionada_indice)}**')
                                st.markdown('<p style="color:red;">Após apertar o botão, a operação não poderá ser desfeita!</p>', unsafe_allow_html=True)
                                
                                st.write('')
                                if st.button("Excluir período", icon=":material/delete:", type="secondary", key=f'deletar_solicitacao_{solicitacao_selecionada_indice}', width=200):
                                    # Remove a solicitação selecionada
                                    del solicitacoes_ano[solicitacao_selecionada_indice]


                                    # Atualiza o banco de dados
                                    colecao.update_one(
                                        { "nome_completo": colaborador_selecionado },  # Filtro correto para encontrar o colaborador
                                        { 
                                            "$set": { 
                                                f"férias.anos.{ano_selecionado}.solicitacoes": solicitacoes_ano  # Caminho correto
                                            } 
                                        }
                                    )

                                    atualizar_dados_colaborador()
                                    
                                    # Mensagem de sucesso
                                    st.success("Período excluído!", icon=":material/thumb_up:")
                                    time.sleep(4)
                                    st.rerun()

                        else:
                            # Mensagem se não houver solicitações no ano
                            st.write("Não há solicitações neste ano.")

                # Botão para abrir o modal de "Editar solicitação"
                colunas_botoes[1].button("Editar solicitação", on_click=editar_solicitacao, width=300, icon=":material/edit:")



        # 3 - BOTÃO DE ENVIAR EMAIL DE SALDO

        # Roteamento de tipo de usuário - somente para gestao_ferias
        if set(st.session_state.tipo_usuario) & {"admin","gestao_ferias"}:

            if colaborador_selecionado != "Todos(as)":

                @st.dialog("Enviar saldo")
                def enviar_saldo():

                    colaborador_dados = next(
                        (registro for registro in colaboradores if registro.get("nome_completo") == colaborador_selecionado),
                        None
                    )

                    # Verifica se há dados do colaborador selecionado
                    if colaborador_dados:
                        anos_disponiveis = sorted(
                            colaborador_dados.get("férias", {}).get("anos", {}).keys(),
                            reverse=True
                        )
                    else:
                        st.write("Não há dados.")
                        return  # Encerra o modal caso não haja dados disponíveis

                    # Título dentro do modal
                    st.write("**Enviar saldo por e-mail**")

                    # Selectbox para selecionar o ano
                    ano_selecionado = st.selectbox("Selecione o ano", anos_disponiveis, key="ano_selecionado_email")


                    # Input para o destinatário
                    destinatario = st.text_input(
                        "Enviar para:", 
                        value=colaborador_dados.get("e_mail", ""),  # Obtém o valor da chave "email", ou uma string vazia se não existir
                        key="email_destinatario"
                    )

                    # Garante que os dados do ano selecionado são acessados
                    if ano_selecionado:
                        ano_dados = colaborador_dados.get("férias", {}).get("anos", {}).get(ano_selecionado, {})

                        df_mail = montar_dataframe_saldo_do_ano(ano_selecionado, ano_dados)

                    # Botão para enviar o e-mail
                    st.write('')
                    if st.button("Enviar e-mail", width=200, icon=":material/mail:", type="primary"):
                        # Extrai os valores do DataFrame com base nas linhas e colunas
                        residual_ano_anterior = df_mail.iloc[0, 1]  # Primeira linha, segunda coluna
                        saldo_inicio_ano = df_mail.iloc[1, 1]      # Segunda linha, segunda coluna
                        total_gozado = df_mail.iloc[2, 1]          # Terceira linha, segunda coluna
                        saldo_atual = df_mail.iloc[3, 1]           # Quarta linha, segunda coluna


                        # Verifica se há solicitações para o ano
                        
                        # Se há solicitações, envia tabela de saldo e a tabela de solicitações
                        if not df_solicitacoes.empty:
                            # Aplicar a transformação diretamente com lambda para listas
                            df_solicitacoes['Período solicitado'] = df_solicitacoes['Período solicitado'].apply(
                                lambda periodo: f"{periodo[0]} a {periodo[1]}"
                            )

                            # Renomear a coluna Período solicitado para Dias de início e fim
                            df_solicitacoes.rename(columns={'Período solicitado': 'Dias de início e fim'}, inplace=True)

                            # Converte df_solicitacoes para HTML
                            df_solicitacoes_html = df_solicitacoes.to_html(index=False, classes="table", border=1, justify="left")

                            # Monta o conteúdo do e-mail com uma tabela HTML



                            conteudo_email = f"""
                            <html>
                            <head>
                                <meta charset="UTF-8">
                                <style>
                                    body {{
                                        font-family: Arial, sans-serif;
                                        background-color: #f9f9f9;
                                        padding: 30px;
                                        color: #333;
                                    }}
                                    .logo {{
                                        text-align: center;
                                        margin-bottom: 20px;
                                    }}
                                    .logo img {{
                                        max-width: 200px;
                                        height: auto;
                                        margin-bottom: 20px;
                                    }}
                                    .container {{
                                        background-color: #ffffff;
                                        padding: 20px 30px;
                                        border-radius: 8px;
                                        border: 1px solid #ddd;
                                        max-width: 700px;
                                        margin: auto;
                                    }}
                                    h2 {{
                                        color: #004d40;
                                    }}
                                    table {{
                                        width: 100%;
                                        border-collapse: collapse;
                                        margin-top: 15px;
                                    }}
                                    th, td {{
                                        border: 1px solid #ccc;
                                        padding: 10px;
                                        text-align: left;
                                    }}
                                    th {{
                                        background-color: #eeeeee;
                                    }}
                                    td:last-child {{
                                        text-align: right;
                                    }}
                                    .section-title {{
                                        margin-top: 30px;
                                        margin-bottom: 10px;
                                        font-weight: bold;
                                        color: #00695c;
                                    }}
                                    .footer {{
                                        margin-top: 40px;
                                        text-align: center;
                                        font-size: 13px;
                                        color: #777;
                                    }}
                                </style>
                            </head>

                            <body>
                                <div class="logo">
                                    <img src="https://ispn.org.br/site/wp-content/uploads/2021/04/logo_ISPN_2021.png" alt="Logo ISPN">
                                </div>

                                <div class="container">
                                    <p>Olá <strong>{colaborador_selecionado}</strong></p>
                                    <p>Segue abaixo o seu saldo de férias para o ano de <strong>{ano_selecionado}</strong>:</p>

                                    <div class="section-title">Saldo de Férias</div>
                                    <table>
                                        <tr>
                                            <th>Descrição</th>
                                            <th>Quantidade (dias)</th>
                                        </tr>
                                        <tr>
                                            <td>Residual do ano anterior ({int(ano_selecionado) - 1})</td>
                                            <td>{residual_ano_anterior}</td>
                                        </tr>
                                        <tr>
                                            <td>Saldo do início do ano</td>
                                            <td>{saldo_inicio_ano}</td>
                                        </tr>
                                        <tr>
                                            <td>Total gozado</td>
                                            <td>{total_gozado}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>Saldo atual</strong></td>
                                            <td><strong>{saldo_atual}</strong></td>
                                        </tr>
                                    </table>

                                    <div class="section-title">Solicitações do ano</div>
                                    {df_solicitacoes_html}

                                    <br>
                                    <p>Atenciosamente,</p>
                                    <p><strong>Departamento Pessoal do ISPN</strong></p>
                                </div>
                            </body>
                            </html>
                            """


                        
                        # Se não há solicitações, envia só a tabela de saldo
                        else:
                            # Monta o conteúdo do e-mail sem a tabela de solicitações

                            conteudo_email = f"""
                            <html>
                            <head>
                                <meta charset="UTF-8">
                                <style>
                                    body {{
                                        font-family: Arial, sans-serif;
                                        background-color: #f9f9f9;
                                        padding: 30px;
                                        color: #333;
                                    }}
                                    .logo {{
                                        text-align: center;
                                        margin-bottom: 20px;
                                    }}
                                    .logo img {{
                                        max-width: 200px;
                                        height: auto;
                                    }}
                                    .container {{
                                        background-color: #ffffff;
                                        padding: 20px 30px;
                                        border-radius: 8px;
                                        border: 1px solid #ddd;
                                        max-width: 700px;
                                        margin: auto;
                                    }}
                                    table {{
                                        border-collapse: collapse;
                                        width: 100%;
                                        margin-top: 20px;
                                    }}
                                    th, td {{
                                        border: 1px solid #ccc;
                                        padding: 10px;
                                        text-align: left;
                                    }}
                                    th {{
                                        background-color: #eeeeee;
                                    }}
                                    td:nth-child(2) {{
                                        text-align: right;
                                    }}
                                    .footer {{
                                        margin-top: 40px;
                                        text-align: center;
                                        font-size: 13px;
                                        color: #777;
                                    }}
                                </style>
                            </head>

                            <body>
                                <div class="logo">
                                    <img src="https://ispn.org.br/site/wp-content/uploads/2021/04/logo_ISPN_2021.png" alt="Logo ISPN">
                                </div>

                                <div class="container">
                                    <p>Olá <strong>{colaborador_selecionado}</strong></p>
                                    <p>Segue abaixo o seu saldo de férias para o ano de <strong>{ano_selecionado}</strong>:</p>

                                    <table>
                                        <tr>
                                            <th>Descrição</th>
                                            <th>Quantidade (dias)</th>
                                        </tr>
                                        <tr>
                                            <td>Residual do ano anterior ({int(ano_selecionado) - 1})</td>
                                            <td>{residual_ano_anterior}</td>
                                        </tr>
                                        <tr>
                                            <td>Saldo do início do ano</td>
                                            <td>{saldo_inicio_ano}</td>
                                        </tr>
                                        <tr>
                                            <td>Total gozado</td>
                                            <td>{total_gozado}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>Saldo atual</strong></td>
                                            <td><strong>{saldo_atual}</strong></td>
                                        </tr>
                                    </table>

                                    <br>
                                    <p>Atenciosamente,</p>
                                    <p><strong>Departamento Pessoal do ISPN</strong></p>
                                </div>
                            </body>
                            </html>
                            """


                        # Lógica de envio do e-mail
                        enviar_email(destinatario, f"Saldo de férias - {ano_selecionado}", conteudo_email, html=True)

                        # Mensagem de confirmação
                        st.success("E-mail enviado com sucesso!", icon=":material/mail:")

                        # Aguarda 4 segundos antes de recarregar
                        # time.sleep(4)
                        # st.rerun()


                # Botão para abrir o modal "Enviar saldo"
                colunas_botoes[2].button("Enviar saldo", on_click=enviar_saldo, width=300, icon=":material/mail:")



        # 4 - BOTÃO DE EDITAR COLABORADOR(A)

        # Roteamento de tipo de usuário - somente para gestao_ferias
        if set(st.session_state.tipo_usuario) & {"admin","gestao_ferias"}:

            if colaborador_selecionado != "Todos(as)":

                colaborador_dados = next(
                    (registro for registro in colaboradores if registro.get("nome_completo") == colaborador_selecionado),
                    None
                )

                # Função para encontrar o menor ano com base no valor_inicial_ano_atual
                def encontrar_ano_menor_valor(anos):
                    return min(anos, key=lambda ano: anos[ano].get("valor_inicial_ano_atual", float('inf')))

                @st.dialog("Editar colaborador(a)")
                def editar_colaborador(nome_colaborador, colaborador_dados): 

                    global colaborador_selecionado

                    # Identificar o menor ano
                    anos_cadastrados = colaborador_dados.get("férias", {}).get("anos", {})
                    # anos_cadastrados = colaborador_dados.get("anos", {})

                    ano_menor_valor = encontrar_ano_menor_valor(anos_cadastrados)

                    # Input para editar o residual do ano anterior
                    # residual_atual = anos_cadastrados[ano_menor_valor].get("residual_ano_anterior")
                    residual_atual = (
                        anos_cadastrados.get(ano_menor_valor, {}).get("residual_ano_anterior", 0)
                        if ano_menor_valor else 0
                    )

                    novo_residual = st.number_input(f"Residual do ano anterior ao primeiro ano cadastrado ({int(ano_menor_valor) - 1})", 
                                                    value=residual_atual, 
                                                    step=1,
                                                    help="Só é possível editar o primeiro ano cadastrado."
                                                    )

                    # Input para editar as férias recebidas no primeiro ano cadastrado
                    recebidas_atual = anos_cadastrados[ano_menor_valor].get("valor_inicial_ano_atual")
                    novo_dias_recebidos = st.number_input(f"Férias recebidas no primeiro ano cadastrado ({ano_menor_valor})", 
                                                    value=recebidas_atual, 
                                                    step=1,
                                                    help="Só é possível editar o primeiro ano cadastrado."
                                                    )


                    # Input para editar "a_receber"
                    a_receber_atual = anos_cadastrados[ano_menor_valor].get("a_receber")
                    novo_a_receber = st.number_input(f"Dias a receber na virada do primeiro ano", 
                                                    value=a_receber_atual, 
                                                    step=1,
                                                    help="Só para novos cadastros, que vão receber alguns de dias na virada do próximo ano."
                                                    )


                    # Botão para salvar alterações no banco de dados
                    if st.button("Salvar alterações", type="primary", icon=":material/save:"):
                        # Criar o dicionário de atualização apenas com os dados de férias
                        atualizacoes = {
                            f"férias.anos.{ano_menor_valor}.a_receber": novo_a_receber,
                            f"férias.anos.{ano_menor_valor}.residual_ano_anterior": novo_residual,
                            f"férias.anos.{ano_menor_valor}.valor_inicial_ano_atual": novo_dias_recebidos,
                        }

                        # Atualizar os campos no MongoDB
                        colecao.update_one(
                            {"nome_completo": nome_colaborador},  # Filtra pelo nome do colaborador
                            {"$set": atualizacoes}
                        )


                        # Atualiza banco de dados
                        atualizar_dados_colaborador()

                        st.success("Informações atualizadas com sucesso!")

                        # Aguarda 3 segundos antes de recarregar a página para atualizar os dados
                        time.sleep(3)
                        st.rerun()

                # Botão para editar colaborardor
                colunas_botoes[3].button("Editar colaborador(a)", 
                                    on_click=lambda: editar_colaborador(colaborador_selecionado, colaborador_dados), 
                                    width=300, 
                                    icon=":material/person_edit:")


        gerar_grafico_tabela(colaborador_selecionado)


    # Chama página de férias para admin, gestao_ferias e supervisao_ferias
    ferias_admin_gestaoFerias_supervisaoFerias()


# Se for um usuário comum
else:

    colaborador_selecionado = 'Todos(as)'

    st.write('')

    gerar_grafico_tabela(colaborador_selecionado)
