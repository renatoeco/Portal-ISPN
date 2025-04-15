import streamlit as st
from pymongo import MongoClient

@st.cache_resource
def conectar_mongo():
    client = MongoClient(
    st.secrets["senhas"]["senha_mongo"])
    db = client["ISPN_Hub"]                    
    return db