# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The Windows folder picker, opened by the local program for the page's "Browse folders": the same
Explorer-style window Windows uses for choosing a folder.

A browser can open a native folder picker, but it never hands the page the folder's PATH — and the
page works in a folder by its path. So the local program opens it instead: the same Explorer-style
"Select Folder" window Windows uses (IFileOpenDialog with FOS_PICKFOLDERS), through PowerShell,
which every Windows carries — nothing added to the bundle. The window belongs to the person's own
click; it reads nothing and writes nothing, and the path it returns goes through the same checks a
typed path does.

Where it can open: on Windows, directly. Under WSL (the demo), through a Windows Python that can
start PowerShell — the one `YTAX_WINDOWS_PYTHON` names — when WSL's interop is working. Anywhere else it is not available, and the page falls back to its own folder list.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ytax_prep.engine.adapter import child_window

POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
TIMEOUT = 900        # a person choosing a folder; the window is theirs until they close it


class PickerUnavailable(RuntimeError):
    """No Windows folder picker can be opened from here."""


# The dialog itself. Written once, passed to PowerShell as its command. It prints the chosen
# folder's file-system path, or nothing when the person cancels. A hidden window owns the dialog and
# is brought to the front first, so the dialog opens in front of the browser rather than behind it:
# started with no console window, PowerShell is a background process, and Windows opened the dialog
# behind the browser (2026-10-12, rc.4 test run).
_SCRIPT = r'''
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class YtaxPicker {
  [ComImport, Guid("DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7")] class FileOpenDialog {}
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  struct FilterSpec { [MarshalAs(UnmanagedType.LPWStr)] public string Name; [MarshalAs(UnmanagedType.LPWStr)] public string Spec; }
  [ComImport, Guid("42f85136-db7e-439c-85f1-e4075d135fc8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IFileOpenDialog {
    [PreserveSig] int Show(IntPtr parent);
    void SetFileTypes(uint count, [MarshalAs(UnmanagedType.LPArray)] FilterSpec[] specs);
    void SetFileTypeIndex(uint index); void GetFileTypeIndex(); void Advise(); void Unadvise();
    void SetOptions(uint fos); void GetOptions(out uint fos);
    void SetDefaultFolder(IShellItem psi); void SetFolder(IShellItem psi);
    void GetFolder(); void GetCurrentSelection(); void SetFileName(); void GetFileName();
    void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string title);
    void SetOkButtonLabel(); void SetFileNameLabel();
    void GetResult(out IShellItem ppsi);
    void AddPlace(); void SetDefaultExtension(); void Close(); void SetClientGuid(); void ClearClientData(); void SetFilter();
    void GetResults(out IShellItemArray items);
  }
  [ComImport, Guid("B63EA76D-1F85-456F-A19C-48159EFA858B"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IShellItemArray {
    void BindToHandler(); void GetPropertyStore(); void GetPropertyDescriptionList(); void GetAttributes();
    void GetCount(out uint count); void GetItemAt(uint index, out IShellItem item);
  }
  [ComImport, Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IShellItem {
    void BindToHandler(); void GetParent();
    void GetDisplayName(uint sigdn, [MarshalAs(UnmanagedType.LPWStr)] out string name);
  }
  [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
  static extern void SHCreateItemFromParsingName(string path, IntPtr pbc, [MarshalAs(UnmanagedType.LPStruct)] Guid riid, out IShellItem item);
  [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window, IntPtr process);
  [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] static extern bool AttachThreadInput(uint from, uint to, bool attach);
  [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr window);
  // Windows lets only the foreground process bring a window forward, and the browser is the
  // foreground process. Sharing its input state for the one call lets the owner take the front, and
  // the dialog it owns opens there.
  public static void ToFront(IntPtr window) {
    uint front = GetWindowThreadProcessId(GetForegroundWindow(), IntPtr.Zero), mine = GetCurrentThreadId();
    bool attached = front != 0 && front != mine && AttachThreadInput(front, mine, true);
    SetForegroundWindow(window);
    if (attached) { AttachThreadInput(front, mine, false); }
  }
  public static string Pick(IntPtr owner, string start, string title, bool files) {
    var dialog = (IFileOpenDialog)new FileOpenDialog();
    if (files) {
      // several tax documents at once: the PDFs, or this return's workbook
      dialog.SetOptions(0x200 | 0x40 | 0x1000);      // ALLOWMULTISELECT | FORCEFILESYSTEM | FILEMUSTEXIST
      dialog.SetFileTypes(2, new[] { new FilterSpec { Name = "Tax documents (PDF) and the workbook", Spec = "*.pdf;*.xlsx" },
                                     new FilterSpec { Name = "All files", Spec = "*.*" } });
      dialog.SetFileTypeIndex(1);
    } else {
      dialog.SetOptions(0x20 | 0x40);                // FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM
    }
    dialog.SetTitle(title);
    if (!string.IsNullOrEmpty(start)) {
      try { IShellItem folder; SHCreateItemFromParsingName(start, IntPtr.Zero, typeof(IShellItem).GUID, out folder); dialog.SetFolder(folder); } catch { }
    }
    if (dialog.Show(owner) != 0) { return ""; }     // cancelled, or closed
    string path;
    if (files) {
      IShellItemArray items; dialog.GetResults(out items);
      uint count; items.GetCount(out count);
      var chosen = new System.Collections.Generic.List<string>();
      for (uint i = 0; i < count; i++) { IShellItem item; items.GetItemAt(i, out item); item.GetDisplayName(0x80058000, out path); chosen.Add(path); }
      return string.Join("\n", chosen);
    }
    IShellItem result; dialog.GetResult(out result);
    result.GetDisplayName(0x80058000, out path);   // SIGDN_FILESYSPATH
    return path;
  }
}
"@
if ($env:YTAX_PICK_CHECK) { [Console]::Out.Write("ready"); exit 0 }   # compiled, nothing shown
$owner = New-Object System.Windows.Forms.Form -Property @{TopMost = $true; ShowInTaskbar = $false; Opacity = 0}
$owner.Show(); [YtaxPicker]::ToFront($owner.Handle)
try { [Console]::Out.Write([YtaxPicker]::Pick($owner.Handle, $env:YTAX_PICK_START, $env:YTAX_PICK_TITLE, [bool]$env:YTAX_PICK_FILES)) }
finally { $owner.Close() }
'''

TITLE = "Choose the folder yTax works in"


def _command(start: str) -> list | None:
    """How to reach PowerShell from here, or None."""
    if os.name == "nt":
        return [POWERSHELL, "-NoProfile", "-NonInteractive", "-STA", "-Command", _SCRIPT]
    interop = Path("/proc/sys/fs/binfmt_misc/WSLInterop")
    python = os.environ.get("YTAX_WINDOWS_PYTHON")
    if interop.exists() and python and Path(python).is_file():
        # WSL: a Windows Python starts PowerShell on the Windows side; the environment carries
        # the start folder and the title across (WSLENV), the script travels as an argument
        runner = ("import os, subprocess, sys; "
                  f"r = subprocess.run([{POWERSHELL!r}, '-NoProfile', '-NonInteractive', '-STA', "
                  "'-Command', sys.argv[1]], capture_output=True, text=True); "
                  "sys.stdout.write(r.stdout); sys.stderr.write(r.stderr); sys.exit(r.returncode)")
        return [str(python), "-c", runner, _SCRIPT]
    return None


def check() -> bool:
    """Whether the picker compiles and could open here — without showing anything."""
    command = _command("")
    if command is None:
        return False
    env = dict(os.environ, YTAX_PICK_CHECK="1")
    if os.name != "nt":
        env["WSLENV"] = ":".join(filter(None, [env.get("WSLENV", ""), "YTAX_PICK_CHECK"]))
    try:
        done = subprocess.run(command, env=env, capture_output=True, text=True, timeout=120,
                              **child_window())
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0 and done.stdout.strip() == "ready"


FILES_TITLE = "Choose your tax documents"


def pick_files(start: str = "") -> list:
    """The documents the person chose — Windows paths — starting in `start` (the working folder's
    input): [] when they cancelled. The browser's own file chooser opens wherever the browser last
    looked, whatever folder the page works in (seen again 2026-09-24)."""
    chosen = _run(start, FILES_TITLE, files=True)
    return [line for line in (chosen or "").splitlines() if line.strip()]


def pick_folder(start: str = "") -> str | None:
    """The folder the person chose, as a Windows path, or None when they cancelled.
    Raises PickerUnavailable when no picker can be opened from this computer."""
    return _run(start, TITLE, files=False)


def _run(start: str, title: str, files: bool) -> str | None:
    command = _command(start)
    if command is None:
        raise PickerUnavailable("no Windows folder picker can be opened from here")
    env = dict(os.environ, YTAX_PICK_START=start or "", YTAX_PICK_TITLE=title,
               YTAX_PICK_FILES="1" if files else "")
    if os.name != "nt":
        env["WSLENV"] = ":".join(filter(None, [env.get("WSLENV", ""), "YTAX_PICK_START",
                                                 "YTAX_PICK_TITLE", "YTAX_PICK_FILES"]))
    try:
        # PowerShell is a console program and `yTax.exe` has no console: without this, Windows
        # opens a console window for it before the picker appears
        done = subprocess.run(command, env=env, capture_output=True, text=True, timeout=TIMEOUT,
                              **child_window())
    except (OSError, subprocess.TimeoutExpired) as why:
        raise PickerUnavailable(f"the folder picker could not be opened: {why}") from why
    if done.returncode != 0:
        raise PickerUnavailable("the folder picker could not be opened: "
                                + (done.stderr.strip().splitlines() or ["no reason given"])[-1])
    chosen = done.stdout.strip()
    return chosen or None
