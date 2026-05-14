import chromadb

client = chromadb.PersistentClient(path="app/data/vector_store")
collections = client.list_collections()
print(f"=== ChromaDB - {len(collections)} collection(s) ===\n")

for c in collections:
    count = c.count()
    print(f"Collection: {c.name} ({count} chunks)")
    if count > 0:
        sample = c.peek(limit=3)
        for i, doc in enumerate(sample["documents"]):
            meta = sample["metadatas"][i] if sample["metadatas"] else {}
            src = meta.get("source", "?")
            origin = meta.get("origin_key", "?")
            fname = meta.get("filename", "?")
            print(f"  [{i+1}] source={src} | origin={origin} | file={fname}")
            print(f"      {doc[:120]}...")
    print()
