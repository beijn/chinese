from functools import reduce
import sys, re



def flashs(path='flashs.txt', lesson2digits=False):
  """Parse Pleco flashcard export txt at path to {category: [{'trad':, 'simp':, 'pinyin':, 'en';}, …], …}"""
  with open(path, encoding='utf-8-sig') as file: lines = file.read().split('\n')

  def pLine(state, l):
    all, cat, vocab = state

    if l == '': return all | {cat: vocab}, 'End of Recursion', []
    if l.startswith('// '):  
      c = l[3:]
      if lesson2digits: 
        c = re.sub(r'Lesson (\d)([^\d]|$)', r'Lesson 0\1\2', c)
        c = re.sub('Extra', 'Xtra', c)
      return all | {cat: vocab}, c, []

    chars, pinyin, *en = l.split('\t', 2)
    simp, trad = chars.split('[', 1) if '[' in chars else (chars, chars)
    trad = trad.rstrip(']')

    return all, cat, vocab + [dict(trad=trad, simp=simp, pinyin=pinyin, en=en[0] if en else '', cat=cat)]
  
  return reduce(pLine, lines, ({}, '', []))[0]

if __name__ == '__main__': print(len([x for xs in flashs(sys.argv[1]).values() for x in xs]))
