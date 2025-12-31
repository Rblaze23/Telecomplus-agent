"""Load Excel data files into pandas DataFrames.

This module loads all Excel files from the data/xlsx folder.
"""

import pandas as pd
import os
from pathlib import Path


def load_dataframes():
    """Load all Excel files from data/xlsx folder.

    Returns:
        Dictionary mapping table names to pandas DataFrames
        Example: {'clients': DataFrame, 'forfaits': DataFrame, ...}
    """
    # Get the data folder path
    current_dir = Path(__file__).parent
    data_folder = current_dir.parent / "data" / "xlsx"

    if not data_folder.exists():
        raise FileNotFoundError(f"Data folder not found: {data_folder}")

    dfs = {}

    # Load each Excel file
    for file in os.listdir(data_folder):
        if file.endswith('.xlsx'):
            file_path = data_folder / file
            table_name = file.replace('.xlsx', '')

            try:
                df = pd.read_excel(file_path)
                dfs[table_name] = df
                print(
                    f"[DATA] Loaded {table_name}: {df.shape[0]} rows, {df.shape[1]} columns")
            except Exception as e:
                print(f"[ERROR] Failed to load {file}: {e}")

    if not dfs:
        print("[WARNING] No Excel files loaded!")

    return dfs


# Test if run directly
if __name__ == "__main__":
    print("Testing data loading...")
    dataframes = load_dataframes()

    print(f"\nTotal tables loaded: {len(dataframes)}")
    print("\nTable summaries:")
    for name, df in dataframes.items():
        print(f"\n{name}:")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Shape: {df.shape}")
        print(f"  Sample:\n{df.head(2)}")
