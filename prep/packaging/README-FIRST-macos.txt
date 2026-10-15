ytax-prep {version} for macOS (Apple silicon and Intel)
=======================================================

NOT YET TESTED ON A MAC. This macOS build is made by the same script as the Windows build, which
is tested; the macOS build itself has not been run on a Mac before this release. If it does not
start, or something on the page does not work, please tell us.

ytax-prep estimates your federal tax and prepares the IRS forms for a 2025 return. It runs on
this Mac only: nothing about your return is sent to ytax, to an AI provider, or anywhere else.
It needs macOS 13.5 (Ventura) or later, on Apple silicon or Intel.

A demonstration release
-----------------------
This release is for demonstration purposes only and is not certified for real filings.
The returns it computes and the forms it fills are not for filing with the IRS.

Start it
--------
1. Drag ytax-prep.app to your Applications folder (or keep it anywhere you like). Nothing else
   needs to be installed, and you don't need an administrator password.
2. Double-click ytax-prep. Your web browser opens the ytax-prep page; no other window opens,
   and there is no Dock icon.

The first time only: macOS may say ytax-prep "cannot be opened because the developer cannot be
verified", because this copy is not signed yet. Right-click (or Control-click) ytax-prep, choose
"Open", then click "Open" in the box that appears. On recent macOS versions, if there is no
"Open" button: open System Settings > Privacy & Security, scroll down to the message about
ytax-prep, and click "Open Anyway". macOS remembers your choice for this copy.

Use it
------
- Each time it starts, the page asks which folder to work in. Put your tax documents (PDFs) in
  that folder's "input" folder; the filled forms are written to its "output" folder.
- Everything ytax-prep keeps about a return is in the folder you choose: "input" (your
  documents and answers), "output" (the filled forms) and "temp" (working files, removed after
  each calculation). Use one folder for each return, for example one for each client. Nothing is
  kept in the app, so you can replace it with a newer version without losing anything.
- To try it with made-up households, use the documents in the "examples" folder beside this
  file (each household's PDFs are under examples/profiles/<name>/input).

Stop it
-------
Click "Quit ytax-prep" at the bottom of the page. Closing the browser tab stops it too, about a
minute and a half later (it waits while it is still working on something). Before then, opening
ytax-prep again reopens the page; after, start it again and choose the same folder to carry on
where you left off.

More
----
"About ytax-prep" at the bottom of the page shows the version, the license, and the
third-party software notices (also in THIRD-PARTY-NOTICES.txt beside this file).
ytax-prep is not tax advice and does not file your return.
