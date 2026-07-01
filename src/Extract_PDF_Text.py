import os as custom_os
import re
import pandas as pd
from PyPDF2 import PdfReader

print2log("===== NODE 2: PDF Text Extraction =====")

# ── Helper: extract text from a PDF ──────────────────────────────────────────

def extract_pdf_text(pdf_path):
    """Extracts and concatenates text from all pages of a PDF using PyPDF2."""
    if not pdf_path or not custom_os.path.isfile(pdf_path):
        print2log(f"ERROR: PDF path not found: {pdf_path}")
        return ""
    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
            except Exception as pe:
                print2log(f"WARNING: Failed extracting text from page {i+1} of {pdf_path}: {pe}")
                page_text = ""
            full_text += "\n" + page_text
        print2log(f"Extracted {len(full_text)} characters from {custom_os.path.basename(pdf_path)} ({len(reader.pages)} pages)")
        return full_text
    except Exception as e:
        print2log(f"ERROR: Could not read PDF '{pdf_path}': {e}")
        return ""


def find_value(text, patterns, field_name, flags=re.IGNORECASE):
    """
    Tries a list of regex patterns (in priority order) against text.
    Returns first non-empty captured group(1), else None.
    Logs whichever pattern succeeded or that none matched.
    """
    for pat in patterns:
        try:
            m = re.search(pat, text, flags)
            if m and m.group(1) and m.group(1).strip():
                val = m.group(1).strip()
                print2log(f"  [FOUND] {field_name} = '{val}'")
                return val
        except Exception as e:
            print2log(f"  WARNING: regex error for field '{field_name}' pattern '{pat}': {e}")
    print2log(f"  [NOT FOUND] {field_name}")
    return None


# ── Rubiscape entry point ─────────────────────────────────────────────────────
# Predecessor task's output is available as 'inputData' (Dictionary),
# keyed by the predecessor task's NAME, with a DataFrame as the value.

print2log(f"inputData keys: {list(inputData.keys())}")

df = inputData.get("Setup_and_File_Classification")   # <-- use the EXACT task name from the canvas
if df is None or len(df) == 0:
    print2log("ERROR: No data received from Node 1 (Setup_and_File_Classification)")
    raise Exception("NODE 2: missing input DataFrame from predecessor task")

row = df.iloc[0]   # Node 1 returns a single-row DataFrame

motor_pdf_path = row.get("motor_pdf_path")
pump_pdf_path  = row.get("pump_pdf_path")

print2log(f"Motor PDF path: {motor_pdf_path}")
print2log(f"Pump PDF path : {pump_pdf_path}")

motor_pdf_text = extract_pdf_text(motor_pdf_path) if motor_pdf_path else ""
pump_pdf_text  = extract_pdf_text(pump_pdf_path) if pump_pdf_path else ""

print2log("===== NODE 2 COMPLETE =====")

# ── Build DataFrame output for next node (carry forward + add new columns) ───
output_df = df.copy()
output_df["motor_pdf_text"] = motor_pdf_text
output_df["pump_pdf_text"]  = pump_pdf_text

return pd.DataFrame(output_df)