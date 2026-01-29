import sqlite3
import sys

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Database Tables:")
print("=" * 50)
for table in tables:
    print(f"- {table[0]}")
    
# Check if admin user exists
cursor.execute("SELECT id, username, is_superuser, is_staff FROM auth_user WHERE username='furniquette'")
admin = cursor.fetchone()

if admin:
    print("\n" + "=" * 50)
    print("Admin User Found:")
    print(f"  ID: {admin[0]}")
    print(f"  Username: {admin[1]}")
    print(f"  Is Superuser: {admin[2]}")
    print(f"  Is Staff: {admin[3]}")
else:
    print("\nWARNING: Admin user 'furniquette' not found!")

conn.close()
