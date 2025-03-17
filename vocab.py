"""Takes an excel spreadsheet containing general vocab and converts it to a CSV file for use with
Kotoba Discord Bot (https://kotobaweb.com/bot). Intended to be used with Genki sheets

Script takes in 2 (optional) positional arguments:
    1. Excel sheet file name (str, default 'vocab.xlsx')
    2. Output csv file name (str, default 'kotoba_vocab.csv')

Also has flag options:
    1. Adjustments (str, default 'adjustments.csv')
        - Not empty: make manual adjustments to entries based on the adjustments csv file
        - Empty: leave entries as original
    2. Split (bool, default 'False')
        - True: split csv into separate csvs for each lesson
        - False: keep entries as one large csv

    TODO:
    3. Reverse (bool, default 'False')
        - True: english meaning to kanji or kana
        - False: japanese to kana
    4. Duplicate (bool, default 'False')
        - True: duplicates word in each associated lesson for more accurate ranges
        - False: word appears in first associated lesson only

Starting on row 11, the excel sheet used has the following columns in this specific order:
    - Word number (No.)
    - Word (単語) (in kana)
    - Kanji notation (漢字表記)
    - Part of speech (品詞)
        - [n.] noun [い-adj.] い-adjective [な-adj.] な-adjective
        - [u-v.] u-verb [ru-v.] ru-verb [irr-v.] irregular verb
    - English translation (英訳)
    - Lesson number (課数)
        - [会] 会話･文法編 [読] 読み書き編 [G] あいさつ [(e)] 課末コラム [I, II, III] 読み書き編の問題番号

The resulting Kotoba CSV file has the following columns:
    - Question: Kanji
    - Answers: Kana
    - Comment: Meaning(s) in English, as well as part(s) of speech and lesson number(s)
    - Instructions: Tells user how to answer
    - Render as: Tells Kotoba Bot how to render the kanji

The Kotoba CSV file is sorted by ascending lesson number
"""

import csv
import re
from collections import defaultdict
import bisect
import argparse
from openpyxl import load_workbook
from utils import get_ranges


class VocabEntries:
    """Abstraction to make modifying the entries dict easier with less code duplication, but
    is probably slower

    - Lessons are automatically sorted upon insertion
    - English meanings/translations are categorized by lesson (stripped to number)
        - e.g. {"5": ["to take"], "6": ["to remove"]}
        - This makes it easier to create csvs per lesson and to create EN->JP csvs
    - Kana (readings) are also categorized by lesson
    - Note that the dict is a defaultdict so there is no explicit check if entry exists before
      adding

    dict structure: dict[ str, dict[ str, list[str] ] ]
    { kanji: { lesson: { kanas[],   meanings[], parts(of speech)[] } } }
      str      str       list[str]  list[str]   list[str]
    - If no kanji exists, use kana for key instead, and kana in value[0] stays the same

    Example dict:
    {
        "食べる": {
            "G": {"kanas": ["たべる"], "meanings": ["to eat"], "parts": ["ru-v."]},
            "1": {"kanas": ["たべる"], "meanings": ["to consume"], "parts": ["ru-v."]},
        },
        "見る": {
            "2": {"kanas": ["みる"], "meanings": ["to see"], "parts": ["ru-v."]},
            "3": {"kanas": ["みる"], "meanings": ["to watch"], "parts": ["ru-v."]},
        },
    }
    """

    def __init__(self):
        self.__dict = defaultdict(
            lambda: defaultdict(lambda: {"kanas": [], "meanings": [], "parts": []})
        )

    def get_entries(
        self,
    ) -> dict[str, dict[str, list[str]]]:
        return self.__dict

    def add_entry(
        self,
        kanji: str,
        kanas: list[str] | str,
        meanings: list[str] | str,
        parts: list[str] | str,
        lessons: list[str] | str,
    ) -> dict[str, dict[str, list[str]]]:
        """
        If given multiple lessons, assumes that each lesson provided gives the same kanas, meanings,
        and parts for this kanji
        - i.e. kanas, meanings, and parts are copied for each lesson
        """
        assert kanas  # should never be None or empty
        # allow inputting single str for ease of use, and convert to list
        if isinstance(kanas, str):
            kanas = [kanas]
        if isinstance(meanings, str):
            meanings = [meanings]
        if isinstance(parts, str):
            parts = [parts]
        if isinstance(lessons, str):
            lessons = [lessons]

        # if kanji is empty, use the kana as the dict key
        # don't use sanitized version since original might have additional info to display
        if not kanji:
            kanji = kanas[0]

        # prepare lesson data
        lesson_nums = [extract_lesson_num(lesson, True) for lesson in lessons]
        lesson_data = dict.fromkeys(
            lesson_nums,
            {
                "kanas": self.__sanitize_kanas(kanas),
                "meanings": meanings,
                "parts": parts,
            },
        )

        return self.add_entry_from_dict(kanji, lesson_data)


        # print(kanji, self._dict[kanji])

    def modify_entry(
        self,
        kanji: str,
        kanas: list[str] | str | None,
        parts: list[str] | str | None,
        meanings: list[str] | str | None,
        lessons: list[str] | str | None,
    ) -> None:
        pass

    def sort(self):
        """Return sorted representation of dict by lesson sort order"""
        ordered = dict(
            sorted(
                self._dict.items(), key=lambda entry: _lesson_sort_key(entry[1][3][0])
            )
        )
        return ordered

    def __add_kanas(self, kanji: str, kanas: list[str]) -> None:
        kana_list = self._dict[kanji][0]
        sanitized_kanas = self.__sanitize_kanas(kanas)
        for kana in sanitized_kanas:
            if kana not in kana_list:
                kana_list.append(kana)

    def __add_parts(self, kanji, parts: list[str]) -> None:
        part_list = self._dict[kanji][1]
        for part in parts:
            if part not in part_list:
                part_list.append(part.strip())

    def __add_meanings(self, kanji, meanings: list[str]) -> None:
        meaning_list = self._dict[kanji][2]
        for meaning in meanings:
            if meaning not in meaning_list:
                meaning_list.append(meaning.strip())

    def __add_lessons(self, kanji, lessons: list[str]) -> None:
        lesson_list = self._dict[kanji][3]
        for num in lessons:
            if num not in lesson_list:
                lesson_list.insert(num.strip())

    def __sanitize_kanas(self, kanas: list[str]) -> list[str]:
        """Some words have extra non-kana/non-katakana symbols which, at best, make it annoying to
        answer. Other times, words inside of parentheses are used for clarification which means they
        aren't even part of the reading. We remove all non-essential symbols from the answer for
        better user experience

        Note: '、' is interpreted by kotoba as a normal comma which separates an answer into multiple

        Examples:
            - Optional: 'おかえり（なさい）', 'ほ（う）っておく'
            - Clarification: 'いう（もんくを）', 'あんぜん（な）'
            - Tilde: 'ただの～', '～かな（あ）', 'もう～ない', '～か～'
            - Ellipse: '（～は）…といういみだ'
            - Alternatives: 'なん/なに'
            - Negative: 'あまり ＋ negative'
            - ???: '～（ん）だろう'
        """
        sanitized_kanas = []
        for kana in kanas:
            sanitized = kana
            # remove anything within parentheses, misc characters, and ' ＋ negative'
            sanitized = re.sub(r"（.*）|[～〜…！、]| ＋ negative", "", sanitized)
            # split words separated by "/" (alternative readings)
            sanitized = [skana.strip() for skana in sanitized.split("/")]
            sanitized_kanas.extend(sanitized)
        return sanitized_kanas

    def __getitem__(self, index: int | slice):
        # support indexing
        return self._dict[index]

    class LessonList:
        """Provides simple interface for inserting into lesson list while maintaining order
        from _lesson_sort_order():

        Lesson number can have the following forms:
        - 会L## (1-2 digits)
        - 会L##(e)
        - 読L##-I, 読L##-II, 読L##-III
        - 会G
            - Greetings lesson, we interpret this as lesson 0

        We want to sort by ascending lesson number, but also need to account for 会L##(e) and 読L##-I.
        For any number x, the sort order should look as below:
            1. 会Lx
            2. 会Lx(e)
            3. 読Lx-I
            4. 読Lx-II
            5. 読Lx-III
        """

        def __init__(self):
            self.key = _lesson_sort_key  # returns (int, int)
            self._lessons: list[tuple[tuple[int, int], str]] = []  # (rank, lesson)

        def insert(self, lesson: str):
            """Insert lesson while maintaining lesson order"""
            key_value = self.key(lesson)
            bisect.insort(self._lessons, (key_value, lesson))

        def __getitem__(self, index: int | slice):
            # support indexing and slicing
            if isinstance(index, slice):
                return [item[1] for item in self._lessons[index]]
            return self._lessons[index][1]

        def __len__(self) -> int:
            # len(length.size())
            return len(self._lessons)

        def __iter__(self):
            # iterate over original values
            return (item[1] for item in self._lessons)

        def __repr__(self):
            # represent as list of values
            return repr([item[1] for item in self._lessons])


class DefaultOrderedDict(OrderedDict):
    # Modified from http://stackoverflow.com/a/6190500/562769
    def __init__(self, *a, **kw):
        super().__init__(self, *a, **kw)
        self.default_factory = lambda: ([], [], [], [])

    def __getitem__(self, key):
        try:
            return super().__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = (self.default_factory,)
        return type(self), args, None, None, self.items()

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy

        return type(self)(self.default_factory, copy.deepcopy(self.items()))

    def __repr__(self):
        return f"OrderedDefaultDict({self.default_factory}, {super().__repr__(self)})"


def excel_to_dict(
    filename: str, adjustments_file: str, reverse: bool
) -> dict[str, (list[str], list[str], list[str], list[str])]:
    """Reads rows from excel sheet and returns a dictionary of kanji

    excel sheet structure (from row 11):
        <word #> <kana>   <kanji> <part of speech> <english meaning> <lesson #>
        str(int) str(int) str     str              str(int)          str
        - Kanji notation may not exist for some words (purely kana)
        - Some words have multiple lesson numbers deliminated by a comma (,)
            - In this case, sort dict using the first number seen
    dict structure:
        { kanji: ( [<kana>], [<part of speech>], [<meaning>], [<lesson #>] ) }
          str      list[str] list[str]           list[str]    list[str]
        - If no kanji exists, use kana for key instead, and kana in value[0] stays the same
    """
    # load sheet as read only, will throw error on invalid file
    workbook = load_workbook(filename, read_only=True)
    sheet = workbook.active

    # vocab_dict = defaultdict(lambda: ([], [], [], []))
    vocab_dict = VocabEntries()
    for row in sheet.iter_rows(min_row=11, values_only=True):
        # stop when reached end of sheet (for some reason doesn't stop automatically)
        if all(cell is None for cell in row):
            break

        # currently extracting data specific to the sheet I'm using
        kana, kanji, part, meaning, lesson = row[1:6]
        # entry may be in multiple lessons that might not have been split yet
        vocab_dict.add_entry(kanji, kana, part, meaning, lesson.split(","))

    # make manual adjustments in place
    if adjustments_file:
        _make_adjustments(vocab_dict.get_entries(), adjustments_file)
    # sort by ascending lesson number (first in lesson list)
    ordered = dict(
        # sorted(vocab_dict.items(), key=lambda entry: _lesson_sort_key(entry[1][3][0]))
        sorted(
            vocab_dict.get_entries().items(),
            key=lambda entry: _lesson_sort_key(entry[1][3][0]),
        )
    )
    return ordered


def _sanitize_kana(kana: str) -> list[str]:
    """Some words have extra non-kana/non-katakana symbols which, at best, make it annoying to
    answer. Other times, words inside of parentheses are used for clarification which means they
    aren't even part of the reading. We remove all non-essential symbols from the answer for better
    user experience

    Note: '、' is interpreted by kotoba as a normal comma which separates an answer into multiple

    Examples:
        - Optional: 'おかえり（なさい）', 'ほ（う）っておく'
        - Clarification: 'いう（もんくを）', 'あんぜん（な）'
        - Tilde: 'ただの～', '～かな（あ）', 'もう～ない', '～か～'
        - Ellipse: '（～は）…といういみだ'
        - Alternatives: 'なん/なに'
        - Negative: 'あまり ＋ negative'
        - ???: '～（ん）だろう'
    """
    sanitized_kana = kana
    # remove anything within parentheses, misc characters, and ' ＋ negative'
    sanitized_kana = re.sub(r"（.*）|[～〜…！、]| ＋ negative", "", sanitized_kana)
    # split words separated by "/" (alternative readings)
    sanitized_kana = [skana.strip() for skana in sanitized_kana.split("/")]
    return sanitized_kana


def _make_adjustments(
    vocab_dict: dict[str, (list[str], list[str], list[str], list[str])],
    adjustments_file: str,
) -> None:
    """Some entries have undesirable properties such as being in hiragana when there is a
    commonly-used kanji for it. This makes opinionated manual adjustments to those entries in place.

    - Rationale for displaying uncommonly-used kanji: It would be better to learn the uncommon kanji
      reading now than to see it and be confused later.

    Pulls from an external file (default 'adjustments.csv'):
        <kotoba line #> <original> <replacement> <answers> <comment> <split> <lesson>
        str(int)        str        str           str       str       str     str
        - <answers>, <comment>, or <split> fields may be empty (None) to indicate no change
        - First char of comment is one of:
            - 'a' (append to last comment)
            - 'A' (append to comments list)
            - 'W' (overwrite)
        - Split means to duplicate original into multiple entries for different kanjis
            - E.g. はし -> 橋 (bridge), 箸 (chopsticks)

    dict structure:
    { kanji: ( [<kana>], [<part of speech>], [<meaning>], [<lesson #>] ) }
        str      list[str] list[str]           list[str]    list[str]

    TODO:
    """
    try:
        with open(adjustments_file, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)  # skip header

            for entry in reader:
                # print(entry)
                (
                    _,
                    original,
                    replacement,
                    answers,
                    comment,
                    split,
                    new_lessons,
                    new_parts,
                ) = entry
                # copy and remove original entry
                kana, parts, meanings, lessons = vocab_dict.pop(original)
                # overwrite all answers if exist
                new_answers = (
                    [answer.strip() for answer in answers.split(",")]
                    if answers
                    else kana
                )
                new_comments: list[str] = meanings
                if comment:
                    # append to last comment
                    if comment[0] == "a":
                        new_comments[-1] += comment[1:]
                    # append to comments list
                    elif comment[0] == "A":
                        new_comments.append(comment[1:])
                    # overwrite all comments
                    elif comment[0] == "W":
                        new_comments = [cmt.strip() for cmt in comment[1:].split(";")]

                # if replacement not specified, keep original
                if not replacement:
                    replacement = original

                # add updated entry
                if replacement in vocab_dict:
                    # merge with existing entry
                    print(
                        "\033[93mkanji already exists, merging with:\033[0m",
                        replacement,
                        vocab_dict[replacement],
                    )
                    # tuple: (answers/kana, parts, meanings/comments, lessons)
                    existing_entry = vocab_dict[replacement]
                    for answer in new_answers:
                        if answer not in existing_entry[0]:
                            existing_entry[0].append(answer)
                    for part in new_parts.split(","):
                        if part and part not in existing_entry[1]:
                            existing_entry[1].append(part)
                    for cmt in new_comments:
                        if cmt not in existing_entry[2]:
                            existing_entry[2].append(cmt)
                    for num in new_lessons.split(","):
                        if num and num not in existing_entry[3]:
                            existing_entry[3].append(num)
                    # adding lesson may have caused lessons to be out of order
                    existing_entry[3].sort(key=_lesson_sort_key)
                    print(
                        "\033[93mupdated:\033[0m", replacement, vocab_dict[replacement]
                    )
                else:
                    # create new entry
                    vocab_dict[replacement] = (
                        new_answers,
                        parts,
                        new_comments,
                        lessons,
                    )

                # bring back original if splitting
                if split:
                    vocab_dict[original] = (kana, parts, meanings, lessons)
    except FileNotFoundError:
        print(f"\033[93m'{adjustments_file}' not found, no adjustments made\033[0m")


def _lesson_sort_key(lesson: str) -> tuple[int, int]:
    """Lesson number can have the following forms:
    - 会L## (1-2 digits)
    - 会L##(e)
    - 読L##-I, 読L##-II, 読L##-III
    - 会G
        - Greetings lesson, we interpret this as lesson 0

    We want to sort by ascending lesson number, but also need to account for 会L##(e) and 読L##-I.
    For any number x, the sort order should look as below:
        1. 会Lx
        2. 会Lx(e)
        3. 読Lx-I
        4. 読Lx-II
        5. 読Lx-III
    """
    # extract each lesson number without sections
    num = "".join(c for c in lesson if c.isdigit())
    num = int(num) if num else 0  # 0 if G

    # sections
    if "e" in lesson:
        rank = 1
    elif "I" in lesson:
        rank = 1 + lesson.count("I")
    else:
        rank = 0

    return num, rank


def dict_to_csv(
    filename: str, vocab_dict: dict[str, (list[str], list[str], list[str], list[str])]
) -> None:
    """Takes in vocab dictionary and writes to CSV file formatted for Kotoba

    dict structure:
        { kanji: ( [<kana>], [<part of speech>], [<meaning>], [<lesson #>] ) }
          str      list[str] list[str]           list[str]    list[str]

    example csv structure:
        Question,Answers,Comment,Instructions,Render as
        明日,"あした,あす",Tomorrow,Type the reading!,Image
    """
    # format dict for kotoba csv
    kotoba_list = [
        {
            "Question": kanji,
            "Answers": ",".join(kana_list),
            "Comment": f"({', '.join(lessons)}) [{', '.join(parts)}] {'; '.join(meanings)}",
            "Instructions": "Type the reading!",
            "Render as": "Image",
        }
        for kanji, (kana_list, parts, meanings, lessons) in vocab_dict.items()
    ]

    # write to csv
    with open(filename, "w", encoding="utf-8") as csv_file:
        fieldnames = ["Question", "Answers", "Comment", "Instructions", "Render as"]
        writer = csv.DictWriter(csv_file, fieldnames)
        writer.writeheader()
        writer.writerows(kotoba_list)


def split_lessons(
    vocab_dict: dict[str, (list[str], list[str], list[str], list[str])],
) -> dict[str, dict[str, (list[str], list[str], list[str], list[str])]]:
    """Takes in vocab dict and splits it into multiple dicts for each lesson. Some entries have
    multiple lessons, so we leave those in each lesson.

    dict structure:
        { kanji: ( [<kana>], [<part of speech>], [<meaning>], [<lesson #>] ) }
          str      list[str] list[str]           list[str]    list[str]
    """

    def lesson_factory():
        return defaultdict(lambda: ([], [], [], []))

    # split dict into dict of lessons: {lesson #, vocab dict}
    lesson_dicts: dict[
        str, dict[str, (list[str], list[str], list[str], list[str])]
    ] = defaultdict(lesson_factory)
    for kanji, (kana_list, parts, meanings, lessons) in vocab_dict.items():
        for lesson in lessons:
            # extract each lesson number without sections, may also be G
            num = "".join(c for c in lesson if c.isdigit()) or "G"
            # add entry to dict but with only this lesson in lesson list
            lesson_dicts[num][kanji] = (kana_list, parts, meanings, [lesson])

    # count = 0
    # for lesson_num, lesson_dict in lesson_dicts.items():
    #     print(lesson_num, len(lesson_dict), *lesson_dict, "\n", sep="\n")
    #     count += len(lesson_dict)
    # print(count)

    return lesson_dicts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Converts excel sheet to kotoba-formatted CSV(s)"
    )
    # dont use type=argparse.FileType for files because we load them manually
    parser.add_argument(
        "sheet_name",
        type=str,
        nargs="?",
        default="vocab.xlsx",
        help="excel sheet file name (default vocab.xlsx)",
    )
    parser.add_argument(
        "outfile_name",
        type=str,
        nargs="?",
        default="kotoba_vocab.csv",
        help="output csv file name (default kotoba_vocab.csv)",
    )
    parser.add_argument(
        "-a",
        "--adjustments",
        action="store_true",
        default=False,
        help="make manual adjustments to entries based on the adjustments file (default False)",
    )
    parser.add_argument(
        "-A",
        "--adjustments-file",
        type=str,
        default="adjustments.csv",
        help="path to adjustments file (default 'adjustments.csv')",
    )
    parser.add_argument(
        "-s",
        "--split",
        action="store_true",
        default=False,
        help="split csv into separate csvs for each lesson and store in the output dir (default False)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="out",
        help="path to output dir (default 'out/' or 'out')",
    )
    parser.add_argument(
        "-r",
        "--reverse",
        action="store_true",
        help="create english to japanese decks instead of the default kanji to kana decks (default False)",
    )
    # parser.add_argument(
    #     "-d",
    #     "--duplicate",
    #     action="store_true",
    #     help="duplicate already-seen word in each associated lesson for more accurate ranges (default False)",
    # )

    args = parser.parse_args()
    # print(*args._get_kwargs(), "", sep="\n")
    # excel_to_dict() checks if adjustments_file is set as the condition for making adjustments
    if not args.adjustments:
        args.adjustments_file = ""
    # strip leading and trailing whitespace and slashes
    args.output_dir = args.output_dir.strip(" \t\n\r\v\f/\\")
    # print(*args._get_kwargs(), sep="\n")

    vocab = excel_to_dict(args.sheet_name, args.adjustments_file, args.reverse)
    if args.split:
        for lesson_num, lesson_dict in split_lessons(vocab).items():
            dict_to_csv(
                f"{args.output_dir}/{args.outfile_name.removesuffix('.csv')}_{lesson_num}.csv",
                lesson_dict,
            )
        print(
            f"saved csvs to '{args.output_dir}/{args.outfile_name.removesuffix('.csv')}_#.csv'"
        )
    else:
        dict_to_csv(f"{args.output_dir}/{args.outfile_name}", vocab)
        print(f"saved csv to '{args.output_dir}/{args.outfile_name}'\n")
        print("lesson ranges:")
        get_ranges(args.outfile_name, True)
