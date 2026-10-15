# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Generate synthetic tax-form PDFs for testing. SYNTHETIC DATA ONLY.

All identifiers are deliberately invalid: SSNs use the 000- area (never issued),
EINs and names are fake. These fixtures are the only PDFs committed to the repo.

Generated with reportlab (BSD-3-Clause); encryption via pypdf
(BSD-3-Clause). Same page geometry as before (US Letter, top-down text lines).
"""
from __future__ import annotations

from pathlib import Path

from reportlab.pdfgen import canvas as _rl_canvas

_PAGE_W, _PAGE_H = 612, 792  # US Letter

FAKE_SSN = "000-12-3456"          # 000 area is never issued
FAKE_EIN = "00-7654321"           # fake employer EIN
PARTNERSHIP_EIN = "00-1112223"    # fake partnership EIN (K-1 Box A)
FAKE_NAME = "Pat Q Testperson"
FAKE_ADDR = "123 Nowhere Lane, Faketown, ZZ 00000"


def _write_page(path: Path, lines: list[tuple[float, float, str]]) -> None:
    """One US-Letter page of 10pt Helvetica text lines at top-down (x, y) points."""
    c = _rl_canvas.Canvas(str(path), pagesize=(_PAGE_W, _PAGE_H), invariant=1)
    c.setFont("Helvetica", 10)
    for x, y, text in lines:
        c.drawString(x, _PAGE_H - y, text)  # top-down y -> bottom-up baseline
    c.showPage()
    c.save()


def make_w2(path: Path, *, wages="48,250.00", fed_wh="5,310.00",
            ss_wages="48,250.00", ss_wh="2,991.50",
            medi_wages="48,250.00", medi_wh="699.63",
            box1_label="1 Wages, tips, other compensation") -> Path:
    """`box1_label` is the caption a layout prints for box 1 (profile-C's `1 Wages, tips,
    other comp.`); the IRS wording by default."""
    _write_page(path, [
        (72, 72, "Form W-2  Wage and Tax Statement   2025"),
        (72, 110, f"Employee's name {FAKE_NAME}"),
        (72, 128, f"Employee's address {FAKE_ADDR}"),
        (72, 146, f"Employee's social security number {FAKE_SSN}"),
        (72, 164, f"Employer identification number (EIN) {FAKE_EIN}"),
        (72, 200, f"{box1_label} {wages}"),
        (72, 218, f"2 Federal income tax withheld {fed_wh}"),
        (72, 236, f"3 Social security wages {ss_wages}"),
        (72, 254, f"4 Social security tax withheld {ss_wh}"),
        (72, 272, f"5 Medicare wages and tips {medi_wages}"),
        (72, 290, f"6 Medicare tax withheld {medi_wh}"),
        # A brokerage-style bare number that must SURVIVE redaction (CUSIP-like).
        (72, 340, "Reference 037833100 lot 000123456"),
    ])
    return path


def make_1099int(path: Path, *, interest="1,234.00", premiums: bool = False) -> Path:
    _write_page(path, [
        (72, 72, "Form 1099-INT  Interest Income   2025"),
        (72, 110, f"Recipient's name {FAKE_NAME}"),
        (72, 128, f"Recipient's TIN {FAKE_SSN}"),
        (72, 164, f"1 Interest income {interest}"),
        # Boxes 2 and 9-13 are printed as the IRS form prints them: blank unless asked for (a
        # blank box is a stated 0; a box the page does not print at all is asked).
        (72, 182, "2 Early withdrawal penalty" + (" 300.00" if premiums else "")),
        (72, 200, "9 Specified private activity bond interest" + (" 50.00" if premiums else "")),
        (72, 218, "10 Market discount" + (" 200.00" if premiums else "")),
        (72, 236, "11 Bond premium" + (" 100.00" if premiums else "")),
        (72, 254, "12 Bond premium on Treasury obligations" + (" 40.00" if premiums else "")),
        (72, 272, "13 Bond premium on tax-exempt bond" + (" 30.00" if premiums else "")),
    ])
    return path


def make_1099b(path: Path, *, wash_sale="", withheld="", loss_not_allowed: bool = False) -> Path:
    """Form 1099-B, ONE transaction, captions as the 2025 form prints them. The description, the
    CUSIP and the state boxes are printed too — they have no fact field and must be left alone."""
    _write_page(path, [
        (72, 72, "Form 1099-B  Proceeds From Broker and Barter Exchange Transactions   2025"),
        (72, 100, f"Recipient's name {FAKE_NAME}"),
        (72, 118, f"Recipient's TIN {FAKE_SSN}"),
        (72, 146, "1a Description of property 100 SH SYNTHETIC CO"),
        (72, 164, "1b Date acquired 02/03/2025"),
        (72, 182, "1c Date sold or disposed 06/16/2025"),
        (72, 200, "1d Proceeds 10,000.00"),
        (72, 218, "1e Cost or other basis 12,000.00"),
        (72, 236, "1f Accrued market discount"),
        (72, 254, f"1g Wash sale loss disallowed {wash_sale}".rstrip()),
        (72, 272, "2 Short-term gain or loss [X]  Long-term gain or loss  Ordinary"),
        (72, 290, "3 Check if proceeds from: Collectibles  QOF"),
        (72, 308, f"4 Federal income tax withheld {withheld}".rstrip()),
        (72, 326, "7 Check if loss is not allowed based on amount in 1d" + (" [X]" if loss_not_allowed else "")),
        (72, 344, "12 Check if basis reported to IRS [X]"),
    ])
    return path


def make_1099oid(path: Path, *, fatca: bool = False, box2="500.00", box11="") -> Path:
    """Form 1099-OID with every box the fact schema holds, captions as printed. Box 7, box 9 and
    the state boxes are printed too — they have no fact field and must be left alone."""
    _write_page(path, [
        (72, 72, "Form 1099-OID  Original Issue Discount   2025"),
        (72, 100, f"Recipient's name {FAKE_NAME}"),
        (72, 118, f"Recipient's TIN {FAKE_SSN}"),
        (72, 146, "FATCA filing requirement" + (" [X]" if fatca else "")),
        (72, 174, "1 Original issue discount for the year 1,000.00"),
        (72, 192, f"2 Other periodic interest {box2}".rstrip()),
        (72, 210, "3 Early withdrawal penalty 100.00"),
        (72, 228, "4 Federal income tax withheld 240.00"),
        (72, 246, "5 Market discount 200.00"),
        (72, 264, "6 Acquisition premium 300.00"),
        (72, 282, "7 Description SYNTHETIC BOND 5% 2030"),
        (72, 300, "8 Original issue discount on U.S. Treasury obligations 400.00"),
        (72, 318, "9 Investment expenses 25.00"),
        (72, 336, "10 Bond premium 60.00"),
        (72, 354, f"11 Tax-exempt OID {box11}".rstrip()),
    ])
    return path


def make_k1(path: Path) -> Path:
    _write_page(path, [
        (72, 72, "Schedule K-1 (Form 1065)   2025"),
        (72, 110, f"Partner's name {FAKE_NAME}"),
        (72, 128, f"Partner's SSN {FAKE_SSN}"),
        (72, 146, f"A Partnership's EIN {PARTNERSHIP_EIN}"),
        (72, 182, "1 Ordinary business income 12,000.00"),
    ])
    return path


def make_encrypted_w2(path: Path, password: str) -> Path:
    """A W-2 saved with password encryption, for the decrypt path."""
    from pypdf import PdfReader, PdfWriter
    tmp = path.with_suffix(".plain.pdf")
    make_w2(tmp)
    writer = PdfWriter(clone_from=PdfReader(str(tmp)))
    writer.encrypt(user_password=password, owner_password=password, algorithm="AES-256")
    with open(path, "wb") as fh:
        writer.write(fh)
    tmp.unlink()
    return path


def make_scanned_blank(path: Path) -> Path:
    """A page with no text layer (image-only-ish): no text => UNKNOWN without OCR."""
    c = _rl_canvas.Canvas(str(path), pagesize=(_PAGE_W, _PAGE_H), invariant=1)
    c.showPage()  # empty, no text
    c.save()
    return path


if __name__ == "__main__":
    out = Path("sample_docs")
    out.mkdir(exist_ok=True)
    make_w2(out / "w2_sample.pdf")
    make_1099int(out / "1099int_sample.pdf")
    make_k1(out / "k1_sample.pdf")
    # Form 1099-OID, box 2 left blank: the sample then asks nothing (its one question — is the
    # box 2 interest tax-exempt? — is reached only beside an amount in box 2).
    make_1099oid(out / "1099oid_sample.pdf", box2="")
    # Form 1099-B with a wash sale: the page reads box 1g and asks 1d, 1e, box 2 and box 3.
    make_1099b(out / "1099b_sample.pdf", wash_sale="1,500.00")
    print(f"wrote synthetic fixtures to {out}/")
