import streamlit as st
from funcoes_auxiliares import conectar_mongo_portal_ispn
import plotly.graph_objects as go



# ---------------------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------------------


st.set_page_config(page_title="Administração", layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')
st.header("Administração")
st.write("")

db = conectar_mongo_portal_ispn()





# ---------------------------------------------------------------------------------
# GRÁFICO DE VELOCÍMETRO - USO DO MONGODB
# ---------------------------------------------------------------------------------

st.write('')
st.write('')

col1, col2, col3 = st.columns(3)


# Obtém estatísticas do banco de dados inteiro
stats = db.command("dbStats")

# Extrai o tamanho total usado (em MB)
usado_mb = stats.get("storageSize", 0) / (1024 * 1024)
capacidade_total_mb = 500  # defina o limite da capacidade total estimada
porcentagem_usada = (usado_mb / capacidade_total_mb) * 100

    # Cores de acordo com a porcentagem usada
if porcentagem_usada <= 50:
    cor = "green"
elif porcentagem_usada <= 75:
    cor = "yellow"
else:
    cor = "red"

# Velocímetro em MB (com 1 casa decimal, sem legenda)
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=round(usado_mb, 1),
    number={'suffix': " MB", "font": {"size": 36}, "valueformat": ".1f"},
    gauge={
        'axis': {'range': [0, capacidade_total_mb], 'tickwidth': 1, 'tickcolor': "gray"},
        'bar': {'color': cor},
        'bgcolor': "white",
        'borderwidth': 2,
        'bordercolor': "gray",
        'steps': [
            {'range': [0, capacidade_total_mb * 0.5], 'color': 'rgba(0, 255, 0, 0.2)'},
            {'range': [capacidade_total_mb * 0.5, capacidade_total_mb * 0.75], 'color': 'rgba(255, 255, 0, 0.2)'},
            {'range': [capacidade_total_mb * 0.75, capacidade_total_mb], 'color': 'rgba(255, 0, 0, 0.2)'},
        ],
        'threshold': {
            'line': {'color': cor, 'width': 6},
            'thickness': 0.75,
            'value': usado_mb
        }
    }
))

fig_gauge.update_layout(
    height=400,
    margin=dict(l=30, r=30, t=60, b=30),
    title="Capacidade do Banco de Dados (MB)"
)

col1.plotly_chart(fig_gauge, use_container_width='stretch')