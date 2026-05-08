import sqlite3

def test_db(db_path, table_name):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    
    for row in cursor.execute(f"""
            SELECT * from {table_name}
            """):
        print(row)
    cursor.close()
    
test_db('./db/long_term_memory.db', 'memory_store')