"""
Módulo de Backend - O Coração do Chatbot Text-to-SQL
---------------------------------------------------
Este arquivo é responsável por toda a "inteligência" do robô.
Ele pega a pergunta em português, analisa o histórico da conversa,
escreve uma consulta (query) em SQL, roda essa consulta no banco
de dados e traduz o resultado de volta para português natural.

Arquitetura: LangChain v1.0 usando LCEL (LangChain Expression Language).
"""

import os
import httpx  # Usado para configurar requisições HTTP customizadas (como ignorar SSL)
from pathlib import Path
from dotenv import load_dotenv

# --- IMPORTS DO LANGCHAIN ---

from langchain_community.utilities import SQLDatabase        # SQLDatabase: Gerencia a conexão física com o banco de dados SQLite.
from langchain_openai import ChatOpenAI                      # ChatOpenAI: O "cérebro" que vai conversar com a API da OpenAI.
from langchain_community.tools import QuerySQLDatabaseTool   # QuerySQLDatabaseTool: Ferramenta pronta que pega uma string SQL e executa no banco.
from langchain_core.output_parsers import StrOutputParser    # StrOutputParser: Pega a resposta complexa do LLM e transforma em texto puro (string).
from langchain_core.prompts import ChatPromptTemplate        # ChatPromptTemplate: Cria as "fôrmas" de texto para enviarmos comandos ao LLM.
from langchain_core.runnables import RunnablePassthrough     # RunnablePassthrough: Ferramenta mágica da LCEL que permite passar dicionários de dados de um passo para o outro na nossa esteira de montagem.
from operator import itemgetter                              # itemgetter: Ajuda a extrair valores específicos de um dicionário rapidamente.

# Carrega as variáveis de ambiente (como OPENAI_API_KEY) do arquivo .env
load_dotenv()


class ChatbotSQLBackend():
    """
    Classe principal que encapsula a lógica de inteligência artificial e banco de dados.
    """
    def __init__(self, database_path: Path):
        # 1. PREPARANDO O CAMINHO DO BANCO DE DADOS
        
        # Converte o caminho para o formato POSIX (barras para a direita: '/').
        # Isso evita que o código quebre se um aluno usar Windows (\) e outro usar Mac/Linux (/).
        db_safe_path = Path(database_path).resolve().as_posix()

        self.db = SQLDatabase.from_uri(f"sqlite:///{db_safe_path}")
        
        # 2. INICIALIZANDO O MODELO DE IA (LLM)

        # temperature=0: Faz com que o modelo seja 100% lógico e determinístico.
        # Não queremos que ele seja "criativo" ao escrever SQL, queremos que seja exato.
        # "gpt-4o-mini" é adicionado aqui como prática de programação defensiva, 
        # para caso aja algum problema com o modelo definido na configuração do ambiente (.env)
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),   
            http_client=httpx.Client(verify=False)   # httpx.Client(verify=False): Ignora bloqueios de certificado SSL da rede
        )
        
        # 3. PREPARANDO A FERRAMENTA DE SQL
        # Essa ferramenta será usada pela IA para rodar o comando diretamente no SQLite.
        self.executor_sql = QuerySQLDatabaseTool(db=self.db)
        
        # 4. MONTANDO A ESTEIRA (PIPELINE)
        # Chamamos a função interna que constrói o fluxo de raciocínio da IA.
        self.pipeline_final = self._construir_pipeline()

    def _construir_pipeline(self):
        """
        Constrói a "linha de montagem" (Pipeline) usando LCEL.
        O operador '|' (pipe) significa "pegue o resultado disso e passe para o próximo passo".
        """
        
        # ==========================================
        # ETAPA A: MEMÓRIA E CONTEXTO (STANDALONE QUESTION)
        # ==========================================
        # O robô precisa entender quando dizemos "E qual o preço *dele*?".
        # Este prompt ensina a IA a trocar o "dele" pelo nome real do produto salvo no histórico.
        prompt_contexto = ChatPromptTemplate.from_template(
            """Dada a seguinte conversa histórica e uma nova pergunta do usuário, reformule a pergunta para que ela seja uma pergunta independente (standalone), ou seja, que faça sentido sozinha sem precisar do histórico.
            Se a pergunta já for clara e independente, retorne-a exatamente igual.
            Retorne APENAS a pergunta reformulada, sem justificativas, saudações ou comentários.

            Histórico da Conversa:
            {historico_texto}

            Nova Pergunta: {question}
            Pergunta Reformulada:"""
        )

        # Cadeia de Contexto: Recebe as variáveis -> Preenche o Prompt -> Envia para IA -> Extrai o Texto
        cadeia_contexto = prompt_contexto | self.llm | StrOutputParser()


        # ==========================================
        # ETAPA B: GERAÇÃO DA QUERY SQL
        # ==========================================
        # Com a pergunta bem clara, pedimos para a IA escrever o código SQL.
        prompt_geracao_sql = ChatPromptTemplate.from_template(
            """Você é um especialista em banco de dados. Dada a pergunta do usuário, crie uma query SQL válida em {dialeto} para responder à pergunta.
            Retorne APENAS a query SQL pura, sem formatação markdown (não use ```sql).

            Estrutura das Tabelas (Schema):
            {informacao_tabelas}

            Pergunta do Usuário: {pergunta_contextualizada}
            Query SQL:"""
        )


        # ==========================================
        # ETAPA C: TRADUÇÃO PARA LINGUAGEM HUMANA
        # ==========================================
        # Pega a resposta "fria e feia" do banco de dados (ex: [(50,)]) e transforma em 
        # português amigável (ex: "Temos 50 unidades no estoque!").
        prompt_resposta = ChatPromptTemplate.from_template(
            """Dado o histórico da conversa, o comando SQL gerado e o resultado obtido do banco, responda de forma natural, amigável e concisa à última pergunta do usuário. 
            Não há a necessidade de terminar com frases como 'Se precisar de mais alguma informação, é só avisar! e semelhantes'. 
            Caso não haja informações disponíveis que respondam ao usuário ou a pergunta não esteja relacionada, diga que não possui informações.
            
            Histórico da Conversa:
            {historico_texto}
            
            Última Pergunta do Usuário: {question}
            Comando SQL Gerado: {query}
            Resultado do Banco: {result}
            
            Resposta do Chatbot:"""
        )

        # ==========================================
        # A LINHA DE MONTAGEM FINAL (A MÁGICA DA LCEL)
        # ==========================================
        # O método `.assign()` vai "agregando" novas variáveis a um dicionário que viaja pela esteira.
        pipeline = (
            # Passo 1: Cria a chave 'pergunta_contextualizada' rodando a cadeia de contexto.
            RunnablePassthrough.assign(pergunta_contextualizada=cadeia_contexto)
            
            # Passo 2: Cria a chave 'query' (o comando SQL)
            .assign(
                query=(
                    {
                        # Pega a pergunta que arrumamos no Passo 1
                        "pergunta_contextualizada": itemgetter("pergunta_contextualizada"),
                        # Descobre qual é o banco (SQLite)
                        "dialeto": lambda _: self.db.dialect,
                        # Pega a estrutura das tabelas (Quais colunas existem)
                        "informacao_tabelas": lambda _: self.db.get_table_info()
                    }
                    | prompt_geracao_sql
                    | self.llm
                    | StrOutputParser()
                    # Função de limpeza: Remove os blocos de código (```sql) se a IA for teimosa e tentar formatar
                    | (lambda x: x.replace("```sql", "").replace("```", "").strip())
                )
            )
            
            # Passo 3: Cria a chave 'result' executando a 'query' (gerada no Passo 2) no banco real.
            .assign(result=itemgetter("query") | self.executor_sql)
            
            # Passo 4: Cria a chave 'answer' (a resposta final) passando tudo que juntamos até agora para a última IA.
            .assign(answer=prompt_resposta | self.llm | StrOutputParser())
        )
        
        # Retorna a esteira pronta para ser usada pela interface
        return pipeline

    def perguntar(self, pergunta_usuario: str, historico_texto: str = "") -> dict:
        """
        Método público que o nosso frontend (app.py) vai chamar.
        Ele injeta a pergunta do usuário na "esteira" e espera o resultado.
        """
        try:
            # .invoke() é o gatilho que liga a esteira. Passamos as variáveis iniciais.
            resposta = self.pipeline_final.invoke({
                "question": pergunta_usuario,
                "historico_texto": historico_texto
            })
            
            # Devolvemos para a interface um dicionário mastigado com os resultados
            return {
                "sucesso": True,
                "resposta": resposta["answer"], # O texto em português
                "query_sql": resposta["query"]  # O SQL
            }
        except Exception as e:
            # Se a internet cair, ou o SQL der erro de sintaxe, o app não trava.
            # Ele cai aqui e avisa o usuário elegantemente.
            return {
                "sucesso": False,
                "resposta": f"Ops, tive um erro ao processar sua pergunta. Erro: {str(e)}",
                "query_sql": "N/A"
            }
    


# Teste rápido do backend
if __name__ == "__main__":

    # Importa o caminho do banco de exemplo só para testar no terminal
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

    historico_simulado = "Usuário: Qual o produto mais vendido?\nAssistente: O produto mais vendido foi o Notebook Gamer com 50 unidades.\n"
    pergunta_com_pronome = "E qual é o preço dele?"
    
    resultado = bot.perguntar(pergunta_com_pronome, historico_simulado)
    print(f"Histórico enviado:\n{historico_simulado}")
    print(f"Pergunta: {pergunta_com_pronome}\n")
    print(f"SQL Gerado dinamicamente: {resultado['query_sql']}\n")
    print(f"Resposta do Bot: {resultado['resposta']}")