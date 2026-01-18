"""Check user password."""
import bcrypt
from sqlalchemy import create_engine, text
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)
conn = engine.connect()

result = conn.execute(text("SELECT email, password_hash FROM users WHERE email='admin@demo.com'"))
row = result.fetchone()

if row:
    print(f"Email: {row[0]}")
    print(f"Hash: {row[1]}")
    print(f"Verify 'admin123': {bcrypt.checkpw(b'admin123', row[1].encode())}")
else:
    print("User not found")

conn.close()
