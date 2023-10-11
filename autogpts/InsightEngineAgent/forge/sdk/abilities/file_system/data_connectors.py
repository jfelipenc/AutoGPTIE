import pandas as pd
import sqlalchemy as sa

from forge.sdk import ForgeLogger
from ..registry import ability

@ability(
    name="read_excel_to_df",
    description="Reads an Excel sheet and returns the data as a DataFrame.",
    parameters=[
        {
            "name": "excel_file_path",
            "type": "string",
            "description": "The path to the Excel file.",
            "required": True,
        },
        {
            "name": "sheet_name",
            "type": "string",
            "description": "The name of the Excel sheet to read. If None, the first sheet will be read.",
            "required": False,
        }
    ],
    output_type="pandas.DataFrame"
)
def read_excel_to_df(agent, task_id: str, excel_file_path: str, sheet_name: str = None):
  """Reads an Excel sheet and returns the data as a DataFrame.

  Args:
    excel_file_path: The path to the Excel file.
    sheet_name: The name of the Excel sheet to read. If None, the first sheet
      will be read.

  Returns:
    A Pandas DataFrame containing the data in the Excel sheet.
  """

  df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
  return df

@ability(
    name="pg_to_df_rquery",
    description="Connects to a PostgreSQL local database and runs a query, returning the table as a DataFrame.",
    parameters=[
        {
            "name": "query",
            "type": "string",
            "description": "The SQL query to run.",
            "required": True,
        },
        {
            "name": "database",
            "type": "string",
            "description": "The name of the database to connect to.",
            "required": False,
        },
        {
            "name": "user",
            "type": "string",
            "description": "The username to use to connect to the database.",
            "required": False,
        },
        {
            "name": "password",
            "type": "string",
            "description": "The password to use to connect to the database.",
            "required": False,
        },
        {
            "name": "host",
            "type": "string",
            "description": "The hostname of the database server.",
            "required": False,
        },
        {
            "name": "port",
            "type": "integer",
            "description": "The port of the database server.",
            "required": False,
        }
    ],
    output_type="pandas.DataFrame"
)
def pg_to_df_rquery(agent, task_id: str, query: str, database: str = "postgres", user: str = "postgres", password: str = "postgres", host: str = "localhost", port: int = 5432):
  """Connects to a PostgreSQL local database and runs a query, returning the table as a DataFrame.

  Args:
    query: The SQL query to run.
    database: The name of the database to connect to.
    user: The username to use to connect to the database.
    password: The password to use to connect to the database.
    host: The hostname of the database server.
    port: The port of the database server.

  Returns:
    A Pandas DataFrame containing the results of the query.
  """

  engine = sa.create_engine(f"postgresql://{user}:{password}@{host}:{port}/{database}")
  conn = engine.connect()
  df = pd.read_sql(query, conn)
  conn.close()
  return df