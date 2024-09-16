"""Gets ranges of lesson numbers to use with Kotoba bot"""
import sys
import csv
import re


def main(filename: str) -> None:
    """Lesson numbers are contained in comments, but format varies slightly between kanji and vocab
    csvs

    Example kanji comment (always 1 lesson):
        "(L3) one, one radical (no.1)
        kunyomi: ひと-, ひと.つ
        onyomi: イチ, イツ"
    Example vocab comment (may contain multiple lessons, including "G"):
        "(読L9-II, 会L17) [n.] dormitory"
    """
    running_num = 0
    last_num = 1
    count = 0
    with open(filename, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # skip header

        for i, (_, _, comment, _, _) in enumerate(reader):
            # extract first lesson
            lesson = re.search(r"[G\d]+", comment).group()
            # print(lesson)
            num = int(lesson) if str.isdigit(lesson) else 0  # 0 if G

            # next lesson number
            if num > running_num:
                print(f"L{'G' if running_num == 0 else running_num}: {last_num}-{i}")
                running_num = num
                last_num = i + 1

            count += 1

        # last lesson
        print(f"L{running_num}: {last_num}-{count}")


if __name__ == "__main__":
    sheet_name = "kotoba_vocab.csv" if len(sys.argv) < 2 else sys.argv[1]
    main(sheet_name)
