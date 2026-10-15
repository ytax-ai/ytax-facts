# ytax-facts — alpha-0.1.0

**Status:** Public source release.

> **A demonstration release.** This release is for demonstration purposes only and is not certified for real filings. The returns it computes and the forms it fills are not for filing with the IRS.

ytax is a product of TRIPLE J AI LLC (New Jersey); product domain: `ytax.ai`.

`ytax-facts` is the fact XML and calculation engine: the federal TY2025 fact dictionary, the IRS Fact Graph engine it runs on (with ytax changes recorded in `provenance/release.json`), the linked JavaScript engine, the XML-to-JavaScript dictionary generator, the TY2025 printed-form field maps under `dictionary/pdf/2025`, and, under [`prep/`](prep/README.md), `ytax-prep`, the application for estimating taxes and preparing returns on the user's own computer. The repository is source, with one prebuilt file, the linked engine `js/engine/factgraph.js` (see [BUILD.md](BUILD.md)). Ready-to-run packages of `ytax-prep` for Windows and macOS, built from this source, are attached to the release (see [Use ytax-prep](#use-ytax-prep)). Neither is a production tax certification.

See [BUILD.md](BUILD.md), [component boundaries](legal/COMPONENT-SCOPE.md), and [pinned sources](UPSTREAM.md).

## Use ytax-prep

ytax-prep estimates your federal tax and prepares the IRS forms for a 2025 return, on your own computer: nothing about your return is sent to ytax, to an AI provider, or anywhere else. It is not tax advice and does not file your return.

### Download

Open this release on the repository's [Releases](https://github.com/ytax-ai/ytax-facts/releases) page and download the package for your computer. For `alpha-0.1.0` the packages are:

| Your computer | Package |
|---|---|
| Windows 10 or 11, 64-bit | `ytax-prep-alpha-0.1.0-windows-x64.zip` |
| Mac with macOS 13.5 (Ventura) or later, Apple silicon or Intel | `ytax-prep-alpha-0.1.0-macos-universal.zip` |

`ytax-prep-alpha-0.1.0-SHA256SUMS.txt` lists the SHA-256 of each package, to check a download.

### What a package holds

- `README-FIRST.txt`: how to start, use and stop ytax-prep on that computer. Read it first.
- The application: `ytax-prep.exe` and its `_internal` folder on Windows, `ytax-prep.app` on macOS. It carries everything it runs on (Python, Node.js, and this release's linked engine and TY2025 dictionary), so nothing else needs to be installed, and no administrator rights are needed.
- `examples/`: tax documents of made-up households to try it with, each household's PDFs under `examples/profiles/<name>/input`.
- `THIRD-PARTY-NOTICES.txt`: the licenses and notices of the third-party software inside it.

"About ytax-prep", at the bottom of the app's page, shows the version, this release's license documents and the third-party notices.

### Run it

1. Unzip the package and keep the folder anywhere you like. On a Mac you can drag `ytax-prep.app` to Applications.
2. Double-click `ytax-prep.exe` (Windows) or `ytax-prep` (macOS). Your web browser opens the ytax-prep page, served from your own computer; no other window opens.
3. The packages are not yet signed by a publisher, so the first time, the system asks whether to open it. On Windows, at "Windows protected your PC", click "More info", then "Run anyway". On macOS, right-click (or Control-click) ytax-prep, choose "Open", then "Open"; if there is no "Open" button, use "Open Anyway" in System Settings > Privacy & Security. `README-FIRST.txt` has the details.
4. Each time ytax-prep starts, the page asks which folder to work in; it suggests `Documents\ytax-prep` (`Documents/ytax-prep` on macOS). Put your tax documents (PDFs) in its `input` folder; the filled forms are written to its `output` folder.
5. To stop, click "Quit ytax-prep" at the bottom of the page. Closing the tab also stops it, about a minute and a half later.

Everything about a return is kept in the folder you choose: `input` (your documents and answers), `output` (the filled forms and workbook) and `temp` (working files, removed after each calculation, and a log). Use one folder for each return, for example one for each client. ytax-prep keeps nothing in AppData or Application Support, and nothing in the package, so a newer package can replace it without losing anything.

To remove ytax-prep, click "Quit ytax-prep", then delete the unzipped folder (or `ytax-prep.app`). The folders you chose hold your own documents and filled forms; deleting them is up to you.

### Where it is tested

Each package is built from this release's tag on GitHub-hosted machines, twice, and the two builds must be identical byte for byte. Before a package is attached to the release, its own self-test runs there: it computes a sample return through the packaged engine, checks that the engine is the one this release pins, and checks the About documents. The Windows package is tested on Windows Server 2022; the macOS package on macOS 14 with Apple silicon, both natively and as an Intel Mac would run it (Rosetta). A Windows package made by the same build script has also been used on a Windows 11 PC. The macOS package has not yet been used on a person's own Mac.

To build ytax-prep from source instead, see [prep/BUILD.md](prep/BUILD.md).

## License

Original copyrightable ytax contributions identified in [LICENSING.md](LICENSING.md) are offered under the PolyForm Strict License 1.0.0. The public grant covers its stated permitted purposes; see [LICENSE](LICENSE) for the applicable conditions and organizational provisions. Other permissions may be obtained by separate written agreement with TRIPLE J AI LLC. Contact <license@ytax.ai>. Upstream and third-party material retains its own legal status. This release does not withdraw rights already granted under earlier licenses.

The IRS engine files ytax has not changed, and the IRS baseline, keep their upstream public-domain/CC0 notices.

State rules, taxpayer records and test corpora are not included.

Provenance and file comparisons are in `provenance/`; runtime and tax tests are not run by the packaging script.
