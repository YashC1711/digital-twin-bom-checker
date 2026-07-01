import os as custom_os
import openpyxl
import ast

print2log("===== NODE 5: Write to Excel =====")

def write_data_to_excel(xlsx_path, data_dict, sheet_name_hint, header_row=2, data_row=4):
    """
    Opens the workbook, builds a header(text)->column_index map from header_row,
    writes data_dict values into data_row, saves the file.
    """
    if not xlsx_path or not custom_os.path.isfile(xlsx_path):
        print2log(f"ERROR: Excel path not found, skipping write: {xlsx_path}")
        return False
    if not data_dict:
        print2log(f"WARNING: No data to write for '{xlsx_path}' — skipping write.")
        return False
    try:
        wb = openpyxl.load_workbook(xlsx_path)
    except Exception as e:
        print2log(f"ERROR: Could not open workbook '{xlsx_path}': {e}")
        return False

    ws = wb.worksheets[0]  # first sheet, as per sample structure
    print2log(f"Opened sheet '{ws.title}' in '{custom_os.path.basename(xlsx_path)}'")

    # Build header text -> column index map (normalize whitespace + case)
    header_map = {}
    for col in range(1, ws.max_column + 1):
        cell_val = ws.cell(row=header_row, column=col).value
        if cell_val:
            key = " ".join(str(cell_val).strip().split()).lower()
            header_map[key] = col

    written = 0
    not_matched = 0
    for header_label, value in data_dict.items():
        key = " ".join(str(header_label).strip().split()).lower()
        col_idx = header_map.get(key)
        if col_idx:
            ws.cell(row=data_row, column=col_idx, value=value)
            written += 1
        else:
            print2log(f"  WARNING: No matching Excel column found for field '{header_label}' — value '{value}' not written.")
            not_matched += 1

    try:
        wb.save(xlsx_path)
        print2log(f"SUCCESS: Wrote {written} field(s) to '{custom_os.path.basename(xlsx_path)}' "
                   f"({not_matched} unmatched). Saved at row {data_row}.")
        return True
    except Exception as e:
        print2log(f"ERROR: Could not save workbook '{xlsx_path}': {e}")
        return False


# ── Rubiscape entry point ─────────────────────────────────────────────────────
# Predecessor task's output is available as 'inputData' (Dictionary),
# keyed by the predecessor task's NAME, with a DataFrame as the value.

print2log(f"inputData keys: {list(inputData.keys())}")

df = inputData.get("Parse_Pump_Data_PDS")   # <-- exact Node 4 task name from the canvas
if df is None or len(df) == 0:
    print2log("ERROR: No data received from Node 4 (Parse_Pump_Data_PDS)")
    raise Exception("NODE 5: missing input DataFrame from predecessor task")

row = df.iloc[0]   # single-row DataFrame threaded through Nodes 1 → 2 → 3 → 4

motor_xlsx_path = row.get("motor_xlsx_path")
pump_xlsx_path  = row.get("pump_xlsx_path")
motor_data       = row.get("motor_data")
pump_data        = row.get("pump_data")

# Safety: if motor_data / pump_data were serialized to string on the CSV export
# round-trip, parse them back into dicts.
if isinstance(motor_data, str):
    try:
        motor_data = ast.literal_eval(motor_data)
    except Exception:
        print2log("WARNING: Could not parse motor_data string back into dict")
        motor_data = {}

if isinstance(pump_data, str):
    try:
        pump_data = ast.literal_eval(pump_data)
    except Exception:
        print2log("WARNING: Could not parse pump_data string back into dict")
        pump_data = {}

motor_status = write_data_to_excel(motor_xlsx_path, motor_data, "motor")
pump_status  = write_data_to_excel(pump_xlsx_path, pump_data, "pump")

print2log(f"Motor excel write status: {motor_status}")
print2log(f"Pump excel write status: {pump_status}")
print2log("===== NODE 5 COMPLETE — PIPELINE FINISHED =====")

# ── Build final DataFrame output ──────────────────────────────────────────────
output_df = df.copy()
output_df["motor_write_status"] = motor_status
output_df["pump_write_status"]  = pump_status

return output_df