from funcoes_auxiliares import conectar_mongo_portal_ispn
import streamlit as st
import pandas as pd

# Conectar ao banco
db = conectar_mongo_portal_ispn()

pj = list(db["projetos_pj"].find())
pf = list(db["projetos_pf"].find())

# Lista oficial de opções válidas
opcoes_temas = [
    "Agroecologia", "Agroextrativismo - Beneficiamento e Comercialização", "Água", "Apicultura e meliponicultura",
    "Artesanato", "Articulação", "Capacitação", "Certificação", "Conservação da biodiversidade", "Criação de animais", "Cultura",
    "Educação Ambiental","Escola Família Agrícola", "Economia solidária", "Energia Renovável", "Fauna", "Fogo", "Gestão Territorial", 
    "Manejo da biodiversidade", "Pesquisa", "Plantas medicinais", "Política Pública", "Recuperação de áreas degradadas", "Segurança alimentar", 
    "Sistemas Agroflorestais - SAFs", "Turismo", "Outro"
]

# Normaliza para facilitar comparação (sem espaços extras)
opcoes_temas_set = {t.strip() for t in opcoes_temas}

# Lista única para armazenar todos os inválidos
temas_invalidos_lista = []

def analisar_colecao(colecao, nome_colecao):
    for proj in colecao:
        temas_str = proj.get("temas", "")
        if not temas_str:
            continue

        # Divide por vírgula e remove espaços extras
        temas_lista = [t.strip() for t in temas_str.split(",") if t.strip()]

        # Procura temas que não estão na lista oficial
        invalidos = [t for t in temas_lista if t not in opcoes_temas_set]

        if invalidos:
            temas_invalidos_lista.append({
                "colecao": nome_colecao,
                "_id": proj["_id"],
                "nome": proj.get("nome", ""),
                "temas_originais": temas_str,
                "temas_invalidos": ", ".join(invalidos)
            })

# Analisar as duas coleções
analisar_colecao(pj, "projetos_pj")
analisar_colecao(pf, "projetos_pf")

# Exibir resultado
if not temas_invalidos_lista:
    st.success("Nenhum tema inválido encontrado.")
else:
    df_temas_invalidos = pd.DataFrame(temas_invalidos_lista)
    st.dataframe(df_temas_invalidos)
