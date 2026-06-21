#!/bin/bash
echo "=== OCR Progress ==="
for f in ~/Desktop/samudrika_lakshana/data_sets/raw_text/*.json; do
  key=$(basename "$f" .json)
  pages=$(python3 -c "import json; d=json.load(open('$f')); print(len(d.get('pages',[])))" 2>/dev/null)
  done=$(python3 -c "import json; d=json.load(open('$f')); print(sum(1 for p in d.get('pages',[]) if p.get('readable')))" 2>/dev/null)
  echo "  $key: $pages pages ($done readable)"
done
echo ""
echo "=== Excel rows so far ==="
python3 -c "
import openpyxl, os
f = os.path.expanduser('~/Desktop/samudrika_lakshana/data_sets/output/Samudrika_Insights.xlsx')
if os.path.exists(f):
    wb = openpyxl.load_workbook(f)
    for s in wb.sheetnames:
        print(f'  {s}: {wb[s].max_row-1} rows')
else:
    print('  (not generated yet)')
" 2>/dev/null
