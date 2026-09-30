import os
import json
import time
import subprocess
import urllib.parse
from tkinter import messagebox
from typing import Tuple, Optional

# Hardcoded recipient number. Please replace with your own phone number.
# Include country code without any spaces or special characters (e.g. +91XXXXXXXXXX or 919876543210)
PHONE_NUMBER = "+917240072503"

class WhatsAppService:
    """
    Manages automation for the native WhatsApp Desktop App on Windows.
    Sends startup and shutdown alerts and Daily Summary PDF statements to the configured/hardcoded number.
    """
    def __init__(self, parent_app=None, config_path: str = "settings.json"):
        self.parent_app = parent_app
        self.config_path = config_path

    def _load_config(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Loads WhatsApp configurations from settings.json."""
        if not os.path.exists(self.config_path):
            return None, None, None
        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
                return (
                    data.get("access_token") or data.get("whatsapp_token"),
                    data.get("phone_number_id") or data.get("whatsapp_phone_id"),
                    data.get("recipient_number") or data.get("whatsapp_recipient")
                )
        except Exception as e:
            print(f"[WhatsApp] Failed to read configurations: {e}")
            return None, None, None

    def _get_recipient(self) -> Optional[str]:
        """Returns the configured or hardcoded phone number."""
        # Clean number from PHONE_NUMBER constant if it's not a placeholder
        if PHONE_NUMBER and "X" not in PHONE_NUMBER:
            return "".join(filter(str.isdigit, PHONE_NUMBER))
            
        # Fall back to settings.json
        _, _, settings_recipient = self._load_config()
        if settings_recipient:
            return "".join(filter(str.isdigit, settings_recipient))
            
        return None

    def _run_powershell(self, script: str) -> bool:
        """Executes a PowerShell script block, captures and prints stdout/stderr."""
        try:
            print("[WhatsApp] Executing PowerShell automation script...")
            # Run powershell command
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            print("[WhatsApp] PowerShell STDOUT:")
            print(res.stdout)
            if res.returncode != 0:
                print(f"[WhatsApp] PowerShell Error Return Code: {res.returncode}")
                print(f"[WhatsApp] PowerShell STDERR: {res.stderr}")
                return False
            print("[WhatsApp] PowerShell script completed successfully.")
            return True
        except Exception as e:
            print(f"[WhatsApp] Failed to run PowerShell: {e}")
            return False

    def send_text_report(self, text: str) -> bool:
        """
        Sends a text message using the native WhatsApp Desktop App.
        """
        recipient = self._get_recipient()
        if not recipient:
            print("[WhatsApp] No phone number configured. Skipping startup notification.")
            return False

        print(f"[WhatsApp] Sending startup status report to {recipient} via native app...")
        
        # URL encode text for safe protocol URL launching
        encoded_text = urllib.parse.quote(text)
        
        ps_script = f"""
        $sig = '
        using System;
        using System.Runtime.InteropServices;
        using System.Text;
        using System.Collections.Generic;
        public class Win32API {{
            [DllImport("user32.dll")]
            [return: MarshalAs(UnmanagedType.Bool)]
            public static extern bool SetForegroundWindow(IntPtr hWnd);
            [DllImport("user32.dll")]
            public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
            [DllImport("user32.dll")]
            public static extern IntPtr GetForegroundWindow();
            [DllImport("user32.dll")]
            public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
            [DllImport("user32.dll")]
            [return: MarshalAs(UnmanagedType.Bool)]
            public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
            [DllImport("user32.dll")]
            [return: MarshalAs(UnmanagedType.Bool)]
            public static extern bool IsWindowVisible(IntPtr hWnd);
            
            public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
            
            public static List<IntPtr> FindWindowsWithTitle(string titleSubstring) {{
                List<IntPtr> found = new List<IntPtr>();
                EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {{
                    if (IsWindowVisible(hWnd)) {{
                        StringBuilder sb = new StringBuilder(256);
                        GetWindowText(hWnd, sb, 256);
                        string title = sb.ToString();
                        if (title.IndexOf(titleSubstring, StringComparison.OrdinalIgnoreCase) >= 0) {{
                            found.Add(hWnd);
                        }}
                    }}
                    return true;
                }}, IntPtr.Zero);
                return found;
            }}
        }}
        '
        Add-Type -TypeDefinition $sig -ErrorAction SilentlyContinue
        [void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms')

        function Get-ActiveWindowTitle {{
            $hwnd = [Win32API]::GetForegroundWindow()
            $title = New-Object System.Text.StringBuilder 256
            [Win32API]::GetWindowText($hwnd, $title, 256) | Out-Null
            return $title.ToString()
        }}

        function Focus-WhatsApp {{
            Write-Output "Searching for WhatsApp window using EnumWindows..."
            $hwnds = [Win32API]::FindWindowsWithTitle("WhatsApp")
            if ($hwnds -and $hwnds.Count -gt 0) {{
                $hwnd = $hwnds[0]
                Write-Output "Found WhatsApp window (HWND: $hwnd). Restoring and setting foreground..."
                [Win32API]::ShowWindowAsync($hwnd, 9) | Out-Null
                Start-Sleep -m 100
                [Win32API]::SetForegroundWindow($hwnd) | Out-Null
                Start-Sleep -m 400
                $cur = Get-ActiveWindowTitle
                Write-Output "Active window title after HWND focus: '$cur'"
                return ($cur -like "*WhatsApp*")
            }}
            Write-Output "EnumWindows search returned nothing. Trying COM AppActivate fallback..."
            $wshell = New-Object -ComObject wscript.shell;
            if ($wshell.AppActivate('WhatsApp')) {{
                Start-Sleep -m 400
                $cur = Get-ActiveWindowTitle
                Write-Output "Active window title after AppActivate fallback: '$cur'"
                return ($cur -like "*WhatsApp*")
            }}
            Write-Output "Failed to find or focus WhatsApp window."
            return $false
        }}

        $uri = "whatsapp://send?phone={recipient}&text={encoded_text}"
        Write-Output "Opening protocol URI: whatsapp://send?phone={recipient}"
        Start-Process $uri
        Write-Output "Waiting 8 seconds for contact chat to load and text to prefill..."
        Start-Sleep -s 8

        if (Focus-WhatsApp) {{
            $activeTitle = Get-ActiveWindowTitle
            Write-Output "WhatsApp focused. Active Window: '$activeTitle'"
            Write-Output "Sending ENTER key to send text message..."
            [System.Windows.Forms.SendKeys]::SendWait("{{ENTER}}")
            Start-Sleep -s 2
            Write-Output "Startup text report automation completed."
        }} else {{
            Write-Error "Could not find or focus WhatsApp window"
            exit 1
        }}
        """
        return self._run_powershell(ps_script)

    def send_report_with_pdf(self, text: str, pdf_path: str) -> bool:
        """
        Sends a text message and attaches the daily summary PDF using the native WhatsApp Desktop App.
        """
        recipient = self._get_recipient()
        if not recipient:
            print("[WhatsApp] No phone number configured. Skipping shutdown report.")
            return False

        abs_pdf_path = os.path.abspath(pdf_path)
        if not os.path.exists(abs_pdf_path):
            print(f"[WhatsApp] PDF file not found at: {abs_pdf_path}. Sending text report only.")
            return self.send_text_report(text)

        print(f"[WhatsApp] Sending shutdown status and PDF to {recipient} via native app...")
        
        # URL encode text for safe protocol URL launching
        encoded_text = urllib.parse.quote(text)
        
        ps_script = f"""
        $sig = '
        using System;
        using System.Runtime.InteropServices;
        using System.Text;
        using System.Collections.Generic;
        public class Win32API {{
            [DllImport("user32.dll")]
            [return: MarshalAs(UnmanagedType.Bool)]
            public static extern bool SetForegroundWindow(IntPtr hWnd);
            [DllImport("user32.dll")]
            public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
            [DllImport("user32.dll")]
            public static extern IntPtr GetForegroundWindow();
            [DllImport("user32.dll")]
            public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
            [DllImport("user32.dll")]
            [return: MarshalAs(UnmanagedType.Bool)]
            public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
            [DllImport("user32.dll")]
            [return: MarshalAs(UnmanagedType.Bool)]
            public static extern bool IsWindowVisible(IntPtr hWnd);
            
            public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
            
            public static List<IntPtr> FindWindowsWithTitle(string titleSubstring) {{
                List<IntPtr> found = new List<IntPtr>();
                EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {{
                    if (IsWindowVisible(hWnd)) {{
                        StringBuilder sb = new StringBuilder(256);
                        GetWindowText(hWnd, sb, 256);
                        string title = sb.ToString();
                        if (title.IndexOf(titleSubstring, StringComparison.OrdinalIgnoreCase) >= 0) {{
                            found.Add(hWnd);
                        }}
                    }}
                    return true;
                }}, IntPtr.Zero);
                return found;
            }}
        }}
        '
        Add-Type -TypeDefinition $sig -ErrorAction SilentlyContinue
        [void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms')

        function Get-ActiveWindowTitle {{
            $hwnd = [Win32API]::GetForegroundWindow()
            $title = New-Object System.Text.StringBuilder 256
            [Win32API]::GetWindowText($hwnd, $title, 256) | Out-Null
            return $title.ToString()
        }}

        function Focus-WhatsApp {{
            Write-Output "Searching for WhatsApp window using EnumWindows..."
            $hwnds = [Win32API]::FindWindowsWithTitle("WhatsApp")
            if ($hwnds -and $hwnds.Count -gt 0) {{
                $hwnd = $hwnds[0]
                Write-Output "Found WhatsApp window (HWND: $hwnd). Restoring and setting foreground..."
                [Win32API]::ShowWindowAsync($hwnd, 9) | Out-Null
                Start-Sleep -m 100
                [Win32API]::SetForegroundWindow($hwnd) | Out-Null
                Start-Sleep -m 400
                $cur = Get-ActiveWindowTitle
                Write-Output "Active window title after HWND focus: '$cur'"
                return ($cur -like "*WhatsApp*")
            }}
            Write-Output "EnumWindows search returned nothing. Trying COM AppActivate fallback..."
            $wshell = New-Object -ComObject wscript.shell;
            if ($wshell.AppActivate('WhatsApp')) {{
                Start-Sleep -m 400
                $cur = Get-ActiveWindowTitle
                Write-Output "Active window title after AppActivate fallback: '$cur'"
                return ($cur -like "*WhatsApp*")
            }}
            Write-Output "Failed to find or focus WhatsApp window."
            return $false
        }}

        $uri = "whatsapp://send?phone={recipient}&text={encoded_text}"
        Write-Output "Opening protocol URI: whatsapp://send?phone={recipient}"
        Start-Process $uri
        Write-Output "Waiting 8 seconds for contact chat to load and text to prefill..."
        Start-Sleep -s 8

        if (Focus-WhatsApp) {{
            # 1. Send the text report first
            $activeTitle = Get-ActiveWindowTitle
            Write-Output "Active Window before text Enter: '$activeTitle'"
            Write-Output "Sending ENTER key to send text message..."
            [System.Windows.Forms.SendKeys]::SendWait("{{ENTER}}")
            Start-Sleep -s 2
            
            # 2. Copy PDF file to clipboard using PowerShell's Set-Clipboard -Path
            if (Test-Path "{abs_pdf_path}") {{
                Write-Output "Copying PDF to Clipboard: {abs_pdf_path}"
                Set-Clipboard -Path "{abs_pdf_path}"
                Start-Sleep -m 500
                
                # Activate WhatsApp again and paste (Ctrl+V)
                if (Focus-WhatsApp) {{
                    $activeTitle = Get-ActiveWindowTitle
                    Write-Output "Active Window before Paste: '$activeTitle'"
                    Write-Output "Sending Ctrl+V to paste PDF..."
                    [System.Windows.Forms.SendKeys]::SendWait("^v")
                    Write-Output "Waiting 4 seconds for attachment preview window to load..."
                    Start-Sleep -s 4
                    
                    # Confirm sending PDF by pressing Enter on the preview window
                    if (Focus-WhatsApp) {{
                        $activeTitle = Get-ActiveWindowTitle
                        Write-Output "Active Window before attachment Enter: '$activeTitle'"
                        Write-Output "Sending ENTER to dispatch PDF..."
                        [System.Windows.Forms.SendKeys]::SendWait("{{ENTER}}")
                        Start-Sleep -s 2
                        Write-Output "Text and PDF dispatch completed successfully."
                    }} else {{
                        Write-Error "Could not focus WhatsApp for confirmation Enter"
                        exit 1
                    }}
                }} else {{
                    Write-Error "Could not focus WhatsApp for Paste command"
                    exit 1
                }}
            }}
        }} else {{
            Write-Error "Could not find or focus WhatsApp window"
            exit 1
        }}
        """
        return self._run_powershell(ps_script)
