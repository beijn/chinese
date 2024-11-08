import sys, re, pandas as pd


def normalize_pinyin(t,p):
  #p = p.replace('ü', 'v')
  return tuple([
    'y1' if r == '一' else
    'bu4' if r == '不' else
    q for r,q in zip(t,re.sub(r'([12345])(\w)', r'\1 \2', p.strip().rstrip(']')).lower().split())
  ])

### CC-CEDICT ###
def read_cedict(path='cedict_ts.u8', omit_surnames=True):
  """Parse CC-Cedict at path -> Traditional, Simplified, Pinyin, Definition"""
  with open(path) as file: lines = file.read().split('\n')

  def do_line(l):
    if l[0]=='#': return
    l = l.rstrip('/').split('/')
    if len(l)<=0 or l[0]=='': return

    d = '; '.join(l[1:])
    ts,p,*_ = l[0].split('[')
    t,s,*_ = ts.split()
    p = normalize_pinyin(t,p)

    if omit_surnames and "surname " in d: return  # NOTE: Characters that are commonly used as surnames have two entries in CC-CEDICT.
    return t,s,p,d
  
  o = pd.DataFrame(list(filter(lambda x: x, map(do_line, lines))), columns=list('tspd'))
  return o


### Pleco Flashcards ###
def read_pleco_flashs(path, PAVC=False) -> pd.DataFrame: # Catergory, Traditional, Simplified, Pinyin, Definition, (Grammar)
  c = 0
  def doline(l):
    nonlocal c
    if not (l:=l.strip()): return
    if l.startswith('// '): 
      c = normalize_category(l[3:]) if PAVC else l[3:]
      return 
    else:
      c_ = c
      st, p, *d = l.split('\t', 2)
      d = '\t'.join(d)
      s,t = re.match(r'(.+)\[(.+)]', st).groups()
      p = normalize_pinyin(t,p)

      if PAVC:
        if isinstance(c,int) and not c % 100: # Is under an Extra
          if ls := [int(n) for n in re.findall(r'\[PAVC-(\d\d\d)]?', d)]: 
            c_ = min(ls)
          else: c_ = c+1
        d = re.sub(r"\s*\[(PAVC|TOP)\-..?.?]?\s*", '', d)
      return c_,t,s,p,d

  with open(path, encoding='utf-8-sig') as f: ls = f.read().split('\n')
  # NOTE: interesting: preallocation super inefficient with pandas. but building list and in one go constructing df if desired is top
  o = []
  for l in ls: 
    if (l:=l.strip()) and (x:=doline(l)):
      o += [x]

  o = pd.DataFrame(o, columns=list("ctspd"))
  o.sort_values(['c'], inplace=True, ignore_index=True)
  return o


def write_pleco_flashs(path, df: pd.DataFrame, PAVC=False):
  with open(path, 'w', encoding='utf-8') as f:
    for i in range(len(df)):
      x = df.iloc[i]
      if PAVC and x.c % 100: f.write(f'// {category_to_str(x.c)}\n')
      f.write(f'{x.s}[{x.t}]\t{x.p}\t{x.d}\n')


## PAVC ##
# NOTE the txt has format errors [PACV-001] instead of [PAVC-001  (沒有"]"), or 一下's defintition has a "[PAVC-1 L??]"
def expand_multiple_definitions(X: pd.DataFrame):
  # NOTE forgot, what was the reasoning for this?
  Y = pd.DataFrame(columns=X.columns)
  for i in range(len(X)):
    x = X.iloc[i]
    x.d,*ds = x.d.split(';')
    X.iloc[i] = x 
    for d in ds:
      x.d = d
      Y = pd.concat([Y, pd.DataFrame(x).T])
  return pd.concat([X,Y]).sort_values('c', ignore_index=True)

def normalize_category(c: str):
  if (m:=re.match(r'AV Chinese/Book (\d)/Lesson (\d\d?)', c)): return 100*int(m.group(1)) + int(m.group(2))
  if (m:=re.match(r'AV Chinese/Book (\d)/Extra', c)): return 100*int(m.group(1))
  if (m:=re.match(r'AV Chinese/TOP/(\w+)', c)): return 1000+dict(Beginner=1, Learner=2, Superior=3, Master=4)[m.group(1)]
  else: raise Exception(f"Invalid category format {c}")

def category_to_str(c: int):
  top_dict = {1: "Beginner", 2: "Learner", 3: "Superior", 4: "Master"}
  if c > 1000: return f'PAVC/TOP/{top_dict[c-1000]}'
  if c % 100: return f'PAVC/Book {c//100}/Lesson {c%100:02d}'
  return f'PAVC/Book {c//100}/Extra'

def extract_grammar_category(x):
  g,d = x.d.split(':', 1)
  x.g = [h.strip() for h in g.rstrip('(TW)').replace("N (PW)", "PW").split(',')]
  x.d = d.strip()
  return x


if __name__=='__main__':
  read_cedict("data/cedict_ts.u8", omit_surnames=True).to_csv("cedict.csv", index=False, sep="\t")
  read_pleco_flashs("data/AV Chinese Flashcards.txt", PAVC=True).to_csv("pavc.csv", index=False, sep="\t")
