import sqlite3
import json
import os
from datetime import datetime

def export_db_to_json():
    db_path = "policy_data.db"
    output_dir = "docs"
    output_file = os.path.join(output_dir, "policies.json")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    if not os.path.exists(db_path):
        print("Database not found, creating empty json.")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Export all policies sorted by date
    c.execute("SELECT id, title, source_name, publish_date, url, summary FROM policies ORDER BY publish_date DESC")
    rows = c.fetchall()
    
    policies = [dict(row) for row in rows]
    
    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(policies, f, ensure_ascii=False, indent=2)
        
    print(f"Exported {len(policies)} policies to {output_file}")
    
    # Also generate a metadata file for stats
    stats = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_count": len(policies),
        "sources": list(set(p['source_name'] for p in policies))
    }
    with open(os.path.join(output_dir, "stats.json"), 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    export_db_to_json()
