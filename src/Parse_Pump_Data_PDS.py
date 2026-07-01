import re
import pandas as pd

print2log("===== NODE 4: Pump Data Parsing =====")

# ── Helper: regex field extractor (redefined here since each node runs isolated) ──

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

# <-- use the EXACT Node 3 task name from the canvas
df = inputData.get("Parse_Motor_Data_MDS")
if df is None or len(df) == 0:
    print2log("ERROR: No data received from Node 3 (Motor_Data_Parsing)")
    raise Exception("NODE 4: missing input DataFrame from predecessor task")

row = df.iloc[0]   # single-row DataFrame threaded from Node 1 → Node 2 → Node 3

pump_pdf_text = row.get("pump_pdf_text")
pump_data = {}

if not pump_pdf_text:
    print2log("WARNING: No pump PDF text available — skipping pump parsing.")
else:
    t = pump_pdf_text

    PUMP_FIELDS = {
        "Tag Name":            ("Tag Name", [r"Item\s*\n?\s*(MP-PD\d+-P\d+[A-Z]?/?[A-Z]?)"]),
        "Manufacture":         ("Manufacture", [r"Manufacturer:\s*M/s\.?\s*([A-Z][A-Z\s.]+LTD)"]),
        "Datasheet No":        ("Datasheet No", [r"(GP3201-MPPD-PD\d+-\d+)"]),
        "Model Number":        ("Model Number", [r"Model designation\s*\n?\s*\*?\s*(MCPK[\d\-]+)"]),
        "pump type":           ("pump type", [r"Type of pump\s*(Centrifugal Horizontal Pump)"]),
        "Number of stages ":   ("Number of stages ", [r"No\. of stages\s*\n?\s*(\d+)"]),
        "Direction of Rotation, from driver end": ("Direction of Rotation, from driver end",
                                                    [r"Rotation\s*(Clockwise|Counter-?clockwise)"]),
        "CASING MOUNTING":     ("CASING MOUNTING", [r"Casing mounting.*?\n?\s*(Foot Mounted|Centreline supported)"]),
        "CASING TYPE":         ("CASING TYPE", [r"Casing type \(Volute/Diffuser\)\s*\n?\s*(Volute|Diffuser)"]),
        "Impeller type":       ("Impeller type", [r"Impeller type\s*\n?\s*(Closed|Open|Semi-open)"]),
        "Suction nozzle size": ("Suction nozzle size", [r"Suction\s*(\d+\s*\d?/?\d*\")"]),
        "Discharge Nozzle size ": ("Discharge Nozzle size ", [r"Discharge\s*(\d+\s*\d?/?\d*\")"]),
        "Discharge Nozzle Rating ": ("Discharge Nozzle Rating ", [r"Discharge\s*\d\s*\d?/?\d*\"\s*(\d+#)"]),
        "Suction Nozzle Rating ":   ("Suction Nozzle Rating ", [r"Suction\s*\d\s*\d?/?\d*\"\s*(\d+#)"]),
        "Shaft diameter @ coupling": ("Shaft diameter @ coupling", [r"Shaft diameter at coupling\s*\n?\s*(\d+)"]),
        "Bearing span":         ("Bearing span", [r"Span between bearing centers\s*\n?\s*(\d+)"]),
        "Wet Critical speed":   ("Wet Critical speed", [r"Critical speed\s*\n?\s*(\d+)\s*wet"]),
        "bearing type, DE":     ("bearing type, DE", [r"Radial bearing\s*type\s*:\s*\w+\s*size\s*:\s*([\w\s]+?)number"]),
        "bearing type, NDE":    ("bearing type, NDE", [r"Thrust bearing\s*type\s*:\s*\w+\s*size\s*:\s*([\w\s]+?)number"]),
        "Bearing lubrication":  ("Bearing lubrication", [r"Lubrication \(Forced/Ring oil/Grease\)\s*\n?\s*([\w\s]+?)(?:\n|Oil viscosity)"]),
        "operating weight":     ("operating weight", [r"Total operation weight\s*kg\s*\n?\s*(\d+)"]),
        "Baseplate weight":     ("Baseplate weight", [r"Base plate\s*\n?\s*kg\s*\n?\s*(\d+)"]),
        "Driver weight":        ("Driver weight", [r"Driver\s*\n?\s*kg\s*\n?\s*(\d+)\s*43"]),
        "dry weight":           ("dry weight", [r"Total erection weight\s*kg\s*\n?\s*([\d.]+)"]),
        "Driver Type":          ("Driver Type", [r"(Electric Motor)"]),
        "Driver Manufacturer":  ("Driver Manufacturer", [r"Manufacturer\s*\n?\s*(BBL)"]),
        "Driver Frame":         ("Driver Frame", [r"Size\s*\n?\s*(160L)"]),
        "Driver Voltage":       ("Driver Voltage", [r"Voltage\s*V\s*\n?\s*([\d\s+/\-%]+)"]),
        "Driver Frequency":     ("Driver Frequency", [r"Frequency / Phases\s*Hz\s*/\s*-\s*\n?\s*(\d+)"]),
        "Driver Phase Number":  ("Driver Phase Number", [r"3 Ph\s*\n?\s*(\d+)"]),
        "Driver Rating ":       ("Driver Rating ", [r"Nominal power\s*\n?\s*([\d.]+)\s*44"]),
        "Hydraulic Power ":     ("Hydraulic Power ", [r"Power consumption\s*kW\s*\n?\s*([\d.]+)"]),
        "Rated Efficiency":     ("Rated Efficiency", [r"Efficiency\s*%\s*\n?\s*([\d.]+)"]),
        "rated speed":          ("rated speed", [r"Speed\s*min-1\s*\n?\s*(\d+)"]),
        "Net positive suction head required": ("Net positive suction head required", [r"NPSH required.*?m\s*\n?\s*([\d.]+)"]),
        "NPSHa @ shaft centreline, rated capcity": ("NPSHa @ shaft centreline, rated capcity",
                                                     [r"NPSH available.*?m\s*\n?\s*([\d.]+)"]),
        "Capacity  Rated / Maximum": ("Capacity  Rated / Maximum", [r"Guarantee/Rated point by pump vendor Rated.*?m³/h\s*\n?\s*([\d.]+)"]),
        "Differential head @ rated flow": ("Differential head @ rated flow", [r"Differential head actual\s*m\s*\n?\s*([\d.]+)"]),
        "Discharge pressure @ rated flow": ("Discharge pressure @ rated flow", [r"Discharge pressure req\./actual\s*kg/cm2 a\s*\n?\s*([\d.]+)"]),
        "Maximum suction  pressure": ("Maximum suction  pressure", [r"Max\. suction pressure\s*kg/cm2 a\s*\n?\s*([\d.]+)"]),
        "Maximum pumping  temperature": ("Maximum pumping  temperature", [r"Max\. operating temperature\s*°C\s*\n?\s*(\d+)"]),
        "density":              ("density", [r"Note\(15\)\s*kg/m³\s*\n?\s*(\d+)"]),
        " Viscosity Maximum":   (" Viscosity Maximum", [r"Dynamic viscosity Note\(15\)\s*cP\s*\n?\s*([\d.]+)"]),
        "fluid name":           ("fluid name", [r"Name of liquid\s*\n?\s*(\w+)"]),
        "explosion protection zone": ("explosion protection zone", [r"Hazard classification / Class\s*\n?\s*(Zone\s*\d)"]),
        "explosion protection temperature class": ("explosion protection temperature class", [r"Zone \d\s*(T\d)"]),
        "explosion protection gas group": ("explosion protection gas group", [r"T\d\s*(I+[AB]\s*/\s*I+[AB])"]),
        "seal type":            ("seal type", [r"Type of sealing.*?\(Mechanical seal/packing\)\s*\n?\s*(Mechanical)"]),
        "Seal API class code":  ("Seal API class code", [r"API seal code\s*\n?\s*([\w\-/]+)"]),
        "Coupling Model":       ("Coupling Model", [r"Model designation\s*\n?\s*(RLM[\w\s()/]+CPLG)"]),
        "Coupling Type":        ("Coupling Type", [r"Type\s*\n?\s*(FLEXIBLE SPACER)"]),
        "Hydro test pressure":  ("Hydro test pressure", [r"Hydrotest Pressure.*?\n?\s*([\d.]+)\s*86"]),
        "Maximum  design pressure": ("Maximum  design pressure", [r"Design pressure req\./actual.*?kg/cm2 g\s*\n?\s*([\d.]+)"]),
        "Maximum design temperature": ("Maximum design temperature", [r"Design temperature req\./actual\s*\n?\s*\n?\s*(\d+)"]),
        "Material: Shaft":      ("Material: Shaft", [r"^06 Shaft\s+([A-Za-z0-9\s().]+?)\s*07"]),
        "MATERIAL:IMPELLER":    ("MATERIAL:IMPELLER", [r"Impeller\s+SS\s*\(([\w\s]+)\)"]),
        "Material : Casing ":   ("Material : Casing ", [r"Casing / Stuffing Box\s+CS\s*\(([\w\s]+)\)"]),
    }

    print2log(f"Parsing {len(PUMP_FIELDS)} candidate fields from pump PDF...")
    for field_key, field_def in PUMP_FIELDS.items():
        header, patterns = field_def[0], field_def[1]
        val = find_value(t, patterns, field_key)
        if val:
            pump_data[header] = val

    print2log(f"Total pump fields successfully extracted: {len(pump_data)} / {len(PUMP_FIELDS)}")

print2log("===== NODE 4 COMPLETE =====")

# ── Build DataFrame output for next node (carry forward + add new column) ───
output_df = df.copy()
output_df["pump_data"] = [pump_data]

return output_df