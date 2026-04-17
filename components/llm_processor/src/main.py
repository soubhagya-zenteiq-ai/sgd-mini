import json
import argparse
from typing import List, Optional
from llama_cpp import Llama
from pydantic import BaseModel, ValidationError


# -------------------------
# Pydantic Schema
# -------------------------

class QA(BaseModel):
    question: str
    answer: str
    source: str

    @classmethod
    def validate_item(cls, item, filename):
        q = item.get("question", "").strip()
        a = item.get("answer", "").strip()

        if not q or not a:
            raise ValueError("Empty QA")

        return cls(question=q, answer=a, source=filename)


# -------------------------
# Helpers
# -------------------------

def extract_json(text: str) -> Optional[str]:
    """
    Safer JSON extraction from LLM output.
    """
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return None


def chunk_text(text: str, chunk_size=1500, overlap=200):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


def generate_qas(llm, content: str, filename: str, retries: int = 3):
    qa_prompt = f"""
Extract 3-5 concise Question-Answer pairs from the following text.

STRICT RULES:
- Output ONLY valid JSON
- Do NOT add explanation
- Do NOT add text before or after JSON
- Format EXACTLY like:
[{{"question": "...", "answer": "..."}}]

Text:
{content}

JSON:
"""

    for attempt in range(retries):
        try:
            response = llm(
                qa_prompt,
                max_tokens=512,
                echo=False
            )

            text_response = response["choices"][0]["text"].strip()

            json_part = extract_json(text_response)
            if not json_part:
                raise ValueError("No JSON found")

            raw_qas = json.loads(json_part)

            validated_qas = []
            for item in raw_qas:
                qa_obj = QA.validate_item(item, filename)
                validated_qas.append(qa_obj.model_dump())

            return validated_qas

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            print(f"[Retry {attempt+1}] QA generation failed for {filename}: {e}")

    print(f"❌ Failed to generate QAs for {filename}")
    return []


# -------------------------
# Main Logic
# -------------------------

def generate_kb_and_qa(input_file: str, model_path: str, output_kb: str, output_qa: str):
    print(f"Loading model from {model_path}...")

    llm = Llama(
        model_path=model_path,
        n_ctx=32768,
        temperature=0.2,
        top_p=0.9,
        repeat_penalty=1.1,
        verbose=False
    )

    with open(input_file, "r") as f:
        documents = json.load(f)

    knowledge_base = ""
    all_qas = []

    total_failures = 0

    for doc in documents:
        filename = doc['filename']
        content = doc['content']

        print(f"Processing {filename}...")

        # -------------------------
        # Summary Generation
        # -------------------------
        summary_prompt = f"""
Provide a very detailed, comprehensive, and long-form summary of the following document.
Include all key facts, technical details, and important entities mentioned.

Document Content:
{content[:3000]}

Detailed Knowledge Base Entry:
"""

        try:
            summary_response = llm(
                summary_prompt,
                max_tokens=1024,
                echo=False
            )

            detailed_summary = summary_response["choices"][0]["text"].strip()

        except Exception as e:
            print(f"❌ Summary failed for {filename}: {e}")
            detailed_summary = "Summary generation failed."
            total_failures += 1

        knowledge_base += f"=== KNOWLEDGE BASE ENTRY: {filename} ===\n"
        knowledge_base += f"ORIGINAL SOURCE: {filename}\n"
        knowledge_base += f"DETAILED SUMMARY:\n{detailed_summary}\n\n"

        # -------------------------
        # QA Generation with Chunking
        # -------------------------
        chunks = chunk_text(content)

        for chunk in chunks:
            qas = generate_qas(llm, chunk, filename)
            if not qas:
                total_failures += 1
            all_qas.extend(qas)

    # -------------------------
    # Deduplicate QAs
    # -------------------------
    seen = set()
    unique_qas = []

    for qa in all_qas:
        key = (qa["question"], qa["answer"])
        if key not in seen:
            seen.add(key)
            unique_qas.append(qa)

    all_qas = unique_qas

    # -------------------------
    # Save Outputs
    # -------------------------
    with open(output_kb, "w") as f:
        f.write(knowledge_base)

    with open(output_qa, "w") as f:
        json.dump(all_qas, f, indent=2)

    # -------------------------
    # Metrics
    # -------------------------
    print("✅ Pipeline completed")
    print({
        "total_docs": len(documents),
        "total_qas": len(all_qas),
        "failures": total_failures
    })


# -------------------------
# Entry Point
# -------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", type=str, required=True)
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--output_kb", type=str, required=True)
    parser.add_argument("--output_qa", type=str, required=True)

    args = parser.parse_args()

    generate_kb_and_qa(
        args.input_file,
        args.model_path,
        args.output_kb,
        args.output_qa
    )