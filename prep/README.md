# ytax-prep

`prep/` holds `ytax-prep`, the user-facing application for estimating taxes and preparing returns for filing. Everything runs on the user's own computer; taxpayer data is not sent to ytax or to any AI provider. This folder is its source; ready-to-run packages for Windows and macOS, built from it, are attached to the release (see [Use ytax-prep](../README.md#use-ytax-prep)). It is not a production tax certification or tax advice.

> **A demonstration release.** This release is for demonstration purposes only and is not certified for real filings. The returns it computes and the forms it fills are not for filing with the IRS.

It runs on the ytax calculation engine and fact dictionary in the rest of this repository. The engine pin it expects (engine commit and dictionary content hash) is recorded under `checks.service_pin` in `../provenance/release.json`, and the builder checks that it matches the dictionary shipped here.

The application is ytax material under the release-root [licensing notice](../LICENSING.md): the PolyForm Strict License 1.0.0 in [`../LICENSE`](../LICENSE). Its scope is in [`../legal/COMPONENT-SCOPE.md`](../legal/COMPONENT-SCOPE.md). See [BUILD.md](BUILD.md) to build and run it. Provenance is in `../provenance/`; runtime and tax tests are not run by the packaging script.
