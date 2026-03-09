import time
from playwright.sync_api import sync_playwright

TARGET_URL = "https://vgu-rangers-monitoring.streamlit.app/"
BUTTON_TEXT = "back up"

def wake_streamlit():
    print("Starting Streamlit wake check")

    start = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = browser.new_page()

        try:
            print("Opening app...")
            page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)

            # wait for streamlit frontend
            page.wait_for_selector("#root", timeout=20000)

            print("Page loaded")

            buttons = page.locator(f"button:has-text('{BUTTON_TEXT}')")

            if buttons.count() > 0:
                print("App sleeping → clicking wake button")
                buttons.first.click()
                time.sleep(3)
            else:
                print("App already awake")

        except Exception as e:
            print("Error during wake check:", e)

        finally:
            elapsed = round(time.time() - start, 2)
            print(f"Finished in {elapsed}s")
            browser.close()


if __name__ == "__main__":
    wake_streamlit()