import sys
import subprocess
from typing import Optional

class NotificationService:
    """
    Abstraction layer for sending system and in-app notifications.
    Uses native Windows PowerShell command executing balloon notifications as a zero-dependency fallback.
    """
    
    def __init__(self):
        pass

    def send_notification(self, title: str, message: str) -> bool:
        """
        Sends a desktop notification. On Windows, uses PowerShell to trigger balloon toast.
        Returns True if successful, False otherwise.
        """
        # Format message safely for PowerShell string quotes
        safe_title = title.replace("'", "''").replace("\n", " ")
        safe_message = message.replace("'", "''").replace("\n", " ")

        if sys.platform == 'win32':
            try:
                # Powershell script to show balloon tip in System Tray
                ps_script = f"""
                [void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');
                [void] [System.Reflection.Assembly]::LoadWithPartialName('System.Drawing');
                $notification = New-Object System.Windows.Forms.NotifyIcon;
                $notification.Icon = [System.Drawing.SystemIcons]::Information;
                $notification.BalloonTipIcon = 'Info';
                $notification.BalloonTipTitle = '{safe_title}';
                $notification.BalloonTipText = '{safe_message}';
                $notification.Visible = $true;
                $notification.ShowBalloonTip(5000);
                Start-Sleep -m 500;
                $notification.Dispose();
                """
                
                # Execute in background to keep GUI responsive
                subprocess.Popen(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return True
            except Exception as e:
                print(f"Windows notification failed: {e}")
                return False
        else:
            # Fallback for non-Windows platforms
            print(f"[{title}] {message}")
            return True
