import re, unicodedata, pandas as pd

import os  # TODO use platform agnostic libraries and paths. TODO caching of downloaded files (

# TODO: omit names: omit dynast.. kingdom.. 


def download(url, filename, what='', overwrite=False):
  import tqdm, requests

  if os.path.isdir(filename): filename = os.path.join(filename, url.split('/')[-1])
  if not overwrite and os.path.isfile(filename): return True
  os.makedirs(os.path.dirname(filename), exist_ok=True)
  try: 
    with open(filename, 'wb') as f:   
      with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))

        with tqdm.tqdm(desc=f'Download {what}', total=total, unit='B', unit_scale=True, unit_divisor=1024) as pb:
          for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
            pb.update(len(chunk))
  except Exception as e:
    os.remove(filename)
    match e.__class__:
      case requests.exceptions.HTTPError if str(e).startswith('404'): raise FileNotFoundError(f'404 URL for {what} not found: {url}.')
      case _: raise e

def unzip(file, only={}, rm=False):
  import zipfile
  with zipfile.ZipFile(file, 'r') as z:
    for f,v in only.items():
      z.extract(f, path=os.path.dirname(file))
      os.rename(os.path.dirname(file)+'/'+f, v)
  if rm: os.remove(file)

def normalize_pinyin(t,p):
  # TODO make if work with tofcl format: split 'měiguó' into 'měi guó'
  p = p.strip().rstrip(']').lower()
  p = re.sub('-', '', p)
  p = re.sub(r'\s+', ' ', p)
  p = unicodedata.normalize('NFD', p).translate(
    {0x304:49, 
     0x301:50, 
     0x30c:51, 0x306:51,
     0x300:52})
  p = re.sub('u:', 'ü', p)
  # shift the number to the end of the syllable  # NOTE that this regex is not perfect I think if theres no apostrophe eg in nanan nanou nane*
  p = re.sub(r'([aeiou])([12345])(o|i|u)?(ng|n(?![aeiou]))?', r'\1\3\4\2', p)
  p = re.sub(r'([12345])(\w)', r'\1 \2', p)
  return tuple([
    'y1' if r == '一' else
    'bu4' if r == '不' else
    q+'5' if not q[-1].isdigit() else
    q for r,q in zip(t,p.split(' '))
  ])


def read_wordlist(path, omit_names):
  raise NotImplementedError('TODO: read additional wordlists from disk, determining their format adhoc')


### TOFCL ###
def get_tocfl(**kw):
  download('https://tocfl.edu.tw/assets/files/vocabulary/8000zhuyin_202409.zip', f:='cache/tocfl.zip', 'TOCFL vocabulary')
  unzip(f, only={'華語八千詞(內含注音字型檔)/華語八千詞表20240923.xlsx':(f:='cache/tocfl.xlsx')})
  return read_tofcl(f, **kw)

def read_tofcl(path):
  levels = '01 02 L1 L2 L3 L4 L5'.split(' ')
  o = pd.DataFrame(columns=['c','t','p','g'])
  for i,l in enumerate(levels):
    L = pd.read_excel(path, sheet_name=i, usecols=[1,2,3] if i<4 else [0,1,2])
    L.columns = ['t','p','g']; L['c'] = [l:=('','',l)]*len(L)
    variants = []
    for i in range(len(L)):
      ts, ps = [[x.strip() for x in tp.split('/')]
                 for tp in (L.loc[i].t, L.loc[i].p)]
      ts = [re.sub(r'\(([\u3100-\u312F]|[\u02C9\u02CA\u02C7\u02CB\u02D9]|[\u31A0-\u31BF])+\)', '', t) for t in ts] # remove bopomofo
      L.loc[i,'t'] = ts[0]
      L.loc[i,'p'] = ps[0]

      lts = len(ts); lps = len(ps)
      if lts>1 and lps==1: variants += [[l,t,ps[0],L.iloc[i].g] for t in ts[1:]]
      elif lts != lps: continue  # TODO accomodate more cases which have systematics as well eg 姊姊/姐姐/姊/姐	jiějie/jiě
      for t,p in zip(ts[1:], ps[1:]):
        variants += [[l,t,p,L.iloc[i].g]]

    o = pd.concat([o, L, pd.DataFrame(variants, columns=['c','t','p','g'])], ignore_index=True)
  o.p = o.apply(lambda x: normalize_pinyin(x.t, x.p), axis=1)
  return o


### HSK ###
def get_hsk(**kw):
  raise NotImplementedError('TODO: download HSK from the internet and parse it')


### CC-CEDICT ###
def get_cedict(**kw):
  download('https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip', f:='cache/cedict.zip', 'CC-CEDICT')
  unzip(f, only={(f:='cedict_ts.u8'):'cache/'+f})
  return read_cedict('cache/'+f, **kw)

def read_cedict(path, omit_names, omit_ascii=True, unique='last') -> pd.DataFrame:
  '''Parse CC-Cedict at path -> Traditional, Simplified, Pinyin, Definition'''
  with open(path) as file: lines = file.read().split('\n')

  def do_line(l):
    if l[0]=='#': return
    l = l.rstrip('/').split('/')
    if len(l)<=0 or l[0]=='': return

    d = '; '.join(l[1:])
    ts,p,*_ = l[0].split('[')
    t,s,*_ = ts.split()
    p = normalize_pinyin(t,p)

    if omit_ascii and re.search(r'[\x00-\x7F]', t): return 
    if omit_names and not len(t)>1 and 'surname ' in d: return  # NOTE: Characters that are commonly used as surnames have two entries in CC-CEDICT.
    # TODO: omit food names, specific places, ...
    return t,s,p,d
  
  o = pd.DataFrame(list(filter(lambda x: x, map(do_line, lines))), columns=list('tspd'))
  if unique: o = o.drop_duplicates(['t', 'p'], keep=unique, ignore_index=True)
  return o


### Pleco Flashcards ###
def read_pleco_flashs(path, PAVC=None, omit_names=True) -> pd.DataFrame: # Catergory, Traditional, Simplified, Pinyin, Definition, (Grammar)
  # TODO: implement omit_names for people, food, ...
  if PAVC is None: PAVC = 'PAVC' in path or 'pavc' in path

  c = (0,0,0)
  def doline(l):
    nonlocal c
    if not (l:=l.strip()): return
    if l.startswith('// '): 
      c = normalize_category(l[3:]) if PAVC else l[3:]
      return 
    else:
      c_ = list(c)
      st, p, *d = l.split('\t', 2)
      d = '\t'.join(d)
      s,t = re.match(r'(.+)\[(.+)]', st).groups()
      p = normalize_pinyin(t,p)

      if PAVC:
        if omit_names and len(t)>1 and re.search(r'transliteration|(pet|\w\sgiven)\sname', d): return
        if c[2]==0: # Is under an Extra
          c_[0] = 0 
          if ls := [int(n) for n in re.findall(r'\[PAVC-(\d\d\d)]?', d)]: 
            c_[2] = min(ls)
            c_[1] = c_[2] // 100; c_[2] = c_[2] % 100
          else: c_[2] = 1
        d = re.sub(r'\s*\[(PAVC|TOP)\-..?.?]?\s*', '', d)
      return c_,t,s,p,d

  with open(path, encoding='utf-8-sig') as f: ls = f.read().split('\n')
  # NOTE: interesting: preallocation super inefficient with pandas. but building list and in one go constructing df if desired is top
  o = []
  for l in ls: 
    if (l:=l.strip()) and (x:=doline(l)):
      o += [x]

  o = pd.DataFrame(o, columns=list('ctspd'))
  o.sort_values(['c'], inplace=True, ignore_index=True, kind='stable')  # stable sort keeps order from the book, which sometimes makes sense. also groups extra at the end
  return o

def write_pleco_flashs(path, df: pd.DataFrame, PAVC=False):
  with open(path, 'w', encoding='utf-8') as f:
    for i in range(len(df)):
      x = df.iloc[i]
      if PAVC and x.c % 100: f.write(f'// {category_to_str(x.c)}\n')
      f.write(f'{x.s}[{x.t}]\t{x.p}\t{x.d}\n')


## PAVC ##
def get_pavc(**kw):
  download('https://www.plecoforums.com/download/av-chinese-flashcards-2015-05-zip.1799/', f:='cache/pavc.zip', 'PAVC flashcards')
  unzip(f, only={(f:='AV Chinese Flashcards.txt'): 'cache/'+f})
  return read_pleco_flashs('cache/'+f, PAVC=True, **kw)

# NOTE the txt has format errors [PACV-001] instead of [PAVC-001  (沒有']'), or 一下's defintition has a '[PAVC-1 L??]'
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
  if (m:=re.match(r'AV Chinese/Book (\d)/Lesson (\d\d?)', c)): return (0, int(m.group(1)), int(m.group(2)))
  if (m:=re.match(r'AV Chinese/Book (\d)/Extra', c)): return (0, int(m.group(1)), 0)
  if (m:=re.match(r'AV Chinese/TOP/(\w+)', c)): return (1, 0, dict(Beginner=1, Learner=2, Superior=3, Master=4)[m.group(1)])
  else: raise Exception(f'Invalid category format {c}')

def category_to_str(c):
  top_dict = {1: 'Beginner', 2: 'Learner', 3: 'Superior', 4: 'Master'}
  if c[0]==1: return f'PAVC/TOP/{top_dict[c[2]]}'
  if c[2]==0: return f'PAVC/Book {c[1]}/Extra'
  else: return f'PAVC/Book {c[1]}/Lesson {c[2]:02d}'

def extract_grammar_category(x):
  g,d = x.d.split(':', 1)
  x.g = [h.strip() for h in g.rstrip('(TW)').replace('N (PW)', 'PW').split(',')]
  x.d = d.strip()
  return x


if __name__=='__main__':
  get_cedict(omit_names=True).to_csv('cedict.csv', index=False, sep='\t')
  get_pavc(omit_names=True).to_csv('pavc.csv', index=False, sep='\t')
  get_tocfl().to_csv('tocfl.csv', index=False, sep='\t')
