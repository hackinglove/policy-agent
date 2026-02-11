import sqlite3
import pandas as pd
from openai import OpenAI
import numpy as np

class RAGEngine:
    def __init__(self, config, db_path="policy_data.db"):
        self.config = config
        self.db_path = db_path
        self.api_key = config['summary'].get('api_key')
        self.base_url = config['summary'].get('base_url')
        self.model = config['summary'].get('model')
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def search_policies(self, query, limit=10):
        """Simple keyword search in DB"""
        conn = sqlite3.connect(self.db_path)
        # Using simple LIKE for now. For better RAG, vector embeddings are needed.
        # Given "Database file as knowledge base", we act as an interface to query SQL and then summarize.
        
        # Split query into keywords
        keywords = query.split()
        conditions = []
        params = []
        for kw in keywords:
            conditions.append("(title LIKE ? OR summary LIKE ?)")
            params.extend([f"%{kw}%", f"%{kw}%"])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"SELECT title, summary, publish_date, source_name, url FROM policies WHERE {where_clause} ORDER BY publish_date DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df

    def chat(self, user_query):
        """Chat with policy data"""
        # 1. Retrieve relevant policies
        # If query is asking about specific policy, keyword search works.
        # If query is "What is the trend?", we might need to fetch MORE recent data.
        
        # Heuristic: Fetch top 20 relevant items or top 20 latest if no keywords detected (simplistic)
        relevant_df = self.search_policies(user_query, limit=15)
        
        context_text = ""
        if not relevant_df.empty:
            for idx, row in relevant_df.iterrows():
                context_text += f"- [{row['publish_date']}] {row['title']} (Source: {row['source_name']})\n  Summary: {row['summary']}\n\n"
        else:
            context_text = "No specific policies found in database matching keywords."
            
        # 2. Build Prompt
        system_prompt = """You are a policy expert assistant. Use the provided Context Information (retrieved from a local policy database) to answer the user's question. 
        If the answer is not in the context, say so, but you can provide general knowledge if explicitly asked. 
        Cite the policy titles and dates when relevant."""
        
        user_prompt = f"""
Context Information:
{context_text}

User Question: {user_query}
"""
        
        # 3. Call LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return response.choices[0].message.content
