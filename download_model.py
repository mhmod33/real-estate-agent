"""
Script to download and save the embedding model locally.
Run once during build to avoid downloading at runtime.
"""
import os
import sys

BASE_DIR = os.path.dirname(__file__)
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
MODEL_PATH = os.path.join(BASE_DIR, "models", "multilingual-minilm")


def download_model():
    if os.path.exists(MODEL_PATH):
        print(f"Model already exists at {MODEL_PATH}, skipping download.")
        return

    print(f"Downloading model: {MODEL_NAME} ...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    os.makedirs(MODEL_PATH, exist_ok=True)
    model.save(MODEL_PATH)
    print(f"Model saved to: {MODEL_PATH}")


if __name__ == "__main__":
    download_model()
