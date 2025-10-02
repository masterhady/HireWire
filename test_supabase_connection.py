import psycopg2
from psycopg2 import OperationalError

def test_connection():
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres.nwdzqvxtrgahhexgmeca",
            password="RZ.3cw@H45+ZLr*",  # 🔑 غيريها بالباسورد
            host="aws-1-eu-north-1.pooler.supabase.com",
            port="6543",
            sslmode="require"
        )
        print("✅ Connection successful!")
        conn.close()
    except OperationalError as e:
        print("❌ Connection failed!")
        print(e)

if __name__ == "__main__":
    test_connection()
