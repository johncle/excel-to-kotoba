import sys
import csv
from openpyxl import load_workbook


def excel_to_dict(filename: str):
    """Reads rows from excel sheet and returns a dictionary of kanji

    excel sheet structure (from row 3):
        <kanji #> <textbook order> <furigana> <kanji> <unique kanji #> <lesson #>
        int       int              str        str     int              str
    dict structure:
        { kanji: ( [<furigana>], [<textbook order>], <lesson #> ) }
          str      list[str]     list[int]           int
    """

    # load sheet as read only
    workbook = load_workbook(filename, read_only=True)
    sheet = workbook.active

    # invariants:
    #   - len([furigana]) == len([textbook order]) (1:1 mapping between furigana and textbook order)
    #   - [<textbook order>] is sorted in ascending order and furigana is inserted accordingly
    kanji_dict = {}
    for row in sheet.iter_rows(min_row=4):
        _, text_order, furigana, kanji, _, lesson_num = [cell.value for cell in row]
        if kanji not in kanji_dict:
            kanji_dict[kanji] = ([furigana], [text_order], int(lesson_num[1:]))
        else:
            furigana_list, order_list, _ = kanji_dict[kanji]
            # if kanji already seen, add furigana and textbook order to existing arrays
            # however, maintain sortedness of textbook order
            insert_idx = get_idx(text_order, order_list)
            furigana_list.insert(insert_idx, furigana)
            order_list.insert(insert_idx, text_order)
    # print(kanji_dict, len(kanji_dict))

    # sort by ascending textbook order since this also naturally sorts unique kanji and lesson #
    ordered = dict(sorted(kanji_dict.items(), key=lambda item: item[1][1][0]))
    return ordered


def dict_to_csv(filename: str, kanji_dict: dict):
    # get kanji meanings and readings from jisho(.csv)
    jisho = None
    with open("jisho.csv", "r", encoding="UTF-8") as file:
        reader = csv.reader(file)
        jisho = {
            kanji: (meanings, kunyomi, onyomi)
            for kanji, meanings, kunyomi, onyomi in reader
        }

    # format dict for kotoba csv
    # e.g. 明日,"あした,あす",Tomorrow,Type the reading!,Image"
    kotoba_list = [
        {
            "Question": kanji,
            "Answers": ",".join(furigana_list),
            "Comment": f"""(L{lesson}) {jisho[kanji][0]}\nkunyomi: {jisho[kanji][1]}\nonyomi: {jisho[kanji][2]}""",
            "Instructions": "Type the reading!",
            "Render as": "Image",
        }
        for kanji, (furigana_list, _, lesson) in kanji_dict.items()
    ]

    # write to csv
    with open(filename, "w", encoding="UTF-8") as file:
        fieldnames = ["Question", "Answers", "Comment", "Instructions", "Render as"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kotoba_list)


def get_idx(order: int, orders: list[int]):
    """Get index to insert current textbook order at, maintaining ascending order
    Uses linear search because of small length of list (max 6)
    """
    for i, num in enumerate(orders):
        # if current order < existing order, insert just before this
        if order < num:
            return i
    # else current order > all orders, add to end
    return len(orders)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Expected excel sheet filename, csv filename")
        sys.exit()
    sheet_name = sys.argv[1] or "kanji.csv"
    csv_name = sys.argv[2] or "kotoba.csv"

    kanji_dict = excel_to_dict(sheet_name)
    dict_to_csv(csv_name, kanji_dict)
