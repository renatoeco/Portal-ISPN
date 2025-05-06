import streamlit as st
import time
from datetime import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn  # Função personalizada para conectar ao MongoDB


###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
###########################################################################################################

# Conecta-se ao banco de dados MongoDB (com cache automático)
db = conectar_mongo_portal_ispn()

# Define as coleções utilizadas
estatistica = db["estatistica"]
colaboradores = db["colaboradores"]
institucional = db["institucional"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################

# Define o nome da página atual
nome_pagina = "Institucional"
# Gera o timestamp atual no formato "dia/mês/ano hora:minuto:segundo"
timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
# Cria o campo dinâmico para armazenar visitas
campo_timestamp = f"{nome_pagina}.Visitas"

# Atualiza ou cria o documento de estatísticas, acumulando o timestamp da visita
estatistica.update_one(
    {},
    {"$push": {campo_timestamp: timestamp}},
    upsert=True  # Cria o documento se ele ainda não existir
)


###########################################################################################################
# FUNÇÕES
###########################################################################################################

# Diálogo para editar a frase de força institucional
@st.dialog("Editar Frase de Força")
def editar_frase_dialog():
    # Recupera a frase atual do banco, se existir
    frase_doc = institucional.find_one({"frase_forca": {"$exists": True}})
    frase_atual = frase_doc["frase_forca"] if frase_doc else ""
    
    # Campo para editar a frase
    nova_frase = st.text_area("Nova frase de força", value=frase_atual)
    
    # Botão para salvar a nova frase
    if st.button("Salvar"):
        if frase_doc:
            # Atualiza documento existente
            institucional.update_one({"_id": frase_doc["_id"]}, {"$set": {"frase_forca": nova_frase}})
        else:
            # Cria novo documento se ainda não existir
            institucional.insert_one({"frase_forca": nova_frase})
        st.success("Frase atualizada com sucesso!")
        time.sleep(2)
        st.rerun()  # Recarrega a interface para refletir a atualização


# Diálogo para editar a missão institucional
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
        time.sleep(2)
        st.rerun()


###########################################################################################################
# INTERFACE PRINCIPAL DA PÁGINA
###########################################################################################################

# Configuração de layout para largura total
st.set_page_config(layout="wide")

# Exibe o logo do ISPN centralizado
st.markdown(
    "<div style='display: flex; justify-content: center;'>"
    "<img src='https://ispn.org.br/site/wp-content/uploads/2021/04/logo_ISPN_2021.png' alt='ISPN Logo'>"
    "</div>",
    unsafe_allow_html=True
)

# Recupera a frase de força e missão do banco (ou exibe mensagens padrão)
frase_doc = institucional.find_one({"frase_forca": {"$exists": True}})
frase_atual = frase_doc["frase_forca"] if frase_doc else "Frase não cadastrada ainda."

missao_doc = institucional.find_one({"missao": {"$exists": True}})
missao_atual = missao_doc["missao"] if missao_doc else "Missão não cadastrada ainda."

# Espaços em branco para espaçamento visual
st.write('')
st.write('')
st.write('')
st.write('')

# Exibe a frase de força centralizada
st.markdown(f"<h3 style='text-align: center;'>{frase_atual}</h3>", unsafe_allow_html=True)

# Se for usuário administrador, mostra botão para editar frase
if st.session_state.get("tipo_usuario") == "adm":
    st.button("Editar", icon=":material/edit:", key="editar_frase", on_click=editar_frase_dialog)

st.write('')
st.write('')

# Exibe missão com botão de edição para administradores
st.subheader("Missão")
st.write(missao_atual)
if st.session_state.get("tipo_usuario") == "adm":
    st.button("Editar", icon=":material/edit:", key="editar_missao", on_click=editar_missao_dialog)

st.write('')
st.write('')

# Visão de longo prazo
st.subheader('Visão de futuro para 2034')
st.write('Consolidar-se como um agente de transformação da sociedade fortalecendo os modos de vida sustentáveis, a participação social nas políticas públicas e a integração de práticas e saberes que promovem a justiça climática.')

st.write('')
st.write('')

# Valores institucionais
st.subheader('Valores do ISPN')
st.write('')

# Exibe os valores do ISPN em colunas com borda
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