ytax-prep {version} for Windows (64-bit)
=========================================

ytax-prep estimates your federal tax and prepares the IRS forms for a 2025 return. It runs on
this computer only: nothing about your return is sent to ytax, to an AI provider, or anywhere
else.
It needs 64-bit Windows 10 or 11.

A demonstration release
-----------------------
This release is for demonstration purposes only and is not certified for real filings.
The returns it computes and the forms it fills are not for filing with the IRS.

Start it
--------
1. Keep this folder anywhere you like (for example Documents\ytax-prep). Nothing else needs to
   be installed, and you don't need administrator rights.
2. Double-click ytax-prep.exe. Your web browser opens the ytax-prep page; no other window opens.

The first time only: Windows may show "Windows protected your PC", because this copy is not
signed yet. Click "More info", then "Run anyway". Windows remembers your choice for this copy.

Use it
------
- Each time it starts, the page asks which folder to work in. Put your tax documents (PDFs) in
  that folder's "input" folder; the filled forms are written to its "output" folder.
- Everything ytax-prep keeps about a return is in the folder you choose: "input" (your
  documents and answers), "output" (the filled forms) and "temp" (working files, removed after
  each calculation). Use one folder for each return, for example one for each client. Nothing is
  kept in this folder, so you can replace it with a newer version without losing anything.
- To try it with made-up households, use the documents in the "examples" folder beside
  ytax-prep.exe (each household's PDFs are under examples\profiles\<name>\input).

Stop it
-------
Click "Quit ytax-prep" at the bottom of the page. Closing the browser tab stops it too, about a
minute and a half later (it waits while it is still working on something). Before then,
double-clicking ytax-prep.exe again reopens the page; after, start it again and choose the same
folder to carry on where you left off.

More
----
"About ytax-prep" at the bottom of the page shows the version, the license, and the
third-party software notices (also in THIRD-PARTY-NOTICES.txt beside this file).
ytax-prep is not tax advice and does not file your return.
