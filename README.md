# Chinese Utilities

- `dict_io.py`: parse CC-CEDICT dictionary and Pleco flashcards txt exports

- `charflashs.py`: generate opinionated flashcards for every single character with word examples (for pleco flashcards import)
  - to be used on the PAVC txt flashcards from https://www.plecoforums.com/threads/practical-audio-visual-chinese-dictionary-and-flashcards.2403/

quick run: `bash run.sh`

- Install conda dependcies: `conda create -yf environment.yml && conda activate chinese`
- Run: `python charflashs.py pavc -w base tocfl -d pavc cedict -o chars-pavc-tocfl.txt`