"""Takes an excel spreadsheet containing general vocab and converts it to a CSV file for use with
Kotoba Discord Bot (https://kotobaweb.com/bot). Intended to be used with Genki sheets

Starting on row 11, the excel sheet used has the following columns in this specific order:
    - Word number (No.)
    - Word (単語) (in hiragana)
    - Kanji notation (漢字表記)
    - Part of speech (品詞)
        - [n.] noun [い-adj.] い-adjective [な-adj.] な-adjective
        - [u-v.] u-verb [ru-v.] ru-verb [irr-v.] irregular verb
    - English translation (英訳)
    - Lesson number (課数)
        - [会] 会話･文法編 [読] 読み書き編 [G] あいさつ [(e)] 課末コラム [I, II, III] 読み書き編の問題番号

The resulting Kotoba CSV file has the following columns:
    - Question: Kanji
    - Answers: Hiragana
    - Comment: Meaning(s) in English, as well as part(s) of speech and lesson number(s)
    - Instructions: Tells user how to answer
    - Render as: Tells Kotoba Bot how to render the kanji

The Kotoba CSV file is sorted by ascending lesson number
"""
import sys
import csv
from openpyxl import load_workbook


def excel_to_dict(
    filename: str,
) -> dict[str, (list[str], list[str], list[str], list[str])]:
    """Reads rows from excel sheet and returns a dictionary of kanji

    excel sheet structure (from row 11):
        <word #> <hiragana> <kanji> <part of speech> <english meaning> <lesson #>
        int      int        str     str              int                   str
        - Kanji notation may not exist for some words (purely hiragana)
        - Some words have multiple lesson numbers deliminated by a comma (,)
            - In this case, sort dict using the first number seen
    dict structure:
        { kanji: ( [<hiragana>], [<part of speech>], [<meaning>], [<lesson #>] ) }
          str      list[str]     list[str]           list[str]    list[str]
        - If no kanji exists, use hiragana for key instead, and hiragana in value stays the same
    """
    # load sheet as read only
    workbook = load_workbook(filename, read_only=True)
    sheet = workbook.active

    vocab_dict = {}
    for row in sheet.iter_rows(min_row=11):
        _, hiragana, kanji, part, meaning, lesson = [cell.value for cell in row]
        # if word is purely hiragana, use that instead of kanji for key
        if not kanji:
            kanji = hiragana
        if kanji not in vocab_dict:
            vocab_dict[kanji] = (
                [hiragana],
                [part],
                [meaning],
                [num.strip() for num in lesson.split(",")],
            )
        else:
            # if kanji already seen, append to existing arrays
            hiragana_list, part_list, meaning_list, lesson_list = vocab_dict[kanji]
            # ignore duplicates
            if hiragana not in hiragana_list:
                hiragana_list.append(hiragana)
            if part not in part_list:
                part_list.append(part)
            if meaning not in meaning_list:
                meaning_list.append(meaning)
            if lesson not in lesson_list:
                lesson_list.append(lesson)
    # print(list(vocab_dict.items())[:5], len(vocab_dict))

    # count = 0
    # for word in vocab_dict.values():
    # print(word)
    # if len(word[0]) > 1:
    #     print(word[0])
    # if len(word[1]) > 1:
    #     print(word[1])
    # if len(word[2]) > 1:
    #     print(word[2])
    # if len(word[3]) > 1:
    #     print(word[0], word[3])
    #     count += 1
    # print(count)
    # print(all(len(word[0]) == 1 for word in vocab_dict))
    # print(list(filter(lambda word: any("e" in lesson for lesson in word[3]), vocab_dict.values())))

    # sort by ascending lesson number (first in list)
    ordered = dict(
        sorted(vocab_dict.items(), key=lambda item: _extract_num(item[1][3][0]))
    )
    return ordered


def _extract_num(lesson: str) -> int:
    """Lesson number can have the following forms:
    - 会L## (1-2 digits)
    - 会L##(e)
    - 読L##-I, 読L##-II, 読L##-III
    - 会G
        - In this case, return -1 to put at top of csv
    """
    num = "".join(c for c in lesson[1:] if c.isdigit())
    return int(num) if num else -1


def dict_to_csv(
    filename: str, vocab_dict: dict[str, (list[str], list[str], list[str], list[str])]
) -> None:
    """Takes in vocab dictionary and writes to CSV file formatted for Kotoba

    Notes:
    - If a

    example csv structure:
        Question,Answers,Comment,Instructions,Render as
        明日,"あした,あす",Tomorrow,Type the reading!,Image
    """
    # format dict for kotoba csv
    kotoba_list = [
        {
            "Question": kanji,
            "Answers": ",".join(hiragana_list),
            "Comment": f"({', '.join(lesson_list)}) [{', '.join(part_list)}] {'; '.join(meaning_list)}",
            "Instructions": "Type the reading!",
            "Render as": "Image",
        }
        for kanji, (
            hiragana_list,
            part_list,
            meaning_list,
            lesson_list,
        ) in vocab_dict.items()
    ]

    # write to csv
    with open(filename, "w", encoding="utf-8") as csv_file:
        fieldnames = ["Question", "Answers", "Comment", "Instructions", "Render as"]
        writer = csv.DictWriter(csv_file, fieldnames)
        writer.writeheader()
        writer.writerows(kotoba_list)


if __name__ == "__main__":
    sheet_name = sys.argv[1] or "vocab.csv"
    outfile_name = sys.argv[2] or "kotoba_vocab.csv"

    vocab_dict = excel_to_dict(sheet_name)
    dict_to_csv(outfile_name, vocab_dict)
