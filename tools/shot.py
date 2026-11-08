import sys, asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        for spec in sys.argv[1:]:
            route, w, out = spec.split("|")
            pg = await b.new_page(viewport={"width": int(w), "height": 900})
            errs = []
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.goto("http://localhost:8765/" + route)
            await pg.wait_for_timeout(900)
            await pg.screenshot(path=out, full_page=False)
            print(route, "errors:", errs)
        await b.close()
asyncio.run(main())
