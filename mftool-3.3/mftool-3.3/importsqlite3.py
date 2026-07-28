import sqlite3
import pandas as pd
from mftool import Mftool

# 1. Initialize mftool and database connection
mf = Mftool()
conn = sqlite3.connect("mutual_funds.db")
cursor = conn.cursor()

# 2. Create a table for scheme details (if you want manual SQL inserts)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheme_info (
        scheme_code TEXT PRIMARY KEY,
        scheme_name TEXT
    )
""")
conn.commit()

# 3. Fetch data using mftool
# Let's search for some schemes and save them
results = mf.search_schemes("Mirae Asset")

# Option A: Insert using standard sqlite3 execution
for scheme in results[:10]: # Saving top 10 results as an example
    cursor.execute("""
        INSERT OR REPLACE INTO scheme_info (scheme_code, scheme_name)
        VALUES (?, ?)
    """, (scheme['code'], scheme['name']))
conn.commit()

# Option B: If working with historical NAV Dataframes, Pandas makes SQLite integration effortless:
# history_df = mf.history(code='118549', period='1yr') # Example scheme code
# history_df.to_sql('nav_history_118549', conn, if_exists='replace', index=True)

# 4. Query your SQLite database to verify
print("--- Data queried from SQLite database ---")
query_results = cursor.execute("SELECT * FROM scheme_info LIMIT 5")
for row in query_results:
    print(f"Code: {row[0]} | Name: {row[1]}")

# Close connection when done
conn.close()