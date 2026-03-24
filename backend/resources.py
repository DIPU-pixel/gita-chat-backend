# ─────────────────────────────────────────
# resources.py - PDF & Resource Links
# ─────────────────────────────────────────

# Topic keywords mapped to resources
TOPIC_RESOURCES = {
    "fear": {
        "keywords": ["fear", "anxiety", "scared", "afraid", "डर", "भय", "चिंता"],
        "resources": [
            {
                "title": "Bhagavad Gita Chapter 2 - Overcoming Fear",
                "url": "https://gitasupersite.iitk.ac.in/srimad?language=dv&field_chapter_value=2",
                "type": "chapter"
            },
            {
                "title": "Sankhya Yoga - Full PDF",
                "url": "https://www.holy-bhagavad-gita.org/chapter/2",
                "type": "pdf"
            }
        ]
    },
    "karma": {
        "keywords": ["karma", "duty", "action", "work", "कर्म", "कर्तव्य"],
        "resources": [
            {
                "title": "Karma Yoga - Chapter 3",
                "url": "https://gitasupersite.iitk.ac.in/srimad?language=dv&field_chapter_value=3",
                "type": "chapter"
            },
            {
                "title": "Karma Yoga Full Explanation",
                "url": "https://www.holy-bhagavad-gita.org/chapter/3",
                "type": "pdf"
            }
        ]
    },
    "mind": {
        "keywords": ["mind", "control", "meditation", "focus", "मन", "ध्यान", "एकाग्रता"],
        "resources": [
            {
                "title": "Dhyana Yoga - Chapter 6",
                "url": "https://gitasupersite.iitk.ac.in/srimad?language=dv&field_chapter_value=6",
                "type": "chapter"
            },
            {
                "title": "Meditation Guide from Gita",
                "url": "https://www.holy-bhagavad-gita.org/chapter/6",
                "type": "pdf"
            }
        ]
    },
    "devotion": {
        "keywords": ["devotion", "love", "god", "bhakti", "worship", "भक्ति", "प्रेम", "ईश्वर"],
        "resources": [
            {
                "title": "Bhakti Yoga - Chapter 12",
                "url": "https://gitasupersite.iitk.ac.in/srimad?language=dv&field_chapter_value=12",
                "type": "chapter"
            },
            {
                "title": "Path of Devotion PDF",
                "url": "https://www.holy-bhagavad-gita.org/chapter/12",
                "type": "pdf"
            }
        ]
    },
    "death": {
        "keywords": ["death", "die", "soul", "afterlife", "rebirth", "मृत्यु", "आत्मा", "मोक्ष"],
        "resources": [
            {
                "title": "The Eternal Soul - Chapter 2",
                "url": "https://gitasupersite.iitk.ac.in/srimad?language=dv&field_chapter_value=2",
                "type": "chapter"
            },
            {
                "title": "Soul and Liberation PDF",
                "url": "https://www.holy-bhagavad-gita.org/chapter/2",
                "type": "pdf"
            }
        ]
    },
    "peace": {
        "keywords": ["peace", "happiness", "joy", "calm", "शांति", "खुशी", "आनंद"],
        "resources": [
            {
                "title": "Finding Inner Peace - Chapter 5",
                "url": "https://gitasupersite.iitk.ac.in/srimad?language=dv&field_chapter_value=5",
                "type": "chapter"
            },
            {
                "title": "Complete Bhagavad Gita PDF",
                "url": "https://sacred-texts.com/hin/gita/index.htm",
                "type": "pdf"
            }
        ]
    },
    "default": {
        "resources": [
            {
                "title": "Complete Bhagavad Gita Online",
                "url": "https://gitasupersite.iitk.ac.in",
                "type": "website"
            },
            {
                "title": "Bhagavad Gita PDF - Sacred Texts",
                "url": "https://sacred-texts.com/hin/gita/index.htm",
                "type": "pdf"
            },
            {
                "title": "Wisdomlib - Hindu Scriptures",
                "url": "https://www.wisdomlib.org/hinduism",
                "type": "website"
            }
        ]
    }
}

def get_resources_for_question(question: str) -> list:
    """Find relevant resources based on question keywords"""
    question_lower = question.lower()

    for topic, data in TOPIC_RESOURCES.items():
        if topic == "default":
            continue
        keywords = data.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in question_lower:
                return data["resources"]

    # Return default resources if no topic matched
    return TOPIC_RESOURCES["default"]["resources"]