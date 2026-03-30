Option Explicit

Dim shell, fso, repoRoot, venvPythonw, venvPython, mainPy, installPs1, logPath
Dim command, exitCode

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

repoRoot = fso.GetParentFolderName(WScript.ScriptFullName)
venvPythonw = fso.BuildPath(repoRoot, ".venv-win\Scripts\pythonw.exe")
venvPython = fso.BuildPath(repoRoot, ".venv-win\Scripts\python.exe")
mainPy = fso.BuildPath(repoRoot, "main.py")
installPs1 = fso.BuildPath(repoRoot, "install_windows.ps1")
logPath = shell.ExpandEnvironmentStrings("%TEMP%\shadow-ai-windows-install.log")

If (Not fso.FileExists(venvPythonw)) Or (Not fso.FileExists(venvPython)) Then
    command = "powershell -NoProfile -ExecutionPolicy Bypass -File " & Quote(installPs1) & " -AutoInstallPython"
    exitCode = shell.Run(command, 0, True)
    If exitCode <> 0 Then
        MsgBox "Shadow AI setup failed. Check this log for details:" & vbCrLf & logPath, vbCritical, "Shadow AI"
        WScript.Quit exitCode
    End If
End If

If Not fso.FileExists(venvPythonw) Then
    MsgBox "Shadow AI could not find pythonw.exe after setup. Check this log for details:" & vbCrLf & logPath, vbCritical, "Shadow AI"
    WScript.Quit 1
End If

command = Quote(venvPythonw) & " " & Quote(mainPy)
shell.Run command, 0, False

Function Quote(value)
    Quote = Chr(34) & value & Chr(34)
End Function
