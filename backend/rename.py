import sqlite3
conn = sqlite3.connect(r'C:\Users\shyam\OneDrive\Desktop\API\backend\dataflow.db')
conn.execute("UPDATE users SET full_name=? WHERE email=?", ("Shyam Patil", "shyam@dataflow.io"))
conn.commit()
row = conn.execute("SELECT full_name, email FROM users WHERE email=?", ("shyam@dataflow.io",)).fetchone()
print(f"Updated: {row[0]} ({row[1]})")
conn.close()
