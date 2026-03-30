import tkinter.filedialog as fd
from PIL import Image
import base64
import io
import os
import zipfile
import xml.etree.ElementTree as ET

TEXT_EXTENSIONS = {
    '.txt', '.md', '.log', '.text', '.csv', '.json', '.xml', '.yaml', '.yml',
    '.ini', '.conf', '.cfg', '.toml', '.sh', '.bash', '.py', '.js', '.ts',
    '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php',
    '.html', '.css', '.jsx', '.tsx', '.vue', '.sql', '.r', '.pl', '.lua',
    '.swift', '.kt', '.dart', '.scala', '.ex', '.exs', '.clj', '.hs', '.ml',
    '.tex', '.rst', '.adoc', '.org', '.rtf'
}


def _extract_docx_text(path):
    try:
        with zipfile.ZipFile(path) as docx:
            with docx.open("word/document.xml") as xml_file:
                root = ET.parse(xml_file).getroot()
        text_chunks = []
        for node in root.iter():
            if node.tag.endswith("}t") and node.text:
                text_chunks.append(node.text)
            elif node.tag.endswith("}p"):
                text_chunks.append("\n")
        return "".join(text_chunks).strip()
    except Exception:
        return None

def select_files():
    files = fd.askopenfilenames()
    processed = []
    for f in files:
        lower = f.lower()
        ext = os.path.splitext(lower)[1]
        if lower.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
            img = Image.open(f)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            processed.append(img_str)
        elif ext == '.docx':
            text = _extract_docx_text(f)
            processed.append(text if text else "[Unreadable .docx document]")
        elif ext in TEXT_EXTENSIONS:
            with open(f, "r", encoding="utf-8", errors="ignore") as txt:
                processed.append(txt.read())
        else:
            processed.append(f"[Unsupported attachment type: {os.path.basename(f)}]")
    return processed or None
