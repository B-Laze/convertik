from io import BytesIO
from pypdf import PdfReader, PdfWriter


def parse_page_range(range_str: str, total_pages: int) -> list[int]:
    pages = set()
    parts = range_str.replace(" ", "").split(",")
    for part in parts:
        if "-" in part:
            start, end = part.split("-")
            start_idx = max(1, int(start))
            end_idx = min(total_pages, int(end))
            for p in range(start_idx, end_idx + 1):
                pages.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= total_pages:
                pages.add(p - 1)
    return sorted(list(pages))


def extract_pdf_pages(input_pdf_bytes: bytes, page_range_str: str) -> bytes:
    reader = PdfReader(BytesIO(input_pdf_bytes))
    writer = PdfWriter()

    selected_indices = parse_page_range(page_range_str, len(reader.pages))

    for idx in selected_indices:
        writer.add_page(reader.pages[idx])

    output_stream = BytesIO()
    writer.write(output_stream)
    return output_stream.getvalue()


def merge_pdfs(pdf_bytes_list: list[bytes]) -> bytes:
    writer = PdfWriter()

    for pdf_bytes in pdf_bytes_list:
        reader = PdfReader(BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    output_stream = BytesIO()
    writer.write(output_stream)
    return output_stream.getvalue()


def rotate_pdf_pages(input_pdf_bytes: bytes, degrees: int, page_range_str: str = "all") -> bytes:
    reader = PdfReader(BytesIO(input_pdf_bytes))
    writer = PdfWriter()
    total_pages = len(reader.pages)

    target_indices = (
        list(range(total_pages))
        if page_range_str.lower() == "all"
        else parse_page_range(page_range_str, total_pages)
    )

    for idx, page in enumerate(reader.pages):
        if idx in target_indices:
            page.rotate(degrees)
        writer.add_page(page)

    output_stream = BytesIO()
    writer.write(output_stream)
    return output_stream.getvalue()