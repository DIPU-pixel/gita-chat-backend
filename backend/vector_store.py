import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

def load_all_gita_chapters():
    """Load all 18 chapters from SrimadBhagvadGita folder"""
    all_verses = []
    data_path = "../data/SrimadBhagvadGita"
    
    for chapter_num in range(1, 19):
        file_path = f"{data_path}/bhagavad_gita_chapter_{chapter_num}.json"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            verses = data['BhagavadGitaChapter']
            
            for verse in verses:
                # Get Sanskrit text
                sanskrit = verse.get('text', '')
                
                # Get Hindi commentary
                hindi = ''
                commentaries = verse.get('commentaries', {})
                if 'Swami Ramsukhdas' in commentaries:
                    hindi = commentaries['Swami Ramsukhdas'][:500]
                elif commentaries:
                    first_key = list(commentaries.keys())[0]
                    hindi = commentaries[first_key][:500]
                
                verse_obj = {
                    "chapter": verse['chapter'],
                    "verse": verse['verse'],
                    "sanskrit": sanskrit,
                    "hindi": hindi,
                    "source": f"Bhagavad Gita Chapter {verse['chapter']}, Verse {verse['verse']}"
                }
                all_verses.append(verse_obj)
            
            print(f"✅ Chapter {chapter_num} loaded → {len(verses)} verses")
            
        except Exception as e:
            print(f"❌ Error loading chapter {chapter_num}: {e}")
    
    print(f"\n📖 Total verses loaded: {len(all_verses)}")
    return all_verses

def setup_chromadb():
    """Setup fresh ChromaDB"""
    client = chromadb.PersistentClient(path="../data/chroma_db")
    
    try:
        client.delete_collection("gita_verses")
        print("🗑️  Old collection deleted")
    except:
        pass
    
    collection = client.create_collection(
        name="gita_verses",
        metadata={"heuristic": "cosine"}
    )
    print("✅ Fresh ChromaDB collection created")
    return collection

def store_all_verses(collection, verses):
    """Convert verses to embeddings and store"""
    print("\n⏳ Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Embedding model loaded!")
    
    # Process in batches of 50
    batch_size = 50
    total = len(verses)
    
    for i in range(0, total, batch_size):
        batch = verses[i:i + batch_size]
        
        texts = []
        ids = []
        metadatas = []
        
        for j, verse in enumerate(batch):
            # Combine Sanskrit + Hindi for better search
            search_text = f"{verse['sanskrit']} {verse['hindi'][:200]}"
            texts.append(search_text)
            ids.append(f"verse_{i+j}")
            metadatas.append({
                "chapter": verse['chapter'],
                "verse": verse['verse'],
                "sanskrit": verse['sanskrit'][:200],
                "hindi": verse['hindi'][:200],
                "source": verse['source']
            })
        
        embeddings = model.encode(texts).tolist()
        
        collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
        
        print(f"✅ Stored verses {i+1} to {min(i+batch_size, total)} / {total}")
    
    print(f"\n🎉 All {total} verses stored in ChromaDB!")

def search_verses(query, top_k=3):
    """Search for relevant verses"""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    client = chromadb.PersistentClient(path="../data/chroma_db")
    collection = client.get_collection("gita_verses")
    
    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    return results

if __name__ == "__main__":
    print("🕉️  Loading Full Bhagavad Gita into ChromaDB\n")
    
    # Load all chapters
    verses = load_all_gita_chapters()
    
    # Setup database
    collection = setup_chromadb()
    
    # Store everything
    store_all_verses(collection, verses)
    
    # Test search
    print("\n🔍 Testing search...")
    results = search_verses("How to control mind and fear?")
    
    print("\n📖 Top matching verses:\n")
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        print(f"Source: {meta['source']}")
        print(f"Sanskrit: {meta['sanskrit'][:80]}...")
        print(f"Hindi: {meta['hindi'][:80]}...")
        print()
    
    print("✅ Full Gita Vector Store Ready!")