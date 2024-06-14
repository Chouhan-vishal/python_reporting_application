# Shri Laxshmi Stell suppliers Reporting Application

## Description
The Reporting Application is a tool for generating and managing various reports. It includes features for user management, report generation, and report querying.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Functionality](#functionality)
- [Contributing](#contributing)
- [License](#license)

## Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/reporting_application.git
    ```
2. Navigate to the project directory:
    ```bash
    cd reporting_application
    ```
3. Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
4. Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5. Set up the environment variables in a `.env` file:
    ```env
    SSLS_DATABASE_NAME=your_database_name
    SSLS_DATABASE_USER=your_database_user
    SSLS_DATABASE_PASSWORD=your_database_password
    SSLS_DATABASE_HOST=your_database_host
    DATABASE_NAME=reporting_application
    DATABASE_USER=report_manager
    DATABASE_PASSWORD=password
    ```
6. Run database migrations:
    ```bash
    python manage.py migrate
    ```
7. Start the development server:
    ```bash
    python manage.py runserver
    ```

## Usage
After setting up the project, you can access the application by navigating to `http://127.0.0.1:8000` in your web browser. You can create an account, log in, and start generating and managing reports.

## Project Structure
The project consists of the following main directories and files:

```plaintext
.
├── env_reports
├── logs
├── reporting_application
├── reports
│   ├── __pycache__
│   ├── migrations
│   ├── services
│   │   ├── __pycache__
│   │   ├── __init__.py
│   │   ├── report_queries.py
│   │   ├── report_services.py
│   │   ├── report_user_rules.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py
├── users
│   ├── __pycache__
│   ├── migrations
│   ├── services
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py
├── .gitignore
├── db.sqlite3
├── manage.py
├── README.md
├── requirements.txt
├── urls.py
└── views.py
```
# Reporting Application

This project is a Django-based application designed for generating and querying reports, as well as managing user authentication and authorization.

## Project Structure

The project is organized into several key directories and files:

### Directories

- **env_reports**: Contains environment-specific configurations.
- **logs**: Stores log files for the application.

### Main Project Directory

- **reporting_application**: This is the main directory for the Django project, containing essential settings and configurations.

### Apps

#### Reports App

The `reports` app is responsible for report generation and querying. It includes the following key files:

- **services/**: Contains service modules for the reports app.
  - `__init__.py`: Initializes the services module.
  - `report_queries.py`: Defines SQL queries for report generation.
  - `report_services.py`: Provides utility functions and services for report generation, such as creating SQL server connections and fetching data.
  - `report_user_rules.py`: Defines rules for user roles and permissions related to report access.
- `__init__.py`: Initializes the reports app.
- `admin.py`: Contains Django admin configurations for the reports app.
- `apps.py`: Contains the configuration for the reports app.
- `models.py`: Defines the database models for the reports app.
- `tests.py`: Contains test cases for the reports app.
- `urls.py`: Defines URL patterns for the reports app.
- `views.py`: Contains view classes that handle HTTP requests related to report generation and querying.

#### Users App

The `users` app handles user management, authentication, and authorization. It includes the following key files:

- `__init__.py`: Initializes the users app.
- `admin.py`: Contains Django admin configurations for the users app.
- `apps.py`: Contains the configuration for the users app.
- `models.py`: Defines the database models for the users app, including:
  - `User`
  - `OTP`
  - `TwoFactorAuthentication`
  - `ReportPermission`
  - `UserActivityLog`
  - `Hierarchy`
- `serializers.py`: Contains serializers for transforming model instances into JSON format and vice versa.
- `tests.py`: Contains test cases for the users app.
- `urls.py`: Defines URL patterns for the users app.
- `views.py`: Contains view classes that handle HTTP requests related to user management, such as:
  - Login
  - Logout
  - Profile management
  - Password reset
  - User search

### Additional Files

- `manage.py`: The Django management script used for running commands like `runserver`, `migrate`, `createsuperuser`, etc.
- `.gitignore`: Specifies files and directories to be ignored by Git.
- `db.sqlite3`: The SQLite database file used for local development.
- `requirements.txt`: Lists the dependencies required to run the project.
- `urls.py`: Defines the root URL patterns for the project.
- `views.py`: Contains additional view classes if necessary.


