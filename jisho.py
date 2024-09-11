"""Get meanings and readings of kanji from jisho and writes to jisho.csv"""
from jisho_api.kanji import Kanji
import csv

kanjis = None
with open("kotoba.csv", "r", encoding="UTF-8") as file:
    reader = csv.reader(file)
    kanjis = [row[0] for row in reader]
    kanjis.pop(0)

jisho_list = []
for kanji in kanjis:
    r = Kanji.request(kanji)
    # print(r)
    if not r:
        jisho_list.append(
            {"kanji": kanji, "meanings": "N/A", "kunyomi": "N/A", "onyomi": "N/A"}
        )
        continue

    meanings = r.data.main_meanings
    kunyomi, onyomi = r.data.main_readings
    # print(meanings, kunyomi, onyomi)

    jisho_list.append(
        {
            "kanji": kanji,
            "meanings": ", ".join(meanings),
            "kunyomi": ", ".join(kunyomi[1] or ["N/A"]),
            "onyomi": ", ".join(onyomi[1] or ["N/A"]),
        }
    )
# print(jisho_list)

with open("jisho.csv", "w", encoding="UTF-8") as file:
    fieldnames = ["kanji", "meanings", "kunyomi", "onyomi"]
    writer = csv.DictWriter(file, fieldnames)
    writer.writeheader()
    writer.writerows(jisho_list)
