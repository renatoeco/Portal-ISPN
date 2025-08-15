import streamlit as st


st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')
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
        "descricao": """A Política de Viagem do ISPN define normas para planejamento, aprovação, execução 
        e reembolso de viagens de colaboradores, prestadores, voluntários e equipe técnica. Inclui 
        diretrizes sobre transporte, hospedagem, alimentação e seguro de viagem.""",
        "arquivo": "https://ispn.org.br/site/wp-content/uploads/2025/04/Politica-para-viagens-1.pdf",
        "versao": "abril de 2025"
    },
    {
        "nome": "Código de Ética",
        "descricao": """O Código de Ética e Conduta do ISPN reúne os princípios, diretrizes e 
        normas que orientam o comportamento de colaboradores, prestadores de serviços e parceiros. 
        Seu objetivo é fortalecer os valores institucionais, garantindo que todas as atividades sejam 
        conduzidas com ética, transparência e respeito, refletindo o compromisso do Instituto com relações 
        responsáveis e alinhadas às suas diretrizes estratégicas.""",
        "arquivo": "https://ispn.org.br/site/wp-content/uploads/2025/02/Codigo-de-Etica-ISPN_jan25-1.pdf",
        "versao": "janeiro de 2025"
    },
    {
        "nome": "Manual operacional do Fundo Ecos",
        "descricao": """O Manual Operacional do Fundo Ecos reúne as diretrizes, procedimentos e estruturas 
        que orientam a gestão e execução de projetos apoiados pelo Fundo. Abrange desde os princípios 
        institucionais do ISPN e os pilares do Fundo, até os processos de seleção, contratação, 
        monitoramento e prestação de contas de projetos. O manual detalha a governança, categorias 
        de projetos, critérios de avaliação, fluxo de recursos e estratégias de comunicação, 
        fornecendo uma referência completa para garantir transparência, eficiência e alinhamento 
        com os objetivos estratégicos do Fundo Ecos.""",
        "arquivo": "https://fundoecos.org.br/wp-content/uploads/2025/05/Manual-operacional-Fundo-Ecos_2025_site.pdf",
        "versao": "fevereiro de 2025"
    }
]

        
# Ordena os manuais por ordem alfabética do nome
manuais.sort(key=lambda x: x["nome"]) 

for manual in manuais:
    
    with st.container(border=True):
        
        # Nome
        st.write(f"**{manual['nome'].upper()}**")

        # Descrição
        st.write(manual["descricao"])

        with st.container(horizontal=True):

            # Versão
            st.write(f"Versão: {manual['versao']}")

            # Botão link
            st.link_button(
                label="Abrir documento :material/open_in_new:",
                url=manual["arquivo"], 
                type="tertiary"
            )
