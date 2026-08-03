import re
import pandas as pd

print2log("===== NODE 3: Motor Data Parsing (FIXED) =====")

# ── NEW: character class matching stray checkbox glyphs from Wingdings/Symbol
# fonts that PyPDF2 extracts as literal Private-Use-Area unicode chars
# (e.g. U+F06E, U+F0A8) instead of rendering them as blank/whitespace.
# Also swallows stray semicolons/colons that sit between a label and its
# Yes/No value in checkbox-style form fields.
CHK = r"[\s\uE000-\uF8FF;:]*"

# ── NEW: fixes PyPDF2 splitting a word across a line break mid-token, e.g.
# "Cooling Time Constant" extracting as "C\nooling Time Constant" or
# "Direction of Rotation" as "Dire\nction of Rotation". Only joins a
# lowercase continuation onto the previous line — safe, won't merge
# unrelated paragraph breaks (which are usually followed by a capital,
# digit, or a fresh label).
def dehyphenate(text):
    return re.sub(r'(?<=[A-Za-z])\n(?=[a-z])', '', text)


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
    # ── NEW: dehyphenate BEFORE any regex runs against it ───────────────────
    t = dehyphenate(motor_pdf_text)

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
        # NOTE: Rated Voltage / Rated Voltage UOM — see call-out at bottom of
        # file. The "415" is extracted by PyPDF2 completely disconnected
        # from the "Supply System:" label (floating text box, out of visual
        # order). This pattern still works because it doesn't rely on that
        # label at all — it just grabs any bare 3-digit number followed by
        # "+-10%" anywhere in the text.
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
        # NOTE: "Rotor End float" removed — confirmed against the real
        # EA001-Motor.xlsx template that no column exists for it anywhere
        # in the 141 headers. Extracting it was harmless but always
        # produced a noisy "no matching Excel column" warning in Node 5.
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
        # ── FIXED: "Cooling Time Constant" was NEVER matching because
        # PyPDF2 was splitting it as "C\nooling Time Constant" — confirmed
        # against your actual PDF. dehyphenate() above fixes the word split;
        # this pattern also loosens the required spacing to be safe.
        "Heating Time Constant": (
            "Heating Time Constant",
            [r"Heating\s*Time\s*Constant.*?=\s*([-+]?\d+(?:\.\d+)?)\s*min"]
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
        # NOTE: "Direction of Rotation" removed — confirmed against the
        # real EA001-Motor.xlsx template that no column exists with this
        # exact name. The template's actual column for this data is named
        # "DOR", which the "DOR" synonym field (loaded via merge below)
        # already extracts and writes correctly. This was a pure duplicate
        # producing a noisy "no matching Excel column" warning in Node 5.
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
        # ── FIXED: "Type of motor" followed by a checkbox glyph (U+F06E),
        # not a plain space. \s+ never matched it. CHK now swallows it.
        "Motor Type": ("Motor Type", [r"Type of motor" + CHK + r"([A-Za-z ]+[Mm]otor)"]),
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
    # ── FIXED: real PDF has "rr=0.0000018" (no spaces around "=") and
    # "20 °C" (an extra space before the degree symbol, so the old single
    # "." wildcard for "20.C" didn't cover it). Both loosened below.
    combined_specs = [
        ("Rotor Resistance (Ac) @ 20°C", r"Rotor\s*Resistance\(ac\)\s*@\s*20\s*.?\s*C\s*rr\s*=\s*([\d.]+)\s*/\s*([\d.]+)", "{} / {}"),
        ("Rotor Reactance @ 20°C", r"Rotor\s*Reactance\s*@\s*20\s*.?\s*C\s*Xr\s*=\s*([\d.]+)\s*/\s*([\d.]+)", "{} / {}"),
        ("Stator Resistance (AC) @ 20°C", r"Stator\s*Resistance\(ac\)\s*@\s*20\s*.?\s*C\s*rs\s*=\s*([\d.]+)\s*/\s*([\d.]+)", "{} / {}"),
        ("Stator Reactance @ 20°C", r"Stator\s*Reactance\s*@\s*20\s*.?\s*C\s*Xs\s*=\s*([\d.]+)\s*/\s*([\d.]+)", "{} / {}"),
    ]
    for field_name, pattern, template in combined_specs:
        val = find_value_combined(t, pattern, field_name, template)
        if val:
            motor_data[field_name] = val

    # ── NEW: standalone value fields that were entirely missing before ─────
    single_specs = [
        ("Stator Leakage Reactance @ 20°C", r"Stator\s*Leakage\s*Reactance\s*@\s*20\s*.?\s*C\s*X1\s*=\s*([\d.]+)"),
        ("Magnetising Resistance @ 20°C", r"Magnetising\s*Resistance\s*@\s*20\s*.?\s*C\s*rm\s*=\s*([\d.]+)"),
        ("Magnetising Reactance @ 20°C", r"Magnetising\s*Reactance\s*@\s*20\s*.?\s*C\s*Xm\s*=\s*([\d.]+)"),
    ]
    for field_name, pattern in single_specs:
        val = find_value(t, [pattern], field_name)
        if val:
            motor_data[field_name] = val

    # ── NEW: UOM fields for the reactance/resistance block — all share the
    # same "pu" token right after the numeric pair, now matched reliably ───
    uom_specs = [
        ("Rotor Resistance (Ac) @ 20°C UOM", r"rr\s*=\s*[\d.]+\s*/\s*[\d.]+\s*(pu)"),
        ("Rotor Reactance @ 20°C UOM", r"Xr\s*=\s*[\d.]+\s*/\s*[\d.]+\s*(pu)"),
        ("Stator Resistance (AC) @ 20°C UOM", r"rs\s*=\s*[\d.]+\s*/\s*[\d.]+\s*(pu)"),
        ("Stator Reactance @ 20°C UOM", r"Xs\s*=\s*[\d.]+\s*/\s*[\d.]+\s*(pu)"),
        ("Stator Leakage Reactance @ 20°C UOM", r"X1\s*=\s*[\d.]+\s*N\.?A\.?\s*(pu)"),
    ]
    for field_name, pattern in uom_specs:
        val = find_value(t, [pattern], field_name)
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

    # ── KNOWN, UNFIXABLE-BY-REGEX gaps (confirmed against your real PDF) ───
    # 1. "Temperature Rise UOM" — the number "77" is followed directly by
    #    "Heater:-" in the extracted text; no unit character exists nearby
    #    anywhere in the PDF text. Not a pattern bug — the data isn't there.
    #    Recommend hardcoding "°C" as a static default at the Excel-write
    #    step, since Temp Rise is always Celsius on these datasheets.
    # 2. "Bearing RTD Required Per Winding" — PyPDF2 extracts this form's
    #    two-column checkbox layout out of visual order, so "Area
    #    Classification:-" (left column) and "RTD's Required:" (right
    #    column, bearing section) end up textually adjacent even though
    #    they're unrelated on the page. Regex can't safely disambiguate
    #    this from "RTD Required Per Winding" — would need pdfplumber with
    #    coordinate-based (x/y) table extraction instead of PyPDF2 to fix
    #    properly.
    # 3. "Rated Voltage UOM" — "415" is extracted completely disconnected
    #    from "Supply System:" (a floating text box pulled out of order).
    #    The Rated Voltage *value* still works (matches "415" via the
    #    "+-10%" anchor elsewhere), but there's no reliable unit anchor.
    #    Recommend hardcoding "V" as a static default — it's always volts.
    for missing_field in ["Temperature Rise UOM", "Bearing RTD Required Per Winding", "Rated Voltage UOM"]:
        print2log(f"  [KNOWN GAP - static default recommended] {missing_field}")
        motor_logs.append({"Field Name": missing_field, "Extracted Value": "", "Status": "NOT IN PDF TEXT - USE STATIC DEFAULT"})

    print2log(f"Total motor fields successfully extracted: {len(motor_data)} / {len(MOTOR_FIELDS)}")

print2log("===== NODE 3 COMPLETE =====")

output_df = df.copy()
output_df["motor_data"] = [motor_data]
output_df["motor_logs"] = [motor_logs]

return output_df
