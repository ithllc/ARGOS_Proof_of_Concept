import io
import requests
from typing import Optional
from PyPDF2 import PdfReader


def download_pdf(url: str) -> Optional[bytes]:
	"""Try to download pdf from a URL. Returns bytes or None."""
	try:
		resp = requests.get(url, timeout=15)
		resp.raise_for_status()
		content_type = resp.headers.get("Content-Type", "")
		if "pdf" in content_type or url.endswith(".pdf"):
			return resp.content
	except Exception:
		return None
	return None


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
	"""Extract plain text from PDF bytes using PyPDF2. For POC we use a simple approach."""
	with io.BytesIO(pdf_bytes) as fh:
		reader = PdfReader(fh)
		text_parts = []
		for page in reader.pages:
			try:
				text_parts.append(page.extract_text() or "")
			except Exception:
				continue
		return "\n\n".join(text_parts)


def extract_text_from_url(url: str) -> Optional[str]:
	from typing import List, Optional
	import os
	import io
	import requests
	from urllib.parse import urlparse
	from PyPDF2 import PdfReader

	def extract_text_from_url(url: str) -> Optional[str]:
	    """Very small PDF/HTML extractor for POC.

	    - If the URL begins with file://, read local file
	    - If the URL is HTTP(S), try to download and parse PDF (or return page text)
	    """
	    if not url:
	        return None

	    parsed = urlparse(url)
	    try:
	        if parsed.scheme == "file":
	            path = parsed.path
	            if os.path.exists(path):
	                if path.lower().endswith(".pdf"):
	                    reader = PdfReader(path)
	                    text = "\n".join([p.extract_text() or "" for p in reader.pages])
	                    return text
	                else:
	                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
	                        return f.read()

	        if parsed.scheme in ("http", "https"):
	            r = requests.get(url, timeout=10)
	            ctype = r.headers.get("Content-Type", "")
	            if "pdf" in ctype or url.lower().endswith(".pdf"):
	                reader = PdfReader(io.BytesIO(r.content))
	                text = "\n".join([p.extract_text() or "" for p in reader.pages])
	                return text
	            else:
	                # Return HTML as text fallback
	                return r.text
	    except Exception:
	        return None
	    return None

