import streamlit as st
import time
import re
from datetime import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn  # Função personalizada para conectar ao MongoDB


###########################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
###########################################################################################################

# Conecta-se ao banco de dados MongoDB (usa cache automático para melhorar performance)
db = conectar_mongo_portal_ispn()

# Define as coleções específicas que serão utilizadas a partir do banco
estatistica = db["estatistica"]
colaboradores = db["colaboradores"]
institucional = db["institucional"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################

# Nome da página atual, usado como chave para contagem de acessos
nome_pagina = "Institucional"

# Cria um timestamp formatado com dia/mês/ano hora:minuto:segundo
timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# Cria o nome do campo dinamicamente baseado na página
campo_timestamp = f"{nome_pagina}.Visitas"

# Atualiza a coleção de estatísticas com o novo acesso, incluindo o timestamp
estatistica.update_one(
    {},
    {"$push": {campo_timestamp: timestamp}},
    upsert=True  # Cria o documento se ele ainda não existir
)


###########################################################################################################
# FUNÇÕES
###########################################################################################################

# Cria uma caixa de diálogo no Streamlit com abas para edição de informações institucionais
@st.dialog("Informações Institucionais", width="large")
def editar_info_institucional_dialog():

    # Cria quatro abas para editar diferentes seções institucionais
    tab1, tab2, tab3, tab4 = st.tabs(["Editar frase força", "Editar missão", "Editar visão de futuro", "Editar valores"])

    # Aba para edição da frase de força
    with tab1:
        frase_doc = institucional.find_one({"frase_forca": {"$exists": True}})
        frase_atual = frase_doc["frase_forca"] if frase_doc else ""
        nova_frase = st.text_area("Nova frase de força", value=frase_atual)

        if st.button("Salvar", key="salvar frase força"):
            if frase_doc:
                institucional.update_one({"_id": frase_doc["_id"]}, {"$set": {"frase_forca": nova_frase}})
            else:
                institucional.insert_one({"frase_forca": nova_frase})
            st.success("Frase atualizada com sucesso!")
            time.sleep(2)
            st.rerun()

    # Aba para edição da missão institucional
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

    # Aba para edição da visão de futuro
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

    # Aba para edição dos valores institucionais
    with tab4:
        valores_doc = institucional.find_one({"valores_titulo": {"$exists": True}})
        valores_titulo_atual = valores_doc["valores_titulo"] if valores_doc else ""
        lista_valores_atual = valores_doc["valores"] if valores_doc and "valores" in valores_doc else []

        novo_valores_titulo = st.text_input("Novo título para os valores", value=valores_titulo_atual)

        # Botão para atualizar o título dos valores
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

        # Ordena os valores alfabeticamente pelo título
        lista_valores_ordenada = sorted(lista_valores_atual, key=lambda x: x.get("titulo", "").lower())
        opcoes_valores = ["- Novo valor -"] + [valor["titulo"] for valor in lista_valores_ordenada]

        titulo_selecionado = st.selectbox("Selecione o valor para editar", options=opcoes_valores)
        valor_selecionado = None
        index_valor = None

        # Se um valor já existente foi selecionado, busca esse valor
        if titulo_selecionado != "- Novo valor -":
            valor_selecionado = next((v for v in lista_valores_atual if v["titulo"] == titulo_selecionado), None)
            index_valor = lista_valores_atual.index(valor_selecionado) if valor_selecionado else None

        # Título da seção condicional conforme valor selecionado
        st.subheader("Editar valor" if valor_selecionado else "Adicionar novo valor")

        novo_titulo = st.text_input("Título", value=valor_selecionado.get("titulo", "") if valor_selecionado else "")
        nova_descricao = st.text_area("Descrição", value=valor_selecionado.get("descricao", "") if valor_selecionado else "")

        # Atualizar valor existente
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

        # Excluir valor existente
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
        if not valor_selecionado and st.button("Adicionar valor", key="adicionar_valor"):
            update_data = {}

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

            time.sleep(2)
            st.rerun()


###########################################################################################################
# INTERFACE PRINCIPAL DA PÁGINA
###########################################################################################################

# Define o layout da página como largura total
st.set_page_config(layout="wide")

# Exibe o logo do ISPN centralizado na tela
st.markdown(
    "<div style='display: flex; justify-content: center;'>"
    "<img src='https://ispn.org.br/site/wp-content/uploads/2021/04/logo_ISPN_2021.png' alt='ISPN Logo'>"
    "</div>",
    unsafe_allow_html=True
)

# Recupera e exibe a frase de força cadastrada (ou mensagem padrão se não houver)
frase_doc = institucional.find_one({"frase_forca": {"$exists": True}})
frase_atual = frase_doc["frase_forca"] if frase_doc else "Frase não cadastrada ainda."

# Recupera e exibe a missão cadastrada (ou mensagem padrão se não houver)
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

tipos_usuario = st.session_state.get("tipo_usuario", [])
if "adm" in tipos_usuario:
    col1, col2, col3 = st.columns([6, 1, 1])  # Ajuste os pesos conforme necessário
    with col3:
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
    def extrair_numero(titulo):
        match = re.match(r"(\d+)", titulo)
        return int(match.group(1)) if match else float("inf")

    # Ordena com base no número extraído do título
    lista_valores = sorted(lista_valores, key=lambda x: extrair_numero(x.get("titulo", "")))

    total_valores = len(lista_valores)

    # Cria blocos de colunas para exibição
    for i in range(0, total_valores, 5):
        valores_linha = lista_valores[i:i + 5]
        colunas = st.columns(5)
        espacos_vazios = (5 - len(valores_linha)) // 2

        for idx, valor in enumerate(valores_linha):
            posicao = idx + espacos_vazios
            with colunas[posicao].container(border=True):
                st.markdown(f"**{valor['titulo']}**  \n{valor['descricao']}")
