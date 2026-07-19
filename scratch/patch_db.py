import sqlite3
import os

db_path = "nhai_dashboard.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE refresh_history ADD COLUMN trigger_source VARCHAR DEFAULT 'Manual'")
        conn.commit()
        print("Column added successfully.")
    except Exception as e:
        print(f"Error adding column: {e}")
    conn.close()
else:
    print("DB not found.")
