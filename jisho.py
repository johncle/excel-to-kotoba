"""Gets meanings and readings of kanji from jisho and writes to jisho.csv"""
import csv
from jisho_api.kanji import Kanji

kanji_dict = None
with open("kotoba_kanji.csv", "r", encoding="utf-8") as file:
    reader = csv.reader(file)
    kanji_dict = [row[0] for row in reader]
    kanji_dict.pop(0)

jisho_list = []
for kanji in kanji_dict:
    r = Kanji.request(kanji)
    if not r:
        jisho_list.append(
            {"kanji": kanji, "meanings": "N/A", "kunyomi": "N/A", "onyomi": "N/A"}
        )
    else:
        meanings = r.data.main_meanings
        kunyomi, onyomi = r.data.main_readings
        jisho_list.append(
            {
                "kanji": kanji,
                "meanings": ", ".join(meanings or ["N/A"]),
                "kunyomi": ", ".join(kunyomi[1] or ["N/A"]),
                "onyomi": ", ".join(onyomi[1] or ["N/A"]),
            }
        )

with open("jisho.csv", "w", encoding="utf-8") as file:
    fieldnames = ["kanji", "meanings", "kunyomi", "onyomi"]
    writer = csv.DictWriter(file, fieldnames)
    writer.writeheader()
    writer.writerows(jisho_list)
