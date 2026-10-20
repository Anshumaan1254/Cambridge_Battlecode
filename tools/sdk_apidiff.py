#!/usr/bin/env python3
"""usage: tools/sdk_apidiff.py DOC.md OLD_cambc.h NEW_cambc.h: every "### name" entry of an API markdown export, searched in two SDK headers
(prints the names missing from either), plus the enums the document lists. Session 15: docs/sprint/RULES_DIFF.md."""
import re,sys
doc=open(sys.argv[1]).read()
h22=open(sys.argv[2]).read(); h30=open(sys.argv[3]).read()
sec=None; names=[]
for line in doc.splitlines():
    if line.startswith('## '): sec=line[3:].strip()
    elif line.startswith('### '): names.append((sec,line[4:].strip()))
seen=set(); 
for s,n in names:
    if (s,n) in seen: continue
    seen.add((s,n))
    w=re.compile(r'\b'+re.escape(n)+r'\b')
    a=bool(w.search(h22)); b=bool(w.search(h30))
    if not (a and b): print(f"{s}::{n}  2.2.5={a} 3.0.1={b}")
print(len(seen),'doc entries')
# enum/value lists in code blocks: champion_draft, camp_type, passive_type, ability_kind
for key in ['enum class champion_draft','enum class champion_type','enum class camp_type','enum class passive_type','enum class ability_kind','enum class item_passive']:
    m=re.search(re.escape(key)+r'[^{]*\{([^}]*)\}',doc)
    print(key,'DOC:',m.group(1).strip() if m else None)
