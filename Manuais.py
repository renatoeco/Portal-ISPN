import streamlit as st
import requests
import fitz  # PyMuPDF
from PIL import Image

st.set_page_config(layout="wide")
st.header("Manuais")
st.write('')

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

manuais = [
    {
        "nome": "Política de Viagem",
        "descricao": "descrição",
        "arquivo": "https://ispn.org.br/site/wp-content/uploads/2025/04/Politica-para-viagens-1.pdf"
    },
    {
        "nome": "Código de Ética",
        "descricao": "descrição",
        "arquivo": "https://ispn.org.br/site/wp-content/uploads/2025/02/Codigo-de-Etica-ISPN_jan25-1.pdf"
    },
    {
        "nome": "Manual operacional do Fundo Ecos",
        "descricao": "descrição",
        "arquivo": "https://fundoecos.org.br/wp-content/uploads/2025/05/Manual-operacional-Fundo-Ecos_2025_site.pdf"
    }
]

@st.dialog("Detalhes do manual", width="large")
def dialogo_manual(nome_manual, descricao, arquivo_url):
    
    #st.html("<span class='big-dialog'></span>")
    
    st.subheader(nome_manual)
    st.write(descricao)

    # Baixar PDF
    r = requests.get(arquivo_url)
    if r.status_code == 200:
        pdf_bytes = r.content

        try:
            # Botão para download
            st.download_button(
                label="Clique aqui para baixar",
                data=pdf_bytes,
                file_name=arquivo_url.split("/")[-1],
                mime="application/pdf"
            )
            
            # Abrir PDF com PyMuPDF
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Zoom 2x para melhor resolução
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                st.image(img, caption=f"Página {page_num+1}", use_container_width=True)

        except Exception as e:
            st.error(f"Erro ao converter PDF: {e}")

        
    else:
        st.error("Não foi possível carregar o PDF.")
        
    

for manual in manuais:
    if st.button(manual["nome"], type="tertiary"):
        dialogo_manual(manual["nome"], manual["descricao"], manual["arquivo"])