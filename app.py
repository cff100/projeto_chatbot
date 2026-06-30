"""
Frontend em Streamlit - A Interface Visual do Usuário
-----------------------------------------------------
Este arquivo cria a página web interativa do nosso chatbot.
O Streamlit tem uma característica muito peculiar: toda vez que o usuário
clica em um botão ou digita algo, ele RODA O CÓDIGO INTEIRO de cima a baixo
novamente. Por isso, usamos o "session_state" para salvar coisas que não 
podem ser esquecidas entre as recargas da página (como o histórico do chat).
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import streamlit as st
from backend import ChatbotSQLBackend # Importa o nosso motor de inteligência criado no backend.py
from paths import DATABASE_EXAMPLE, DATA_FOLDER # Importa o caminho do banco de exemplo de dados padronizado

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
# Define como a aba do navegador vai aparecer. 
# "layout='centered'" mantém o chat no meio da tela (estilo ChatGPT).
# Nota: Deve ser sempre o primeiro comando Streamlit a ser chamado.
st.set_page_config(
    page_title="Chatbot DB",
    page_icon="📊",
    layout="centered"
)

PASTA_BANCOS = DATA_FOLDER
PASTA_BANCOS.mkdir(exist_ok=True)

# ESCANEANDO A PASTA:
# .glob("*.db") busca todos os arquivos que terminam com .db naquela pasta.
# Juntamos os arquivos .db e .sqlite em uma única lista e ordenamos alfabeticamente.
arquivos_encontrados = sorted(list(PASTA_BANCOS.glob("*.db")) + list(PASTA_BANCOS.glob("*.sqlite")))

# Extraímos apenas o NOME do arquivo (ex: "vendas.db") para exibir no menu da tela.
opcoes_bancos = [arq.name for arq in arquivos_encontrados]

# TRAVA DE SEGURANÇA: Se o grupo esquecer de colocar arquivos na pasta, avisamos na tela.
if not opcoes_bancos:
    st.sidebar.error(f"⚠️ Nenhum arquivo .db ou .sqlite encontrado na pasta '/{PASTA_BANCOS.name}'.")
    st.sidebar.info("Por favor, cole um arquivo de banco de dados dentro dessa pasta no seu repositório.")
    # st.stop() interrompe o Streamlit elegantemente para não dar erro visual de falta de arquivo.
    st.stop()


# ==========================================
# 4. MENU LATERAL (SIDEBAR) COM UPLOAD DE ARQUIVOS
# ==========================================
import sqlite3
import pandas as pd
import shutil
from database_setup import import_csv_to_table  # Importa a função existente

with st.sidebar:
    st.title("⚙️ Configurações do Sistema")
    
    # --- ÁREA DE UPLOAD DE NOVOS ARQUIVOS ---
    st.subheader("📤 Adicionar Nova Base")
    arquivo_enviado = st.file_uploader(
        "Envie um arquivo .csv ou .db / .sqlite", 
        type=["csv", "db", "sqlite"],
        help="Arquivos .csv serão convertidos automaticamente em um novo banco .db"
    )
    
    if arquivo_enviado is not None:
        nome_arquivo = arquivo_enviado.name
        caminho_salvamento = PASTA_BANCOS / nome_arquivo
        
        # Evitar reprocessamento contínuo se o arquivo já foi processado neste ciclo
        chave_upload = f"processado_{nome_arquivo}"
        if chave_upload not in st.session_state:
            with st.spinner(f"Processando arquivo {nome_arquivo}..."):
                try:
                    # CASO 1: É um banco de dados SQLite pronto (.db ou .sqlite)
                    if nome_arquivo.endswith(('.db', '.sqlite')):
                        with open(caminho_salvamento, "wb") as f:
                            f.write(arquivo_enviado.getbuffer())
                        st.success(f"✅ Banco `{nome_arquivo}` adicionado!")
                        
                    # CASO 2: É um arquivo CSV
                    elif nome_arquivo.endswith('.csv'):
                        # Define o nome para o novo banco criado a partir do CSV
                        nome_tabela = nome_arquivo.split(".")[0].replace("-", "_").replace(" ", "_")
                        caminho_novo_db = PASTA_BANCOS / f"{nome_tabela}.db"
                        
                        # Lê o CSV enviado na memória usando o Pandas
                        df = pd.read_csv(arquivo_enviado, sep=None, engine='python', encoding='utf-8-sig')
                        df.columns = df.columns.str.strip()
                        
                        # Cria o novo arquivo de banco e insere os dados
                        conn = sqlite3.connect(caminho_novo_db)
                        df.to_sql(nome_tabela, conn, if_exists="append", index=False)
                        conn.close()
                        
                        st.success(f"✅ CSV convertido em `{nome_tabela}.db` com sucesso!")
                    
                    st.session_state[chave_upload] = True
                    # Força o recarregamento do app para atualizar a lista do selectbox instantaneamente
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao processar o arquivo: {e}")

    st.markdown("---")
    
    # --- SELEÇÃO DO BANCO ATIVO ---
    # Recarrega a lista dinamicamente para incluir o arquivo que acabou de subir
    arquivos_encontrados = sorted(list(PASTA_BANCOS.glob("*.db")) + list(PASTA_BANCOS.glob("*.sqlite")))
    opcoes_bancos = [arq.name for arq in arquivos_encontrados]
    
    # TRAVA DE SEGURANÇA: Se a pasta estiver vazia
    if not opcoes_bancos:
        st.error(f"⚠️ Nenhum banco encontrado. Faça o upload de um arquivo acima para começar.")
        st.stop()
        
    banco_selecionado_nome = st.selectbox(
        "Selecione a Base de Dados:",
        options=opcoes_bancos,
        help="Escolha qual banco de dados do seu repositório você deseja consultar agora."
    )
    
    caminho_banco_completo = PASTA_BANCOS / banco_selecionado_nome
    
    st.markdown("---")
    if st.button("🗑️ Limpar Conversa"):
        st.session_state.mensagens = [{
            "role": "assistant", 
            "content": f"Olá! Sou seu assistente. Estou conectado à base `{banco_selecionado_nome}`. O que deseja consultar?"
        }]
        st.rerun()

# Título principal da página central
st.title("📊 Chatbot Inteligente de Dados")

# @st.cache_resource
# def obter_hora_deploy():
#     fuso_local = ZoneInfo("America/Sao_Paulo")
#     return datetime.now(fuso_local).strftime('%d/%m/%Y %H:%M:%S')
# # Recupera o horário fixo global
# hora_fixa = obter_hora_deploy()
# st.caption(f"Backend (app.py) atualizado em: {hora_fixa}")


# ==========================================
# 2 e 5. GERENCIAMENTO DINÂMICO DO BACKEND (Correção do Problema 1 e 2)
# ==========================================
# O 'st.session_state' é a "memória de curto prazo" do Streamlit.
# Unificamos e corrigimos a lógica de inicialização do backend. Agora diferenciamos
# o "Primeiro Carregamento" de uma "Alteração Real" feita pelo usuário no selectbox.
if "bot" not in st.session_state:
    # 1. Guarda qual banco foi o primeiro a ser carregado
    st.session_state.banco_atual = banco_selecionado_nome
    
    # 2. Só cria o bot na PRIMEIRA vez que o usuário abrir a página, conectando na base inicial
    st.session_state.bot = ChatbotSQLBackend(caminho_banco_completo)

# Se o bot já existe, mas o banco ativo guardado for DIFERENTE da seleção atual do Combobox...
# Significa que o usuário mudou o arquivo ativamente!
elif st.session_state.banco_atual != banco_selecionado_nome:
    
    # 1. Atualiza qual é o banco que está ativo no momento
    st.session_state.banco_atual = banco_selecionado_nome
    
    # 2. Reinicializa o Backend passando a NOVA variável de caminho
    st.session_state.bot = ChatbotSQLBackend(caminho_banco_completo)
    
    # 3. Limpa o histórico de mensagens anteriores.
    # IMPORTANTE: Se mudamos o banco de dados, o histórico antigo não faz mais sentido,
    # pois o novo banco tem tabelas e dados completamente diferentes!
    st.session_state.mensagens = [{
        "role": "assistant", 
        "content": f"🔄 Conexão alterada com sucesso! Agora estou conectado ao banco: `{banco_selecionado_nome}`. O que deseja consultar nesta nova base?"
    }]


# ==========================================
# 3. INICIALIZAÇÃO DO HISTÓRICO DE MENSAGENS
# ==========================================
# Criamos uma lista vazia na memória para guardar a conversa se ela não existir.
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
    
    # Já adicionamos uma primeira mensagem padrão do robô para que 
    # a tela não fique completamente em branco ao abrir o app.
    st.session_state.mensagens.append({
        "role": "assistant", # 'assistant' = Robô | 'user' = Humano
        "content": f"Olá! Sou seu assistente de banco de dados com memória de contexto. Conectado à base `{banco_selecionado_nome}`. O que deseja consultar hoje?"
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