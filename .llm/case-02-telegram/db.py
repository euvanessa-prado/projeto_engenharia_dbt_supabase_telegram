import os
import yaml
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


def _get_engine():
    postgres_url = os.getenv("POSTGRES_URL")
    if postgres_url:
        return create_engine(postgres_url)

    profiles_path = os.path.join(os.path.expanduser("~"), ".dbt", "profiles.yml")
    with open(profiles_path, "r") as f:
        profiles = yaml.safe_load(f)
    dev = profiles["ecommerce"]["outputs"]["dev"]
    url = (
        f"postgresql+psycopg2://{dev['user']}:{dev['pass']}"
        f"@{dev['host']}:{dev['port']}/{dev['dbname']}"
    )
    return create_engine(url)


def execute_query(sql: str) -> pd.DataFrame:
    sql_clean = sql.strip().upper()
    if not (sql_clean.startswith("SELECT") or sql_clean.startswith("WITH")):
        raise ValueError("Apenas queries SELECT ou WITH são permitidas.")

    engine = _get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df
