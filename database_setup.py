"""Script rápido para criar e popular o banco de dados"""

import sqlite3
import csv

from paths import CSV_FOLDER
from paths import DATABASE_EXAMPLE

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


def import_csv_to_table(csv_name: str, table_name: str, columns: list, create_new_db: bool = True):
    """
    Lê um arquivo CSV e insere os dados na tabela SQL correspondente.
    
    :param csv_name: Nome do arquivo CSV (localizado na pasta CSV_FOLDER).
    :param table_name: Nome da tabela onde os dados serão inseridos.
    :param columns: Lista com o nome das colunas na ordem em que aparecem no CSV.
    :param create_new_db: Se True, cria um novo banco de dados com o nome da tabela.
    """

    table_name = table_name.replace("-", "_").replace(" ", "_")
    csv_path = CSV_FOLDER / csv_name

    if not csv_path.exists():
        print(f"Erro: O arquivo {csv_path} não foi encontrado.")
        return

    # Define qual banco de dados usar
    if create_new_db:
        # Cria o caminho para o novo banco na mesma pasta do banco padrão, ex: caminho/para/vendas.db
        db_path = DATABASE_EXAMPLE.parent / f"{table_name}.db"
        print(f"Criando/Conectando ao novo banco de dados: {db_path.name}")
    else:
        db_path = DATABASE_EXAMPLE

    cleaned_columns = [col.strip().replace("\ufeff", "") for col in columns]

    # Monta a query de inserção dinamicamente: INSERT INTO tabela (col1, col2) VALUES (?, ?)
    placeholders = ", ".join(["?"] * len(cleaned_columns))
    columns_str = ", ".join([f'"{col}"' for col in cleaned_columns])
    insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Se for um banco novo, precisamos criar a tabela antes de inserir os dados
        if create_new_db:
            # Cria colunas dinamicamente como TEXT (padrão seguro para CSV)
            create_columns = ", ".join([f"{col} TEXT" for col in cleaned_columns])
            create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({create_columns})"
            cursor.execute(create_table_query)

        with open(csv_path, mode="r", encoding="utf-8") as file:
            csv_reader = csv.reader(file)
            next(csv_reader)  # Pula a linha do cabeçalho do CSV
            
            # Lê todas as linhas restantes
            data_to_insert = [row for row in csv_reader if row]

        # Executa a inserção em lote
        cursor.executemany(insert_query, data_to_insert)
        conn.commit()
        print(f"Sucesso: {len(data_to_insert)} registros importados do CSV para a tabela '{table_name}' no banco '{db_path.name}'.")

    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    import_csv_to_table("searched_with_rising-searches_BR_20260308-1139_20260608-1139.csv", "searched_with_rising-searches_BR_20260308-1139_20260608-1139", ["query", "search_interest", "increase_percent"])