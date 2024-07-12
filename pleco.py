from functools import reduce
import sys

def pleco(path='flashs.txt'):
  """Parse Pleco flashcard export txt at path to {category: [{'trad':, 'simp':, 'pinyin':, 'en';}, …], …}"""
  with open(path, encoding='utf-8-sig') as file: lines = file.read().split('\n')

  def pLine(state, l):
    all, cat, vocab = state

    if l == '': return all | {cat: vocab}, 'End of Recursion', []
    if l.startswith('// '): return all | {cat: vocab}, l[3:], []

    chars, pinyin, *en = l.split('\t')
    trad, simp = chars.split('[', 1) if '[' in chars else (chars, chars)
    simp = simp.rstrip(']')

    return all, cat, vocab + [dict(trad=trad, simp=simp, pinyin=pinyin, en=en)]
  
  return reduce(pLine, lines, ({}, '', []))[0]

if __name__ == '__main__': print(len([x for xs in pleco(sys.argv[1]).values() for x in xs]))
