import pandas as pd

print2log("===== NODE: Load Motor Field Synonyms =====")

MOTOR_SYNONYMS = {
    "Tag Name": [(r"Tag No\.\s*(MP-PP\d+-M\d+A/B)", 1)],
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

    "ATEX Category": [],  # NOT IN PDF

    "Bearing RTD Required Per Winding": [
        (r"Bearing Temp\. Monitoring:.*?RTD's Required:\s*;?\s*(Yes|No)", 1),
    ],  # NOTE: Excel expects "NA", PDF gives "No" — value mismatch, flag for review

    "Bearing Type DE": [(r"Make\s*&\s*Ref No\.\s*\(DE\):\s*([^\n]+)", 1)],
    "Bearing Type NDE": [(r"Make\s*&\s*Ref No\.\s*\(NDE\):\s*([^\n]+)", 1)],

    "Cable Entry": [(r"TOP\s+(M\d+X[\d.]+P)", 1)],

    "Cooling Time Constant": [(r"Cooling Time Constant:-\s*=\s*(\d+)", 1)],

    "DE Bearing": [(r"Make\s*&\s*Ref No\.\s*\(DE\):\s*([^\n]+)", 1)],
    "DOR": [
        (r"Direction of rotation\s+([A-Za-z]+)", 1),
        (r"Direction of Rotation:-.*?(Bi-Dir\.?)", 2),
    ],

    "Driver Enclosure": [(r"Degree\s*of\s*Protection\s+(IP\d+)", 1)],

    "Duty": [(r"Duty:-\s*(S1)", 1)],

    "Efficiency": [(r"Efficiency\s+IE2\s*-\s*([\d.]+)\s*%", 1)],

    "Electric Motor Cooling Method": [
        (r"Insulation Class:-\s*(TEFC|TENV|TETC|TEAAC|CACA|CACW|TEWAC|WPI|WPII)", 1),
    ],

    "Exciter Output Current": [],  # NOT IN PDF
    "Exciter Output Voltage": [],  # NOT IN PDF
    "Excitor Amp": [],             # NOT IN PDF
    "Excitor Voltage": [],         # NOT IN PDF

    "Explosion Protection Examination Certificate Number": [(r"Certificate No\.:-\s*([^\n]+)", 1)],
    "Explosion Protection Notified Body": [(r"Certifying Authority:-\s*([^\n]+)", 1)],
    "Explosion Protection Temperature Class": [(r"Temperature Class:-\s*([^\n]+)", 1)],

    "Frame Size": [(r"Frame\s+([A-Z0-9]+)\s*Rated Output", 1)],

    "Gas Group": [(r"Gas\s*Group.*?([^\n]+)", 1)],

    "Grease Facility": [],  # NOT IN PDF

    "Heating Time Constant": [(r"Heating\s*Time\s*Constant.*?=\s*(\d+)", 1)],

    "Ingress Protection": [(r"Degree\s*of\s*Enclosure\s*Protection.*?(IP\d+)", 1)],

    "Instrumentation Cable": [(r"Heater:-\s*([0-9A-Za-z.,]+Sq,?mm)", 1)],

    "Insulation Class": [(r"([A-Z]\s*\(Temp\.\s*rise limited to class\s*[‘'][A-Z][’']\))", 1)],

    "Locked Rotor Withstand Time (100% Volts) Hot & Cold UOM": [(r"100%\s*Volts.*?Hot.*?[\d.]+\s*(secs)", 1)],
    "Locked Rotor Withstand Time (80% Volts) Hot & Cold UOM": [(r"80%\s*Volts.*?Hot.*?[\d.]+\s*(secs)", 1)],

    "Magnetizing Reactance @ 20°C": [(r"Magnetising Reactance @ 20.C Xm = ([\d.]+)", 1)],
    "Magnetizing Resistance @ 20°C": [(r"Magnetising Resistance @ 20.C rm = ([\d.]+)", 1)],

    "Minimum Accelerating Torque (Motor & Load) @ 80%Volts": [
        (r"Minimum Accelerating Torque.*?80%Volts:-\s*([\d.]+)", 1),
    ],
    "Minimum Accelerating Torque (Motor & Load) @ 80%Volts UOM": [
        (r"Minimum Accelerating Torque.*?80%Volts:-\s*[\d.]+\s*(%\s*FLT)", 1),
    ],

    "Motor Greasing Details – Name of Grease ": [(r"grease type\s*([A-Z0-9\-]+)", 1)],
    "Motor Type": [(r"Type of motor\s+([A-Za-z ]+[Mm]otor)", 1)],
    "Mounting Arrangement": [(r"Mounting:\s*\*?\s*(B3|B5|V1|V3|Foot|Flange)", 1)],
    "MTB Position": [(r"Terminal box position\s+([A-Z]+)", 1)],
    "NDE Bearing": [(r"Make\s*&\s*Ref No\.\s*\(NDE\):\s*([^\n]+)", 1)],

    "No Load Current": [],       # NOT IN PDF
    "No Load Current UOM": [],   # NOT IN PDF

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

    "Rated Voltage": [(r"Supply System:\s*(\d+)\s*V", 1)],
    "Rated Voltage UOM": [(r"Supply System:\s*\d+\s*(V)\s*\+", 1)],

    "Re-Acceleration Scheme (Yes/No)": [],  # NOT IN PDF

    "Rotor Reactance @ 20°C UOM": [(r"Rotor Reactance @ 20.C Xr = [\d.]+\s*/\s*[\d.]+\s*(pu)", 1)],
    "Rotor Resistance (Ac) @ 20°C UOM": [(r"Rotor Resistance\(ac\) @ 20.C rr = [\d.]+\s*/\s*[\d.]+\s*(pu)", 1)],

    "RTD Required Per Winding": [(r"Winding Temp\. Monitoring:.*?RTD's Required:\s*;?\s*(No|Yes)", 1)],

    "Run-Up Time (Motor & Load) (100% Volts) Hot & Cold UOM": [
        (r"Run-Up Time.*?100%\s*Volts.*?Hot.*?[\d.]+\s*(secs)", 1),
    ],
    "Run-Up Time (Motor & Load) (80% Volts) Hot & Cold UOM": [
        (r"Run-Up Time.*?80%\s*Volts.*?Hot.*?[\d.]+\s*(secs)", 1),
    ],

    "Service Factor": [(r"Service\s*Factor:\s*\D*?(\d+)", 1)],
    "Shaft Orientation": [(r"Shaft\s*Orientation\s*\*?\s*(Horizontal|Vertical)", 1)],

    "Size Control Cable": [(r"Heater:-\s*(\d)CX([\d.]+)Sq", 1)],
    "Size Control Cable UOM": [],  # NOT IN PDF as separate field

    "Space Heater": [(r"Heater Rating:-\s*([0-9A-Za-z. ]+Nos\.)", 1)],
    "Space Heater UOM": [],  # NOT IN PDF as "Kw" — PDF unit is Watts, mismatch

    "Starting Current": [(r"Starting Current:-\s*(\d+)\s*%\s*FLC", 1)],
    "Starting Current UOM": [(r"Starting Current:-\s*\d+\s*(%\s*FLC)", 1)],  # NOTE: Excel expects %FLT

    "Starting Method": [(r"Method of starting\s+(Direct On Line)", 1)],

    "Starting Torque": [(r"Starting Torque:-\s*([\d.]+)", 1)],
    "Starting Torque UOM": [(r"Starting Torque:-\s*[\d.]+\s*(%\s*FLT)", 1)],

    "Stator Leakage Reactance @ 20°C": [(r"Stator Leakage Reactance @ 20.C X1 = ([\d.]+)", 1)],
    "Stator Leakage Reactance @ 20°C UOM": [(r"Stator Leakage Reactance @ 20.C X1 = [\d.]+\s*N\.A\s*(pu)", 1)],

    "Stator Reactance @ 20°C UOM": [(r"Stator Reactance @ 20.C Xs = [\d.]+\s*/\s*[\d.]+\s*(pu)", 1)],
    "Stator Resistance (AC) @ 20°C UOM": [(r"Stator Resistance\(ac\) @ 20.C rs = [\d.]+\s*/\s*[\d.]+\s*(pu)", 1)],

    # NOTE: "Temperature Ambient" (the value, not UOM) is deliberately NOT here —
    # it needs 3 capture groups combined into "Max {} / Min {} / Design {}",
    # which this flat single-group table can't express. Handle it directly
    # in Node 3 via find_value_combined() instead — see snippet below.
    "Temperature Ambient UOM": [(r"MAX:-\s*\d+(°C)", 1)],

    "Temperature Rise": [(r"Max\.\s*Permitted Temp Rise:-\s*class\s*.B.\s*(\d+)", 1)],
    "Temperature Rise UOM": [(r"Max\.\s*Permitted Temp Rise:-\s*class\s*.B.\s*\d+\s*(°?C)", 1)],

    "Thermocouples Required Per Winding": [(r"Winding Temp\. Monitoring:.*?Thermocouples Req\.:\s*;?\s*(No|Yes)", 1)],

    "Transportation Weight": [(r"Weight of Motor:-\s*(\d+)\s*kg", 1)],
    "Transportation Weight UOM": [(r"Weight of Motor:-\s*\d+\s*(kg)", 1)],

    "Type of Electrical Current Supply": [],  # NOT IN PDF

    "Type of Painting": [(r"Paint shade\s+([A-Za-z0-9 ]+grey)", 1)],

    "Winding Connection": [(r"Winding\s*connections\s+(Delta|Star)", 1)],

    "Tag Requisition Number": [(r"M\.R\.\s*NO\.:\s*([A-Z0-9\-]+)", 1)],
    "Purchase Order Number": [],  # NOT IN PDF
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