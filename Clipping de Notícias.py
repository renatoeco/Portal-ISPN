import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from funcoes_auxiliares import conectar_mongo_portal_ispn
import locale
import math
import io


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.header("Clipping de Notícias")

st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

st.write('')


#######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
#######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas (inalterada)
monitor_noticias = db["monitor_noticias"]  # Coleção de notícias 

# Obtém todos os documentos da coleção (cada doc = 1 notícia)
documentos = list(monitor_noticias.find())


########################################################################################################
# FUNÇÕES
########################################################################################################


@st.dialog("Triagem de notícias", width="large")
def editar_status_noticias_dialog():
    mostrar_irrelevantes = st.checkbox("Mostrar notícias irrelevantes")

    st.write("")

    # Agora chama apenas uma vez
    renderizar_noticias_fragment(mostrar_irrelevantes=mostrar_irrelevantes)


# Fragmento reutilizável que renderiza as notícias e os botões de triagem
@st.fragment
def renderizar_noticias_fragment(mostrar_irrelevantes=False):
    # Contador exibido SEMPRE, pois agora o fragmento roda apenas uma vez
    qtd_sem_status = monitor_noticias.count_documents({
        "$or": [
            {"status": {"$exists": False}},
            {"status": None},
            {"status": ""},
            {"status": {"$regex": r"^\s*$"}}
        ]
    })

    if qtd_sem_status > 0:
        st.warning(f"{qtd_sem_status} notícia(s) aguardando triagem.")
    else:
        st.success("Todas as notícias foram triadas.", icon=":material/check_circle:")

    # Busca todas as notícias relevantes ou irrelevantes
    if mostrar_irrelevantes:
        query = {"status": "Irrelevante"}
    else:
        query = {
            "$or": [
                {"status": {"$exists": False}},
                {"status": None},
                {"status": ""},
                {"status": {"$regex": r"^\s*$"}}
            ]
        }

    noticias_cursor = monitor_noticias.find(query).sort("data", -1)
    noticias = list(noticias_cursor)

    for idx, noticia in enumerate(noticias):
        st.subheader(str(noticia.get("titulo_da_noticia", "(Sem título)")))

        data_val = pd.to_datetime(noticia.get("data"), errors='coerce')
        data_fmt = data_val.strftime('%d/%m/%Y') if not pd.isna(data_val) else "Data inválida"
        st.write(f"{data_fmt} | {noticia.get('fonte', '')}")

        link_val = noticia.get("link")
        if link_val:
            st.write(f"[Abrir notícia]({link_val})", unsafe_allow_html=True)

        st.write(f"**Palavra-chave:** {noticia.get('palavra_chave', '(Não definida)')}")

        if mostrar_irrelevantes:
            st.markdown(f"**Status:** {noticia.get('status', 'Sem status')}")

        btn_cols = st.columns([1, 1, 2])
        if mostrar_irrelevantes:
            if btn_cols[0].button("Relevante", key=f"relevante_{idx}", icon=":material/check:", use_container_width=True):
                monitor_noticias.update_one({"_id": noticia["_id"]}, {"$set": {"status": "Relevante"}})
                st.rerun(scope="fragment")
        else:
            with btn_cols[0]:
                if st.button("Relevante", key=f"relevante_{idx}", icon=":material/check:", use_container_width=True):
                    monitor_noticias.update_one({"_id": noticia["_id"]}, {"$set": {"status": "Relevante"}})
                    st.rerun(scope="fragment")

            with btn_cols[1]:
                if st.button("Irrelevante", key=f"irrelevante_{idx}", icon=":material/close:", use_container_width=True):
                    monitor_noticias.update_one({"_id": noticia["_id"]}, {"$set": {"status": "Irrelevante"}})
                    st.rerun(scope="fragment")

        st.divider()


########################################################################################################
# MAIN
########################################################################################################


# Define o locale para formatação de datas
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except locale.Error:
    pass

# Verifica se há dados no banco
if not documentos:
    st.info("Nenhuma notícia encontrada no banco de dados.")
else:
    # Como cada documento já É uma notícia, basta normalizar e renomear colunas para manter o restante do fluxo.
    # Cria DataFrame base
    df = pd.DataFrame(documentos)

    # Garantir todas as colunas esperadas
    for coluna in ["palavra_chave", "titulo_da_noticia", "data", "fonte", "link", "status"]:
        if coluna not in df.columns:
            df[coluna] = None

    # Renomear para manter compatibilidade com o restante do código antigo
    df = df.rename(columns={
        "palavra_chave": "Palavra-chave",
        "titulo_da_noticia": "Título da notícia",
        "data": "Data",
        "fonte": "Fonte",
        "link": "Link",
        "status": "Status",
    })

    # FILTROS //////////////////////////////////////////////////////////////////////////////////////////////////
    
    # Prepara colunas auxiliares para filtros
    def limpar_texto(texto):
        return texto.strip().lower() if isinstance(texto, str) else ""

    df["Palavra-chave limpa"] = df["Palavra-chave"].apply(limpar_texto)
    df["Fonte limpa"] = df["Fonte"].apply(limpar_texto)
    df["Data_Convertida"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
    df = df.sort_values("Data_Convertida", ascending=False).reset_index(drop=True)
    df["Data da notícia"] = df["Data_Convertida"].dt.strftime("%d/%m/%Y")

    # Prepara opções de filtro, só com as notícias relevantes
    df_relevantes = df[df["Status"] == "Relevante"].copy()
    titulos_opcoes = sorted(df_relevantes["Palavra-chave limpa"].dropna().unique())
    fontes_opcoes  = sorted(df_relevantes["Fonte limpa"].dropna().unique())

    with st.expander("Filtros", expanded=False, icon=":material/filter_alt:"):
        # Formulário que conterá os campos de filtro
        with st.form("filtros_form", border=False):
            # Três colunas para os campos de filtro
            col1, col2, col3 = st.columns(3)

            with col1:
                titulos_selecionados = st.multiselect(
                    "Palavra-chave",
                    options=titulos_opcoes,
                    format_func=lambda x: df[df["Palavra-chave limpa"] == x]["Palavra-chave"].iloc[0],
                    placeholder="Escolha uma palavra-chave"
                )

            # Filtra com base nas palavras-chave selecionadas
            if titulos_selecionados:
                df_filtrado_por_titulo = df_relevantes[df_relevantes["Palavra-chave limpa"].isin(titulos_selecionados)]
                fontes_opcoes_filtradas = sorted(df_filtrado_por_titulo["Fonte limpa"].unique())
            else:
                fontes_opcoes_filtradas = fontes_opcoes

            with col2:
                fontes_selecionadas = st.multiselect(
                    "Veículo",
                    options=fontes_opcoes_filtradas,
                    format_func=lambda x: df[df["Fonte limpa"] == x]["Fonte"].iloc[0],
                    placeholder="Escolha um veículo"
                )

            # Filtro de datas
            hoje = date.today()
            data_min = df["Data_Convertida"].min().date() if not df["Data_Convertida"].isna().all() else hoje
            data_max = df["Data_Convertida"].max().date() if not df["Data_Convertida"].isna().all() else hoje

            # Intervalo padrão: últimos 30 dias (ajustado p/ evitar erro se min/max vazios)
            inicio_padrao = max(data_min, hoje - timedelta(days=31))
            fim_padrao = min(data_max, hoje - timedelta(days=1))

            # Corrigir se fim_padrao < inicio_padrao
            if fim_padrao < inicio_padrao:
                fim_padrao = inicio_padrao

            with col3:
                intervalo_datas = st.date_input(
                    "Período",
                    value=(inicio_padrao, fim_padrao),
                    min_value=data_min,
                    max_value=data_max,
                    format="DD/MM/YYYY"
                )


            # Garantir valores padrão
            if not intervalo_datas:
                intervalo_datas = (inicio_padrao, fim_padrao)

            aplicar = st.form_submit_button("Aplicar filtros", icon=":material/check:", type="primary")

    # Aplica os filtros selecionados
    if aplicar:
        if not titulos_selecionados:
            titulos_selecionados = titulos_opcoes
        if not fontes_selecionadas:
            fontes_selecionadas = fontes_opcoes

        df_filtrado = df_relevantes[
            (df_relevantes["Palavra-chave limpa"].isin(titulos_selecionados)) &
            (df_relevantes["Fonte limpa"].isin(fontes_selecionadas)) &
            (df_relevantes["Data_Convertida"].dt.date >= intervalo_datas[0]) &
            (df_relevantes["Data_Convertida"].dt.date <= intervalo_datas[1])
        ]
    else:
        df_filtrado = df_relevantes[
            df_relevantes["Data_Convertida"].dt.date.between(hoje - timedelta(days=31), hoje - timedelta(days=1))
        ]

    st.write("")

    # TRIAGEM //////////////////////////////////////////////////////////////////////////////////////////////
    noticias_sem_status = df[(df["Status"].isna()) | (df["Status"].astype(str).str.strip() == "")]
    qtd_sem_status = len(noticias_sem_status)

    if qtd_sem_status > 0:
        st.warning(f"{qtd_sem_status} notícia(s) aguardando triagem.", icon=":material/warning:")

    st.write("")

    # Botão de triagem só para alguns tipos de usuário
    if set(st.session_state.tipo_usuario) & {"admin", "gestao_noticias"}:
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

        with col1:
            st.button("Triagem de notícias", icon=":material/search:", use_container_width=True, on_click=editar_status_noticias_dialog)

        with col2:
            if st.button("Atualizar página", icon=":material/refresh:", use_container_width=True):
                st.rerun()

        with col3:
            container_botao_exportar = st.container()

        with col4:
            @st.dialog("Palavras-chave monitoradas")
            def mostrar_palavras_chave():
                palavras = [
                    "Economias da sociobiodiversidade",
                    "Fundo Ecos",
                    "Institute for Society, Population and Nature",
                    "Instituto Sociedade, População e Natureza",
                    "ISPN",
                    "Observatório da Economia da Sociobiodiversidade",
                    "Observatório da sociobiodiversidade",
                    "ÓSocioBio",
                    "Paisagens Produtivas Ecossociais",
                    "PPP-ECOS",
                    "Rede Cerrado",
                    "Tô no Mapa",
                    "PIPOU indígena"
                ]
                for palavra in palavras:
                    st.write(f"- {palavra}")
                st.divider()
                st.write("Para adicionar novas palavras-chave, entre em contato com renato@ispn.org.br ou bernardo@ispn.org.br.")

            if st.button("Palavras-chave", icon=":material/list:", use_container_width=True):
                mostrar_palavras_chave()
    else:
        col1, col2, col3 = st.columns([2, 2, 1])
        # Mesmo se não for admin precisamos definir container_botao_exportar p/ botão de download adiante
        container_botao_exportar = col3.container()

    st.write('')

    # Contador de notícias na tela ////////////////////////////////////////////////////////////////////////////////////////////
    num_noticias = len(df_filtrado)
    if num_noticias == 1:
        st.subheader("1 notícia relevante")
    else:
        st.write('')
        st.markdown(f"<p style='font-size: 1.5em'><b>{num_noticias} notícias relevantes</b> entre {intervalo_datas[0].strftime('%d/%m/%Y')} e {intervalo_datas[1].strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)

    # Gráfico ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    if not df_filtrado.empty:
        df_filtrado_sorted = df_filtrado.sort_values(by='Data_Convertida')

        # Contagem de notícias por dia
        contagem = (
            df_filtrado_sorted
            .groupby(df_filtrado_sorted['Data_Convertida'].dt.normalize())
            .size()
            .rename_axis('Data')
            .reset_index(name='Quantidade')
        )

        # Criar série contínua de dias
        data_min_real = contagem['Data'].min()
        data_max_real = contagem['Data'].max()
        todos_dias = pd.date_range(data_min_real, data_max_real, freq='D')
        df_completo = pd.DataFrame({'Data': todos_dias})

        contagem_completa = df_completo.merge(contagem, on='Data', how='left').fillna(0)
        contagem_completa['Quantidade'] = contagem_completa['Quantidade'].astype(int)
        contagem_completa['Texto'] = contagem_completa['Quantidade'].replace(0, "")

        # Definir altura máxima em barras (eixo Y)
        max_qtd = contagem_completa['Quantidade'].max()
        y_limite = max_qtd * 1.20  # acima do maior valor para não encostar no topo

        # Gráfico
        fig = px.bar(
            contagem_completa,
            x="Data",
            y="Quantidade",
            text="Texto",
            labels={"Data": "", "Quantidade": ""}
        )

        fig.update_traces(
            textposition="outside",
            marker_color="#1f77b4",
        )

        fig.update_layout(
            xaxis=dict(
                tickformat="%d/%m/%Y",
                tickangle=-45,
                dtick="D1",
                showgrid=False
            ),
            yaxis=dict(
                visible=False,
                showgrid=False,
                zeroline=False,
                range=[0, y_limite]  # aqui limitamos a altura máxima
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            height=220
        )

        st.plotly_chart(fig, 
                        use_container_width=True,
                        config={
                            "displayModeBar": False,  # remove a barra de ferramentas
                            "staticPlot": True        # torna o gráfico 100% estático
                        }
                        )


    # TABELA ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////// 
    st.write("")
    container_tabela = st.container()

    tabela = df_filtrado[["Data da notícia", "Título da notícia", "Fonte", "Palavra-chave", "Link"]].copy()

    # Prepara uma versão limpa só para exportação (sem mudar nomes nem transformar em HTML)
    tabela_exportar = df_filtrado[["Palavra-chave", "Data da notícia", "Título da notícia", "Fonte", "Link"]].copy()

    tabela = tabela.rename(columns={
        "Título da notícia": "Notícia",
        "Data da notícia": "Data",
        "Fonte": "Veículo",
    })

    # Torna a coluna 'Notícia' um link clicável
    tabela['Notícia'] = tabela.apply(
        lambda row: f'<a href="{row["Link"]}" target="_blank">{row["Notícia"]}</a>',
        axis=1
    )

    tabela = tabela.drop(columns=['Link'])

    # Paginação
    linhas_por_pagina = 20
    total_linhas = len(tabela)
    total_paginas = max(1, math.ceil(total_linhas / linhas_por_pagina))

    st.write("")
    col1, col2, col3 = st.columns([5, 2, 1])

    pagina_atual = col3.number_input(
        "Página",
        min_value=1,
        max_value=total_paginas,
        value=1,
        step=1
    )
    if pagina_atual is None:
        pagina_atual = 1

    inicio = (pagina_atual - 1) * linhas_por_pagina
    fim = inicio + linhas_por_pagina

    with col2:
        st.write("")
        st.write("")
        st.write(f"Mostrando {inicio + 1} a {min(fim, total_linhas)} de {total_linhas} resultados")

    tabela_paginada = tabela.iloc[inicio:fim]

    html = tabela_paginada.to_html(escape=False, index=False)

    st.markdown(
        """
        <style>
        table {
            width: 100%;
            border-collapse: collapse;
            border-radius: 10px;
            overflow: hidden;
        }
        table th {
            text-align: left !important;
            padding: 8px;
            border: 1px solid #ddd;
            background-color: #f2f2f2;
            min-width: 150px; 
        }
        table td {
            padding: 8px;
            border: 1px solid #ddd;
            min-width: 150px;
        }
        table th:nth-child(1), table td:nth-child(1) { min-width: 100px; }
        table th:nth-child(2), table td:nth-child(2) { min-width: 350px; }
        table th:nth-child(3), table td:nth-child(3) { max-width: 250px; }
        table th:nth-child(4), table td:nth-child(4) { max-width: 300px; }
        </style>
        """,
        unsafe_allow_html=True
    )

    container_tabela.markdown(html, unsafe_allow_html=True)

    # EXPORTAR TABELA ------------------------------------------------------------------------------------
    tabela_exportar = tabela_exportar.rename(columns={
        "Título da notícia": "Notícia",
        "Data da notícia": "Data",
        "Fonte": "Veículo"
    })

    colunas_exportar = ['Palavra-chave', 'Data', 'Notícia', 'Veículo','Link']
    tabela_exportar = tabela_exportar[colunas_exportar]

    output = io.BytesIO()
    tabela_exportar.to_excel(output, index=False)
    output.seek(0)

    data_de_hoje = date.today().strftime("%d/%m/%Y")

    container_botao_exportar.download_button(
        label="Baixar tabela",
        data=output,
        file_name=f"clipping_de_noticias_ISPN - {data_de_hoje}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        icon=":material/file_download:"
    )