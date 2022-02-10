If WScript.Arguments.Count = 0 Then
	Wscript.Echo "NoConsole: At least one argument is required"
	WScript.Quit
End If
' Join every arguments
command_line = ""
For i = 0 to (WScript.Arguments.Count - 1)
	arg = WScript.Arguments(i)
	If InStr(WScript.Arguments(i), " ") > 0 Then
		' String contains space quote it
		' If string contains quote double it (Escape it)
		
		If InStr(WScript.Arguments(i), """") > 0 Then
			arg = Replace(arg,"""","""""")
			Wscript.Echo arg & ": Contains quote"
		End If
		
		' Now quote it as it contains space
		arg = """" & arg & """"
		
	End If
	command_line = command_line & " " & arg
	
Next
Set objShell = WScript.CreateObject("WScript.Shell")
objShell.Run Trim(command_line), 0, True