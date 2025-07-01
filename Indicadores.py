import streamlit as st
import pandas as pd
from funcoes_auxiliares import conectar_mongo_portal_ispn


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
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


def somar_indicador_por_nome(nome_indicador, projetos_filtrados=None, anos_filtrados=None, autores_filtrados=None):
    indicador_doc = indicadores.find_one({"nome_indicador": nome_indicador})
    if not indicador_doc:
        return "0"
    indicador_id = indicador_doc["_id"]

    filtro = {"id_do_indicador": indicador_id}
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
def mostrar_detalhes(nome_indicador, projetos_filtrados=None, anos_filtrados=None, autores_filtrados=None):
    indicador_doc = indicadores.find_one({"nome_indicador": nome_indicador})
    if not indicador_doc:
        st.warning("Indicador não encontrado.")
        return

    st.subheader(f"{formatar_nome_legivel(nome_indicador)}")

    indicador_id = indicador_doc["_id"]

    filtro = {"id_do_indicador": indicador_id}
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



######################################################################################################
# MAIN
######################################################################################################


st.header("Indicadores")
st.write('')


# ===== FILTROS =====


todos_lancamentos = list(lancamentos.find())
df_lancamentos = pd.DataFrame(todos_lancamentos)

projetos_disponiveis = sorted(df_lancamentos["projeto"].dropna().unique().tolist())
anos_disponiveis = sorted(df_lancamentos["ano"].dropna().unique().tolist())
autores_disponiveis = sorted(df_lancamentos["autor_anotacao"].dropna().unique().tolist())

col1, col2, col3 = st.columns(3)

with col1:
    projetos_filtrados = st.multiselect("Filtrar por projeto", projetos_disponiveis, default=[], placeholder="")

with col2:
    anos_filtrados = st.multiselect("Filtrar por ano", anos_disponiveis, default=[], placeholder="")
    
with col3:
    autores_filtrados = st.multiselect("Filtrar por autor", autores_disponiveis, default=[], placeholder="")

# Se não houver filtros, considerar todos
if not projetos_filtrados:
    projetos_filtrados = projetos_disponiveis
if not anos_filtrados:
    anos_filtrados = anos_disponiveis
if not autores_filtrados:
    autores_filtrados = autores_disponiveis

col1, col2 = st.columns(2)


# ---------------------- ORGANIZAÇÕES E COMUNIDADES ----------------------

with col1.container(border=True):
    st.write('**Organizações e Comunidades**')
    st.button(f"Número de organizações apoiadas: **{somar_indicador_por_nome('numero_de_organizacoes_apoiadas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_organizacoes_apoiadas', projetos_filtrados, anos_filtrados), type="tertiary")
    st.button(f"Número de comunidades fortalecidas: **{somar_indicador_por_nome('numero_de_comunidades_fortalecidas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_comunidades_fortalecidas', projetos_filtrados, anos_filtrados), type="tertiary")


# ---------------------- PESSOAS ----------------------

with col2.container(border=True):
    st.write('**Pessoas**')
    st.button(f"Número de famílias: **{somar_indicador_por_nome('numero_de_familias', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_familias', projetos_filtrados, anos_filtrados), type="tertiary")
    st.button(f"Número de homens jovens (até 29 anos): **{somar_indicador_por_nome('numero_de_homens_jovens', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_homens_jovens', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de homens adultos: **{somar_indicador_por_nome('numero_de_homens_adultos', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_homens_adultos', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de mulheres jovens (até 29 anos): **{somar_indicador_por_nome('numero_de_mulheres_jovens', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_mulheres_jovens', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de mulheres adultas: **{somar_indicador_por_nome('numero_de_mulheres_adultas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_mulheres_adultas', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de Indígenas: **{somar_indicador_por_nome('numero_de_indigenas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_indigenas', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de lideranças comunitárias fortalecidas: **{somar_indicador_por_nome('numero_de_liderancas_comunitarias_fortalecidas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_liderancas_comunitarias_fortalecidas', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de famílias comercializando produtos da sociobio: **{somar_indicador_por_nome('numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_fundo_ecos', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_fundo_ecos', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de famílias acessando vendas institucionais: **{somar_indicador_por_nome('numero_de_familias_acessando_vendas_institucionais_com_apoio_do_fundo_ecos', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_familias_acessando_vendas_institucionais_com_apoio_do_fundo_ecos', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de estudantes recebendo bolsa: **{somar_indicador_por_nome('numero_de_estudantes_recebendo_bolsa', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_estudantes_recebendo_bolsa', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- CAPACITAÇÕES ----------------------

with col1.container(border=True):
    st.write('**Capacitações**')
    st.button(f"Número de capacitações realizadas: **{somar_indicador_por_nome('numero_de_capacitacoes_realizadas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_capacitacoes_realizadas', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de homens jovens capacitados (até 29 anos): **{somar_indicador_por_nome('numero_de_homens_jovens_capacitados', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_homens_jovens_capacitados', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de homens adultos capacitados: **{somar_indicador_por_nome('numero_de_homens_adultos_capacitados', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_homens_adultos_capacitados', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de mulheres jovens capacitadas (até 29 anos): **{somar_indicador_por_nome('numero_de_mulheres_jovens_capacitadas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_mulheres_jovens_capacitadas', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de mulheres adultas capacitadas: **{somar_indicador_por_nome('numero_de_mulheres_adultas_capacitadas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_mulheres_adultas_capacitadas', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- INTERCÂMBIOS ----------------------

with col1.container(border=True):
    st.write('**Intercâmbios**')
    st.button(f"Número de intercâmbios realizados: **{somar_indicador_por_nome('numero_de_intercambios_realizados', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_intercambios_realizados', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de homens em intercâmbios: **{somar_indicador_por_nome('numero_de_homens_em_intercambios', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_homens_em_intercambios', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de mulheres em intercâmbios: **{somar_indicador_por_nome('numero_de_mulheres_em_intercambios', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_mulheres_em_intercambios', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- TERRITÓRIO ----------------------

with col2.container(border=True):
    st.write('**Território**')
    st.button(f"Número de iniciativas de Gestão Territorial implantadas: **{somar_indicador_por_nome('numero_de_iniciativas_de_gestao_territorial_implantadas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_iniciativas_de_gestao_territorial_implantadas', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Área com manejo ecológico do fogo (ha): **{somar_indicador_por_nome('area_com_manejo_ecologico_do_fogo_ha', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('area_com_manejo_ecologico_do_fogo_ha', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Área com manejo agroecológico (ha): **{somar_indicador_por_nome('area_com_manejo_agroecologico_ha', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('area_com_manejo_agroecologico_ha', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Área com manejo para restauração (ha): **{somar_indicador_por_nome('area_com_manejo_para_restauracao_ha', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('area_com_manejo_para_restauracao_ha', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Área com manejo para extrativismo (ha): **{somar_indicador_por_nome('area_com_manejo_para_extrativismo_ha', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('area_com_manejo_para_extrativismo_ha', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- TECNOLOGIA E INFRA ----------------------

with col1.container(border=True):
    st.write('**Tecnologia e Infra-estrutura**')
    st.button(f"Número de agroindústrias implementadas/reformadas: **{somar_indicador_por_nome('numero_de_agroindustiras_implementadas_ou_reformadas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_agroindustiras_implementadas_ou_reformadas', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de tecnologias instaladas: **{somar_indicador_por_nome('numero_de_tecnologias_instaladas', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_tecnologias_instaladas', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de pessoas beneficiadas com tecnologias: **{somar_indicador_por_nome('numero_de_pessoas_beneficiadas_com_tecnologias', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_pessoas_beneficiadas_com_tecnologias', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- FINANCEIRO ----------------------

with col1.container(border=True):
    st.write('**Financeiro**')
    st.button(f"Faturamento bruto anual pré-projeto (R$): **{somar_indicador_por_nome('faturamento_bruto_anual_pre_projeto', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('faturamento_bruto_anual_pre_projeto', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Faturamento bruto anual pós-projeto (R$): **{somar_indicador_por_nome('faturamento_bruto_anual_pos_projeto', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('faturamento_bruto_anual_pos_projeto', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Volume financeiro de vendas institucionais com apoio do Fundo Ecos: **{somar_indicador_por_nome('volume_financeiro_de_vendas_institucionais_com_apoio_do_fundo_ecos', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('volume_financeiro_de_vendas_institucionais_com_apoio_do_fundo_ecos', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")


# ---------------------- COMUNICAÇÃO ----------------------

with col2.container(border=True):
    st.write('**Comunicação**')
    st.button(f"Número de vídeos produzidos: **{somar_indicador_por_nome('numero_de_videos_produzidos', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_videos_produzidos', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de aparições na mídia: **{somar_indicador_por_nome('numero_de_aparicoes_na_midia', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_aparicoes_na_midia', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de publicações de caráter técnico: **{somar_indicador_por_nome('numero_de_publicacoes_de_carater_tecnico', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_publicacoes_de_carater_tecnico', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de artigos acadêmicos produzidos e publicados: **{somar_indicador_por_nome('numero_de_artigos_academicos_produzidos_e_publicados', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_artigos_academicos_produzidos_e_publicados', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
    st.button(f"Número de comunicadores comunitários contribuindo na execução das ações do ISPN: **{somar_indicador_por_nome('numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn', projetos_filtrados, anos_filtrados, autores_filtrados)}**",
              on_click=lambda: mostrar_detalhes('numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn', projetos_filtrados, anos_filtrados, autores_filtrados), type="tertiary")
