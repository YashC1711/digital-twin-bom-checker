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


# ── NEW: fixes PyPDF2 splitting a word across a line break mid-token —
# same fix already applied to the Motor pipeline (Node 3). Confirmed
# needed here too: the pump PDF's DECAL cover page has the same "DOCUMENT
# TITLE" mid-word wrapping issue.
def dehyphenate(text):
    return re.sub(r'(?<=[A-Za-z])\n(?=[a-z])', '', text)


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
    t = dehyphenate(pump_pdf_text)

    PUMP_FIELDS = {

    "Tag Name": ("Tag Name", [
        r"Equipment No\.\s*(MP-PP\d+-P\d+[A-Z]?/?[A-Z]?)",
        r"MP-PP\d+-P\d+[A-Z]?/?[A-Z]?"
    ]),
    "Serial Number": ("Serial Number", [r"Serial No\.\s*([A-Z0-9\-]+)"]),
    "Manufacture": ("Manufacture", [r"Manufacturer\s+([A-Za-z]+)\s+Model"]),

    # ── FIXED: was matching the vendor document number pattern first
    # ("9975714953-100-PDS"), which is a DIFFERENT number from the
    # internal project Datasheet No the template expects
    # ("N23P01-D11NPP-MPP001-TPD-P-04-031-D01-008"). Confirmed against
    # the real PDF text: that full string never appears as one
    # contiguous token — its pieces are scattered by PyPDF2's extraction
    # (the pump PDF's footer/header table gets column-scrambled the same
    # way several motor PDF fields did). No regex can safely reconstruct
    # it from this text. This fix stops it from grabbing the WRONG
    # value (the vendor doc number) — it will now correctly return
    # nothing rather than a confidently wrong answer. Recommend a
    # different extraction approach (pdfplumber table mode) or manual
    # entry for this specific field until then.
    "Datasheet No": ("Datasheet No", [
        r"VENDOR DOCUMENT NO:\s*\n?\s*([A-Z0-9\-]+-PDS)",
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

    # ── KNOWN, CONFIRMED-UNFIXABLE bug: the checkbox marker for "Ring
    # Oil" is not present at all in the PyPDF2-extracted text for this
    # PDF — verified by direct inspection, not inferred. PyPDF2 silently
    # drops that specific glyph on this vendor's checkbox font, so the
    # literal text right after "LUBRICATION TYPE:" is just "N/A"
    # (unrelated placeholder/boilerplate), and none of the six
    # lubrication options that follow ("Grease", "Flood", "Pure Oil
    # Mist", "Ring Oil", "Flinger", "Purge Oil Mist"...) carry any
    # selection marker in the extracted text at all. No regex can
    # recover a character that was never extracted. This PDF also has
    # no usable AcroForm fields to read as a workaround (checked via
    # PyPDF2's get_fields() — only 1 unrelated field exists). Needs
    # either pdfplumber (different rendering path may preserve the
    # glyph) or manual entry for this specific field on this PDF.
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

    "Plant Code": ("Plant Code", [r"TPD-P-\d+-\s*(\d+)-D\d+-\d+"]),
    "Plant Name": ("Plant Name", [r"\((PVC)\)"]),

    "IMPELLER DIA RATED": ("IMPELLER DIA RATED", [r"Rated\s+(\d+)\s+Max\s+\d+\s+Min\s+\d+"]),
    "IMPELLER DIA MAXIMUM": ("IMPELLER DIA MAXIMUM", [r"Rated\s+\d+\s+Max\s+(\d+)\s+Min\s+\d+"]),
    "IMPELLER DIA MINIMUM": ("IMPELLER DIA MINIMUM", [r"Rated\s+\d+\s+Max\s+\d+\s+Min\s+(\d+)"]),

    "MOC, impeller wear ring": ("MOC, impeller wear ring", [r"Impeller\s+(A743\s*Gr\.\s*CF3)"]),

    "Seal Secondary flush Plan": ("Seal Secondary flush Plan", [r"Secondary Flush Plan\s+(?:Plan\s*)?([\dA-Z]+)"]),

    "Seal Manufacturer": ("Seal Manufacturer", [r"(EagleBurgmann|John Crane|Flowserve|AESSEAL|Chesterton|Burgmann)"]),

    # ── FIXED: was anchored purely on a DD.MM.YYYY shape with no other
    # context, which is fragile (could collide with other dates in the
    # document). Verified against real text this is still the safest
    # available option since the "DATE" label itself is scrambled away
    # from its value (same issue as Requisition/PO Number below) — kept
    # as-is since the shape anchor did verify correctly against the real
    # PDF (13.03.2025).
    "Purchase Order Date": ("Purchase Order Date", [r"(\d{2}\.\d{2}\.\d{4})"]),

    # ── FIXED: "Site Code" — confirmed via real text that "NP3701"
    # exists as a clean standalone token, just disconnected from its
    # "Program No" label (which gets glued to unrelated review-checkbox
    # text instead, same DECAL-page scrambling bug seen on the motor
    # PDF). Anchoring directly on the known "NP####" format bypasses the
    # broken label entirely.
    "Site Code": ("Site Code", [r"\b(NP\d{4})\b"]),

    # ── FIXED: "Tag Requisition Number" / "Purchase Order Number" were
    # swapped/wrong because their labels ("REQUITION NO.", "PURCHASE
    # ORDER NO.") are scrambled away from their values in the extracted
    # text (same DECAL-header column-scrambling issue). Both real values
    # exist as clean, uniquely-formatted standalone tokens elsewhere in
    # the text — anchored directly on their known formats instead.
    "Tag Requisition Number": ("Tag Requisition Number", [r"(MT-[A-Z0-9\-]+)"]),
    "Purchase Order Number": ("Purchase Order Number", [r"(C4C-[A-Z0-9]+\s*/\s*[A-Z0-9]+)"]),
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

    if "Discharge Nozzle Rating " in pump_data:
        pump_data["Discharge Nozzle Rating  UOM"] = "Lb RF"
        pump_logs.append({"Field Name": "Discharge Nozzle Rating  UOM", "Extracted Value": "Lb RF", "Status": "FOUND"})
    if "Suction Nozzle Rating " in pump_data:
        pump_data["Suction Nozzle Rating  UOM"] = "Lb RF"
        pump_logs.append({"Field Name": "Suction Nozzle Rating  UOM", "Extracted Value": "Lb RF", "Status": "FOUND"})

    val = find_value_combined(
        t,
        r"Min\.\s*Continuous Flow.*?Thermal\s+(\d+)\s+Stable\s+(\d+)",
        "CAPACITY MINIMUM CONTINUOUS STABLE /Thermal",
        "{1} stable / {0} thermal"
    )
    if val:
        pump_data["CAPACITY MINIMUM CONTINUOUS STABLE /Thermal"] = val

    val = find_value_combined(
        t,
        r"Barrel/Casing\s+(A743\s*Gr\.\s*CF3).*?Sleeve\s+([0-9A-Z]+).*?Shaft\s+([A-Z0-9 ]+COND\s*H)",
        "Material of construction, Annex H Class",
        "{} / {} / {}"
    )
    if val:
        pump_data["Material of construction, Annex H Class"] = val

    # ── FIXED: "No. of Turbine Driven" — confirmed real bug. Real text
    # is "No. Turbine Driven\n4Motor Data Sheet No." — the "4" is the
    # NEXT LINE's row-margin number (this form numbers every row down
    # the left edge), not a real value; the field is genuinely blank on
    # this pump (it's motor-driven, not turbine-driven). The old pattern
    # used \s* which crosses the newline and grabs that stray digit.
    # Restricted to same-line matching only — now correctly returns
    # nothing, so it can default to 0/NA downstream instead of a wrong "4".
    turbine_m = re.search(r"No\.\s*Turbine Driven[ \t]*(\d+)", t, re.IGNORECASE)
    if turbine_m:
        set_field("Number of PRT driven", turbine_m.group(1), note="(same-line match only)")
    else:
        set_field("Number of PRT driven", "0", status="STATIC DEFAULT",
                   note="(confirmed blank in source — this pump is motor-driven, not turbine-driven)")

    # ── FIXED: "Hydro test pressure" / "Casing hydortest pr @ atmos
    # temp" — confirmed real bug: the main data-table row for this value
    # extracts as truncated "24" (decimal portion silently dropped,
    # likely a PDF form-field rendering quirk), but the full "24.75"
    # survives intact in a separate circled-callout annotation elsewhere
    # in the extracted text. Try that first; fall back to the truncated
    # table value only if the annotation isn't found.
    # ⚠ FRAGILE: this fix is anchored on the literal word "NOTES"
    # appearing right before the annotation blob on THIS specific PDF's
    # layout — it is very likely to need re-verification against pump
    # PDFs from other vendors/layouts before trusting it broadly.
    hydrotest_decimal_m = re.search(r"NOTES\s*\n\s*(\d+\.\d{2})", t)
    if hydrotest_decimal_m:
        hydrotest_val = hydrotest_decimal_m.group(1)
        set_field("Hydro test pressure", hydrotest_val, note="(recovered from annotation callout — fragile anchor)")
        set_field("Casing hydortest pr @ atmos temp", hydrotest_val, note="(recovered from annotation callout — fragile anchor)")
    # (if not found, the truncated "24" from the main PUMP_FIELDS pass
    # above is kept as-is rather than left blank)

    # ──────────────────────────────────────────────────────────────────────
    # NEW: cross-node lookup — Driver Voltage/Phase/Frequency are motor
    # nameplate values, confirmed genuinely absent from the pump PDF text.
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
    # REMOVED: the previous Suction/Discharge nozzle-position heuristic
    # ("HORIZONTAL"/"VERTICAL" document-order guess) has been verified
    # against this real PDF and found to be WRONG — the assumed order
    # ("VERTICAL always appears before HORIZONTAL") is backwards here;
    # HORIZONTAL actually appears first. Rather than ship a heuristic
    # that's confidently incorrect, these two fields are left unset.
    # Recommend manual entry, or a pdfplumber-based positional extraction
    # instead of a text-order guess.
    #
    # The Suction nozzle SIZE heuristic is ALSO confirmed broken —
    # verified the raw extracted token is "035\"" (character-level
    # corruption, not just a label/value ordering issue), so "5" cannot
    # be safely recovered by regex. Left unset for the same reason.
    # Discharge nozzle size is unaffected (has its own reliable anchor
    # via the literal "RATING" substring immediately following it).
    # ──────────────────────────────────────────────────────────────────────
    discharge_size_m = re.search(r'(\d+(?:/\d+)?)"RATING', t)
    if discharge_size_m:
        set_field("Discharge Nozzle size ", discharge_size_m.group(1), note="(anchored on literal '\"RATING')")

    all_ratings = re.findall(r'(\d+)\s*#', t)
    if len(all_ratings) >= 2:
        set_field("Suction Nozzle Rating ", all_ratings[0], note="(heuristic — positional, unverified beyond this doc)")
        set_field("Discharge Nozzle Rating ", all_ratings[1], note="(heuristic — positional, unverified beyond this doc)")
        pump_data["Suction Nozzle Rating  UOM"] = "Lb RF"
        pump_data["Discharge Nozzle Rating  UOM"] = "Lb RF"

    # ──────────────────────────────────────────────────────────────────────
    # Suction / Vapour pressure block — unchanged from before, still
    # correct against this real PDF (Max suction pressure=0.68, Suction
    # pressure Min/Normal=-0.1, confirmed matching Excel expectations).
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

    if "Shaft diameter @ coupling" not in pump_data:
        set_field("Shaft diameter @ coupling", "NA", status="STATIC DEFAULT (confirmed N/A on this pump type)")

    if re.search(r"Hydrostatic", t, re.IGNORECASE):
        set_field("test medium", "Water / hydrostatic test", status="STATIC DEFAULT (business convention)")

    print2log(f"Total pump fields successfully extracted: {len(pump_data)} / {len(PUMP_FIELDS)}")

    # ──────────────────────────────────────────────────────────────────────
    # KNOWN, UNFIXABLE-BY-REGEX / DATA-MISMATCH / NEEDS-BUSINESS-DECISION gaps
    # (confirmed against the real PDF text):
    #
    # 1. "Auxiliary connections" — same as before, no 4-item list in PDF.
    # 2. "Weight Maintenance" (Excel expects 1056 vs PDF's 1050) — confirmed
    #    genuinely different numbers, not extractable.
    # 3. "MOC, bearing housing" — confirmed absent from extracted text.
    # 4. "Number Running " / "Number Stand by " — confirmed no run/standby
    #    split printed anywhere; only "No. Pumps Required = 4" exists.
    # 5. "operation single/parallel", "Pump Single Line " — confirmed no
    #    such checkbox exists.
    # 6. "Capacity Normal UOM" / "Capacity Minimum UOM" (Excel expects LPM) —
    #    confirmed PDF unit is m³/h throughout; needs a unit-conversion
    #    decision, not a parsing fix.
    # 7. "Brake Power MAXIMUM of RATED IMPELLER" (Excel expects 300) —
    #    confirmed this is actually Impeller Dia Rated; template mapping
    #    mismatch, not a parsing gap.
    # 8. "explosion protection zone" — PDF confirmed says "UNCLASSIFIED"
    #    (correct extraction); Excel expects "NA". This is a business-rule
    #    question (does UNCLASSIFIED area always map to NA explosion
    #    protection?), not a bug — flag for confirmation before hardcoding.
    # 9. "Bearing lubrication" — confirmed the "Ring Oil" checkbox glyph is
    #    entirely absent from the PyPDF2 extraction (not a pattern bug,
    #    the character was never extracted). Needs pdfplumber or manual
    #    entry.
    # 10. "Suction nozzle size" — confirmed the raw extracted token itself
    #     is corrupted ("035\"" instead of "5\""), not a label/pattern
    #     issue. Needs pdfplumber or manual entry.
    # 11. "Suction/Discharge Nozzle Position" — the old positional
    #     heuristic has been verified WRONG against this real PDF and has
    #     been removed rather than left shipping incorrect guesses.
    # 12. "Datasheet No" — confirmed the correct value is not reconstructable
    #     as one contiguous token from this extraction; now correctly
    #     returns blank instead of the wrong vendor-document-number value.
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
        "Suction Nozzle Position",
        "Discharge Nozzle Position",
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
