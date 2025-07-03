import streamlit as st
import pandas as pd
from bson import ObjectId
from funcoes_auxiliares import conectar_mongo_portal_ispn


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
projetos_pj = db["projetos_pj"]
projetos_pf = db["projetos_pf"]
projetos_ispn = db["projetos_ispn"]
indicadores = db["indicadores"]
lancamentos = db["lancamentos_indicadores"]


######################################################################################################
# FUNÇÕES
######################################################################################################


def formatar_brasileiro(valor):
    try:
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip('0').rstrip(',')
    except:
        return valor


def somar_indicador_por_nome(nome_indicador, tipo_selecionado=None, projetos_filtrados=None, anos_filtrados=None, autores_filtrados=None):
    indicador_doc = indicadores.find_one({"nome_indicador": nome_indicador})
    if not indicador_doc:
        return "0"
    indicador_id = indicador_doc["_id"]

    filtro = {"id_do_indicador": indicador_id}
    if tipo_selecionado:
        filtro["tipo"] = tipo_selecionado
    if projetos_filtrados:
        filtro["projeto"] = {"$in": projetos_filtrados}
    if anos_filtrados:
        filtro["ano"] = {"$in": anos_filtrados}
    if autores_filtrados:
        filtro["autor_anotacao"] = {"$in": autores_filtrados}

    total = 0
    for doc in lancamentos.find(filtro):
        valor = doc.get("valor", "")
        try:
            if isinstance(valor, (int, float)):
                total += valor
            elif isinstance(valor, str) and valor.strip() != "":
                total += float(valor.replace(".", "").replace(",", "."))
        except ValueError:
            pass

    if total == 0:
        return "0"
    return formatar_brasileiro(total)


@st.dialog("Lançamentos", width="large")
def mostrar_detalhes(nome_indicador, tipo_selecionado=None, projetos_filtrados=None, anos_filtrados=None, autores_filtrados=None):
    indicador_doc = indicadores.find_one({"nome_indicador": nome_indicador})
    if not indicador_doc:
        st.warning("Indicador não encontrado.")
        return

    st.subheader(f"{formatar_nome_legivel(nome_indicador)}")

    indicador_id = indicador_doc["_id"]

    filtro = {"id_do_indicador": indicador_id}
    if tipo_selecionado:
        filtro["tipo"] = tipo_selecionado
    if projetos_filtrados:
        filtro["projeto"] = {"$in": projetos_filtrados}
    if anos_filtrados:
        filtro["ano"] = {"$in": anos_filtrados}
    if autores_filtrados:
        filtro["autor_anotacao"] = {"$in": autores_filtrados}

    lancs = list(lancamentos.find(filtro))
    if not lancs:
        st.info("Nenhum lançamento encontrado para este indicador.")
        return

    df = pd.DataFrame(lancs)

    # Renomear colunas para exibição
    colunas_mapeadas = {
        "projeto": "Projeto",
        "ano": "Ano",
        "valor": "Valor",
        "autor_anotacao": "Autor",
        "data_anotacao": "Data da Anotação",
        "observacoes": "Observações"
    }

    for col in colunas_mapeadas.keys():
        if col not in df.columns:
            df[col] = ""

    df.rename(columns=colunas_mapeadas, inplace=True)

    # Converter para ObjectId apenas se ainda não for
    df["Projeto"] = df["Projeto"].astype(str).map(id_para_codigo).fillna("Sem código")

    df["Observações"] = df["Observações"].fillna("")

    # Reordenar as colunas e ordenar pelo código do projeto
    df = df[list(colunas_mapeadas.values())].sort_values("Projeto")

    st.dataframe(df[list(colunas_mapeadas.values())], hide_index=True, use_container_width=True)


def handler(nome_indicador, projetos_filtrados=None, anos_filtrados=None):
    def _handler():
        mostrar_detalhes(nome_indicador, projetos_filtrados, anos_filtrados)
    return _handler


def formatar_nome_legivel(nome):
    
    NOMES_INDICADORES_LEGIVEIS = {
        "numero_de_organizacoes_apoiadas": "Número de organizações apoiadas",
        "numero_de_comunidades_fortalecidas": "Número de comunidades fortalecidas",
        "numero_de_familias": "Número de famílias",
        "numero_de_homens_jovens": "Número de homens jovens (até 29 anos)",
        "numero_de_homens_adultos": "Número de homens adultos",
        "numero_de_mulheres_jovens": "Número de mulheres jovens (até 29 anos)",
        "numero_de_mulheres_adultas": "Número de mulheres adultas",
        "numero_de_indigenas": "Número de indígenas",
        "numero_de_liderancas_comunitarias_fortalecidas": "Número de lideranças comunitárias fortalecidas",
        "numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_fundo_ecos": "Número de famílias comercializando produtos da sociobio com apoio do Fundo Ecos",
        "numero_de_familias_acessando_vendas_institucionais_com_apoio_do_fundo_ecos": "Número de famílias acessando vendas institucionais com apoio do Fundo Ecos",
        "numero_de_estudantes_recebendo_bolsa": "Número de estudantes recebendo bolsa",
        "numero_de_capacitacoes_realizadas": "Número de capacitações realizadas",
        "numero_de_homens_jovens_capacitados": "Número de homens jovens capacitados (até 29 anos)",
        "numero_de_homens_adultos_capacitados": "Número de homens adultos capacitados",
        "numero_de_mulheres_jovens_capacitadas": "Número de mulheres jovens capacitadas (até 29 anos)",
        "numero_de_mulheres_adultas_capacitadas": "Número de mulheres adultas capacitadas",
        "numero_de_intercambios_realizados": "Número de intercâmbios realizados",
        "numero_de_homens_em_intercambios": "Número de homens em intercâmbios",
        "numero_de_mulheres_em_intercambios": "Número de mulheres em intercâmbios",
        "numero_de_iniciativas_de_gestao_territorial_implantadas": "Número de iniciativas de Gestão Territorial implantadas",
        "area_com_manejo_ecologico_do_fogo_ha": "Área com manejo ecológico do fogo (ha)",
        "area_com_manejo_agroecologico_ha": "Área com manejo agroecológico (ha)",
        "area_com_manejo_para_restauracao_ha": "Área com manejo para restauração (ha)",
        "area_com_manejo_para_extrativismo_ha": "Área com manejo para extrativismo (ha)",
        "numero_de_agroindustiras_implementadas_ou_reformadas": "Número de agroindústrias implementadas/reformadas",
        "numero_de_tecnologias_instaladas": "Número de tecnologias instaladas",
        "numero_de_pessoas_beneficiadas_com_tecnologias": "Número de pessoas beneficiadas com tecnologias",
        "numero_de_videos_produzidos": "Número de vídeos produzidos",
        "numero_de_aparicoes_na_midia": "Número de aparições na mídia",
        "numero_de_publicacoes_de_carater_tecnico": "Número de publicações de caráter técnico",
        "numero_de_artigos_academicos_produzidos_e_publicados": "Número de artigos acadêmicos produzidos e publicados",
        "numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn": "Número de comunicadores comunitários contribuindo na execução das ações do ISPN",
        "faturamento_bruto_anual_pre_projeto": "Faturamento bruto anual pré-projeto",
        "faturamento_bruto_anual_pos_projeto": "Faturamento bruto anual pós-projeto",
        "volume_financeiro_de_vendas_institucionais_com_apoio_do_fundo_ecos": "Volume financeiro de vendas institucionais com apoio do Fundo Ecos",
        "numero_de_visitas_de_monitoramento_realizadas_ao_projeto_apoiado": "Número de visitas de monitoramento realizadas ao projeto apoiado",
        "valor_da_contrapartida_financeira_projetinhos": "Valor da contrapartida financeira projetinhos",
        "valor_da_contrapartida_nao_financeira_projetinhos": "Valor da contrapartida não financeira projetinhos",
        "especies": "Espécies",
        "numero_de_organizacoes_apoiadas_que_alavancaram_recursos": "Número de organizações apoiadas que alavancaram recursos",
        "valor_mobilizado_de_novos_recursos": "Valor mobilizado de novos recursos",
        "numero_de_politicas_publicas_monitoradas_pelo_ispn": "Número de políticas públicas monitoradas pelo ISPN",
        "numero_de_proposicoes_legislativas_acompanhadas_pelo_ispn": "Número de proposições legislativas acompanhadas pelo ISPN",
        "numero_de_contribuicoes_notas_tecnicas_participacoes_e_ou_documentos_que_apoiam_a_construcao_e_aprimoramento_de_politicas_publicas": "Número de contribuições (notas técnicas, participações e/ou documentos) que apoiam a construção e aprimoramento de políticas públicas"
    }
    
    return NOMES_INDICADORES_LEGIVEIS.get(nome, nome.replace("_", " ").capitalize())


# Função para aplicar filtros progressivamente
def atualizar_opcoes(df, campo, campos_restritivos):
    df_filtrado = df.copy()
    for outro_campo, valores in campos_restritivos.items():
        if outro_campo != campo and valores:
            df_filtrado = df_filtrado[df_filtrado[outro_campo].isin(valores)]
    return sorted(df_filtrado[campo].dropna().unique().tolist())


######################################################################################################
# MAIN
######################################################################################################


st.header("Indicadores")
st.write('')


# ===== FILTROS =====


tipo_selecionado = st.pills(
    label="Tipo de projeto",
    options=["fundo_ecos", "ispn"],
    format_func=lambda x: "Fundo Ecos" if x == "fundo_ecos" else "ISPN",
    default="fundo_ecos"
)


# Cria dicionário id_string ➔ codigo
id_para_codigo = {}

# Adiciona projetos ISPN
for proj in projetos_ispn.find({}, {"_id": 1, "codigo": 1}):
    id_para_codigo[str(proj["_id"])] = proj.get("codigo", "Sem código")

# Adiciona projetos PF
for proj in projetos_pf.find({}, {"_id": 1, "codigo": 1}):
    id_para_codigo[str(proj["_id"])] = proj.get("codigo", "Sem código")

# Adiciona projetos PJ
for proj in projetos_pj.find({}, {"_id": 1, "codigo": 1}):
    id_para_codigo[str(proj["_id"])] = proj.get("codigo", "Sem código")

# Carregar lançamentos
todos_lancamentos = list(lancamentos.find())
df_base = pd.DataFrame(todos_lancamentos)

if tipo_selecionado:
    df_base = df_base[df_base["tipo"] == tipo_selecionado]

# Criar coluna 'codigo' baseada no mapeamento
df_base["codigo"] = df_base["projeto"].astype(str).map(id_para_codigo)


# Inicialização com todas as opções possíveis
projetos_unicos = sorted(df_base["codigo"].dropna().unique().tolist())

anos_unicos = sorted(df_base["ano"].dropna().unique().tolist())
autores_unicos = sorted(df_base["autor_anotacao"].dropna().unique().tolist())

# Colunas dos filtros
col1, col2, col3 = st.columns(3)

# Filtro de autor primeiro
with col3:
    filtro_autor = st.multiselect("Filtrar por autor", autores_unicos, placeholder="")

# Filtrar base por autor (se houver)
df_filtrada_autor = df_base.copy()
if filtro_autor:
    df_filtrada_autor = df_base[df_base["autor_anotacao"].isin(filtro_autor)]

# Filtro de projeto com base nos autores
with col1:
    projetos_filtrados = sorted([str(x) for x in df_filtrada_autor["codigo"].dropna().unique().tolist()])

    filtro_projeto = st.multiselect("Filtrar por projeto", projetos_unicos, placeholder="")

# Filtrar base por autor + projeto (se houver)
df_filtrada_projeto = df_filtrada_autor.copy()
if filtro_projeto:
    df_filtrada_projeto = df_filtrada_autor[df_filtrada_autor["codigo"].isin(filtro_projeto)]

# Filtro de ano com base nos filtros anteriores
with col2:
    anos_filtrados = sorted(df_filtrada_projeto["ano"].dropna().unique().tolist())
    filtro_ano = st.multiselect("Filtrar por ano", anos_filtrados, placeholder="")

# Base final com todos os filtros aplicados
df_filtrado_final = df_base.copy()
if filtro_autor:
    df_filtrado_final = df_filtrado_final[df_filtrado_final["autor_anotacao"].isin(filtro_autor)]

# Converter códigos selecionados para _id utilizados no MongoDB
if filtro_projeto:
    projetos_filtrados_ids = [ObjectId(k) for k, v in id_para_codigo.items() if v in filtro_projeto]
else:
    projetos_filtrados_ids = None

if filtro_ano:
    df_filtrado_final = df_filtrado_final[df_filtrado_final["ano"].isin(filtro_ano)]

# Extrai listas finais
projetos_filtrados = projetos_filtrados_ids
anos_filtrados = df_filtrado_final["ano"].dropna().unique().tolist()
autores_filtrados = df_filtrado_final["autor_anotacao"].dropna().unique().tolist()


# ---------------------- ORGANIZAÇÕES E COMUNIDADES ----------------------


col1, col2 = st.columns(2)

with col1.container(border=True):
    st.write('**Organizações e Comunidades**')
    st.button(f"Número de organizações apoiadas: **{somar_indicador_por_nome('numero_de_organizacoes_apoiadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_organizacoes_apoiadas', tipo_selecionado, projetos_filtrados, anos_filtrados), type="tertiary")
    st.button(f"Número de comunidades fortalecidas: **{somar_indicador_por_nome('numero_de_comunidades_fortalecidas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_comunidades_fortalecidas', tipo_selecionado, projetos_filtrados, anos_filtrados), type="tertiary")


# ---------------------- PESSOAS ----------------------

with col2.container(border=True):
    st.write('**Pessoas**')
    st.button(f"Número de famílias: **{somar_indicador_por_nome('numero_de_familias', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_familias', tipo_selecionado, projetos_filtrados, anos_filtrados), type="tertiary")
    st.button(f"Número de homens jovens (até 29 anos): **{somar_indicador_por_nome('numero_de_homens_jovens', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_homens_jovens', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de homens adultos: **{somar_indicador_por_nome('numero_de_homens_adultos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_homens_adultos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de mulheres jovens (até 29 anos): **{somar_indicador_por_nome('numero_de_mulheres_jovens', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_mulheres_jovens', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de mulheres adultas: **{somar_indicador_por_nome('numero_de_mulheres_adultas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_mulheres_adultas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de Indígenas: **{somar_indicador_por_nome('numero_de_indigenas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_indigenas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de lideranças comunitárias fortalecidas: **{somar_indicador_por_nome('numero_de_liderancas_comunitarias_fortalecidas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_liderancas_comunitarias_fortalecidas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de famílias comercializando produtos da sociobio: **{somar_indicador_por_nome('numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_fundo_ecos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_fundo_ecos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de famílias acessando vendas institucionais: **{somar_indicador_por_nome('numero_de_familias_acessando_vendas_institucionais_com_apoio_do_fundo_ecos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_familias_acessando_vendas_institucionais_com_apoio_do_fundo_ecos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de estudantes recebendo bolsa: **{somar_indicador_por_nome('numero_de_estudantes_recebendo_bolsa', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_estudantes_recebendo_bolsa', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- CAPACITAÇÕES ----------------------

with col1.container(border=True):
    st.write('**Capacitações**')
    st.button(f"Número de capacitações realizadas: **{somar_indicador_por_nome('numero_de_capacitacoes_realizadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_capacitacoes_realizadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de homens jovens capacitados (até 29 anos): **{somar_indicador_por_nome('numero_de_homens_jovens_capacitados', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_homens_jovens_capacitados', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de homens adultos capacitados: **{somar_indicador_por_nome('numero_de_homens_adultos_capacitados', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_homens_adultos_capacitados', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de mulheres jovens capacitadas (até 29 anos): **{somar_indicador_por_nome('numero_de_mulheres_jovens_capacitadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_mulheres_jovens_capacitadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de mulheres adultas capacitadas: **{somar_indicador_por_nome('numero_de_mulheres_adultas_capacitadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_mulheres_adultas_capacitadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- INTERCÂMBIOS ----------------------

with col1.container(border=True):
    st.write('**Intercâmbios**')
    st.button(f"Número de intercâmbios realizados: **{somar_indicador_por_nome('numero_de_intercambios_realizados', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_intercambios_realizados', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de homens em intercâmbios: **{somar_indicador_por_nome('numero_de_homens_em_intercambios', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_homens_em_intercambios', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de mulheres em intercâmbios: **{somar_indicador_por_nome('numero_de_mulheres_em_intercambios', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_mulheres_em_intercambios', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- TERRITÓRIO ----------------------

with col2.container(border=True):
    st.write('**Território**')
    st.button(f"Número de iniciativas de Gestão Territorial implantadas: **{somar_indicador_por_nome('numero_de_iniciativas_de_gestao_territorial_implantadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_iniciativas_de_gestao_territorial_implantadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Área com manejo ecológico do fogo (ha): **{somar_indicador_por_nome('area_com_manejo_ecologico_do_fogo_ha', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('area_com_manejo_ecologico_do_fogo_ha', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Área com manejo agroecológico (ha): **{somar_indicador_por_nome('area_com_manejo_agroecologico_ha', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('area_com_manejo_agroecologico_ha', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Área com manejo para restauração (ha): **{somar_indicador_por_nome('area_com_manejo_para_restauracao_ha', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('area_com_manejo_para_restauracao_ha', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Área com manejo para extrativismo (ha): **{somar_indicador_por_nome('area_com_manejo_para_extrativismo_ha', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('area_com_manejo_para_extrativismo_ha', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- TECNOLOGIA E INFRA ----------------------

with col1.container(border=True):
    st.write('**Tecnologia e Infra-estrutura**')
    st.button(f"Número de agroindústrias implementadas/reformadas: **{somar_indicador_por_nome('numero_de_agroindustiras_implementadas_ou_reformadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_agroindustiras_implementadas_ou_reformadas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de tecnologias instaladas: **{somar_indicador_por_nome('numero_de_tecnologias_instaladas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_tecnologias_instaladas', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de pessoas beneficiadas com tecnologias: **{somar_indicador_por_nome('numero_de_pessoas_beneficiadas_com_tecnologias', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_pessoas_beneficiadas_com_tecnologias', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- FINANCEIRO ----------------------

with col1.container(border=True):
    st.write('**Financeiro**')
    st.button(f"Faturamento bruto anual pré-projeto (R$): **{somar_indicador_por_nome('faturamento_bruto_anual_pre_projeto', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('faturamento_bruto_anual_pre_projeto', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Faturamento bruto anual pós-projeto (R$): **{somar_indicador_por_nome('faturamento_bruto_anual_pos_projeto', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('faturamento_bruto_anual_pos_projeto', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Volume financeiro de vendas institucionais com apoio do Fundo Ecos: **{somar_indicador_por_nome('volume_financeiro_de_vendas_institucionais_com_apoio_do_fundo_ecos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('volume_financeiro_de_vendas_institucionais_com_apoio_do_fundo_ecos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- COMUNICAÇÃO ----------------------

with col2.container(border=True):
    st.write('**Comunicação**')
    st.button(f"Número de vídeos produzidos: **{somar_indicador_por_nome('numero_de_videos_produzidos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_videos_produzidos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de aparições na mídia: **{somar_indicador_por_nome('numero_de_aparicoes_na_midia', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_aparicoes_na_midia', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de publicações de caráter técnico: **{somar_indicador_por_nome('numero_de_publicacoes_de_carater_tecnico', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_publicacoes_de_carater_tecnico', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de artigos acadêmicos produzidos e publicados: **{somar_indicador_por_nome('numero_de_artigos_academicos_produzidos_e_publicados', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_artigos_academicos_produzidos_e_publicados', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de comunicadores comunitários contribuindo na execução das ações do ISPN: **{somar_indicador_por_nome('numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- PROJETOS FUNDO ECOS ----------------------

if tipo_selecionado == "fundo_ecos":
    with col1.container(border=True):
        st.write('**Projetos Fundo Ecos**')
        st.button(f"Número de visitas de monitoramento realizadas ao projeto apoiado: **{somar_indicador_por_nome('numero_de_visitas_de_monitoramento_realizadas_ao_projeto_apoiado', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
                  on_click=lambda: mostrar_detalhes('numero_de_visitas_de_monitoramento_realizadas_ao_projeto_apoiado', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
        st.button(f"Valor da Contrapartidas Financeira (R$): **{somar_indicador_por_nome('valor_da_contrapartida_financeira_projetinhos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
                  on_click=lambda: mostrar_detalhes('valor_da_contrapartida_financeira_projetinhos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
        st.button(f"Valor da Contrapartida Não-Financeira (R$): **{somar_indicador_por_nome('valor_da_contrapartida_nao_financeira_projetinhos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
                  on_click=lambda: mostrar_detalhes('valor_da_contrapartida_nao_financeira_projetinhos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
        st.button(f"Espécies: **clique para mais informações**",
                  on_click=lambda: mostrar_detalhes('especies', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
        st.button(f"Número de organizações apoiadas que alavancaram recursos: **{somar_indicador_por_nome('numero_de_organizacoes_apoiadas_que_alavancaram_recursos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
                  on_click=lambda: mostrar_detalhes('numero_de_organizacoes_apoiadas_que_alavancaram_recursos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
        st.button(f"Valor mobilizado de novos recursos (R$): **{somar_indicador_por_nome('valor_mobilizado_de_novos_recursos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)}**",
                  on_click=lambda: mostrar_detalhes('valor_mobilizado_de_novos_recursos', tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")

