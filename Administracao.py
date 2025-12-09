import streamlit as st
from funcoes_auxiliares import conectar_mongo_portal_ispn
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


# ---------------------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------------------

st.set_page_config(page_title="Administração", layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')
st.header("Administração")
st.write("")

db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]

# Coleta o único documento da coleção
doc = estatistica.find_one({}, {"_id": 0})

# ---------------------------------------------------------------------------------
# ABAS
# ---------------------------------------------------------------------------------

aba_banco, aba_visitas = st.tabs(["Banco de Dados", "Visitações"])


# ---------------------------------------------------------------------------------
# ABA 1 — BANCO DE DADOS
# ---------------------------------------------------------------------------------
with aba_banco:

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
        title="Capacidade do Banco de Dados (MB)"
    )

    col1.plotly_chart(fig_gauge)



# ---------------------------------------------------------------------------------
# ABA 2 — VISITAÇÕES
# ---------------------------------------------------------------------------------
with aba_visitas:

    # -----------------------------
    # Transformar estatísticas em dataframe
    # -----------------------------
    registros = []

    for pagina, lista in doc.items():
        if isinstance(lista, list):
            for item in lista:
                registros.append({
                    "pagina": pagina,
                    "data": item["data"],
                    "acessos": item["numero_de_acessos"]
                })

    df = pd.DataFrame(registros)

    # Converter para datetime
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")

    # Remover hora e deixar apenas a data
    df["data"] = df["data"].dt.date

    # ------------------------------------------
    # GRÁFICO 1 — Barras verticais (visitas por dia)
    # ------------------------------------------
    visitas_por_dia = df.groupby("data")["acessos"].sum().reset_index()

    fig_dias = px.bar(
        visitas_por_dia,
        x="data",
        y="acessos",
        title="Visitações por Dia",
        labels={"acessos": "Número de Acessos"},
    )

    # Forçar que só apareça 1 tick por barra
    fig_dias.update_xaxes(
        tickmode="array",
        tickvals=visitas_por_dia["data"],
        ticktext=[d.strftime("%d/%m/%Y") for d in visitas_por_dia["data"]],
        tickangle=-45  # Inclinar as datas
    )
    
    # Remover labels dos eixos
    fig_dias.update_layout(
        xaxis_title=None,
    )

    st.plotly_chart(fig_dias, use_container_width=True)

    # ------------------------------------------
    # GRÁFICO 2 — Barras horizontais (visitas por página)
    # ------------------------------------------

    visitas_por_pagina = df.groupby("pagina")["acessos"].sum().reset_index()
    visitas_por_pagina = visitas_por_pagina.sort_values("acessos", ascending=True)

    fig_paginas = px.bar(
        visitas_por_pagina,
        x="acessos",
        y="pagina",
        orientation="h",
        title="Total de Visitas por Página",
    )

    # Remover labels dos eixos
    fig_paginas.update_layout(
        xaxis_title=None,
        yaxis_title=None
    )

    st.plotly_chart(fig_paginas, use_container_width=True)