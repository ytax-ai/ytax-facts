# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""Decryption and password handling, kept isolated from the rest of the pipeline.

Passwords are accepted in-memory only: never written to disk, never logged,
never placed in the IR or the report. The rest of the pipeline only ever sees
already-decrypted bytes.

pypdf (BSD-3-Clause) replaces pikepdf (MPL-2.0). AES-encrypted inputs
are handled via pypdf's `cryptography` provider (Apache-2.0/BSD dual).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pypdf import PasswordType, PdfReader, PdfWriter
from pypdf.errors import FileNotDecryptedError, WrongPasswordError


class DecryptError(Exception):
    pass


class WrongPassword(DecryptError):
    pass


class CorruptFile(DecryptError):
    pass


def is_encrypted(path: Path) -> bool:
    try:
        return bool(PdfReader(str(path)).is_encrypted)
    except Exception:
        # Could not even probe; treat as not-encrypted and let later steps fail
        # with a clearer error.
        return False


def decrypt_to(path: Path, out_path: Path, password: Optional[str]) -> None:
    """Open `path` (optionally with `password`) and write a decrypted copy.

    Raises WrongPassword if the password is rejected, CorruptFile otherwise.
    """
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            if reader.decrypt(password or "") == PasswordType.NOT_DECRYPTED:
                raise WrongPassword(f"password rejected for {path.name}")
        writer = PdfWriter(clone_from=reader)
        with open(out_path, "wb") as fh:
            writer.write(fh)
    except WrongPassword:
        raise
    except (WrongPasswordError, FileNotDecryptedError) as e:
        raise WrongPassword(f"password rejected for {path.name}") from e
    except Exception as e:  # noqa: BLE001 - normalize to a domain error
        raise CorruptFile(f"could not open {path.name}: {e}") from e
