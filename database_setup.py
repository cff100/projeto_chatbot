"""Script rápido para criar e popular o banco de dados"""

import sqlite3
import pandas as pd

from paths import CSV_FOLDER
from paths import DATABASE_EXAMPLE, DATA_FOLDER, CENTRAL_DATABASE

def create_example_database():

    DATABASE_EXAMPLE.parent.mkdir(parents=True, exist_ok=True)

    # Conecta (ou cria) o arquivo do banco de dados
    conn = sqlite3.connect(DATABASE_EXAMPLE)
    cursor = conn.cursor()

    # Criando tabelas de exemplo (Produtos e Vendas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        preco REAL NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER,
        quantidade INTEGER,
        data_venda TEXT,
        FOREIGN KEY (produto_id) REFERENCES produtos (id)
    )
    """)

    # Inserindo dados fictícios se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO produtos (nome, preco) VALUES (?, ?)", [
            ("Notebook", 4500.00),
            ("Smartphone", 2500.00),
            ("Teclado Mecânico", 3500.00)
        ])
        cursor.executemany("INSERT INTO vendas (produto_id, quantidade, data_venda) VALUES (?, ?, ?)", [
            (1, 2, "2026-06-01"),
            (2, 5, "2026-06-02"),
            (3, 10, "2026-06-03")
        ])
        conn.commit()
    
    conn.close()
    print("Banco de dados configurado com sucesso!")


def import_csv_to_table(csv_name: str, create_new_db: bool = False):
    """
    Lê um arquivo CSV usando Pandas e exporta direto para o SQLite.
    
    :param csv_name: Nome do arquivo CSV.
    :param create_new_db: Se True, cria um novo banco de dados com o nome da tabela.
    """

    table_name = csv_name.split(".")[0]  # Usa o nome do arquivo CSV como nome da tabela
    table_name = table_name.replace("-", "_").replace(" ", "_") # Sanitiza o nome da tabela (remove hifens e espaços)
    
    csv_path = CSV_FOLDER / csv_name
    if not csv_path.exists():
        print(f"Erro: O arquivo {csv_path} não foi encontrado.")
        return

    # Define o banco de dados destino
    if create_new_db:

        db_path = DATA_FOLDER / f"{table_name}.db"
        print(f"Criando/Conectando ao novo banco de dados: {db_path.name}")
    else:
        db_path = CENTRAL_DATABASE

    # CORREÇÃO 2: Inicializa a variável como None para evitar o UnboundLocalError
    conn = None

    try:
        # CORREÇÃO 1: sep=None + engine='python' detecta automaticamente se é vírgula, ponto e vírgula, etc.
        df = pd.read_csv(csv_path, sep=None, engine='python', encoding='utf-8-sig')
        
        # Limpa os nomes das colunas (remove espaços extras nas pontas)
        df.columns = df.columns.str.strip()

        # Conecta ao banco e envia o DataFrame completo
        conn = sqlite3.connect(db_path)
        
        # if_exists='append': se a tabela já existir, ele adiciona os dados.
        # index=False: não cria uma coluna extra para o índice do Pandas.
        df.to_sql(table_name, conn, if_exists="append", index=False)
        
        print(f"Sucesso: {len(df)} registros importados com Pandas para a tabela '{table_name}'.")

    except Exception as e:
        print(f"Erro na importação com Pandas no arquivo '{csv_name}': {e}")
    finally:
        # Só fecha a conexão se ela realmente chegou a ser aberta
        if conn is not None:
            conn.close()


def import_all_csv_files():
    """
    Importa todos os arquivos CSV da pasta CSV_FOLDER para o banco de dados central.
    """
    for csv_file in CSV_FOLDER.glob("*.csv"):
        import_csv_to_table(csv_file.name)


if __name__ == "__main__":
    import_all_csv_files()