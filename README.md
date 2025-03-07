# DataParityChecker

## Overview
DataParityChecker is a robust tool that compares **Excel (`.xlsx`)** and **CSV (`.csv`)** files to verify data parity, accounting for common formatting variations like different date formats, number representations, whitespace differences, and case sensitivity. It generates detailed Markdown reports showing exactly what differences exist between files.

## Features
- ✅ **Intelligent format handling**: Recognizes common variations in data representation
- ✅ **Content-aware comparison**: Finds true data differences vs formatting differences
- ✅ **Flexible configuration**: YAML-based configuration for customizing comparison behavior
- ✅ **Multiple encodings**: Handles various CSV encodings automatically
- ✅ **Detailed reports**: Comprehensive Markdown reports with specific recommendations
- ✅ **Case normalization**: Optional case-insensitive comparison

---

## **1. Installation & Setup**
### Clone the Repository
```bash
git clone https://github.com/jtouley/DataParityChecker.git
cd DataParityChecker
```

### Run Setup Script
```sh
bash setup.sh
```
This will:
- Create a virtual environment
- Install dependencies (**pandas, openpyxl, PyYAML, tabulate**)

---

## **2. Configuring File Comparisons**

All file comparisons are configured in `files_to_compare.yaml`. This enables you to compare multiple file pairs with different settings.

### Basic Configuration
```yaml
comparisons:
  - excel_file: "path/to/your/spreadsheet.xlsx"
    csv_file: "path/to/your/data.csv"
```

### Advanced Configuration Options

#### Complete Configuration Example
```yaml
comparisons:
  - excel_file: "input_files/examples/data_report.xlsx"
    csv_file: "input_files/examples/data_report.csv"
    
    # Column type definitions
    date_columns: ["created_date", "modified_date"]  # Columns to be processed as dates
    string_columns: ["id", "description", "notes"]   # Columns to be treated as strings
    numeric_columns: ["amount", "quantity", "price"] # Columns to be processed as numbers
    
    # Row matching configuration
    key_columns: ["id"]  # Column(s) used to match rows between files
    
    # Case sensitivity
    normalize_case: true  # Set to true for case-insensitive comparison
    
    # Reporting options
    max_rows: 100  # Maximum number of differences to include in report
```

#### Configuration Options Explained

| Option | Description | Default |
|--------|-------------|---------|
| `excel_file` | Path to Excel file (required) | - |
| `csv_file` | Path to CSV file (required) | - |
| `date_columns` | List of columns to process as dates | `[]` |
| `string_columns` | List of columns to force as strings | `[]` |
| `numeric_columns` | List of columns to process as numbers | `[]` |
| `key_columns` | Column(s) to use for matching rows | Auto-detected |
| `normalize_case` | Whether to normalize text case | `false` |
| `max_rows` | Max rows in difference examples | No limit |

---

## **3. Running the Comparison**

Run the comparison tool:
```sh
python compare.py
```

This will:
- Process each file pair defined in `files_to_compare.yaml`
- Generate detailed reports in the `data/` folder

---

## **4. Understanding the Results**

### Report Location
Reports are saved in the `data/` directory with timestamped filenames:
```
data/Parity_Check_filename1_filename2_YYYY-MM-DD_HH-MM-SS.md
```

### Report Content
The report includes:
- Summary of files compared
- Row and column counts
- Categorized differences (format, whitespace, case, values)
- Sample differences with specific examples
- Recommendations to resolve differences

### Example Report Sections

#### Summary
```
# Data Parity Check Report
**Timestamp:** 2025-03-07_17-07-57
**Excel File:** `input_files/examples/data_file.xlsx`
**CSV File:** `input_files/examples/data_file.csv`
**Status:** ❌ Files Differ
```

#### Differences Summary
```
## Differences Summary
- Total Differences: 127
- Format Differences (e.g., '1.0' vs '1'): 85
- Whitespace Differences: 12
- Case Differences (e.g., 'ABC' vs 'abc'): 30
- Actual Value Differences: 0
```

#### Recommendations
```
## Recommendations
- **Format standardization**: The files contain the same data with different formatting.
- **Whitespace cleaning**: There are differences in leading/trailing spaces.
- **Case normalization**: Text case differences were found.
```

---

## **5. Common Use Cases**

### Checking Data Extract Consistency
Verify that data exported to CSV matches the original Excel file.

### Validating Data Transformation
Confirm that data transformation processes didn't alter values.

### Cross-System Data Verification
Check that data imported into a new system matches the source data.

---

## **6. Troubleshooting**

### CSV Encoding Issues
The tool automatically tries multiple encodings (`utf-8-sig`, `utf-8`, `latin1`, `ISO-8859-1`). If you experience encoding issues, you may need to pre-convert your CSV file.

### Configuration Errors
YAML syntax errors will be reported on startup. Check spacing and indentation if you encounter errors.

### Large Files
For very large files, comparison may be slow. Consider setting `max_rows` to limit the analysis.

---

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
