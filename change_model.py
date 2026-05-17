import sys

with open('rag/embeddings.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Change model to smaller/faster version
content = content.replace('paraphrase-multilingual-MiniLM-L12-v2', 'paraphrase-multilingual-MiniLM-L6-v2')

with open('rag/embeddings.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Switched to smaller model: paraphrase-multilingual-MiniLM-L6-v2')
