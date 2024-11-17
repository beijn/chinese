from dict_io import *

import re, pandas as pd
from collections import defaultdict 


# TODO: Add TOCFL cards sorted by level, where dict entry is just the level


def create_character_flashcards(base, wordlists, dicts, simplified, output=''):
  tp2c = mk_tp2c(base)
  t2wss = [(mode, index_words_by_char(mode, wordlist, tp2c))
           for mode, wordlist in wordlists]
  t2p2d = collect_definitions(dicts)

  done = set()
  last = ()
  C = None
  if output: 
    with open(output, 'w', encoding='utf-8') as f:
      for _,r in base.iterrows():
        if r.c != C:
          C = r.c
          f.write(f'// {category_to_str(C)}\n')
        for (t,p),s in zip(zip(r.t, r.p), r.s):
          if len(r.t)>1 and ((t,p) in done or any(map(lambda tone: (t,p[:-1]+tone) == last, '1234'))): continue
          done.add((t,p))
          last = (t,p)
          f.write(format_flashcard(s,t,p,t2p2d,t2wss, S=simplified, 
                    overwrite_d=r.d if len(r.t)==1 else ''))
  else: raise Exception('TODO just return DataFrame')

def mk_tp2c(dict: pd.DataFrame):
  tp2c = {}
  for _,x in dict.iterrows():
    for t,p in zip(x.t, x.p):
      if (t,p) not in tp2c: tp2c[(t,p)] = x.c
      else: tp2c[(t,p)] = min(tp2c[(t,p)], x.c)
  return lambda k: tp2c.get(k, False)

def format_flashcard(s,t,p,t2p2d,t2wss, S=0, overwrite_d=''):
  if t in t2p2d and p in t2p2d[t]: d = t2p2d[t][p]
  else: d = f'No definition found for {t} ({p}).'

  if overwrite_d: d = overwrite_d
  for q in t2p2d[t]:
    if q != p: d += f'\uEAB1‣{q}: {t2p2d[t][q]}'

  wss = [(mode, t2ws.get(t, defaultdict(list))) for mode,t2ws in t2wss]  # type: ignore
  
  o = f'{s}[{t}]\t{p}\t{shorten_def(d, S=S)}\uEAB1\uEAB1'

  for mode, ws in wss:
    categories = {'relative': [0,1,2],
                  'categoric': all}[mode]
    write_category = {'relative': slice(0,0),
                      'categoric': slice(2,3)}[mode]
    for c in sorted(ws.keys()):
      if categories is not all and c not in categories: continue
      _c =  '▪' + ('/'.join(c[write_category]) if isinstance(c, tuple) else '')
      if _c: o += f'{_c}  ' #\u3000

      _c = '  '.join([w.s if S else w.t for w in ws[c]])
      if _c: o += _c + '\uEAB1'
    o += '\uEAB1'
  return o[:-2]+'\n'

def shorten_def(d, S=0) -> str:
  d = re.sub('(bound form)', 'BF', d)
  d = re.sub('(literary)', 'lit.', d)
  d = re.sub(r'\[(\w+\d\s?)+]', '', d)
  d = re.sub(r'([\u4e00-\u9fa5]+)\|([\u4e00-\u9fa5]+)', rf'\{2 if S else 1}', d) # remove trad/simp alternative forms
  return d

def collect_definitions(dicts):
  t2p2d = defaultdict(lambda: defaultdict(str))
  for dct in dicts:
    for i,w in dct.iterrows():
      if len(w.t) == 1 and hasattr(w, 'd'): 
        #if w.p[0] in t2p2d[w.t[0]]: t2p2d[w.t[0]][w.p[0]] += '; '
        t2p2d[w.t[0]][w.p[0]] = w.d  # +=
  return t2p2d

def index_words_by_char(mode, lst, tp2c):
  # tp2ws = tp: cat: [word]
  t2ws = defaultdict(lambda: defaultdict(list))
  def add(t,_p,c,w): t2ws[t][c] += [w]
  # relative mode: 
  # 0: all chars subsubcategories <= this
  # 1: all chars subcategories <= this
  # 2: all chars categories <= this
  # 3: all others in no category in base
  # long: phrases with a comma
  for i,w in lst.iterrows():
    #if len(w.t) <= 1: continue

    tps = list(zip(w.t, w.p))
    if '\uff0c' in w.t:  
      for t,p in tps: add(t,p,',', w)
      continue

    cs = list(map(tp2c, tps)) # NOTE: Python iterators are a bit weird in that they are consumed after the first iteration
    
    for (t,p), c in zip(tps, cs):
      if mode=='relative':
        if   all(map(lambda d: d[0:3]<=c[0:3], cs)): add(t,p,0,w)  # eg in same lesson
        elif all(map(lambda d: d[0:2]<=c[0:2], cs)): add(t,p,1,w)  # eg in same book
        elif all(map(lambda d: d[0:1]<=c[0:1], cs)): add(t,p,2,w)  # eg in same category
        else: add(t,p,3,w)
      else: add(t,p,w.c,w)
                  
  return t2ws


if __name__=='__main__': 
  import argparse

  p = argparse.ArgumentParser()
  p.add_argument('base', nargs='?', help='Pleco flashcards path, which the character flashcards should be based on. Defaults to downloading the PAVC flashcards.', default='pavc')
  p.add_argument('-w', '--words', nargs='+', help='Source of the example words. Special words: `base`: From the `base` flashcards sorted by category <= this subsubcategory, <= this subcategory, <= this category. `tocfl`: From TOCFL sorted by level. `hsk`: From HSK sorted by level. `pavc`: From the PAVC book series.')
  p.add_argument('-d', '--dicts', nargs='+', help='Additional user supplied dictionaries to source character definitions from. Special cases: `cedict` will automatically download and use the latest CC-CEDICT.')
  p.add_argument('-o', '--output', default='chars.txt', help='Output file path.')
  p.add_argument('-s', '--simplified', action='store_true', help='Use simplified characters for flashcard text and example words.', default=False)
  p.add_argument('--keep_names', action='store_true', help='Dont omit words that are names for specific food, specific places, persons...', default=False)
  args = p.parse_args()
  kw = {'omit_names': not args.keep_names}

  pavc = get_pavc(**kw) if args.base=='pavc' or 'pavc' in args.dicts or 'pavc' in args.words else None
  base = pavc if args.base=='pavc' else read_wordlist(args.base, **kw) 

  wordlists = [{'base':lambda: base, 'tocfl':get_tocfl, 'hsk':get_hsk}[_w]() for _w in args.words]
  dicts = []

  if args.dicts: 
    for path in args.dicts: 
      if args.dicts.count(path)>1: raise Exception('Remove duplicate in positional argument `dicts`: '+path)
      elif path=='pavc': dicts += [pavc]
      elif path=='cedict': dicts += [get_cedict(**kw)]
      else: dicts += [read_wordlist(path, **kw)]

  modes = ['relative' if w=='base' else 'categoric' for w in args.words]

  create_character_flashcards(base, zip(modes, wordlists), dicts, args.simplified, args.output)
