#!/bin/bash

conda='micromamba'
$conda create -yf environment.yml

$conda run -n chinese \
     python charflashs.py pavc tocfl cedict -o chars-pavc-tocfl.txt \
  # && python charflashs.py pavc plain cedict -o chars-pavc.txt \
  # && python charflashs.py pavc hsk cedict -o chars-pavc-hsk.txt --simplified
