# DataParityChecker

## Overview
This tool compares **Excel (`.xlsx`)** and **CSV (`.csv`)** files to check for **100% parity** and generates a Markdown report for each comparison.

---

## **1. Installation & Setup**
### Clone the Repository
```bash
git clone https://github.com/jtouley/DataParityChecker.git
cd DataParityChecker
```

### 1. Run Setup Script
```sh
bash setup.sh
```
This will:
- Create a virtual environment
- Install dependencies (**pandas, openpyxl, PyYAML**)
---

### 2. Configuring File Comparisons
Instead of modifying Python files, simply update files_to_compare.yaml with your dataset:
```yaml
comparisons:
  - excel_file: "data_2025.xlsx"
    csv_file: "data_2025.csv"
  - excel_file: "sales_report.xlsx"
    csv_file: "sales_data.csv"
```

### 3. Running the Comparison
Run:
```sh
python compare.py
```
This will:
- Compare each file pair in files_to_compare.yaml
- Generate reports in data/ folder

### 4. Checking Results
- ✅ If files match, a report confirms parity.
- ❌ If differences exist, the mismatches are logged:
    - differences.xlsx (Excel report)
    - data/Parity_Check_[filename1]_[filename2].md (Markdown report)

### Can It Run in Parallel?

🚀 Right now, it runs sequentially for simplicity.

---

This update ensures config-driven execution instead of hardcoding filenames! 🚀 Let me know if you need enhancements.
