from PyPDF2 import PdfReader

import faiss
import numpy as np

from nltk.tokenize import sent_tokenize

from sentence_transformers import SentenceTransformer

import fitz  # pymupdf

import requests

# def load_pdf(path):
#     reader = PdfReader(path)
#     text = ""
#     for page in reader.pages:
#         text += page.extract_text()
#     return text

def load_pdf_structured(path):
    doc = fitz.open(path)

    sections = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("blocks")

        for b in blocks:
            text = b[4].strip()
            if len(text) > 30:
                sections.append({
                    "text": text,
                    "page": page_num
                })

    return sections

# def chunk_text(text, chunk_size=5, overlap=2):
#     sentences = sent_tokenize(text)

#     chunks = []
#     i = 0

#     while i < len(sentences):
#         chunk = sentences[i:i + chunk_size]
#         chunks.append(" ".join(chunk))
#         i += (chunk_size - overlap)

#     return chunks

def build_chunks(sections):
    chunks = []
    temp = ""

    for s in sections:
        temp += s["text"] + " "

        if len(temp) > 800:
            chunks.append(temp.strip())
            temp = ""

    if temp:
        chunks.append(temp.strip())

    return chunks

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_text(chunks):
    return model.encode(chunks)

def create_index(embeddings):
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))
    return index

def search(query, index, chunks, k=3):
    query_vec = model.encode([query])
    distances, indices = index.search(np.array(query_vec), k)

    return [chunks[i] for i in indices[0]]

def simple_answer(query, contexts):
    return "Context:\n" + "\n".join(contexts)

def llm(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "gemma3:4b",
            "prompt": prompt,
            "stream": False
        }
    )
    return response.json()["response"]

def answer_with_llm(query, contexts):
    prompt = f"""
    Answer based only on context:

    {contexts}

    Question: {query}
    """
    return llm(prompt)

print("Loading PDF...")
text = load_pdf_structured("mca134.pdf")

print("Chunking...")
chunks = build_chunks(text)

print("Creating embeddings...")
embeddings = embed_text(chunks)

print("Building index...")
index = create_index(embeddings)

print("Ready!")

while True:
    query = input("Ask: ")

    context = search(query, index, chunks)
    print("\nRetrieved Context:\n", context)

    answer = answer_with_llm(query, context)

    print("\nFinal Answer:\n", answer)