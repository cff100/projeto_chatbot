"""Script rápido para criar e popular o banco de dados"""


import sqlite3

def criar_banco_exemplo():
    # Conecta (ou cria) o arquivo do banco de dados
    conn = sqlite3.connect("dados/database.db")
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

if __name__ == "__main__":
    criar_banco_exemplo()