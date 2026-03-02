import boto3
import json
import base64
import re

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
lambda_client = boto3.client("lambda")

SQL_EXECUTOR = "dharnij-sql-lambda"

# Safety enforcement
_SELECT_ONLY = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_BLOCKLIST = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


def _response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body, default=str),
    }


def _parse_event(event: dict) -> dict:
    if "body" in event:
        raw = event["body"] or ""

        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode("utf-8")

        if isinstance(raw, str) and raw.strip():
            try:
                return json.loads(raw)
            except Exception:
                return {}

        return {}

    return event


def generate_sql(question: str) -> str:
    prompt = f"""
You are a STRICT SQL generator for Microsoft SQL Server.

DATABASE SCHEMA:

dbo.Countries(
  country_id INT,
  name NVARCHAR
)

dbo.Observations(
  country_id INT,
  year INT,
  gdp_usd DECIMAL,
  population BIGINT,
  life_expectancy DECIMAL,
  unemployment_rate_pct DECIMAL,
  co2_tons_per_capita DECIMAL,
  access_to_electricity_pct DECIMAL
)

CRITICAL RULES:

1. ALWAYS use dbo schema.
2. ALWAYS JOIN Countries and Observations properly:
   dbo.Countries.country_id = dbo.Observations.country_id
3. If filtering by year and unsure about availability,
   use: year = (SELECT MAX(year) FROM dbo.Observations)
4. Output MUST start with SELECT or WITH.
5. ONLY read-only queries allowed.
6. DO NOT output explanations.
7. DO NOT output markdown.
8. DO NOT output comments.
9. NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, MERGE, EXEC.
10. If unsure, output: SELECT 1 WHERE 1=0

Return SQL ONLY.

User question:
{question}
"""

    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "temperature": 0.0,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            }
        ),
    )

    result = json.loads(response["body"].read())
    sql = result["content"][0]["text"].strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()

    return sql


def _validate_sql(sql: str) -> bool:
    if not sql:
        return False

    if not _SELECT_ONLY.search(sql):
        return False

    if _BLOCKLIST.search(sql):
        return False

    return True


def lambda_handler(event, context):
    try:
        body = _parse_event(event)

        question = body.get("question")
        if not question or not str(question).strip():
            return _response(400, {"error": "Missing question."})

        question = str(question).strip()

        # Generate SQL
        sql = generate_sql(question)

        # Validate SQL
        if not _validate_sql(sql):
            return _response(
                400,
                {
                    "error": "Unsafe or invalid SQL generated.",
                    "generated_sql": sql,
                },
            )

        # Invoke SQL Executor (Lambda2)
        invoke_payload = {
            "sql": sql,
            "params": [],
            "max_rows": 100,
        }

        resp = lambda_client.invoke(
            FunctionName=SQL_EXECUTOR,
            InvocationType="RequestResponse",
            Payload=json.dumps(invoke_payload).encode("utf-8"),
        )

        result = json.loads(resp["Payload"].read())

        # Decode Lambda2 proxy response
        if isinstance(result, dict) and "body" in result:
            try:
                data = json.loads(result["body"])
            except Exception:
                data = result["body"]
        else:
            data = result

        return _response(
            200,
            {
                "generated_sql": sql,
                "data": data,
            },
        )

    except Exception as e:
        return _response(500, {"error": str(e)})