from django.core.management.utils import get_random_secret_key

secret_key = get_random_secret_key()

with open(".env", "a") as f:
    f.write("\nSECRET_KEY={}\n".format(secret_key))

print("✅ SECRET_KEY generated and added to .env")
