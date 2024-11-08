from dict_io import read_cedict, read_pleco_flashs, category_to_str

import sys, re, pandas as pd, string
from collections import defaultdict 


def main(argv):
  cedict = read_cedict(argv[1], omit_surnames=True)
  pavc = read_pleco_flashs(argv[2], PAVC=True)#.where(lambda x: x.c == 101).dropna()
  tp2l = mk_tp2l(pavc)
  tp2d, tp2ws = index_words_by_char([pavc, cedict], tp2l)

  already = set()
  category = None
  with open('pleco_pavc_chars.txt', 'w', encoding='utf-8') as f:
    for _,r in pavc.iterrows():
      if r.c != category:
        category = r.c
        f.write(f"// {category_to_str(category)}\n")
      for tp,s in zip(zip(r.t, r.p), r.s):
        if tp in already: continue
        already.add(tp)
        f.write(format_flashcard(s,*tp,tp2d,tp2ws))

def mk_tp2l(pavc: pd.DataFrame):
  tp2l = {}
  for _,x in pavc.iterrows():
    for t,p in zip(x.t, x.p):
      if (t,p) not in tp2l: tp2l[(t,p)] = x.c
      else: tp2l[(t,p)] = min(tp2l[(t,p)], x.c)
  return lambda k: tp2l.get(k, False)

def try_all_tones(t,p, dict, default=''):
  if (t,p) in dict: return dict[(t,p)]
  for y in [1,2,3,4,5]:
    if (t,p[:-1]+str(y)) in dict: return dict[(t,p[:-1]+str(y))]
  return default

def format_flashcard(s,t,p,tp2d,tp2ws):
  z = '\uEAB1'; zz = z+' '+z
  d = try_all_tones(t,p, tp2d, 'No definition found')
  wss = try_all_tones(t,p, tp2ws, [{},{},{},{},{},{}])
  ws = zz.join(['  '.join([w.t for w in ws.values()]) for ws in wss[:3]]) # NOTE: ommited words containing chars from outside the books. because for them I can just use plecos buildin search with "?" 
  #ws += (z+z)+'   '.join([w.t for w in wss[-1].values()][:10])
  o = f"{s}[{t}]\t{p}\t{shorten_def(d)}{zz}{ws}\n" 
  return re.sub(f'{zz}+', zz, o)

def shorten_def(d) -> str:
  d = re.sub('(bound form)', 'BF', d)
  d = re.sub('(literary)', 'lit.', d)
  d = re.sub(r'\[(\w+\d\s?)+]', '', d)
  d = re.sub(r'\|'+f'[{re.escape(string.punctuation)},\uEAB1'+r'\w]+', '', d)
  return d

def index_words_by_char(dicts, tp2l):
  tp2d = {}
  tp2ws = defaultdict(lambda: [{}, {}, {}, {}, {}])  
  add = lambda w,tp,i: tp2ws[tp][i].update({w.t:w}) 
  # [0] # all other characters were in previous lessons
  # [1] # all other characters occur up to in this book
  # [2] # all other characters atleast occur in the book series
  # [3] # all other characters are in the dict
  # [4] # its a longer phrase (with a comma)
  for zidian in dicts:
    for i,w in zidian.iterrows():
      if len(w.t) == 1: 
        if (w.t[0], w.p[0]) not in tp2d: 
          tp2d[(w.t[0], w.p[0])] = w.d
      else: 
        tps = list(zip(w.t, w.p))
        if '，' in w.t: 
          for tp in tps: add(w, tp, 4)
        else:
          ls = list(map(tp2l, tps)) # NOTE: Python iterators are a bit weird in that they are consumed after the first iteration
          if not all(ls): 
            for tp in tps: add(w, tp, 3)
          else:
            for tp, l in zip(tps, ls):
              if all(k<=l for k in ls): add(w, tp, 0)
              elif all(k//100<=l//100 for k in ls): add(w, tp, 1)  # TODO can improve performance by preordering by lesson, then I only have to check for how many more characters to add the word: lts = [(lesson(t), t) for t in w].sort()
              else: add(w, tp, 2)
  return tp2d, tp2ws


if __name__=='__main__': 
  if len(sys.argv) == 1: main([sys.argv[0], "data/cedict_ts.u8", "data/AV Chinese Flashcards.txt"])
  elif len(sys.argv) == 3: main(sys.argv)
  else: print("Usage: charflashs.py cedict.txt pavc.txt")
