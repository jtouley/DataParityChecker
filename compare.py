import os
import yaml
import logging
import pandas as pd
import re
from datetime import datetime
from tabulate import tabulate

# Configure logging
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
    A class to compare an Excel file with a CSV file to ensure parity.
    It generates a Markdown report documenting the results.
    """

    def __init__(self, excel_file: str, csv_file: str, max_rows: int = None, report_dir="data"):
        self.excel_file = excel_file
        self.csv_file = csv_file
        self.max_rows = max_rows  # Configurable row limit from YAML
        self.df_excel = None
        self.df_csv = None
        self.report_dir = report_dir
        self.differences = None
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.report_file = self._generate_report_filename()

        os.makedirs(self.report_dir, exist_ok=True)
        logging.info(f"Initialized FileComparator for {self.excel_file} and {self.csv_file}")

    def _generate_report_filename(self) -> str:
        """Generate a timestamped Markdown report filename."""
        excel_name = os.path.basename(self.excel_file).replace(" ", "_").replace(".", "_")
        csv_name = os.path.basename(self.csv_file).replace(" ", "_").replace(".", "_")
        return os.path.join(self.report_dir, f"Parity_Check_{excel_name}_{csv_name}_{self.timestamp}.md")

    def load_data(self):
        """Load data from Excel and CSV files into Pandas DataFrames."""
        try:
            logging.info(f"Loading Excel file: {self.excel_file}")
            self.df_excel = pd.read_excel(self.excel_file, dtype=str)

            logging.info(f"Loading CSV file: {self.csv_file}")
            self.df_csv = pd.read_csv(self.csv_file, dtype=str, encoding="utf-8-sig")  # Handle BOM
        except Exception as e:
            logging.error(f"Error loading files: {e}")
            self._generate_report(success=False, error_message=str(e))
            raise

    def clean_column_names(self):
        """Remove BOM characters and normalize column names."""
        self.df_excel.columns = self.df_excel.columns.str.replace(r'\ufeff', '', regex=True).str.strip().str.lower()
        self.df_csv.columns = self.df_csv.columns.str.replace(r'\ufeff', '', regex=True).str.strip().str.lower()

    def clean_text_data(self):
        """Remove hidden characters and normalize text data."""
        def clean_text(value):
            if isinstance(value, str):
                return re.sub(r'[^\x20-\x7E]', '', value).strip()  # Remove non-ASCII characters
            return value

        self.df_excel = self.df_excel.applymap(clean_text)
        self.df_csv = self.df_csv.applymap(clean_text)

    def standardize_numeric_data(self):
        """Ensure numeric values are stored as float and rounded, and integer-like floats converted to int."""
        for col in self.df_excel.columns:
            # Convert text columns to numeric where applicable
            if self.df_excel[col].str.replace(".", "", 1).str.isnumeric().all() and \
               self.df_csv[col].str.replace(".", "", 1).str.isnumeric().all():
                
                self.df_excel[col] = pd.to_numeric(self.df_excel[col], errors="coerce")
                self.df_csv[col] = pd.to_numeric(self.df_csv[col], errors="coerce")

                # If all values are whole numbers, convert to int
                if (self.df_excel[col] % 1 == 0).all():
                    self.df_excel[col] = self.df_excel[col].astype(int)
                    self.df_csv[col] = self.df_csv[col].astype(int)
                else:
                    self.df_excel[col] = self.df_excel[col].round(6)
                    self.df_csv[col] = self.df_csv[col].round(6)

    def sort_rows(self):
        """Sort rows to remove order-based discrepancies before comparison."""
        logging.info("Sorting rows to ensure order consistency...")
        self.df_excel = self.df_excel.sort_values(by=list(self.df_excel.columns)).reset_index(drop=True)
        self.df_csv = self.df_csv.sort_values(by=list(self.df_csv.columns)).reset_index(drop=True)

    def compare_files(self) -> bool:
        """Compare Excel and CSV files for parity."""
        logging.info("Comparing data...")

        if list(self.df_excel.columns) != list(self.df_csv.columns):
            logging.warning("❗ Column mismatch detected.")
            self._generate_report(success=False, error_message="Column names do not match.")
            return False

        diff = self.df_excel.compare(self.df_csv, keep_shape=True, keep_equal=True)
        if diff.empty:
            logging.info("✅ Files are identical.")
            self._generate_report(success=True)
            return True
        else:
            logging.warning(f"❌ Differences found. Total differing rows: {len(diff)}")
            self.differences = diff
            self._generate_report(success=False)
            return False

    def _generate_report(self, success: bool, error_message: str = None):
        """Generate a Markdown report detailing the comparison results."""
        report_content = [
            f"# Data Parity Check Report",
            f"**Timestamp:** {self.timestamp}",
            f"**Excel File:** `{self.excel_file}`",
            f"**CSV File:** `{self.csv_file}`",
            f"**Status:** {'✅ Files Match' if success else '❌ Files Differ'}",
            "",
            f"### Details"
        ]

        if error_message:
            report_content.append(f"❗ **Error:** {error_message}")

        elif success:
            report_content.append("No discrepancies found.")
        else:
            report_content.append("#### **Differences Found (Showing First 10 Rows):**")
            if isinstance(self.differences, pd.DataFrame):
                diff_to_display = self.differences if self.max_rows is None else self.differences.head(self.max_rows)
                report_content.append(tabulate(diff_to_display, headers='keys', tablefmt='github'))

        with open(self.report_file, "w") as report:
            report.write("\n".join(report_content))

        logging.info(f"Report saved: {self.report_file}")

    def run_comparison(self):
        """Execute the full comparison workflow."""
        logging.info("Starting comparison process...")
        try:
            self.load_data()
            self.clean_column_names()
            self.clean_text_data()
            self.standardize_numeric_data()
            self.sort_rows()
            identical = self.compare_files()
            if not identical:
                logging.info(f"Differences logged in {self.report_file}")
        except Exception as e:
            logging.error(f"Comparison process failed: {e}")
            self._generate_report(success=False, error_message=str(e))
        logging.info("Comparison process completed.")

def load_yaml_config(config_file="files_to_compare.yaml"):
    """Load file comparison configuration from YAML."""
    logging.info(f"Loading configuration from {config_file}...")
    try:
        with open(config_file, "r") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logging.error(f"Error loading YAML file: {e}")
        raise

if __name__ == "__main__":
    config = load_yaml_config()
    comparisons = config.get("comparisons", [])

    for files in comparisons:
        logging.info(f"Processing comparison: {files['excel_file']} vs {files['csv_file']}")
        comparator = FileComparator(
            excel_file=files["excel_file"],
            csv_file=files["csv_file"],
            max_rows=files.get("max_rows")  # Use YAML-defined row limit
        )
        comparator.run_comparison()