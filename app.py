"""
Frontend em Streamlit - A Interface Visual do Usuário
-----------------------------------------------------
Este arquivo cria a página web interativa do nosso chatbot.
O Streamlit tem uma característica muito peculiar: toda vez que o usuário
clica em um botão ou digita algo, ele RODA O CÓDIGO INTEIRO de cima a baixo
novamente. Por isso, usamos o "session_state" para salvar coisas que não 
podem ser esquecidas entre as recargas da página (como o histórico do chat).
"""

from pathlib import Path
import streamlit as st
from backend import ChatbotSQLBackend # Importa o nosso motor de inteligência criado no backend.py
from paths import DATABASE_EXAMPLE # Importa o caminho do banco de exemplo de dados padronizado

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
# Define como a aba do navegador vai aparecer. 
# "layout='centered'" mantém o chat no meio da tela (estilo ChatGPT).
st.set_page_config(
    page_title="Chatbot DB",
    page_icon="📊",
    layout="centered"
)

# ==========================================
# 2. INICIALIZAÇÃO DO BACKEND (Singleton)
# ==========================================
# O 'st.session_state' é a "memória de curto prazo" do Streamlit.
# Se não usarmos isso, toda vez que o usuário digitar uma letra, o Streamlit
# vai recriar o backend inteiro (conectando no banco e na OpenAI tudo de novo),
# o que deixaria o app super lento e gastaria recursos.
if "bot" not in st.session_state:
    # Só cria o bot na PRIMEIRA vez que o usuário abrir a página
    st.session_state.bot = ChatbotSQLBackend(DATABASE_EXAMPLE)


# ==========================================
# 3. INICIALIZAÇÃO DO HISTÓRICO DE MENSAGENS
# ==========================================
# Criamos uma lista vazia na memória para guardar a conversa.
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
    
    # Já adicionamos uma primeira mensagem padrão do robô para que 
    # a tela não fique completamente em branco ao abrir o app.
    st.session_state.mensagens.append({
        "role": "assistant", # 'assistant' = Robô | 'user' = Humano
        "content": "Olá! Sou seu assistente de banco de dados com memória de contexto. O que deseja consultar hoje?"
    })


# ==========================================
# 4. MENU LATERAL (SIDEBAR)
# ==========================================
# Tudo que for colocado dentro do bloco 'with st.sidebar' vai 
# aparecer em uma barra lateral esquerda da página.
with st.sidebar:
    st.title("⚙️ Configurações do Sistema")
    
    # CRIANDO A VARIÁVEL DO BANCO DE DADOS:
    # st.text_input cria uma caixa de texto. O 'value' é o valor padrão inicial.
    # Convertemos o DATABASE_EXAMPLE para string para exibir bonitinho na caixa.
    caminho_banco_variavel = st.text_input(
        "Caminho do Banco de Dados (SQLite):",
        value=str(DATABASE_EXAMPLE),
        help="Digite o caminho do arquivo .db ou .sqlite que deseja consultar."
    )
    
    # st.markdown("---")
    # st.markdown("**Integrantes do Grupo:**\n- Aluno 1\n- Aluno 2")
    
    # Botão manual de limpar conversa
    if st.button("🗑️ Limpar Conversa"):
        st.session_state.mensagens = []
        st.rerun()

# Título principal da página central
st.title("📊 Chatbot Inteligente de Dados")

# ==========================================
# 5. GERENCIAMENTO DINÂMICO DO BACKEND
# ==========================================
# Criamos uma chave chamada 'banco_atual' no session_state.
# Se o usuário mudar o texto na caixa lateral, o 'caminho_banco_variavel' vai ficar diferente
# do 'banco_atual'. Quando isso acontecer, o 'if' abaixo é disparado!
if "banco_atual" not in st.session_state or st.session_state.banco_atual != caminho_banco_variavel:
    
    # 1. Atualiza qual é o banco que está ativo no momento
    st.session_state.banco_atual = caminho_banco_variavel
    
    # 2. Reinicializa o Backend passando a NOVA variável de caminho
    # Isso destrói o bot antigo e cria um novo conectado ao novo arquivo!
    st.session_state.bot = ChatbotSQLBackend(Path(caminho_banco_variavel))
    
    # 3. Limpa o histórico de mensagens anteriores.
    # IMPORTANTE: Se mudamos o banco de dados, o histórico antigo não faz mais sentido,
    # pois o novo banco tem tabelas e dados completamente diferentes!
    st.session_state.mensagens = []
    st.session_state.mensagens.append({
        "role": "assistant", 
        "content": f"🔄 Conexão alterada com sucesso! Agora estou conectado ao banco: `{caminho_banco_variavel}`. O que deseja consultar nesta nova base?"
    })


# ==========================================
# 6. RENDERIZAÇÃO DO HISTÓRICO NA TELA
# ==========================================
# Como o Streamlit recarrega a página a cada interação, precisamos 
# redesenhar todas as mensagens passadas na tela.
for msg in st.session_state.mensagens:
    # Cria o balãozinho de chat (com ícone de robô ou de pessoa, dependendo do role)
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Se na mensagem salva existir a chave "sql" (e ela não for um erro N/A),
        # nós desenhamos o componente que permite expandir e ver o código SQL.
        if "sql" in msg and msg["sql"] != "N/A" and msg["sql"] != "-- NAO_SQL":
            with st.expander("Ver código SQL gerado"):
                st.code(msg["sql"], language="sql")


# ==========================================
# 7. ENTRADA DO USUÁRIO E PROCESSAMENTO
# ==========================================
# O ':=' é o "Walrus Operator" do Python. Ele faz duas coisas ao mesmo tempo:
# 1. Desenha a barra de digitar na parte inferior (st.chat_input)
# 2. Se o usuário apertar Enter, ele salva o texto na variável 'pergunta' e entra no 'if'
if pergunta := st.chat_input("Faça uma pergunta..."):
    
    # --- PREPARAÇÃO DO CONTEXTO PARA O BACKEND ---
    # O nosso backend espera receber o histórico como um texto longo.
    # Ex: "Usuário: Olá\nAssistente: Oi!"
    # Então, varremos o 'session_state' e montamos essa string (historico_formatado).
    historico_formatado = ""
    for msg in st.session_state.mensagens:
        origem = "Usuário" if msg["role"] == "user" else "Assistente"
        historico_formatado += f"{origem}: {msg['content']}\n"
    
    # --- ATUALIZAÇÃO DA TELA (USUÁRIO) ---
    # Salva a nova pergunta na memória do Streamlit e já desenha na tela
    st.session_state.mensagens.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)
    
    # --- RESPOSTA DO ROBÔ ---
    with st.chat_message("assistant"):
        # Coloca a animação de "carregando..." enquanto o backend faz a mágica
        with st.spinner("Analisando contexto e banco de dados..."):
            
            # Chama o método que programamos no backend.py!
            # Passamos a pergunta atual E o histórico acumulado.
            resultado = st.session_state.bot.perguntar(pergunta, historico_formatado)
            
            # Se não houve erros no SQL ou na OpenAI:
            if resultado["sucesso"]:
                # Mostra a resposta em texto
                st.markdown(resultado["resposta"])
                
                # Mostra o código do banco de dados
                if resultado["query_sql"] != "-- NAO_SQL":
                    with st.expander("Ver código SQL gerado"):
                        st.code(resultado["query_sql"], language="sql")
                
                # Salva a resposta do robô na memória para que ela não suma na próxima recarga
                st.session_state.mensagens.append({
                    "role": "assistant",
                    "content": resultado["resposta"],
                    "sql": resultado["query_sql"]
                })
            else:
                # Se der erro (ex: sem internet), mostra a mensagem em vermelho
                st.error(resultado["resposta"])