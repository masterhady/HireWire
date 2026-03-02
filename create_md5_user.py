import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

username = "md5_user"
password = "md5_password"
email = "md5@example.com"

if User.objects.filter(username=username).exists():
    print(f"User {username} already exists, deleting...")
    User.objects.get(username=username).delete()

print(f"Creating user {username}...")
user = User.objects.create_user(username=username, email=email, password=password)
print(f"User {username} created with password: {user.password}")
