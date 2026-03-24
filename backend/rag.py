# ─────────────────────────────────────────
# rag.py - RAG System with Crisis + Resources
# ─────────────────────────────────────────

import os
import anthropic
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from crisis import detect_crisis, get_crisis_response
from resources import get_resources_for_question

load_dotenv()

print("⏳ Loading RAG system...")
model = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path="../data/chroma_db")
collection = client.get_collection("gita_verses")
anthropic_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)
print("✅ RAG system ready!")

def search_relevant_verses(question, top_k=3):
    query_embedding = model.encode([question]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    return results

def detect_language(text):
    hindi_chars = set('अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह')
    for char in text:
        if char in hindi_chars:
            return 'hindi'
    return 'english'

def build_prompt(question, search_results, language):
    verses_text = ""
    for doc, meta in zip(
        search_results['documents'][0],
        search_results['metadatas'][0]
    ):
        verses_text += f"\n[{meta['source']}]"
        verses_text += f"\nSanskrit: {meta['sanskrit'][:200]}"
        verses_text += f"\nHindi: {meta['hindi'][:200]}\n"

    if language == 'hindi':
        prompt = f"""आप एक बुद्धिमान आध्यात्मिक गुरु हैं जो केवल भगवद्गीता के आधार पर उत्तर देते हैं।

यहाँ प्रासंगिक श्लोक हैं:
{verses_text}

इस प्रश्न का उत्तर केवल ऊपर दिए गए श्लोकों के आधार पर दें:
प्रश्न: {question}

नियम:
- उत्तर हिंदी में दें
- गर्मजोशी और प्रेम से बोलें
- श्लोक का स्रोत जरूर बताएं
- उत्तर 150 शब्दों से कम रखें
- अंत में प्रेरणादायक वाक्य लिखें
"""
    else:
        prompt = f"""You are a wise spiritual guru who answers ONLY from the Bhagavad Gita.

Here are the most relevant verses:
{verses_text}

Answer this question using ONLY the verses above:
Question: {question}

Rules:
- Answer warmly like a loving guru
- Always cite the chapter and verse number
- Keep answer under 150 words
- End with an encouraging line
"""
    return prompt

def ask_gita(question):
    print(f"\n🔍 Searching: '{question}'")

    # Step 1: Detect language
    language = detect_language(question)
    print(f"🌐 Language: {language}")

    # Step 2: Crisis check FIRST
    if detect_crisis(question):
        print("🆘 Crisis detected!")
        return get_crisis_response(language)

    # Step 3: Search verses
    search_results = search_relevant_verses(question)
    print(f"✅ Found {len(search_results['documents'][0])} verses")

    # Step 4: Build prompt
    prompt = build_prompt(question, search_results, language)

    # Step 5: Ask Claude
    print("⏳ Asking Claude AI...")
    message = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    answer = message.content[0].text
    sources = [
        meta['source']
        for meta in search_results['metadatas'][0]
    ]

    # Step 6: Get related resources
    resources = get_resources_for_question(question)
    print(f"📚 Found {len(resources)} related resources")

    return {
        "answer": answer,
        "sources": sources,
        "language": language,
        "is_crisis": False,
        "resources": resources
    }

# Test
if __name__ == "__main__":
    print("\n🕉️  Testing RAG System\n")

    tests = [
        "How do I deal with fear?",
        "I want to die, I lost everything",
        "What is karma yoga?",
        "मन को कैसे नियंत्रित करें?"
    ]

    for q in tests:
        print(f"\n{'='*50}")
        print(f"❓ {q}")
        result = ask_gita(q)
        print(f"🆘 Crisis: {result['is_crisis']}")
        print(f"📖 Answer: {result['answer'][:100]}...")
        print(f"📚 Resources: {len(result['resources'])} links")
        print(f"{'='*50}")