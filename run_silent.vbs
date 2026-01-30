Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' Check if venv exists
If Not fso.FolderExists(strPath & "\venv") Then
    MsgBox "Virtual environment not found. Please run setup.bat first.", 16, "Error"
    WScript.Quit
End If

' Run using pythonw.exe (Windowless Python)
' We run directly from venv, skipping run.bat to avoid its console window
WshShell.CurrentDirectory = strPath
WshShell.Run chr(34) & strPath & "\venv\Scripts\pythonw.exe" & chr(34) & " -m app.main", 0
Set WshShell = Nothing
