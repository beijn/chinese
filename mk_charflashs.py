import cedict, pleco

import sys, urllib.request
import unicodedata, re
from collections import defaultdict 


# todo: cache to disk
def get_all_unicode_blocks():
  url = "https://www.unicode.org/Public/UNIDATA/Blocks.txt"
  blocks = {}
  lines = urllib.request.urlopen(url).read().decode('utf-8').split('\n')
  for l in map(str.strip, lines):
    if not l or l.startswith('#'): continue
    range, name = l.split(';'); l, h = range.split('..')
    blocks[name.strip()] = (int(l, 16), int(h, 16))
  return blocks

# todo: defer execution until needed
include = {b:r for b,r in get_all_unicode_blocks().items() if 'CJK' in b}

def check(c):
  if unicodedata.category(c)[0] in 'PS': return False
  for b, (l, h) in include.items():
    if l <= ord(c) <= h: return True
  return False


def chars(flashs):
  cat2char = defaultdict(list)
  D = defaultdict(lambda: defaultdict(list))
  for cat, vocab in sorted(flashs.items(), key=lambda x: x[0]):
    if not cat.startswith('AV Chinese/Book'): continue

    for word in vocab:
      pinyin = re.sub(r'(\d)\-?([a-zA-Z1-5])', r'\1 \2', word['pinyin']).split(' ')
      for c,cs,py in zip(word['trad'], word['simp'], pinyin):
        if not check(c): continue
        if c not in D: cat2char[cat] += [c]
        if cat not in D[c]['cat']: D[c]['cat'] += [cat]
        if word not in D[c]['words']: D[c]['words'] += [word]
        if py not in D[c]['pinyin']: D[c]['pinyin'] += [py] 
        if cs not in D[c]['simp']: D[c]['simp'] += [cs]

    cat2char[cat] = sorted(set(cat2char[cat]))
  return cat2char, D


def flashs2dict(flashs, fill):
  D = defaultdict(dict)
  def inner(f,k): 
    w = f['trad']
    D[w][k] = f[k] if f[k].strip() else fill[w][k] if w in fill else '' # and k in fill[w] else ''
  # note: don't append defs, because AV dict already did
  [ inner(f,k) for cat,fs in flashs.items() for f in fs for k in ('en', 'cat', 'pinyin', 'simp') if k in f ]
  return D


if __name__ == '__main__':
  cedict = cedict.cedict(sys.argv[1], count=False)
  flashs = pleco.flashs(sys.argv[2], lesson2digits=True)

  cat2char, bychar = chars(flashs)

  flashs = flashs2dict(flashs, fill=cedict)
  byword = cedict | flashs


  def get_words(c, dict, include='prev'):
    def knownchar(d):
      c_cat = bychar[c]['cat'][0]
      return c in bychar and d in bychar and (d_cat:=bychar[d]['cat'][0]) <= (\
        'z' if include=='all'else 'AV Chinese/Book 1/Lesson 12' if 'Book 1' in d_cat and include=='book' else c_cat if include=='prev' else include)
    return sorted([w for w in dict if c in w and all(map(knownchar, w))], key=len)[1:]  # remove c itself

  # list(dict.fromkeys imitates ordered set
  examples = {c: list(dict.fromkeys(get_words(c, flashs) + get_words(c, flashs, 'book') + get_words(c, flashs, 'all')
                  + get_words(c, cedict) + get_words(c, cedict, 'book') + get_words(c, cedict, 'all')
                  ))[:5] for c in bychar}
  for c, exs in examples.items(): 
    examples[c] = [(ex+' '+byword[ex]['en'] if ex in byword and byword[ex]['en'].strip() else ex) for ex in exs]
    # +' '+byword[ex]['pinyin']

  for cat, chars in sorted(cat2char.items(), key=lambda x: x[0]):
    #if 'Book 01' not in cat: continue
    print(f'// Chars-{cat}')
    for c in chars:
      line = f"{bychar[c]['simp'][0]}[{c}]"+(f"\t{bychar[c]['pinyin'][0]}\t{byword[c]['en']}" + ''.join(f"\uEAB1▪ "+e for e in examples[c])).replace(c, '＿')
      line = re.sub(r' \[(PAVC-...|TOP-.)\]', r'', line)
      line = re.sub(r'\|\S+\[', '[', line)
      print(line) 

