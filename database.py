import sqlite3

DB_PATH = "requisicoes.db"

def inicializar_banco():
    """Cria a tabela no banco de dados se não existir."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requisicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_fiscal TEXT NOT NULL,
            data_emissao TEXT NOT NULL,
            status TEXT DEFAULT 'pendente'
        )
    """)
    conn.commit()
    conn.close()

def adicionar_requisicao(nota_fiscal, data_emissao):
    """Adiciona uma nova requisição no banco."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO requisicoes (nota_fiscal, data_emissao) VALUES (?, ?)", (nota_fiscal, data_emissao))
    conn.commit()
    conn.close()

def buscar_requisicao_pendente():
    """Retorna a próxima requisição pendente."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nota_fiscal, data_emissao FROM requisicoes WHERE status = 'pendente' LIMIT 1")
    requisicao = cursor.fetchone()
    conn.close()
    return requisicao

def marcar_como_processada(requisicao_id):
    """Marca uma requisição como processada."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE requisicoes SET status = 'processada' WHERE id = ?", (requisicao_id,))
    conn.commit()
    conn.close()

# Inicializa o banco na primeira execução
inicializar_banco()
