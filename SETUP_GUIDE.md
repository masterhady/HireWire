# Project Setup Guide

This guide will help you set up and run the AI Project MVP backend locally on your computer.

## Prerequisites

### For Everyone
- A computer running Windows, macOS, or Linux
- Internet connection
- Basic familiarity with command line/terminal

### For Frontend Developers
- Node.js knowledge (for future frontend integration)
- Understanding of REST APIs
- Experience with authentication (JWT tokens)

---

## Step 1: Install Python

### Windows
1. Go to [python.org](https://www.python.org/downloads/)
2. Download Python 3.8 or newer
3. Run the installer
4. **IMPORTANT**: Check "Add Python to PATH" during installation
5. Verify installation by opening Command Prompt and typing:
   ```cmd
   python --version
   ```
   You should see something like `Python 3.8.10`

### macOS
1. Open Terminal
2. Install Homebrew (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Install Python:
   ```bash
   brew install python
   ```
4. Verify installation:
   ```bash
   python3 --version
   ```

### Linux (Ubuntu/Debian)
1. Open Terminal
2. Update package list:
   ```bash
   sudo apt update
   ```
3. Install Python and pip:
   ```bash
   sudo apt install python3 python3-pip python3-venv
   ```
4. Verify installation:
   ```bash
   python3 --version
   ```

---

## Step 2: Install Git (if not already installed)

### Windows
- Download from [git-scm.com](https://git-scm.com/download/win)
- Run the installer with default settings

### macOS
```bash
brew install git
```

### Linux
```bash
sudo apt install git
```

---

## Step 3: Download the Project

1. Open Terminal/Command Prompt
2. Navigate to your desired folder (e.g., Desktop):
   ```bash
   cd ~/Desktop
   ```
3. Clone the project:
   ```bash
   git clone <repository-url>
   ```
   Or if you have the project files, navigate to the project folder:
   ```bash
   cd AI_Project_MVP/core
   ```

---

## Step 4: Set Up Virtual Environment

### What is a Virtual Environment?
A virtual environment is like a separate container for your project's dependencies. It prevents conflicts between different projects.

### Create Virtual Environment
1. Navigate to the project folder:
   ```bash
   cd /path/to/AI_Project_MVP/core
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   ```
   (On some systems, use `python3` instead of `python`)

3. Activate virtual environment:

   **Windows:**
   ```cmd
   venv\Scripts\activate
   ```

   **macOS/Linux:**
   ```bash
   source venv/bin/activate
   ```

4. You should see `(venv)` at the beginning of your command prompt, indicating the virtual environment is active.

---

## Step 5: Install Dependencies

With the virtual environment activated, install required packages:

```bash
pip install -r requirements.txt
```

This will install:
- Django (web framework)
- Django REST Framework (API framework)
- JWT authentication
- PostgreSQL database connector
- CORS headers support
- Image processing library

---

## Step 6: Database Configuration

### Option A: Use Supabase (Recommended)
1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to Settings > Database
4. Copy your database credentials
5. Create a `.env` file in the project root:
   ```bash
   touch .env
   ```
6. Add your credentials to `.env`:
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   USE_SQLITE=False
   
   DB_NAME=your-database-name
   DB_USER=your-database-user
   DB_PASSWORD=your-database-password
   DB_HOST=your-database-host
   DB_PORT=5432
   DB_SSLMODE=require
   ```

### Option B: Use SQLite (For Testing Only)
1. Create a `.env` file:
   ```bash
   touch .env
   ```
2. Add to `.env`:
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   USE_SQLITE=True
   ```

---

## Step 7: Run Database Migrations

This creates the necessary database tables:

```bash
python manage.py migrate
```

---

## Step 8: Create Admin User (Optional)

Create a superuser account for the Django admin panel:

```bash
python manage.py createsuperuser
```

Follow the prompts to set username, email, and password.

---

## Step 9: Start the Server

```bash
python manage.py runserver 0.0.0.0:8080
```

You should see:
```
Watching for file changes with StatReloader
Performing system checks...
System check identified some issues:
WARNINGS:
?: (staticfiles.W004) The directory '/path/to/static' in the STATICFILES_DIRS setting does not exist.
System check identified 1 issue (0 silenced).
October 01, 2025 - 12:24:53
Django version 4.2.24, using settings 'core.settings'
Starting development server at http://0.0.0.0:8080/
Quit the server with CONTROL-C.
```

---

## Step 10: Test the API

### Test in Browser
Open your browser and go to:
- `http://localhost:8080/api/skills/` (should show skills data)
- `http://localhost:8080/admin/` (Django admin panel)

### Test with cURL
Open a new terminal and test:

```bash
# Test skills endpoint (public)
curl http://localhost:8080/api/skills/

# Test registration
curl -X POST http://localhost:8080/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123",
    "email": "test@example.com",
    "role": "jobseeker"
  }'
```

---

## Troubleshooting

### Common Issues

#### 1. "python: command not found"
- **Solution**: Use `python3` instead of `python`
- **Alternative**: Add Python to your system PATH

#### 2. "pip: command not found"
- **Solution**: Use `python -m pip` instead of `pip`
- **Alternative**: Install pip separately

#### 3. "Permission denied" errors
- **Solution**: Don't use `sudo` with pip in virtual environments
- **Alternative**: Check file permissions

#### 4. Database connection errors
- **Solution**: Verify your `.env` file has correct database credentials
- **Alternative**: Use SQLite for testing (`USE_SQLITE=True`)

#### 5. "Port already in use"
- **Solution**: Use a different port:
  ```bash
  python manage.py runserver 0.0.0.0:8081
  ```

#### 6. Virtual environment not activating
- **Windows**: Use `venv\Scripts\activate.bat`
- **macOS/Linux**: Use `source venv/bin/activate`

### Getting Help

1. Check the terminal output for error messages
2. Verify all steps were completed correctly
3. Ensure virtual environment is activated (you should see `(venv)` in prompt)
4. Check that all dependencies are installed: `pip list`

---

## For Frontend Developers

### API Integration

The backend provides a REST API that your frontend can consume:

#### Base URL
```
http://localhost:8080/api/
```

#### Authentication Flow
1. Register user: `POST /auth/register/`
2. Login: `POST /auth/login/` → get access token
3. Use token in headers: `Authorization: Bearer <token>`

#### Key Endpoints
- **Public**: `/skills/`, `/auth/register/`, `/auth/login/`
- **Protected**: All other endpoints require JWT token

#### Example Frontend Integration (JavaScript)
```javascript
// Login and get token
const login = async (username, password) => {
  const response = await fetch('http://localhost:8080/api/auth/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password })
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access);
  return data;
};

// Use token for protected requests
const fetchCompanies = async () => {
  const token = localStorage.getItem('access_token');
  const response = await fetch('http://localhost:8080/api/companies/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
};
```

### CORS Configuration
The backend is configured to allow requests from any origin for development. For production, update CORS settings in `core/settings.py`.

---

## Project Structure

```
core/
├── api/                    # Main API app
│   ├── models.py          # Database models
│   ├── views.py           # API views
│   ├── serializers.py     # Data serializers
│   └── urls.py            # URL routing
├── core/                  # Django settings
│   ├── settings.py        # Main configuration
│   └── urls.py            # Root URL config
├── venv/                  # Virtual environment
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
└── API_DOCUMENTATION.md   # Complete API docs
```

---

## Next Steps

1. **Explore the API**: Use the provided API documentation
2. **Test endpoints**: Try different API calls with Postman or cURL
3. **Build frontend**: Create your frontend application
4. **Deploy**: When ready, deploy to a cloud platform

---

## Support

If you encounter issues:
1. Check this guide first
2. Look at the terminal output for error messages
3. Verify all prerequisites are installed
4. Ensure virtual environment is activated
5. Check database configuration

Remember: The virtual environment must be activated every time you work on the project!
