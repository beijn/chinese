# Chinese Utilities

- `dict_io.py`: read Pleco flashcards txt exports, download and read CC-CEDICT and TOCFL and HSK word lists. 

- `charflashs.py`: generate opinionated flashcards for every single character with word examples (for pleco flashcards import)

## Usage
- Install conda dependcies: `conda create -yf environment.yml && conda activate chinese`
- Run: `python charflashs.py pavc -w base tocfl -d pavc cedict -o chars-pavc-tocfl.txt`

## IMPORT INTO PLECO
