"""
Migration script to add settled fields to the Expense table.
Run this script to update the database schema.
"""

import sqlite3
import psycopg2
import os
from datetime import datetime

def migrate():
    """
    Add settled, settled_at, and settled_by columns to the Expense table.
    """
    # Get database URL from environment variable or use default
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and database_url.startswith('postgresql'):
        # PostgreSQL database
        print("Migrating PostgreSQL database...")
        migrate_postgresql(database_url)
    else:
        # SQLite database (fallback)
        print("Migrating SQLite database...")
        migrate_sqlite()
        
    print("Migration completed successfully!")

def migrate_postgresql(database_url):
    """Migrate PostgreSQL database"""
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='expense' AND column_name='settled';")
        if cursor.fetchone() is None:
            # Add settled column
            cursor.execute("ALTER TABLE expense ADD COLUMN settled BOOLEAN DEFAULT FALSE;")
            print("Added 'settled' column")
            
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='expense' AND column_name='settled_at';")
        if cursor.fetchone() is None:
            # Add settled_at column
            cursor.execute("ALTER TABLE expense ADD COLUMN settled_at TIMESTAMP;")
            print("Added 'settled_at' column")
            
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='expense' AND column_name='settled_by';")
        if cursor.fetchone() is None:
            # Add settled_by column
            cursor.execute("ALTER TABLE expense ADD COLUMN settled_by VARCHAR(120) REFERENCES \"user\"(id);")
            print("Added 'settled_by' column")
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error migrating PostgreSQL database: {e}")
        raise

def migrate_sqlite():
    """Migrate SQLite database"""
    try:
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(expense);")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'settled' not in columns:
            # Add settled column
            cursor.execute("ALTER TABLE expense ADD COLUMN settled BOOLEAN DEFAULT 0;")
            print("Added 'settled' column")
            
        if 'settled_at' not in columns:
            # Add settled_at column
            cursor.execute("ALTER TABLE expense ADD COLUMN settled_at TIMESTAMP;")
            print("Added 'settled_at' column")
            
        if 'settled_by' not in columns:
            # Add settled_by column
            cursor.execute("ALTER TABLE expense ADD COLUMN settled_by VARCHAR(120) REFERENCES user(id);")
            print("Added 'settled_by' column")
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error migrating SQLite database: {e}")
        raise

if __name__ == "__main__":
    migrate()
