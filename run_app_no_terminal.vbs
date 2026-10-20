Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir

pythonwPath = "pythonw.exe"
If fso.FileExists("D:\Python\pythonw.exe") Then
    pythonwPath = """D:\Python\pythonw.exe"""
End If

WshShell.Run pythonwPath & " server.py", 0, False
