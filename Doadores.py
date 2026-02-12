import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import plotly.express as px
from plotly.colors import diverging
import plotly.graph_objects as go
from plotly.colors import diverging
import plotly.graph_objects as go
import time
from bson import ObjectId
from funcoes_auxiliares import conectar_mongo_portal_ispn, ajustar_altura_dataframe


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas

df_doadores = pd.DataFrame(list(db["doadores"].find()))
doadores_dict = {str(d["_id"]): d["nome_doador"] for d in db["doadores"].find()}
df_programas = pd.DataFrame(list(db["programas_areas"].find()))
df = pd.DataFrame(list(db["projetos_ispn"].find()))
# Remover projetos sem doador válido
df = df[df["doador"].notna() & (df["doador"] != "")].copy()


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "pagina_doadores"
nome_pagina = "Doadores"

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


######################################################################################################
# FUNÇÕES
######################################################################################################


@st.dialog("Gerenciar doadores", width="large")
def gerenciar_doadores():

    TIPOS_DOADOR = [
        "Cooperação internacional",
        "Empresa",
        "Filantropia privada",
        "Governo"
    ]

    tab_adicionar, tab_editar = st.tabs([":material/add: Adicionar", ":material/edit: Editar"])
    
    # =========================
    # ABA ADICIONAR
    # =========================
    with tab_adicionar:
        with st.form("form_adicionar_doador", border=False):
            nome_novo = st.text_input("Nome do doador")
            sigla_nova = st.text_input("Sigla")
            tipo_novo = st.selectbox("Tipo de doador", TIPOS_DOADOR)

            submitted = st.form_submit_button("Adicionar", icon=":material/add:", type="primary")

            if submitted:
                nome_limpo = nome_novo.strip()
                if nome_limpo:
                    doador_existente = db["doadores"].find_one({
                        "nome_doador": {"$regex": f"^{nome_limpo}$", "$options": "i"}
                    })

                    if doador_existente:
                        st.warning(f"Já existe um doador com o nome '{doador_existente['nome_doador']}'.")
                    else:
                        db["doadores"].insert_one({
                            "nome_doador": nome_limpo,
                            "sigla_doador": sigla_nova.strip(),
                            "tipo_doador": tipo_novo
                        })
                        st.success(f"Doador '{nome_limpo}' adicionado com sucesso!")
                        time.sleep(2)
                        st.rerun()
                else:
                    st.warning("O nome do doador é obrigatório.")

    # =========================
    # ABA EDITAR
    # =========================
    with tab_editar:

        opcoes = [""] + list(doadores_dict.keys())

        doador_id = st.selectbox(
            "Selecione o doador para editar",
            opcoes,
            format_func=lambda x: doadores_dict.get(x, ""),
            key="editar_doador_select"
        )

        if doador_id != "":

            doador = db["doadores"].find_one({"_id": ObjectId(doador_id)})

            with st.form("form_editar_doador"):

                novo_nome = st.text_input(
                    "Editar nome",
                    value=doador.get("nome_doador", "")
                )

                nova_sigla = st.text_input(
                    "Editar sigla",
                    value=doador.get("sigla_doador", "")
                )

                tipo_atual = doador.get("tipo_doador", TIPOS_DOADOR[0])

                novo_tipo = st.selectbox(
                    "Editar tipo de doador",
                    TIPOS_DOADOR,
                    index=TIPOS_DOADOR.index(tipo_atual) if tipo_atual in TIPOS_DOADOR else 0
                )

                submitted = st.form_submit_button("Salvar alterações", icon=":material/save:")

                if submitted:
                    db["doadores"].update_one(
                        {"_id": ObjectId(doador_id)},
                        {"$set": {
                            "nome_doador": novo_nome.strip(),
                            "sigla_doador": nova_sigla.strip(),
                            "tipo_doador": novo_tipo
                        }}
                    )
                    st.success("Doador atualizado com sucesso!")
                    time.sleep(2)
                    st.rerun()


######################################################################################################
# MAIN
######################################################################################################


st.header("Doadores")


# Conversão dos ids de Doador e Programa


# --- 1. Converter listas de documentos em DataFrames ---



# --- 2. Criar dicionários de mapeamento ---
# Criar mapas completos a partir da coleção doadores
doadores_docs = list(db["doadores"].find())

mapa_doador = {d["_id"]: d.get("nome_doador", "Sem nome") for d in doadores_docs}
mapa_tipo_doador = {d["_id"]: d.get("tipo_doador", "Não informado") for d in doadores_docs}
mapa_programa = {p["_id"]: p["nome_programa_area"] for p in db["programas_areas"].find()}

# --- 3. Aplicar os mapeamentos ao df ---
df["nome_doador"] = df["doador"].map(mapa_doador)

df["tipo_de_doador"] = df["doador"].map(mapa_tipo_doador)

df["nome_doador"] = df["nome_doador"].fillna("Doador não cadastrado")

df["tipo_de_doador"] = df["tipo_de_doador"].fillna("Não informado")

df["programa_nome"] = df["programa"].map(mapa_programa)

# Conversão e limpeza do valor
df["valor"] = (
    df["valor"]
    .astype(str)
    .str.replace(".", "", regex=False)   # Remove separadores de milhar
    .str.replace(",", ".", regex=False)  # Troca vírgula decimal por ponto
)
df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

# >>> Formatar Valor com base na moeda <<<
def formatar_valor(row):
    if pd.isna(row["valor"]):
        return ""
    simbolo = "R$" if row["moeda"] == "Reais" else "US$"
    return f"{simbolo} {row['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

df["Valor"] = df.apply(formatar_valor, axis=1)

tab1, tab2 = st.tabs(["Visão geral", "Doadores"])

with tab1:
    st.write("")

    # Converter datas de contrato
    df["Início"] = pd.to_datetime(df["data_inicio_contrato"], errors="coerce", format="%d/%m/%Y")
    df["Fim"] = pd.to_datetime(df["data_fim_contrato"], errors="coerce", format="%d/%m/%Y")

    # Pegar menor e maior anos
    anos_inicio = df["Início"].dropna().dt.year.astype(int)
    anos_fim = df["Fim"].dropna().dt.year.astype(int)

    if not anos_inicio.empty and not anos_fim.empty:
        menor_ano = min(anos_inicio.min(), anos_fim.min())
        maior_ano = max(anos_inicio.max(), anos_fim.max())

        # Faz um range contínuo
        anos_disponiveis = list(range(menor_ano, maior_ano + 1))
    else:
        anos_disponiveis = []

    # Selectboxes dinâmicos
    
    # col1, col2, col3 = st.columns(3)

    with st.container(horizontal=True):

        ano_inicio = st.selectbox("Projetos vigentes entre", anos_disponiveis, index=0, width=200)
        ano_fim = st.selectbox("e", anos_disponiveis, index=len(anos_disponiveis)-1, width=200)

    # Garantir que são inteiros
    ano_inicio = int(ano_inicio)
    ano_fim = int(ano_fim)

    # Selecionar projetos vigentes entre os anos escolhidos
    df_filtrado = df[
        (df["Início"].dt.year <= ano_fim) &   # começou antes ou durante o intervalo
        (df["Fim"].dt.year >= ano_inicio)     # terminou depois ou durante o intervalo
    ].copy()

    # agrupamento normal (cada moeda em uma linha)
    resumo = df_filtrado.groupby(
        ["nome_doador", "tipo_de_doador", "moeda"], as_index=False
    ).agg({
        "valor": "sum",
        "_id": "count"
    })

    # pivotar moedas para colunas
    pivot = resumo.pivot_table(
        index=["nome_doador", "tipo_de_doador"],
        columns="moeda",
        values=["valor", "_id"],
        aggfunc="sum",
        fill_value=0
    )

    # flatten dos MultiIndex
    pivot.columns = [f"{a}_{b}" for a, b in pivot.columns]
    pivot = pivot.reset_index()

    # garantir que colunas existem
    if "valor_Reais" not in pivot:
        pivot["valor_Reais"] = 0
    if "valor_Dólares" not in pivot:
        pivot["valor_Dólares"] = 0
    if "_id_Reais" not in pivot:
        pivot["_id_Reais"] = 0
    if "_id_Dólares" not in pivot:
        pivot["_id_Dólares"] = 0

    # criar colunas formatadas dinâmicas
    def fmt_valor(valor, moeda):
        simbolo = "R$" if moeda == "Reais" else "US$"
        return f"{simbolo} {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def formatar_valor_linha(row):
        partes = []
        if row["valor_Dólares"] > 0:
            partes.append(fmt_valor(row["valor_Dólares"], "Dólares"))
        if row["valor_Reais"] > 0:
            partes.append(fmt_valor(row["valor_Reais"], "Reais"))
        return " | ".join(partes)

    pivot["Valor_fmt"] = pivot.apply(formatar_valor_linha, axis=1)

    # total de projetos
    pivot["Número de projetos"] = pivot["_id_Dólares"] + pivot["_id_Reais"]
    pivot = pivot[pivot["Número de projetos"] > 0]

    # renomear colunas para exibir
    resumo_final = pivot.rename(columns={
        "nome_doador": "Doador",
        "tipo_de_doador": "Tipo de Doador",
        "Valor_fmt": "Valor"
    })
    
    col1, col2 = st.columns([1,2])

    # Pega todos os doadores que têm projetos no período filtrado
    doadores_filtrados = sorted(df_filtrado["nome_doador"].dropna().unique())

    st.write('')

    # Ajusta singular/plural
    texto = "doador com projeto(s)" if len(doadores_filtrados) == 1 else "doadores com projeto(s)"
    col1.subheader(f'{len(doadores_filtrados)} {texto}')



    resumo_final = resumo_final[["Doador", "Tipo de Doador", "Número de projetos", "Valor"]]

    # exibir na tela:

    ajustar_altura_dataframe(resumo_final, 1)

    # st.dataframe(
    #     resumo_final[["Doador", "Tipo de Doador", "Número de projetos", "Valor"]],
    #     hide_index=True
    # )
    
    st.write("")
    st.write("")
    st.write("")
    
    # --- 1. Número total de projetos (Reais + Dólares) ---
    # Agrupa de novo somando os números de projetos por doador (independente da moeda)
    # resumo_total = (
    #     resumo_final.groupby("Doador", as_index=False)["Número de projetos"]
    #     .sum()
    # )

    
    # -----------------------------
    # Reais
    # -----------------------------
    df_reais = resumo[resumo["moeda"] == "Reais"].groupby("nome_doador", as_index=False).agg(
    valor=("valor", "sum"),
    num_proj=("_id", "sum")
)

    # Ordena por valor decrescente
    df_reais = df_reais.sort_values(by="valor", ascending=False).reset_index(drop=True)

    df_reais["Valor"] = df_reais["valor"].apply(
        lambda v: f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    # Paleta para consistência
    cor_proj = "#1f77b4"   
    cor_valor = "#19d8e6"  

    fig_reais = go.Figure()

    # Barras de número de projetos
    fig_reais.add_trace(go.Bar(
        x=df_reais["nome_doador"],
        y=df_reais["num_proj"],
        name="Nº de Projetos",
        marker_color=cor_proj,
        yaxis='y1',
        width=0.35,
        offset=-0.2,
        hovertemplate='Doador: %{x}<br>Nº Projetos: %{y}<extra></extra>'
    ))

    # Barras de valor total
    fig_reais.add_trace(go.Bar(
        x=df_reais["nome_doador"],
        y=df_reais["valor"],
        name="Valor Total de Apoio",
        marker_color=cor_valor,
        yaxis='y2',
        width=0.35,
        offset=0.2,
        hovertext=df_reais["Valor"],
        hovertemplate='Doador: %{x}<br>Valor Total: %{hovertext}<extra></extra>'
    ))

    fig_reais.update_layout(
        title="Número de Projetos e Valor de Apoio por Doador (R$)",
        yaxis=dict(
            title="Nº de Projetos",
            side='left',
            showgrid=False,       # mostra apenas linhas horizontais
            gridcolor='lightgray'
        ),
        yaxis2=dict(
            title="Valor Total (R$)",
            overlaying='y',
            side='right',
            showgrid=True
        ),
        xaxis=dict(
            showgrid=False      # remove linhas verticais
        ),
        barmode='group',
        legend=dict(x=0.5, y=1.1, orientation='h', xanchor='center')
    )

    st.plotly_chart(fig_reais)

    # -----------------------------
    # Dólares
    # -----------------------------
    df_dolares = resumo[resumo["moeda"] == "Dólares"].groupby("nome_doador", as_index=False).agg(
        valor=("valor", "sum"),
        num_proj=("_id", "sum")
    )

    # Ordena por valor decrescente
    df_dolares = df_dolares.sort_values(by="valor", ascending=False).reset_index(drop=True)

    df_dolares["Valor"] = df_dolares["valor"].apply(
        lambda v: f"US$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    fig_dolares = go.Figure()

    fig_dolares.add_trace(go.Bar(
        x=df_dolares["nome_doador"],
        y=df_dolares["num_proj"],
        name="Nº de Projetos",
        marker_color=cor_proj,
        yaxis='y1',
        width=0.35,
        offset=-0.2,
        hovertemplate='Doador: %{x}<br>Nº Projetos: %{y}<extra></extra>'
    ))

    fig_dolares.add_trace(go.Bar(
        x=df_dolares["nome_doador"],
        y=df_dolares["valor"],
        name="Valor Total de Apoio",
        marker_color=cor_valor,
        yaxis='y2',
        width=0.35,
        offset=0.2,
        hovertext=df_dolares["Valor"],
        hovertemplate='Doador: %{x}<br>Valor Total: %{hovertext}<extra></extra>'
    ))

    fig_dolares.update_layout(
        title="Número de Projetos e Valor de Apoio por Doador (US$)",
        yaxis=dict(
            title="Nº de Projetos",
            side='left',
            showgrid=False,
            gridcolor='lightgray'
        ),
        yaxis2=dict(
            title="Valor Total (US$)",
            overlaying='y',
            side='right',
            showgrid=True
        ),
        xaxis=dict(
            showgrid=False
        ),
        barmode='group',
        legend=dict(x=0.5, y=1.1, orientation='h', xanchor='center')
    )

    st.plotly_chart(fig_dolares)


    st.write("")
    st.write("")
    st.write("")


with tab2:
    st.write('')
    
    if set(st.session_state.tipo_usuario) & {"admin", "gestao_projetos_doadores"}:
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 3, 2])

        col5.write('')
        col5.button("Gerenciar doadores", on_click=gerenciar_doadores, width=300, icon=":material/wallet:")

    df = df.dropna(subset=["valor"])
    df["doador"] = df["doador"].fillna("Desconhecido")
    df["data_inicio_contrato"] = df["data_inicio_contrato"].fillna("")
    df["data_fim_contrato"] = df["data_fim_contrato"].fillna("")

    st.write("")
    

    todos_doadores = sorted(doadores_dict.values())
    
    # Adiciona opção vazia no topo
    todos_doadores_opcoes = [""] + todos_doadores

    # col1, col2, col3, col4 = st.columns([2, 1, 1, 3])

    doador_selecionado = col1.selectbox("Selecione o doador", todos_doadores_opcoes)
    
    # Só processa se um doador foi selecionado
    if doador_selecionado:

        # Filtrar apenas projetos do doador
        df_doador = df[df["nome_doador"] == doador_selecionado].copy()

        # Converte datas (não quebra se estiver vazio)
        df_doador["Início"] = pd.to_datetime(df_doador["Início"], dayfirst=True, errors="coerce")
        df_doador["Fim"] = pd.to_datetime(df_doador["Fim"], dayfirst=True, errors="coerce")

        if df_doador.empty:
            # DataFrame vazio com as colunas que você quer mostrar
            df_vazio = pd.DataFrame(columns=["Projeto", "Valor", "Início", "Fim", "Situação"])
            st.dataframe(df_vazio, hide_index=True, use_container_width=True)

            # Gráfico vazio — você pode criar um Altair sem dados
            chart_vazio = alt.Chart(pd.DataFrame({"x": [], "y": []})).mark_bar()
            st.altair_chart(chart_vazio, use_container_width=True)

            # Timeline vazia
            fig = px.timeline(pd.DataFrame(columns=["Início", "Fim", "Projeto", "Situação"]),
                            x_start="Início", x_end="Fim", y="Projeto", color="Situação")
            st.plotly_chart(fig, use_container_width=True)

        else:
            # Converter datas
            def parse_data(data_str):
                try:
                    return pd.to_datetime(data_str, format="%d/%m/%Y")
                except:
                    return pd.NaT

            df_doador["Início"] = df_doador["data_inicio_contrato"].apply(parse_data)
            df_doador["Fim"] = df_doador["data_fim_contrato"].apply(parse_data)

            # --- FILTRO DE PROJETOS VIGENTES (igual aba 1) ---
            anos_inicio = df_doador["Início"].dropna().dt.year.astype(int)
            anos_fim = df_doador["Fim"].dropna().dt.year.astype(int)
            anos_disponiveis = sorted(set(anos_inicio) | set(anos_fim))
            
            if not anos_inicio.empty and not anos_fim.empty:
                menor_ano = min(anos_inicio.min(), anos_fim.min())
                maior_ano = max(anos_inicio.max(), anos_fim.max())
                anos_disponiveis = list(range(menor_ano, maior_ano + 1))
            else:
                anos_disponiveis = []

            if anos_disponiveis:
                ano_inicio = col2.selectbox("Projetos vigentes entre", anos_disponiveis, index=0)
                ano_fim = col3.selectbox("e", anos_disponiveis, index=len(anos_disponiveis)-1)
                ano_inicio, ano_fim = int(ano_inicio), int(ano_fim)

                # Filtrar projetos vigentes
                df_doador = df_doador[
                    (df_doador["Início"].dt.year <= ano_fim) &
                    (df_doador["Fim"].dt.year >= ano_inicio)
                ].copy()

            df_doador["Projeto"] = df_doador["sigla"].fillna("Sem nome")
            df_doador["Situação"] = df_doador["status"].fillna("Desconhecido")
        
            moeda = df_doador['moeda'].iloc[0]  # se todos iguais, pega o 1º
            simbolo = "R$" if moeda == "Reais" else "US$"
            # Agrupa por moeda e soma os valores
            somas_moeda = df_doador.groupby('moeda')['valor'].sum()

            # Formata cada valor com símbolo e separa por " | "
            valores_formatados = []
            for moeda, valor in somas_moeda.items():
                simbolo = "R$" if moeda == "Reais" else "US$"
                valor_fmt = f"{simbolo} {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                valores_formatados.append(valor_fmt)

            # Junta os valores separados por " | "
            valor_total_formatado = " | ".join(valores_formatados)

            st.write('')
            st.metric('Valor total dos apoios', valor_total_formatado)

            st.write('')
            st.write(f'**{len(df_doador)} Projetos**')

            #st.metric("Número de projetos do doador", num_projetos_doador)

            # E na exibição do dataframe:
            st.dataframe(
                df_doador[["Projeto", "Valor", "data_inicio_contrato", "data_fim_contrato", "Situação"]]
                .rename(columns={
                    "data_inicio_contrato": "Início",
                    "data_fim_contrato": "Fim"
                })
                .sort_values(by="Início"),
                hide_index=True
            )


            st.write('')
            st.write('**Cronograma de projetos**')

            # Ordena por data de início para exibir em ordem cronológica
            df_doador_sorted = df_doador.sort_values(by="Início", ascending=False)

            # Altura proporcional ao número de projetos
            num_projetos = df_doador_sorted["Projeto"].nunique()
            altura_total = max(300, num_projetos * 50)

            fig = px.timeline(
                df_doador_sorted,
                x_start='Início',
                x_end='Fim',
                y='Projeto',
                color='Situação',
                hover_data=['Valor'],   # ← formatada
                height=altura_total
            )


            fig.update_yaxes(
                categoryorder='array',
                categoryarray=df_doador_sorted["Projeto"].tolist()
            )

            fig.update_xaxes(
                dtick="M12",           # Mostrar a cada 12 meses
                tickformat="%Y",       # Exibir apenas o ano (2022, 2023 etc.)
                tickangle=-50
            )

            fig.update_layout(
                margin=dict(l=100, r=50, t=50, b=50),
                yaxis_title=""
            )

            # Linha pontilhada preta no dia de hoje
            fig.add_vline(
                x=datetime.today(),
                line_width=2,
                line_dash="dot",
                line_color="black",
            )

            st.plotly_chart(fig)