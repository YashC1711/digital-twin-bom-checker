import re
import pandas as pd

print2log("===== NODE 3: Motor Data Parsing =====")

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

# df = inputData.get("PDF_Text_Extraction")   # <-- use the EXACT Node 2 task name from the canvas
df = inputData.get("Extract_PDF_Text")
if df is None or len(df) == 0:
    print2log("ERROR: No data received from Node 2 (PDF_Text_Extraction)")
    raise Exception("NODE 3: missing input DataFrame from predecessor task")

row = df.iloc[0]   # single-row DataFrame threaded from Node 1 → Node 2

motor_pdf_text = row.get("motor_pdf_text")
motor_data = {}

if not motor_pdf_text:
    print2log("WARNING: No motor PDF text available — skipping motor parsing.")
else:
    t = motor_pdf_text

    # field_name -> (excel header text to match, [regex patterns])
    MOTOR_FIELDS = {
        "Tag Name":              ("Tag Name", [r"Equipment No\.?\s*:?-?\s*\n?\s*([A-Z0-9\-]+/[A-Z])",
                                                r"(MP-PD\d+-M\d+\s*[A-Z]/[A-Z])"]),
        "Manufacture":           ("Manufacture", [r"Manufacturer:-?\s*\n?\s*([A-Z][A-Z\s]+LTD)"]),
        "Datasheet No":          ("Datasheet No", [r"MOTOR DATA SHEET No\s*\n?\s*([A-Z0-9\-]+)",
                                                    r"(10080-DS-EL-45001/Rev\s*\d+)"]),
        "Frame Size":            ("Frame Size", [r"Frame Ref\. No\.:-?\s*\n?\s*(\w+)"]),
        "Model Number":          ("Model Number", [r"Model/Cat\. No\.:-?\s*\n?\s*([A-Z0-9]+)"]),
        "Rated Output Power":    ("Rated Output Power", [r"Continuous Rating:-?\s*\n?\s*([\d.]+)\s*kW"]),
        "Service Factor":        ("Service Factor", [r"Service Factor:\s*\n?\s*(\d+\.?\d*)"]),
        "Rated Speed":           ("Rated Speed", [r"Speed at Full Load:-?\s*\n?\s*([\d.]+)\s*rpm"]),
        "Insulation Class":      ("Insulation Class", [r"Insulation Class:-?\s*\n?\s*([A-Z])\s*with"]),
        "Temperature Rise":      ("Temperature Rise", [r"Temp Rise restricted to Class\s*B\s*\n?\s*(\d+)",
                                                        r"Max\. Permitted Temp Rise:-?\s*Class\s*B\s*(\d+)"]),
        "Rated Voltage":         ("Rated Voltage", [r"Supply System:\s*\n?\s*(\d+\s*±?\s*\d*%?)\s*V"]),
        "Number of Electrical Phases": ("Number of Electrical Phases", [r"V\s*\n?\s*(\d)\s*Ph"]),
        "Rated Frequency":       ("Rated Frequency", [r"(\d+)\s*±\s*\d+%\s*Hz"]),
        "Rated Amp":             ("Rated Amp", [r"Full Load Current \(FLC\):-?\s*\n?\s*([\d.]+)\s*Amps"]),
        "Starting Current":      ("Starting Current", [r"Starting Current:-?\s*\n?\s*(\d+)\s*%\s*FLC"]),
        "Efficiency":            ("Efficiency", [r"Efficiency \(100/75/50%\):-?\s*\n?\s*([\d.]+)\s*/"]),
        "Rated Power Factor (Lagging)": ("Power Factor (Starting)", [r"Power Factor \(Starting\):-?\s*\n?\s*([\d.]+)"]),
        "Starting Torque":       ("Starting Torque", [r"Starting Torque:-?\s*\n?\s*(\d+)\s*%\s*FLT"]),
        "Pull-Out Torque":       ("Pull-Out Torque", [r"Pull-Out Torque:-?\s*\n?\s*(\d+)\s*%\s*FLT"]),
        "Minimum Accelerating Torque (Motor & Load) @ 80%Volts": (
            "Minimum Accelerating Torque (Motor & Load) @ 80%Volts",
            [r"Minimum Accelerating Torque.*?@\s*80%Volts:-?\s*\n?\s*(\d+)\s*%\s*FLT"]),
        "Locked Rotor Withstand Time (100% Volts) Hot & Cold": (
            "Locked Rotor Withstand Time (100% Volts) Hot & Cold",
            [r"100% Volts:-?\s*Hot:-?\s*(\d+)\s*secs\s*Cold:-?\s*(\d+)\s*secs"]),
        "Locked Rotor Withstand Time (80% Volts) Hot & Cold": (
            "Locked Rotor Withstand Time (80% Volts) Hot & Cold",
            [r"80% Volts:-?\s*Hot:-?\s*(\d+)\s*secs\s*Cold:-?\s*(\d+)\s*secs"]),
        "Run-Up Time (Motor & Load) (100% Volts) Hot & Cold": (
            "Run-Up Time (Motor & Load) (100% Volts) Hot & Cold",
            [r"Run-Up Time.*?100% Volts:-?\s*Hot:-?\s*([\d.]+)\s*secs\s*Cold:-?\s*([\d.]+)\s*secs"]),
        "Run-Up Time (Motor & Load) (80% Volts) Hot & Cold": (
            "Run-Up Time (Motor & Load) (80% Volts) Hot & Cold",
            [r"80% Volts:-?\s*Hot:-?\s*([\d.]+)\s*secs\s*Cold:-?\s*([\d.]+)\s*secs"]),
        "Rotor Resistance (Ac) @ 20°C":  ("Rotor Resistance (Ac) @ 20°C", [r"Rotor Resistance\(ac\) @ 20°C\s*r[r1]?\s*=\s*([\d.]+)"]),
        "Rotor Reactance @ 20°C":        ("Rotor Reactance @ 20°C", [r"Rotor Reactance @ 20°C\s*X[r1]?\s*=\s*([\d.]+)"]),
        "Stator Resistance (AC) @ 20°C": ("Stator Resistance (AC) @ 20°C", [r"Stator Resistance\(ac\) @ 20°C\s*r[s1]?\s*=\s*([\d.]+)"]),
        "Stator Reactance @ 20°C":       ("Stator Reactance @ 20°C", [r"Stator Reactance @ 20°C\s*X[s1]?\s*=\s*([\d.]+)"]),
        "Stator Leakage Reactance @ 20°C": ("Stator Leakage Reactance @ 20°C", [r"Stator Leakage Reactance @ 20°C\s*X1\s*=\s*([\d.]+)"]),
        "Magnetizing Resistance @ 20°C": ("Magnetizing Resistance @ 20°C", [r"Magnetising Resistance @ 20°C\s*r[m1]?\s*=\s*([\d.]+)"]),
        "Magnetizing Reactance @ 20°C":  ("Magnetizing Reactance @ 20°C", [r"Magnetising Reactance @ 20°C\s*X[m1]?\s*=\s*([\d.]+)"]),
        "Number of Starts Per Hour":     ("Number of Starts Per Hour", [r"Max\. No\. of Starts in 1 Hour:-?\s*\n?\s*(\d+)"]),
        "Transportation Weight":         ("Transportation Weight", [r"Weight of Motor:-?\s*\n?\s*(\d+)\s*kg"]),
        "Ingress Protection":            ("Ingress Protection", [r"Degree of Enclosure Protection:-?\s*\n?\s*(IP\s*\d+)"]),
        "Electric Motor Cooling Method": ("Electric Motor Cooling Method", [r"Cooling method:.*?\n.*?(TEFC|TENV|TETC|TEAAC|CACA|CACW|TEWAC|WPI|WPII)"]),
        "Explosion Protection Concept":  ("Explosion Protection Concept", [r"Type of Protection:-?\s*\n?\s*(Ex\s*\w+)"]),
        "Explosion Protection Temperature Class": ("Explosion Protection Temperature Class", [r"Temperature Class:-?\s*\n?\s*(T\d)"]),
        "Gas Group":                     ("Gas Group", [r"Gas Group:-?\s*\n?\s*(I+[ABC])"]),
        "Bearing Type DE":               ("Bearing Type DE", [r"Make & Ref No\. \(DE\):\s*\n?\s*([\w\s/]+?)(?:\n|Make)"]),
        "Bearing Type NDE":              ("Bearing Type NDE", [r"Make & Ref No\. \(NDE\):\s*\n?\s*([\w\s/]+?)(?:\n|Lubrication)"]),
        "Electric Motor Bearing Lubrication": ("Electric Motor Bearing Lubrication", [r"Lubrication:.*?\n?\s*(Oil|Grease)"]),
        "Heating Time Constant":         ("Heating Time Constant", [r"Heating Time Constant:-?\s*\n?\s*=?\s*(\d+)\s*min"]),
        "Cooling Time Constant":         ("Cooling Time Constant", [r"Cooling Time Constant:-?\s*\n?\s*=?\s*(\d+)\s*min"]),
        "Size Power Cable":              ("Size Power Cable", [r"(\dR\s*x\s*\dC\s*x\s*\d+\s*A?SQ\.?MM)"]),
        "Cable Entry":                   ("Cable Entry", [r"(1X?\s*M\d+X[\d.]+P)"]),
        "Winding Connection":            ("Winding Connection", [r"Winding Connection:\s*\*?\s*□?\s*Star\s*■?\s*(Star|Delta)"]),
        "Starting Method":               ("Starting Method", [r"Method of Starting:\s*\*?\s*■?\s*(DOL|VFD|Soft starter)"]),
        "Shaft Orientation":             ("Shaft Orientation", [r"Shaft Orientation\s*\*?\s*■?\s*(Horizontal|Vertical)"]),
        "Mounting Arrangement":          ("Mounting Arrangement", [r"Mounting:\s*\*?\s*■?\s*(Foot|Flange)"]),
    }

    print2log(f"Parsing {len(MOTOR_FIELDS)} candidate fields from motor PDF...")
    for field_key, (header, patterns) in MOTOR_FIELDS.items():
        val = find_value(t, patterns, field_key)
        if val:
            motor_data[header] = val

    print2log(f"Total motor fields successfully extracted: {len(motor_data)} / {len(MOTOR_FIELDS)}")

print2log("===== NODE 3 COMPLETE =====")

# ── Build DataFrame output for next node (carry forward + add new column) ───
output_df = df.copy()
output_df["motor_data"] = [motor_data]   # store the dict as a single cell (object dtype)

return output_df