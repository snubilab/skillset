#!/usr/bin/env python3
"""Remove DrawingML locks that prevent editing exported PowerPoint shapes."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


LOCK_NAMES = (
    b"noGrp|noUngrp|noSelect|noRot|noChangeAspect|noMove|noResize|"
    b"noEditPoints|noAdjustHandles|noChangeArrowheads|noChangeShapeType|noTextEdit"
)
EDIT_LOCK = re.compile(rb'\s+(?:' + LOCK_NAMES + rb')="1"')


def prepare(pptx_path: Path) -> None:
    with ZipFile(pptx_path) as source, tempfile.NamedTemporaryFile(
        dir=pptx_path.parent, suffix=".pptx", delete=False
    ) as temp:
        temp_path = Path(temp.name)
        with ZipFile(temp, "w", ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename.startswith("ppt/slides/") and info.filename.endswith(".xml"):
                    data = EDIT_LOCK.sub(b"", data)
                target.writestr(info, data)
    os.replace(temp_path, pptx_path)

    with ZipFile(pptx_path) as result:
        assert all(
            EDIT_LOCK.search(result.read(name)) is None
            for name in result.namelist()
            if name.startswith("ppt/slides/") and name.endswith(".xml")
        )


if __name__ == "__main__":
    prepare(Path(sys.argv[1]).resolve())
