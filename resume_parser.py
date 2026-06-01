"""
services/resume_parser.py
Extracts plain text from an uploaded PDF resume using PyPDF2.
"""

import logging
from typing import Optional

import PyPDF2

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Open a PDF file at *file_path* and return all of its text content
    as a single string.

    Args:
        file_path: Absolute or relative path to the PDF file on disk.

    Returns:
        A string containing the concatenated text of every page in the PDF.

    Raises:
        FileNotFoundError: If *file_path* does not exist.
        ValueError: If the PDF has no extractable text (e.g. scanned image only).
        RuntimeError: If PyPDF2 raises an unexpected error during reading.
    """
    try:
        with open(file_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)

            if len(reader.pages) == 0:
                raise ValueError("The uploaded PDF contains no pages.")

            extracted_pages: list[str] = []
            for page_number, page in enumerate(reader.pages, start=1):
                try:
                    page_text: Optional[str] = page.extract_text()
                    if page_text:
                        extracted_pages.append(page_text)
                    else:
                        logger.warning(
                            "Page %d returned no text — it may be an image-only page.",
                            page_number,
                        )
                except Exception as page_error:  # noqa: BLE001
                    logger.warning(
                        "Could not extract text from page %d: %s",
                        page_number,
                        page_error,
                    )

            full_text = "\n".join(extracted_pages).strip()

            if not full_text:
                raise ValueError(
                    "No text could be extracted from the PDF. "
                    "The file may consist entirely of scanned images."
                )

            logger.info(
                "Successfully extracted %d characters from '%s'.",
                len(full_text),
                file_path,
            )
            return full_text

    except FileNotFoundError:
        logger.error("PDF file not found: %s", file_path)
        raise
    except ValueError:
        raise
    except Exception as exc:
        logger.error("Unexpected error while parsing PDF '%s': %s", file_path, exc)
        raise RuntimeError(f"Failed to parse PDF: {exc}") from exc
