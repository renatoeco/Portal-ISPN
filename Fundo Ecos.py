import streamlit as st
import pandas as pd
import folium
import unicodedata
import math
import time
from bson import ObjectId
import plotly.express as px
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from bson import ObjectId
from funcoes_auxiliares import conectar_mongo_portal_ispn


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()

pj = list(db["projetos_pj"].find())
pf = list(db["projetos_pf"].find())
projetos_ispn = list(db["projetos_ispn"].find())

colecao_doadores = db["doadores"]
ufs_municipios = db["ufs_municipios"]
programas = db["programas_areas"]
pessoas = db["pessoas"]
estatistica = db["estatistica"]  # Coleção de estatísticas


######################################################################################################
# CSS PARA DIALOGO MAIOR
######################################################################################################


st.markdown(
    """
<style>
div[data-testid="stDialog"] div[role="dialog"]:has(.big-dialog) {
    width: 70vw;
    
}
</style>
""",
    unsafe_allow_html=True,
)

######################################################################################################
# FUNÇÕES
######################################################################################################


# Função para converter lista de códigos em lista de nomes
def converter_codigos_para_nomes(valor):
    if not valor:
        return ""

    try:
        # Divide por vírgula, remove espaços e filtra vazios
        partes = [v.strip() for v in valor.split(",") if v.strip()]
        nomes = []

        for parte in partes:
            if parte.isdigit():
                # Tenta mapear o código (int convertido para str)
                nome = codigo_para_nome.get(parte, parte)
                nomes.append(nome)
            else:
                # Já é nome (ex: 'Brasília')
                nomes.append(parte)

        return ", ".join(nomes)
    except Exception as e:
        return valor
    
def converter_uf_codigo_para_nome(valor):
    """
    Converte um ou mais códigos de UF para seus nomes correspondentes.
    Exemplo de entrada: "12,27"
    """
    if not valor:
        return ""

    try:
        partes = [v.strip() for v in valor.split(",") if v.strip()]
        nomes = []

        for parte in partes:
            if parte.isdigit():
                nome = uf_para_nome.get(parte, parte)
                nomes.append(nome)
            else:
                nomes.append(parte)

        return ", ".join(nomes)
    except Exception as e:
        return valor
    

@st.dialog("Detalhes do projeto", width="large")
def mostrar_detalhes(codigo_proj: str):
    codigo_proj = str(codigo_proj).strip()
    df_filtrado = st.session_state.get("df_filtrado", pd.DataFrame())
    if df_filtrado.empty:
        st.error("Não há dados filtrados no momento.")
        return

    mask = df_filtrado["Código"].astype(str).str.strip() == codigo_proj
    if not mask.any():
        st.error("Projeto não encontrado nos filtros atuais.")
        return

    projeto_df = df_filtrado.loc[mask].iloc[0]

    projeto = projetos_por_codigo.get(codigo_proj, {})

    nome_ponto_focal = "Não informado"
    ponto_focal_obj = projeto.get("ponto_focal")
    if isinstance(ponto_focal_obj, ObjectId):
        pessoa = db["pessoas"].find_one(
            {"_id": ponto_focal_obj},
            {"nome_completo": 1, "_id": 0}  # Projeta apenas o campo necessário → mais rápido
        )
        if pessoa:
            nome_ponto_focal = pessoa.get("nome_completo", "Não encontrado")

    # Corpo do diálogo
    st.write(f"**Proponente:** {projeto.get('proponente', '')}")
    st.write(f"**Nome do projeto:** {projeto.get('nome_do_projeto', '')}")
    st.write(f"**Tipo:** {projeto.get('tipo', '')}")
    st.write(f"**Edital:** {projeto_df['Edital']}")
    st.write(f"**Doador:** {projeto_df['Doador']}")
    st.write(f"**Moeda:** {projeto.get('moeda', '')}")
    st.write(f"**Valor:** {projeto_df['Valor']}")
    st.write(f"**Categoria:** {projeto.get('categoria', '')}")
    st.write(f"**Ano de aprovação:** {projeto_df['Ano']}")
    st.write(f"**Estado(s):** {converter_uf_codigo_para_nome(projeto.get('ufs', ''))}")
    st.write(f"**Município(s):** {converter_codigos_para_nomes(projeto.get('municipios', ''))}")
    st.write(f"**Data de início:** {projeto.get('data_inicio_do_contrato', '')}")
    st.write(f"**Data de fim:** {projeto.get('data_final_do_contrato', '')}")
    st.write(f"**Ponto Focal:** {nome_ponto_focal}")
    st.write(f"**Temas:** {projeto.get('temas', '')}")
    st.write(f"**Público:** {projeto.get('publico', '')}")
    st.write(f"**Bioma:** {projeto.get('bioma', '')}")
    st.write(f"**Situação:** {projeto.get('status', '')}")
    st.write(f"**Objetivo geral:** {projeto.get('objetivo_geral', '')}")

    nomes_legiveis = {
        "numero_de_organizacoes_apoiadas": "Número de organizações apoiadas",
        "numero_de_comunidades_fortalecidas": "Número de comunidades fortalecidas",
        "numero_de_familias": "Número de famílias beneficiadas",
        "numero_de_homens_jovens": "Número de homens jovens",
        "numero_de_homens_adultos": "Número de homens adultos",
        "numero_de_mulheres_jovens": "Número de mulheres jovens",
        "numero_de_mulheres_adultas": "Número de mulheres adultas",
        "numero_de_indigenas": "Número de indígenas",
        "numero_de_lideranas_comunitarias_fortalecidas": "Número de lideranças comunitárias fortalecidas",
        "numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_fundo_ecos": "Número de famílias comercializando produtos da sociobio com apoio do Fundo Ecos",
        "numero_de_familias_acessando_vendas_institucionais_com_apoio_do_fundo_ecos": "Número de famílias acessando vendas institucionais com apoio do Fundo Ecos",
        "numero_de_estudantes_recebendo_bolsa": "Número de estudantes recebendo bolsa",
        "numero_de_capacitacoes_realizadas": "Número de capacitações realizadas",
        "numero_de_homens_jovens_capacitados": "Número de homens jovens capacitados",
        "numero_de_homens_adultos_capacitados": "Número de homens adultos capacitados",
        "numero_de_mulheres_jovens_capacitadas": "Número de mulheres jovens capacitadas",
        "numero_de_mulheres_adultas_capacitadas": "Número de mulheres adultas capacitadas",
        "numero_de_intercambios_realizados": "Número de intercâmbios realizados",
        "numero_de_homens_em_intercambios": "Número de homens em intercâmbios",
        "numero_de_mulheres_em_intercambios": "Número de mulheres em intercâmbios",
        "numero_de_iniciativas_de_gestao_territorial_implantadas": "Número de iniciativas de gestão territorial implantadas",
        "area_com_manejo_ecologico_do_fogo_ha": "Área com manejo ecológico do fogo (ha)",
        "area_com_manejo_agroecologico_ha": "Área com manejo agroecológico (ha)",
        "area_com_manejo_para_restauracao_ha": "Área com manejo para restauração (ha)",
        "area_com_manejo_para_extrativismo_ha": "Área com manejo para extrativismo (ha)",
        "numero_de_agroindustiras_implementadas_ou_reformadas": "Número de agroindústrias implementadas ou reformadas",
        "numero_de_tecnologias_instaladas": "Número de tecnologias instaladas",
        "numero_de_pessoas_beneficiadas_com_tecnologias": "Número de pessoas beneficiadas com tecnologias",
        "numero_de_videos_produzidos": "Número de vídeos produzidos",
        "numero_de_aparicoes_na_midia": "Número de aparições na mídia",
        "numero_de_publicacoes_de_carater_tecnico": "Número de publicações de caráter técnico",
        "numero_de_artigos_academicos_produzidos_e_publicados": "Número de artigos acadêmicos produzidos e publicados",
        "numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn": "Número de comunicadores comunitários contribuindo na execução das ações do ISPN",
        "faturamento_bruto_anual_pre_projeto": "Faturamento bruto anual pré-projeto",
        "faturamento_bruto_anual_pos_projeto": "Faturamento bruto anual pós-projeto",
        "volume_financeiro_de_vendas_institucionais_com_apoio_do_ppp_ecos": "Volume financeiro de vendas institucionais com apoio do PPP-ECOS",
        "numero_de_visitas_de_monitoramento_realizadas_ao_projeto_apoiado": "Número de visitas de monitoramento realizadas ao projeto apoiado",
        "valor_da_contrapartida_financeira_projetinhos": "Valor da contrapartida financeira",
        "valor_da_contrapartida_nao_financeira_projetinhos": "Valor da contrapartida não financeira",
        "especies": "Espécies",
        "numero_de_organizacoes_apoiadas_que_alavancaram_recursos": "Número de organizações que alavancaram recursos",
        "valor_mobilizado_de_novos_recursos": "Valor mobilizado de novos recursos",
        "numero_de_politicas_publicas_monitoradas_pelo_ispn": "Número de políticas públicas monitoradas pelo ISPN",
        "numero_de_proposicoes_legislativas_acompanhadas_pelo_ispn": "Número de proposições legislativas acompanhadas pelo ISPN",
        "numero_de_contribuicoes_notas_tecnicas_participacoes_e_ou_documentos_que_apoiam_a_construcao_e_aprimoramento_de_politicas_publicas": "Número de contribuições (notas técnicas, participações e/ou documentos) que apoiam a construção e aprimoramento de políticas públicas",
        "numero_de_imoveis_rurais_com_producao_sustentavel": "Número de imóveis rurais com produção sustentável",
        "area_de_vegetacao_natural_diretamente_manejada": "Área de vegetação natural diretamente manejada (ha)",
        "area_de_recuperacao_tecnica_saf": "Área de recuperação técnica (SAF) (ha)",
        "area_de_recuperacao_tecnica_regeneracao": "Área de recuperação técnica (regeneração) (ha)",
        "area_de_recuperacao_tecnica_plantio_adensamento": "Área de recuperação técnica (plantio/adensamento) (ha)",
        "numero_de_unidades_demonstrativas_de_plantio": "Número de unidades demonstrativas de plantio",
        "numero_de_infraestruturas_de_producao_implantadas": "Número de infraestruturas de produção implantadas",
        "numero_de_transportes_adquiridos_para_plantio": "Número de transportes adquiridos para plantio",
        "numero_de_transportes_adquiridos_para_beneficiamento": "Número de transportes adquiridos para beneficiamento",
        "faturamento_bruto_produtos_in_natura": "Faturamento bruto de produtos in natura",
        "faturamento_bruto_produtos_beneficiados": "Faturamento bruto de produtos beneficiados"
    }

    proj_id = projeto.get("_id")  # ObjectId do projeto

    lancamentos = list(db["lancamentos_indicadores"].find({"projeto": proj_id}))
    if not lancamentos:
        st.info("Não há lançamentos de indicadores para este projeto.")
    else:
        # Monta DataFrame diretamente
        linhas = []
        for lan in lancamentos:
            ind_id = lan.get("id_do_indicador")
            
            # Garantir que seja ObjectId para consulta
            if isinstance(ind_id, str):
                try:
                    ind_id_obj = ObjectId(ind_id)
                except Exception:
                    ind_id_obj = None
            elif isinstance(ind_id, ObjectId):
                ind_id_obj = ind_id
            else:
                ind_id_obj = None

            indicador_nome = str(ind_id)
            
            if ind_id_obj:
                indicador_doc = db["indicadores"].find_one({"_id": ind_id_obj})
                if indicador_doc:
                    indicador_nome = (
                        indicador_doc.get("nome_legivel") or 
                        indicador_doc.get("nome_indicador") or 
                        indicador_doc.get("nome") or 
                        str(ind_id)
                    )
            
            # Traduzir via nomes_legiveis se aplicável
            nome_legivel_traduzido = nomes_legiveis.get(indicador_nome, indicador_nome)

            linhas.append({
                "Indicador": nome_legivel_traduzido,
                "Valor": lan.get("valor", ""),
                "Ano": lan.get("ano", ""),
            })

        df_indicadores = pd.DataFrame(linhas)
        df_indicadores = df_indicadores[["Indicador", "Valor", "Ano"]]

        df_indicadores["Valor_num"] = df_indicadores["Valor"].apply(parse_valor)

        # Resumo por indicador
        df_resumo = (
            df_indicadores.groupby("Indicador", as_index=False)["Valor_num"]
            .sum(min_count=1)
            .rename(columns={"Valor_num": "Total"})
        )
        df_resumo["Total"] = df_resumo["Total"].fillna("")

        st.write("**Indicadores:**")
        st.dataframe(
            df_indicadores.drop(columns=["Valor_num"], errors="ignore"),
            hide_index=True,
            use_container_width=True
        )

    st.html("<span class='big-dialog'></span>")


def form_projeto(projeto, tipo_projeto, pessoas_dict, programas_dict, projetos_ispn_dict):
    form_key = f"form_projeto_{str(projeto.get('_id', 'novo'))}"
    
    with st.form(key=form_key):

        # --- Detecta se é adicionar ou editar ---
        modo = st.session_state.get("modo_formulario", "adicionar")  # valor padrão

        # Obtemos categorias e moedas únicas a partir das duas coleções
        colecoes_projetos = [db["projetos_pf"], db["projetos_pj"]]
        categorias_set = set()
        moedas_set = set()
        for colecao in colecoes_projetos:
            categorias_set.update(filter(None, [p.get("categoria", "").strip() for p in colecao.find()]))
            moedas_set.update(filter(None, [p.get("moeda", "").strip() for p in colecao.find()]))

        opcoes_categoria = sorted(categorias_set)
        opcoes_moeda = sorted(moedas_set)

        # --- Carrega dados do Mongo ---
        doc_ufs = ufs_municipios.find_one({"ufs": {"$exists": True}})
        doc_municipios = ufs_municipios.find_one({"municipios": {"$exists": True}})

        dados_ufs = doc_ufs.get("ufs", []) if doc_ufs else []
        dados_municipios = doc_municipios.get("municipios", []) if doc_municipios else []

        # Mapas para nome <-> código
        ufs_dict = {uf["nome_uf"].strip(): int(uf["codigo_uf"]) for uf in dados_ufs}
        ufs_codigo_para_nome = {int(uf["codigo_uf"]): uf["nome_uf"].strip() for uf in dados_ufs}

        # Criar mapeamento código -> "Município - UF"
        municipios_codigo_para_label = {
            int(m["codigo_municipio"]): f'{m["nome_municipio"].strip()} - {codigo_uf_para_sigla[str(m["codigo_municipio"])[:2]]}'
            for m in dados_municipios
        }

       # Converte ufs do projeto, que estão salvos como string separada por vírgula, para lista de códigos (int)
        ufs_codigos = []
        ufs_str = projeto.get("ufs", "")
        if isinstance(ufs_str, str):
            ufs_codigos = [int(c.strip()) for c in ufs_str.split(",") if c.strip()]

        ufs_valor_nome = [ufs_codigo_para_nome.get(c) for c in ufs_codigos if c in ufs_codigo_para_nome]

        # municipio_principal do projeto (string), converte para int para buscar label
        municipio_principal_codigo = projeto.get("municipio_principal", None)
        if municipio_principal_codigo is not None:
            try:
                municipio_principal_codigo = int(municipio_principal_codigo)
            except:
                municipio_principal_codigo = None

        # municipios de atuação (string separada por vírgula)
        municipios_codigos = []
        municipios_str = projeto.get("municipios", "")
        if isinstance(municipios_str, str):
            municipios_codigos = [int(c.strip()) for c in municipios_str.split(",") if c.strip()]


        # Campos específicos
        if tipo_projeto == "PF":
            col1, col2, col3, col4, col5 = st.columns(5)
            cpf = col4.text_input("CPF", projeto.get("cpf", ""))
            genero = col5.selectbox("Gênero", ["Masculino", "Feminino", "Outro"], 
                                    index=["Masculino", "Feminino", "Outro"].index(projeto.get("genero", "Masculino")))
        else:
            col1, col2, col3, col4 = st.columns(4)
            cnpj = col4.text_input("CNPJ", projeto.get("cnpj", ""))

        # Campos comuns
        codigo = col1.text_input("Código", projeto.get("codigo", ""))
        sigla = col2.text_input("Sigla", projeto.get("sigla", ""))
        proponente = col3.text_input("Proponente", projeto.get("proponente", ""))

        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        nome_do_projeto = col1.text_input("Nome do projeto", projeto.get("nome_do_projeto", ""))

        categoria_valor = projeto.get("categoria", "")
        categoria = col2.selectbox(
            "Categoria",
            options=opcoes_categoria,
            index=opcoes_categoria.index(categoria_valor) if categoria_valor in opcoes_categoria else 0,
            placeholder=""
        )

        edital = col3.text_input("Edital", projeto.get("edital", ""))
        ano_aprovacao = col4.number_input("Ano de aprovação", value=projeto.get("ano_de_aprovacao", 2025), step=1)

        col1, col2, col3 = st.columns(3)

        # --- Seleção de estados (não afeta municípios) ---
        ufs_selecionados = col1.multiselect(
            "Estado(s)",
            options=sorted(ufs_dict.keys()),
            default=ufs_valor_nome,
            key=f"ufs_{form_key}",
            placeholder=""
        )

        # --- Município principal (todos os municípios) ---
        municipio_principal = col2.selectbox(
            "Município principal",
            options=sorted(municipios_codigo_para_label.keys()),
            format_func=lambda codigo: municipios_codigo_para_label.get(codigo, ""),
            index=sorted(municipios_codigo_para_label.keys()).index(municipio_principal_codigo)
                if municipio_principal_codigo in municipios_codigo_para_label else 0,
            key=f"municipio_principal_{form_key}", 
            placeholder=""
        )

        # --- Municípios de atuação (todos os municípios) ---
        municipios_atuacao = col3.multiselect(
            "Municípios de atuação",
            options=sorted(municipios_codigo_para_label.keys()),
            format_func=lambda codigo: municipios_codigo_para_label.get(codigo, ""),
            default=municipios_codigos,
            key=f"municipios_{form_key}",
            placeholder=""
        )

        col1, col2 = st.columns([1, 4])
        latlong = col1.text_input("Latitude e longitude principais", projeto.get("lat_long_principal", ""))
        local_obs = col2.text_area("Observações sobre o local", projeto.get("observacoes_sobre_o_local", ""))

        

        if modo == "editar":
            col1, col2, col3, col4 = st.columns(4)
            duracao = col1.text_input("Duração original (meses)", projeto.get("duracao_original_meses", ""))
            data_inicio = col2.text_input("Data início do contrato", projeto.get("data_inicio_do_contrato", ""))
            data_fim = col3.text_input("Data fim do contrato", projeto.get("data_final_do_contrato", ""))
            data_relatorio = col4.text_input(
                "Data relatório final",
                projeto.get("data_relatorio_monitoramento_final", "")
            )
        else:
            col1, col2, col3 = st.columns(3)
            duracao = col1.text_input("Duração original (meses)", projeto.get("duracao_original_meses", ""))
            data_inicio = col2.text_input("Data início do contrato", projeto.get("data_inicio_do_contrato", ""))
            data_fim = col3.text_input("Data fim do contrato", projeto.get("data_final_do_contrato", ""))
            data_relatorio = ""

        col1, col2 = st.columns(2)
        moeda_valor = projeto.get("moeda", "")
        moeda = col1.selectbox(
            "Moeda",
            options=opcoes_moeda,
            index=opcoes_moeda.index(moeda_valor) if moeda_valor in opcoes_moeda else 0,
            placeholder=""
        )
        valor = col2.text_input("Valor", projeto.get("valor", ""))

        col1, col2, col3, col4 = st.columns(4)
        opcoes_temas = ["Agroecologia", "Agroextrativismo - Beneficiamento e Comercialização", "Água", "Apicultura e meliponicultura",
            "Artesanato", "Articulação", "Capacitação", "Certificação", "Conservação da biodiversidade", "Criação de animais", "Cultura",
            "Educação Ambiental", "Energia Renovável", "Fauna", "Fogo", "Gestão Territorial", "Manejo da biodiversidade", "Pesquisa",
            "Plantas medicinais", "Política Pública", "Recuperação de áreas degradadas", "Sistemas Agroflorestais - SAFs", "Turismo"
        ]
        opcoes_publico = ["Agricultores Familiares", "Assentados da Reforma Agrária", "Comunidade Tradicional", "Garimpeiros", 
                          "Idosos", "Indígenas", "Jovens", "Mulheres", "Pescador Artesanal", "Quilombola", "Urbano", "Outro" ]
        opcoes_bioma = ["Amazônia", "Caatinga", "Cerrado", "Mata Atlântica", "Pampas", "Pantanal"]
        opcoes_status = ["Em andamento", "Finalizado", "Cancelado"]

        temas_valor = [
            p.strip()
            for p in projeto.get("temas", "").split(",")
            if p.strip() in opcoes_temas
        ]

        publico_valor = [p.strip() for p in projeto.get("publico", "").split(",") if p.strip()]
        bioma_valor = [b.strip() for b in projeto.get("bioma", "").split(",") if b.strip()]
        status_valor = projeto.get("status", opcoes_status[0])

        temas = col1.multiselect("Temas", options=opcoes_temas, default=temas_valor, placeholder="")
        publico = col2.multiselect("Público", options=opcoes_publico, default=publico_valor, placeholder="")
        bioma = col3.multiselect("Bioma", options=opcoes_bioma, default=bioma_valor, placeholder="")
        status = col4.selectbox("Status", options=opcoes_status, index=opcoes_status.index(status_valor) if status_valor in opcoes_status else 0)

        objetivo_geral = st.text_area("Objetivo geral", projeto.get("objetivo_geral", ""))

        col1, col2, col3 = st.columns(3)
        pessoas_options = {str(k): v for k, v in sorted(pessoas_dict.items(), key=lambda item: item[1].lower())}
        ponto_focal_default = str(projeto.get("ponto_focal", ""))
        ponto_focal_keys = list(pessoas_options.keys())
        ponto_focal = col1.selectbox(
            "Ponto focal",
            options=ponto_focal_keys,
            format_func=lambda x: pessoas_options.get(x, ""),
            index=ponto_focal_keys.index(ponto_focal_default) if ponto_focal_default in ponto_focal_keys else 0,
            placeholder=""
        )

        programas_excluidos = {"ADM Brasília", "ADM Santa Inês", "Comunicação", "Advocacy", "Coordenação"}
        programas_filtrados = {
            str(k): v for k, v in programas_dict.items()
            if v not in programas_excluidos and v.strip()
        }
        programas_options = {
            str(k): v for k, v in sorted(programas_filtrados.items(), key=lambda item: item[1].lower())
        }
        programa_default = str(projeto.get("programa", ""))
        programa_keys = list(programas_options.keys())
        programa = col2.selectbox(
            "Programa",
            options=programa_keys,
            format_func=lambda x: programas_options.get(x, ""),
            index=programa_keys.index(programa_default) if programa_default in programa_keys else 0,
            placeholder=""
        )

        projetos_pai_options = {
            str(k): v for k, v in projetos_ispn_dict.items() if v.strip()
        }
        sorted_keys = sorted(projetos_pai_options, key=lambda x: projetos_pai_options[x].lower())
        codigo_pai_default = str(projeto.get("codigo_projeto_pai", ""))
        codigo_pai = col3.selectbox(
            "Projeto pai",
            options=sorted_keys,
            format_func=lambda x: projetos_pai_options.get(x, "Desconhecido"),
            index=sorted_keys.index(codigo_pai_default) if codigo_pai_default in sorted_keys else 0,
            placeholder=""
        )

        submitted = st.form_submit_button("Salvar", icon=":material/save:")
        if submitted:
            doc = {
                "codigo": codigo,
                "sigla": sigla,
                "proponente": proponente,
                "nome_do_projeto": nome_do_projeto,
                "edital": edital,
                "categoria": categoria,
                "ano_de_aprovacao": ano_aprovacao,
                "lat_long_principal": latlong,
                "observacoes_sobre_o_local": local_obs,
                "duracao_original_meses": duracao,
                "data_inicio_do_contrato": data_inicio,
                "data_final_do_contrato": data_fim,
                "data_relatorio_monitoramento_final": data_relatorio,
                "moeda": moeda,
                "valor": valor,
                "bioma": ", ".join(bioma) if isinstance(bioma, list) else str(bioma),
                "status": status,
                "temas": ", ".join(temas) if isinstance(temas, list) else str(temas),
                "publico": ", ".join(publico) if isinstance(publico, list) else str(publico),
                "objetivo_geral": objetivo_geral,
                "tipo": tipo_projeto,
                "ponto_focal": ObjectId(ponto_focal) if ponto_focal and ObjectId.is_valid(ponto_focal) else None,
                "programa": ObjectId(programa) if programa and ObjectId.is_valid(programa) else None,
                "codigo_projeto_pai": ObjectId(codigo_pai) if codigo_pai and ObjectId.is_valid(codigo_pai) else None,
                "ufs": ",".join(str(ufs_dict[nome]) for nome in ufs_selecionados if nome in ufs_dict),
                "municipio_principal": str(municipio_principal) if municipio_principal is not None else "",
                "municipios": ",".join(str(codigo) for codigo in municipios_atuacao),
            }
            if tipo_projeto == "PF":
                doc["cpf"] = cpf
                doc["genero"] = genero
            else:
                doc["cnpj"] = cnpj
            return doc

    return None


@st.dialog("Gerenciar projetos", width="large")
def gerenciar_projetos():

    st.html("<span class='big-dialog'></span>")

    abas = st.tabs(["Adicionar", "Editar", "Excluir"])

    pessoas_dict = {p["_id"]: p.get("nome_completo", "") for p in pessoas.find()}
    programas_dict = {p["_id"]: p.get("nome_programa_area", "") for p in db["programas_areas"].find()}
    projetos_ispn_dict = {p["_id"]: p.get("codigo", "") for p in db["projetos_ispn"].find()}

    # --- Adicionar ---
    with abas[0]:
        st.session_state["modo_formulario"] = "adicionar"
        tipo_projeto = st.pills("Tipo de projeto", ["PF", "PJ"], selection_mode="single", default="PJ")
        colecao = db["projetos_pf"] if tipo_projeto == "PF" else db["projetos_pj"]
        novo = form_projeto({}, tipo_projeto, pessoas_dict, programas_dict, projetos_ispn_dict)
        if novo:
            colecao.insert_one(novo)
            st.success("Projeto adicionado com sucesso.")
            time.sleep(2)
            st.rerun()

    # --- Editar ---
    with abas[1]:
        st.session_state["modo_formulario"] = "editar"
        projetos_pf = list(db["projetos_pf"].find())
        projetos_pj = list(db["projetos_pj"].find())
        todos_projetos = [(p, "PF") for p in projetos_pf] + [(p, "PJ") for p in projetos_pj]

        opcoes = {
            str(proj["_id"]): f"{proj.get('codigo', '')} ({proj.get('sigla', '')})"
            for proj, tipo in todos_projetos
        }

        if not opcoes:
            st.info("Nenhum projeto encontrado para editar.")
        else:
            selecionado_id = st.selectbox("Selecione o projeto", list(opcoes.keys()), format_func=lambda x: opcoes[x])
            tipo = "PF" if selecionado_id in [str(p["_id"]) for p, t in todos_projetos if t == "PF"] else "PJ"
            colecao = db["projetos_pf"] if tipo == "PF" else db["projetos_pj"]
            projeto = colecao.find_one({"_id": ObjectId(selecionado_id)})
            atualizado = form_projeto(projeto, tipo, pessoas_dict, programas_dict, projetos_ispn_dict)
            if atualizado:
                colecao.update_one({"_id": ObjectId(selecionado_id)}, {"$set": atualizado})
                st.success("Projeto atualizado com sucesso.")
                time.sleep(2)
                st.rerun()


    # ---------------------- Excluir ----------------------
    with abas[2]:
        
        # Somente para admin
        if set(st.session_state.tipo_usuario) & {"admin"}:
        

            projetos_pf = list(db["projetos_pf"].find())
            projetos_pj = list(db["projetos_pj"].find())
            todos_projetos = [(p, "PF") for p in projetos_pf] + [(p, "PJ") for p in projetos_pj]

            opcoes = {
                str(proj["_id"]): f"{proj.get('codigo', '')} ({proj.get('sigla', '')})"
                for proj, tipo in todos_projetos
            }

            if not opcoes:
                st.info("Nenhum projeto encontrado para excluir.")
            else:
                selecionado_id = st.selectbox("Selecione o projeto para excluir", list(opcoes.keys()), format_func=lambda x: opcoes[x])
                tipo = "PF" if selecionado_id in [str(p["_id"]) for p, t in todos_projetos if t == "PF"] else "PJ"
                colecao = db["projetos_pf"] if tipo == "PF" else db["projetos_pj"]
                projeto = colecao.find_one({"_id": ObjectId(selecionado_id)})
                if st.button(f"Excluir projeto", icon=":material/delete:"):
                    colecao.delete_one({"_id": ObjectId(selecionado_id)})
                    st.warning("Projeto excluído.")
                    time.sleep(2)
                    st.rerun()
    
    
def extrair_itens_distintos(series: pd.Series) -> pd.Series:
        """
        Recebe uma Series de strings (ex: 'Acre, Rondônia') e retorna uma Series
        'longa' com cada item já limpo, 1 item por linha.
        """
        if series.empty:
            return pd.Series(dtype=str)

        s = (
            series.fillna("")                   # garante string
            .astype(str)
            .str.split(",")                     # divide
            .explode()                          # 1 item por linha
            .str.strip()                        # remove espaços
        )
        # remove vazios e nans textuais
        s = s[(s != "") & (s.str.lower() != "nan")]
        return s
        
                   
def parse_valor(valor):
    """Converte valor string para float, retornando 0.0 se não for possível."""
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        valor = valor.strip()
        if valor == "":
            return 0.0
        # Remover separadores de milhar e converter vírgula decimal para ponto
        valor = valor.replace(".", "").replace(",", ".")
        try:
            return float(valor)
        except ValueError:
            return 0.0
    return 0.0


def normalizar(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


######################################################################################################
# MAIN
######################################################################################################


# Combine os dados
todos_projetos = pj + pf

projetos_por_codigo = {str(p.get("codigo", "")).strip(): p for p in todos_projetos if p.get("codigo") is not None}

dados_municipios = list(ufs_municipios.find())

mapa_nome_doador = {
    str(d["_id"]): d.get("nome_doador", "") for d in colecao_doadores.find()
}

mapa_doador = {}
for proj in projetos_ispn:
    id_proj = str(proj["_id"])
    id_doador = proj.get("doador")
    
    if isinstance(id_doador, ObjectId):
        nome_doador = mapa_nome_doador.get(str(id_doador), "")
        mapa_doador[id_proj] = nome_doador
    else:
        mapa_doador[id_proj] = ""

# Criar dicionário código_uf -> nome_uf
uf_para_nome = {}
for doc in dados_municipios:
    for uf in doc.get("ufs", []):
        uf_para_nome[str(uf["codigo_uf"])] = uf["nome_uf"]

# Criar dicionário de mapeamento código -> nome
codigo_para_nome = {}
for doc in dados_municipios:
    for m in doc.get("municipios", []):
        codigo_para_nome[str(m["codigo_municipio"])] = m["nome_municipio"]
         
for projeto in todos_projetos:
    projeto_pai_id = projeto.get("codigo_projeto_pai")
    if projeto_pai_id:
        projeto["doador"] = mapa_doador.get(str(projeto_pai_id), "")
    else:
        projeto["doador"] = ""


for projeto in todos_projetos:
    valor_bruto = projeto.get("valor")

    if isinstance(valor_bruto, str):
        valor_limpo = valor_bruto.replace(".", "").replace(",", ".")
        try:
            projeto["valor"] = float(valor_limpo)
        except:
            projeto["valor"] = None
    elif isinstance(valor_bruto, (int, float)):
        projeto["valor"] = float(valor_bruto)
    else:
        projeto["valor"] = None


# Transforme em DataFrame
df_projetos = pd.DataFrame(todos_projetos)

# Dicionário de símbolos por moeda
simbolos = {
    "reais": "R$",
    "real": "R$",
    "dólares": "US$",
    "dólar": "US$",
    "euros": "€",  # Incluído para futuro uso
    "euro": "€"
}

# Lista base de colunas obrigatórias
colunas = [
    "codigo",
    "sigla",
    "edital",
    "valor",
    "categoria",
    "ano_de_aprovacao",
    "ufs",
    "municipios",
    "tipo",
    "municipio_principal",
    "cnpj",
    "programa",
    "temas",
    "bioma",
    "publico",
    "genero",
    "status",
    "cpf",
    "proponente",
    "ponto_focal"
]

# Adiciona "doador" se ela estiver presente no DataFrame
if "doador" in df_projetos.columns:
    colunas.insert(3, "doador")  # Mantém a ordem: após "proponente"

# Seleciona apenas as colunas existentes
df_projetos = df_projetos[colunas].rename(columns={
    "codigo": "Código",
    "sigla": "Sigla",
    "edital": "Edital",
    "doador": "Doador",
    "valor": "Valor",
    "categoria": "Categoria",
    "ano_de_aprovacao": "Ano",
    "ufs": "Estado(s)",
    "municipios": "Município(s)",
    "tipo": "Tipo",
    "municipio_principal": "Município Principal",
    "cnpj": "CNPJ",
    "cpf": "CPF",
    "proponente": "Proponente",
    "programa": "Programa",
    "temas": "Temas",
    "publico": "Público",
    "bioma": "Bioma",
    "genero": "Gênero",
    "status": "Status",
    "ponto_focal": "Ponto Focal"
})


# Criar dicionário código_uf -> sigla
codigo_uf_para_sigla = {
    '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
    '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA',
    '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP',
    '41': 'PR', '42': 'SC', '43': 'RS',
    '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'
}


df_projetos_codigos = df_projetos.copy()


# Garantir que todos os campos estão como string
df_projetos = df_projetos.fillna("").astype(str)

# Aplicar a função na coluna 'Municípios'
df_projetos["Município(s)"] = df_projetos["Município(s)"].apply(converter_codigos_para_nomes)
df_projetos["Município Principal"] = df_projetos["Município Principal"].apply(converter_codigos_para_nomes)

# Corrigir a coluna 'Ano' para remover ".0"
df_projetos["Ano"] = df_projetos["Ano"].str.replace(".0", "", regex=False)

df_projetos["Estado(s)"] = [
    converter_uf_codigo_para_nome(proj.get("ufs", "")) for proj in todos_projetos
]

valores_formatados = []
for i, projeto in enumerate(todos_projetos):
    valor = df_projetos.at[i, "Valor"]
    moeda = projeto.get("moeda", "reais").lower()

    
    simbolo = simbolos.get(moeda, "")

    # Limpar o valor original antes da conversão
    valor_limpo = valor.replace("R$", "").replace("US$", "").replace("€", "").replace(" ", "")

    try:
        # Detectar se está no formato brasileiro (vírgula como decimal)
        if "," in valor_limpo and valor_limpo.count(",") == 1 and valor_limpo.count(".") >= 0:
            # Substitui "." por "" (remove separadores de milhar) e "," por "." (converte decimal brasileiro)
            valor_float = float(valor_limpo.replace(".", "").replace(",", "."))

        else:
            valor_float = float(valor_limpo.replace(",", ""))

        valor_formatado = f"{simbolo} {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        valor_formatado = f"{simbolo} {valor}" if valor else ""

    valores_formatados.append(valor_formatado)

df_projetos["Valor"] = valores_formatados

st.header("Fundo Ecos")

st.write('')

with st.expander("Filtros", expanded=False, icon=":material/filter_alt:"):
    df_base = df_projetos.copy()  # nunca mexa no original

    # Começa com máscara True
    mask = pd.Series(True, index=df_base.index)

    # ===== PRIMEIRA LINHA =====
    
    col1, col2 = st.columns([1, 5])
    tipos_disponiveis = ["Projetos PJ", "Projetos PF"]
    tipo_sel = col1.pills("Tipo", tipos_disponiveis, selection_mode="multi")

    if tipo_sel:
        if "Projetos PJ" in tipo_sel and "Projetos PF" not in tipo_sel:
            mask &= (df_base["Tipo"] == "PJ")
        elif "Projetos PF" in tipo_sel and "Projetos PJ" not in tipo_sel:
            mask &= (df_base["Tipo"] == "PF")
            
    # Campo de busca geral
    busca_geral = col2.text_input("Buscar por Sigla, Proponente, CNPJ ou CPF").strip()

    if busca_geral:
        termo = normalizar(busca_geral)
        
        def corresponde(row):
            return (
                termo in normalizar(row["Sigla"]) or
                termo in normalizar(row["Proponente"]) or
                termo in normalizar(row["CNPJ"]) or
                termo in normalizar(row["CPF"])
            )

        mask &= df_base.apply(corresponde, axis=1)
    

    # ===== Segunda Linha =====

    # Dicionários de ID -> Nome
    pessoas_dict = {str(p["_id"]): p["nome_completo"] for p in pessoas.find()}
    programas_dict = {str(p["_id"]): p["nome_programa_area"] for p in programas.find()}

    #st.write(df_base)

    df_base["Ponto Focal"] = df_base["Ponto Focal"].apply(lambda x: pessoas_dict.get(str(x), "Não informado") if pd.notna(x) else "Não informado")
    df_base["Programa"] = df_base["Programa"].apply(lambda x: programas_dict.get(str(x), "Não informado") if pd.notna(x) else "Não informado")

    col1, col2, col3, col4 = st.columns(4)

    # Filtro Categoria
    categoria_disponiveis = sorted(df_base["Categoria"].dropna().unique())
    categoria_sel = col1.multiselect("Categoria", options=categoria_disponiveis, placeholder="Todos")
    if categoria_sel:
        mask &= df_base["Categoria"].isin(categoria_sel)

    # Filtro Ponto Focal
    ponto_focal_disponiveis = sorted(df_base["Ponto Focal"].dropna().unique())
    ponto_focal_sel = col2.multiselect("Ponto Focal", options=ponto_focal_disponiveis, placeholder="Todos")
    if ponto_focal_sel:
        mask &= df_base["Ponto Focal"].isin(ponto_focal_sel)

    # Filtro Programa
    programa_disponiveis = sorted(df_base["Programa"].dropna().unique())
    programa_sel = col3.multiselect("Programa", options=programa_disponiveis, placeholder="Todos")
    if programa_sel:
        mask &= df_base["Programa"].isin(programa_sel)

    # Filtro Gênero
    genero_disponiveis = sorted(df_base["Gênero"].dropna().unique())
    genero_sel = col4.multiselect("Gênero", options=genero_disponiveis, placeholder="Todos")
    if genero_sel:
        mask &= df_base["Gênero"].isin(genero_sel)
        
    # ===== Terceira Linha =====

    col1, col2, col3, col4 = st.columns(4)

    # Edital
    editais_disponiveis = sorted(df_base["Edital"].dropna().unique(), key=lambda x: float(x))
    edital_sel = col1.multiselect("Edital", options=editais_disponiveis, placeholder="Todos")
    if edital_sel:
        mask &= df_base["Edital"].isin(edital_sel)

    # Ano
    anos_disponiveis = sorted(df_base["Ano"].dropna().unique())
    ano_sel = col2.multiselect("Ano", options=anos_disponiveis, placeholder="Todos")
    if ano_sel:
        mask &= df_base["Ano"].isin(ano_sel)

    # Doador
    doadores_disponiveis = sorted(df_base["Doador"].dropna().unique())
    doador_sel = col3.multiselect("Doador", options=doadores_disponiveis, placeholder="Todos")
    if doador_sel:
        mask &= df_base["Doador"].isin(doador_sel)

    # Código
    codigos_disponiveis = sorted(df_base["Código"].dropna().unique())
    codigo_sel = col4.multiselect("Código", options=codigos_disponiveis, placeholder="Todos")
    if codigo_sel:
        mask &= df_base["Código"].isin(codigo_sel)

    # ===== Quarta Linha =====

    col1, col2, col3, col4 = st.columns(4)

    temas_disponiveis = sorted(
        df_base["Temas"]
        .dropna()
        .apply(lambda x: [m.strip() for m in x.split(",")])
        .explode()
        .unique(),
        key=normalizar
    )

    temas_sel = col1.multiselect("Temas", options=temas_disponiveis, placeholder="Todos")
    if temas_sel:
        mask &= df_base["Temas"].apply(
            lambda x: any(m.strip() in temas_sel for m in x.split(",")) if isinstance(x, str) else False
        )

    publicos_disponiveis = sorted(
        df_base["Público"]
        .dropna()
        .apply(lambda x: [m.strip() for m in x.split(",")])
        .explode()
        .unique(),
        key=normalizar
    )

    publicos_sel = col2.multiselect("Público", options=publicos_disponiveis, placeholder="Todos")
    if publicos_sel:
        mask &= df_base["Público"].apply(
            lambda x: any(m.strip() in publicos_sel for m in x.split(",")) if isinstance(x, str) else False
        )

    biomas_disponiveis = sorted(
        df_base["Bioma"]
        .dropna()
        .apply(lambda x: [m.strip() for m in x.split(",")])
        .explode()
        .unique(),
        key=normalizar
    )

    biomas_sel = col3.multiselect("Bioma", options=biomas_disponiveis, placeholder="Todos")
    if biomas_sel:
        mask &= df_base["Bioma"].apply(
            lambda x: any(m.strip() in biomas_sel for m in x.split(",")) if isinstance(x, str) else False
        )

    status_disponiveis = sorted(df_base["Status"].dropna().unique())
    status_sel = col4.multiselect("Status", options=status_disponiveis, placeholder="Todos")
    if status_sel:
        mask &= df_base["Status"].isin(status_sel)


    # ===== Quinta Linha =====
    
    col5, col6 = st.columns(2)

    # Estado
    estados_unicos = sorted(
        df_base["Estado(s)"].dropna().apply(lambda x: [m.strip() for m in x.split(",")]).explode().unique()
    )
    uf_sel = col5.multiselect("Estado(s)", options=estados_unicos, placeholder="Todos")
    if uf_sel:
        mask &= df_base["Estado(s)"].apply(
            lambda x: any(m.strip() in uf_sel for m in x.split(",")) if isinstance(x, str) else False
        )

    # Município
    municipios_unicos = sorted(
        df_base["Município(s)"].dropna().apply(lambda x: [m.strip() for m in x.split(",")]).explode().unique()
    )
    municipio_sel = col6.multiselect("Município(s)", options=municipios_unicos, placeholder="Todos")
    if municipio_sel:
        mask &= df_base["Município(s)"].apply(
            lambda x: any(m.strip() in municipio_sel for m in x.split(",")) if isinstance(x, str) else False
        )

    # Aplica filtro UMA vez e gera cópia segura
    df_filtrado = df_base.loc[mask].copy()

    if df_filtrado.empty:
        st.warning("Nenhum projeto encontrado")

# Salva no session_state para o diálogo de detalhes
st.session_state["df_filtrado"] = df_filtrado

geral, lista, mapa = st.tabs(["Visão geral", "Projetos", "Mapa"])

with geral:
    
    # Separar projetos PF e PJ
    df_pf = df_filtrado[df_filtrado['Tipo'] == 'PF']
    df_pj = df_filtrado[df_filtrado['Tipo'] == 'PJ']


    total_projetos_pf = len(df_pf)
    total_projetos_pj = len(df_pj)
    total_projetos = len(df_filtrado)

    estados_series = extrair_itens_distintos(df_filtrado["Estado(s)"])
    total_ufs = estados_series.nunique()

    municipios_series = extrair_itens_distintos(df_filtrado["Município(s)"])
    total_municipios = municipios_series.nunique()

    # Total de editais únicos (remover vazios)
    total_editais = df_filtrado["Edital"].replace("", pd.NA).dropna().nunique()

    # Total de doadores únicos (remover vazios)
    total_doador = df_filtrado["Doador"].replace("", pd.NA).dropna().nunique()

    # Apresentar em colunas organizadas
    col1, col2, col3 = st.columns(3)
    
    # Contar CNPJs únicos (organizações apoiadas)
    total_organizacoes = df_pj["CNPJ"].replace("", pd.NA).dropna().nunique()

    col1.metric("Editais", f"{total_editais}")
    col1.metric("Doadores", f"{total_doador}")
    col1.metric("Organizações apoiadas", f"{total_organizacoes}")

    
    col2.metric("Total de apoios", f"{total_projetos}")
    col2.metric("Apoios a Pessoa Jurídica", f"{total_projetos_pj}")
    col2.metric("Apoios a Pessoa Física", f"{total_projetos_pf}")
    

    col3.metric("Estados", f"{total_ufs}")
    col3.metric("Municípios", f"{total_municipios}")

    st.divider()

    # Inicializar acumuladores
    valor_total_dolar_corrigido = 0.0
    valor_nominal_dolar = 0.0
    valor_nominal_real = 0.0

    # Criar set de códigos filtrados
    codigos_filtrados = set(df_filtrado["Código"].astype(str).str.strip())

    # Filtrar apenas os projetos que estão em df_filtrado
    projetos_filtrados = [p for p in todos_projetos if str(p.get("codigo", "")).strip() in codigos_filtrados]

    # Inicializar acumuladores
    valor_total_dolar_corrigido = 0.0
    valor_nominal_dolar = 0.0
    valor_nominal_real = 0.0

    for projeto in projetos_filtrados:
        moeda = str(projeto.get("moeda", "")).strip().lower()

        # Valor nominal em US$ (sem correção)
        valor_dolar_original = projeto.get("valor_dolar_original")
        if valor_dolar_original is None or valor_dolar_original == "":
            if moeda in ("dólar"):
                valor_dolar_original = projeto.get("valor", 0)
            else:
                valor_dolar_original = 0
        valor_nominal_dolar += parse_valor(valor_dolar_original)

        # Valor atualizado em US$ (corrigido até 2024)
        valor_dolar_atualizado = projeto.get("valor_dolar_atualizado", 0)
        valor_total_dolar_corrigido += parse_valor(valor_dolar_atualizado)

        # Valor nominal em R$ (somente para projetos em real)
        if moeda in ("real"):
            valor_nominal_real += parse_valor(projeto.get("valor", 0))



    # Exibição das métricas
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Valor total em US$ corrigido até 2024",
        f"{valor_total_dolar_corrigido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    col2.metric(
        "Valor nominal dos contratos em US$",
        f"{valor_nominal_dolar:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    col3.metric(
        "Valor nominal dos contratos em R$",
        f"{valor_nominal_real:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )


    st.write("")
    st.write("")
 
    # Gráfico  

    # Garantir que os campos são string
    df_filtrado["Ano"] = df_filtrado["Ano"].astype(str)
    df_filtrado["Doador"] = df_filtrado["Doador"].astype(str)

    # Agrupamento dos apoios existentes
    dados = (
        df_filtrado
        .groupby(["Ano", "Doador"])
        .size()
        .reset_index(name="apoios")
    )
    
    if df_filtrado.empty:
        anos_todos = []  # garante variável existente
    else:
        try:
            anos_min = pd.to_numeric(df_filtrado["Ano"], errors="coerce").min()
            anos_max = pd.to_numeric(df_filtrado["Ano"], errors="coerce").max()

            if pd.notna(anos_min) and pd.notna(anos_max):
                anos_todos = list(map(str, range(int(anos_min), int(anos_max) + 1)))
            else:
                anos_todos = []
        except Exception as e:
            st.error(f"Erro ao calcular anos disponíveis: {e}")
            anos_todos = []

    # Preencher com 0 onde não há apoio (para doadores já existentes)
    doadores = dados["Doador"].unique()
    todos_anos_doador = pd.MultiIndex.from_product([anos_todos, doadores], names=["Ano", "Doador"])
    dados_completos = dados.set_index(["Ano", "Doador"]).reindex(todos_anos_doador, fill_value=0).reset_index()

    # Paleta com mais cores distintas (exemplo: 'Plotly', 'Viridis', 'Turbo', ou personalizada)
    # paleta_cores = px.colors.diverging.Spectral
    from plotly.colors import diverging, sequential
    paleta_cores = diverging.Spectral_r[::2] + diverging.curl[::2]
    paleta_cores = paleta_cores[:15]  # garante 15 cores únicas
    
    # Criar gráfico
    fig = px.bar(
        dados_completos,
        x="Ano",
        y="apoios",
        color="Doador",
        color_discrete_sequence=paleta_cores,
        barmode="stack",
        title="Número de apoios por doador e ano",
        labels={"apoios": "Número de apoios", "Ano": ""},
        height=600,
        category_orders={"Ano": anos_todos}  # ordem cronológica
    )

    # Estética
    fig.update_layout(
        xaxis_tickangle=-45,
        xaxis=dict(type='category'),
        legend_font_size=17,
        bargap=0.1,         # espaço entre anos
        bargroupgap=0.05,   # barras mais grossas
        margin=dict(t=60, b=60, l=40, r=10)
    )

    # fig.update_traces(
    #     marker_pattern_shape=["", "/", "\\", "x", "-", "|", "."],
    # )


    # Mostrar
    st.plotly_chart(fig, use_container_width=True)


with lista:
    st.write("")

    if set(st.session_state.tipo_usuario) & {"admin", "gestao_fundo_ecos"}:

        st.button("Gerenciar projetos", on_click=gerenciar_projetos, icon=":material/contract_edit:")

    # --- Ordenar Ano desc, Código asc ---
    df_exibir = (
        st.session_state["df_filtrado"]
        .copy()
        .sort_values(by=["Ano", "Código"], ascending=[False, True])
        .reset_index(drop=True)
    )

    # --- Paginação ---
    itens_por_pagina = 50
    total_linhas = len(df_exibir)
    total_paginas = max(math.ceil(total_linhas / itens_por_pagina), 1)

    # --- Inicializar paginação no session_state ---
    if "pagina_atual" not in st.session_state:
        st.session_state["pagina_atual"] = 1
    if "pagina_topo" not in st.session_state:
        st.session_state["pagina_topo"] = st.session_state["pagina_atual"]
    if "pagina_rodape" not in st.session_state:
        st.session_state["pagina_rodape"] = st.session_state["pagina_atual"]

    # --- Funções de callback para sincronização ---
    def atualizar_topo():
        st.session_state["pagina_atual"] = st.session_state["pagina_topo"]
        st.session_state["pagina_rodape"] = st.session_state["pagina_topo"]

    def atualizar_rodape():
        st.session_state["pagina_atual"] = st.session_state["pagina_rodape"]
        st.session_state["pagina_topo"] = st.session_state["pagina_rodape"]

    # --- Controle topo ---
    col1, col2, col3 = st.columns([5,2,1])

    col3.number_input(
        "Página",
        min_value=1,
        max_value=total_paginas,
        value=st.session_state["pagina_topo"],
        step=1,
        key="pagina_topo",
        on_change=atualizar_topo
    )

    # --- Definir intervalo de linhas ---
    inicio = (st.session_state["pagina_atual"] - 1) * itens_por_pagina
    fim = inicio + itens_por_pagina
    df_paginado = df_exibir.iloc[inicio:fim]



    # --- Informação de contagem ---
    with col2:
        st.write("")
        st.write(f"**Mostrando {inicio + 1} a {min(fim, total_linhas)} de {total_linhas} projetos**")
        st.write("")
        st.write("")

    # --- Layout da tabela customizada ---
    # colunas_visiveis = [c for c in df_exibir.columns]  # personalizar se quiser excluir colunas
    colunas_visiveis = [c for c in df_exibir.columns if c not in ["Tipo", "Município Principal", "CNPJ", "CPF", "Proponente", "Programa", "Temas", "Público", "Bioma", "Gênero", "Status", "Ponto Focal"]]

    headers = colunas_visiveis + ["Detalhes"]

    col_sizes = [2, 2, 1, 2, 2, 2, 1, 2, 3, 3]  

    header_cols = st.columns(col_sizes)
    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.divider()

    for _, row in df_paginado.iterrows():
        cols = st.columns(col_sizes)
        for j, key in enumerate(colunas_visiveis):
            cols[j].write(row[key])

        codigo_proj = str(row["Código"]).strip()
        cols[-1].button(
            "Detalhes",
            key=f"ver_{codigo_proj}",
            on_click=mostrar_detalhes,
            args=(codigo_proj,),
            icon=":material/menu:"
        )
        st.divider()

    # --- Controle rodapé ---
    col1, col2, col3 = st.columns([5,2,1])

    # --- Informação de contagem ---
    with col2:
        st.write("")
        st.write(f"**Mostrando {inicio + 1} a {min(fim, total_linhas)} de {total_linhas} projetos**")
        st.write("")
        st.write("")

    col3.number_input(
        "Página",
        min_value=1,
        max_value=total_paginas,
        value=st.session_state["pagina_rodape"],
        step=1,
        key="pagina_rodape",
        on_change=atualizar_rodape
    )
























    # # Ordenar Ano desc, Código asc
    # df_exibir = (
    #     st.session_state["df_filtrado"]
    #     .copy()
    #     .sort_values(by=["Ano", "Código"], ascending=[True, True])
    #     .reset_index(drop=True)
    # )

    # # Paginação
    # itens_por_pagina = 50
    # total_linhas = len(df_exibir)
    # total_paginas = max(math.ceil(total_linhas / itens_por_pagina), 1)

    # # Controle de paginas
    # col1, col2, col3 = st.columns([5, 1, 1])
    # pagina_atual = col3.number_input(
    #     "Página",
    #     min_value=1, max_value=total_paginas, value=1, step=1,
    #     key="pagina_projetos"
    # )

    # inicio = (pagina_atual - 1) * itens_por_pagina
    # fim = inicio + itens_por_pagina
    # df_paginado = df_exibir.iloc[inicio:fim]

    # with col1:
    #     st.write("")
    #     st.subheader(f"Mostrando {inicio + 1} a {min(fim, total_linhas)} de {total_linhas} projetos")
    #     st.write("")
    #     st.write("")

    # st.write("")

    # colunas_visiveis = [c for c in df_exibir.columns if c not in ["Tipo", "Município Principal", "CNPJ", "CPF", "Proponente", "Programa", "Temas", "Público", "Bioma", "Gênero", "Status", "Ponto Focal"]]
    # headers = colunas_visiveis + ["Detalhes"]

    # col_sizes = [2, 2, 1, 2, 2, 2, 1, 2, 3, 3]  # ajuste se necessário
    # header_cols = st.columns(col_sizes)
    # for col, header in zip(header_cols, headers):
    #     col.markdown(f"**{header}**")

    # st.divider()

    # for _, row in df_paginado.iterrows():
    #     cols = st.columns(col_sizes)
    #     for j, key in enumerate(colunas_visiveis):
    #         cols[j].write(row[key])

    #     codigo_proj = str(row["Código"]).strip()
    #     cols[-1].button(
    #         "Detalhes",
    #         key=f"ver_{codigo_proj}",
    #         on_click=mostrar_detalhes,
    #         args=(codigo_proj,),
    #         icon=":material/menu:"
    #     )
    #     st.divider()

    # col1, col2, col3 = st.columns([5, 1, 1])
    # pagina_atual = col3.number_input(
    #     "Página",
    #     min_value=1, max_value=total_paginas, value=1, step=1,
    #     key="pagina_projetos_embaixo"
    # )


with mapa:
    st.subheader("Mapa de distribuição de projetos")

    @st.cache_data
    def carregar_municipios():
        url = "https://raw.githubusercontent.com/kelvins/Municipios-Brasileiros/master/csv/municipios.csv"
        df = pd.read_csv(url)
        df.rename(columns={'codigo_ibge': 'codigo_municipio'}, inplace=True)
        df['codigo_municipio'] = df['codigo_municipio'].astype(str)
        return df

    df_munis = carregar_municipios()

    @st.cache_data
    def preparar_df_coords(df_projetos_codigos, df_filtrado, df_munis):
        # Extrair código do município
        df_projetos_codigos['codigo_municipio'] = [
            m.split(",")[0].strip() if m else "" 
            for m in df_projetos_codigos['Município Principal']
        ]

        # Filtrar
        df_filtrado_proj = df_projetos_codigos[df_projetos_codigos["Código"].isin(df_filtrado["Código"])].copy()
        df_filtrado_proj['codigo_municipio'] = df_filtrado_proj['Município Principal'].astype(str)
        df_filtrado_proj['Ano'] = df_filtrado_proj['Ano'].astype(str).str.replace(".0", "", regex=False)

        # Merge para coordenadas
        df_coords = df_filtrado_proj.merge(
            df_munis,
            left_on='codigo_municipio',
            right_on='codigo_municipio',
            how='left'
        ).dropna(subset=['latitude', 'longitude']).drop_duplicates(subset='Código')

        return df_coords
    
    @st.cache_data
    def carregar_pontos_focais(_projetos):
        ids = [p["ponto_focal"] for p in _projetos if isinstance(p.get("ponto_focal"), ObjectId)]
        if not ids:
            return {}

        pessoas = list(db["pessoas"].find(
            {"_id": {"$in": ids}},
            {"_id": 1, "nome_completo": 1}
        ))

        return {p["_id"]: p.get("nome_completo", "Não encontrado") for p in pessoas}


    df_coords_projetos = preparar_df_coords(df_projetos_codigos, df_filtrado, df_munis)
    num_proj_mapa = len(df_coords_projetos)
    pontos_focais_dict = carregar_pontos_focais(todos_projetos)
    st.write(f"{num_proj_mapa} projetos no mapa")

    @st.cache_data
    def gerar_mapa(df_coords_projetos, _todos_projetos, df_munis):
        
        m = folium.Map(location=[-15.78, -47.93], zoom_start=4, tiles="CartoDB positron", height="800px")
        cluster = MarkerCluster().add_to(m)

        for _, row in df_coords_projetos.iterrows():
            lat, lon = row['latitude'], row['longitude']
            codigo = row['Código']
            ano_de_aprovacao = row['Ano']

            projeto = next((p for p in todos_projetos if p.get("codigo") == codigo), None)
            if not projeto:
                continue

            proponente = projeto.get("proponente", "")
            nome_proj = projeto.get("nome_do_projeto", "")
            tipo_do_projeto = projeto.get("tipo")
            categoria = projeto.get("categoria")
            sigla = projeto.get("sigla")
            edital = projeto.get("edital")

            # Ponto focal
            ponto_focal_obj = projeto.get("ponto_focal")
            nome_ponto_focal = pontos_focais_dict.get(ponto_focal_obj, "Não informado")

            # Município principal
            muni_principal_codigo = str(row.get('codigo_municipio', '')).strip()
            muni_principal_info = df_munis[df_munis['codigo_municipio'] == muni_principal_codigo]
            if not muni_principal_info.empty:
                nome_muni_principal = muni_principal_info.iloc[0]['nome'].title()
                uf_sigla_principal = codigo_uf_para_sigla.get(str(int(muni_principal_info.iloc[0]['codigo_uf'])), "")
                muni_principal_str = f"{nome_muni_principal} - {uf_sigla_principal}"
            else:
                muni_principal_str = "Não informado"

            # Demais municípios
            codigos_municipios_projeto = [c.strip() for c in str(row.get('Município(s)', '')).split(',') if c.strip()]
            demais_municipios = []
            for cod in codigos_municipios_projeto:
                if cod == muni_principal_codigo:
                    continue
                muni_info = df_munis[df_munis['codigo_municipio'] == cod]
                if not muni_info.empty:
                    nome_muni = muni_info.iloc[0]['nome'].title()
                    uf_sigla = codigo_uf_para_sigla.get(str(int(muni_info.iloc[0]['codigo_uf'])), "")
                    demais_municipios.append(f"{nome_muni} - {uf_sigla}")
            demais_municipios_html = "<br>".join(demais_municipios) if demais_municipios else "Nenhum"

            popup_html = f"""
                <b>Proponente:</b> {proponente}<br>
                <b>Projeto:</b> {nome_proj}<br><br>
                <b>Código:</b> {codigo}<br>
                <b>Sigla:</b> {sigla}<br>
                <b>Ano:</b> {ano_de_aprovacao}<br>
                <b>Edital:</b> {edital}<br>
                <b>Ponto Focal:</b> {nome_ponto_focal}<br>
                <b>{tipo_do_projeto} - {categoria}</b><br><br>
                <b>Município principal:</b> {muni_principal_str}<br>
                <b>Outros municípios:</b><br>
                {demais_municipios_html}
            """

            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=400)
            ).add_to(cluster)

        return m

    mapa_folium = gerar_mapa(df_coords_projetos, todos_projetos, df_munis)
    st_folium(mapa_folium, width=None, height=800, returned_objects=[])