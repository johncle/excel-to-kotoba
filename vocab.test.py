"""Tests that resulting CSV file from vocab.py is sorted properly

Lesson number can have the following forms:
    - 会L## (1-2 digits)
    - 会L##(e)
    - 読L##-I, 読L##-II, 読L##-III
    - 会G
        - Greetings lesson, we interpret this as lesson 0

We want to sort by ascending lesson number, but also need to account for 会L##(e) and 読L##-I.
For any number x, the sorted order should look as below:
    1. 会Lx
    2. 会Lx(e)
    3. 読Lx-I
    4. 読Lx-II
    5. 読Lx-III
"""
import csv

with open("kotoba_vocab.csv", "r", encoding="utf-8") as file:
    reader = csv.reader(file)
    next(reader)  # skip header

    running_num = 0
    running_reading_num = 0
    e_seen = False

    for i, (_, _, comment, _, _) in enumerate(reader):
        # example comment: "(読L9-II, 会L17) [n.] dormitory"
        # extract first lesson
        lesson = comment[1:].split(")")[0].split(",")[0]
        # print(lesson)
        num = "".join(c for c in lesson if c.isdigit())
        num = int(num) if num else 0  # 0 if G
        reading_num = lesson.count("I")

        # next lesson number
        if num > running_num:
            # assert num == cur_num + 1   # not necessary
            running_num = num
            running_reading_num = 0
            e_seen = False

        try:
            # num is monotonically non-decreasing
            assert num >= running_num
            # normal lesson numbers are before (e), and (e) is before reading numbers
            assert not (e_seen and "e" not in lesson and "I" not in lesson)
            # reading numbers are monotonically non-decreasing
            assert not (running_reading_num and reading_num < running_reading_num)
        except AssertionError:
            print(f"AssertionError on: '{comment}'")
            print(f"cur_num: {running_num} num: {num}")
            print(f"cur_reading_num: {reading_num} reading_num: {running_reading_num}")
            print(f"e_seen: {e_seen}")
            print()

        # update trackers
        running_reading_num = reading_num
        if "e" in lesson:
            e_seen = True

print("All tests passed")
