from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader



# =========================
# 读取 TXT
# =========================

def extract_txt(file_path: Path) -> str:


    try:

        return file_path.read_text(
            encoding="utf-8"
        )


    except UnicodeDecodeError:

        return file_path.read_text(
            encoding="gbk",
            errors="ignore"
        )



# =========================
# 读取 DOCX
# =========================

def extract_docx(file_path: Path) -> str:


    document = DocxDocument(
        str(file_path)
    )


    paragraphs = []


    for paragraph in document.paragraphs:


        text = paragraph.text.strip()


        if text:

            paragraphs.append(text)


    return "\n".join(paragraphs)



# =========================
# 读取 PDF
# =========================

def extract_pdf(file_path: Path) -> str:


    reader = PdfReader(
        str(file_path)
    )


    pages = []


    for page in reader.pages:


        text = page.extract_text() or ""


        if text.strip():

            pages.append(
                text.strip()
            )


    return "\n".join(pages)



# =========================
# 根据类型选择解析器
# =========================

def extract_document_text(

    file_path: str | Path,

    file_type: str

) -> str:


    path = Path(file_path)


    if not path.exists():

        raise FileNotFoundError(
            f"文件不存在：{path}"
        )


    normalized_type = (
        file_type
        .lower()
        .lstrip(".")
    )


    if normalized_type == "txt":

        return extract_txt(path)


    if normalized_type == "docx":

        return extract_docx(path)


    if normalized_type == "pdf":

        return extract_pdf(path)


    raise ValueError(
        f"暂不支持此文件类型：{normalized_type}"
    )