from dict_io import *

import re, pandas as pd
from collections import OrderedDict, defaultdict 

def create_character_flashcards(mode, base, words, dicts, simplified, output=''):
  tp2c = mk_tp2c(base)
  tp2ws = index_words_by_char('relative' if mode=='plain' else 'categoric', words, tp2c)
  tp2d = collect_definitions(dicts)

  done = set()
  C = None
  if output: 
    with open(output, 'w', encoding='utf-8') as f:
      for _,r in base.iterrows():
        if r.c != C:
          C = r.c
          f.write(f'// {category_to_str(C)}\n')
        for tp,s in zip(zip(r.t, r.p), r.s):
          if tp in done: continue
          done.add(tp)
          f.write(format_flashcard(s,*tp,tp2d,tp2ws, S=simplified,
            categories=[0,1,2] if mode=='plain' else all, 
            write_category=slice(0,0) if mode=='plain' else slice(2,3)))
  else: raise Exception('TODO decompose DataFrame')

def mk_tp2c(dict: pd.DataFrame):
  tp2c = {}
  for _,x in dict.iterrows():
    for t,p in zip(x.t, x.p):
      if (t,p) not in tp2c: tp2c[(t,p)] = x.c
      else: tp2c[(t,p)] = min(tp2c[(t,p)], x.c)
  return lambda k: tp2c.get(k, False)

def try_all_tones(t,p, dict, default=''):
  if (t,p) in dict: return dict[(t,p)]
  for y in [1,2,3,4,5]:
    if (t,p[:-1]+str(y)) in dict: return dict[(t,p[:-1]+str(y))]
  return default

def format_flashcard(s,t,p,tp2d,tp2ws, S=0, categories=all, write_category=slice(0,0)):
  d = try_all_tones(t,p, tp2d, 'No definition found')
  ws = try_all_tones(t,p, tp2ws, defaultdict(list))  # type: ignore
  
  o = f'{s}[{t}]\t{p}\t{shorten_def(d, S=S)}\uEAB1\uEAB1'

  for c in sorted(ws.keys()):
    if categories is not all and c not in categories: continue
    _c = '/'.join(c[write_category])
    if _c: o += f'{_c}\u3000'

    _c = '\u3000'.join([w.s if S else w.t for w in ws[c]])
    if _c: o += _c + '\uEAB1\uEAB1'
  return o[:-2]+'\n'

def shorten_def(d, S=0) -> str:
  d = re.sub('(bound form)', 'BF', d)
  d = re.sub('(literary)', 'lit.', d)
  d = re.sub(r'\[(\w+\d\s?)+]', '', d)
  d = re.sub(r'([\u4e00-\u9fa5]+)\|([\u4e00-\u9fa5]+)', rf'\{2 if S else 1}', d)
  return d

def collect_definitions(dicts):
  tp2d = {}
  for dict in dicts:
    for i,w in dict.iterrows():
      if len(w.t) == 1 and (w.t[0], w.p[0]) not in tp2d and hasattr(w, 'd'): 
        tp2d[(w.t[0], w.p[0])] = w.d
  return tp2d

def index_words_by_char(mode, lists, tp2c):
  # tp2ws = tp: cat: [word]
  tp2ws = defaultdict(lambda: defaultdict(list))
  def add(tp,c,w): tp2ws[tp][c] += [w]
  # relative mode: 
  # 0: all chars subsubcategories <= this
  # 1: all chars subcategories <= this
  # 2: all chars categories <= this
  # 3: all others in no category in base
  # long: phrases with a comma
  for lst in lists:
    for i,w in lst.iterrows():
      #if len(w.t) <= 1: continue

      tps = list(zip(w.t, w.p))
      if '，' in w.t:  # TODO replace with \u 
        for tp in tps: tp2ws[tp][','] += [w]
        continue

      cs = list(map(tp2c, tps)) # NOTE: Python iterators are a bit weird in that they are consumed after the first iteration
      
      for tp, c in zip(tps, cs):
        if mode=='relative':
          if   all(map(lambda d: d[0:3]<=c[0:3], cs)): add(tp,0,w)  # eg in same lesson
          elif all(map(lambda d: d[0:2]<=c[0:2], cs)): add(tp,1,w)  # eg in same book
          elif all(map(lambda d: d[0:1]<=c[0:1], cs)): add(tp,2,w)  # eg in same category
          else: add(tp,3,w)
        else: add(tp,w.c,w)
                  
  return tp2ws


if __name__=='__main__': 
  import argparse

  p = argparse.ArgumentParser()
  p.add_argument('base', nargs='?', help='Pleco flashcards path, which the character flashcards should be based on. Defaults to downloading the PAVC flashcards.', default='pavc')
  p.add_argument('words', nargs='?', choices=['plain','tocfl','hsk'], default='plain', help='Source of the example words. `plain`: From the `base` flashcards and optional `dictionaries` sorted by categories in base. `tocfl`: From TOCFL sorted by level. `hsk`: From HSK sorted by level.')
  p.add_argument('dicts', nargs='*', help='Additional user supplied dictionaries to source character dinitions from. If mode=`plain` also supply example words. Special cases: `cedict` will automatically download and use the latest CC-CEDICT.')
  p.add_argument('-o', '--output', default='chars.txt', help='Output file path.')
  p.add_argument('-s', '--simplified', action='store_true', help='Use simplified characters for flashcard text and example words.', default=False)
  p.add_argument('--keep_names', action='store_true', help='Dont omit words that are names for specific food, specific places, persons...', default=False)
  args = p.parse_args()
  kw = {'omit_names': not args.keep_names}

  # TODO change syntax to  $ program base [plain | tofcl | hsk] [cedict | ...]
  # TODO if mode!=plain still use the additional dictionaries for meanings 
  # TODO sorting in plain mode: category<=this, supercategory<=this, all. NO ',' in word. maybe also filter out too long

  pavc = get_pavc(**kw) if args.base=='pavc' or 'pavc' in args.dicts else None
  base = pavc if args.base=='pavc' else read_wordlist(args.base, **kw) 

  words = [{'plain':lambda: base, 'tocfl':get_tocfl, 'hsk':get_hsk}[args.words]()]
  dicts = []

  if args.dicts: 
    for path in args.dicts: 
      if args.dicts.count(path)>1: raise Exception('Remove duplicate in positional argument `dicts`: '+path)
      elif path=='nobase': dicts.remove(base)
      elif path=='pavc': dicts += [pavc]
      elif path=='cedict': dicts += [get_cedict(**kw)]
      else: dicts += [read_wordlist(path, **kw)]

  if args.words == 'plain': words += dicts

  create_character_flashcards(args.words, base, words, dicts, args.simplified, args.output)
