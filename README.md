# Digital Twin – AI Based BOM Checker

## Overview

This workflow is developed using **Rubiscape Workflow Designer** and implemented using **RubPython Nodes**.

The purpose of this workflow is to:

1. Identify Motor and Pump Datasheet PDFs from the input directory.
2. Extract text from the PDFs.
3. Parse Motor Datasheet (MDS) information using regex-based extraction.
4. Parse Pump Datasheet (PDS) information using regex-based extraction.
5. Populate the extracted values into predefined Excel templates.
6. Save the updated Excel files in the output directory.

---

# Workflow Information

### Platform
- Rubiscape Workflow
- RubPython Nodes

### Workflow Name
Digital Twin – AI Based BOM Checker

### Processing Type
PDF → Text Extraction → Data Parsing → Excel Population

---

# External Variables

The workflow uses the following external variables:

| Variable Name | Value |
|--------------|---------|
| input_path | `/data/ksb_storage/AI_Based_BOM_Checker/Digital_Twin_Reliance_Copy/input` |
| output_path | `/data/ksb_storage/AI_Based_BOM_Checker/Digital_Twin_Reliance_Copy/output` |

---

# Expected Input Files

## PDF Files

The workflow identifies PDFs based on filename conventions.

### Motor Datasheet
Filename must contain:

```text
MDS
```

Example:

```text
Motor data sheet_9975641119-100 MDS Code1.pdf
```

### Pump Datasheet
Filename must contain:

```text
PDS
```

Example:

```text
Pump data sheet_9975641119-PDS-100 Code1.pdf
```

---

# Expected Output Excel Files

The workflow identifies Excel files based on filename conventions.

### Motor Template

Filename must contain:

```text
motor
```

Example:

```text
EA001-Motor.xlsx
```

### Pump Template

Filename must contain:

```text
pump
```

Example:

```text
MR009-Centrifugal pump.xlsx
```

---

# Workflow Sequence

## Node 1 – Setup_and_File_Classification

### Purpose

Performs initial setup and classifies all required files.

### Activities

- Reads external variables:
  - `input_path`
  - `output_path`
- Validates directory existence.
- Scans input directory for PDF files.
- Identifies:
  - Motor Datasheet PDF (MDS)
  - Pump Datasheet PDF (PDS)
- Scans output directory for Excel files.
- Identifies:
  - Motor Excel Template
  - Pump Excel Template
- Creates output dataframe containing file paths.

### Output Columns

| Column |
|----------|
| motor_pdf_path |
| pump_pdf_path |
| motor_xlsx_path |
| pump_xlsx_path |

---

## Node 2 – Extract_PDF_Text

### Purpose

Extracts text from Motor and Pump PDF files.

### Library Used

```python
PyPDF2
```

### Activities

- Reads file paths received from Node 1.
- Opens PDFs using `PdfReader`.
- Extracts text page by page.
- Concatenates all page text.
- Stores extracted text for downstream parsing.

### Output Columns Added

| Column |
|----------|
| motor_pdf_text |
| pump_pdf_text |

---

## Node 3 – Parse_Motor_Data_MDS

### Purpose

Parses Motor Datasheet information from extracted PDF text.

### Method

Regex-based field extraction.

### Major Fields Extracted

Examples include:

- Tag Name
- Manufacturer
- Datasheet Number
- Frame Size
- Model Number
- Rated Output Power
- Service Factor
- Rated Speed
- Insulation Class
- Temperature Rise
- Rated Voltage
- Rated Frequency
- Rated Current
- Starting Current
- Efficiency
- Power Factor
- Starting Torque
- Pull-Out Torque
- Rotor Parameters
- Stator Parameters
- Number of Starts per Hour
- Transportation Weight
- Ingress Protection
- Cooling Method
- Explosion Protection Details
- Bearing Details
- Cable Information
- Winding Connection

### Output Column Added

| Column |
|----------|
| motor_data |

The column contains a dictionary of extracted field-value pairs.

---

## Node 4 – Parse_Pump_Data_PDS

### Purpose

Parses Pump Datasheet information from extracted PDF text.

### Method

Regex-based field extraction.

### Major Fields Extracted

Examples include:

- Tag Name
- Manufacturer
- Datasheet Number
- Model Number
- Pump Type
- Number of Stages
- Rotation Direction
- Casing Mounting
- Casing Type
- Impeller Type
- Suction Nozzle Details
- Discharge Nozzle Details
- Bearing Details
- Driver Details
- Hydraulic Power
- Efficiency
- Rated Speed
- NPSH Values
- Capacity
- Differential Head
- Pressure Details
- Temperature Details
- Fluid Information
- Explosion Protection Details
- Seal Information
- Coupling Details
- Hydro Test Pressure
- Material Details

### Output Column Added

| Column |
|----------|
| pump_data |

The column contains a dictionary of extracted field-value pairs.

---

## Node 5 – Write_Data_into_Excel_Files

### Purpose

Writes extracted data into predefined Excel templates.

### Library Used

```python
openpyxl
```

### Activities

- Opens Motor Excel template.
- Opens Pump Excel template.
- Reads header names from row 2.
- Creates header-to-column mapping.
- Writes values into row 4.
- Saves updated Excel files.

### Excel Mapping Logic

Header matching is performed using:

- Case-insensitive comparison
- Whitespace normalization

### Default Configuration

| Parameter | Value |
|------------|---------|
| Header Row | 2 |
| Data Row | 4 |

### Output Columns Added

| Column |
|----------|
| motor_write_status |
| pump_write_status |

---

# Workflow Data Flow

```text
Setup_and_File_Classification
            │
            ▼
Extract_PDF_Text
            │
            ▼
Parse_Motor_Data_MDS
            │
            ▼
Parse_Pump_Data_PDS
            │
            ▼
Write_Data_into_Excel_Files
```

---

# Folder Structure

```text
Digital_Twin_Reliance_Copy
│
├── input
│   ├── Motor Datasheet PDF (MDS)
│   └── Pump Datasheet PDF (PDS)
│
└── output
    ├── Motor Excel Template
    └── Pump Excel Template
```

---

# Logging

Each RubPython node uses:

```python
print2log()
```

for workflow execution logs.

Logs include:

- Input validation
- File classification
- PDF extraction status
- Regex extraction status
- Excel write status
- Error handling messages

---

# Error Handling

The workflow handles:

### Missing Directories
- Invalid input path
- Invalid output path

### Missing Files
- Missing MDS PDF
- Missing PDS PDF
- Missing Motor Excel
- Missing Pump Excel

### PDF Processing Errors
- Corrupt PDF
- Unreadable PDF
- Page extraction failures

### Excel Processing Errors
- Missing workbook
- Save failures
- Missing header mappings

---

# Dependencies

Install the following Python packages in the Rubiscape execution environment:

```bash
pip install pandas
pip install PyPDF2
pip install openpyxl
```

---

# Execution Outcome

After successful execution:

1. Motor Datasheet information is extracted and written to the Motor Excel template.
2. Pump Datasheet information is extracted and written to the Pump Excel template.
3. Updated Excel files are saved in the configured output directory.
4. Workflow execution status is available through Rubiscape logs.