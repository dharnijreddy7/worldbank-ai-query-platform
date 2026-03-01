# World Bank Data Loader: Step-by-Step Guide

This document summarizes all steps taken to set up, configure, and run the World Bank data loader for Microsoft SQL Server (MSSQL).

---

## 1. Project Setup
- Created a project directory with:
  - `create_worldbankdb.sql` (SQL schema)
  - `world_bank_dataset.csv` (data)
  - `requirements.txt` (Python dependencies)

## 2. Python Environment
- Set up a Python virtual environment (e.g., `.venv`).
- Activated the environment:
  ```powershell
  & .venv\Scripts\Activate.ps1
  ```

## 3. Install Dependencies
- Added required packages to `requirements.txt`:
  - `pyodbc` (MSSQL connection)
  - `pandas` (CSV handling)
  - `python-dotenv` (load .env files)
- Installed dependencies:
  ```powershell
  pip install -r requirements.txt
  ```

## 4. Database Schema
- Used `create_worldbankdb.sql` to create tables in MSSQL:
  - `Countries`
  - `Years`
  - `Observations`
- Ran the SQL script in my MSSQL instance.

## 5. Environment Variables
- Created `.env.example` as a template for connection variables.
- Created `.env` for my actual credentials:
  ```dotenv
  MSSQL_SERVER=awsmssqlrds.c4fssmou4qmi.us-east-1.rds.amazonaws.com
  MSSQL_DATABASE=WorldBankDB
  MSSQL_DRIVER=ODBC Driver 18 for SQL Server
  MSSQL_TRUSTED=yes
  MSSQL_TRUST_SERVER_CERT=yes
  # If using SQL authentication:
  # MSSQL_TRUSTED=no
  # MSSQL_UID=your_user
  # MSSQL_PWD=your_password
  ```

## 6. Loader Script
- Created `load_worldbank_to_mssql.py`:
  - Reads `.env` automatically (via `python-dotenv`).
  - Connects to MSSQL using `pyodbc`.
  - Loads data from `world_bank_dataset.csv`.

  - Inserts/updates rows in `Countries`, `Years`, and `Observations`.

  - Handles SSL/trust issues with `MSSQL_TRUST_SERVER_CERT`.



## 7. Running the Loader
