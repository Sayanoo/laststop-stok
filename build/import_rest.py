import json, os, sys, urllib.request
K="AIzaSyD8-lambe8bUCX0AY68XDWXI3Gns9DDlyA"; P="laststop-stok-4787"; B=os.path.dirname(os.path.abspath(__file__))
def post(url, body, tok=None):
    h={"Content-Type":"application/json"}
    if tok: h["Authorization"]="Bearer "+tok
    return json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), h)))
pw=open(os.path.join(B,".pw")).read().strip()
tok=post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={K}",{"email":"dukkan@laststop-stok-4787.firebaseapp.com","password":pw,"returnSecureToken":True})["idToken"]
def val(v):
    if v is None: return {"nullValue":None}
    if isinstance(v,bool): return {"booleanValue":v}
    if isinstance(v,int): return {"integerValue":str(v)}
    if isinstance(v,float): return {"doubleValue":v}
    if isinstance(v,str): return {"stringValue":v}
    if isinstance(v,list): return {"arrayValue":{"values":[val(x) for x in v]}}
    if isinstance(v,dict): return {"mapValue":{"fields":{k:val(x) for k,x in v.items()}}}
    raise TypeError(v)
d=os.path.join(B,"..","export","items"); writes=[]
for f in sorted(os.listdir(d)):
    x=json.load(open(os.path.join(d,f),encoding="utf-8")); x.pop("updatedBy",None)
    writes.append({"update":{"name":f"projects/{P}/databases/(default)/documents/items/{f[:-5]}","fields":{k:val(v) for k,v in x.items()}}})
r=post(f"https://firestore.googleapis.com/v1/projects/{P}/databases/(default)/documents:commit",{"writes":writes},tok)
print("written",len(r.get("writeResults",[])))
