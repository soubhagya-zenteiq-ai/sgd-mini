import argparse
import os
import json
import boto3
import psycopg2
from pathlib import Path

def save_to_minio(file_path, bucket, object_name):
    s3 = boto3.client(
        's3',
        endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://minio-service:9000'),
        aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
        aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    )
    try:
        # Check if bucket exists, if not create it
        if bucket not in [b['Name'] for b in s3.list_buckets()['Buckets']]:
            s3.create_bucket(Bucket=bucket)
            print(f"Created bucket: {bucket}")
            
        s3.upload_file(file_path, bucket, object_name)
        print(f"Uploaded {file_path} to MinIO as {object_name}")
    except Exception as e:
        print(f"Error uploading to MinIO: {e}")

def save_to_postgres(qa_file, kb_file):
    conn_str = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/dbname')
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        # Create tables if not exist
        cur.execute("CREATE TABLE IF NOT EXISTS knowledge_base (id SERIAL PRIMARY KEY, source_file TEXT, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        cur.execute("CREATE TABLE IF NOT EXISTS qas (id SERIAL PRIMARY KEY, source_file TEXT, question TEXT, answer TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        
        # Insert KB
        with open(kb_file, 'r') as f:
            kb_data = json.load(f)
            for entry in kb_data:
                cur.execute("INSERT INTO knowledge_base (source_file, content) VALUES (%s, %s)", (entry['filename'], entry['summary']))
        
        # Insert QAs
        with open(qa_file, 'r') as f:
            qas = json.load(f)
            for qa in qas:
                cur.execute("INSERT INTO qas (source_file, question, answer) VALUES (%s, %s, %s)", (qa['source'], qa['question'], qa['answer']))
        
        conn.commit()
        cur.close()
        conn.close()
        print("Data saved to PostgreSQL successfully.")
    except Exception as e:
        print(f"Error saving to PostgreSQL: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--kb_file", type=str, required=True)
    parser.add_argument("--qa_file", type=str, required=True)
    parser.add_argument("--storage_type", type=str, choices=['minio', 'postgres', 'both'], default='both')
    args = parser.parse_args()
    
    if args.storage_type in ['minio', 'both']:
        save_to_minio(args.kb_file, 'rag-kb', 'knowledge_base.json')
        save_to_minio(args.qa_file, 'rag-qa', 'qas.json')
        
    if args.storage_type in ['postgres', 'both']:
        save_to_postgres(args.qa_file, args.kb_file)
