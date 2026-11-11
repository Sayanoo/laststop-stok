import re, json, os, glob, shutil
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s=open(os.path.join(R,"docs/index.html"),encoding="utf-8").read()
s=re.sub(r'<script src="https://www.gstatic.com[^>]*></script>\n?','',s)
seed={os.path.basename(f)[:-5]:json.load(open(f,encoding="utf-8")) for f in glob.glob(os.path.join(R,"export/items/*.json"))}
s=s.replace('<script src="config.js"></script><script src="shim.js"></script>','<script>window.SEED='+json.dumps(seed,ensure_ascii=False)+'</script><script src="mock.js"></script>')
open(os.path.join(R,"test/index.html"),"w",encoding="utf-8").write(s)
for f in ["logo.png"]: shutil.copy(os.path.join(R,"docs",f),os.path.join(R,"test",f))
print("test page", len(seed))
