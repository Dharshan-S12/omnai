import psycopg2

def init_db():
    conn = psycopg2.connect(host='127.0.0.1', port=5433, user='ai_user', dbname='postgres')
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("ALTER USER ai_user WITH PASSWORD 'ai_password';")
    cur.execute("SELECT 1 FROM pg_database WHERE datname='sovereign_db';")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE sovereign_db OWNER ai_user;")
        print("Created database sovereign_db successfully!")
    else:
        print("Database sovereign_db already exists.")
    conn.close()

if __name__ == '__main__':
    init_db()
