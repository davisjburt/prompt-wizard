"""Press any key to see what Windows reports for it.

Run this, press your microphone/Copilot button once, and note the
key name / scan code lines it prints. Put that value in config.yaml
as the hotkey. Ctrl+C to quit.
"""
import keyboard


def show(event):
    kind = "DOWN" if event.event_type == "down" else "UP  "
    print(f"{kind}  name={event.name!r:20}  scan_code={event.scan_code}")


print(__doc__)
keyboard.hook(show)
keyboard.wait()
