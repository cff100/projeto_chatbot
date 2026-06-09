"""O coração do chatbot - Versão Atualizada para LangChain v1.0 (LCEL Puro)"""

import os
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter

# Carrega as variáveis do arquivo .env
load_dotenv()

class ChatbotSQLBackend:
    def __init__(self):
        # Conecta ao arquivo do banco SQLite
        self.db = SQLDatabase.from_uri("sqlite:///database.db")
        
        # Inicializa o LLM
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0
        )
        
        # Ferramenta comunitária para executar o SQL (continua válida na v1.0)
        self.executor_sql = QuerySQLDataBaseTool(db=self.db)
        
        # Monta a pipeline completa usando a nova arquitetura
        self.pipeline_final = self._construir_pipeline()

    def _construir_pipeline(self):
        """Monta a lógica de geração, execução e tradução usando LCEL Puro."""
        
        # 1. PROMPT PARA GERAR O SQL
        # Na v1.0, nós controlamos exatamente o que o modelo recebe sobre o banco
        prompt_geracao_sql = ChatPromptTemplate.from_template(
            """Você é um especialista em banco de dados. Dada a pergunta do usuário, crie uma query SQL válida em {dialeto} para responder à pergunta.
            Retorne APENAS a query SQL pura, sem formatação markdown (não use ```sql).

            Estrutura das Tabelas (Schema):
            {informacao_tabelas}

            Pergunta do Usuário: {question}
            Query SQL:"""
        )

        # 2. CADEIA DE GERAÇÃO DE SQL (Substitui o antigo create_sql_query_chain)
        cadeia_geracao_sql = (
            {
                "question": itemgetter("question"),
                "dialeto": lambda _: self.db.dialect,
                "informacao_tabelas": lambda _: self.db.get_table_info()
            }
            | prompt_geracao_sql
            | self.llm
            | StrOutputParser()
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
        # Junta a geração do SQL, a execução dele no banco e a resposta final humana
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
if __name__ == "__main__":
    bot = ChatbotSQLBackend()
    resultado = bot.perguntar("Qual o produto mais vendido e sua quantidade?")
    print(f"SQL Executado: {resultado['query_sql']}\n")
    print(f"Resposta do Bot: {resultado['resposta']}")