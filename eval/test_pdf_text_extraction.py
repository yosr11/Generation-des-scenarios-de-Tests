from pathlib import Path
import sys

import pdfplumber


def read_pdf_text(pdf_path: Path) -> str:
    pages = []
    with pdfplumber.open(pdf_path) as doc:
        for index, page in enumerate(doc.pages, start=1):
            content = page.extract_text()
            if not content:
                continue
            cleaned = content.replace("\r\n", "\n").strip()
            if cleaned:
                pages.append(f"--- Page {index} ---\n{cleaned}")
    return "\n\n".join(pages)


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file.pdf>")
        raise SystemExit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    print(read_pdf_text(path))


if __name__ == "__main__":
    main()
