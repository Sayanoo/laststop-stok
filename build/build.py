# Artifact HTML'ini GitHub Pages sayfasına çevirir: python build.py <artifact.html>
import sys, os, re, shutil
src = sys.argv[1]; root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); out = os.path.join(root, "docs")
body = open(src, encoding="utf-8").read()
V = "12.19.0"
head = f'''<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1A0E0A"><link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="logo.png"><link rel="apple-touch-icon" href="logo.png">
<style>
#loginGate{{position:fixed;inset:0;z-index:100;display:grid;place-items:center;padding:16px;background:radial-gradient(120% 90% at 0% 0%,#4A1A0C,#150B08 70%)}}
.lg-card{{width:100%;max-width:360px;background:#1E1410;color:#FBEFE6;border-radius:22px;padding:26px 22px;display:grid;gap:12px;box-shadow:0 20px 60px rgba(0,0,0,.5);border:1px solid #3B2A21;font-family:Inter,system-ui,sans-serif}}
.lg-card h2{{margin:0;font:800 24px Archivo,system-ui,sans-serif;text-align:center}} .lg-card p{{margin:0 0 4px;color:#BFA392;text-align:center;font-size:14px}}
.lg-logo{{width:96px;height:96px;border-radius:26px;margin:0 auto;box-shadow:0 0 0 3px #FF8A00,0 10px 30px rgba(255,90,20,.5)}}
.lg-card label{{display:grid;gap:5px;font-size:13px;color:#BFA392}}
.lg-card input{{font:16px Inter,system-ui,sans-serif;padding:12px;border-radius:12px;border:1px solid #3B2A21;background:#130C09;color:#FBEFE6}}
.lg-card .btn{{border:0;border-radius:12px;padding:13px;font:700 16px Inter,system-ui,sans-serif;color:#fff;background:linear-gradient(135deg,#FF8A00,#F2491B 55%,#C8102E);cursor:pointer}}
.lg-err{{color:#FF7A86;font-size:13px;text-align:center;min-height:1em}}
</style>
<script src="https://www.gstatic.com/firebasejs/{V}/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/{V}/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/{V}/firebase-firestore-compat.js"></script>
<script src="config.js"></script><script src="shim.js"></script>
</head><body>
'''
who = '''<script>
(function(){const box=document.querySelector(".hrow > div");if(!box)return;const b=document.createElement("button");b.className="btn ghost sm";b.style.padding="8px 10px";
let n="";try{n=localStorage.getItem("ls-staff-name")||""}catch(_){}b.textContent=n?n.split(" ")[0]:"Kişi";b.title="Kişi değiştir";b.setAttribute("aria-label","Kişi değiştir: "+n);
b.onclick=()=>{if(confirm((n?n+" olarak giriş yapıldı. ":"")+"Kişi değiştirilsin mi?"))lsSwitchUser()};box.prepend(b)})();
</script>'''
html = head + body + who + "\n</body></html>\n"
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html)
for f in ["shim.js", "config.js", "logo.png", "manifest.webmanifest", "icon-512.png"]:
    p = os.path.join(root, "build", f)
    if os.path.exists(p): shutil.copy(p, os.path.join(out, f))
open(os.path.join(out, ".nojekyll"), "w").close()
print("built", len(html))
