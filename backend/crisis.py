# ─────────────────────────────────────────
# crisis.py - Crisis Detection System
# ─────────────────────────────────────────

# Crisis keywords in English and Hindi
CRISIS_KEYWORDS = [
    # English
    "want to die", "kill myself", "end my life",
    "suicide", "suicidal", "no reason to live",
    "want to end it", "cant go on", "can't go on",
    "worthless", "rather be dead", "better off dead",
    "want to disappear", "life is pointless",
    "nobody cares", "end everything", "i want to die",
    "i lost everything",

    # Hindi
    "मरना चाहता", "मरना चाहती", "जीना नहीं चाहता",
    "जीना नहीं चाहती", "आत्महत्या", "खुद को खत्म",
    "जिंदगी बेकार", "मर जाना चाहता", "सब खत्म करना",
    "जीवन समाप्त", "मुझे नहीं जीना",
]

CRISIS_RESPONSE_ENGLISH = """
Dear soul, I can feel the pain in your words. 🙏

Please know that you are not alone. The Bhagavad Gita 
teaches us in Chapter 2, Verse 20:

"The soul is never born nor dies at any time. 
It is unborn, eternal, ever-existing and primeval."

Your life has infinite value. This pain is temporary, 
but your soul is eternal. Please reach out for help:

🆘 iCall India: 9152987821
🆘 Vandrevala Foundation: 1860-2662-345
🆘 AASRA: 9820466627

These wonderful people are available 24/7. 
You matter. Please call them right now. 🙏
"""

CRISIS_RESPONSE_HINDI = """
प्रिय आत्मा, आपके शब्दों में दर्द महसूस हो रहा है। 🙏

जान लीजिए कि आप अकेले नहीं हैं। भगवद्गीता अध्याय 2, 
श्लोक 20 में कहा गया है:

"आत्मा कभी जन्म नहीं लेती और न कभी मरती है। 
यह अजन्मा, नित्य, शाश्वत और पुरातन है।"

आपका जीवन अनमोल है। यह दर्द अस्थायी है।
कृपया अभी मदद लें:

🆘 iCall India: 9152987821
🆘 Vandrevala Foundation: 1860-2662-345
🆘 AASRA: 9820466627

ये लोग 24/7 उपलब्ध हैं।
आप महत्वपूर्ण हैं। कृपया अभी call करें। 🙏
"""

def detect_crisis(text: str) -> bool:
    """Check if message contains crisis keywords"""
    text_lower = text.lower()
    for keyword in CRISIS_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    return False

def get_crisis_response(language: str) -> dict:
    """Return crisis response based on language"""
    if language == "hindi":
        answer = CRISIS_RESPONSE_HINDI
    else:
        answer = CRISIS_RESPONSE_ENGLISH

    return {
        "answer": answer,
        "sources": ["Bhagavad Gita Chapter 2, Verse 20"],
        "language": language,
        "is_crisis": True,
        "resources": [
            {
                "title": "iCall Mental Health Support",
                "url": "https://icallhelpline.org",
                "type": "mental_health"
            },
            {
                "title": "Vandrevala Foundation",
                "url": "https://www.vandrevalafoundation.com",
                "type": "mental_health"
            }
        ]
    }