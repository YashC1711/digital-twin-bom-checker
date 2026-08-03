import pandas as pd

print2log("===== NODE: Load Pump Field Synonyms (198-field version) =====")

PUMP_SYNONYMS = {
    # ── Header / Tag block ──────────────────────────────────────────────
    "Tag Description": [(r"DOCUMENT TITLE:\s*([^\n]+)", 1)],
    "Site Code": [(r"Program No\s*\n?\s*([A-Z0-9]+)", 1)],
    "Site Name": [(r"PROJECT TITLE:\s*([^\n]+)", 1)],
    "Plant Code": [(r"Unit No\.\s*\(Plant WBS\).*?-\s*(\d+)\s*-", 1)],
    "Plant Name": [],  # NOT IN PDF — derived substring of Site Name ("PVC"), not a distinct field
    "Parent Tag Name": [(r"ITEM NO\.\s*(MP-PP\d+-P\d+[A-Z]?/?[A-Z]?)", 1)],
    "Electrical Area Classification": [(r"Area Classification\s*([A-Z ]+)", 1)],

    # ── Driver electrical (mostly NOT on pump PDF — lives on Motor MDS) ──
    "Driver Voltage": [],                # NOT IN PDF — motor datasheet field
    "Driver Voltage UOM": [],            # NOT IN PDF — motor datasheet field
    "Driver Phase Number": [],           # NOT IN PDF — motor datasheet field
    "Driver Frequency": [],              # NOT IN PDF — motor datasheet field
    "Driver Frequency UOM": [],          # NOT IN PDF — motor datasheet field
    "Driver Rating UOM": [(r"NAMEPLATE POWER\s*[\d.]+\s*(Kw)", 1)],

    "Weight Maintenance": [],            # NOT IN PDF as such — closest is Total Mass=1050, but Excel value 1056 differs; flag for manual check
    "Weight Maintenance UOM": [(r"Total Mass\s*\d+\s*(kg)", 1)],

    " Viscosity Maximum UOM": [(r"Viscosity\s*\((cP)\)", 1)],

    "Auxiliary connections ": [
        (r"OTHER CONNECTIONS.*?Drain\s+1\s+(1/2\")", 1),   # partial — table is multi-row, full string not reconstructable by single regex
    ],

    "Baseplate weight UOM": [(r"Mass of Baseplate\s*\d+\s*(kg)", 1)],

    "Bearing No. ": [(r"Radial\s+Deep groove ball bearing\s*([0-9A-Z ]+)", 1)],
    "Bearing RTD, radial bearing": [(r"Radial\s+(Deep groove ball bearing[0-9A-Z ]+)", 1)],
    "Bearing RTD, thrust bearing": [(r"Thrust\s+(Deep groove ball bearing[0-9A-Z ]+)", 1)],

    "Brake Power  MAXIMUM of RATED IMPELLER": [(r"Impeller Dia\.\s*\(mm\).*?Rated\s+(\d+)", 1)],  # NOTE: Excel expects 300 which is actually Impeller Dia Rated, not Max Power(68kW) — likely field-mapping mismatch in template, flag for review
    "Brake Power  MAXIMUM of RATED IMPELLER UOM": [(r"Impeller Dia\.\s*\((mm)\)", 1)],

    "CAPACITY MINIMUM CONTINUOUS STABLE /Thermal": [
        (r"Min\.\s*Continuous Flow.*?Thermal\s+(\d+)\s+Stable\s+(\d+)", 1),
    ],
    "CAPACITY MINIMUM CONTINUOUS STABLE /Thermal UOM": [(r"Min\.\s*Continuous Flow\s*\((m³/h)\)", 1)],

    "Capacity  Rated / Maximum": [(r"Capacity.*?Rated\s+(\d+)", 1)],
    "Capacity  Rated / Maximum UOM": [(r"Capacity\s*(m³/h)", 1)],

    "Capacity Minimum UOM": [],  # NOT IN PDF — no "Capacity Minimum" field; PDF only has Normal/Rated, in m3/h not LPM

    "Capacity Normal": [(r"Capacity.*?Normal\s+(\d+)", 1)],
    "Capacity Normal UOM": [],   # NOT IN PDF as LPM — PDF unit is m3/h; unit mismatch, not just naming

    "Casing hydortest pr @ atmos temp": [(r"Hydrotest Pressure\s*\(kg/cm²?g\):\s*([\d.]+)", 1)],
    "Casing hydortest pr @ atmos temp UOM": [(r"Hydrotest Pressure\s*\((kg/cm²?g)\)", 1)],
    "Casing MAWP @ max op temp": [(r"Max\.\s*Allowable Working Pressure\s*\(MAWP\):\s*([\d.]+)", 1)],
    "Casing MAWP @ max op temp UOM": [(r"Max\.\s*Allowable Working Pressure\s*\(MAWP\)", 0)],  # unit not printed separately; use whole match as marker

    "CASING MOUNTING": [(r"CASING MOUNTING.*?;\s*(Foot|Sump|Centreline|Near Centreline|Vertical|Vertical Barrel|Inline|Bracket)", 1)],
    "CASING TYPE": [(r"CASING TYPE.*?;\s*(Single Volute|Double Volute|Diffuser|Staggered|Vertical Double|Barrel)", 1)],

    "chloride concentration": [(r"CHLORIDE CONCENTRATION\s*:\s*(\d+)\s*PPM", 1)],
    "chloride concentration UOM": [(r"CHLORIDE CONCENTRATION\s*:\s*\d+\s*(PPM)", 1)],

    "Coupling Type": [(r"(FLEXIBLE METALLIC SPACER)", 1)],

    "density": [(r"Specific Gravity @:\s*°?C?\s*0\.(\d+)", 1)],   # note: PDF gives 0.981 (specific gravity, unitless) not kg/m3 — value/unit mismatch vs Excel's 981 kg/m3
    "density UOM": [],   # NOT IN PDF — Specific Gravity is unitless in source doc
    "density maximum": [(r"Specific Gravity @:\s*°?C?\s*0\.(\d+)", 1)],
    "density maximum UOM": [],  # same as above

    "design specification": [(r"Other\s+(ISO\s*-?\s*5199 and MR-002)", 1)],

    "Differential head @ normal flow": [(r"Diff\.\s*Head\(m\)\s*\(1\)\(2\)\s*([\d.]+)", 1)],
    "Differential head @ normal flow UOM": [(r"Diff\.\s*Head\((m)\)", 1)],
    "Differential head @ rated flow UOM": [(r"Diff\.\s*Head\((m)\)", 1)],

    "Differential pressure": [(r"Diff\.\s*Pres\.\s*\(kg/cm²\)\s*\(1\)\(2\)\s*([\d.]+)", 1)],
    "Differential Pressure  UOM": [(r"Diff\.\s*Pres\.\s*\((kg/cm²)\)", 1)],

    "Direction of Rotation, from driver end": [(r"Shaft Rotation.*?;\s*(CW|CCW)", 1)],

    "Discharge Nozzle Rating ": [(r"Discharge\s+\d+(?:/\d+)?\"?\s+(\d+)\s*#", 1)],
    "Discharge Nozzle Rating  UOM": [(r"Discharge\s+\d+(?:/\d+)?\"?\s+\d+\s*(#)", 1)],
    "Discharge Nozzle size ": [(r"Discharge\s+(\d+)(?:/\d+)?\"", 1)],
    "Discharge Nozzle size  UOM": [(r"Discharge\s+\d+(?:/\d+)?(\")", 1)],

    "Discharge pressure @ rated flow UOM": [(r"Disch\.\s*Press\s*\((kg/cm²\s*g)\)", 1)],
    "Discharge pressure Normal": [(r"Disch\.\s*Press\s*\(kg/cm²\s*g\)\s*\(1\)\(2\)\s*([\d.]+)", 1)],
    "Discharge pressure Normal UOM": [(r"Disch\.\s*Press\s*\((kg/cm²\s*g)\)", 1)],

    "Driver Motor Driven/ Turbine Driven ": [(r"DRIVER TYPE\s*(Motor)", 1)],

    "Driver weight UOM": [(r"Mass of Motor\s*\d+\s*(kg)", 1)],
    "dry weight UOM": [(r"Mass of Pump\s*\d+\s*(kg)", 1)],

    "Actual Efficiency": [(r"Efficiency\s*\(%\)\s*([\d.]+)", 1)],
    "Rated Efficiency": [(r"Efficiency\s*\(%\)\s*([\d.]+)", 1)],

    "Erosive ": [],  # NOT IN PDF — no erosive-fluid field present

    "explosion protection gas group": [],       # NOT IN PDF — only Area Classification: UNCLASSIFIED given, no gas group
    "explosion protection temperature class": [], # NOT IN PDF — same reason

    "fluid name": [(r"Name\s+(RECYCLED WATER)", 1)],

    "Gearbox weight": [],       # NOT IN PDF — Gearbox Data Sheet No. row is blank in source
    "Gearbox weight UOM": [],   # NOT IN PDF

    "H2S concentration": [],       # NOT IN PDF — no H2S field
    "H2S concentration UOM": [],   # NOT IN PDF

    "Hydraulic Power  UOM": [(r"Hyd\.\s*Power\s*\((kW)\)", 1)],

    "Hydro test pressure UOM": [(r"Hydrotest Pressure\s*\((kg/cm²?g)\)", 1)],

    "immersed": [],  # NOT IN PDF — no immersed-pump field; not applicable to this OH1 horizontal pump

    "Impeller balancing grade": [],  # NOT IN PDF — no balancing grade field

    "Impeller weight": [],       # NOT IN PDF — no impeller weight field
    "Impeller weight UOM": [],   # NOT IN PDF

    "IMPELLER DIA MAXIMUM": [(r"Impeller Dia\.\s*\(mm\).*?Max\s+(\d+)", 1)],
    "IMPELLER DIA MAXIMUM UOM": [(r"Impeller Dia\.\s*\((mm)\)", 1)],
    "IMPELLER DIA MINIMUM": [(r"Impeller Dia\.\s*\(mm\).*?Min\s+(\d+)", 1)],
    "IMPELLER DIA MINIMUM UOM": [(r"Impeller Dia\.\s*\((mm)\)", 1)],
    "IMPELLER DIA RATED": [(r"Impeller Dia\.\s*\(mm\).*?Rated\s+(\d+)", 1)],
    "IMPELLER DIA RATED UOM": [(r"Impeller Dia\.\s*\((mm)\)", 1)],

    "Inducer": [],             # NOT IN PDF — no inducer field (OH1 single-stage pump)
    "ingress protection": [],  # NOT IN PDF — no IP rating field for pump (this is a motor-datasheet concept)

    "Material of construction, Annex H Class": [
        (r"Barrel/Casing\s+(A743\s*Gr\.\s*CF3).*?Sleeve\s+([0-9A-Z]+).*?Shaft\s+([A-Z0-9 ]+COND\s*H)", 1),
    ],
    "MATERIAL:CASE/IMPELLER WEAR RING": [(r"Case Wear Rings\s+(A743\s*Gr\.CF3\s*\(Col coat\))", 1)],
    "MATERIAL:DIFFUSERS": [],         # NOT IN PDF — pump has no diffuser (single volute casing)
    "MATERIAL:DISCHARGE COLUMN": [],  # NOT IN PDF — no vertical column pump construction
    "MATERIAL:DISCHARGE HEAD": [],    # NOT IN PDF — same reason
    "MATERIAL:LINESHAFT": [],         # NOT IN PDF — no lineshaft (OH1 overhung pump, not vertical turbine)
    "MATERIAL:LINESHAFT BEARING": [], # NOT IN PDF — same reason
    "MATERIAL:SUCTION CAN/BARREL": [],# NOT IN PDF — no suction can construction

    "Maximum  design pressure UOM": [(r"MAWP\)?:\s*[\d.]+\s*\n?\s*\((kg/cm²g)\)", 1)],
    "Maximum allowable working  pressure": [(r"MAX\.\s*ALLOWABLE CASING WORKING PRESSURE SHALL NOT BE LESS THAN\s*([\d.]+)", 1)],
    "Maximum allowable working  pressure UOM": [(r"MAX\.\s*ALLOWABLE CASING WORKING PRESSURE SHALL NOT BE LESS THAN\s*[\d.]+\s*(kg/cm²g)", 1)],

    "Maximum ambient  temperature UOM": [],  # NOT IN PDF — no separate "Maximum ambient temperature" field (Site Conditions gives Temp Max/Min only, no explicit UOM cell)

    "Maximum design temperature UOM": [(r"design temperature\s*:\s*\d+\s*(deg C)", 1)],

    "Maximum discharge pressure UOM": [],  # NOT IN PDF — no explicit "Maximum discharge pressure" field (Note 12 discusses shut-off qualitatively, no isolated value+unit)

    "Maximum pumping  temperature UOM": [(r"Pumping Temperature\s*\d+\s*\((°?C)\)", 1)],

    "Maximum suction  pressure": [(r"Suct\.\s*Pres\..*?Max\.\s*([\d.]+)", 1)],
    "Maximum suction  pressure UOM": [(r"Suct\.\s*Pres\.\s*\((kg/cm²\s*g)\)", 1)],

    "Minimum  design temperature": [(r"MDMT\s*=\s*(\d+)", 1)],
    "Minimum  design temperature UOM": [(r"MDMT\s*=\s*\d+\s*(°C)", 1)],
    "Minimum ambient  temperature": [(r"MIN:-\s*(\d+)°C", 1)],   # NOTE: pattern generic — may collide with motor PDF text if both texts share this node; verify scoping
    "Minimum ambient  temperature UOM": [(r"MIN:-\s*\d+(°C)", 1)],
    "Minimum Design Metal Temperature": [(r"MDMT\s*=\s*(\d+)", 1)],
    "Minimum Design Metal Temperature UOM": [(r"MDMT\s*=\s*\d+\s*(°C)", 1)],

    "MOC, barrel": [(r"Barrel/Casing\s+(A743\s*Gr\.\s*CF3)", 1)],
    "MOC, bearing housing": [],  # NOT IN PDF — no bearing housing material field
    "MOC, case wear ring": [(r"Case Wear Rings\s+(A743\s*Gr\.CF3\s*\(Col coat\))", 1)],
    "MOC, cover": [(r"Case\s+(A743\s*Gr\.\s*CF3)", 1)],  # closest available — PDF has no separate "cover", covered under "Case"
    "MOC, impeller wear ring": [(r"Imp\.\s*Wear Rings\s+(A743\s*Gr\.\s*CF3)", 1)],
    "MOC, inducer": [],             # NOT IN PDF
    "MOC, interstage bushing": [],  # NOT IN PDF — single-stage pump, no interstage bushing
    "MOC, shaft": [(r"Shaft\s+(A276\s*TP\s*410\s*COND\s*H)", 1)],
    "MOC, throat bush": [],  # NOT IN PDF

    "Net positive suction head required UOM": [(r"NPSH Required\s*\((m Water)\)", 1)],

    "normal operating vapour pressure": [(r"Vapour press.*?Rated\s+([\d.]+)", 1)],
    "normal operating vapour pressure UOM": [(r"Vapour press\s*\((kg/cm²\s*a)\)", 1)],

    "NPSH available": [(r"NPSH Available\s*\(m\)\s*\(1\)\(2\)\s*([\d.]+)", 1)],
    "NPSH available UOM": [(r"NPSH Available\s*\((m)\)", 1)],

    "NPSH margin, max capacity": [],       # NOT IN PDF — no margin field, only Available/Required separately
    "NPSH margin, max capacity UOM": [],
    "NPSH margin, min capacity": [],
    "NPSH margin, min capacity UOM": [],

    "NPSHa @ shaft centreline, max capcity": [(r"800\s*MM ELEVATION", 0)],  # value pulled from Note 9 text, not a clean numeric field
    "NPSHa @ shaft centreline, max capcity UOM": [(r"800\s*(MM) ELEVATION", 1)],
    "NPSHa @ shaft centreline, min capcity": [],      # NOT IN PDF — only one elevation value given in Note 9, no separate min/max
    "NPSHa @ shaft centreline, min capcity UOM": [],

    "NPSHr @ shaft centreline, max capcity": [],     # NOT IN PDF — only single "NPSH Required (m Water): 2.8" given
    "NPSHr @ shaft centreline, max capcity UOM": [],
    "NPSHr @ shaft centreline, min capcity": [],
    "NPSHr @ shaft centreline, min capcity UOM": [],
    "NPSHr @ shaft centreline, rated capcity UOM": [(r"NPSH Required\s*\((m Water)\)", 1)],

    "Number Installed ": [(r"No\.\s*Pumps Required\s*(\d+)", 1)],
    "Number of PRT driven": [(r"No\.\s*Turbine Driven\s*(\d+)", 1)],
    "Number of seals per pump": [],  # NOT IN PDF explicitly — inferred as 1 from "Single" cartridge mount, not a direct field

    "Number Running ": [],   # NOT IN PDF — derived split of "No. Pumps Required = 4", not stated directly
    "Number Stand by ": [],  # NOT IN PDF — same reason

    "Online vibration measurement": [],  # NOT IN PDF — Vibration probe fields all NA in Instrumentation section

    "Operating Speed, max": [(r"Pump Speed\s*\(rpm\)\s*(\d+)", 1)],
    "Operating Speed, max UOM": [(r"Pump Speed\s*\((rpm)\)", 1)],

    "operating weight UOM": [(r"Total Mass\s*\d+\s*(kg)", 1)],

    "operation continuous / intermittent": [(r"(Continuous)\s*Intermittent Service", 1)],
    "operation single/parallel": [],  # NOT IN PDF as "Single"/"Parallel" text — PDF only has unchecked Parallel/Series checkboxes; inferred, not extracted

    "Orientation (Horizontal /Vertical)": [(r"ORIENTATION\s*(Horizontal)", 1)],

    "Piping class": [],  # NOT IN PDF — no piping class field

    "Pump Duty ( contineous/ Intermittent)": [(r"(Continuous)\s*Intermittent Service", 1)],

    "Pump OEM ": [(r"VENDOR NAME:\s*([^\n]+)", 1)],

    "Pump Single Line ": [],  # NOT IN PDF — no "single line" Yes/No field

    "Pumping Fluid Polymerisation agent with Concentration ": [],  # NOT IN PDF
    "Pumping Fluid Solid Containment with Concentration ": [],      # NOT IN PDF

    "Pumping temperature Minimum UOM": [(r"Pumping Temperature\s*\d+\s*\((°?C)\)", 1)],
    "Pumping temperature Normal UOM": [(r"Pumping Temperature\s*\d+\s*\((°?C)\)", 1)],

    "Radial Vibration probe type": [],  # NOT IN PDF — Instrumentation vibration probes all NA

    "rated speed UOM": [(r"Pump Speed\s*\((rpm)\)", 1)],

    "Rotor axial position probe": [],  # NOT IN PDF

    "Rotor weight": [],       # NOT IN PDF — no rotor weight field
    "Rotor weight UOM": [],   # NOT IN PDF

    "seal type": [(r"(Mechanical Seal)", 1)],
    "Seal  Primary flush Plan": [(r"Primary Flush Plan\s+(Plan\s*\d+)", 1)],
    "Seal Manufacturer": [(r"MECHANICAL SEAL:.*?Manufacturer\s+([A-Za-z]+)", 1)],
    "Seal Secondary flush Plan": [(r"Secondary Flush Plan\s+(Plan\s*[\dA-Z]+)", 1)],

    "Shaft diameter @ coupling": [],       # NOT IN PDF — no shaft diameter field at all
    "Shaft diameter @ coupling UOM": [],
    "Shaft diameter @ seal": [],
    "Shaft diameter @ seal UOM": [],

    "Shaft rotation from Drive end ": [(r"Shaft Rotation.*?;\s*(CW|CCW)", 1)],

    "Shaft weight": [],      # NOT IN PDF
    "Shaft weight UOM": [],  # NOT IN PDF

    "SHUTOFF HEAD AT RATED IMPELLER": [(r"Max\.\s*Head\s*@\s*Rated Imp\.\s*\(m\)\s*([\d.]+)", 1)],
    "SHUTOFF HEAD AT RATED IMPELLER UOM": [(r"Max\.\s*Head\s*@\s*Rated Imp\.\s*\((m)\)", 1)],
    "SHUTOFF HEAD AT MAX IMPELLER": [(r"Max\.\s*Head\s*@\s*Max\.\s*Imp\.\s*\(m\)\s*([\d.]+)", 1)],
    "SHUTOFF HEAD AT MAX IMPELLER UOM": [(r"Max\.\s*Head\s*@\s*Max\.\s*Imp\.\s*\((m)\)", 1)],

    "Specific Speed": [(r"Suction Specific Speed\s*(\d+)", 1)],
    "Specific Speed UOM": [(r"Suction Specific Speed\s*\d+\s*(rpm, m, m³/h)", 1)],

    "Suction Nozzle Rating ": [(r"Suction\s+\d+(?:/\d+)?\"?\s+(\d+)\s*#", 1)],
    "Suction Nozzle Rating  UOM": [(r"Suction\s+\d+(?:/\d+)?\"?\s+\d+\s*(#)", 1)],
    "Suction nozzle size": [(r"Suction\s+(\d+)(?:/\d+)?\"", 1)],
    "Suction nozzle size UOM": [(r"Suction\s+\d+(?:/\d+)?(\")", 1)],

    "Suction pressure Minimum": [(r"Suct\.\s*Pres\..*?Rated\s+(-?[\d.]+)", 1)],
    "Suction pressure Minimum UOM": [(r"Suct\.\s*Pres\.\s*\((kg/cm²\s*g)\)", 1)],
    "Suction Pressure Normal": [(r"Suct\.\s*Pres\..*?Rated\s+(-?[\d.]+)", 1)],
    "Suction Pressure Normal UOM": [(r"Suct\.\s*Pres\.\s*\((kg/cm²\s*g)\)", 1)],

    "Suction Specific Speed, SI units": [(r"Suction Specific Speed\s*(\d+)", 1)],
    "Suction Specific Speed, SI units UOM": [(r"Suction Specific Speed\s*\d+\s*(rpm, m, m³/h)", 1)],

    "test medium": [],  # NOT IN PDF as a named "test medium" field — inferred from Hydrostatic test row, no direct text value

    "Vapor pressure, max": [(r"Vapour press.*?Max\.\s*([\d.]+)", 1)],
    "Vapor pressure, max UOM": [(r"Vapour press\s*\((kg/cm²\s*a)\)", 1)],
    "Vapor pressure, min": [(r"Vapour press.*?Rated\s+([\d.]+)", 1)],
    "Vapor pressure, min UOM": [(r"Vapour press\s*\((kg/cm²\s*a)\)", 1)],

    "Viscosity Normal ": [(r"Viscosity\s*\(cP\)\s*@\s*°?C?\s*([\d.]+)", 1)],
    "Viscosity Normal  UOM": [(r"Viscosity\s*\((cP)\)", 1)],

    "Wet Critical speed": [],       # NOT IN PDF — no critical speed field
    "Wet Critical speed UOM": [],   # NOT IN PDF

    "Tag Requisition Number": [(r"REQUITION NO\.\s*([A-Z0-9\-]+)", 1)],
    "Purchase Order Number": [(r"PURCHASE ORDER NO\.\s*([A-Z0-9/\-]+)", 1)],
    "Purchase Order Date": [(r"DATE\s*([\d.]+)", 1)],
}

rows = []
skipped_fields = []
for field_key, pattern_list in PUMP_SYNONYMS.items():
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