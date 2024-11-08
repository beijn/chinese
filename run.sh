#!/bin/bash

conda='micromamba'
$conda create -yf environment.yml

mkdir -p data 
cd data

curl -L https://www.plecoforums.com/download/av-chinese-flashcards-2015-05-zip.1799/ -o pavc.zip
unzip -o "pavc.zip"
rm "pavc.zip"
rm "Pleco Flashcard Database.pqb"

cedict=
curl -L https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip -o cedict.zip
unzip -o cedict.zip
rm cedict.zip

cd ..
$conda run -n chinese \
  python charflashs.py data/cedict_ts.u8 "data/AV Chinese Flashcards.txt"
