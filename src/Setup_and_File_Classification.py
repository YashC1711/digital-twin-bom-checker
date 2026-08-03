import os as custom_os
import re
import pandas as pd
# ── Rubiscape entry point ─────────────────────────────────────────────────────
input_path  = getVariable(@@input_path@@)
output_path = getVariable(@@output_path@@)
print2log("===== NODE 1: Setup & Classification (FIXED) =====")
print2log(f"Input path : {input_path}")
print2log(f"Output path: {output_path}")
if not input_path or not custom_os.path.isdir(input_path):
    print2log(f"ERROR: Input path invalid or not found: {input_path}")
    raise Exception(f"Invalid input path: {input_path}")
if not output_path or not custom_os.path.isdir(output_path):
    print2log(f"ERROR: Output path invalid or not found: {output_path}")
    raise Exception(f"Invalid output path: {output_path}")
# ── Classify input PDFs ──────────────────────────────────────────────────────
pdf_files = [f for f in custom_os.listdir(input_path) if f.lower().endswith(".pdf") and not f.startswith("~$")]
print2log(f"Found {len(pdf_files)} PDF file(s) in input path: {pdf_files}")
motor_pdf_path = None
pump_pdf_path  = None
for f in pdf_files:
    upper_name = f.upper()
    full_path  = custom_os.path.join(input_path, f)
    if "MDS" in upper_name:
        motor_pdf_path = full_path
        print2log(f"Identified MOTOR datasheet (MDS): {f}")
    elif "PDS" in upper_name:
        pump_pdf_path = full_path
        print2log(f"Identified PUMP datasheet (PDS): {f}")
    else:
        print2log(f"WARNING: Could not classify file '{f}' (no MDS/PDS in name) - skipped")
if not motor_pdf_path:
    print2log("WARNING: No Motor Datasheet (MDS) PDF found in input path.")
if not pump_pdf_path:
    print2log("WARNING: No Pump Datasheet (PDS) PDF found in input path.")
# ── Classify output Excel files ──────────────────────────────────────────────
# ── FIXED: "and not f.startswith('~$')" added below. Without this, Microsoft
# Office lock/temp files (created while the real .xlsx is open in Excel, or
# left behind after a crash — e.g. "~$EA001-Motor.xlsx") still end in
# ".xlsx" and were passing the old filter. Since the lock filename also
# contains "motor", it would get classified as motor_xlsx_path instead of
# (or ahead of) the real "EA001-Motor.xlsx" — causing Node 5's openpyxl
# .load_workbook() to fail downstream with "File is not a zip file", because
# a lock file isn't a real xlsx/zip archive at all.
xlsx_files = [f for f in custom_os.listdir(output_path) if f.lower().endswith(".xlsx") and not f.startswith("~$")]
print2log(f"Found {len(xlsx_files)} Excel file(s) in output path: {xlsx_files}")
motor_xlsx_path = None
pump_xlsx_path  = None
for f in xlsx_files:
    lower_name = f.lower()
    full_path  = custom_os.path.join(output_path, f)
    if "pump" in lower_name:
        pump_xlsx_path = full_path
        print2log(f"Identified PUMP excel: {f}")
    elif "motor" in lower_name:
        motor_xlsx_path = full_path
        print2log(f"Identified MOTOR excel: {f}")
    else:
        print2log(f"WARNING: Could not classify excel file '{f}' (no pump/motor in name) - skipped")
if not motor_xlsx_path:
    print2log("ERROR: No Motor excel file found (filename must contain 'motor').")
if not pump_xlsx_path:
    print2log("ERROR: No Pump excel file found (filename must contain 'pump').")
# ── Summary ───────────────────────────────────────────────────────────────────
print2log(f"\n{'='*60}")
print2log(f"Motor PDF  : {motor_pdf_path}")
print2log(f"Pump PDF   : {pump_pdf_path}")
print2log(f"Motor Excel: {motor_xlsx_path}")
print2log(f"Pump Excel : {pump_xlsx_path}")
print2log(f"{'='*60}\n")
print2log("===== NODE 1 COMPLETE =====")
# ── Build dictionary output for Rubiscape Custom Output Variables ────────────
output = {
    "motor_pdf_path":  motor_pdf_path,
    "pump_pdf_path":   pump_pdf_path,
    "motor_xlsx_path": motor_xlsx_path,
    "pump_xlsx_path":  pump_xlsx_path,
}
return pd.DataFrame([output])
