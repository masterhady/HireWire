import socket
import time

hostname = "aws-1-eu-north-1.pooler.supabase.com"

print(f"Resolving {hostname}...")

# Test 1: gethostbyname (usually IPv4 only, but might still try IPv6 internally depending on libc)
start = time.time()
try:
    ip = socket.gethostbyname(hostname)
    end = time.time()
    print(f"gethostbyname: {ip} in {end - start:.4f}s")
except Exception as e:
    print(f"gethostbyname failed: {e}")

# Test 2: getaddrinfo with AF_INET (Force IPv4)
start = time.time()
try:
    # AF_INET = 2
    info = socket.getaddrinfo(hostname, None, socket.AF_INET)
    ip = info[0][4][0]
    end = time.time()
    print(f"getaddrinfo(AF_INET): {ip} in {end - start:.4f}s")
except Exception as e:
    print(f"getaddrinfo failed: {e}")
