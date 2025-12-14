import os
import time
import psycopg2
from decouple import config

# Load environment variables manually
from pathlib import Path
env_path = Path(__file__).parent / '.env'

def read_env():
    if not env_path.exists():
        return {}
    env = {}
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, val = line.strip().split('=', 1)
                env[key] = val
    return env

env = read_env()

db_name = env.get('DB_NAME') or os.environ.get('DB_NAME')
db_user = env.get('DB_USER') or os.environ.get('DB_USER')
db_password = env.get('DB_PASSWORD') or os.environ.get('DB_PASSWORD')
# FORCE IP ADDRESS
db_host = "13.60.102.132" 
db_port = env.get('DB_PORT') or os.environ.get('DB_PORT')

print(f"Connecting to {db_host}:{db_port} (Direct IP)...")

start = time.time()
try:
    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
        sslmode='require'
    )
    end = time.time()
    print(f"Connection established in {end - start:.4f} seconds")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
