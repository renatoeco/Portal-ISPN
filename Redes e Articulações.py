import streamlit as st


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')
st.header("Redes e Articulações")
st.write('')



# TESTE DE CAIXA DE ANOTAÇÕES COM LIMITE DE CARACTERES

MAX_CARACTERES = 2000

texto = st.text_area("Digite seu texto (máx. 2000 caracteres):", height=400)
num_caracteres = len(texto)
caracteres_restantes = MAX_CARACTERES - num_caracteres

if caracteres_restantes < 0:
    st.error(f"Você ultrapassou o limite em {-caracteres_restantes} caracteres!")
else:
    st.write(f"{num_caracteres} / {MAX_CARACTERES}")
    st.write(f"*Clique fora da caixa de texto para atualizar o contador")