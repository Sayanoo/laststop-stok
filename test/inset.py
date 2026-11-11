import pathlib, sys
from playwright.sync_api import sync_playwright
U=(pathlib.Path(__file__).parent/"index.html").as_uri(); SH=pathlib.Path(__file__).parent/"shots"
tag=sys.argv[1] if len(sys.argv)>1 else "x"
with sync_playwright() as p:
    b=p.chromium.launch(channel="chrome")
    ctx=b.new_context(viewport={"width":384,"height":820},device_scale_factor=2,is_mobile=True,has_touch=True,color_scheme="dark")
    pg=ctx.new_page(); cdp=ctx.new_cdp_session(pg)
    try: cdp.send("Emulation.setSafeAreaInsetsOverride",{"insets":{"top":40,"bottom":24}}); print("inset override ok")
    except Exception as e: print("no override:",str(e)[:100])
    pg.goto(U); pg.wait_for_selector(".row[data-item]")
    print("env top:",pg.evaluate("()=>{const d=document.createElement('div');d.style.height='env(safe-area-inset-top,0px)';document.body.append(d);const h=d.getBoundingClientRect().height;d.remove();return h}"))
    bad=0
    for t in ["stok","cikis","sayim","siparis","hareket"]:
        pg.click(f'.tab[data-tab="{t}"]'); pg.wait_for_timeout(200)
        r=pg.evaluate("""()=>{const hb=document.querySelector('header').getBoundingClientRect().bottom;const m=document.querySelector('#main');const f=m.firstElementChild;return {scroll:scrollY,header:hb,first:f?f.getBoundingClientRect().top:null}}""")
        ok=r["first"] is not None and r["first"]>=r["header"]-0.5; bad+=not ok
        print(t,r,"OK" if ok else "ÜSTÜ ÖRTÜLÜYOR")
        pg.screenshot(path=str(SH/f"inset-{tag}-{t}.png"))
    b.close(); print("SONUÇ:", "TEMİZ" if not bad else f"{bad} sekmede sorun")
