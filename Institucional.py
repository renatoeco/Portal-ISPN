import streamlit as st
from datetime import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn


###########################################################################################################
# Conectando ao MongoDB
###########################################################################################################


db = conectar_mongo_portal_ispn()  # Isso vai usar o cache automaticamente
estatistica = db["estatistica"]
colaboradores = db["colaboradores"]
institucional = db["institucional"]


###########################################################################################################
# Contador de acessos
###########################################################################################################


# Nome da página como chave
nome_pagina = "Institucional"
timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# Constrói o campo dinâmico para adicionar o timestamp
campo_timestamp = f"{nome_pagina}.Visitas"

# Atualiza ou cria o documento, acumulando os timestamps
estatistica.update_one(
    {},
    {"$push": {campo_timestamp: timestamp}},
    upsert=True
)


###########################################################################################################
# FUNÇÕES 
###########################################################################################################


@st.dialog("Editar Frase de Força")
def editar_frase_dialog():
    frase_doc = institucional.find_one({"frase_forca": {"$exists": True}})
    frase_atual = frase_doc["frase_forca"] if frase_doc else ""
    nova_frase = st.text_area("Nova frase de força", value=frase_atual)
    if st.button("Salvar"):
        if frase_doc:
            institucional.update_one({"_id": frase_doc["_id"]}, {"$set": {"frase_forca": nova_frase}})
        else:
            institucional.insert_one({"frase_forca": nova_frase})
        st.success("Frase atualizada com sucesso!")
        st.rerun()

@st.dialog("Editar Missão")
def editar_missao_dialog():
    missao_doc = institucional.find_one({"missao": {"$exists": True}})
    missao_atual = missao_doc["missao"] if missao_doc else ""
    nova_missao = st.text_area("Nova missão", value=missao_atual)
    if st.button("Salvar"):
        if missao_doc:
            institucional.update_one({"_id": missao_doc["_id"]}, {"$set": {"missao": nova_missao}})
        else:
            institucional.insert_one({"missao": nova_missao})
        st.success("Missão atualizada com sucesso!")
        st.rerun()


###########################################################################################################
# MAIN
###########################################################################################################


st.set_page_config(layout="wide")

# st.logo("/home/renato/Projetos_Python/ISPN_HUB/app_ispn_hub/images/logo_ISPN_horizontal_ass.png")

st.markdown(
    "<div style='display: flex; justify-content: center;'>"
    "<img src='https://ispn.org.br/site/wp-content/uploads/2021/04/logo_ISPN_2021.png' alt='ISPN Logo'>"
    "</div>",
    unsafe_allow_html=True
)


frase_doc = institucional.find_one({"frase_forca": {"$exists": True}})
frase_atual = frase_doc["frase_forca"] if frase_doc else "Frase não cadastrada ainda."
missao_doc = institucional.find_one({"missao": {"$exists": True}})
missao_atual = missao_doc["missao"] if missao_doc else "Missão não cadastrada ainda."


st.write('')
st.write('')
st.write('')
st.write('')


col_frase, col_btn = st.columns([10, 1])
with col_frase:
    st.markdown(f"<h3 style='text-align: center;'>{frase_atual}</h3>", unsafe_allow_html=True)
if st.session_state.get("tipo_usuario") == "adm":
    col_btn.button("Editar", icon=":material/edit:", key="editar_frase", on_click=editar_frase_dialog)


#st.markdown("<h3 style='text-align: center;'>Fortalecer meios de vida sustentáveis com protagonismo comunitário.</h3>", unsafe_allow_html=True)


st.write('')
st.write('')


col_missao, col_btn2 = st.columns([10, 1])
with col_missao:
    st.subheader("Missão")
    st.write(missao_atual)
if st.session_state.get("tipo_usuario") == "adm":
    
    col_btn2.button("Editar", icon=":material/edit:", key="editar_missao", on_click=editar_missao_dialog)
    

#st.subheader('Missão')
#st.write('Contribuir para viabilizar a equidade social e o equilíbrio ambiental, com o fortalecimento de meios de vida sustentáveis e estratégias de adaptação às mudanças climáticas.')

st.write('')
st.write('')
st.subheader('Visão de futuro para 2034')
st.write('Consolidar-se como um agente de transformação da sociedade fortalecendo os modos de vida sustentáveis, a participação social nas políticas públicas e a integração de práticas e saberes que promovem a justiça climática.')

st.write('')
st.write('')
st.subheader('Valores do ISPN')

st.write('')

col1, col2, col3, col4, col5 = st.columns(5)

cont1 = col1.container(border=True)
cont1.write("""
**1 - Relações de confiança** \n
Trabalhamos na construção de relações de respeito, confiança, honestidade e transparência, primando pelo diálogo e pela realização conjunta de ações para o alcance das transformações socioambientais.
""")

cont2 = col2.container(border=True)
cont2.write("""           
**2 - Compromisso socioambiental** \n
Agimos com responsabilidade para equilibrar interesses socioeconômicos e ambientais em favor do bem-estar das pessoas e comunidades.
""")

cont3 = col3.container(border=True)
cont3.write("""**3 - Reconhecimento de saberes** \n
Valorizamos processos de aprendizagem que inspirem e multipliquem a diversidade de saberes e práticas para gerar transformações com impactos socioambientais justos e inclusivos.
""")

cont4 = col4.container(border=True)
cont4.write("""**4 - Valorização da diversidade** \n
Primamos pelas relações baseadas no respeito e na inclusão de todas as pessoas, reconhecendo e valorizando a pluralidade e o protagonismo de cada indivíduo e de seus coletivos.
""")

cont5 = col5.container(border=True)
cont5.write("""**5 - Cooperação** \n
Atuamos de maneira colaborativa e solidária no trabalho em equipe e entre organizações, parceiros e comunidades na busca de soluções para os desafios socioambientais contemporâneos.
""")
