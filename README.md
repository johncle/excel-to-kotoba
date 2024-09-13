# excel-to-kotoba
Converts Excel spreadsheet to csv for Kotoba discord bot (https://kotobaweb.com/bot)

Currently supports two types of spreadsheets, kanji and vocab (see kanji.py and vocab.py).

The resulting Kotoba CSV file has the following columns:
- Question: Kanji
- Answers: Hiragana
- Comment: Meanings in English, as well as additional information such as readings or lesson number
- Instructions: Tells user how to answer
- Render as: Tells Kotoba Bot how to render the kanji

## TODO:
- Implement generic harness for use with any excel sheet