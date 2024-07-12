### adapted by Benjamin Eckhardt 2024 from Franki Allegra 2020 https://github.com/rubber-duck-dragon/rubber-duck-dragon.github.io/blob/8210d352c9527f51ab539b05e2f3a6eb170eea68/cc-cedict_parser/parser.py ###

def cedict(path='cedict_ts.u8', remove_surname=False):
  """Parse CC-Cedict at path -> [dict(trad=…, simp=…, pinyin=…, en=…), …]"""
  with open(path) as file: lines = file.read().split('\n')

  def pLine(line):
    line = line.rstrip('/').split('/')
    if len(line)<=0 or line[0] == '' or line[0][0] == '#': return {}

    en = line[1]
    chars, pinyin, *_ = line[0].split('[')
    trad, simp, *_ = chars.split()
    pinyin = pinyin.rstrip().rstrip("]")

    if remove_surname and "surname " in en: return {}  # note: removed and cedict[x]['trad'] == cedict[x+1]['trad']  # Original author note: Characters that are commonly used as surnames have two entries in CC-CEDICT. This program will remove the surname entry if there is another entry for the character. If you want to include the surnames, simply delete lines 59 and 60.
    return dict( trad=trad, simp=simp, pinyin=pinyin, en=en )
  
  return list(filter(lambda x: x != {}, map(pLine, lines)))

if __name__ == '__main__': print(cedict())
