import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import time
from datetime import date, timedelta
from funcoes_auxiliares import conectar_mongo_portal_ispn
import locale
import math
import io


st.set_page_config(layout="wide")
st.header("Visualizador de Notícias do Google Alertas")


#######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
#######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas
monitor_noticias = db["monitor_noticias"]  # Coleção de notícias monitoradas

# Obtém todos os documentos da coleção
documentos = list(monitor_noticias.find())


########################################################################################################
# FUNÇÕES
########################################################################################################


# Diálogo de triagem para revisão e alteração de status das notícias
@st.dialog("Triagem", width="large")
def editar_status_noticias_dialog():
    titulos_busca = monitor_noticias.distinct("Palavra-chave")
    abas = st.tabs(titulos_busca)

    for i, titulo in enumerate(titulos_busca):
        with abas[i]:
            mostrar_irrelevantes = st.checkbox("Mostrar notícias irrelevantes", key=f"mostrar_irrelevantes_{i}")
            renderizar_noticias_fragment(titulo, mostrar_irrelevantes=mostrar_irrelevantes)


# Fragmento reutilizável que renderiza as notícias e os botões de triagem
@st.fragment
def renderizar_noticias_fragment(titulo, mostrar_irrelevantes=False):
    doc = monitor_noticias.find_one({"Palavra-chave": titulo})
    noticias = doc.get("noticias", []) if doc else []

    # Filtra as notícias com base no status
    if mostrar_irrelevantes:
        noticias_exibidas = [n for n in noticias if n.get("Status") == "Irrelevante"]
    else:
        noticias_exibidas = [n for n in noticias if not n.get("Status")]

    if not noticias_exibidas:
        st.info("Nenhuma notícia para exibir.")
        return

    # Loop para exibir cada notícia
    for idx, noticia in enumerate(noticias_exibidas):
        st.markdown(f"#### {noticia['Título da notícia']}")
        data = pd.to_datetime(noticia.get("Data"), errors='coerce')
        data_fmt = data.strftime('%d/%m/%Y') if not pd.isna(data) else "Data inválida"
        st.markdown(f"**{data_fmt}** | **{noticia['Fonte']}**")
        st.markdown(f"[Abrir notícia]({noticia['Link']})", unsafe_allow_html=True)

        if mostrar_irrelevantes:
            st.markdown(f"**Status:** {noticia.get('Status', 'Sem status')}")

        # Centraliza os botões na interface
        left_col, center_col, right_col = st.columns([1, 2, 1])
        with center_col:
            btn_cols = st.columns(2)
            if mostrar_irrelevantes:
                # Mostra apenas o botão "Relevante"
                if st.button("Relevante", key=f"relevante_{titulo}_{idx}", icon=":material/check:", use_container_width=True):
                    monitor_noticias.update_one(
                        {"Palavra-chave": titulo, "noticias.Link": noticia["Link"]},
                        {"$set": {"noticias.$.Status": "Relevante"}}
                    )
                    st.success("Status atualizado para **Relevante** com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")
            else:
                # Mostra os dois botões: Relevante e Irrelevante
                if btn_cols[0].button("Relevante", key=f"relevante_{titulo}_{idx}", icon=":material/check:"):
                    monitor_noticias.update_one(
                        {"Palavra-chave": titulo, "noticias.Link": noticia["Link"]},
                        {"$set": {"noticias.$.Status": "Relevante"}}
                    )
                    st.success("Status atualizado para **Relevante** com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")

                if btn_cols[1].button("Irrelevante", key=f"irrelevante_{titulo}_{idx}", icon=":material/close:"):
                    monitor_noticias.update_one(
                        {"Palavra-chave": titulo, "noticias.Link": noticia["Link"]},
                        {"$set": {"noticias.$.Status": "Irrelevante"}}
                    )
                    st.success("Status atualizado para **Irrelevante** com sucesso!")
                    time.sleep(2)
                    st.rerun(scope="fragment")

        st.divider()  # Linha divisória para separar notícias


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
    # Compila todas as notícias em um único DataFrame
    noticias = []
    for doc in documentos:
        titulo_busca = doc["Palavra-chave"]
        for n in doc.get("noticias", []):
            noticias.append({
                "Palavra-chave": titulo_busca,
                "Título da notícia": n.get("Título da notícia"),
                "Data": n.get("Data"),
                "Fonte": n.get("Fonte"),
                "Link": n.get("Link"),
                "Status": n.get("Status")
            })

    df = pd.DataFrame(noticias)

    # Prepara colunas auxiliares para filtros
    def limpar_texto(texto):
        return texto.strip().lower() if texto else ""

    df["Palavra-chave limpa"] = df["Palavra-chave"].apply(limpar_texto)
    df["Fonte limpa"] = df["Fonte"].apply(limpar_texto)
    df["Data_Convertida"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
    df = df.sort_values("Data_Convertida", ascending=False).reset_index(drop=True)
    df["Data da notícia"] = df["Data_Convertida"].dt.strftime("%d/%m/%Y")

    # Prepara opções de filtro
    titulos_opcoes = sorted(df["Palavra-chave limpa"].unique())
    fontes_opcoes  = sorted(df["Fonte limpa"].unique())

    with st.expander("Filtros", expanded=False, icon=":material/info:"):
        with st.form("filtros_form"):
            col1, col2, col3 = st.columns(3)

            with col1:
                titulos_selecionados = st.multiselect(
                    "Palavra-chave",
                    options=titulos_opcoes,
                    format_func=lambda x: df[df["Palavra-chave limpa"] == x]["Palavra-chave"].iloc[0],
                    placeholder="Escolha uma palavra-chave"
                )

            # Filtra as opções de fontes com base nas palavras-chave selecionadas
            if titulos_selecionados:
                df_filtrado_por_titulo = df[df["Palavra-chave limpa"].isin(titulos_selecionados)]
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

            data_min = df["Data_Convertida"].min().date()
            data_max = df["Data_Convertida"].max().date()
            hoje = date.today()
            inicio_padrao = max(data_min, hoje - timedelta(days=30))
            fim_padrao = min(data_max, hoje)

            with col3:
                intervalo_datas = st.date_input(
                    "Período",
                    value=(inicio_padrao, fim_padrao),
                    min_value=data_min,
                    max_value=data_max,
                    format="DD/MM/YYYY"
                )

            aplicar = st.form_submit_button("Aplicar filtros")



    # Aplica os filtros selecionados
    if aplicar:
        if not titulos_selecionados:
            titulos_selecionados = titulos_opcoes
        if not fontes_selecionadas:
            fontes_selecionadas = fontes_opcoes

        df_filtrado = df[
            (df["Palavra-chave limpa"].isin(titulos_selecionados)) &
            (df["Fonte limpa"].isin(fontes_selecionadas)) &
            (df["Data_Convertida"].dt.date >= intervalo_datas[0]) &
            (df["Data_Convertida"].dt.date <= intervalo_datas[1])
        ]
    else:
        df_filtrado = df

    col1, col2, col3 = st.columns([4, 1, 1])

    # Se usuário for admin, exibe botão para triagem
    tipos_usuario = st.session_state.get("tipo_usuario", [])
    if "adm" in tipos_usuario:
        noticias_sem_status = df[df["Status"].isna() | (df["Status"].str.strip() == "")]
        qtd_sem_status = len(noticias_sem_status)

        
        with col1:
            if qtd_sem_status > 0:
                st.warning(f"{qtd_sem_status} notícia(s) ainda precisam ser triadas.")

        with col2:
            st.button("Triagem de notícias", icon=":material/settings:", on_click=editar_status_noticias_dialog)

    with col3:
        if st.button("Atualizar (R)"):
            st.rerun()

        

    # Filtra apenas notícias marcadas como Relevantes para exibição
    df_filtrado = df_filtrado[df_filtrado["Status"] == "Relevante"]
    
    num_noticias = len(df_filtrado)

    if num_noticias == 1:
        st.subheader("1 notícia encontrada")
    else:
        st.subheader(f"{num_noticias} notícias encontradas")
        
    st.write("")
    st.write("")
    st.write("")
    st.write("")
    
    if not df_filtrado.empty:

        # Garanta que 'Data_Convertida' é do tipo datetime
        df_filtrado['Data_Convertida'] = pd.to_datetime(df_filtrado['Data_Convertida'], errors='coerce')

        # Ordene o DataFrame pela coluna de data
        df_filtrado_sorted = df_filtrado.sort_values(by='Data_Convertida')

        # Cria figura
        fig, ax = plt.subplots(figsize=(6, 1.5), dpi=200)  

        fig.patch.set_alpha(0)  # fundo da figura transparente
        ax.set_facecolor('none')  # fundo dos eixos transparente
        


        # Desenha histograma com barras finas
        sns.histplot(
            data=df_filtrado_sorted,
            x='Data_Convertida',
            binwidth=pd.Timedelta(days=1),
            discrete=True,
            shrink=0.8,  # barras mais finas
            color="#007ad3",
            ax=ax,
            edgecolor=None
        )

        # Formata datas do eixo X
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
        ax.xaxis.set_major_locator(mdates.DayLocator())

        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

        plt.xticks(rotation=45, ha='right', fontsize=3.5)  # fonte das datas 
        plt.xlabel('')

        # Remove eixo Y
        ax.yaxis.set_visible(False)

        # Remove bordas
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Adiciona rótulos nas barras com fonte pequena
        bars = ax.containers[0]
        labels = [int(bar.get_height()) if bar.get_height() > 0 else '' for bar in bars]
        ax.bar_label(bars, labels=labels, padding=2, fontsize=3.5)  # fonte pequena

        plt.tight_layout()
        st.pyplot(plt.gcf())
        

    tabela = df_filtrado[["Palavra-chave", "Data da notícia", "Título da notícia", "Fonte", "Link"]].copy()

    # Prepara uma versão limpa só para exportação (sem mudar nomes nem transformar em HTML)
    tabela_exportar = df_filtrado[["Palavra-chave", "Data da notícia", "Título da notícia", "Fonte", "Link"]].copy()
    
    tabela = tabela.rename(columns={
        "Título da notícia": "Notícia",
        "Data da notícia": "Data",
        "Fonte": "Veículo"
    })

    # Torna a coluna 'Título' um link clicável
    tabela['Notícia'] = tabela.apply(
        lambda row: f'<a href="{row["Link"]}" target="_blank">{row["Notícia"]}</a>',
        axis=1
    )

    # Remove a coluna 'Link' (oculta)
    tabela = tabela.drop(columns=['Link'])

    # Define número de linhas por página
    linhas_por_pagina = 20
    total_linhas = len(tabela)
    total_paginas = math.ceil(total_linhas / linhas_por_pagina)


    # Seleciona página atual
    col1, col2 = st.columns([1,13])
    pagina_atual = col1.selectbox(
        "Página",
        options=list(range(1, total_paginas + 1)),
        index=0,  # index começa em 0, então página 1
    )
    
    if pagina_atual is None:
        pagina_atual = 1  # valor padrão


    # Calcula os índices da página
    inicio = (pagina_atual - 1) * linhas_por_pagina
    fim = inicio + linhas_por_pagina
    
    st.write("")
        
    # Exibir informações de paginação
    st.write(f"Mostrando {inicio + 1} a {min(fim, total_linhas)} de {total_linhas} resultados")

    # Fatiar tabela para exibir apenas a página atual
    tabela_paginada = tabela.iloc[inicio:fim]

    # Gera HTML da tabela
    html = tabela_paginada.to_html(escape=False, index=False)

    # Injetar CSS para estilização
    st.markdown(
        """
        <style>
        table {
            width: 100%;
            border-collapse: collapse;
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
        table th:nth-child(1), table td:nth-child(1) { min-width: 320px; }
        table th:nth-child(2), table td:nth-child(2) { min-width: 100px; }
        table th:nth-child(3), table td:nth-child(3) { min-width: 350px; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Exibir a tabela paginada
    st.markdown(html, unsafe_allow_html=True)

    st.write("")
    
    
    # Renomeia para as colunas desejadas no Excel
    tabela_exportar = tabela_exportar.rename(columns={
        "Título da notícia": "Notícia",
        "Data da notícia": "Data",
        "Fonte": "Veículo"
    })
    
    # Define as colunas a exportar
    colunas_exportar = ['Palavra-chave', 'Data', 'Notícia', 'Veículo','Link',]
    tabela_exportar = tabela_exportar[colunas_exportar]

    # Cria buffer Excel
    output = io.BytesIO()
    tabela_exportar.to_excel(output, index=False)
    output.seek(0)

    data_de_hoje = hoje.strftime("%d/%m/%Y")

    # Botão único para exportar e baixar
    st.download_button(
        label="Exportar Excel",
        data=output,
        file_name=f"tabela_de_noticias - {data_de_hoje}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )