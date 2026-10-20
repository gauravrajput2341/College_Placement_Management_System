# College Placement Management System (CPMS)

A web-based **College Placement Management System** built with Python, Flask, and MySQL to simplify campus recruitment workflows by connecting students, recruiters, and administrators through a centralized platform.

## Overview

The College Placement Management System (CPMS) helps manage student accounts, company registrations, resume submissions, placement eligibility, and applicant shortlisting. It provides separate workflows for students, companies, and administrators to make placement activities more organized and efficient.

## Key Features

### Student Module
- Student registration and login.
- Resume upload and management.
- Access to relevant placement opportunities.
- Job matching and eligibility checking.

### Company Module
- Company registration and login.
- Manage recruitment-related activities.
- Review student applications.
- Sort and shortlist applicants.

### Admin Module
- Dedicated admin dashboard.
- Centralized management of placement activities.
- Administrative access to relevant platform information.

### Matching and Shortlisting
- Resume-based job matching.
- Eligibility checking for placement opportunities.
- Applicant sorting to support recruiter screening.
- Shortlisting workflow for candidate selection.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Flask | Web application framework |
| MySQL | Relational database |
| HTML | Web page structure |
| Jinja2 | Dynamic page rendering through Flask templates |

## Project Structure

```text
College_Placement_Management_System/
├── Templates/
│   ├── admin.html
│   ├── admin_applicants.html
│   ├── admin_login.html
│   ├── company.html
│   ├── company_login.html
│   ├── company_register.html
│   ├── login.html
│   ├── register.html
│   └── student.html
├── app.py
├── admin.py
├── matcher.py
├── resume_utils.py
├── requirements.txt
├── schema.sql
├── admin.sql
├── dashboard.sql
├── rebuild.sql
├── sortlist.sql
├── reset_admin.py
├── backup_app.py
└── .gitignore
```

## Getting Started

### Prerequisites

Install the following before running the project:

- Python 3.x
- MySQL Server
- Git
- pip

### 1. Clone the Repository

```bash
git clone https://github.com/gauravrajput2341/College_Placement_Management_System.git
cd College_Placement_Management_System
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure MySQL

1. Start your MySQL server.
2. Create the database required by the application.
3. Review `schema.sql` and the other SQL scripts to understand the database structure and setup requirements.
4. Configure your local database connection settings in `config.py` according to the variables expected by the application.

**Security note:** Keep database passwords and other secrets in your local configuration. Do not commit `config.py`, passwords, or private user data to GitHub.

### 5. Run the Application

After completing the database setup and local configuration, run:

```bash
python app.py
```

Open the local URL printed in the terminal to access the application.

> Note: Database initialization and configuration details may need to be adjusted according to the SQL scripts and settings in your local environment.

## Security

- Do not publish database credentials or secret keys.
- Keep private configuration files out of version control.
- Do not commit real student resumes or personal records.
- Use secure passwords and appropriate access controls when deploying the application.

## Future Improvements

Potential improvements include automated testing, stronger input validation, improved error handling, deployment configuration, and more comprehensive placement analytics.

## Author

**Gaurav Rajput**

GitHub: [@gauravrajput2341](https://github.com/gauravrajput2341)

## License

No license has been specified yet. Add a license if you intend to define how others may use, modify, and distribute this project.
