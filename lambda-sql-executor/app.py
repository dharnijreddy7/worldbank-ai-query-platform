def _validate_sql(sql: str):
    if not sql or not sql.strip():
        raise ValueError("Missing 'sql' in request body")

    sql = sql.strip()

    # Extract first SELECT or WITH statement if model added extra text
    match = re.search(r"(SELECT|WITH)\b.*", sql, re.IGNORECASE | re.DOTALL)
    if match:
        sql = match.group(0).strip()

    # Block dangerous keywords
    if _BLOCKLIST.search(sql):
        raise ValueError("Blocked keyword detected. Only read-only queries are allowed")

    # Must start strictly with SELECT or WITH
    if not _READONLY_START.match(sql):
        raise ValueError("Only read-only SELECT/WITH queries are allowed")

    # Optional: remove trailing semicolon
    if sql.endswith(";"):
        sql = sql[:-1]

    return sql