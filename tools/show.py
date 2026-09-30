import json,sys,glob
sys.path.insert(0, ".")
from eelab.core import fmt
for pat in sys.argv[1:]:
    for f in sorted(glob.glob(f"projects/*/*/{pat}*/results.json")):
        r=json.load(open(f)); print("==",r['meta']['id'],r['meta']['title'],r['runtime_s'])
        for x in r['rows']: print(f"   {x['quantity'][:55]:55s} P={fmt(x['predicted'],x['unit']):>14s} M={fmt(x['measured'],x['unit']):>14s} {x['error_str']}")
        for m in r['metrics']: print(f"   * {m['quantity'][:55]:55s} {fmt(m['value'],m['unit'])} {m['note'][:50]}")
