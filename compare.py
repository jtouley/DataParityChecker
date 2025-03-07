#!/usr/bin/env python3
"""
DataParityChecker: Excel and CSV File Comparison Tool

This script compares Excel and CSV files to verify data parity, accounting for
encoding differences, formatting variations, and other common discrepancies that
don't affect the actual business data content.

Configuration is read from files_to_compare.yaml.
Detailed reports are generated in the data/ directory.
"""

import os
import yaml
import logging
import pandas as pd
import numpy as np
import re
from datetime import datetime
from tabulate import tabulate
from typing import Dict, List, Any, Optional

# Configure logging to both file and console
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("comparison.log"),  # Save logs to file
        logging.StreamHandler()  # Display logs in terminal
    ]
)

class FileComparator:
    """
    Compare Excel and CSV files for data parity with intelligent handling of
    format and encoding differences.
    
    This class performs several key steps:
    1. Loads and preprocesses both files with encoding detection
    2. Normalizes data formats (text, numbers, column names)
    3. Intelligently matches rows across files
    4. Analyzes differences by category (format, whitespace, case, values)
    5. Generates a detailed Markdown report with recommendations
    """

    def __init__(self, excel_file: str, csv_file: str, config: Dict = None, max_rows: int = None, report_dir="data"):
        """
        Initialize the file comparator with source files and output settings.
        
        Args:
            excel_file: Path to the Excel (.xlsx) file
            csv_file: Path to the CSV file
            config: Configuration settings for this file comparison
            max_rows: Maximum rows to include in difference examples (None = unlimited)
            report_dir: Directory where reports will be saved
        """
        self.excel_file = excel_file
        self.csv_file = csv_file
        self.config = config or {}
        self.max_rows = max_rows
        self.df_excel = None
        self.df_csv = None
        self.report_dir = report_dir
        self.differences = None
        self.diff_summary = {}
        self.missing_columns = []
        self.extra_columns = []
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.report_file = self._generate_report_filename()
        self.excel_row_count = 0
        self.csv_row_count = 0
        self.common_keys = []
        self.key_columns = []
        self.common_columns = set()

        # Create report directory if it doesn't exist
        os.makedirs(self.report_dir, exist_ok=True)
        logging.info(f"Initialized FileComparator for {self.excel_file} and {self.csv_file}")

    def _generate_report_filename(self) -> str:
        """Generate a timestamped Markdown report filename."""
        excel_name = os.path.basename(self.excel_file).replace(" ", "_").replace(".", "_")
        csv_name = os.path.basename(self.csv_file).replace(" ", "_").replace(".", "_")
        return os.path.join(self.report_dir, f"Parity_Check_{excel_name}_{csv_name}_{self.timestamp}.md")

    def load_data(self):
        """Load data from Excel and CSV files with robust encoding detection."""
        try:
            # Load Excel file
            logging.info(f"Loading Excel file: {self.excel_file}")
            # Use options to prevent automatic date conversion
            self.df_excel = pd.read_excel(
                self.excel_file, 
                dtype=str,  # Force all columns to be strings
                na_filter=False,
                date_format=None  # Don't try to parse dates
            )
            self.excel_row_count = len(self.df_excel)
            
            # Try multiple encodings for CSV file
            logging.info(f"Loading CSV file: {self.csv_file}")
            encodings = ['utf-8-sig', 'utf-8', 'latin1', 'ISO-8859-1']
            self.df_csv = None
            
            for encoding in encodings:
                try:
                    self.df_csv = pd.read_csv(
                        self.csv_file, 
                        dtype=str,  # Force all columns to be strings
                        encoding=encoding, 
                        na_filter=False
                    )
                    self.csv_row_count = len(self.df_csv)
                    logging.info(f"Successfully loaded CSV with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            if self.df_csv is None:
                raise ValueError(f"Could not load CSV file with any of the attempted encodings: {encodings}")
            
            logging.info(f"Excel file: {self.excel_row_count} rows, {len(self.df_excel.columns)} columns")
            logging.info(f"CSV file: {self.csv_row_count} rows, {len(self.df_csv.columns)} columns")
            
        except Exception as e:
            logging.error(f"Error loading files: {e}")
            self._generate_report(success=False, error_message=str(e))
            raise

    def clean_column_names(self):
        """Normalize column names across both files to handle encoding and format differences."""
        # Function to standardize column names
        def standardize_column(col):
            # Remove BOM and non-printable characters
            col = re.sub(r'[\ufeff\u200b\xa0]', '', col)
            # Convert to lowercase, replace spaces and special chars with underscores
            col = re.sub(r'[^a-zA-Z0-9]', '_', col.lower().strip())
            # Remove consecutive underscores
            col = re.sub(r'_+', '_', col)
            # Remove leading/trailing underscores
            return col.strip('_')
        
        # Save original column mappings for reporting
        self.excel_column_mapping = dict(zip(self.df_excel.columns, 
                                         [standardize_column(col) for col in self.df_excel.columns]))
        self.csv_column_mapping = dict(zip(self.df_csv.columns, 
                                      [standardize_column(col) for col in self.df_csv.columns]))
        
        # Rename columns
        self.df_excel.columns = [standardize_column(col) for col in self.df_excel.columns]
        self.df_csv.columns = [standardize_column(col) for col in self.df_csv.columns]
        
        # Find missing and extra columns
        excel_cols = set(self.df_excel.columns)
        csv_cols = set(self.df_csv.columns)
        
        self.missing_columns = excel_cols - csv_cols
        self.extra_columns = csv_cols - excel_cols
        self.common_columns = excel_cols.intersection(csv_cols)
        
        logging.info(f"Common columns: {len(self.common_columns)}")
        if self.missing_columns:
            logging.warning(f"Columns in Excel but not in CSV: {self.missing_columns}")
        if self.extra_columns:
            logging.warning(f"Columns in CSV but not in Excel: {self.extra_columns}")

    def clean_text_data(self):
        """Normalize text data to handle encoding and formatting variations."""
        logging.info("Cleaning and normalizing text data...")
        
        def clean_text(value):
            if not isinstance(value, str):
                return value
            
            # Handle None/NaN/empty values
            if pd.isna(value) or value.strip() == '':
                return ''
            
            # Normalize unicode
            import unicodedata
            value = unicodedata.normalize('NFKD', value)
            
            # Replace non-breaking spaces with regular spaces
            value = value.replace('\xa0', ' ')
            
            # Remove BOM and hidden characters
            value = re.sub(r'[\ufeff\u200b]', '', value)
            
            # Replace multiple spaces with single space
            value = re.sub(r'\s+', ' ', value)
            
            # Strip leading/trailing whitespace
            return value.strip()
        
        # Apply cleaning to all columns in both dataframes
        for col in self.df_excel.columns:
            self.df_excel[col] = self.df_excel[col].map(clean_text)
        
        for col in self.df_csv.columns:
            self.df_csv[col] = self.df_csv[col].map(clean_text)
        
        # Apply type-specific handling based on configuration
        self.apply_column_types()

    def normalize_case_if_configured(self):
        """Normalize the case of string columns if configured in YAML."""
        if self.config.get('normalize_case', False):
            logging.info("Normalizing case based on configuration...")
            
            # Function to normalize case
            def normalize_case(value):
                if isinstance(value, str):
                    return value.lower()  # or value.upper() if you prefer
                return value
            
            # Apply to both dataframes
            for col in self.df_excel.columns:
                if self.df_excel[col].dtype == 'object':  # Only apply to string columns
                    self.df_excel[col] = self.df_excel[col].map(normalize_case)
            
            for col in self.df_csv.columns:
                if self.df_csv[col].dtype == 'object':  # Only apply to string columns
                    self.df_csv[col] = self.df_csv[col].map(normalize_case)

    def apply_column_types(self):
        """Apply type-specific handling to columns based on configuration."""
        # Get column type configurations
        date_columns = self.config.get('date_columns', [])
        string_columns = self.config.get('string_columns', [])
        numeric_columns = self.config.get('numeric_columns', [])
        
        # Log the configuration
        if date_columns:
            logging.info(f"Columns to be processed as dates: {date_columns}")
        if string_columns:
            logging.info(f"Columns to be treated as strings: {string_columns}")
        if numeric_columns:
            logging.info(f"Columns to be treated as numeric: {numeric_columns}")
        
        # Process date columns
        for col in date_columns:
            if col in self.common_columns:
                logging.info(f"Processing date column: {col}")
                self._normalize_date_column(col)
            else:
                logging.warning(f"Date column '{col}' specified in config not found in data")
        
        # Process string columns - explicitly ensure they're strings (already done by default)
        for col in string_columns:
            if col in self.common_columns:
                logging.info(f"Ensuring column is treated as string: {col}")
                # Force string type (though should already be strings from loading)
                self.df_excel[col] = self.df_excel[col].astype(str)
                self.df_csv[col] = self.df_csv[col].astype(str)
        
        # Process numeric columns
        for col in numeric_columns:
            if col in self.common_columns:
                logging.info(f"Processing numeric column: {col}")
                self._normalize_numeric_column(col)
            else:
                logging.warning(f"Numeric column '{col}' specified in config not found in data")

    def _normalize_date_column(self, column):
        """Normalize a date column to a standard format across both dataframes."""
        logging.info(f"Normalizing date formats in column: {column}")
        
        def parse_and_format_date(value):
            """Parse various date formats and return a standardized version."""
            if not isinstance(value, str) or not value:
                return value
                
            # Try different date formats
            date_formats = [
                # Excel-style formats
                '%Y-%m-%d',
                '%Y-%m-%d %H:%M:%S',
                # CSV-style formats
                '%m/%d/%Y',
                '%m/%d/%Y %I:%M:%S %p',  # with AM/PM
                '%m/%d/%Y %H:%M:%S'  # 24-hour
            ]
            
            for fmt in date_formats:
                try:
                    # Try to parse the date with this format
                    parsed_date = datetime.strptime(value, fmt)
                    # Return a standardized format (ISO format)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # If we couldn't parse it as a date, return the original value
            return value
        
        # Apply date normalization to both dataframes
        self.df_excel[column] = self.df_excel[column].map(parse_and_format_date)
        self.df_csv[column] = self.df_csv[column].map(parse_and_format_date)

    def _normalize_numeric_column(self, column):
        """Normalize a numeric column to a consistent format."""
        logging.info(f"Standardizing numeric column: {column}")
        
        def standardize_numeric(value):
            """Standardize a numeric string value to consistent format."""
            if not isinstance(value, str) or value.strip() == '':
                return value
            
            # Remove thousand separators and normalize decimal point
            cleaned = re.sub(r'[,\s]', '', value)
            
            try:
                # Try converting to float
                num = float(cleaned)
                # Check if it's an integer
                if num.is_integer():
                    return str(int(num))
                else:
                    # Format with consistent decimal places, removing trailing zeros
                    return f"{num:.6f}".rstrip('0').rstrip('.') if '.' in f"{num:.6f}" else f"{int(num)}"
            except ValueError:
                return value
        
        # Apply numeric standardization to both dataframes
        self.df_excel[column] = self.df_excel[column].map(standardize_numeric)
        self.df_csv[column] = self.df_csv[column].map(standardize_numeric)

    def standardize_numeric_data(self):
        """
        Standardize numeric values for columns not explicitly typed.
        Only applies to columns not already handled by apply_column_types.
        """
        logging.info("Standardizing remaining numeric data...")
        
        # Skip columns that have already been explicitly typed
        typed_columns = set()
        typed_columns.update(self.config.get('date_columns', []))
        typed_columns.update(self.config.get('string_columns', []))
        typed_columns.update(self.config.get('numeric_columns', []))
        
        def is_numeric_column(series):
            """Determine if a column appears to contain numeric data."""
            numeric_pattern = r'^[-+]?[0-9]*\.?[0-9]+$'
            # Consider a column numeric if more than 90% of non-empty values match the pattern
            non_empty = series[series != '']
            if len(non_empty) == 0:
                return False
            matches = non_empty.str.match(numeric_pattern)
            return matches.mean() > 0.9

        # Process only columns that haven't been explicitly typed
        for col in self.common_columns:
            if col not in typed_columns and col in self.df_excel.columns and col in self.df_csv.columns:
                if is_numeric_column(self.df_excel[col]) or is_numeric_column(self.df_csv[col]):
                    self._normalize_numeric_column(col)

    def detect_key_columns(self):
        """Detect columns that can serve as keys for row matching."""
        logging.info("Detecting potential key columns...")
        
        # Check if key columns are specified in config
        config_key_columns = self.config.get('key_columns', [])
        if config_key_columns:
            # Verify these columns exist in the data
            valid_key_columns = [col for col in config_key_columns if col in self.common_columns]
            if valid_key_columns:
                self.key_columns = valid_key_columns
                logging.info(f"Using configured key column(s): {self.key_columns}")
                return
            else:
                logging.warning(f"Configured key columns {config_key_columns} not found in data")
        
        # Candidate columns that often serve as keys
        key_candidates = [
            col for col in self.common_columns if any(
                key_term in col.lower() for key_term in 
                ['id', 'key', 'code', 'number', 'uuid', 'guid', 'pk', 'identifier']
            )
        ]
        
        # If no candidates found by name, look for columns with unique values
        if not key_candidates:
            for col in self.common_columns:
                if (self.df_excel[col].nunique() == len(self.df_excel) and 
                    self.df_csv[col].nunique() == len(self.df_csv)):
                    key_candidates.append(col)
                    break
        
        # If still no candidates, try to create compound keys
        if not key_candidates:
            # Try common sets of columns that might form a compound key
            self.key_columns = list(self.common_columns)[:3]  # Just use first few columns
            logging.info(f"Using compound key from columns: {self.key_columns}")
            return
        
        self.key_columns = key_candidates[:1]  # Use the first detected key column
        logging.info(f"Detected key column(s): {self.key_columns}")

    def compare_files(self) -> bool:
        """Compare Excel and CSV files with detailed difference tracking."""
        logging.info("Comparing data...")
        
        # Check for column differences
        if self.missing_columns or self.extra_columns:
            logging.warning("Column mismatch detected.")
            # We'll continue comparison with common columns
        
        # Restrict comparison to common columns
        excel_filtered = self.df_excel[list(self.common_columns)].copy()
        csv_filtered = self.df_csv[list(self.common_columns)].copy()
        
        # Compare row counts
        if len(excel_filtered) != len(csv_filtered):
            logging.warning(f"Row count mismatch: Excel={len(excel_filtered)}, CSV={len(csv_filtered)}")
            self.diff_summary['row_count_diff'] = abs(len(excel_filtered) - len(csv_filtered))
        
        # Try direct comparison first
        exact_match = excel_filtered.equals(csv_filtered)
        if exact_match:
            logging.info("✅ Files are identical for common columns.")
            self._generate_report(success=True)
            return True
        
        # Detailed comparison by row using key columns
        logging.info("Files differ - analyzing differences...")
        self.analyze_differences(excel_filtered, csv_filtered)
        
        self._generate_report(success=False)
        return False

    def analyze_differences(self, excel_df, csv_df):
        """Analyze differences between dataframes and categorize them."""
        # Initialize difference counters
        diff_types = {
            'format_differences': 0,  # e.g., '1.0' vs '1'
            'whitespace_differences': 0,  # e.g., 'value ' vs 'value'
            'case_differences': 0,  # e.g., 'Value' vs 'value'
            'missing_rows': 0,  # Rows in Excel but not in CSV
            'extra_rows': 0,  # Rows in CSV but not in Excel
            'value_differences': 0,  # Actual different values
            'sample_differences': []  # Sample of differences for reporting
        }

        # If we have key columns, use them for matching rows
        if self.key_columns:
            # Create dictionaries of rows keyed by key column values
            excel_dict = self._create_row_dict(excel_df, self.key_columns)
            csv_dict = self._create_row_dict(csv_df, self.key_columns)
            
            # Find common keys
            excel_keys = set(excel_dict.keys())
            csv_keys = set(csv_dict.keys())
            common_keys = excel_keys.intersection(csv_keys)
            self.common_keys = list(common_keys)
            
            # Check for missing/extra rows
            missing_keys = excel_keys - csv_keys
            extra_keys = csv_keys - excel_keys
            
            diff_types['missing_rows'] = len(missing_keys)
            diff_types['extra_rows'] = len(extra_keys)
            
            if len(missing_keys) > 0:
                logging.warning(f"Found {len(missing_keys)} rows in Excel missing from CSV")
                # Sample some missing keys
                diff_types['missing_keys_sample'] = list(missing_keys)[:5]
            
            if len(extra_keys) > 0:
                logging.warning(f"Found {len(extra_keys)} rows in CSV missing from Excel")
                diff_types['extra_keys_sample'] = list(extra_keys)[:5]
            
            # Compare common rows
            for key in common_keys:
                excel_row = excel_dict[key]
                csv_row = csv_dict[key]
                
                for col in self.common_columns:
                    excel_val = str(excel_row.get(col, ''))
                    csv_val = str(csv_row.get(col, ''))
                    
                    if excel_val != csv_val:
                        # Categorize the difference
                        if excel_val.lower() == csv_val.lower():
                            diff_types['case_differences'] += 1
                        elif excel_val.strip() == csv_val.strip():
                            diff_types['whitespace_differences'] += 1
                        elif re.sub(r'[.\s,]', '', excel_val) == re.sub(r'[.\s,]', '', csv_val):
                            diff_types['format_differences'] += 1
                        else:
                            diff_types['value_differences'] += 1
                            
                            # Save some examples for reporting
                            if len(diff_types['sample_differences']) < 10:
                                diff_types['sample_differences'].append({
                                    'key': key,
                                    'column': col,
                                    'excel_value': excel_val,
                                    'csv_value': csv_val
                                })
        
        else:
            # If no key columns, compare row by row
            min_rows = min(len(excel_df), len(csv_df))
            
            for i in range(min_rows):
                for col in self.common_columns:
                    excel_val = str(excel_df.iloc[i][col])
                    csv_val = str(csv_df.iloc[i][col])
                    
                    if excel_val != csv_val:
                        if excel_val.lower() == csv_val.lower():
                            diff_types['case_differences'] += 1
                        elif excel_val.strip() == csv_val.strip():
                            diff_types['whitespace_differences'] += 1
                        elif re.sub(r'[.\s,]', '', excel_val) == re.sub(r'[.\s,]', '', csv_val):
                            diff_types['format_differences'] += 1
                        else:
                            diff_types['value_differences'] += 1
                            
                            # Save examples
                            if len(diff_types['sample_differences']) < 10:
                                diff_types['sample_differences'].append({
                                    'row': i,
                                    'column': col,
                                    'excel_value': excel_val,
                                    'csv_value': csv_val
                                })
        
        # Calculate total differences
        total_diffs = sum([
            diff_types['format_differences'],
            diff_types['whitespace_differences'],
            diff_types['case_differences'],
            diff_types['value_differences']
        ])
        
        diff_types['total_differences'] = total_diffs
        logging.info(f"Total differences found: {total_diffs}")
        logging.info(f"Format differences: {diff_types['format_differences']}")
        logging.info(f"Whitespace differences: {diff_types['whitespace_differences']}")
        logging.info(f"Case differences: {diff_types['case_differences']}")
        logging.info(f"Value differences: {diff_types['value_differences']}")
        
        self.diff_summary = diff_types

    def _create_row_dict(self, df, key_columns):
        """Create a dictionary of rows keyed by values in key columns."""
        result = {}
        
        for _, row in df.iterrows():
            # Create a composite key from the key columns
            if len(key_columns) == 1:
                key = row[key_columns[0]]
            else:
                key = tuple(row[col] for col in key_columns)
                
            # Store the entire row as a dictionary
            result[key] = row.to_dict()
            
        return result

    def _generate_report(self, success: bool, error_message: str = None):
        """Generate a detailed Markdown report with difference summary."""
        report_content = [
            f"# Data Parity Check Report",
            f"**Timestamp:** {self.timestamp}",
            f"**Excel File:** `{self.excel_file}`",
            f"**CSV File:** `{self.csv_file}`",
            f"**Status:** {'✅ Files Match' if success else '❌ Files Differ'}",
            "",
            f"## Summary",
            f"- Excel Row Count: {self.excel_row_count}",
            f"- CSV Row Count: {self.csv_row_count}",
            f"- Excel Column Count: {len(self.df_excel.columns) if self.df_excel is not None else 0}",
            f"- CSV Column Count: {len(self.df_csv.columns) if self.df_csv is not None else 0}",
            f"- Common Columns: {len(self.common_columns) if hasattr(self, 'common_columns') else 0}",
            ""
        ]

        if error_message:
            report_content.extend([
                f"## Error",
                f"❗ **Error:** {error_message}",
                ""
            ])
        elif success:
            report_content.extend([
                "## Result",
                "✅ **No discrepancies found.** The files have identical data content.",
                ""
            ])
        else:
            # Add difference summary
            report_content.extend([
                "## Differences Summary",
                f"- Total Differences: **{self.diff_summary.get('total_differences', 0)}**",
                f"- Format Differences (e.g., '1.0' vs '1'): {self.diff_summary.get('format_differences', 0)}",
                f"- Whitespace Differences: {self.diff_summary.get('whitespace_differences', 0)}",
                f"- Case Differences (e.g., 'ABC' vs 'abc'): {self.diff_summary.get('case_differences', 0)}",
                f"- Actual Value Differences: {self.diff_summary.get('value_differences', 0)}",
                ""
            ])
            
            # Add row count differences
            if 'row_count_diff' in self.diff_summary:
                report_content.extend([
                    f"- Row Count Difference: {self.diff_summary['row_count_diff']}",
                    f"- Missing Rows (in Excel but not CSV): {self.diff_summary.get('missing_rows', 0)}",
                    f"- Extra Rows (in CSV but not Excel): {self.diff_summary.get('extra_rows', 0)}",
                    ""
                ])
            
            # Add column differences
            if self.missing_columns or self.extra_columns:
                report_content.extend(["## Column Discrepancies", ""])
                
                if self.missing_columns:
                    report_content.extend([
                        "### Columns in Excel but missing from CSV:",
                        "```",
                        ", ".join(self.missing_columns),
                        "```",
                        ""
                    ])
                
                if self.extra_columns:
                    report_content.extend([
                        "### Columns in CSV but missing from Excel:",
                        "```",
                        ", ".join(self.extra_columns),
                        "```",
                        ""
                    ])
            
            # Add difference examples
            if 'sample_differences' in self.diff_summary and self.diff_summary['sample_differences']:
                report_content.extend(["## Sample Differences", ""])
                
                # Create a table of sample differences
                diff_table = []
                for diff in self.diff_summary['sample_differences']:
                    if 'key' in diff:
                        diff_table.append([
                            f"Key: {diff['key']}", 
                            diff['column'], 
                            diff['excel_value'], 
                            diff['csv_value']
                        ])
                    else:
                        diff_table.append([
                            f"Row: {diff['row']}", 
                            diff['column'], 
                            diff['excel_value'], 
                            diff['csv_value']
                        ])
                
                report_content.append(tabulate(
                    diff_table, 
                    headers=['Location', 'Column', 'Excel Value', 'CSV Value'],
                    tablefmt='github'
                ))
                report_content.append("")
            
            # Add recommendations section
            report_content.extend([
                "## Recommendations",
                "",
                "Based on the analysis, here are recommendations to resolve the differences:",
                ""
            ])
            
            # Format-related recommendations
            if self.diff_summary.get('format_differences', 0) > 0:
                report_content.append("- **Format standardization**: The files contain the same data with different formatting (e.g., '1.0' vs '1', or '1,000' vs '1000'). Consider standardizing the numeric format in both sources.")
            
            # Whitespace-related recommendations
            if self.diff_summary.get('whitespace_differences', 0) > 0:
                report_content.append("- **Whitespace cleaning**: There are differences in leading/trailing spaces. Consider trimming whitespace in both sources.")
            
            # Case-related recommendations
            if self.diff_summary.get('case_differences', 0) > 0:
                report_content.append("- **Case normalization**: Text case differences were found. Consider normalizing case (upper/lower) in both sources.")
            
            # Column-related recommendations
            if self.missing_columns or self.extra_columns:
                report_content.append("- **Column alignment**: Ensure both files contain the same columns, or document which columns are intentionally different.")
            
            # Row-related recommendations
            if self.diff_summary.get('missing_rows', 0) > 0 or self.diff_summary.get('extra_rows', 0) > 0:
                report_content.append("- **Row alignment**: The files contain different numbers of rows. Verify if this is expected or if data is missing from one source.")
            
            # Value-related recommendations
            if self.diff_summary.get('value_differences', 0) > 0:
                report_content.append("- **Data verification**: Actual data value differences were found. Review the sample differences to determine the cause.")
                
                # Add configuration suggestion if there appear to be problematic columns
                problematic_cols = set([diff['column'] for diff in self.diff_summary['sample_differences']])
                if problematic_cols:
                    report_content.append("")
                    report_content.append("Consider updating your YAML configuration to specify column types for problematic columns:")
                    report_content.append("```yaml")
                    report_content.append("date_columns: [\"demolition_date\"]  # Columns to be treated as dates")
                    report_content.append(f"string_columns: {list(problematic_cols)}  # Force these to be treated as strings")
                    report_content.append("```")

        with open(self.report_file, "w") as report:
            report.write("\n".join(report_content))

        logging.info(f"Report saved: {self.report_file}")

    def run_comparison(self):
        """Execute the full comparison workflow with preprocessing and analysis."""
        logging.info("Starting comparison process...")
        try:
            self.load_data()
            self.clean_column_names()
            self.clean_text_data()
            self.normalize_case_if_configured()  # Add this line
            self.standardize_numeric_data()
            self.detect_key_columns()
            identical = self.compare_files()
            if not identical:
                logging.info(f"Differences logged in {self.report_file}")
        except Exception as e:
            logging.error(f"Comparison process failed: {e}")
            self._generate_report(success=False, error_message=str(e))
        logging.info("Comparison process completed.")

# ======================================================================
# HELPER FUNCTIONS
# ======================================================================

def load_yaml_config(config_file="files_to_compare.yaml"):
    """Load file comparison configuration from YAML."""
    logging.info(f"Loading configuration from {config_file}...")
    try:
        with open(config_file, "r") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logging.error(f"Error loading YAML file: {e}")
        raise

# ======================================================================
# MAIN EXECUTION
# ======================================================================

if __name__ == "__main__":
    """
    Main entry point for the file comparison tool.
    
    Loads configuration from YAML file and processes each file comparison.
    Results are saved as Markdown reports in the data/ directory.
    """
    config = load_yaml_config()
    comparisons = config.get("comparisons", [])

    if not comparisons:
        logging.warning("No file comparisons found in configuration. Check your files_to_compare.yaml file.")
    
    for index, files in enumerate(comparisons, 1):
        logging.info(f"Processing comparison {index}/{len(comparisons)}: {files['excel_file']} vs {files['csv_file']}")
        comparator = FileComparator(
            excel_file=files["excel_file"],
            csv_file=files["csv_file"],
            config=files,  # Pass the entire configuration for this comparison
            max_rows=files.get("max_rows")
        )
        comparator.run_comparison()