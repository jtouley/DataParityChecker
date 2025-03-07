import os
import yaml
import pandas as pd
from datetime import datetime

class FileComparator:
    """
    A class to compare an Excel file with a CSV file to ensure 100% parity.
    It also generates a Markdown report documenting the comparison results.

    Attributes:
        excel_file (str): Path to the Excel file.
        csv_file (str): Path to the CSV file.
        df_excel (pd.DataFrame): DataFrame holding the Excel data.
        df_csv (pd.DataFrame): DataFrame holding the CSV data.
        report_dir (str): Directory to store the comparison reports.
    """

    def __init__(self, excel_file: str, csv_file: str, report_dir="data"):
        """
        Initialize the FileComparator with file paths and setup report directory.

        Args:
            excel_file (str): Path to the Excel file.
            csv_file (str): Path to the CSV file.
            report_dir (str): Directory for saving reports.
        """
        self.excel_file = excel_file
        self.csv_file = csv_file
        self.df_excel = None
        self.df_csv = None
        self.report_dir = report_dir
        self.report_file = self._generate_report_filename()

        # Ensure the report directory exists
        os.makedirs(self.report_dir, exist_ok=True)

    def _generate_report_filename(self) -> str:
        """
        Generate a Markdown report filename based on input filenames.

        Returns:
            str: File path for the markdown report.
        """
        excel_name = os.path.basename(self.excel_file).replace(" ", "_").replace(".", "_")
        csv_name = os.path.basename(self.csv_file).replace(" ", "_").replace(".", "_")
        return os.path.join(self.report_dir, f"Parity_Check_{excel_name}_{csv_name}.md")

    def load_data(self):
        """Load data from the Excel and CSV files into Pandas DataFrames."""
        self.df_excel = pd.read_excel(self.excel_file, dtype=str)
        self.df_csv = pd.read_csv(self.csv_file, dtype=str)

    def normalize_data(self):
        """Normalize column names and sort columns alphabetically for consistent comparison."""
        for df in [self.df_excel, self.df_csv]:
            df.columns = df.columns.str.strip().str.lower()
            df.sort_index(axis=1, inplace=True)

    def sort_rows(self):
        """Sort rows by all columns to remove row order discrepancies."""
        self.df_excel = self.df_excel.sort_values(by=list(self.df_excel.columns)).reset_index(drop=True)
        self.df_csv = self.df_csv.sort_values(by=list(self.df_csv.columns)).reset_index(drop=True)

    def compare_files(self) -> bool:
        """Compare the Excel and CSV DataFrames for parity."""
        if list(self.df_excel.columns) != list(self.df_csv.columns):
            self._generate_report(success=False, message="Column mismatch detected.")
            return False

        if self.df_excel.equals(self.df_csv):
            self._generate_report(success=True)
            return True
        else:
            self._generate_report(success=False, message="Data differences found.")
            return False

    def get_differences(self, output_diff_file="differences.xlsx"):
        """Identify differences and save them to an Excel file if discrepancies exist."""
        diff = self.df_excel.compare(self.df_csv, keep_shape=True, keep_equal=True)
        if not diff.empty:
            diff.to_excel(output_diff_file, index=True)
            print(f"Differences saved to {output_diff_file}")

    def _generate_report(self, success: bool, message: str = ""):
        """Generate a Markdown report summarizing the comparison results."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_content = [
            f"# Data Parity Check Report",
            f"**Timestamp:** {timestamp}",
            f"**Excel File:** `{self.excel_file}`",
            f"**CSV File:** `{self.csv_file}`",
            f"**Status:** {'✅ Files Match' if success else '❌ Files Differ'}",
            "",
            f"### Details",
            f"{message}" if message else "No discrepancies found.",
        ]

        with open(self.report_file, "w") as report:
            report.write("\n".join(report_content))

        print(f"Report saved: {self.report_file}")

    def run_comparison(self):
        """Run the full comparison process and generate reports."""
        self.load_data()
        self.normalize_data()
        self.sort_rows()
        identical = self.compare_files()
        if not identical:
            self.get_differences()


def load_yaml_config(config_file="files_to_compare.yaml"):
    """Load comparison file paths from YAML configuration."""
    with open(config_file, "r") as file:
        return yaml.safe_load(file)


if __name__ == "__main__":
    # Load file pairs from YAML
    config = load_yaml_config()
    comparisons = config.get("comparisons", [])

    # Run comparisons for each file pair
    for files in comparisons:
        comparator = FileComparator(files["excel_file"], files["csv_file"])
        comparator.run_comparison()