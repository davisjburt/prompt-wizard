' Launch Prompt Wizard with no console window (tray icon only).
' Activity is written to logs\prompt-wizard.log
Dim fso, sh, dir
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run """" & dir & "\.venv\Scripts\pythonw.exe"" """ & dir & "\src\main.py""", 0, False
