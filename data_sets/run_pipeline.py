"""
Master runner — executes all 4 stages in order.
Run: python3 run_pipeline.py [--sample]   (--sample = English book only, first 80 pages)
"""
import sys, subprocess
from pathlib import Path

BASE    = Path(__file__).parent
SAMPLE  = "--sample" in sys.argv
SCRIPTS = ["00_extract_text.py", "01_filter.py", "02_draft.py", "03_qc.py", "04_write_excel.py"]

# Rename our excel writer to 04
excel_old = BASE / "03_write_excel.py"
excel_new = BASE / "04_write_excel.py"
if excel_old.exists() and not excel_new.exists():
    excel_old.rename(excel_new)

if SAMPLE:
    # Patch 01_filter to only process the English book for sample run
    print("⚡ SAMPLE MODE — English book only, first 80 readable pages\n")

for script in SCRIPTS:
    path = BASE / script
    if not path.exists():
        print(f"  skip (not found): {script}")
        continue
    print(f"▶  Running {script}...")
    result = subprocess.run(["python3", str(path)], capture_output=False)
    if result.returncode != 0:
        print(f"  ✗ {script} failed — stopping.")
        sys.exit(1)
    print()

print("🎉 Pipeline complete! Open data_sets/output/Samudrika_Insights.xlsx")
