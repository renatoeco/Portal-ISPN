import streamlit as st

st.set_page_config(layout="wide")

# st.logo("/home/renato/Projetos_Python/ISPN_HUB/app_ispn_hub/images/logo_ISPN_horizontal_ass.png")

st.markdown(
    "<div style='display: flex; justify-content: center;'>"
    "<img src='https://ispn.org.br/site/wp-content/uploads/2021/04/logo_ISPN_2021.png' alt='ISPN Logo'>"
    "</div>",
    unsafe_allow_html=True
)





st.write('')
st.write('')
st.write('')

st.write('')
st.markdown("<h3 style='text-align: center;'>Fortalecer meios de vida sustentáveis com protagonismo comunitário.</h3>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

st.write('')
st.subheader('Missão')

st.write('Contribuir para viabilizar a equidade social e o equilíbrio ambiental, com o fortalecimento de meios de vida sustentáveis e estratégias de adaptação às mudanças climáticas.')

st.write('')
st.subheader('Visão de futuro para 2034')

st.write('Consolidar-se como um agente de transformação da sociedade fortalecendo os modos de vida sustentáveis, a participação social nas políticas públicas e a integração de práticas e saberes que promovem a justiça climática.')

st.write('')
st.subheader('Valores do ISPN')

st.write('')

col1, col2, col3, col4, col5 = st.columns(5)

col1.write("""
**1 - Relações de confiança** \n
Trabalhamos na construção de relações de respeito, confiança, honestidade e transparência, primando pelo diálogo e pela realização conjunta de ações para o alcance das transformações socioambientais.
""")

col2.write("""           
**2 - Compromisso socioambiental** \n
Agimos com responsabilidade para equilibrar interesses socioeconômicos e ambientais em favor do bem-estar das pessoas e comunidades.
""")

col3.write("""**3 - Reconhecimento de saberes** \n
Valorizamos processos de aprendizagem que inspirem e multipliquem a diversidade de saberes e práticas para gerar transformações com impactos socioambientais justos e inclusivos.
""")

col4.write("""**4 - Valorização da diversidade** \n
Primamos pelas relações baseadas no respeito e na inclusão de todas as pessoas, reconhecendo e valorizando a pluralidade e o protagonismo de cada indivíduo e de seus coletivos.
""")

col5.write("""**5 - Cooperação** \n
Atuamos de maneira colaborativa e solidária no trabalho em equipe e entre organizações, parceiros e comunidades na busca de soluções para os desafios socioambientais contemporâneos.
""")
