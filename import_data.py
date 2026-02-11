import sqlite3
import json
import os
from policy_agent.storage import Storage

def import_json_to_db():
    json_path = "docs/policies.json"
    db_path = "policy_data.db"
    
    if not os.path.exists(json_path):
        print(f"{json_path} not found. Starting with empty DB.")
        return

    # Initialize DB using Storage class to create tables
    storage = Storage(db_path)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            policies = json.load(f)
        except json.JSONDecodeError:
            print("Invalid JSON, skipping import.")
            return

    if not policies:
        print("JSON is empty.")
        return

    print(f"Importing {len(policies)} policies from {json_path}...")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    count = 0
    for p in policies:
        # Check existence by URL
        c.execute("SELECT id FROM policies WHERE url = ?", (p['url'],))
        if c.fetchone():
            continue
            
        # Insert (Assuming schema matches Storage.save_policy logic mostly)
        # Note: policies.json keys: id, title, source_name, publish_date, url, summary
        # storage table: id, title, source_name, publish_date, url, summary, crawled_at
        
        c.execute('''
            INSERT INTO policies (title, source_name, publish_date, url, summary)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            p.get('title'),
            p.get('source_name'),
            p.get('publish_date'),
            p.get('url'),
            p.get('summary', '')
        ))
        count += 1
        
    conn.commit()
    conn.close()
    print(f"Imported {count} new policies (duplicates skipped).")

if __name__ == "__main__":
    import_json_to_db()
