"""Frontend em Streamlit - Interface de Chat Moderna"""

import streamlit as st
from backend import ChatbotSQLBackend
from paths import DATABASE_EXAMPLE # Importamos o caminho do banco

# 1. Configuração da Página (Aba do navegador mais bonita)
st.set_page_config(
    page_title="Chatbot DB",
    page_icon="📊",
    layout="centered"
)

# 2. Inicialização do Backend (Apenas uma vez)
if "bot" not in st.session_state:
    # Passamos o caminho do banco que está no nosso arquivo paths.py
    st.session_state.bot = ChatbotSQLBackend(DATABASE_EXAMPLE)

# 3. Inicialização do Histórico de Mensagens
# Se for a primeira vez abrindo a página, cria uma lista vazia
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
    # Mensagem inicial de boas-vindas do robô
    st.session_state.mensagens.append({
        "role": "assistant", 
        "content": "Olá! Sou seu assistente de banco de dados. O que você gostaria de saber sobre nossas vendas e produtos?"
    })

# 4. Interface Lateral (Sidebar) para informações do projeto
with st.sidebar:
    st.title("🤖 Sobre o Projeto")
    st.markdown("""
    Este chatbot consulta diretamente um banco de dados SQLite usando **LangChain v1.0** e **OpenAI**.
    
    **Integrantes do Grupo:**
    - Aluno 1
    - Aluno 2
    """)
    if st.button("🗑️ Limpar Conversa"):
        st.session_state.mensagens = []
        st.rerun()

st.title("📊 Chatbot Inteligente de Dados")

# 5. Renderizar o histórico na tela (Faz parecer um chat real)
for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Se a mensagem tiver SQL salvo, mostra no expansor
        if "sql" in msg and msg["sql"] != "N/A":
            with st.expander("Ver código SQL gerado"):
                st.code(msg["sql"], language="sql")

# 6. Caixa de entrada do usuário fixa na parte inferior
if pergunta := st.chat_input("Faça uma pergunta sobre as vendas ou produtos..."):
    
    # Adiciona a pergunta do usuário na tela e no histórico
    st.session_state.mensagens.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)
    
    # Processa a resposta do robô
    with st.chat_message("assistant"):
        with st.spinner("Analisando o banco de dados..."):
            resultado = st.session_state.bot.perguntar(pergunta)
            
            if resultado["sucesso"]:
                st.markdown(resultado["resposta"])
                with st.expander("Ver código SQL gerado"):
                    st.code(resultado["query_sql"], language="sql")
                
                # Salva a resposta do robô no histórico
                st.session_state.mensagens.append({
                    "role": "assistant",
                    "content": resultado["resposta"],
                    "sql": resultado["query_sql"]
                })
            else:
                st.error(resultado["resposta"])