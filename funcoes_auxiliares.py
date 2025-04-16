import streamlit as st
from pymongo import MongoClient

@st.cache_resource
def conectar_mongo_portal_ispn():
    cliente = MongoClient(
    st.secrets["senhas"]["senha_mongo_portal_ispn"])
    db_portal_ispn = cliente["ISPN_Hub"]                   
    return db_portal_ispn


@st.cache_resource
def conectar_mongo_pls():
    cliente_2 = MongoClient(
    st.secrets["senhas"]["senha_mongo_pls"])
    db_pls = cliente_2["db_pls"]
    return db_pls