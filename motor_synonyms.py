import pandas as pd

print2log("===== NODE: Load Motor Field Synonyms (FIXED) =====")

# Matches stray checkbox glyphs (Wingdings/Symbol private-use unicode, e.g.
# U+F06E, U+F0A8) that PyPDF2 leaves in place of what looks like blank
# space around Yes/No checkboxes, plus stray ; or : separators.
CHK = r"[\s\uE000-\uF8FF;:]*"

MOTOR_SYNONYMS = {
    "Tag Name": [(r"Tag No\.\s*(MP-PP\d+-M\d+A/B)", 1)],
    # ── FIXED: real text is "DOCUMENT TITLE:\nApproved.Pump Motor
    # Datasheet for Recycled water pump (10kg/cm2g)" — a page-1 review
    # checkbox label ("Approved.") gets glued onto the front of the real
    # value due to column-scrambled extraction. The pattern itself can't
    # cleanly exclude this (it's not separated by anything regex can
    # anchor on), so Node 3 strips a small known set of these review-
    # status prefixes as a post-processing step after extraction — see
    # the "Tag Description" cleanup block in Node 3.
    "Tag Description": [(r"DOCUMENT TITLE:\s*([^\n]+)", 1)],
    "Site Code": [(r"Program No\s*\n?\s*([A-Z0-9]+)", 1)],
    "Site Name": [(r"PROJECT LOCATION:\s*([^\n]+)", 1)],
    "Plant Code": [(r"Unit No\.\s*\(Plant WBS\).*?-\s*(\d+)\s*-", 1)],
    "Plant Name": [(r"PROJECT TITLE:\s*([^\n]+)", 1)],
    "Manufacture": [(r"Manufacturer:-\s*([^\n]+)", 1)],
    "Model Number": [(r"Model/Cat\.?\s*No\.?\s*:?\s*([^\n]+)", 1)],
    "Serial Number": [(r"(\d{6,}-\d+)-MDS", 1)],
    "Datasheet No": [(r"Doc\.\s*No\.\s*([A-Z0-9\- ]+?)\s*Revision No\.", 1)],
    "Parent tag name": [(r"Tag No\.\s*(MP-PP\d+-M\d+A/B)", 1)],
    "Application ": [(r"Doc\.\s*Name\s+([^\n]+)", 1)],

    "ATEX Category": [],  # NOT IN PDF (confirmed - no such label anywhere in extracted text)

    # ── FIXED: was requiring "Yes" then ";?" then "No" as if adjacent with
    # only whitespace/semicolon between. Real text has a checkbox glyph
    # (U+F0A8 before "Yes", U+F06E before "No") sitting right in that gap.
    "Bearing RTD Required Per Winding": [
        # NOTE: confirmed unreliable — see call-out below. Left in as a
        # best-effort pattern but flag output for manual review; PyPDF2
        # scrambles this specific two-column section's reading order so
        # this may pick up an unrelated label. Do not trust blindly.
        (r"Bearing Temp\.\s*Monitoring:" + CHK + r"Yes" + CHK + r"No.*?RTD's\s*Required:" + CHK + r"(Yes|No)", 1),
    ],

    "Bearing Type DE": [(r"Make\s*&\s*Ref No\.\s*\(DE\):\s*([^\n]+)", 1)],
    "Bearing Type NDE": [(r"Make\s*&\s*Ref No\.\s*\(NDE\):\s*([^\n]+)", 1)],

    "Cable Entry": [(r"TOP\s+(M\d+X[\d.]+P)", 1)],

    # ── FIXED: was requiring literal "Cooling Time Constant" contiguous —
    # PyPDF2 splits this as "C\nooling Time Constant" mid-word. Node 3 now
    # runs dehyphenate() on the text before this ever gets applied, and the
    # pattern itself is loosened as a second layer of safety.
    "Cooling Time Constant": [(r"Cooling\s*Time\s*Constant.*?=\s*(\d+)", 1)],

    # ── FIXED: same "captures to end-of-line, glues on grease info" bug
    # already fixed for the separately-named "Bearing Type DE" field —
    # this is a DIFFERENT Excel column with the same underlying pattern
    # bug, so it needed the identical fix applied here too.
    "DE Bearing": [(r"Make\s*&\s*Ref No\.\s*\(DE\):\s*([A-Za-z0-9/\-]+(?:\s[A-Za-z0-9/\-]+)*?)\s+grease", 1)],
    "DOR": [
        # ── FIXED: reordered. The generic pattern below used to run
        # first (in Node 3's own merge order, base MOTOR_FIELDS didn't
        # have this field so this synonym list's own order decides
        # priority) and matched a boilerplate NOTE sentence ("*Direction
        # of rotation to be as required by driven equipment.*"),
        # capturing the word "to" instead of the real value. This
        # specific, colon-anchored pattern (matches the actual checkbox
        # line "Direction of Rotation:- ... Bi-Dir.") now runs first.
        (r"Direction of Rotation:-.*?(Bi-Dir\.?)", 1),
        (r"Direction of rotation\s+([A-Za-z]+)", 1),  # fallback only
    ],

    "Driver Enclosure": [(r"Degree\s*of\s*Protection\s+(IP\d+)", 1)],

    "Duty": [(r"Duty:-\s*(S1)", 1)],

    "Efficiency": [(r"Efficiency\s+IE2\s*-\s*([\d.]+)\s*%", 1)],

    "Electric Motor Cooling Method": [
        (r"Insulation Class:-\s*(TEFC|TENV|TETC|TEAAC|CACA|CACW|TEWAC|WPI|WPII)", 1),
    ],

    "Exciter Output Current": [],  # NOT IN PDF (confirmed)
    "Exciter Output Voltage": [],  # NOT IN PDF (confirmed)
    "Excitor Amp": [],             # NOT IN PDF (confirmed)
    "Excitor Voltage": [],         # NOT IN PDF (confirmed)

    # ── FIXED: was capturing to end-of-line, gluing on unrelated codes
    # crammed onto the same line by PyPDF2 ("Not ApplicableMT-N23P01-
    # D11NPP-MPP001-TPD-Q-04MP-PP031-M600173A/B"). This value is always
    # either "Not Applicable" or an actual alphanumeric certificate code
    # on this vendor's datasheets, so we match either explicitly and stop
    # there rather than capturing everything to end of line.
    "Explosion Protection Examination Certificate Number": [
        (r"Certificate No\.:-\s*(Not Applicable|[A-Z0-9\-/]+)", 1),
    ],
    "Explosion Protection Notified Body": [(r"Certifying Authority:-\s*([^\n]+)", 1)],
    "Explosion Protection Temperature Class": [(r"Temperature Class:-\s*([^\n]+)", 1)],

    "Frame Size": [(r"Frame\s+([A-Z0-9]+)\s*Rated Output", 1)],

    "Gas Group": [(r"Gas\s*Group.*?([^\n]+)", 1)],

    "Grease Facility": [],  # NOT IN PDF (confirmed)

    "Heating Time Constant": [(r"Heating\s*Time\s*Constant.*?=\s*(\d+)", 1)],

    "Ingress Protection": [(r"Degree\s*of\s*Enclosure\s*Protection.*?(IP\d+)", 1)],

    "Instrumentation Cable": [(r"Heater:-\s*([0-9A-Za-z.,]+Sq,?mm)", 1)],

    "Insulation Class": [(r"([A-Z]\s*\(Temp\.\s*rise limited to class\s*[‘'][A-Z][’']\))", 1)],

    "Locked Rotor Withstand Time (100% Volts) Hot & Cold UOM": [(r"100%\s*Volts.*?Hot.*?[\d.]+\s*(secs)", 1)],
    "Locked Rotor Withstand Time (80% Volts) Hot & Cold UOM": [(r"80%\s*Volts.*?Hot.*?[\d.]+\s*(secs)", 1)],

    # ── FIXED: "Magnetising ... rm = 0.0000416" — old pattern required an
    # exact single "." for the degree symbol slot; real text has "20°C"
    # directly (no gap) here, so it actually worked, but made consistent
    # with the other @20°C patterns for safety with the \s*.?\s*C form.
    "Magnetizing Reactance @ 20°C": [(r"Magnetising\s*Reactance\s*@\s*20\s*.?\s*C\s*Xm\s*=\s*([\d.]+)", 1)],
    "Magnetizing Resistance @ 20°C": [(r"Magnetising\s*Resistance\s*@\s*20\s*.?\s*C\s*rm\s*=\s*([\d.]+)", 1)],

    "Minimum Accelerating Torque (Motor & Load) @ 80%Volts": [
        (r"Minimum Accelerating Torque.*?80%Volts:-\s*([\d.]+)", 1),
    ],
    "Minimum Accelerating Torque (Motor & Load) @ 80%Volts UOM": [
        (r"Minimum Accelerating Torque.*?80%Volts:-\s*[\d.]+\s*(%\s*FLT)", 1),
    ],

    "Motor Greasing Details – Name of Grease ": [(r"grease type\s*([A-Z0-9\-]+)", 1)],

    # ── FIXED: "Type of motor" followed by checkbox glyph U+F06E, not a
    # plain space — \s+ silently failed to match it.
    "Motor Type": [(r"Type of motor" + CHK + r"([A-Za-z ]+[Mm]otor)", 1)],

    "Mounting Arrangement": [(r"Mounting:\s*\*?\s*(B3|B5|V1|V3|Foot|Flange)", 1)],
    "MTB Position": [(r"Terminal box position\s+([A-Z]+)", 1)],
    # ── FIXED: same grease-trim fix as DE Bearing above. Note the real
    # PDF text has a stray internal space in this specific line ("SK F/
    # FAG 6314-C4" instead of "SKF/FAG") — that's a PyPDF2 extraction
    # artifact in the source, not something this regex introduces or can
    # safely "fix" by guessing; flagging it rather than silently altering
    # the extracted text.
    "NDE Bearing": [(r"Make\s*&\s*Ref No\.\s*\(NDE\):\s*([A-Za-z0-9/\-]+(?:\s[A-Za-z0-9/\-]+)*?)\s+grease", 1)],

    "No Load Current": [],       # NOT IN PDF (confirmed)
    "No Load Current UOM": [],   # NOT IN PDF (confirmed)

    "Number of Electrical Phases": [(r"(\d)\s*Ph\b", 1)],
    "Number of Starts Per Hour": [(r"Max\.\s*No\.\s*of\s*Starts\s*in\s*1\s*Hour.*?([\d/]+)", 1)],
    "Power Factor (Starting)": [(r"Power\s*Factor\s*\(Starting\).*?([\d.]+)", 1)],

    "Pull-Out Torque": [(r"Pull[- ]*Out\s*Torque:-\s*([\d.]+)", 1)],
    "Pull-Out Torque UOM": [(r"Pull[- ]*Out\s*Torque:-\s*[\d.]+\s*(%\s*FLT)", 1)],

    "Rated Amp": [(r"Full\s*Load\s*Current\s*\(FLC\):-\s*([\d.]+)", 1)],
    "Rated Amp UOM": [(r"Full\s*Load\s*Current\s*\(FLC\):-\s*[\d.]+\s*(Amps)", 1)],

    "Rated Frequency": [(r"Ph\.\s*(\d+)\s*Hz", 1)],
    "Rated Frequency UOM": [(r"Ph\.\s*\d+\s*(Hz)", 1)],

    "Rated Output Power": [(r"Continuous Rating:-\s*([\d.]+)\s*kW", 1)],
    "Rated Output Power UOM": [(r"Continuous Rating:-\s*[\d.]+\s*(kW)", 1)],

    "Rated Power Factor (Lagging)": [(r"Power\s*Factor\s*\(100/75/50%\).*?([\d.]+)", 1)],

    "Rated Speed": [(r"Speed at Full Load:-\s*([\d.]+)\s*rpm", 1)],
    "Rated Speed UOM": [(r"Speed at Full Load:-\s*[\d.]+\s*(rpm)", 1)],

    "Rated Voltage": [(r"Supply System:\s*(\d+)\s*V", 1), (r"(\d{3})\s*\+-\s*10%", 1)],
    # NOT RELIABLY IN PDF TEXT (confirmed): "415" is extracted completely
    # disconnected from "Supply System:" — a floating textbox pulled out
    # of visual reading order by PyPDF2. Left empty on purpose; apply a
    # static default of "V" at the Excel-write step instead of trusting
    # a regex here — any anchor-based pattern will be unreliable across
    # different vendor PDFs.
    "Rated Voltage UOM": [],

    "Re-Acceleration Scheme (Yes/No)": [],  # NOT IN PDF (confirmed)

    # ── FIXED: no-space "Xr =0.0000036" / "rr=0.0000018" pattern in real
    # text; old pattern required literal " " around "=" plus an exact
    # 1-char wildcard for the degree slot ("20.C") that didn't cover the
    # real "20 °C" (space + degree = 2 chars).
    "Rotor Reactance @ 20°C UOM": [(r"Xr\s*=\s*[\d.]+\s*/\s*[\d.]+\s*(pu)", 1)],
    "Rotor Resistance (Ac) @ 20°C UOM": [(r"rr\s*=\s*[\d.]+\s*/\s*[\d.]+\s*(pu)", 1)],

    # ── FIXED: same checkbox-glyph gap issue as Motor Type/Bearing RTD.
    "RTD Required Per Winding": [(r"Winding Temp\.\s*Monitoring:" + CHK + r"Yes" + CHK + r"(No|Yes)", 1)],

    "Run-Up Time (Motor & Load) (100% Volts) Hot & Cold UOM": [
        (r"Run-Up Time.*?100%\s*Volts.*?Hot.*?[\d.]+\s*(secs)", 1),
    ],
    "Run-Up Time (Motor & Load) (80% Volts) Hot & Cold UOM": [
        (r"80%\s*Volts.*?Hot.*?[\d.]+\s*(secs)\s*Cold", 1),  # FIXED: scoped tighter to avoid matching the 100% block first
    ],

    "Service Factor": [(r"Service\s*Factor:\s*\D*?(\d+)", 1)],
    "Shaft Orientation": [(r"Shaft\s*Orientation\s*\*?\s*(Horizontal|Vertical)", 1)],

    "Size Control Cable": [(r"Heater:-\s*(\d)CX([\d.]+)Sq", 1)],
    "Size Control Cable UOM": [],  # NOT IN PDF as separate field (confirmed)

    "Space Heater": [(r"Heater Rating:-\s*([0-9A-Za-z. ]+Nos\.)", 1)],
    "Space Heater UOM": [],  # NOT IN PDF as "Kw" — PDF unit is Watts, mismatch (confirmed)

    "Starting Current": [(r"Starting Current:-\s*(\d+)\s*%\s*FLC", 1)],
    "Starting Current UOM": [(r"Starting Current:-\s*\d+\s*(%\s*FLC)", 1)],  # NOTE: Excel expects %FLT

    "Starting Method": [(r"Method of starting\s+(Direct On Line)", 1)],

    "Starting Torque": [(r"Starting Torque:-\s*([\d.]+)", 1)],
    "Starting Torque UOM": [(r"Starting Torque:-\s*[\d.]+\s*(%\s*FLT)", 1)],

    # ── NEW: was completely missing before — value and UOM now both present
    "Stator Leakage Reactance @ 20°C": [(r"Stator Leakage Reactance\s*@\s*20\s*.?\s*C\s*X1\s*=\s*([\d.]+)", 1)],
    "Stator Leakage Reactance @ 20°C UOM": [(r"X1\s*=\s*[\d.]+\s*N\.?A\.?\s*(pu)", 1)],

    "Stator Reactance @ 20°C UOM": [(r"Xs\s*=\s*[\d.]+\s*/\s*[\d.]+\s*(pu)", 1)],
    "Stator Resistance (AC) @ 20°C UOM": [(r"rs\s*=\s*[\d.]+\s*/\s*[\d.]+\s*(pu)", 1)],

    "Temperature Ambient UOM": [(r"MAX:-\s*\d+(°C)", 1)],

    "Temperature Rise": [(r"Max\.\s*Permitted Temp Rise:-\s*class\s*.B.\s*(\d+)", 1)],
    # NOT IN PDF TEXT (confirmed): the number "77" is followed directly by
    # "Heater:-" with no unit character anywhere nearby. Apply a static
    # default of "°C" at the Excel-write step instead.
    "Temperature Rise UOM": [],

    # ── FIXED: same checkbox-glyph gap. Also: the unchecked box's "Yes"
    # always appears textually BEFORE the checked box's "No" in this vendor's
    # PDF (confirmed pattern across every checkbox pair on this datasheet),
    # so we must skip past the first "Yes" and capture the second token,
    # exactly like the RTD pattern above — grabbing the first (No|Yes) blindly
    # returns the wrong (unchecked) value.
    "Thermocouples Required Per Winding": [(r"Thermocouples Req\.:" + CHK + r"Yes" + CHK + r"(No|Yes)", 1)],

    "Transportation Weight": [(r"Weight of Motor:-\s*(\d+)\s*kg", 1)],
    "Transportation Weight UOM": [(r"Weight of Motor:-\s*\d+\s*(kg)", 1)],

    "Type of Electrical Current Supply": [],  # NOT IN PDF (confirmed)

    "Type of Painting": [(r"Paint shade\s+([A-Za-z0-9 ]+grey)", 1)],

    "Winding Connection": [(r"Winding\s*connections\s+(Delta|Star)", 1)],

    "Tag Requisition Number": [(r"M\.R\.\s*NO\.:\s*([A-Z0-9\-]+)", 1)],
    "Purchase Order Number": [],  # NOT IN PDF as a single field (confirmed - PO no. and RIL PO no. are two separate fragments, not adjacent)
    "Purchase Order Date": [(r"Date\s*:\s*(\d{2}/\d{2}/\d{4})", 1)],
}

rows = []
skipped_fields = []
for field_key, pattern_list in MOTOR_SYNONYMS.items():
    if not pattern_list:
        skipped_fields.append(field_key)
        continue
    for pattern, order in pattern_list:
        rows.append({"field_key": field_key, "pattern": pattern, "pattern_order": order})

synonyms_df = pd.DataFrame(rows, columns=["field_key", "pattern", "pattern_order"])

print2log(f"Loaded {synonyms_df['field_key'].nunique()} fields with patterns, {len(synonyms_df)} total patterns.")
print2log(f"{len(skipped_fields)} fields flagged as not-in-PDF (no pattern emitted): {skipped_fields}")

output_df = synonyms_df
return output_df
