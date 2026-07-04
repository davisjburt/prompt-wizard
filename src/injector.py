import time

import keyboard
import pyperclip


def paste_text(text: str, restore_clipboard: bool = True):
    """Put text at the cursor of the focused window via clipboard paste."""
    old = None
    if restore_clipboard:
        try:
            old = pyperclip.paste()
        except Exception:
            old = None
    pyperclip.copy(text)
    time.sleep(0.05)
    keyboard.send("ctrl+v")
    if restore_clipboard and old is not None:
        # Give the target app time to read the clipboard before restoring
        time.sleep(0.4)
        pyperclip.copy(old)


def copy_text(text: str):
    pyperclip.copy(text)
