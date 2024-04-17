import sqlite3

# Update the database schema to include the new category column if it doesn't already exist
# Connect to your SQLite database
conn = sqlite3.connect('menu.db')
c = conn.cursor()

# Check if the category column already exists in the menu table
c.execute('''PRAGMA table_info(menu)''')
columns = c.fetchall()
category_exists = False
for column in columns:
    if column[1] == 'category':
        category_exists = True
        break

# If the category column doesn't exist, add it
if not category_exists:
    c.execute('''ALTER TABLE menu 
                 ADD COLUMN category TEXT NOT NULL DEFAULT 'Uncategorized' ''')

# Commit the changes and close the connection
conn.commit()
conn.close()
