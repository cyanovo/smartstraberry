"""Loopback-only OpenAI-compatible CPU embedding endpoint for the local stack."""

from pathlib import Path
from threading import Lock

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModel, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
MODEL = "BAAI/bge-small-zh-v1.5"
PATH = ROOT / ".runtime/models/bge-small-zh-v1.5"
torch.set_num_threads(4)
tokenizer = AutoTokenizer.from_pretrained(PATH, local_files_only=True)
model = AutoModel.from_pretrained(PATH, local_files_only=True).eval()
lock = Lock()
app = FastAPI(docs_url=None, redoc_url=None)


class Request(BaseModel):
    model: str
    input: str | list[str] = Field(min_length=1, max_length=16384)


@app.get("/health")
def health():
    return {"model": MODEL, "dimension": 512, "device": "cpu"}


@app.post("/v1/embeddings")
def embeddings(request: Request):
    texts = [request.input] if isinstance(request.input, str) else request.input
    if request.model != MODEL:
        raise HTTPException(400, "Unknown local embedding model")
    if len(texts) > 64 or any(len(text) > 16384 for text in texts):
        raise HTTPException(413, "Batch or text length exceeds local limits")
    with lock, torch.inference_mode():
        tokens = tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
        vectors = torch.nn.functional.normalize(model(**tokens).last_hidden_state[:, 0], p=2, dim=1)
    return {
        "object": "list", "model": MODEL,
        "data": [{"object": "embedding", "index": index, "embedding": value} for index, value in enumerate(vectors.tolist())],
        "usage": {"prompt_tokens": int(tokens["attention_mask"].sum()), "total_tokens": int(tokens["attention_mask"].sum())},
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=18081)
