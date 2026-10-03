import sqlite3
conn = sqlite3.connect(r'C:\Users\shyam\OneDrive\Desktop\API\backend\dataflow.db')
print('=== DATASETS ===')
for r in conn.execute('SELECT name, status, row_count, column_count, last_profiled_at FROM datasets'):
    print(f'  {r[0]}: status={r[1]}, rows={r[2]}, cols={r[3]}, profiled={r[4]}')
print('\n=== COLUMNS PER DATASET ===')
for r in conn.execute('SELECT d.name, COUNT(c.id) FROM datasets d LEFT JOIN dataset_columns c ON c.dataset_id=d.id GROUP BY d.id'):
    print(f'  {r[0]}: {r[1]} columns')
print('\n=== QUALITY REPORTS ===')
for r in conn.execute('SELECT d.name, q.overall_score, q.issue_count FROM quality_reports q JOIN datasets d ON d.id=q.dataset_id'):
    print(f'  {r[0]}: score={r[1]}, issues={r[2]}')
conn.close()
