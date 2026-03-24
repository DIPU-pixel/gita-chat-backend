import requests
import json
import time

print("🕉️ Fetching Full Bhagavad Gita Data...")
print("Languages: English + Hindi + Sanskrit\n")

all_verses = []

chapter_verse_count = {
    1: 47, 2: 72, 3: 43, 4: 42, 5: 29,
    6: 47, 7: 30, 8: 28, 9: 34, 10: 42,
    11: 55, 12: 20, 13: 35, 14: 27, 15: 20,
    16: 24, 17: 28, 18: 78
}

for chapter, verse_count in chapter_verse_count.items():
    print(f"📖 Fetching Chapter {chapter} ({verse_count} verses)...")

    for verse in range(1, verse_count + 1):
        try:
            url = f"https://gita-api.vercel.app/eng/verses/{chapter}/{verse}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                verse_obj = {
                    "chapter": chapter,
                    "verse": verse,
                    "english": data.get("meaning", ""),
                    "sanskrit": data.get("slok", ""),
                    "transliteration": data.get("transliteration", ""),
                    "hindi": data.get("tej", {}).get("ht", ""),
                    "source": f"Bhagavad Gita Chapter {chapter}, Verse {verse}"
                }

                all_verses.append(verse_obj)
                print(f"  ✅ Chapter {chapter}, Verse {verse}")
            else:
                print(f"  ⚠️ Skipped Chapter {chapter}, Verse {verse} → Status {response.status_code}")

            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ Error Chapter {chapter}, Verse {verse}: {e}")
            continue

# Save
print(f"\n💾 Saving {len(all_verses)} verses...")
with open('../data/gita_multilingual.json', 'w', encoding='utf-8') as f:
    json.dump(all_verses, f, ensure_ascii=False, indent=2)

print(f"\n✅ Done! Saved {len(all_verses)} verses!")
print("📁 File: data/gita_multilingual.json")