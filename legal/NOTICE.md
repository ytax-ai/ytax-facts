# ytax — Notices

## Company and project identity

TRIPLE J AI LLC is a limited liability company registered in New Jersey. ytax is its product and project name; the product website is <https://ytax.ai>. The ytax brand, domain name, and GitHub account name are not separate copyright owners or licensing parties.

## ytax material

Copyright (c) 2026 TRIPLE J AI LLC, solely in its original copyrightable contributions identified in the source notices, [`COMPONENT-SCOPE.md`](COMPONENT-SCOPE.md), and `../provenance/release.json`. Other contributors retain their respective copyrights unless validly transferred.

Contains original tax-rule material from the ytax project. The application under `prep/`, where a release includes it, contains original software from the ytax project.

The identified ytax material is offered under the PolyForm Strict License 1.0.0 (`LicenseRef-PolyForm-Strict-1.0.0`). See [`../LICENSE`](../LICENSE), [`../LICENSING.md`](../LICENSING.md), and [`LICENSE-REFERENCE.md`](LICENSE-REFERENCE.md). Other permissions need a separate written agreement; see [`COMMERCIAL-LICENSING.md`](COMMERCIAL-LICENSING.md).

Rights already granted in copies distributed earlier under other license terms are not withdrawn by this notice.

## IRS-origin and other preexisting material

This release includes material from IRS public repositories: the Fact Graph engine under `engine/fact-graph-scala/`, with ytax changes to some of its files; the Direct File baseline under `upstream/`; and IRS-origin material within mixed dictionary modules and generator files. `../provenance/release.json` records which engine files ytax changed. No copyright is claimed by TRIPLE J AI LLC in preexisting public-domain material.

Consult the license and notices shipped with the exact upstream revision: `engine/fact-graph-scala/LICENSE.md` and `upstream/direct-file/LICENSE`. Any applicable CC0 dedication, upstream copyright notice, and independently licensed third-party material keep their respective status and terms. This notice does not replace them.

## Third-party libraries in the linked engine

`js/engine/factgraph.js` is a whole-program Scala.js link that contains compiled code from the third-party Scala libraries listed, with organization, name, version and license, in `js/engine/factgraph.libraries.tsv` (MIT, Apache-2.0 and BSD-3-Clause licenses at this release; the license file of scala-java-locales also carries the Unicode, Inc. permission notice for its code generated from Unicode CLDR data). Each keeps its own license and copyright notices, which ship unchanged in `js/engine/third-party/`, copied from each project's repository at the released version and indexed in `js/engine/THIRD-PARTY-NOTICES.md`; nothing in this release relicenses them.

Incorporating public-domain content into the ytax material does not make that content material exclusively owned by TRIPLE J AI LLC.

## Origin and endorsement

This is not an official IRS release. The use of IRS-origin materials does not indicate IRS approval, endorsement, certification, sponsorship, or affiliation.

Use of ytax material does not establish a partnership, certification, support arrangement, or endorsement by TRIPLE J AI LLC or the ytax project. Attribution identifies origin; it is not a testimonial.

## Trademarks and warranties

The public license grants no trademark rights in ytax names or logos. Truthful identification and uses otherwise permitted by law are unaffected.

See [`../LICENSE`](../LICENSE) ("No Liability") and any separate written agreement for warranty and liability terms. This notice does not guarantee tax correctness, coverage, filing acceptance, or continuing maintenance.
