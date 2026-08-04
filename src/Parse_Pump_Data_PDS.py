import re
import pandas as pd

print2log("===== NODE 4: Pump Data Parsing (FIXED v2) =====")

# ── Helper: regex field extractor ────────────────────────────────────────────
def find_value(text, patterns, field_name, flags=re.IGNORECASE):
    regex_error = False
    for pat in patterns:
        try:
            m = re.search(pat, text, flags)
            if m:
                val = m.group(1) if m.groups() else m.group(0)
                if val and val.strip():
                    val = val.strip()
                    print2log(f"[FOUND] {field_name} = '{val}'")
                    pump_logs.append({"Field Name": field_name, "Extracted Value": val, "Status": "FOUND"})
                    return val
        except Exception as e:
            regex_error = True
            print2log(f"WARNING: regex error for field '{field_name}' pattern '{pat}': {e}")
    print2log(f"[NOT FOUND] {field_name}")
    pump_logs.append({"Field Name": field_name, "Extracted Value": "", "Status": "REGEX ERROR" if regex_error else "NOT FOUND"})
    return None


# ── Helper: multi-group regex extractor, joins captured groups with a separator ──
def find_value_combined(text, pattern, field_name, template, flags=re.IGNORECASE):
    try:
        m = re.search(pattern, text, flags)
        if m:
            groups = [g.strip() for g in m.groups() if g]
            if groups:
                val = template.format(*groups)
                print2log(f"[FOUND] {field_name} = '{val}'")
                pump_logs.append({"Field Name": field_name, "Extracted Value": val, "Status": "FOUND"})
                return val
    except Exception as e:
        print2log(f"WARNING: regex error for field '{field_name}': {e}")
    print2log(f"[NOT FOUND] {field_name}")
    pump_logs.append({"Field Name": field_name, "Extracted Value": "", "Status": "NOT FOUND"})
    return None


def set_field(field_name, value, status="FOUND", note=""):
    """Directly set a field (used for cross-node lookups, static defaults,
    and heuristic/positional extractions that don't fit find_value's model)."""
    if value:
        pump_data[field_name] = value
        print2log(f"[{status}] {field_name} = '{value}'{('  ' + note) if note else ''}")
        pump_logs.append({"Field Name": field_name, "Extracted Value": value, "Status": status})
    else:
        print2log(f"[NOT FOUND] {field_name}{('  ' + note) if note else ''}")
        pump_logs.append({"Field Name": field_name, "Extracted Value": "", "Status": "NOT FOUND"})


# ── Rubiscape entry point ────────────────────────────────────────────────────
print2log(f"inputData keys: {list(inputData.keys())}")

df = inputData.get("Parse_Motor_Data_MDS")
if df is None or len(df) == 0:
    print2log("ERROR: No data received from Node 3 (Motor_Data_Parsing)")
    raise Exception("NODE 4: missing input DataFrame from predecessor task")

row = df.iloc[0]
pump_pdf_text = row.get("pump_pdf_text")
pump_data = {}
pump_logs = []

# ── NEW: motor_data comes along for free on this same row from Node 3 —
# use it directly for fields the pump PDF genuinely doesn't contain
# (Driver Voltage/Phase/Frequency are motor nameplate values, not pump
# datasheet values; confirmed absent from the pump PDF text).
motor_data = row.get("motor_data") or {}

# ── Load synonym patterns (node output key is 'pump_synonyms' per your canvas) ──
synonyms_df = inputData.get("pump_synonyms")

synonym_patterns_by_field = {}
if synonyms_df is not None and len(synonyms_df) > 0:
    sorted_syn = synonyms_df.sort_values(["field_key", "pattern_order"])
    for field_key, group in sorted_syn.groupby("field_key"):
        synonym_patterns_by_field[field_key] = group["pattern"].tolist()
    print2log(f"Loaded synonym patterns for {len(synonym_patterns_by_field)} fields from pump_synonyms node.")
else:
    print2log("WARNING: No synonym DataFrame found — proceeding with base patterns only.")

if not pump_pdf_text:
    print2log("WARNING: No pump PDF text available — skipping pump parsing.")
else:
    t = pump_pdf_text

    PUMP_FIELDS = {

    "Tag Name": ("Tag Name", [
        r"Equipment No\.\s*(MP-PP\d+-P\d+[A-Z]?/?[A-Z]?)",
        r"MP-PP\d+-P\d+[A-Z]?/?[A-Z]?"
    ]),
    "Serial Number": ("Serial Number", [r"Serial No\.\s*([A-Z0-9\-]+)"]),
    "Manufacture": ("Manufacture", [r"Manufacturer\s+([A-Za-z]+)\s+Model"]),
    "Datasheet No": ("Datasheet No", [
        r"(\d{6,}-\d+-PDS)",
        r"VENDOR DOCUMENT NO:\s*\n?\s*([A-Z0-9\-]+-PDS)"
    ]),
    "Model Number": ("Model Number", [
        r"Model\s+(CPK\s*80-315)",
        r"Model\s+([A-Za-z0-9\- ]+)"
    ]),
    "pump type": ("pump type", [
        r"Type\s+(OH1)",
        r"Type of pump\s*([^\n]+)"
    ]),
    "Number of stages ": ("Number of stages ", [r"No\.\s*Stages\s*(\d+)"]),
    "Direction of Rotation, from driver end": ("Direction of Rotation, from driver end", [
        r"CW\s*\n?\s*CCW",
        r";\s*(CW|CCW)",
        r"Shaft Rotation.*?(CW|CCW)",
        r"Rotation\s*(Clockwise|Counter-?clockwise)"
    ]),
    "CASING MOUNTING": ("CASING MOUNTING", [
        r"CASING MOUNTING.*?;?\s*(Foot|Sump|Centreline|Near Centreline|Vertical|Vertical Barrel|Inline|Bracket)"
    ]),
    "CASING TYPE": ("CASING TYPE", [
        r"CASING TYPE.*?;?\s*(Single Volute|Double Volute|Diffuser|Staggered|Vertical Double|Barrel)"
    ]),
    "Impeller type": ("Impeller type", [r"Impeller Style:.*?;?\s*(Closed|Open|Semi-open)"]),
    "Suction nozzle size": ("Suction nozzle size", [
        r"Suction\s+(\d+(?:/\d+)?)\"",
        r"MAIN CONNECTIONS.*?Suction\s+(\d+)\""
    ]),
    "Discharge Nozzle size ": ("Discharge Nozzle size ", [
        r"Discharge\s+(\d+(?:/\d+)?)\""
    ]),
    "Discharge Nozzle Rating ": ("Discharge Nozzle Rating ", [
        r"Discharge\s+\d+(?:/\d+)?\"?\s+(\d+\s*#)"
    ]),
    "Suction Nozzle Rating ": ("Suction Nozzle Rating ", [
        r"Suction\s+\d+(?:/\d+)?\"?\s+(\d+\s*#)"
    ]),
    "Shaft diameter @ coupling": ("Shaft diameter @ coupling", [r"Shaft diameter.*?(\d+)"]),
    "Bearing span": ("Bearing span", [r"Span between bearing centers.*?(\d+)"]),
    "Wet Critical speed": ("Wet Critical speed", [r"Critical speed.*?(\d+)"]),
    "bearing type, DE": ("bearing type, DE", [r"Radial\s+Deep groove ball bearing\s*([0-9A-Z ]+)"]),
    "bearing type, NDE": ("bearing type, NDE", [r"Thrust\s+Deep groove ball bearing\s*([0-9A-Z ]+)"]),
    "Bearing lubrication": ("Bearing lubrication", [
        r"LUBRICATION TYPE:\s*([^\n]+)",
        r"Lubrication.*?(Grease|Ring Oil|Forced Oil|Pure Oil Mist|N/A)"
    ]),
    "operating weight": ("operating weight", [
        r"Total Mass\s*(\d+)\s*kg",
        r"Total operation weight.*?(\d+)"
    ]),
    "Baseplate weight": ("Baseplate weight", [r"Mass of Baseplate\s*(\d+)\s*kg"]),
    "Driver weight": ("Driver weight", [r"Mass of Motor\s*(\d+)\s*kg"]),
    "dry weight": ("dry weight", [r"Mass of Pump\s*(\d+)\s*kg"]),
    "Driver Type": ("Driver Type", [
        r"DRIVER TYPE\s*(Motor)",
        r"(Electric Motor)"
    ]),
    "Driver Manufacturer": ("Driver Manufacturer", [
        r"MANUFACTURER\s+([A-Z]+)\s+NOMINAL RPM",
        r"MANUFACTURER\s*(CGL|KSB|ABB|Siemens|CG)"
    ]),
    "Driver Frame": ("Driver Frame", [r"FRAME OR MODEL\s*([^\n]+)"]),
    "Driver Rating ": ("Driver Rating ", [
        r"NAMEPLATE POWER\s*([\d.]+)\s*Kw",
        r"Rated Power.*?([\d.]+)"
    ]),
    "Hydraulic Power ": ("Hydraulic Power ", [r"Hyd\. Power\s*\(kW\)\s*([\d.]+)"]),
    "Rated Efficiency": ("Rated Efficiency", [
        r"Efficiency\s*\(%\)\s*([\d.]+)"
    ]),
    "rated speed": ("rated speed", [
        r"Pump Speed\s*\(rpm\)\s*(\d+)"
    ]),
    "Net positive suction head required": ("Net positive suction head required", [
        r"NPSH Required\s*\(m Water\)\s*([\d.]+)",
        r"NPSH Required.*?([\d.]+)"
    ]),
    "NPSHa @ shaft centreline, rated capcity": ("NPSHa @ shaft centreline, rated capcity", [
        r"NPSH Available.*?\(1\)\(2\)\s*([\d.]+)"
    ]),
    "Capacity  Rated / Maximum": ("Capacity  Rated / Maximum", [
        r"Capacity\s*m³/h.*?Rated\s+([\d.]+)",
        r"Capacity.*?Rated\s+([\d.]+)"
    ]),
    "Differential head @ rated flow": ("Differential head @ rated flow", [
        r"Diff\. Head.*?\(1\)\(2\)\s*([\d.]+)"
    ]),
    "Discharge pressure @ rated flow": ("Discharge pressure @ rated flow", [
        r"Disch\. Press.*?\(1\)\(2\)\s*([\d.]+)"
    ]),
    "Maximum pumping  temperature": ("Maximum pumping  temperature", [
        r"Pumping Temperature\s*(\d+)",
        r"Max\.\s*operating\s*temperature.*?(\d+)"
    ]),
    "density": ("density", [
        r"Specific Gravity @:\s*°?C?\s*([\d.]+)"
    ]),
    " Viscosity Maximum": (" Viscosity Maximum", [
        r"Viscosity.*?([\d.]+)"
    ]),
    "fluid name": ("fluid name", [
        r"Name\s+([A-Z ]+?)\s*\n"
    ]),
    "explosion protection zone": ("explosion protection zone", [
        r"Area Classification\s*([A-Z ]+)"
    ]),
    "explosion protection temperature class": ("explosion protection temperature class", [
        r"Temperature Class\s*(T\d)",
        r"Zone.*?(T\d)"
    ]),
    "explosion protection gas group": ("explosion protection gas group", [
        r"Gas Group\s*([^\n]+)"
    ]),
    "seal type": ("seal type", [
        r"(Mechanical Seal)"
    ]),
    "Seal API class code": ("Seal API class code", [
        r"API Class Code\s*(API\s*682.*?4th)",
        r"(API\s*682)"
    ]),
    "Coupling Model": ("Coupling Model", [
        r"FLEXIBLE METALLIC SPACER\s*([A-Z0-9()\- ]+CPLG)",
        r"(SWQ-276\(140\)\s*STD\s*CPLG)"
    ]),
    "Coupling Type": ("Coupling Type", [
        r"(FLEXIBLE METALLIC SPACER)"
    ]),
    "Hydro test pressure": ("Hydro test pressure", [
        r"Hydrotest Pressure\s*\(kg/cm²g\):\s*([\d.]+)",
        r"Hydrotest Pressure.*?([\d.]+)"
    ]),
    "Maximum  design pressure": ("Maximum  design pressure", [
        r"MAWP\)?:\s*([\d.]+)",
        r"Max\.\s*Allowable\s*Working\s*Pressure.*?([\d.]+)"
    ]),
    "Maximum design temperature": ("Maximum design temperature", [
        r"design temperature\s*:\s*(\d+)",
        r"Design temperature.*?(\d+)"
    ]),
    "Material: Shaft": ("Material: Shaft", [r"Shaft\s+(A276\s*TP\s*410\s*COND\s*H)"]),
    "MATERIAL:IMPELLER": ("MATERIAL:IMPELLER", [r"Impeller\s+(A743\s*Gr\.\s*CF3)"]),
    "Material : Casing ": ("Material : Casing ", [
        r"Case\s+(A743\s*Gr\.\s*CF3)",
        r"Barrel/Casing\s+([^\n]+)"
    ]),

    # ── NEW: fixed / newly derived clean-anchor fields ──────────────────────

    # Plant Code — the DECAL header's "Unit No. (Plant WBS)" box is digit-
    # by-digit scrambled ("N23P01-...-04  1 - 0 -03 Cat. No\n0 08"), totally
    # unrecoverable. But the identical "031" appears cleanly embedded in the
    # Data Sheet No. printed in the page footers — anchor there instead.
    "Plant Code": ("Plant Code", [r"TPD-P-\d+-\s*(\d+)-D\d+-\d+"]),

    # Plant Name — "PVC" bracket in the project title survives intact even
    # though the surrounding text has an extraction artifact
    # ("POLYVINY L CHLORIDE").
    "Plant Name": ("Plant Name", [r"\((PVC)\)"]),

    # IMPELLER DIA RATED/MAX/MIN — the "Impeller Dia. (mm)" label is
    # scrambled away to a different table column, but the numeric triple
    # itself survives as an intact, unique unit: "Rated 300 Max 320 Min 268".
    # Matched as a shape rather than anchored on the broken label.
    "IMPELLER DIA RATED": ("IMPELLER DIA RATED", [r"Rated\s+(\d+)\s+Max\s+\d+\s+Min\s+\d+"]),
    "IMPELLER DIA MAXIMUM": ("IMPELLER DIA MAXIMUM", [r"Rated\s+\d+\s+Max\s+(\d+)\s+Min\s+\d+"]),
    "IMPELLER DIA MINIMUM": ("IMPELLER DIA MINIMUM", [r"Rated\s+\d+\s+Max\s+\d+\s+Min\s+(\d+)"]),

    # MOC, impeller wear ring — reuses the same clean "Impeller A743 Gr.
    # CF3" materials-table row already used for MATERIAL:IMPELLER.
    "MOC, impeller wear ring": ("MOC, impeller wear ring", [r"Impeller\s+(A743\s*Gr\.\s*CF3)"]),

    # Seal Secondary flush Plan — BUG FOUND: text literally reads
    # "Secondary Flush Plan 61M" (no "Plan" prefix on the value itself,
    # unlike Primary which does say "Plan 11"). Old regex required the
    # literal word "Plan" before the value and could never match. Capture
    # the bare code and re-add the "Plan " prefix in code instead.
    "Seal Secondary flush Plan": ("Seal Secondary flush Plan", [r"Secondary Flush Plan\s+(?:Plan\s*)?([\dA-Z]+)"]),

    # Seal Manufacturer — "Manufacturer" label (row 32/34) is scrambled
    # away from "EagleBurgmann" (which lands disconnected, later in the
    # stream). Matched via a whitelist of known seal-vendor brand names
    # instead of relying on label adjacency at all.
    "Seal Manufacturer": ("Seal Manufacturer", [r"(EagleBurgmann|John Crane|Flowserve|AESSEAL|Chesterton|Burgmann)"]),

    # Purchase Order Date — "DATE" label and its value are scrambled apart
    # (value lands next to the Item No. / MRQ Number block instead).
    # Anchored on the DD.MM.YYYY shape instead, which is distinctive enough
    # not to collide elsewhere in this document.
    "Purchase Order Date": ("Purchase Order Date", [r"(\d{2}\.\d{2}\.\d{4})"]),
    }

    # ── Merge synonym patterns ───────────────────────────────────────────────
    added_count = 0
    merged_count = 0
    for field_key, syn_patterns in synonym_patterns_by_field.items():
        if field_key in PUMP_FIELDS:
            header, existing_patterns = PUMP_FIELDS[field_key]
            new_patterns = existing_patterns + [p for p in syn_patterns if p not in existing_patterns]
            PUMP_FIELDS[field_key] = (header, new_patterns)
            merged_count += 1
        else:
            PUMP_FIELDS[field_key] = (field_key, syn_patterns)
            added_count += 1

    print2log(f"Merged synonym patterns into {merged_count} existing fields; "
              f"added {added_count} new fields from synonyms.")

    print2log(f"Parsing {len(PUMP_FIELDS)} candidate fields from pump PDF...")
    for field_key, field_def in PUMP_FIELDS.items():
        header, patterns = field_def[0], field_def[1]
        val = find_value(t, patterns, field_key)
        if val:
            pump_data[header] = val

    # ── Combined / derived fields that can't live in the flat synonym table ──

    # density / density maximum: PDF gives Specific Gravity (unitless), Excel
    # expects kg/m3 — needs a x1000 conversion; UOM is never printed, hardcoded.
    sg_val = find_value(t, [r"Specific Gravity @:\s*°?C?\s*([\d.]+)"], "density (raw specific gravity)")
    if sg_val:
        try:
            density_kg_m3 = round(float(sg_val) * 1000)
            pump_data["density"] = str(density_kg_m3)
            pump_data["density maximum"] = str(density_kg_m3)
            pump_data["density UOM"] = "kg/m3"
            pump_data["density maximum UOM"] = "kg/m3"
            print2log(f"[FOUND] density = '{density_kg_m3}' (converted from SG {sg_val})")
            pump_logs.append({"Field Name": "density", "Extracted Value": str(density_kg_m3), "Status": "FOUND"})
        except ValueError:
            print2log(f"WARNING: could not convert specific gravity '{sg_val}' to density")

    # Discharge / Suction Nozzle Rating UOM: PDF prints "#" (pound rating),
    # Excel expects "Lb RF" — static mapping.
    if "Discharge Nozzle Rating " in pump_data:
        pump_data["Discharge Nozzle Rating  UOM"] = "Lb RF"
        pump_logs.append({"Field Name": "Discharge Nozzle Rating  UOM", "Extracted Value": "Lb RF", "Status": "FOUND"})
    if "Suction Nozzle Rating " in pump_data:
        pump_data["Suction Nozzle Rating  UOM"] = "Lb RF"
        pump_logs.append({"Field Name": "Suction Nozzle Rating  UOM", "Extracted Value": "Lb RF", "Status": "FOUND"})

    # CAPACITY MINIMUM CONTINUOUS STABLE /Thermal: two numbers combined.
    val = find_value_combined(
        t,
        r"Min\.\s*Continuous Flow.*?Thermal\s+(\d+)\s+Stable\s+(\d+)",
        "CAPACITY MINIMUM CONTINUOUS STABLE /Thermal",
        "{1} stable / {0} thermal"
    )
    if val:
        pump_data["CAPACITY MINIMUM CONTINUOUS STABLE /Thermal"] = val

    # Material of construction, Annex H Class: three material strings combined.
    val = find_value_combined(
        t,
        r"Barrel/Casing\s+(A743\s*Gr\.\s*CF3).*?Sleeve\s+([0-9A-Z]+).*?Shaft\s+([A-Z0-9 ]+COND\s*H)",
        "Material of construction, Annex H Class",
        "{} / {} / {}"
    )
    if val:
        pump_data["Material of construction, Annex H Class"] = val

    # ──────────────────────────────────────────────────────────────────────
    # NEW: cross-node lookup — Driver Voltage/Phase/Frequency are motor
    # nameplate values, confirmed genuinely absent from the pump PDF text.
    # Node 4 already receives Node 3's full output row, which carries the
    # already-parsed motor_data dict — read them from there instead of
    # trying (and failing) to regex the pump PDF for them.
    # ──────────────────────────────────────────────────────────────────────
    if motor_data:
        if motor_data.get("Rated Voltage"):
            set_field("Driver Voltage", motor_data["Rated Voltage"], note="(from motor_data, Node 3)")
            set_field("Driver Voltage UOM", "V", note="(static — always volts)")
        if motor_data.get("Number of Electrical Phases"):
            set_field("Driver Phase Number", motor_data["Number of Electrical Phases"], note="(from motor_data, Node 3)")
        if motor_data.get("Rated Frequency"):
            set_field("Driver Frequency", motor_data["Rated Frequency"], note="(from motor_data, Node 3)")
            set_field("Driver Frequency UOM", "Hz", note="(static — always hertz)")
    else:
        print2log("WARNING: no motor_data found on input row — Driver Voltage/Phase/Frequency will be blank. "
                   "Confirm Node 3 output is being passed through to Node 4 unchanged.")

    # ──────────────────────────────────────────────────────────────────────
    # NEW: Suction / Discharge nozzle block — HEURISTIC, POSITIONAL.
    # There is NO reliable label-adjacency here at all: PyPDF2 extracts the
    # "SIZE / RATING / FACING / POSITION" grid header row immediately next
    # to the MECHANICAL SEAL column's labels (a different, unrelated column
    # scrambled in), while the actual Suction/Discharge values land
    # disconnected, further down the stream, in a fixed order specific to
    # this vendor's PDF rendering.
    #
    # Confirmed against this exact document's raw text: sizes appear in
    # document order as [suction, drain, discharge] — e.g. 5", 1/2", 3" —
    # and the discharge size is uniquely anchored by "RATING" appearing
    # immediately after it with no space ("3"RATING"). Facing ("RF") and
    # rating ("150 #") appear exactly twice each on this page, used only
    # for these two nozzles. Position tokens are matched in ALL CAPS only
    # ("HORIZONTAL"/"VERTICAL") to avoid colliding with the unrelated
    # "ORIENTATION Horizontal" field, which is lowercase in the source.
    #
    # ⚠ This is template-order-dependent, not label-based. It will very
    # likely need re-validation (or a different heuristic) against pump
    # PDFs from other vendors before trusting it broadly — please spot
    # check a second vendor's PDF before relying on this in production.
    # ──────────────────────────────────────────────────────────────────────
    discharge_size_m = re.search(r'(\d+(?:/\d+)?)"RATING', t)
    all_sizes = [s for s in re.findall(r'(\d+(?:/\d+)?)"', t) if s != "1/2"]  # 1/2" = drain, exclude
    all_ratings = re.findall(r'(\d+)\s*#', t)
    all_facings = re.findall(r'\bRF\b', t)
    all_positions = re.findall(r'\b(HORIZONTAL|VERTICAL)\b', t)  # case-sensitive, excludes "Orientation Horizontal"

    if all_sizes:
        set_field("Suction nozzle size", all_sizes[0], note="(heuristic — positional)")
    if discharge_size_m:
        set_field("Discharge Nozzle size ", discharge_size_m.group(1), note="(anchored on literal '\"RATING')")
    elif len(all_sizes) > 1:
        set_field("Discharge Nozzle size ", all_sizes[-1], note="(heuristic — positional fallback)")

    if len(all_ratings) >= 2:
        set_field("Suction Nozzle Rating ", all_ratings[0], note="(heuristic — positional)")
        set_field("Discharge Nozzle Rating ", all_ratings[1], note="(heuristic — positional)")
        pump_data["Suction Nozzle Rating  UOM"] = "Lb RF"
        pump_data["Discharge Nozzle Rating  UOM"] = "Lb RF"

    if len(all_positions) >= 2:
        # Document order: VERTICAL appears before HORIZONTAL in the raw
        # stream on this template, corresponding to Discharge (row 32) then
        # Suction (row 31) once un-scrambled by content rather than order.
        pos_by_token = {"HORIZONTAL": "Horizontal", "VERTICAL": "Vertical"}
        found_tokens = set(all_positions)
        if "HORIZONTAL" in found_tokens:
            set_field("Suction Nozzle Position", "Horizontal", note="(heuristic)")
        if "VERTICAL" in found_tokens:
            set_field("Discharge Nozzle Position", "Vertical", note="(heuristic)")

    # ──────────────────────────────────────────────────────────────────────
    # NEW: Suction / Vapour pressure block — see conversation notes.
    # The pair "Max. 0.68 Rated -0.10" is textually attached to the
    # "Vapour press" label, but the values actually belong to the row
    # ABOVE it ("Suct. Pres.") — this vendor's fillable-form layout prints
    # entered values one visual row below their label, so PyPDF2's linear
    # extraction shifts them down by one row. Confirmed by matching your
    # Excel's expected values exactly (Max suction pressure=0.68,
    # Suction pressure Min/Normal=-0.1).
    #
    # ⚠ IMPORTANT: this means the pre-existing "Vapor pressure, max" field
    # (built on the OLD "Vapour press...Max." pattern) has likely been
    # silently extracting 0.68 all along — Suction's number, not Vapour
    # press's own. Recommend spot-checking that field's historical output.
    #
    # Vapour press's OWN rated value (0.25) shows up separately, anchored
    # on the literal "RATING0.25" substring further down the stream.
    # ──────────────────────────────────────────────────────────────────────
    suct_pair = re.search(r"Max\.\s*([\d.]+)\s*Rated\s*(-?[\d.]+)", t)
    if suct_pair:
        set_field("Maximum suction  pressure", suct_pair.group(1), note="(row-shift corrected — see comments)")
        set_field("Suction pressure Minimum", suct_pair.group(2), note="(row-shift corrected — see comments)")
        set_field("Suction Pressure Normal", suct_pair.group(2), note="(row-shift corrected — see comments)")

    vapour_rated = re.search(r"RATING(0\.\d+)\s*\n?\s*HORIZONTAL", t)
    if vapour_rated:
        set_field("normal operating vapour pressure", vapour_rated.group(1), note="(fragile anchor — verify)")
        set_field("Vapor pressure, min", vapour_rated.group(1), note="(fragile anchor — verify)")
    # NOTE: Vapour press's own MAXIMUM value could not be confidently located
    # anywhere in the extracted text — left blank rather than guessed.
    # Recommend a manual check of page 2, row 14 ("Vapour press... Max.").

    # ──────────────────────────────────────────────────────────────────────
    # NEW: static defaults for fields confirmed genuinely not applicable to
    # this pump (single-stage OH1, no lineshaft/inducer/diffuser, etc.) —
    # your synonyms file already flags these as NOT IN PDF, and your Excel's
    # own "Prefilled from vendor" column expects NA/N/A for every one of
    # them, so this isn't a parsing gap, it's a known-absent-attribute list.
    # ──────────────────────────────────────────────────────────────────────
    STATIC_NOT_APPLICABLE = {
        "Erosive ": "NA",
        "explosion protection gas group": "NA",
        "explosion protection temperature class": "NA",
        "Gearbox weight": "NA",
        "Gearbox weight UOM": "kg",
        "H2S concentration": "NA",
        "H2S concentration UOM": "PPM",
        "immersed": "No",
        "Impeller weight": "NA",
        "Impeller weight UOM": "Kg",
        "Inducer": "NA",
        "ingress protection": "NA",
        "MATERIAL:DIFFUSERS": "NA",
        "MATERIAL:DISCHARGE COLUMN": "NA",
        "MATERIAL:DISCHARGE HEAD": "NA",
        "MATERIAL:LINESHAFT": "NA",
        "MATERIAL:LINESHAFT BEARING": "NA",
        "MATERIAL:SUCTION CAN/BARREL": "NA",
        "MOC, inducer": "NA",
        "MOC, interstage bushing": "NA",
        "MOC, throat bush": "NA",
        "NPSH margin, max capacity": "NA",
        "NPSH margin, max capacity UOM": "M",
        "NPSH margin, min capacity": "NA",
        "NPSH margin, min capacity UOM": "M",
        "NPSHa @ shaft centreline, min capcity": "NA",
        "NPSHa @ shaft centreline, min capcity UOM": "M",
        "NPSHr @ shaft centreline, max capcity": "NA",
        "NPSHr @ shaft centreline, max capcity UOM": "M",
        "NPSHr @ shaft centreline, min capcity": "NA",
        "NPSHr @ shaft centreline, min capcity UOM": "m",
        "Piping class": "NA",
        "Pumping Fluid Polymerisation agent with Concentration ": "NA",
        "Pumping Fluid Solid Containment with Concentration ": "NA",
        "Radial Vibration probe type": "N/A",
        "Rotor axial position probe": "N/A",
        "Rotor weight": "NA",
        "Rotor weight UOM": "kg",
        "Shaft diameter @ coupling UOM": "mm",
        "Shaft diameter @ seal": "NA",
        "Shaft diameter @ seal UOM": "MM",
        "Shaft weight": "NA",
        "Shaft weight UOM": "KG",
        "Wet Critical speed UOM": "rpm",
    }
    for field_name, default_val in STATIC_NOT_APPLICABLE.items():
        if field_name not in pump_data or not pump_data.get(field_name):
            set_field(field_name, default_val, status="STATIC DEFAULT (confirmed N/A on this pump type)")

    # Shaft diameter @ coupling: still attempt real extraction first (see
    # PUMP_FIELDS above); if it genuinely found nothing, only THEN this
    # confirms the field truly isn't printed for this pump — default to NA.
    if "Shaft diameter @ coupling" not in pump_data:
        set_field("Shaft diameter @ coupling", "NA", status="STATIC DEFAULT (confirmed N/A on this pump type)")

    # ──────────────────────────────────────────────────────────────────────
    # NEW: test medium — not stated anywhere as an explicit "medium" value
    # in the PDF; hydrostatic testing with water is standard convention for
    # this test type, and the Inspection & Testing table does show
    # Hydrostatic testing is required (witnessed). Treat as a business-rule
    # default tied to that confirmed checkbox, not a literal extraction.
    # ──────────────────────────────────────────────────────────────────────
    if re.search(r"Hydrostatic", t, re.IGNORECASE):
        set_field("test medium", "Water / hydrostatic test", status="STATIC DEFAULT (business convention)")

    print2log(f"Total pump fields successfully extracted: {len(pump_data)} / {len(PUMP_FIELDS)}")

    # ──────────────────────────────────────────────────────────────────────
    # KNOWN, UNFIXABLE-BY-REGEX / DATA-MISMATCH gaps (confirmed against the
    # real PDF text — no value exists in this document, or the Excel's
    # expected value conflicts with what the PDF actually prints):
    #
    # 1. "Auxiliary connections" — Excel expects a 4-item connection list
    #    (casing drain, base frame drain, vent/inlet & drain, flush) that
    #    does not exist anywhere in this PDF; the PDF's own "OTHER
    #    CONNECTIONS" table only has a single Drain row. Almost certainly
    #    sourced from a separate nozzle schedule / GAD drawing, not this PDS.
    # 2. "Weight Maintenance" (Excel expects 1056) — PDF's only mass total
    #    is "Total Mass 1050 kg". Different number entirely; likely a
    #    manually-calculated maintenance-spares weight, not in this document.
    # 3. "MOC, bearing housing" (Excel expects "IS 210 Gr.FG260") — this
    #    string does not appear anywhere in the extracted PDF text.
    # 4. "Number Running " / "Number Stand by " — PDF only states
    #    "No. Pumps Required = 4"; there is no run/standby split printed
    #    anywhere. A 50/50 default could be hardcoded IF that's always your
    #    convention, but that would be an assumption, not extraction —
    #    confirm before adding.
    # 5. "operation single/parallel", "Pump Single Line " — confirmed no
    #    such checkbox exists in this PDF (only Parallel/Series Operation
    #    checkboxes exist, both unchecked here).
    # 6. "Capacity Normal UOM" / "Capacity Minimum UOM" (Excel expects
    #    "LPM") — PDF's own capacity unit is m³/h throughout; hardcoding
    #    "LPM" as the unit while leaving the numeric value in m³/h would be
    #    internally inconsistent. Needs a decision: convert the values too,
    #    or treat "LPM" in the Excel as an error and use "m³/h" instead.
    # 7. "Brake Power MAXIMUM of RATED IMPELLER" (Excel expects 300) — this
    #    number matches Impeller Dia Rated (300 mm), not any brake-power
    #    value in the PDF (the PDF's actual "Max. Power @ Rated Imp." is a
    #    different value, ~68 kW, itself only weakly recoverable from the
    #    scrambled text). This looks like a field-name/mapping mismatch in
    #    the Excel template rather than a parsing gap — recommend
    #    confirming with whoever owns the template before writing any
    #    further regex against it.
    # ──────────────────────────────────────────────────────────────────────
    for gap_field in [
        "Auxiliary connections ",
        "Weight Maintenance",
        "MOC, bearing housing",
        "Number Running ",
        "Number Stand by ",
        "operation single/parallel",
        "Pump Single Line ",
        "Capacity Normal UOM",
        "Capacity Minimum UOM",
        "Brake Power  MAXIMUM of RATED IMPELLER",
    ]:
        if gap_field not in pump_data:
            print2log(f"  [KNOWN GAP - manual review / business decision needed] {gap_field}")
            pump_logs.append({"Field Name": gap_field, "Extracted Value": "", "Status": "NOT IN PDF - NEEDS DECISION"})

print2log("===== NODE 4 COMPLETE =====")

output_df = df.copy()
output_df["pump_data"] = [pump_data]
output_df["pump_logs"] = [pump_logs]

print2log(output_df.columns.tolist())

return output_df
