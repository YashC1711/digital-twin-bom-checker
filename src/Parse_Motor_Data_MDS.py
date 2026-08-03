import re
import pandas as pd

print2log("===== NODE 3: Motor Data Parsing =====")

# ── Helper: single-value regex field extractor ─────────────────────────────
def find_value(text, patterns, field_name, flags=re.IGNORECASE):
    regex_error = False
    for pat in patterns:
        try:
            m = re.search(pat, text, flags)
            if m:
                val = m.group(1) if m.groups() else m.group(0)
                if val and val.strip():
                    val = val.strip()
                    print2log(f"  [FOUND] {field_name} = '{val}'")
                    motor_logs.append({"Field Name": field_name, "Extracted Value": val, "Status": "FOUND"})
                    return val
        except Exception as e:
            regex_error = True
            print2log(f"  WARNING: regex error for field '{field_name}' pattern '{pat}': {e}")
    print2log(f"  [NOT FOUND] {field_name}")
    motor_logs.append({"Field Name": field_name, "Extracted Value": "", "Status": "REGEX ERROR" if regex_error else "NOT FOUND"})
    return None


# ── Helper: multi-group regex extractor, joins captured groups with a separator ──
def find_value_combined(text, pattern, field_name, template, flags=re.IGNORECASE):
    try:
        m = re.search(pattern, text, flags)
        if m:
            groups = [g.strip() for g in m.groups() if g]
            if groups:
                val = template.format(*groups)
                print2log(f"  [FOUND] {field_name} = '{val}'")
                motor_logs.append({"Field Name": field_name, "Extracted Value": val, "Status": "FOUND"})
                return val
    except Exception as e:
        print2log(f"  WARNING: regex error for field '{field_name}': {e}")
    print2log(f"  [NOT FOUND] {field_name}")
    motor_logs.append({"Field Name": field_name, "Extracted Value": "", "Status": "NOT FOUND"})
    return None


# ── Rubiscape entry point ─────────────────────────────────────────────────────
print2log(f"inputData keys: {list(inputData.keys())}")

df = inputData.get("Extract_PDF_Text")
if df is None or len(df) == 0:
    print2log("ERROR: No data received from Node 2 (PDF_Text_Extraction)")
    raise Exception("NODE 3: missing input DataFrame from predecessor task")

row = df.iloc[0]

motor_pdf_text = row.get("motor_pdf_text")
motor_data = {}
motor_logs = []

# ── Load synonym patterns from Load_Motor_Field_Synonyms node ──────────────
synonyms_df = inputData.get("motor_synonyms")

synonym_patterns_by_field = {}
if synonyms_df is not None and len(synonyms_df) > 0:
    sorted_syn = synonyms_df.sort_values(["field_key", "pattern_order"])
    for field_key, group in sorted_syn.groupby("field_key"):
        synonym_patterns_by_field[field_key] = group["pattern"].tolist()
    print2log(f"Loaded synonym patterns for {len(synonym_patterns_by_field)} fields from motor_synonyms node.")
else:
    print2log("WARNING: No synonym DataFrame found — proceeding with base patterns only.")

if not motor_pdf_text:
    print2log("WARNING: No motor PDF text available — skipping motor parsing.")
else:
    t = motor_pdf_text

    MOTOR_FIELDS = {
        "Tag Name": (
            "Tag Name",
            [
                r"Client:.*?Tag No\s*[-:]?\s*([A-Z0-9\-/ ]+)",
                r"Equipment\s*No\.?\s*:?\s*([A-Z0-9\-/ ]+)",
                r"Tag\s*No\.?\s*:?\s*([A-Z0-9\-/ ]+)"
            ]
        ),
        "Serial Number": ("Serial Number", [r"(\d{6,}-\d+)-MDS"]),
        "Datasheet No": ("Datasheet No", [r"Doc\.\s*No\.\s*([A-Z0-9\- ]+?)\s*Revision No\."]),
        "Parent tag name": (
            "Parent tag name",
            [r"Tag No\.\s*(MP-PP\d+-M\d+A/B)"]
        ),
        "Manufacture": (
            "Manufacture",
            [
                r"Manufacturer:-\s*([^\n]+CG Power and Industrial Solutions Limited)",
                r"Manufacturer:-\s*([^\n]+)",
                r"Manufacturer:\s*([^\n]+)"
            ]
        ),
        "Frame Size": ("Frame Size", [r"Frame\s*Ref\.?\s*No\.?\s*:?\s*([^\n]+)"]),
        "Model Number": ("Model Number", [r"Model/Cat\.?\s*No\.?\s*:?\s*([^\n]+)"]),
        "Rated Output Power": (
            "Rated Output Power",
            [
                r"Continuous\s*Rating.*?([-+]?\d+(?:\.\d+)?)\s*kW",
                r"Rated\s*Output.*?([-+]?\d+(?:\.\d+)?)"
            ]
        ),
        "Service Factor": ("Service Factor", [r"Service\s*Factor.*?([-+]?\d+(?:\.\d+)?)"]),
        "Rated Speed": (
            "Rated Speed",
            [
                r"Speed\s*at\s*Full\s*Load.*?([-+]?\d+(?:\.\d+)?)\s*rpm",
                r"Rated\s*Speed.*?([-+]?\d+(?:\.\d+)?)"
            ]
        ),
        "Insulation Class": (
            "Insulation Class",
            [
                r"([A-Z]\s*\(Temp\.\s*rise limited to class\s*[‘'][A-Z][’']\))",
                r"Insulation\s*Class:-\s*([A-Z])"
            ]
        ),
        "Temperature Rise": (
            "Temperature Rise",
            [
                r"Temp\s*Rise.*?([-+]?\d+(?:\.\d+)?)",
                r"Max\.\s*Permitted\s*Temp\s*Rise.*?([-+]?\d+(?:\.\d+)?)",
                r"Insulation\s*Class\s*&\s*Temp\s*Rise.*?([-+]?\d+(?:\.\d+)?)"
            ]
        ),
        "Rated Voltage": ("Rated Voltage", [r"(\d{3})\s*\+-\s*10%"]),
        "Number of Electrical Phases": (
            "Number of Electrical Phases",
            [
                r"(\d)\s*Ph",
                r"Supply\s*System.*?(\d)\s*Ph"
            ]
        ),
        "Rated Frequency": (
            "Rated Frequency",
            [
                r"([-+]?\d+(?:\.\d+)?)\s*Hz",
                r"Frequency.*?([-+]?\d+(?:\.\d+)?)"
            ]
        ),
        "Rated Amp": (
            "Rated Amp",
            [
                r"Full\s*Load\s*Current.*?([-+]?\d+(?:\.\d+)?)\s*Amps?",
                r"Rated\s*Current.*?([-+]?\d+(?:\.\d+)?)"
            ]
        ),
        "Starting Current": (
            "Starting Current",
            [
                r"Starting\s*Current.*?([-+]?\d+(?:\.\d+)?)",
                r"Locked\s*rotor\s*current.*?([-+]?\d+(?:\.\d+)?)"
            ]
        ),
        "Efficiency": (
            "Efficiency",
            [
                r"Efficiency\s*\(100/75/50%\).*?([-+]?\d+(?:\.\d+)?)",
                r"Efficiency\s*IE2.*?([-+]?\d+(?:\.\d+)?)"
            ]
        ),
        "Rated Power Factor (Lagging)": (
            "Rated Power Factor (Lagging)",
            [
                r"Power\s*Factor\s*\(100/75/50%\).*?([-+]?\d+(?:\.\d+)?)",
                r"Power\s*Factor\s*\(Starting\).*?([-+]?\d+(?:\.\d+)?)"
            ]
        ),
        "Starting Torque": ("Starting Torque", [r"Starting\s*Torque.*?([-+]?\d+(?:\.\d+)?)"]),
        "Pull-Out Torque": ("Pull-Out Torque", [r"Pull[- ]*Out\s*Torque.*?([-+]?\d+(?:\.\d+)?)"]),
        "Minimum Accelerating Torque (Motor & Load) @ 80%Volts": (
            "Minimum Accelerating Torque (Motor & Load) @ 80%Volts",
            [
                r"Minimum\s*Accelerating\s*Torque.*?80%Volts.*?([-+]?\d+(?:\.\d+)?)",
                r"Minimum\s*Accelerating\s*Torque.*?([-+]?\d+(?:\.\d+)?)\s*%\s*FLT"
            ]
        ),
        "Rotor End float": ("Rotor End float", [r"Rotor\s*End\s*float.*?([-+]?\d+(?:\.\d+)?)"]),
        "Number of Starts Per Hour": (
            "Number of Starts Per Hour",
            [r"Max\.\s*No\.\s*of\s*Starts\s*in\s*1\s*Hour.*?([^\n]+)"]
        ),
        "Transportation Weight": (
            "Transportation Weight",
            [
                r"Weight\s*of\s*Motor.*?([-+]?\d+(?:\.\d+)?)\s*kg",
                r"Net\s*Weight.*?([-+]?\d+(?:\.\d+)?)"
            ]
        ),
        "Ingress Protection": (
            "Ingress Protection",
            [
                r"Degree\s*of\s*Enclosure\s*Protection.*?(IP\d+)",
                r"Enclosure.*?(IP\d+)"
            ]
        ),
        "Electric Motor Cooling Method": (
            "Electric Motor Cooling Method",
            [
                r"Insulation Class:-\s*(TEFC|TENV|TETC|TEAAC|CACA|CACW|TEWAC|WPI|WPII)",
                r"Cooling method:.*?(TEFC|TENV|TETC|TEAAC|CACA|CACW|TEWAC|WPI|WPII)"
            ]
        ),
        "Explosion Protection Concept": (
            "Explosion Protection Concept",
            [
                r"Type\s*of\s*Protection.*?([^\n]+)",
                r"Explosion\s*Protection.*?([^\n]+)"
            ]
        ),
        "Explosion Protection Temperature Class": (
            "Explosion Protection Temperature Class",
            [r"Temperature\s*Class.*?([^\n]+)"]
        ),
        "Gas Group": ("Gas Group", [r"Gas\s*Group.*?([^\n]+)"]),
        "Bearing Type DE": (
            "Bearing Type DE",
            [
                r"Make\s*&\s*Ref\s*No\.\s*\(DE\)\s*:?\s*([^\n]+)",
                r"Bearing\s*DE.*?([^\n]+)"
            ]
        ),
        "Bearing Type NDE": ("Bearing Type NDE", [r"Make\s*&\s*Ref\s*No\.\s*\(NDE\):\s*([^\n]+)"]),
        "Heating Time Constant": (
            "Heating Time Constant",
            [r"Heating\s*Time\s*Constant.*?([-+]?\d+(?:\.\d+)?)\s*min"]
        ),
        "Cooling Time Constant": (
            "Cooling Time Constant",
            [r"Cooling\s*Time\s*Constant.*?=\s*([-+]?\d+(?:\.\d+)?)"]
        ),
        "Cable Entry": (
            "Cable Entry",
            [
                r"TOP\s+(M\d+X[\d.]+P)",
                r"Heater\s*Terminal\s*Box\s*Entry\s*:?\s*([^\n]+)",
                r"Terminal\s*Box\s*Entry\s*:?\s*([^\n]+)"
            ]
        ),
        "Winding Connection": (
            "Winding Connection",
            [
                r"Winding\s*Connection.*?(Star|Delta)",
                r"Delta",
                r"Star"
            ]
        ),
        "Starting Method": (
            "Starting Method",
            [
                r"Method\s*of\s*Starting.*?(DOL|VFD|Soft\s*starter)",
                r"Direct\s*On\s*Line",
                r"DOL"
            ]
        ),
        "Shaft Orientation": (
            "Shaft Orientation",
            [
                r"Shaft\s*Orientation.*?(Horizontal|Vertical)",
                r"Horizontal",
                r"Vertical"
            ]
        ),
        "Mounting Arrangement": (
            "Mounting Arrangement",
            [
                r"Mounting.*?(B3|B5|V1|V3|Foot|Flange)",
                r"Mounting.*?([^\n]+)"
            ]
        ),
        "Direction of Rotation": (
            "Direction of Rotation",
            [
                r"Direction of Rotation.*?(Bi-Dir)",
                r"(Bidirectional)"
            ]
        ),
        "Duty": (
            "Duty",
            [
                r"Duty:-\s*(S1).*?Continuous",
                r"Duty.*?([^\n]+)"
            ]
        ),
        "Driver Enclosure": (
            "Driver Enclosure",
            [
                r"Degree\s*of\s*Enclosure\s*Protection.*?(IP\d+)",
                r"Type\s*of\s*Protection.*?(IP\d+)"
            ]
        ),
        "Exciter Output Current": ("Exciter Output Current", [r"Exciter\s*Output\s*Current.*?([^\n]+)"]),
        "Exciter Output Voltage": ("Exciter Output Voltage", [r"Exciter\s*Output\s*Voltage.*?([^\n]+)"]),
        "Excitor Amp": ("Excitor Amp", [r"Excitor\s*Amp.*?([^\n]+)"]),
        "Excitor Voltage": ("Excitor Voltage", [r"Excitor\s*Voltage.*?([^\n]+)"]),
    }

    # ── Merge synonym patterns: extend existing fields, add missing ones ────
    added_count = 0
    merged_count = 0
    for field_key, syn_patterns in synonym_patterns_by_field.items():
        if field_key in MOTOR_FIELDS:
            header, existing_patterns = MOTOR_FIELDS[field_key]
            new_patterns = existing_patterns + [p for p in syn_patterns if p not in existing_patterns]
            MOTOR_FIELDS[field_key] = (header, new_patterns)
            merged_count += 1
        else:
            MOTOR_FIELDS[field_key] = (field_key, syn_patterns)
            added_count += 1

    print2log(f"Merged synonym patterns into {merged_count} existing fields; "
              f"added {added_count} new fields from synonyms.")

    print2log(f"Parsing {len(MOTOR_FIELDS)} candidate fields from motor PDF...")
    for field_key, (header, patterns) in MOTOR_FIELDS.items():
        val = find_value(t, patterns, field_key)
        if val:
            motor_data[header] = val

    # ── Post-processing: strip stray internal space in Datasheet No ────────
    if "Datasheet No" in motor_data:
        motor_data["Datasheet No"] = motor_data["Datasheet No"].replace(" ", "")

    # ── Combined / multi-part fields ────────────────────────────────────────
    combined_specs = [
        ("Rotor Resistance (Ac) @ 20°C", r"Rotor\s*Resistance.*?=\s*([\d.]+)\s*/\s*([\d.]+)", "{} / {}"),
        ("Rotor Reactance @ 20°C", r"Rotor\s*Reactance.*?=\s*([\d.]+)\s*/\s*([\d.]+)", "{} / {}"),
        ("Stator Resistance (AC) @ 20°C", r"Stator\s*Resistance.*?=\s*([\d.]+)\s*/\s*([\d.]+)", "{} / {}"),
        ("Stator Reactance @ 20°C", r"Stator\s*Reactance.*?=\s*([\d.]+)\s*/\s*([\d.]+)", "{} / {}"),
    ]
    for field_name, pattern, template in combined_specs:
        val = find_value_combined(t, pattern, field_name, template)
        if val:
            motor_data[field_name] = val

    val = find_value_combined(
        t,
        r"Motor:-\s*(\dR)\*(\dC),(\d+)sqmm",
        "Size Power Cable",
        "{} x {} x {}"
    )
    if val:
        motor_data["Size Power Cable"] = val

    val = find_value_combined(
        t,
        r"MAX:-\s*([\d.]+)°C.*?MIN:-\s*([\d.]+)°C.*?DESIGN:-\s*([\d.]+)°C",
        "Temperature Ambient",
        "Max {} / Min {} / Design {}"
    )
    if val:
        motor_data["Temperature Ambient"] = val

    # Size Control Cable needs 2 capture groups combined into "2C x 2.5"
    # format — motor_synonyms.py's pattern is present but find_value only
    # reads group(1), so this override guarantees the full combined string.
    val = find_value_combined(
        t,
        r"Heater:-\s*(\d)CX([\d.]+)Sq",
        "Size Control Cable",
        "{}C x {}"
    )
    if val:
        motor_data["Size Control Cable"] = val

    run_up_idx = t.find("Run-Up Time")
    if run_up_idx != -1:
        locked_rotor_text = t[:run_up_idx]
        run_up_text = t[run_up_idx:]
    else:
        locked_rotor_text = t
        run_up_text = t

    time_fields = [
        ("Locked Rotor Withstand Time (100% Volts) Hot & Cold", locked_rotor_text, r"100%\s*Volts.*?Hot.*?([\d.]+)\s*secs.*?Cold.*?([\d.]+)\s*secs"),
        ("Locked Rotor Withstand Time (80% Volts) Hot & Cold", locked_rotor_text, r"80%\s*Volts.*?Hot.*?([\d.]+)\s*secs.*?Cold.*?([\d.]+)\s*secs"),
        ("Run-Up Time (Motor & Load) (100% Volts) Hot & Cold", run_up_text, r"100%\s*Volts.*?Hot.*?([\d.]+)\s*secs.*?Cold.*?([\d.]+)\s*secs"),
        ("Run-Up Time (Motor & Load) (80% Volts) Hot & Cold", run_up_text, r"80%\s*Volts.*?Hot.*?([\d.]+)\s*secs.*?Cold.*?([\d.]+)\s*secs"),
    ]
    for field_name, scoped_text, pattern in time_fields:
        val = find_value_combined(scoped_text, pattern, field_name, "Hot: {} / Cold: {}")
        if val:
            motor_data[field_name] = val

    type_m = re.search(r"grease type\s*([A-Z0-9\-]+)", t, re.IGNORECASE)
    qty_m = re.search(r"grease qty,?\s*(\d+)\s*gram", t, re.IGNORECASE)
    interval_m = re.search(r"grease interval,?\s*(\d+)\s*Hrs", t, re.IGNORECASE)
    has_grease = re.search(r"Grease", t, re.IGNORECASE) is not None

    if has_grease and type_m and qty_m and interval_m:
        val = f"Grease; {type_m.group(1)}; grease qty {qty_m.group(1)} gram; interval {interval_m.group(1)} Hrs"
        print2log(f"  [FOUND] Electric Motor Bearing Lubrication = '{val}'")
        motor_data["Electric Motor Bearing Lubrication"] = val
        motor_logs.append({"Field Name": "Electric Motor Bearing Lubrication", "Extracted Value": val, "Status": "FOUND"})
    else:
        print2log("  [NOT FOUND] Electric Motor Bearing Lubrication")
        motor_logs.append({"Field Name": "Electric Motor Bearing Lubrication", "Extracted Value": "", "Status": "NOT FOUND"})

    print2log(f"Total motor fields successfully extracted: {len(motor_data)} / {len(MOTOR_FIELDS)}")

print2log("===== NODE 3 COMPLETE =====")

output_df = df.copy()
output_df["motor_data"] = [motor_data]
output_df["motor_logs"] = [motor_logs]

return output_df
