import streamlit as st
import pandas as pd
import datetime
import time
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
pessoas = db["pessoas"]


######################################################################################################
# CSS PARA DIALOGO MAIOR
######################################################################################################


st.markdown(
    """
<style>
div[data-testid="stDialog"] div[role="dialog"]:has(.big-dialog) {
    width: 70vw;
    height: 80vh;
}
</style>
""",
    unsafe_allow_html=True,
)


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
        filtro["tipo"] = {"$in": tipo_selecionado}
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
        filtro["tipo"] = {"$in": tipo_selecionado}
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
    
    st.html("<span class='big-dialog'></span>")


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


def botao_indicador_legivel(titulo, nome_indicador, tipo, projetos, anos, autores):
    valor = somar_indicador_por_nome(nome_indicador, tipo, projetos, anos, autores)
    if valor != "0":
        st.button(f"{titulo}: **{valor}**", 
                  on_click=lambda: mostrar_detalhes(nome_indicador, tipo, projetos, anos, autores),
                  type="tertiary")


# Função para aplicar filtros progressivamente
def atualizar_opcoes(df, campo, campos_restritivos):
    df_filtrado = df.copy()
    for outro_campo, valores in campos_restritivos.items():

        if outro_campo != campo and valores:
            df_filtrado = df_filtrado[df_filtrado[outro_campo].isin(valores)]
    return sorted(df_filtrado[campo].dropna().unique().tolist())


def atualizar_filtro_interativo(campo, opcoes, label):
    selecao_antiga = st.session_state.filtros_indicadores[campo]
    selecao_nova = st.multiselect(
        label,
        opcoes,
        default=selecao_antiga,
        key=f"multiselect_{campo}",
        placeholder=""
    )
    if set(selecao_nova) != set(selecao_antiga):
        st.session_state.filtros_indicadores[campo] = selecao_nova
        st.rerun()
        
        
@st.dialog("Registrar lançamentos", width="large")
def registrar_lancamentos():
    st.subheader("Novo lançamento de indicador")

    tipo_projeto = st.selectbox(
        "Tipo de projeto",
        ["", "Fundo Ecos", "Projeto do ISPN"],
        key="tipo_projeto_lanc"
    )

    subtipo = None
    if tipo_projeto == "Fundo Ecos":
        subtipo = st.selectbox(
            "Subtipo",
            ["", "PJ", "PF"],
            key="subtipo_projeto_lanc"
        )

    if (tipo_projeto == "Projeto do ISPN") or (tipo_projeto == "Fundo Ecos" and subtipo in ["PJ", "PF"]):

        if tipo_projeto == "Projeto do ISPN":
            colecao = projetos_ispn
            tipo_salvar = "ispn"
        elif subtipo == "PJ":
            colecao = projetos_pj
            tipo_salvar = "PJ"
        elif subtipo == "PF":
            colecao = projetos_pf
            tipo_salvar = "PF"
        else:
            st.warning("Selecione o subtipo para continuar.")
            st.stop()

        projetos_lista = list(colecao.find({}, {"_id": 1, "codigo": 1, "nome_do_projeto": 1}))
        if not projetos_lista:
            st.warning("Nenhum projeto encontrado.")
            st.stop()

        projetos_opcoes = {
            f"{p.get('codigo', 'Sem código')} - {p.get('nome_do_projeto', '')}": p["_id"]
            for p in projetos_lista
        }

        projeto_selecionado = st.selectbox(
            "Projeto",
            [""] + list(projetos_opcoes.keys())
        )

        if projeto_selecionado != "":
            projeto_oid = projetos_opcoes[projeto_selecionado]

            indicadores_lista = list(indicadores.find({}, {"_id": 1, "nome_indicador": 1}))
            indicadores_opcoes = {
                formatar_nome_legivel(i["nome_indicador"]): i
                for i in indicadores_lista
            }

            indicador_legivel = st.selectbox(
                "Indicador",
                [""] + list(indicadores_opcoes.keys())
            )

            if indicador_legivel != "":
                indicador_doc = indicadores_opcoes[indicador_legivel]
                indicador_oid = indicador_doc["_id"]

                with st.form(key="form_lancamento_indicador"):
                    col1, col2 = st.columns(2)

                    # Lógica de campo de valor
                    if "espécies" in indicador_legivel.lower():
                        valor = col1.text_input("Espécies")  # texto livre
                    else:
                        valor = col1.number_input("Valor", step=1.0, format="%.2f")

                    # Campo de ano como number_input a partir de 2025
                    ano = col2.number_input("Ano", min_value=2025, step=1)

                    # Lista de pessoas da coleção
                    #pessoas_lista = list(pessoas.find({}, {"_id": 1, "nome_completo": 1}))
                    # opcoes_autores = {
                    #     pessoa["nome_completo"]: pessoa["_id"]
                    #     for pessoa in pessoas_lista if "nome_completo" in pessoa
                    # }

                    #autor_nome = col1.selectbox("Autor do lançamento", [""] + sorted(opcoes_autores.keys()))
                    
                    # Lista de pessoas da coleção
                    pessoas_lista = list(pessoas.find({}, {"_id": 1, "nome_completo": 1}))
                    opcoes_autores = sorted([
                        pessoa["nome_completo"]
                        for pessoa in pessoas_lista if "nome_completo" in pessoa
                    ])

                    autor_nome = col1.selectbox("Autor do lançamento", [""] + opcoes_autores)

                    
                    observacoes = col2.text_area("Observações", height=100)

                    submit = st.form_submit_button("Salvar lançamento")


                if submit:
                    if autor_nome == "":
                        st.warning("Selecione um autor.")
                        st.stop()

                    novo_lancamento = {
                        "id_do_indicador": indicador_oid,
                        "projeto": projeto_oid,
                        "data_anotacao": datetime.datetime.now(),
                        #"autor_anotacao": opcoes_autores[autor_nome],  # salva o _id da pessoa
                        "autor_anotacao": autor_nome,  # salva o nome completo
                        "valor": valor,
                        "ano": str(ano),
                        "observacoes": observacoes,
                        "tipo": tipo_salvar
                    }

                    lancamentos.insert_one(novo_lancamento)
                    st.success("Lançamento salvo com sucesso.")
                    time.sleep(2)
                    st.rerun()

            else:
                st.info("Por favor, selecione as opções acima para prosseguir.")



######################################################################################################
# MAIN
######################################################################################################


st.header("Indicadores")
st.write('')

if set(st.session_state.tipo_usuario) & {"admin",}:
    col1, col2, col3 = st.columns([2, 2, 1])
    col3.button("Registrar lançamentos", on_click=registrar_lancamentos, use_container_width=True, icon=":material/stylus_note:")


# ===== FILTROS =====

# 1. Carrega todos os projetos das 3 coleções
projetos_todos = []
for coll in [projetos_ispn, projetos_pf, projetos_pj]:
    projetos_todos.extend(list(coll.find({}, {"_id": 1, "bioma": 1, "sigla": 1, "programa": 1})))

df_proj_info = pd.DataFrame(projetos_todos).rename(columns={"_id": "projeto"})

# Se a coluna "programa" não existe, cria com valores vazios
if "programa" not in df_proj_info.columns:
    df_proj_info["programa"] = ""

# Carrega nomes dos programas
programas = list(db["programas_areas"].find({}, {"_id": 1, "nome_programa_area": 1}))
map_programa_nome = {p["_id"]: p["nome_programa_area"] for p in programas}

# Converte programa (ObjectId) em nome
df_proj_info["programa"] = df_proj_info["programa"].map(map_programa_nome).fillna("")



tipo_selecionado = st.pills(
    label="Tipo de projeto",
    options=["PJ", "PF", "ispn"],
    format_func=lambda x: {"PJ": "PJ", "PF": "PF", "ispn": "ISPN"}.get(x, x),
    selection_mode="multi",
    default=None,
)

# Cria dicionário id_string ➔ codigo
id_para_codigo = {}

for coll in [projetos_ispn, projetos_pf, projetos_pj]:
    for proj in coll.find({}, {"_id": 1, "codigo": 1}):
        id_para_codigo[str(proj["_id"])] = proj.get("codigo", "Sem código")

# Carregar lançamentos
todos_lancamentos = list(lancamentos.find())
df_base = pd.DataFrame(todos_lancamentos)

# Filtra por tipo
if tipo_selecionado:
    df_base = df_base[df_base["tipo"].isin(tipo_selecionado)]

# Criar coluna 'codigo' baseada no mapeamento
df_base["codigo"] = df_base["projeto"].astype(str).map(id_para_codigo)

# Preencher campos vazios
df_base["autor_anotacao"] = df_base["autor_anotacao"].fillna("")
df_base["ano"] = df_base["ano"].fillna("")
df_base["codigo"] = df_base["codigo"].fillna("")

# Concatena os campos bioma, sigla e programa ao df_base com merge pelo campo "projeto"
df_base = df_base.merge(df_proj_info, on="projeto", how="left")

# Preencher campos nulos
df_base["bioma"] = df_base["bioma"].fillna("")
df_base["sigla"] = df_base["sigla"].fillna("")
df_base["programa"] = df_base["programa"].fillna("")

# Inicializa session_state
if "filtros_indicadores" not in st.session_state:
    st.session_state.filtros_indicadores = {
        "autor_anotacao": [],
        "codigo": [],
        "ano": [],
        "bioma": [],
        "sigla": [],
        "programa": []
    }

# Iteração até estabilização para recalcular opções
for _ in range(2):  # Duas iterações normalmente são suficientes
    df_filtrado_tmp = df_base.copy()
    for campo, selecao in st.session_state.filtros_indicadores.items():
        if selecao:
            df_filtrado_tmp = df_filtrado_tmp[df_filtrado_tmp[campo].isin(selecao)]
    
    opcoes_autor = sorted(df_filtrado_tmp["autor_anotacao"].dropna().unique())
    opcoes_projeto = sorted(df_filtrado_tmp["codigo"].dropna().unique())
    opcoes_ano = sorted(df_filtrado_tmp["ano"].dropna().unique())
    opcoes_bioma = sorted(df_filtrado_tmp["bioma"].dropna().unique())
    opcoes_sigla = sorted(df_filtrado_tmp["sigla"].dropna().unique())
    opcoes_programa = sorted(df_filtrado_tmp["programa"].dropna().unique())

    # Remover seleções inválidas automaticamente
    st.session_state.filtros_indicadores["autor_anotacao"] = [x for x in st.session_state.filtros_indicadores["autor_anotacao"] if x in opcoes_autor]
    st.session_state.filtros_indicadores["codigo"] = [x for x in st.session_state.filtros_indicadores["codigo"] if x in opcoes_projeto]
    st.session_state.filtros_indicadores["ano"] = [x for x in st.session_state.filtros_indicadores["ano"] if x in opcoes_ano]
    st.session_state.filtros_indicadores["bioma"] = [x for x in st.session_state.filtros_indicadores["bioma"] if x in opcoes_bioma]
    st.session_state.filtros_indicadores["sigla"] = [x for x in st.session_state.filtros_indicadores["sigla"] if x in opcoes_sigla]
    st.session_state.filtros_indicadores["programa"] = [x for x in st.session_state.filtros_indicadores["programa"] if x in opcoes_programa]


col1, col2, col3 = st.columns(3)

# Interface de seleção dinâmica

with col1:
    atualizar_filtro_interativo("sigla", opcoes_sigla, "Filtrar por sigla")
with col2:
    atualizar_filtro_interativo("codigo", opcoes_projeto, "Filtrar por código")
with col3:
    atualizar_filtro_interativo("autor_anotacao", opcoes_autor, "Filtrar por autor")

col4, col5, col6 = st.columns(3)

with col4:
    atualizar_filtro_interativo("programa", opcoes_programa, "Filtrar por programa")
with col5:
    atualizar_filtro_interativo("bioma", opcoes_bioma, "Filtrar por bioma")
with col6:
    atualizar_filtro_interativo("ano", opcoes_ano, "Filtrar por ano")
    


# Aplicar filtros finais
df_filtrado = df_base.copy()
for campo, selecao in st.session_state.filtros_indicadores.items():
    if selecao:
        df_filtrado = df_filtrado[df_filtrado[campo].isin(selecao)]

# Extrai listas para passar aos botões
autores_filtrados = df_filtrado["autor_anotacao"].dropna().unique().tolist()
anos_filtrados = df_filtrado["ano"].dropna().unique().tolist()

# Projetos filtrados como ObjectId
if st.session_state.filtros_indicadores["codigo"]:
    projetos_filtrados = [
        ObjectId(k) for k, v in id_para_codigo.items() 
        if v in st.session_state.filtros_indicadores["codigo"]
    ]
else:
    projetos_filtrados = df_filtrado["projeto"].dropna().unique().tolist()



# ---------------------- ORGANIZAÇÕES E COMUNIDADES ----------------------


col1, col2 = st.columns(2)

with col1.container(border=True):
    st.write('**Organizações e Comunidades**')
    botao_indicador_legivel("Número de organizações apoiadas", "numero_de_organizacoes_apoiadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de comunidades fortalecidas", "numero_de_comunidades_fortalecidas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- PESSOAS ----------------------


with col2.container(border=True):
    st.write('**Pessoas**')
    botao_indicador_legivel("Número de famílias", "numero_de_familias", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de homens jovens (até 29 anos)", "numero_de_homens_jovens", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de homens adultos", "numero_de_homens_adultos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de mulheres jovens (até 29 anos)", "numero_de_mulheres_jovens", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de mulheres adultas", "numero_de_mulheres_adultas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de Indígenas", "numero_de_indigenas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de lideranças comunitárias fortalecidas", "numero_de_liderancas_comunitarias_fortalecidas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de famílias comercializando produtos da sociobio", "numero_de_familias_comercializando_produtos_da_sociobio_com_apoio_do_fundo_ecos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de famílias acessando vendas institucionais", "numero_de_familias_acessando_vendas_institucionais_com_apoio_do_fundo_ecos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de estudantes recebendo bolsa", "numero_de_estudantes_recebendo_bolsa", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- CAPACITAÇÕES ----------------------


with col1.container(border=True):
    st.write('**Capacitações**')
    botao_indicador_legivel("Número de capacitações realizadas", "numero_de_capacitacoes_realizadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de homens jovens capacitados (até 29 anos)", "numero_de_homens_jovens_capacitados", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de homens adultos capacitados", "numero_de_homens_adultos_capacitados", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de mulheres jovens capacitadas (até 29 anos)", "numero_de_mulheres_jovens_capacitadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de mulheres adultas capacitadas", "numero_de_mulheres_adultas_capacitadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- INTERCÂMBIOS ----------------------


with col1.container(border=True):
    st.write('**Intercâmbios**')
    botao_indicador_legivel("Número de intercâmbios realizados", "numero_de_intercambios_realizados", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de homens em intercâmbios", "numero_de_homens_em_intercambios", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de mulheres em intercâmbios", "numero_de_mulheres_em_intercambios", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- TERRITÓRIO ----------------------


with col2.container(border=True):
    st.write('**Território**')
    botao_indicador_legivel("Número de iniciativas de Gestão Territorial implantadas", "numero_de_iniciativas_de_gestao_territorial_implantadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Área com manejo ecológico do fogo (ha)", "area_com_manejo_ecologico_do_fogo_ha", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Área com manejo agroecológico (ha)", "area_com_manejo_agroecologico_ha", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Área com manejo para restauração (ha)", "area_com_manejo_para_restauracao_ha", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Área com manejo para extrativismo (ha)", "area_com_manejo_para_extrativismo_ha", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- TECNOLOGIA E INFRA ----------------------


with col1.container(border=True):
    st.write('**Tecnologia e Infra-estrutura**')
    botao_indicador_legivel("Número de agroindústrias implementadas/reformadas", "numero_de_agroindustiras_implementadas_ou_reformadas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de tecnologias instaladas", "numero_de_tecnologias_instaladas", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de pessoas beneficiadas com tecnologias", "numero_de_pessoas_beneficiadas_com_tecnologias", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- FINANCEIRO ----------------------


with col1.container(border=True):
    st.write('**Financeiro**')
    botao_indicador_legivel("Faturamento bruto anual pré-projeto (R$)", "faturamento_bruto_anual_pre_projeto", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Faturamento bruto anual pós-projeto (R$)", "faturamento_bruto_anual_pos_projeto", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Volume financeiro de vendas institucionais com apoio do Fundo Ecos", "volume_financeiro_de_vendas_institucionais_com_apoio_do_fundo_ecos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- COMUNICAÇÃO ----------------------


with col2.container(border=True):
    st.write('**Comunicação**')
    botao_indicador_legivel("Número de vídeos produzidos", "numero_de_videos_produzidos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de aparições na mídia", "numero_de_aparicoes_na_midia", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de publicações de caráter técnico", "numero_de_publicacoes_de_carater_tecnico", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de artigos acadêmicos produzidos e publicados", "numero_de_artigos_academicos_produzidos_e_publicados", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
    botao_indicador_legivel("Número de comunicadores comunitários contribuindo na execução das ações do ISPN", "numero_de_comunicadores_comunitarios_contribuindo_na_execucao_das_acoes_do_ispn", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)


# ---------------------- PROJETOS FUNDO ECOS ----------------------


if not tipo_selecionado or any(tipo in ["PJ", "PF"] for tipo in tipo_selecionado):
    with col1.container(border=True):
        st.write('**Projetos Fundo Ecos**')
        botao_indicador_legivel("Número de visitas de monitoramento realizadas ao projeto apoiado", "numero_de_visitas_de_monitoramento_realizadas_ao_projeto_apoiado", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
        botao_indicador_legivel("Valor da Contrapartidas Financeira (R$)", "valor_da_contrapartida_financeira_projetinhos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
        botao_indicador_legivel("Valor da Contrapartida Não-Financeira (R$)", "valor_da_contrapartida_nao_financeira_projetinhos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
        botao_indicador_legivel("Espécies: clique para mais informações", "especies", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
        botao_indicador_legivel("Número de organizações apoiadas que alavancaram recursos", "numero_de_organizacoes_apoiadas_que_alavancaram_recursos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)
        botao_indicador_legivel("Valor mobilizado de novos recursos (R$)", "valor_mobilizado_de_novos_recursos", tipo_selecionado, projetos_filtrados, anos_filtrados, autores_filtrados)

