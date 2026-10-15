# SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
# Copyright (c) 2026 TRIPLE J AI LLC
# Contains original software from the ytax project.
# See the release-root LICENSING.md for scope and separate licensing options.

"""The application's library, all of it running on the person's own computer.

`project_case` keeps identity out of the fact set the engine computes on; `merge_identity` puts it
back when the forms are filled. `run_gap_loop` drives a case: it resends the complete fact set each
round to the in-process service (`transport.local_sender`), and stops on a bound it can observe.
"""
from . import identity_file
from .case import CaseFile, CaseRefused
from .documents import DocumentsRefused, read_extractions, w2s_from
from .interview import Question, completeness_prompt, open_questions
from .loop import GapLoopResult, LoopRefused, OUTCOMES, run_gap_loop
from .transport import TransportRefused, local_sender
from .merge import IdentityMergeRefused, VOCABULARY, identity_index, merge_identity
from .payload import PayloadRefused, project_case

__all__ = ["PayloadRefused", "project_case",
           "IdentityMergeRefused", "VOCABULARY", "identity_index", "merge_identity",
           "GapLoopResult", "LoopRefused", "OUTCOMES", "run_gap_loop",
           "TransportRefused", "local_sender",
           "DocumentsRefused", "read_extractions", "w2s_from",
           "Question", "completeness_prompt", "open_questions",
           "CaseFile", "CaseRefused", "identity_file"]
