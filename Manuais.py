import streamlit as st
from datetime import datetime
from funcoes_auxiliares import conectar_mongo_portal_ispn

st.set_page_config(layout="wide")
st.logo("images/logo_ISPN_horizontal_ass.png", size='large')
st.header("Manuais")
st.write('')


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]


###########################################################################################################
# CONTADOR DE ACESSOS À PÁGINA
###########################################################################################################


# # Nome da página atual, usado como chave para contagem de acessos
# nome_pagina = "Regiões de Atuação"

# # Cria um timestamp formatado com dia/mês/ano hora:minuto:segundo
# timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# # Cria o nome do campo dinamicamente baseado na página
# campo_timestamp = f"{nome_pagina}.Visitas"

# # Atualiza a coleção de estatísticas com o novo acesso, incluindo o timestamp
# estatistica.update_one(
#     {},
#     {"$push": {campo_timestamp: timestamp}},
#     upsert=True  # Cria o documento se ele ainda não existir
# )

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


st.write('Para assuntos administrativos referentes a prestação de contas, relatórios, solicitações de viagens e formulários de evento, entre em contato com os seguintes endereços:')

st.write("**Brasília**: admbsb@ispn.org.br")
st.write("**Maranhão**: administrativoma@ispn.org.br")

st.write('')



# ###########################################################################################################

# COLOCAR OS DOCUMENTOS EM ORDEM ALFABÉTICA

# ###########################################################################################################


# ACORDOS DE CONVIVÊNCIA
with st.expander("ACORDOS DE CONVIVÊNCIA"):
    st.write("**Acordo de Convivência do Escritório de Brasília**")
    st.write("""O Acordo de convivência do escritório de Brasília orienta sobre uso organizado do espaço, incluindo 
             agendamento de reuniões, respeito ao silêncio, limpeza de áreas comuns e cuidados com 
             equipamentos e segurança ao final do expediente.""")
    
    with st.container(horizontal=True):
        st.write("Versão: março de 2023")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2023/03/Acordo-de-convivencia_Marco-2023.pdf", 
            type="tertiary",
            icon=":material/open_in_new:"
        )

# CÓDIGO DE ÉTICA
with st.expander("CÓDIGO DE ÉTICA"):
    st.write("""O Código de Ética e Conduta do ISPN reúne os princípios, diretrizes e 
    normas que orientam o comportamento de colaboradores, prestadores de serviços e parceiros. 
    Seu objetivo é fortalecer os valores institucionais, garantindo que todas as atividades sejam 
    conduzidas com ética, transparência e respeito, refletindo o compromisso do Instituto com relações 
    responsáveis e alinhadas às suas diretrizes estratégicas.""")
    
    with st.container(horizontal=True):
        st.write("Versão: janeiro de 2025")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2025/09/Codigo-de-Etica-ISPN_jan25-1.pdf", 
            type="tertiary",
            icon=":material/open_in_new:"
        )


# LISTAS DE PRESENÇA
with st.expander("LISTAS DE PRESENÇA"):
    st.write('')
    st.write("Modelo de Lista de Presença com autorização de uso de imagem.")
    
    with st.container(horizontal=True):
        st.write("Versão: 2025")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2023/04/Modelo-para-lista-de-presenca_Uso-de-Imagem-e-LGPD_Generica.docx", 
            type="tertiary",
            icon=":material/open_in_new:"
        )

    st.divider()
    st.write("Modelo de Lista de Presença com autorização de uso de imagem para **povos indígenas**.")
    
    with st.container(horizontal=True):
        st.write("Versão: 2025")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2025/10/Modelo-para-lista-de-presença_Uso-de-Imagem-e-LGPD_com-Povos-Indigenas.docx", 
            type="tertiary",
            icon=":material/open_in_new:"
        )



# MANUAL DE CARGOS E POLÍTICA DE REMUNERAÇÃO
with st.expander("MANUAL DE CARGOS E POLÍTICA DE REMUNERAÇÃO"):
    st.write("""O Manual de Cargos e Política de Remuneração Reúne a descrição da estrutura organizacional, 
             cargos e funções, além de metodologias aplicadas para definição de responsabilidades, 
             competências e requisitos. Também estabelece diretrizes para o plano de remuneração, 
             critérios de progressão de carreira e alinhamento salarial, promovendo transparência, 
             não discriminação e clareza nas funções e possibilidades de crescimento profissional dentro da instituição.""")
    
    with st.container(horizontal=True):
        st.write("Versão: julho de 2025")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2025/10/ISPN_MANUAL-DE-CARGOS-E-REMUNERACAO_VFINAL-1-1.pdf", 
            type="tertiary",
            icon=":material/open_in_new:"
        )


# MANUAL DO ISPN
with st.expander("MANUAL DO ISPN"):
    st.write("""O manual do ISPN apresenta diretrizes institucionais e operacionais, abordando 
             políticas de ética, conduta e privacidade, princípios e valores, teoria da mudança, 
             estratégias de atuação socioambiental, programas e iniciativas, gestão financeira e 
             administrativa, normas internas, responsabilidades de cargos, comunicação, manutenção 
             de espaços e tecnologia, além de políticas anticorrupção e de prevenção a fraudes.""")
    
    with st.container(horizontal=True):
        st.write("Versão: maio de 2025")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2025/10/Manual_ISPN_V7.pdf", 
            type="tertiary",
            icon=":material/open_in_new:"
        )


# MANUAL OPERACIONAL DO FUNDO ECOS
with st.expander("MANUAL OPERACIONAL DO FUNDO ECOS"):
    st.write("""O Manual Operacional do Fundo Ecos reúne as diretrizes, procedimentos e estruturas 
    que orientam a gestão e execução de projetos apoiados pelo Fundo. Abrange desde os princípios 
    institucionais do ISPN e os pilares do Fundo, até os processos de seleção, contratação, 
    monitoramento e prestação de contas de projetos. O manual detalha a governança, categorias 
    de projetos, critérios de avaliação, fluxo de recursos e estratégias de comunicação, 
    fornecendo uma referência completa para garantir transparência, eficiência e alinhamento 
    com os objetivos estratégicos do Fundo Ecos.""")
    
    with st.container(horizontal=True):
        st.write("Versão: fevereiro de 2025")
        st.link_button(
            label="Ver documento",
            url="https://fundoecos.org.br/wp-content/uploads/2025/05/Manual-operacional-Fundo-Ecos_2025_site.pdf", 
            type="tertiary",
            icon=":material/open_in_new:"
        )


# ORGANOGRAMA
with st.expander("ORGANOGRAMA"):
    st.write("Organograma do ISPN")

    st.image('https://ispn.org.br/wp-content/uploads/2025/02/Organograma-2025.png', width=1000)

# POLÍTICA DE PRIVACIDADE
with st.expander("POLÍTICA DE PRIVACIDADE"):
    st.write("""A Política de Privacidade do ISPN regula a coleta, uso, compartilhamento e proteção de 
    dados pessoais, em conformidade com a LGPD (Lei nº 13.709/2018). Ela explica quem está sujeito à política, 
    quais dados são coletados, como são utilizados, medidas de segurança adotadas, direitos dos titulares e 
    formas de contato.""")
    
    with st.container(horizontal=True):
        st.write("Versão: fevereiro de 2025")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2025/09/Politica-de-Privacidade-1.pdf", 
            type="tertiary",
            icon=":material/open_in_new:"
        )


# POLÍTICA DE PROTEÇÃO DE PESSOAS EM SITUAÇÃO DE VULNERABILIDADE
with st.expander("POLÍTICA DE PROTEÇÃO DE PESSOAS EM SITUAÇÃO DE VULNERABILIDADE"):
    st.write("""A Política de Proteção de Pessoas em Situação de Vulnerabilidade do ISPN define normas de 
    conduta para todos que atuam em nome do Instituto (diretores, funcionários, colaboradores, prestadores, 
    estagiários e voluntários), com o objetivo de proteger pessoas em situação de vulnerabilidade – incluindo 
    crianças, adolescentes e adultos expostos a ameaças, exclusão, discriminação, pobreza ou outras condições 
    que aumentem sua vulnerabilidade. A política busca prevenir danos, garantir a dignidade e integridade humana, 
    e orientar procedimentos para enfrentar riscos específicos. Projetos apoiados pelo Fundo Ecos devem respeitar 
    esta política.""")
    
    with st.container(horizontal=True):
        st.write("Versão: 3a edição - janeiro de 2025")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2025/09/3a-edicao_POLITICA_SEGURANCA-jan25-1.pdf", 
            type="tertiary",
            icon=":material/open_in_new:"
        )


# POLÍTICA DE VIAGEM
with st.expander("POLÍTICA DE VIAGEM"):
    st.write("""A Política de Viagem do ISPN define normas para planejamento, aprovação, execução 
    e reembolso de viagens de colaboradores, prestadores, voluntários e equipe técnica. Inclui 
    diretrizes sobre transporte, hospedagem, alimentação e seguro de viagem.""")
    
    with st.container(horizontal=True):
        st.write("Versão: abril de 2025")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2025/10/Politica-para-viagens-1.pdf", 
            type="tertiary",
            icon=":material/open_in_new:"
        )


# PLANILHA PARA REEMBOLSO DE EVENTO
with st.expander("PLANILHA PARA REEMBOLSO DE EVENTO"):
    st.write("Modelo de planilha para solicitação de Reembolso de despesas / Prestação de contas.")

    with st.container(horizontal=True):
        st.write("Versão: 2025")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2022/07/5.-PLANILHA-PARA-REEMBOLSO-EVENTOS.xlsx", 
            type="tertiary",
            icon=":material/open_in_new:"
        )

# RELATÓRIO MENSAL
with st.expander("RELATÓRIO MENSAL DE ATIVIDADES"):

    # 1) Modelo de relatório
    st.write("**1) Modelo de relatório**")
    st.link_button(
        label="Ver documento",
        url="https://ispn.org.br/wp-content/uploads/2022/08/6.-Modelo-Relatorio-mensal-de-atividades.docx", 
        type="secondary",
        icon=":material/open_in_new:"
    )

    st.write('')

    # 2) Vídeo tutorial do Autentique
    st.write("**2) Vídeo tutorial para assinatura do Relatório via Autentique**")
    st.video('https://www.youtube.com/watch?v=pLILQpTCX5U', width=1000)

    st.write('')

    # 3) Importação automática dos eventos da agenda
    st.write("**3) Dica extra: método de importação automática dos eventos da agenda**")
    st.write('É uma função no menu do google sheets que importa todos os eventos da sua agenda em um determinado período.')
    st.write('Auxilia na sistematização de atividades para o relatório mensal. Se você anota tudo certinho na agenda, no final do mês seu relatório estará praticamente pronto.')

 

    st.write('O script precisa ser instalado apenas na primeira vez. No dia a dia, basta chamar a função no menu e inserir as datas.')

    st.write('Abaixo está um vídeo tutorial e o botão para o script utilizado.')


    with st.container(horizontal=True):
        st.link_button(
            label="Vídeo tutorial",
            url="https://drive.google.com/file/d/1GbdjPHbkD2arXqLxwaznXkp_1rXQDS5E/view", 
            type="secondary",
            icon=":material/live_tv:"
        )

        st.link_button(
            label="Copiar script",
            url="https://docs.google.com/document/d/1EsB1bzEEdgxHw3dqfNd4ufFnS7_Rzd5khbGQ3qK_HmU/edit?usp=sharing", 
            type="secondary",
            icon=":material/docs:"
        )

    st.write('O script foi desenvolvido por André Moraes e Renato Araujo.')



# SOLICITAÇÃO DE AUTORIZAÇÃO DE VIAGEM (SAV)
with st.expander("SOLICITAÇÃO DE AUTORIZAÇÃO DE VIAGEM"):
    st.write('')
    st.write("As **Solicitações de Autorização de Viagem (SAVs)** e os **Relatórios de Viagem Simplificados (RVSs)** são feitos no **[Portal de Viagens do ISPN](https://ispn-viagens.streamlit.app)**")

    st.divider()

    st.write("**Guia de utilização do Portal de Viagens**")

    with st.container(horizontal=True):
        st.write("Versão: fevereiro 2025")
        st.link_button(
            label="Ver documento",
            url="https://drive.google.com/file/d/1xs5L4OBXDbhvUfmOGpxIlLnvTgD3dX1c/view?usp=sharing", 
            type="tertiary",
            icon=":material/open_in_new:"
        )    

# TERMOS DE REFERÊNCIA
with st.expander("TERMOS DE REFERÊNCIA"):
    st.write("Modelo de Termo de Referência para contratação de serviços.")

    with st.container(horizontal=True):
        st.write("Versão: maio de 2025")
        st.link_button(
            label="Ver documento",
            url="https://ispn.org.br/wp-content/uploads/2025/10/TDR_padrao_15-05-2025.docx", 
            type="tertiary",
            icon=":material/open_in_new:"
        )


