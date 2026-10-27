from playwright.sync_api import sync_playwright

URL = "https://people-tech-command-center-samnerd.streamlit.app"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)
    button = page.get_by_role("button", name="Yes, get this app back up!")
    if button.count():
        button.first.click()
        page.wait_for_timeout(30000)
    print("Visited:", page.title())
    browser.close()
