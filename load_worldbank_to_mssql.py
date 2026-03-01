import os
import csv
from decimal import Decimal, InvalidOperation
import pyodbc
from dotenv import load_dotenv

load_dotenv()


def connect() -> pyodbc.Connection:
    driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("MSSQL_SERVER")
    db = os.getenv("MSSQL_DATABASE", "WorldBankDB")
    user = os.getenv("MSSQL_USERNAME")
    pwd = os.getenv("MSSQL_PASSWORD")
    encrypt = os.getenv("MSSQL_ENCRYPT", "no")
    trust = os.getenv("MSSQL_TRUST_CERT", "yes")

    if not server:
        raise ValueError("MSSQL_SERVER is missing in .env")
    if not user or not pwd:
        raise ValueError("MSSQL_USERNAME / MSSQL_PASSWORD are missing in .env")

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={db};"
        f"UID={user};"
        f"PWD={pwd};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust};"
    )
    return pyodbc.connect(conn_str)


def clean_str(v):
    if v is None:
        return None
    v = str(v).strip()
    return v if v else None


def to_int(v):
    v = clean_str(v)
    if v is None:
        return None
    try:
        return int(v)
    except:
        return None


def to_decimal(v):
    """
    Returns Decimal or None. Handles blanks and bad values safely.
    Your schema uses DECIMAL(20,2) / DECIMAL(6,2), so Decimal is ideal.
    """
    v = clean_str(v)
    if v is None:
        return None
    try:
        return Decimal(v)
    except (InvalidOperation, ValueError):
        # try float->Decimal fallback
        try:
            return Decimal(str(float(v)))
        except:
            return None


def get_or_create_country_id(cur, country_name, cache):
    if country_name in cache:
        return cache[country_name]

    cur.execute("SELECT country_id FROM Countries WHERE name = ?", country_name)
    row = cur.fetchone()
    if row:
        cid = int(row[0])
        cache[country_name] = cid
        return cid

    # Insert and fetch inserted id (safe, single round-trip)
    cur.execute(
        "INSERT INTO Countries(name) OUTPUT INSERTED.country_id VALUES (?)",
        country_name,
    )
    cid = int(cur.fetchone()[0])
    cache[country_name] = cid
    return cid


def ensure_year(cur, year, years_cache):
    if year in years_cache:
        return
    # Insert only if not exists
    cur.execute(
        "IF NOT EXISTS (SELECT 1 FROM Years WHERE year = ?) INSERT INTO Years(year) VALUES (?)",
        year, year
    )
    years_cache.add(year)


def upsert_observation(cur, country_id, year, gdp, population, life, unemp, co2, access):
    # First try UPDATE (most efficient if row exists)
    cur.execute(
        """
        UPDATE Observations
        SET gdp_usd = ?,
            population = ?,
            life_expectancy = ?,
            unemployment_rate_pct = ?,
            co2_tons_per_capita = ?,
            access_to_electricity_pct = ?
        WHERE country_id = ? AND year = ?;
        """,
        gdp, population, life, unemp, co2, access, country_id, year
    )

    # If nothing updated, INSERT
    if cur.rowcount == 0:
        cur.execute(
            """
            INSERT INTO Observations
                (country_id, year, gdp_usd, population, life_expectancy,
                 unemployment_rate_pct, co2_tons_per_capita, access_to_electricity_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            country_id, year, gdp, population, life, unemp, co2, access
        )


def load_csv(csv_path="world_bank_dataset.csv", commit_every=1000):
    conn = connect()
    cur = conn.cursor()

    countries_cache = {}
    years_cache = set()

    processed = 0
    upserted = 0
    skipped = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            processed += 1

            country = clean_str(r.get("Country"))
            year = to_int(r.get("Year"))

            if not country or not year:
                skipped += 1
                continue

            # parent tables
            cid = get_or_create_country_id(cur, country, countries_cache)
            ensure_year(cur, year, years_cache)

            # numeric fields
            gdp = to_decimal(r.get("GDP (USD)"))                      # DECIMAL(20,2)
            population = to_int(r.get("Population"))                 # BIGINT
            life = to_decimal(r.get("Life Expectancy"))              # DECIMAL(6,2)
            unemp = to_decimal(r.get("Unemployment Rate (%)"))       # DECIMAL(6,2)
            co2 = to_decimal(r.get("CO2 Emissions (metric tons per capita)"))  # DECIMAL(6,2)
            access = to_decimal(r.get("Access to Electricity (%)"))  # DECIMAL(6,2)

            upsert_observation(cur, cid, year, gdp, population, life, unemp, co2, access)
            upserted += 1

            if upserted % commit_every == 0:
                conn.commit()

    conn.commit()
    cur.close()
    conn.close()

    print(f"Processed: {processed} | Upserted: {upserted} | Skipped: {skipped}")


if __name__ == "__main__":
    load_csv("world_bank_dataset.csv", commit_every=1000)