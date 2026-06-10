"""O coração do chatbot - Versão Atualizada para LangChain v1.0 (LCEL Puro)"""

import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.tools import QuerySQLDatabaseTool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter

# Carrega as variáveis do arquivo .env
load_dotenv()

# LIMPEZA DE SEGURANÇA: Garante que nenhuma variável antiga interfira na URL da OpenAI
# os.environ.pop("OPENAI_API_BASE", None)
# os.environ.pop("OPENAI_BASE_URL", None)

class ChatbotSQLBackend():
    def __init__(self, database_path: Path):
        # Correção Cross-Platform: Garante barras para a direita (/) independente do OS
        db_safe_path = Path(database_path).resolve().as_posix()
        self.db = SQLDatabase.from_uri(f"sqlite:///{db_safe_path}")
        
        # Inicializa o LLM
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            http_client=httpx.Client(verify=False)
        )
        
        # Ferramenta comunitária para executar o SQL
        self.executor_sql = QuerySQLDatabaseTool(db=self.db)
        
        # Monta a pipeline completa
        self.pipeline_final = self._construir_pipeline()

    def _construir_pipeline(self):
        """Monta a lógica de geração, execução e tradução usando LCEL Puro."""
        
        # 1. PROMPT PARA GERAR O SQL
        prompt_geracao_sql = ChatPromptTemplate.from_template(
            """Você é um especialista em banco de dados. Dada a pergunta do usuário, crie uma query SQL válida em {dialeto} para responder à pergunta.
            Retorne APENAS a query SQL pura, sem formatação markdown (não use ```sql).

            Estrutura das Tabelas (Schema):
            {informacao_tabelas}

            Pergunta do Usuário: {question}
            Query SQL:"""
        )

        # 2. CADEIA DE GERAÇÃO DE SQL (Com limpador de Markdown acoplado)
        cadeia_geracao_sql = (
            {
                "question": itemgetter("question"),
                "dialeto": lambda _: self.db.dialect,
                "informacao_tabelas": lambda _: self.db.get_table_info()
            }
            | prompt_geracao_sql
            | self.llm
            | StrOutputParser()
            # Esta linha garante que, se a IA falhar e mandar markdown, o código limpa antes de ir pro banco:
            | (lambda x: x.replace("```sql", "").replace("```", "").strip())
        )

        # 3. PROMPT PARA A RESPOSTA FINAL AO USUÁRIO
        prompt_resposta = ChatPromptTemplate.from_template(
            """Dado o seguinte comando SQL, o resultado desse comando e a pergunta do usuário, responda de forma natural e amigável.
            
            Pergunta do Usuário: {question}
            Comando SQL Gerado: {query}
            Resultado do Banco: {result}
            
            Resposta do Chatbot:"""
        )

        # 4. A ESTEIRA FINAL (PIPELINE)
        pipeline = (
            RunnablePassthrough.assign(query=cadeia_geracao_sql)
            .assign(result=itemgetter("query") | self.executor_sql)
            .assign(answer=prompt_resposta | self.llm | StrOutputParser())
        )
        return pipeline

    def perguntar(self, pergunta_usuario: str) -> dict:
        """Método principal que o frontend chamará."""
        try:
            resposta = self.pipeline_final.invoke({"question": pergunta_usuario})
            return {
                "sucesso": True,
                "resposta": resposta["answer"],
                "query_sql": resposta["query"]
            }
        except Exception as e:
            return {
                "sucesso": False,
                "resposta": f"Ops, tive um erro ao processar sua pergunta. Erro: {str(e)}",
                "query_sql": "N/A"
            }

# Teste rápido do backend
# Teste rápido do backend
if __name__ == "__main__":
    from paths import DATABASE_EXAMPLE
    
    # ---- BLOCO DE DIAGNÓSTICO (DEBUG) ----
    print("\n🔍 --- VERIFICAÇÃO DE AMBIENTE ---")
    print(f"Diretório atual de execução: {os.getcwd()}")
    
    modelo = os.getenv("OPENAI_MODEL")
    print(f"Modelo carregado do .env: {modelo}")
    
    chave = os.getenv("OPENAI_API_KEY")
    if chave:
        # Mostra só os 6 primeiros caracteres por segurança
        print(f"Chave encontrada? Sim! (Começa com: {chave[:6]}...)")
    else:
        print("Chave encontrada? NÃO! O arquivo .env não foi lido ou está sem a chave.")
    print("---------------------------------\n")
    # ---------------------------------------

    bot = ChatbotSQLBackend(DATABASE_EXAMPLE)
    resultado = bot.perguntar("Qual o produto mais vendido e sua quantidade?")
    print(f"SQL Executado: {resultado['query_sql']}\n")
    print(f"Resposta do Bot: {resultado['resposta']}")