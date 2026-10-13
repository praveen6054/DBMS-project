# JurisDesk — Legal Case & Client Management System

Python Flask + SQLite demo application for the DBMS project brief.

## Run on Windows
1. Extract this folder.
2. Open the folder in VS Code.
3. In the terminal run: `python -m pip install -r requirements.txt`
4. Run: `python app.py`
5. Open `http://127.0.0.1:5000`

The SQLite database `legal_management.db` is created automatically with demonstration data on first run.

## Modules
Clients, lawyers, cases, lawyer assignments, hearing scheduling with overlap checks, task/deadline tracking, invoices, payments with outstanding-balance validation, and summary reports.

## Academic prototype notes
This is a local demonstration app with sample data, not a production legal records system. The `documents` and `time_entries` tables are included in the relational schema; the basic UI focuses on casework, deadlines, hearings, billing and reports.
