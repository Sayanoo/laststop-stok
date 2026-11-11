import pathlib
from playwright.sync_api import sync_playwright
U=(pathlib.Path(__file__).parent/"index.html").as_uri(); SH=pathlib.Path(__file__).parent/"shots"
with sync_playwright() as p:
    b=p.chromium.launch(channel="chrome")
    for w,h in [(360,740),(412,915)]:
        ctx=b.new_context(viewport={"width":w,"height":h},device_scale_factor=2,is_mobile=True,has_touch=True,color_scheme="dark")
        pg=ctx.new_page(); ctx.new_cdp_session(pg).send("Emulation.setSafeAreaInsetsOverride",{"insets":{"top":40,"bottom":24}})
        pg.goto(U); pg.wait_for_selector(".row[data-item]")
        pg.mouse.wheel(0,600); pg.wait_for_timeout(300)
        r=pg.evaluate("()=>({hdrTop:document.querySelector('header').getBoundingClientRect().top,scroll:scrollY,hscroll:document.documentElement.scrollWidth>innerWidth})")
        print(w,"kaydırınca başlık:",r)
        pg.screenshot(path=str(SH/f"inset2-{w}-scrolled.png"))
        pg.locator(".row[data-item]").nth(3).click(); pg.wait_for_selector("#amt"); pg.wait_for_timeout(300)
        r=pg.evaluate("()=>{const s=document.querySelector('.sheet').getBoundingClientRect();return {sheetTop:s.top,sheetBottom:s.bottom,vh:innerHeight}}")
        print(w,"pencere:",r); pg.screenshot(path=str(SH/f"inset2-{w}-sheet.png"))
        pg.keyboard.press("Escape"); pg.click('[data-act="close"]') if pg.locator('[data-act="close"]').count() else None; pg.wait_for_timeout(200)
        pg.click('.tab[data-tab="sayim"]'); pg.wait_for_timeout(300)
        r=pg.evaluate("()=>{const s=document.querySelector('.savebar');const b=s&&s.querySelector('.btn:last-child').getBoundingClientRect();return s?{btnBottom:b.bottom,vh:innerHeight}:null}")
        print(w,"sayım kaydet çubuğu:",r); pg.screenshot(path=str(SH/f"inset2-{w}-sayim.png"))
        ctx.close()
    b.close()
