# Data Parity Check Report
**Timestamp:** 2025-03-07_17-22-07
**Excel File:** `input_files/examples/Completed_Residential_Demolitions_-8776591415274907616.xlsx`
**CSV File:** `input_files/examples/Completed_Residential_Demolitions_-8776591415274907616.csv`
**Status:** ❌ Files Differ

## Summary
- Excel Row Count: 30024
- CSV Row Count: 30024
- Excel Column Count: 21
- CSV Column Count: 21
- Common Columns: 21

## Differences Summary
- Total Differences: **19**
- Format Differences (e.g., '1.0' vs '1'): 0
- Whitespace Differences: 0
- Case Differences (e.g., 'ABC' vs 'abc'): 0
- Actual Value Differences: 19

## Sample Differences

| Location   | Column               | Excel Value         | CSV Value   |
|------------|----------------------|---------------------|-------------|
| Key: 15474 | address              | 9110-05-01 00:00:00 | 9110 may    |
| Key: 24829 | address              | 6640-05-01 00:00:00 | 6640 may    |
| Key: 13944 | address              | 6317-05-01 00:00:00 | 6317 may    |
| Key: 17825 | address              | 8914-05-01 00:00:00 | 8914 may    |
| Key: 447   | address              | 9014-05-01 00:00:00 | 9014 may    |
| Key: 21530 | demolition_rfp_group | 37 days, 1:43:00    | 36: 51223   |
| Key: 9797  | demolition_rfp_group | 37 days, 0:07:00    | 35: 51187   |
| Key: 13932 | address              | 6634-05-01 00:00:00 | 6634 may    |
| Key: 9444  | demolition_rfp_group | 36 days, 22:38:00   | 34: 51158   |
| Key: 6147  | address              | 9100-05-01 00:00:00 | 9100 may    |

## Recommendations

Based on the analysis, here are recommendations to resolve the differences:

- **Data verification**: Actual data value differences were found. Review the sample differences to determine the cause.

Consider updating your YAML configuration to specify column types for problematic columns:
```yaml
date_columns: ["demolition_date"]  # Columns to be treated as dates
string_columns: ['demolition_rfp_group', 'address']  # Force these to be treated as strings
```