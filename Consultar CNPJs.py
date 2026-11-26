import streamlit as st
import pandas as pd 
from funcoes_auxiliares import conectar_mongo_portal_ispn
import datetime
import re
import requests
import time
import io



# Exibe o logo do ISPN na página
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')

# Cabeçalho da página
st.header("Consultar CNPJs")
st.write('')  # Espaço vazio




######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################

# Conecta no banco MongoDB usando função auxiliar
db = conectar_mongo_portal_ispn()

# Carrega as coleções
estatistica = db["estatistica"] 
pessoas = db["pessoas"]



###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


PAGINA_ID = "consulta_cnpjs"
nome_pagina = "Consulta CNPJs"

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




# --------------------------------------------------
# CONFIGURAÇÃO DA TABELA DE CNPJs
# --------------------------------------------------

# Inicializa os dados da tabela na sessão
if "cnpjs_tabela" not in st.session_state:
    st.session_state["cnpjs_tabela"] = pd.DataFrame(
        columns=["Insira os CNPJs"]
    )

if "cnpjs_editor_versao" not in st.session_state:
    st.session_state["cnpjs_editor_versao"] = 0




# --------------------------------------------------
# CARREGAMENTO DOS CNPJs DOS COLABORADORES ATIVOS
# --------------------------------------------------

st.caption(
    "Insira os CNPJs manualmente ou utilize o botão abaixo para "
    "carregar os CNPJs dos colaboradores ativos."
)




with st.container(horizontal=True):

    if st.button(
        "Carregar CNPJs dos colaboradores ativos do ISPN",
        width="content",
        icon=":material/manage_search:"
    ):

        # Recupera os CNPJs dos colaboradores ativos
        documentos = pessoas.find(
            {
                "status": "ativo",
                "cnpj": {"$exists": True, "$nin": [None, ""]}
            },
            {
                "_id": 0,
                "cnpj": 1
            }
        )

        lista_cnpjs = []
        cnpjs_unicos = set()

        for documento in documentos:

            cnpj = re.sub(
                r"\D",
                "",
                str(documento.get("cnpj", ""))
            )

            if cnpj and cnpj not in cnpjs_unicos:

                lista_cnpjs.append(cnpj)
                cnpjs_unicos.add(cnpj)

        st.session_state["cnpjs_tabela"] = pd.DataFrame({
            "Insira os CNPJs": lista_cnpjs
        })

        # Reinicia o editor para carregar os novos dados
        st.session_state["cnpjs_editor_versao"] += 1

        st.session_state.pop("resultados_consulta_cnpj", None)
        st.session_state.pop("erros_consulta_cnpj", None)
        st.session_state.pop("cnpjs_consultados", None)



    if st.button(
        "Limpar lista",
        width="content",
        icon=":material/playlist_remove:"
    ):

        st.session_state["cnpjs_tabela"] = pd.DataFrame(
            columns=["Insira os CNPJs"]
        )

        # Reinicia o editor com a tabela vazia
        st.session_state["cnpjs_editor_versao"] += 1

        st.session_state.pop("resultados_consulta_cnpj", None)
        st.session_state.pop("erros_consulta_cnpj", None)
        st.session_state.pop("cnpjs_consultados", None)

st.write("")

# --------------------------------------------------
# FORMULÁRIO DE INSERÇÃO E CONSULTA DE CNPJs
# --------------------------------------------------


with st.form(
    key=f"form_consulta_cnpjs_{st.session_state['cnpjs_editor_versao']}",
    width=300,
    border=False
):

    df_editor = st.data_editor(
        st.session_state["cnpjs_tabela"],
        key=f"editor_cnpjs_{st.session_state['cnpjs_editor_versao']}",
        num_rows="dynamic",
        hide_index=True,
        column_order=["Insira os CNPJs"],
        width="stretch",
        column_config={
            "Insira os CNPJs": st.column_config.TextColumn(
                "Insira os CNPJs",
                help="Informe o CNPJ em qualquer formato. A limpeza será realizada automaticamente.",
                width="large"
            )
        }
    )

    consultar = st.form_submit_button(
        "Consultar CNPJs",
        type="primary",
        width="content",
        icon=":material/search:"
    )





# --------------------------------------------------
# FUNÇÃO DE FORMATAÇÃO DE DATAS
# --------------------------------------------------

def formatar_data(data):

    if not data:
        return None

    try:

        data_convertida = pd.to_datetime(
            data,
            errors="coerce"
        )

        if pd.isna(data_convertida):
            return None

        return data_convertida

    except (ValueError, TypeError):
        return None


# --------------------------------------------------
# VALIDAÇÃO E CONSULTA DOS CNPJs
# --------------------------------------------------

if consultar:

    # Atualiza os dados da sessão somente após o envio do formulário
    st.session_state["cnpjs_tabela"] = df_editor.copy()

    cnpjs_validos = []
    cnpjs_invalidos = []


    # Remove caracteres de formatação e valida os CNPJs
    for indice, valor in enumerate(
        st.session_state["cnpjs_tabela"]["Insira os CNPJs"],
        start=1
    ):

        if pd.isna(valor) or not str(valor).strip():
            continue

        cnpj = re.sub(
            r"\D",
            "",
            str(valor)
        )

        if len(cnpj) != 14:

            cnpjs_invalidos.append({
                "Linha": indice,
                "CNPJ informado": valor,
                "Quantidade de dígitos": len(cnpj)
            })

        else:

            cnpjs_validos.append(cnpj)

    # Impede a consulta quando existem CNPJs inválidos
    if cnpjs_invalidos:

        st.warning(
            f"Foram encontrados {len(cnpjs_invalidos)} CNPJs "
            "com quantidade de dígitos diferente de 14. "
            "Corrija os valores antes de realizar a consulta."
        )

        st.dataframe(
            pd.DataFrame(cnpjs_invalidos),
            hide_index=True,
            width="stretch"
        )

    elif not cnpjs_validos:

        st.warning("Informe pelo menos um CNPJ válido.")

    else:

        # Remove duplicidades sem alterar a ordem original
        cnpjs_validos = list(dict.fromkeys(cnpjs_validos))

        resultados = []
        erros_consulta = []

        total_cnpjs = len(cnpjs_validos)

        progresso = st.progress(0)
        mensagem_progresso = st.empty()





        # Recupera os nomes associados aos CNPJs cadastrados
        documentos_pessoas = pessoas.find(
            {"cnpj": {"$exists": True}},
            {
                "_id": 0,
                "cnpj": 1,
                "nome_completo": 1
            }
        )

        mapa_nomes = {}

        for pessoa in documentos_pessoas:

            cnpj_pessoa = re.sub(
                r"\D",
                "",
                str(pessoa.get("cnpj", ""))
            )

            if cnpj_pessoa:
                mapa_nomes.setdefault(
                    cnpj_pessoa,
                    pessoa.get("nome_completo", "")
                )


        # Configuração das requisições
        headers = {
            "User-Agent": "ConsultaCNPJ-Streamlit/1.0",
            "Accept": "application/json"
        }


        with requests.Session() as sessao:

            sessao.headers.update(headers)

            for indice, cnpj in enumerate(
                cnpjs_validos,
                start=1
            ):

                # Aplica a máscara brasileira ao CNPJ exibido
                cnpj_exibicao = re.sub(
                    r"^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$",
                    r"\1.\2.\3/\4-\5",
                    cnpj
                )

                mensagem_progresso.text(
                    f"Consultando CNPJ {indice} de "
                    f"{total_cnpjs}: {cnpj_exibicao}"
                )

                url = (
                    f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
                )

                try:

                    resposta = sessao.get(
                        url,
                        timeout=30
                    )

                    resposta.raise_for_status()

                    dados = resposta.json()

                    # Organiza os campos retornados pela API
                    cnpj_retorno = re.sub(
                        r"\D",
                        "",
                        str(dados.get("cnpj", cnpj))
                    )

                    cnpj_formatado = re.sub(
                        r"^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$",
                        r"\1.\2.\3/\4-\5",
                        cnpj_retorno
                    )






                    # Organiza os campos retornados pela API
                    resultados.append({

                        "CNPJ": cnpj_formatado,
                        
                        "Nome completo": mapa_nomes.get(cnpj, ""),

                        "Porte": dados.get("porte") or "",

                        "Razão social": dados.get("razao_social") or "",

                        "Município": dados.get("municipio") or "",

                        "Situação cadastral CNPJ": dados.get(
                            "descricao_situacao_cadastral"
                        ) or "",

                        "Data situação cadastral": formatar_data(
                            dados.get("data_situacao_cadastral")
                        ),

                        "Opção SIMPLES": (
                            "Optante"
                            if dados.get("opcao_pelo_simples") is True
                            else "Não optante"
                            if dados.get("opcao_pelo_simples") is False
                            else ""
                        ),

                        "Data opção SIMPLES": formatar_data(
                            dados.get("data_opcao_pelo_simples")
                        ),

                        "Data exclusão SIMPLES": formatar_data(
                            dados.get("data_exclusao_do_simples")
                        ),

                        "Opção MEI": (
                            "Optante"
                            if dados.get("opcao_pelo_mei") is True
                            else "Não optante"
                            if dados.get("opcao_pelo_mei") is False
                            else ""
                        )

                    })




                except requests.exceptions.RequestException as erro:

                    erros_consulta.append({
                        "CNPJ": cnpj_formatado,
                        "Erro": str(erro)
                    })

                except ValueError as erro:

                    erros_consulta.append({
                        "CNPJ": cnpj_formatado,
                        "Erro": f"Resposta inválida da API: {erro}"
                    })

                # Atualiza o progresso da execução
                progresso.progress(indice / total_cnpjs)

                # Intervalo entre as requisições
                if indice < total_cnpjs:
                    time.sleep(1)

        mensagem_progresso.empty()
        progresso.empty()

        # Armazena os resultados na sessão
        st.session_state["resultados_consulta_cnpj"] = resultados
        st.session_state["erros_consulta_cnpj"] = erros_consulta
        st.session_state["cnpjs_consultados"] = cnpjs_validos


# --------------------------------------------------
# APRESENTAÇÃO DOS RESULTADOS
# --------------------------------------------------

# Recupera os CNPJs atualmente presentes no editor
cnpjs_atualizados = []

for valor in st.session_state["cnpjs_tabela"]["Insira os CNPJs"]:

    if pd.isna(valor) or not str(valor).strip():
        continue

    cnpj = re.sub(r"\D", "", str(valor))

    if len(cnpj) == 14:
        cnpjs_atualizados.append(cnpj)

cnpjs_atualizados = list(dict.fromkeys(cnpjs_atualizados))

# Apresenta os resultados somente quando correspondem à tabela atual
if (
    "resultados_consulta_cnpj" in st.session_state
    and st.session_state.get("cnpjs_consultados") == cnpjs_atualizados
):

    resultados = st.session_state["resultados_consulta_cnpj"]
    erros_consulta = st.session_state["erros_consulta_cnpj"]

    st.divider()

    st.subheader("Resultado da consulta")

    col1, col2 = st.columns(2)

    col1.metric(
        "CNPJs consultados",
        len(resultados) + len(erros_consulta)
    )


    col2.metric(
        "Erros",
        len(erros_consulta)
    )

    # Apresenta os erros antes do DataFrame
    if erros_consulta:

        st.warning(
            f"{len(erros_consulta)} CNPJ(s) não puderam ser consultados."
        )

        with st.expander("Visualizar erros das consultas"):

            st.dataframe(
                pd.DataFrame(erros_consulta),
                hide_index=True,
                width="stretch"
            )

    # Apresenta os resultados
    if resultados:

        df_resultados = pd.DataFrame(resultados)

        st.dataframe(
            df_resultados,
            hide_index=True,
            width="stretch",
            column_config={

                "Data situação cadastral": st.column_config.DateColumn(
                    "Data situação cadastral",
                    format="DD/MM/YYYY"
                ),

                "Data opção SIMPLES": st.column_config.DateColumn(
                    "Data opção SIMPLES",
                    format="DD/MM/YYYY"
                ),

                "Data exclusão SIMPLES": st.column_config.DateColumn(
                    "Data exclusão SIMPLES",
                    format="DD/MM/YYYY"
                )

            }
        )

        # Gera o arquivo Excel em memória
        arquivo_excel = io.BytesIO()

        with pd.ExcelWriter(
            arquivo_excel,
            engine="openpyxl",
            date_format="DD/MM/YYYY",
            datetime_format="DD/MM/YYYY"
        ) as escritor:

            df_resultados.to_excel(
                escritor,
                index=False,
                sheet_name="Consulta CNPJs"
            )

            # Aplica o formato brasileiro às células das colunas de data
            planilha = escritor.sheets["Consulta CNPJs"]

            for coluna in [
                "Data situação cadastral",
                "Data opção SIMPLES",
                "Data exclusão SIMPLES"
            ]:

                indice_coluna = df_resultados.columns.get_loc(coluna) + 1

                for linha in range(2, len(df_resultados) + 2):

                    celula = planilha.cell(
                        row=linha,
                        column=indice_coluna
                    )

                    if celula.value is not None:
                        celula.number_format = "DD/MM/YYYY"

        arquivo_excel.seek(0)

        # Identifica o arquivo com data e hora da exportação
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%Hh-%Mm")

        st.download_button(
            "Baixar resultados em Excel",
            data=arquivo_excel.getvalue(),
            file_name=f"consulta_cnpjs_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/download:"
        )

    elif not erros_consulta:

        st.info("Nenhum resultado foi retornado pela consulta.")


