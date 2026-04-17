import os
import json
import argparse
from pathlib import Path

def ingest_md_files(input_dir, output_file):
    documents = []
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Directory {input_dir} does not exist.")
        return

    for md_file in input_path.glob("**/*.md"):
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append({
                "filename": str(md_file.relative_to(input_path)),
                "content": content
            })
            
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2)
    
    print(f"Ingested {len(documents)} files into {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str, required=True)
    parser.add_argument("--output_file", type=str, required=True)
    args = parser.parse_args()
    
    ingest_md_files(args.input_dir, args.output_file)
