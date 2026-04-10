import sqlite3
import psycopg2
from uuid import UUID

# Configuration
SQLITE_DB = 'apps/backend/data/summarization.db'
POSTGRES_DSN = 'postgresql://postgres:postgres@localhost:5432/summarization'

def migrate():
    # This is a template script. Adjust table names and columns as per your schema.
    # Note: init_db() must be run first to create target tables in Postgres.
    
    try:
        sl_conn = sqlite3.connect(SQLITE_DB)
        pg_conn = psycopg2.connect(POSTGRES_DSN)
        sl_cur = sl_conn.cursor()
        pg_cur = pg_conn.cursor()
        
        # Example for 'users' table
        print("Migrating users...")
        sl_cur.execute("SELECT * FROM users")
        for row in sl_cur.fetchall():
            # Adjust mapping here
            pg_cur.execute("INSERT INTO app_users (...) VALUES (...)", row)
            
        pg_conn.commit()
        print("Migration complete.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        sl_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    print("Please customize this script with your specific table mappings before running.")
    # migrate()
