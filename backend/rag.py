# ─────────────────────────────────────────
# rag.py - RAG System with Crisis + Resources + Context
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


def build_messages(question, search_results, language, conversation_history=None):
    """
    Build messages array for Claude.
    conversation_history = list of past {question, answer} dicts from this session.
    Last 5 messages are passed for context memory.
    """
    verses_text = ""
    for doc, meta in zip(
        search_results['documents'][0],
        search_results['metadatas'][0]
    ):
        verses_text += f"\n[{meta['source']}]"
        verses_text += f"\nSanskrit: {meta['sanskrit'][:200]}"
        verses_text += f"\nHindi: {meta['hindi'][:200]}\n"

    # System instruction based on language
    if language == 'hindi':
        system_prompt = f"""आप एक बुद्धिमान आध्यात्मिक गुरु हैं जो केवल भगवद्गीता के आधार पर उत्तर देते हैं।

यहाँ प्रासंगिक श्लोक हैं:
{verses_text}

नियम:
- उत्तर हिंदी में दें
- गर्मजोशी और प्रेम से बोलें
- श्लोक का स्रोत जरूर बताएं
- उत्तर 150 शब्दों से कम रखें
- अंत में प्रेरणादायक वाक्य लिखें
- यदि पिछली बातचीत है तो उसका संदर्भ लें"""
    else:
        system_prompt = f"""You are a wise spiritual guru who answers ONLY from the Bhagavad Gita.

Here are the most relevant verses:
{verses_text}

Rules:
- Answer warmly like a loving guru
- Always cite the chapter and verse number
- Keep answer under 150 words
- End with an encouraging line
- If there is prior conversation, refer to it naturally"""

    # Build messages array with history (last 5 exchanges)
    messages = []

    if conversation_history:
        # Only take last 5 exchanges to keep context window small
        recent_history = conversation_history[-5:]
        for entry in recent_history:
            messages.append({"role": "user", "content": entry["question"]})
            messages.append({"role": "assistant", "content": entry["answer"]})

    # Add current question
    messages.append({"role": "user", "content": question})

    return system_prompt, messages


def ask_gita(question, conversation_history=None):
    """
    conversation_history: list of {question, answer} dicts from current session.
    Pass None or [] for a fresh session with no context.
    """
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

    # Step 4: Build messages with history
    system_prompt, messages = build_messages(
        question, search_results, language, conversation_history
    )

    # Step 5: Ask Claude with context
    print("⏳ Asking Claude AI...")
    message = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=system_prompt,
        messages=messages
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