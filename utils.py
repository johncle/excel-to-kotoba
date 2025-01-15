"""Miscellaneous utility functions"""
import sys
import csv
import re
from jisho_api.kanji import Kanji


def get_ranges(filename: str, printing: bool = False) -> dict[str, str]:
    """Gets ranges of lesson numbers to use with Kotoba bot
    Lesson numbers are contained in comments, but format varies slightly between kanji and vocab
    csvs
    Prints the first lesson found

    Example kanji comment (always 1 lesson):
        "(L3) one, one radical (no.1)
        kunyomi: ひと-, ひと.つ
        onyomi: イチ, イツ"
    Example vocab comment (may contain multiple lessons, including "G"):
        "(読L9-II, 会L17) [n.] dormitory"
    """
    ranges: dict[str, str] = {}
    running_num = 0
    last_num = 1
    count = 0
    with open(filename, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # skip header

        for i, (_, _, comment, _, _) in enumerate(reader):
            # extract first lesson
            lesson = re.search(r"[G\d]+", comment).group()
            num = int(lesson) if str.isdigit(lesson) else 0  # 0 if G

            # next lesson number
            if num > running_num:
                ranges["G" if running_num == 0 else running_num] = f"{last_num}-{i}"
                if printing:
                    print(
                        f"L{'G' if running_num == 0 else running_num}: {last_num}-{i}"
                    )
                running_num = num
                last_num = i + 1
            count += 1

        # last lesson
        ranges[running_num] = f"{last_num}-{count}"
        if printing:
            print(f"L{running_num}: {last_num}-{count}")

    return ranges


def get_kanji_from_jisho():
    """Gets meanings and readings of kanji from jisho and writes to jisho.csv"""
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


def convert_to_en2jp(filename: str) -> None:
    """Converts vocab csv from kanji -> kana to english -> kanji/kana
    TODO: do it
    """
    with open(filename, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # skip header

        for i, (question, answers, comment, _, _) in enumerate(reader):
            pass


def get_hiragana_entries(filename: str, start: int = 2) -> None:
    """Gets the hiragana only entries from kotoba_vocab_original.csv file for finding entries to
    make manual adjustments on (see vocab.py -> _make_adjustments())

    Writes to 'hiragana_entries.csv':
        <kotoba line #> <question> <comment>
        str             str        str
    """
    out = "index,question,comment\n"
    with open(filename, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # skip header

        for i, (question, _, comment, _, _) in enumerate(reader):
            # if entire question is in hiragana, add to file
            # also skip entries before start line number
            # use i + 2 bc 1-based index and skipping header
            if i + 2 >= start and re.fullmatch(r"[ぁ-ん]+", question):
                out += f"{i + 2},{question},{comment}\n"

    with open("hiragana_entries.csv", "w", encoding="utf-8") as file:
        file.write(out)


if __name__ == "__main__":
    pass
    # get_hiragana_entries("kotoba_vocab_original.csv", 607)
