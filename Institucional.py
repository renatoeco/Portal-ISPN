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
@st.dialog("Informações Institucionais", width="large")
def editar_info_institucional_dialog():

    tab1, tab2, tab3, tab4 = st.tabs(["Editar frase força", "Editar missão", "Editar visão de futuro", "Editar valores"])


    # Frase Força //////////////////////////////////////////////////////
    with tab1:
        # Recupera a frase atual do banco, se existir
        frase_doc = institucional.find_one({"frase_forca": {"$exists": True}})
        frase_atual = frase_doc["frase_forca"] if frase_doc else ""
        
        # Campo para editar a frase
        nova_frase = st.text_area("Nova frase de força", value=frase_atual)
        
        # Botão para salvar a nova frase
        if st.button("Salvar", key="salvar frase força"):
            if frase_doc:
                # Atualiza documento existente
                institucional.update_one({"_id": frase_doc["_id"]}, {"$set": {"frase_forca": nova_frase}})
            else:
                # Cria novo documento se ainda não existir
                institucional.insert_one({"frase_forca": nova_frase})
            st.success("Frase atualizada com sucesso!")
            time.sleep(2)
            st.rerun()  # Recarrega a interface para refletir a atualização


    # Missão //////////////////////////////////////////////////////
    with tab2:
        missao_doc = institucional.find_one({"missao": {"$exists": True}})
        missao_atual = missao_doc["missao"] if missao_doc else ""
        
        nova_missao = st.text_area("Nova missão", value=missao_atual)
        
        if st.button("Salvar", key="salvar missão"):
            if missao_doc:
                institucional.update_one({"_id": missao_doc["_id"]}, {"$set": {"missao": nova_missao}})
            else:
                institucional.insert_one({"missao": nova_missao})
            st.success("Missão atualizada com sucesso!")
            time.sleep(2)
            st.rerun()


    # Visão de Futuro //////////////////////////////////////////////////////
    with tab3:
        visao_doc_titulo = institucional.find_one({"visao_titulo": {"$exists": True}})
        visao_doc_texto = institucional.find_one({"visao_texto": {"$exists": True}})
        visao_atual_titulo = visao_doc_titulo["visao_titulo"] if visao_doc_titulo else ""
        visao_atual_texto = visao_doc_texto["visao_texto"] if visao_doc_texto else ""
        
        nova_visao_titulo = st.text_input("Novo título para a visão", value=visao_atual_titulo)

        nova_visao_texto = st.text_area("Novo texto para a visão", value=visao_atual_texto)
        
        if st.button("Salvar", key="salvar visao"):
            if visao_doc_titulo and visao_doc_texto:
                institucional.update_one({"_id": visao_doc_titulo["_id"]}, {"$set": {"visao_titulo": nova_visao_titulo}})
                institucional.update_one({"_id": visao_doc_texto["_id"]}, {"$set": {"visao_texto": nova_visao_texto}})
            else:
                institucional.insert_one({"visao_titulo": nova_visao_titulo})
                institucional.insert_one({"visao_texto": nova_visao_texto})

            st.success("Visão atualizada com sucesso!")
            time.sleep(2)
            st.rerun()


    # Valores //////////////////////////////////////////////////////
    with tab4:
        # Busca o documento no MongoDB que contém os valores
        valores_doc = institucional.find_one({"valores_titulo": {"$exists": True}})

        # Recupera o título atual e a lista de valores
        valores_titulo_atual = valores_doc["valores_titulo"] if valores_doc else ""
        lista_valores_atual = valores_doc["valores"] if valores_doc and "valores" in valores_doc else []

        # Campo para editar o título geral
        novo_valores_titulo = st.text_input("Novo título para os valores", value=valores_titulo_atual)

        # Botão para atualizar apenas o título
        if st.button("Atualizar título", key="atualizar_valores_titulo"):
            if valores_doc:
                institucional.update_one(
                    {"_id": valores_doc["_id"]},
                    {"$set": {"valores_titulo": novo_valores_titulo}}
                )
                st.success("Título dos valores atualizado com sucesso!")
                time.sleep(2)
                st.rerun()
            else:
                st.error("Documento não encontrado.")

        st.markdown("---")

        # Ordena os valores por título (você pode trocar 'titulo' por outro campo se quiser outra ordem)
        lista_valores_ordenada = sorted(lista_valores_atual, key=lambda x: x.get("titulo", "").lower())

        # Dropdown com valores ordenados
        opcoes_valores = ["- Novo valor -"] + [valor["titulo"] for valor in lista_valores_ordenada]


        # Dropdown com opção de não selecionar nenhum valor
        titulo_selecionado = st.selectbox("Selecione o valor para editar", options=opcoes_valores)
        
        valor_selecionado = None
        index_valor = None

        if titulo_selecionado != "- Novo valor -":
            valor_selecionado = next((v for v in lista_valores_atual if v["titulo"] == titulo_selecionado), None)
            index_valor = lista_valores_atual.index(valor_selecionado) if valor_selecionado else None

        #st.markdown("---")

        st.subheader("Editar valor" if valor_selecionado else "Adicionar novo valor")

        # Campos de entrada
        novo_titulo = st.text_input("Título", value=valor_selecionado.get("titulo", "") if valor_selecionado else "")
        nova_descricao = st.text_area("Descrição", value=valor_selecionado.get("descricao", "") if valor_selecionado else "")

        # Atualizar valor
        if valor_selecionado and st.button("Atualizar valor", key="atualizar_valor"):
            lista_valores_atual[index_valor]["titulo"] = novo_titulo
            lista_valores_atual[index_valor]["descricao"] = nova_descricao

            update_data = {"valores": lista_valores_atual}
            if novo_valores_titulo != valores_titulo_atual:
                update_data["valores_titulo"] = novo_valores_titulo

            institucional.update_one(
                {"_id": valores_doc["_id"]},
                {"$set": update_data}
            )
            
            st.success("Valor atualizado com sucesso!")
            time.sleep(2)
            st.rerun()

        # Excluir valor
        if valor_selecionado and st.button("Excluir valor", key="excluir_valor"):
            lista_valores_atual.pop(index_valor)

            update_data = {"valores": lista_valores_atual}
            if novo_valores_titulo != valores_titulo_atual:
                update_data["valores_titulo"] = novo_valores_titulo

            institucional.update_one(
                {"_id": valores_doc["_id"]},
                {"$set": update_data}
            )
            st.success("Valor excluído com sucesso!")
            time.sleep(2)
            st.rerun()

        # Adicionar novo valor
        if not valor_selecionado and st.button("Adicionar valor / Atualizar título", key="adicionar_valor"):
            update_data = {}

            # Atualiza título, se tiver sido alterado
            if novo_valores_titulo != valores_titulo_atual:
                update_data["valores_titulo"] = novo_valores_titulo

            # Se o título e a descrição do novo valor estiverem preenchidos, adiciona à lista
            if novo_titulo.strip() or nova_descricao.strip():
                novo_valor = {"titulo": novo_titulo, "descricao": nova_descricao}
                lista_valores_atual.append(novo_valor)
                update_data["valores"] = lista_valores_atual

                if valores_doc:
                    institucional.update_one(
                        {"_id": valores_doc["_id"]},
                        {"$set": update_data}
                    )
                else:
                    institucional.insert_one({
                        "valores_titulo": novo_valores_titulo,
                        "valores": [novo_valor]
                    })
                st.success("Novo valor adicionado com sucesso!")

            elif update_data:
                # Atualiza apenas o título, se necessário
                institucional.update_one(
                    {"_id": valores_doc["_id"]},
                    {"$set": update_data}
                )
                st.success("Título dos valores atualizado com sucesso!")

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


# Busca o documento da missão
missao_doc = institucional.find_one({"missao": {"$exists": True}})
missao_atual = missao_doc["missao"] if missao_doc else "Missão não cadastrada ainda."


# Busca o documento do título da visão de futuro
visao_doc_titulo = institucional.find_one({"visao_titulo": {"$exists": True}})
visao_atual_titulo = visao_doc_titulo["visao_titulo"] if visao_doc_titulo else "Título da visão não cadastrado ainda."


# Busca o documento do texto da visão de futuro
visao_doc_texto = institucional.find_one({"visao_texto": {"$exists": True}})
visao_atual_texto = visao_doc_texto["visao_texto"] if visao_doc_texto else "Texto da visão não cadastrado ainda."


# Busca o documento de valores
valores_doc = institucional.find_one({"valores_titulo": {"$exists": True}})
valores_titulo_atual = valores_doc["valores_titulo"] if missao_doc else "Título dos valores não cadastrado ainda."
lista_valores = valores_doc.get("valores", []) if valores_doc else []

# Espaços em branco para espaçamento visual
st.write('')
st.write('')
st.write('')
st.write('')

# Se for usuário administrador, mostra botão para editar frase
if st.session_state.get("tipo_usuario") == "adm":
    st.button("Editar", icon=":material/edit:", key="editar_info", on_click=editar_info_institucional_dialog)

# Exibe a frase de força centralizada
st.markdown(f"<h3 style='text-align: center;'>{frase_atual}</h3>", unsafe_allow_html=True)


st.write('')
st.write('')


# Exibe missão com botão de edição para administradores
st.subheader("Missão")
st.write(missao_atual)


st.write('')
st.write('')

# Visão de longo prazo
st.subheader(visao_atual_titulo)
st.write(visao_atual_texto)

st.write('')
st.write('')

# Valores institucionais
st.subheader(valores_titulo_atual)
st.write('')


if lista_valores:
    # Ordena os valores por título (opcional)
    lista_valores = sorted(lista_valores, key=lambda x: x.get("titulo", "").lower())

    # Define o número de colunas por linha
    num_colunas = 5

    # Itera em blocos de até `num_colunas` valores por linha
    for i in range(0, len(lista_valores), num_colunas):
        valores_linha = lista_valores[i:i + num_colunas]
        colunas = st.columns(len(valores_linha))  # Cria somente o número de colunas necessárias

        for col, valor in zip(colunas, valores_linha):
            with col.container(border=True):
                st.markdown(f"**{lista_valores.index(valor) + 1} - {valor['titulo']}**  \n{valor['descricao']}")





# Exibe os valores do ISPN em colunas com borda
# col1, col2, col3, col4, col5 = st.columns(5)

# cont1 = col1.container(border=True)
# cont1.write("""
# **1 - Relações de confiança** \n
# Trabalhamos na construção de relações de respeito, confiança, honestidade e transparência, primando pelo diálogo e pela realização conjunta de ações para o alcance das transformações socioambientais.
# """)

# cont2 = col2.container(border=True)
# cont2.write("""           
# **2 - Compromisso socioambiental** \n
# Agimos com responsabilidade para equilibrar interesses socioeconômicos e ambientais em favor do bem-estar das pessoas e comunidades.
# """)

# cont3 = col3.container(border=True)
# cont3.write("""**3 - Reconhecimento de saberes** \n
# Valorizamos processos de aprendizagem que inspirem e multipliquem a diversidade de saberes e práticas para gerar transformações com impactos socioambientais justos e inclusivos.
# """)

# cont4 = col4.container(border=True)
# cont4.write("""**4 - Valorização da diversidade** \n
# Primamos pelas relações baseadas no respeito e na inclusão de todas as pessoas, reconhecendo e valorizando a pluralidade e o protagonismo de cada indivíduo e de seus coletivos.
# """)

# cont5 = col5.container(border=True)
# cont5.write("""**5 - Cooperação** \n
# Atuamos de maneira colaborativa e solidária no trabalho em equipe e entre organizações, parceiros e comunidades na busca de soluções para os desafios socioambientais contemporâneos.
# """)
