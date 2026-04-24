import streamlit as st
from funcoes_auxiliares import conectar_mongo_portal_ispn
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import datetime
import time


# ---------------------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------------------

st.set_page_config(page_title="Administração", layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')
st.header("Administração")
st.write("")

db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]
colaboradores = db["pessoas"]


# ---------------------------------------------------------------------------------
# CONTADOR DE ACESSOS À PÁGINA
# ---------------------------------------------------------------------------------


PAGINA_ID = "pagina_administracao"
nome_pagina = "Administração"

hoje = datetime.datetime.now().strftime("%d/%m/%Y")

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


# Coleta o único documento da coleção
doc = estatistica.find_one({}, {"_id": 0})

# ---------------------------------------------------------------------------------
# ABAS
# ---------------------------------------------------------------------------------

aba_visitas, aba_banco, aba_impersonar = st.tabs(["Visitações", "Banco de Dados", "Impersonar Usuário"])


# ---------------------------------------------------------------------------------
# ABA 1 — BANCO DE DADOS
# ---------------------------------------------------------------------------------
with aba_banco:

    st.write('')
    st.markdown("##### Uso do Banco de Dados")

    col1, col2, col3 = st.columns(3)

    # Obtém estatísticas do banco
    stats = db.command("dbStats")

    # Extrai o tamanho total usado (em MB)
    usado_mb = stats.get("storageSize", 0) / (1024 * 1024)
    capacidade_total_mb = 500
    porcentagem_usada = (usado_mb / capacidade_total_mb) * 100

    if porcentagem_usada <= 50:
        cor = "green"
    elif porcentagem_usada <= 75:
        cor = "yellow"
    else:
        cor = "red"

    # Velocímetro
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(usado_mb, 1),
        number={'suffix': " MB", "font": {"size": 36}, "valueformat": ".1f"},
        gauge={
            'axis': {'range': [0, capacidade_total_mb]},
            'bar': {'color': cor},
            'steps': [
                {'range': [0, capacidade_total_mb*0.5], 'color': 'rgba(0,255,0,0.2)'},
                {'range': [capacidade_total_mb*0.5, capacidade_total_mb*0.75], 'color': 'rgba(255,255,0,0.2)'},
                {'range': [capacidade_total_mb*0.75, capacidade_total_mb], 'color': 'rgba(255,0,0,0.2)'},
            ],
            'threshold': {'line': {'color': cor, 'width': 6}, 'value': usado_mb}
        }
    ))


    fig_gauge.update_layout(
        height=400,
        margin=dict(l=30, r=30, t=60, b=30),
        title="Limite do plano gratuito 500 MB"
    )

    col1.plotly_chart(fig_gauge)



# ---------------------------------------------------------------------------------
# ABA 2 — VISITAÇÕES
# ---------------------------------------------------------------------------------
with aba_visitas:

    # -----------------------------
    # Transformar estatísticas em dataframe (páginas)
    # -----------------------------
    registros = []

    for pagina, lista in doc.items():

        # Ignorar campo global total_sessoes
        if pagina == "total_sessoes":
            continue

        # Apenas listas que representam páginas
        if isinstance(lista, list):
            for item in lista:
                registros.append({
                    "pagina": pagina,
                    "data": item["data"],
                    "acessos": item.get("numero_de_acessos", 0)
                })

    df = pd.DataFrame(registros)

    # Converter datas
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")

    # ------------------------------------------
    # FILTRO DE PERÍODO
    # ------------------------------------------
    filtro_periodo = st.selectbox(
        "Período",
        ["Últimos 30 dias", "Últimos 12 meses", "Todo o período"],
        width=200
    )

    # Garante que a comparação seja só por data (sem horário)
    hoje = pd.Timestamp.today().normalize()

    if filtro_periodo == "Últimos 30 dias":
        data_inicio = hoje - pd.Timedelta(days=30)
    elif filtro_periodo == "Últimos 12 meses":
        data_inicio = hoje - pd.DateOffset(months=12)
    else:
        data_inicio = None
        
    if data_inicio is not None:
        df = df[df["data"] >= data_inicio]

    # ------------------------------------------
    # Sessões por dia
    # ------------------------------------------
    df_sessoes = pd.DataFrame(doc["total_sessoes"]).copy()
    df_sessoes["data"] = pd.to_datetime(df_sessoes["data"], format="%d/%m/%Y")
    
    if data_inicio is not None:
        df_sessoes = df_sessoes[df_sessoes["data"] >= data_inicio]

    sessoes_por_dia = (
        df_sessoes
        .groupby("data")["numero_de_sessoes"]
        .sum()
        .reset_index()
        .rename(columns={"numero_de_sessoes": "sessoes"})
    )

    # ------------------------------------------
    # Visualizações de páginas por dia
    # ------------------------------------------
    visitas_por_dia = (
        df
        .groupby("data")["acessos"]
        .sum()
        .reset_index()
        .rename(columns={"acessos": "visualizacoes"})
    )

    # ------------------------------------------
    # Unir os dois por data
    # ------------------------------------------
    df_dia = pd.merge(
        sessoes_por_dia,
        visitas_por_dia,
        on="data",
        how="outer"
    ).fillna(0)

    fig = go.Figure()

    fig.add_bar(
        x=df_dia["data"],
        y=df_dia["sessoes"],
        name="Total de Sessões",
        text=df_dia["sessoes"],
        textposition="inside"
    )

    fig.add_bar(
        x=df_dia["data"],
        y=df_dia["visualizacoes"],
        name="Visualizações de Páginas",
        text=df_dia["visualizacoes"],
        textposition="inside"
    )

    fig.update_layout(
        title="Acessos e Visualizações por Dia",
        barmode="group",
        xaxis_title=None,
        legend_title=None,
        height=450
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=df_dia["data"],
        ticktext=[d.strftime("%d/%m/%Y") for d in df_dia["data"]],
        tickangle=-45
    )

    st.plotly_chart(fig, width="stretch")

    # ------------------------------------------
    # GRÁFICO 2 — Visitas por página
    # ------------------------------------------
    visitas_por_pagina = df.groupby("pagina")["acessos"].sum().reset_index()
    visitas_por_pagina = visitas_por_pagina.sort_values("acessos", ascending=True)

    fig_paginas = px.bar(
        visitas_por_pagina,
        x="acessos",
        y="pagina",
        orientation="h",
        title="Total de Visitas por Página",
        text="acessos"
    )

    fig_paginas.update_traces(
        textposition="outside",
        texttemplate="%{x}"
    )

    fig_paginas.update_layout(xaxis_title=None, yaxis_title=None)

    st.plotly_chart(fig_paginas)




# ---------------------------------------------------------------------------------
# ABA 3 - IMPERSONAR USUÁRIOS, SÓ PARA ADMIN
# ---------------------------------------------------------------------------------

if "admin" in st.session_state.tipo_usuario:

    with aba_impersonar:

        st.markdown("##### Impersonar usuário")
        st.write('')

        email_impersonar = st.text_input("E-mail do usuário que deseja impersonar", width=400)

        if st.button("Impersonar usuário", icon=":material/skull:"):
            usuario = colaboradores.find_one({
                "e_mail": {"$regex": f"^{email_impersonar.strip()}$", "$options": "i"}
            })

            if usuario:
                # reconstrução completa da sessão (mesmo padrão do login)
                st.session_state["logged_in"] = True

                # captura string do banco (nome correto do campo)
                tipo_usuario_raw = usuario.get("tipo de usuário", "")


                # converte string "a, b, c" → lista ["a", "b", "c"]
                tipo_usuario = [
                    t.strip().lower()
                    for t in tipo_usuario_raw.split(",")
                    if t.strip()
                ]

                st.session_state["tipo_usuario"] = tipo_usuario

                st.session_state["nome"] = usuario.get("nome_completo")
                st.session_state["id_usuario"] = usuario.get("_id")

                # inclusão do CPF conforme padrão do banco
                st.session_state["cpf"] = usuario.get("CPF")

                st.session_state["email"] = usuario.get("e_mail", "")
                st.session_state["projetos"] = usuario.get("projetos", [])

                # reseta navegação para fluxo correto
                st.session_state["pagina_atual"] = None
                st.session_state["projeto_atual"] = None

                st.success(f"Acessando como {st.session_state['nome']}")

                st.balloons()
               
                time.sleep(3)
                st.rerun()
            else:
                st.error("Usuário não encontrado.")


