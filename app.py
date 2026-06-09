"""Frontend em Streamlit"""

import streamlit as st
from backend import ChatbotSQLBackend

st.title("📊 Chatbot Inteligente de Banco de Dados")

# Garante que o backend é instanciado apenas uma vez para economizar memória
if "bot" not in st.session_state:
    st.session_state.bot = ChatbotSQLBackend()

pergunta = st.text_input("Faça uma pergunta sobre as vendas ou produtos:")

if st.button("Enviar"):
    if pergunta:
        with st.spinner("Consultando o banco de dados..."):
            resultado = st.session_state.bot.perguntar(pergunta)
            
            if resultado["sucesso"]:
                st.write(resultado["resposta"])
                # Expansor opcional para fins acadêmicos (professores adoram ver o SQL gerado!)
                with st.expander("Ver código SQL gerado por trás dos panos"):
                    st.code(resultado["query_sql"], language="sql")
            else:
                st.error(resultado["resposta"])