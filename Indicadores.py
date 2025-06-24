import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
from funcoes_auxiliares import conectar_mongo_portal_ispn


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
indicadores = db["indicadores"]


######################################################################################################
# FUNÇÕES
######################################################################################################


def formatar_brasileiro(valor):
    try:
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip('0').rstrip(',')
    except:
        return valor


def somar_indicador(nome_indicador):
    total = 0
    for doc in indicadores.find():
        valor = doc.get(nome_indicador, "")
        try:
            if valor and str(valor).strip() != "":
                total += float(str(valor).replace(".", "").replace(",", "."))
        except ValueError:
            pass
    if total == 0:
        return "0"
    return formatar_brasileiro(total)


@st.dialog("Detalhes dos reportes de indicadores", width="large")
def mostrar_detalhes():
    docs = list(indicadores.find())
    if docs:
        df = pd.DataFrame(docs)
        st.dataframe(df, hide_index=True)


def handler():
    def _handler():
        mostrar_detalhes()
    return _handler


######################################################################################################
# MAIN
######################################################################################################


st.header("Indicadores")
st.write('')

col1, col2 = st.columns(2)

with col1.container(border=True):
    st.write('**Organizações e Comunidades**')
    st.button(f"Número de organizações apoiadas: **{somar_indicador('numero_de_organizacoes_apoiadas')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de comunidades fortalecidas: **{somar_indicador('numero_de_comunidades_fortalecidas')}**", on_click=handler(), type="tertiary")

with col2.container(border=True):
    st.write('**Pessoas**')
    st.button(f"Número de famílias: **{somar_indicador('numero_de_familias')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de homens jovens (até 29): **{somar_indicador('numero_de_homens_jovens')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de homens adultos: **{somar_indicador('numero_de_homens_adultos')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de mulheres jovens (até 29): **{somar_indicador('numero_de_mulheres_jovens')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de mulheres adultas: **{somar_indicador('numero_de_mulheres_adultas')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de Indígenas: **{somar_indicador('numero_de_indigenas')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de lideranças comunitárias fortalecidas: **{somar_indicador('numero_de_lideranas_comunitarias_fortalecidas')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de fam. comercializando produtos da sociobio: **{somar_indicador('numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_ppp_ecos')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de famílias acessando vendas institucionais: **{somar_indicador('numero_de_familias_acessando_vendas_institucionais_com_apoio_do_ppp_ecos')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de estudantes recebendo bolsa: **{somar_indicador('numero_de_estudantes_recebendo_bolsa')}**", on_click=handler(), type="tertiary")

with col1.container(border=True):
    st.write('**Capacitações**')
    st.button(f"Número de capacitações realizadas: **{somar_indicador('numero_de_capacitacoes_realizadas')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de homens jovens capacitados (até 29): **{somar_indicador('numero_de_homens_jovens_capacitados')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de homens adultos capacitados: **{somar_indicador('numero_de_homens_adultos_capacitados')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de mulheres jovens capacitadas (até 29): **{somar_indicador('numero_de_mulheres_jovens_capacitadas')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de mulheres adultas capacitadas: **{somar_indicador('numero_de_mulheres_adultas_capacitadas')}**", on_click=handler(), type="tertiary")

with col1.container(border=True):
    st.write('**Intercâmbios**')
    st.button(f"Número de intercâmbios realizados: **{somar_indicador('numero_de_intercambios_realizados')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de homens em intercâmbios: **{somar_indicador('numero_de_homens_em_intercambios')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de mulheres em intercâmbios: **{somar_indicador('numero_de_mulheres_em_intercambios')}**", on_click=handler(), type="tertiary")

with col2.container(border=True):
    st.write('**Território**')
    st.button(f"Número de iniciativas de Gestão Territorial implantadas: **{somar_indicador('numero_de_iniciativas_de_gestao_territorial_implantadas')}**", on_click=handler(), type="tertiary")
    st.button(f"Área com manejo ecológico do fogo (ha): **{somar_indicador('area_com_manejo_ecologico_do_fogo_ha')}**", on_click=handler(), type="tertiary")
    st.button(f"Área com manejo agroecológico (ha): **{somar_indicador('area_com_manejo_agroecologico_ha')}**", on_click=handler(), type="tertiary")
    st.button(f"Área com manejo para restauração (ha): **{somar_indicador('area_com_manejo_para_restauracao_ha')}**", on_click=handler(), type="tertiary")
    st.button(f"Área com manejo para extrativismo (ha): **{somar_indicador('area_com_manejo_para_extrativismo_ha')}**", on_click=handler(), type="tertiary")

with col1.container(border=True):
    st.write('**Tecnologia e Infra-estrutura**')
    st.button(f"Número de agroindústrias implementadas/reformadas: **{somar_indicador('numero_de_agroindustiras_implementadas_ou_reformadas')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de tecnologias instaladas: **{somar_indicador('numero_de_tecnologias_instaladas')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de pessoas beneficiadas com tecnologias: **{somar_indicador('numero_de_pessoas_beneficiadas_com_tecnologias')}**", on_click=handler(), type="tertiary")

with col1.container(border=True):
    st.write('**Financeiro**')
    st.button(f"Incremento médio do faturamento bruto das organizações apoiadas: **{somar_indicador('faturamento_bruto_anual_pos_projeto')}**", on_click=handler(), type="tertiary")
    st.button(f"Volume financeiro de vendas institucionais das organizações apoiadas: **{somar_indicador('volume_financeiro_de_vendas_institucionais_com_apoio_do_ppp_ecos')}**", on_click=handler(), type="tertiary")

with col2.container(border=True):
    st.write('**Comunicação**')
    st.button(f"Número de vídeos produzidos: **{somar_indicador('numero_de_videos_produzidos')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de aparições na mídia: **{somar_indicador('numero_de_aparicoes_na_midia')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de publicações de caráter técnico: **{somar_indicador('numero_de_publicacoes_de_carater_tecnico')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de artigos acadêmicos produzidos e publicados: **{somar_indicador('numero_de_artigos_academicos_produzidos_e_publicados')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de comunicadores comunitários contribuindo na execução das ações: **{somar_indicador('numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn')}**", on_click=handler(), type="tertiary")

with col1.container(border=True):
    st.write('**Políticas Públicas**')
    st.button(f"Número de políticas públicas monitoradas pelo Programa: **{somar_indicador('numero_de_politicas_publicas_monitoradas_pelo_ispn')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de Proposições Legislativas acompanhadas pelo Programa: **{somar_indicador('numero_de_proposicoes_legislativas_acompanhadas_pelo_ispn')}**", on_click=handler(), type="tertiary")
    st.button(f"Número de contribuições que apoiam a construção e aprimoramento de pol. públicas: **{somar_indicador('numero_de_contribuicoes_notas_tecnicas_participacoes_e_ou_documentos_que_apoiam_a_construcao_e_aprimoramento_de_politicas_publicas')}**", on_click=handler(), type="tertiary")
