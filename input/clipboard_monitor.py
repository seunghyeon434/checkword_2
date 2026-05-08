import time

import pyperclip


def monitor_clipboard(callback, initial_text=""):
    last_text = initial_text
    first_sample = True
    last_time = 0.0

    while True:
        text = pyperclip.paste()

        if first_sample:
            first_sample = False
            if text != last_text and text.strip():
                last_text = text
                last_time = time.time()
                callback(text)
            time.sleep(0.25)
            continue

        if text != last_text and text.strip():
            current_time = time.time()
            if current_time - last_time > 0.6:
                last_text = text
                last_time = current_time
                callback(text)

        time.sleep(0.25)
