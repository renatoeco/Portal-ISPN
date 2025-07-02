import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
from funcoes_auxiliares import conectar_mongo_portal_ispn
from pymongo import UpdateOne


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas
programas_areas = db["programas_areas"]
projetos_ispn = db["projetos_ispn"] 
doadores = db["doadores"]
# projetos_pj = db["projetos_pj"] 
# projetos_pf = db["projetos_pf"]  
colaboradores_raw = list(db["pessoas"].find())


# Buscando todos os documentos da coleção programas_areas
dados_programas = list(programas_areas.find())


######################################################################################################
# FUNÇÕES
######################################################################################################


# Função para limpar e formatar o valor
def formatar_valor(valor_bruto, moeda_bruta):
    moeda = moedas.get(str(moeda_bruta).lower(), "R$")
    try:
        if valor_bruto is None:
            valor_num = 0
        else:
            valor_str = str(valor_bruto).replace(".", "").replace(",", ".")
            valor_num = float(valor_str)
        valor_formatado = f"{valor_num:,.0f}".replace(",", ".")
        return f"{moeda} {valor_formatado}"
    except Exception:
        return f"{moeda} 0"


######################################################################################################
# MAIN
######################################################################################################


# Verifica se há programas sem coordenador
programas_sem_coordenador = [
    prog for prog in dados_programas if not prog.get("coordenador_id")
]

if programas_sem_coordenador:
    atualizacoes = []

    for programa in programas_sem_coordenador:
        nome_programa = programa.get("nome_programa_area")
        coordenador_id = programa.get("coordenador_id")

        if not coordenador_id:
            # Busca coordenador correspondente ao programa
            for pessoa in colaboradores_raw:
                if (
                    pessoa.get("tipo de usuário", "").strip().lower() == "coordenador"
                    and pessoa.get("programa_area", "").strip() == nome_programa.strip()
                ):
                    novo_id = pessoa["_id"]
                    atualizacoes.append(UpdateOne(
                        {"_id": programa["_id"]},
                        {"$set": {"coordenador_id": novo_id}}
                    ))
                    break  # Parar no primeiro coordenador compatível encontrado

    # Executa as atualizações em lote
    if atualizacoes:
        resultado = programas_areas.bulk_write(atualizacoes)
        st.success(f"{resultado.modified_count} programa(s) atualizado(s) com coordenador_id.")
    else:
        st.info("Programas sem coordenador encontrados, mas nenhum coordenador correspondente foi localizado.")

colaborador_id_para_nome = {
    str(col["_id"]): col.get("nome_completo", "Não encontrado")
    for col in colaboradores_raw
}

# Lista com nomes dos coordenadores, para filtrar da equipe
nomes_coordenadores = set()

lista_programas = []

for doc in dados_programas:
    # Verifica se o documento é um programa simples ou tem subprogramas embutidos
    programas_embutidos = doc.get("nome_programa_area")
    if not isinstance(programas_embutidos, list):
        programas_embutidos = [doc] if isinstance(doc, dict) else []

    for programa in programas_embutidos:
        if not isinstance(programa, dict):
            continue

        coordenador_id = programa.get("coordenador_id")
        nome_coordenador = colaborador_id_para_nome.get(str(coordenador_id), "Não encontrado")
        nomes_coordenadores.add(nome_coordenador)

        genero_coordenador = "Não informado"
        for colab_doc in colaboradores_raw:
            if str(colab_doc.get("_id")) == str(coordenador_id):
                genero_coordenador = colab_doc.get("gênero", "Não informado")
                break

        lista_programas.append({
            "titulo": programa.get("nome_programa_area", "Sem título"),
            "coordenador": nome_coordenador,
            "genero_coordenador": genero_coordenador
        })

titulos_abas = [p['titulo'] for p in lista_programas if p.get('titulo')]

lista_equipe = []

for colab_doc in colaboradores_raw:
    if colab_doc.get("status", "").lower() != "ativo":
        continue  # Pula quem não for ativo

    nome = colab_doc.get("nome_completo", "Desconhecido")

    # Ignora coordenadores
    if nome in nomes_coordenadores:
        continue

    genero = colab_doc.get("gênero", "")
    programa_area = colab_doc.get("programa_area", "")
    projeto_pagador = colab_doc.get("projeto_pagador", "")

    lista_equipe.append({
        "Nome": nome,
        "Gênero": genero,
        "Programa": programa_area,
        "Projeto": projeto_pagador
    })

df_equipe = pd.DataFrame(lista_equipe)

# Cria o DataFrame para exibição com coluna "Projetos" vazia
df_equipe_exibir = df_equipe[["Nome", "Gênero", "Projeto"]].copy()


st.header("Programas e Áreas")

st.write("")

abas = st.tabs(titulos_abas)

# Carrega todos os projetos ISPN
dados_projetos_ispn = list(projetos_ispn.find())

# Carrega todos os doadores
dados_doadores = list(doadores.find())
mapa_doador_id_para_nome = {
    str(d["_id"]): d.get("nome_doador", "Não informado")
    for d in dados_doadores
}

# Dicionário de símbolos por moeda
moedas = {
    "reais": "R$",
    "real": "R$",
    "dólares": "US$",
    "dólar": "US$",
    "euros": "€",
    "euro": "€"
}

for i, aba in enumerate(abas):
    with aba:
        programa = lista_programas[i]
        titulo_programa = programa['titulo']
        id_programa = dados_programas[i].get("_id") 


        # Filtra no df original (que tem a coluna 'Programa')
        df_equipe_filtrado = df_equipe[df_equipe['Programa'] == titulo_programa].copy()

        # Para exibir, pega só as linhas do df_equipe_exibir correspondentes
        df_exibir_filtrado = df_equipe_exibir.loc[df_equipe_filtrado.index].copy()

        df_exibir_filtrado.index = range(1, len(df_exibir_filtrado) + 1)

        st.subheader(f"{titulo_programa}")
        
        genero = programa['genero_coordenador']
        prefixo = "Coordenador" if genero == "Masculino" else "Coordenadora" if genero == "Feminino" else "Coordenador(a)"
        st.write(f"**{prefixo}:** {programa['coordenador']}")

        st.write("")
        st.write('**Equipe**:')
        st.write(f'{len(df_exibir_filtrado)} colaboradores(as):')
        st.dataframe(df_exibir_filtrado, hide_index=True)

        st.divider()

        # PROJETOS

        st.write('')
        st.write('**Projetos:**')

        col1, col2, col3 = st.columns(3)
        situacao_filtro = col1.selectbox(
            "Situação",
            ["Todos", "Em andamento", "Finalizado", ""],
            key=f"situacao_{i}"
        )

        # Filtra os projetos ligados ao programa atual pelo ID do programa
        projetos_do_programa = [
            p for p in dados_projetos_ispn
            if p.get("programa") == id_programa
        ]

        # Ordena por código
        projetos_do_programa_ordenados = sorted(
            projetos_do_programa,
            key=lambda p: p.get("codigo", "")
        )

        # Aplica o filtro de situação
        if situacao_filtro != "Todos":
            projetos_do_programa_ordenados = [
                p for p in projetos_do_programa_ordenados
                if p.get("status", "Não informado") == situacao_filtro
            ]

        if projetos_do_programa_ordenados:
            dados_projetos = {
                "Código": [],
                "Nome do projeto": [],
                "Início": [],
                "Fim": [],
                "Valor": [],
                "Doador": [],
                "Situação": []
            }

            for projeto in projetos_do_programa_ordenados:
                dados_projetos["Código"].append(projeto.get("codigo", ""))
                dados_projetos["Nome do projeto"].append(projeto.get("nome_do_projeto", "Sem nome"))
                dados_projetos["Início"].append(projeto.get("data_inicio_contrato", "Não informado"))
                dados_projetos["Fim"].append(projeto.get("data_fim_contrato", "Não informado"))

                valor_bruto = projeto.get("valor", 0) or 0
                moeda_bruta = projeto.get("moeda", "reais")  # padrão "reais" caso não exista
                valor_formatado = formatar_valor(valor_bruto, moeda_bruta)
                dados_projetos["Valor"].append(valor_formatado)

                id_doador = projeto.get("doador")
                nome_doador = mapa_doador_id_para_nome.get(str(id_doador), "Não informado")
                dados_projetos["Doador"].append(nome_doador)

                dados_projetos["Situação"].append(projeto.get("status", "Não informado"))

            df_projetos = pd.DataFrame(dados_projetos)
            df_projetos.index += 1
            quantidade = len(df_projetos)
            plural = "projetos vinculados" if quantidade != 1 else "projeto vinculado"

            areas = ["Comunicação", "ADM Brasília", "ADM Santa Inês", "Advocacy", "Coordenação"]

            if titulo_programa in areas:
                st.write(f"{quantidade} {plural} à área **{titulo_programa}**:")
            else:
                st.write(f"{quantidade} {plural} ao programa **{titulo_programa}**:")


            st.dataframe(df_projetos, hide_index=True)
        else:
            st.info("Nenhum projeto vinculado a este programa/área.")



        st.divider()

        # INDICADORES DO PROGRAMA
        # st.write('')

        # st.write('**Indicadores do Programa:**')
        # st.write('')

        # sel1, sel2, sel3 = st.columns(3)
        
        # sel1.selectbox("Ano", ["2023", "2024", "2025"], key=f"ano_{i}")
        # sel2.selectbox("Projeto", ["Todos", "Projeto 1", "Projeto 2", "Projeto 3"], key=f"projeto_{i}")
        
        # st.write('')
        # st.write('')

        # # Mostrar detalhes
        # # Função principal decorada com dialog
        # @st.dialog("Detalhes dos reportes de indicadores", width="large")
        # def mostrar_detalhes():
        #     df_indicadores = pd.DataFrame({
        #         "Reporte": [
        #             "Organizações do x",
        #             "Projeto x",
        #             "Preparação pra COP do Clima",
        #             "Apoio à Central do Programa 1"
        #         ],
        #         "Valor": [
        #             25,
        #             2,
        #             8,
        #             18,
        #         ],
        #         "Ano": [
        #             2023,
        #             2023,
        #             2023,
        #             2023,
        #         ],"Projeto": [
        #             "x",
        #             "x",
        #             "x",
        #             "x do Programa 1",
        #         ],
        #         "Observações": [
        #             "Contagem manual",
        #             "Por conversa telefônica",
        #             "Se refere ao seminário estadual",
        #             "Contagem manual",
        #         ],
        #         "Autor": [
        #             "João",
        #             "Maria",
        #             "José",
        #             "Pedro",
        #         ]
        #     })
        #     # st.dataframe(df_indicadores, hide_index=True)

        #     ui.table(df_indicadores)


        # # Função handler que será passada para on_click
        # def handler():
        #     def _handler():
        #         mostrar_detalhes()
        #     return _handler


        # col1, col2 = st.columns(2)

        # with col1.container(border=True):
        #     st.write('**Organizações e Comunidades**')
        #     st.button("Indicador X **51**", on_click=handler(), type="tertiary", key=f"org_51_{i}")
        #     st.button("Indicador X **12**", on_click=handler(), type="tertiary", key=f"org_12_{i}")
            



        # with col2.container(border=True):
        
        #     st.write('**Pessoas**')

        #     st.button("Indicador X **1500**", on_click=handler(), type="tertiary", key=f"pessoas_1500_{i}")
        #     st.button("Indicador X **300**", on_click=handler(), type="tertiary", key=f"pessoas_300_{i}")
        #     st.button("Indicador X **500**", on_click=handler(), type="tertiary", key=f"pessoas_500_{i}")
        #     st.button("Indicador X **350**", on_click=handler(), type="tertiary", key=f"pessoas_350_{i}")
        #     st.button("Indicador X **550**", on_click=handler(), type="tertiary", key=f"pessoas_550_{i}")
        #     st.button("Indicador X **200**", on_click=handler(), type="tertiary", key=f"pessoas_200_{i}")
        #     st.button("Indicador X **100**", on_click=handler(), type="tertiary", key=f"pessoas_100_{i}")
        #     st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"pessoas_50_{i}")
        #     st.button("Indicador X **75**", on_click=handler(), type="tertiary", key=f"pessoas_75_{i}")
        #     st.button("Indicador X **25**", on_click=handler(), type="tertiary", key=f"pessoas_25_{i}")

        # with col1.container(border=True):
        #     st.write('**Capacitações**')
        #     st.button("Indicador X **10**", on_click=handler(), type="tertiary", key=f"cap_10_{i}")
        #     st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"cap_50_{i}")
        #     st.button("Indicador X **75**", on_click=handler(), type="tertiary", key=f"cap_75_{i}")
        #     st.button("Indicador X **60**", on_click=handler(), type="tertiary", key=f"cap_60_{i}")
        #     st.button("Indicador X **100**", on_click=handler(), type="tertiary", key=f"cap_100_{i}")


        # with col1.container(border=True):
        #     st.write('**Intercâmbios**')
        #     st.button("Indicador X **10**", on_click=handler(), type="tertiary", key=f"inter_10_{i}")
        #     st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"inter_50_{i}")
        #     st.button("Indicador X **60**", on_click=handler(), type="tertiary", key=f"inter_60_{i}")

        # with col2.container(border=True):
        #     st.write('**Território**')
        #     st.button("Indicador X **25**", on_click=handler(), type="tertiary", key=f"ter_25_{i}")
        #     st.button("Indicador X **235**", on_click=handler(), type="tertiary", key=f"ter_235_{i}")
        #     st.button("Indicador X **321**", on_click=handler(), type="tertiary", key=f"ter_321_{i}")
        #     st.button("Indicador X **58**", on_click=handler(), type="tertiary", key=f"ter_58_{i}")
        #     st.button("Indicador X **147**", on_click=handler(), type="tertiary", key=f"ter_147_{i}")

        # with col1.container(border=True):
        #     st.write('**Tecnologia e Infra-estrutura**')
        #     st.button("Indicador X **20**", on_click=handler(), type="tertiary", key=f"tec_20_{i}")
        #     st.button("Indicador X **50**", on_click=handler(), type="tertiary", key=f"tec_50_{i}")
        #     st.button("Indicador X **200**", on_click=handler(), type="tertiary", key=f"tec_200_{i}")

        # with col1.container(border=True):
        #     st.write('**Financeiro**')
        #     st.button("Indicador X **25200**", on_click=handler(), type="tertiary", key=f"fin_25200_{i}")
        #     st.button("Indicador X **14000**", on_click=handler(), type="tertiary", key=f"fin_14000_{i}")

        # with col2.container(border=True):
        #     st.write('**Comunicação**')
        #     st.button("Indicador X **25**", on_click=handler(), type="tertiary", key=f"com_25_{i}")
        #     st.button("Indicador X **14**", on_click=handler(), type="tertiary", key=f"com_14_{i}")
        #     st.button("Indicador X **12**", on_click=handler(), type="tertiary", key=f"com_12_{i}")
        #     st.button("Indicador X **35**", on_click=handler(), type="tertiary", key=f"com_35_{i}")
        #     st.button("Indicador X **24**", on_click=handler(), type="tertiary", key=f"com_24_{i}")

        # with col1.container(border=True):
        #     st.write('**Políticas Públicas**')
        #     st.button("Indicador X **5**", on_click=handler(), type="tertiary", key=f"pol_5_{i}")
        #     st.button("Indicador X **2**", on_click=handler(), type="tertiary", key=f"pol_2_{i}")
        #     st.button("Indicador X **6**", on_click=handler(), type="tertiary", key=f"pol_6_{i}")