import pandas as pd
import xlrd
import string
import random
import os
import re
import sqlalchemy as sa

from forge.sdk import ForgeLogger
from ..registry import ability

LOG = ForgeLogger(__name__)

async def id_generator(size=8, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

@ability(
    name="read_excel_to_df",
    description="Read data from Excel file and return a DataFrame in dictionary format. Use when needing to extract data from excel file.",
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
    output_type="dict"
)
async def read_excel_to_df(agent, task_id: str, excel_file_path: str, sheet_name: str = None) -> dict:
    """Reads an Excel sheet and returns the data as a DataFrame.

    Args:
    excel_file_path: The path to the Excel file.
    sheet_name: The name of the Excel sheet to read. If None, the first sheet
        will be read.quit

    Returns:
    A dictionary containing the temporary table name and other metadata for agent to use.
    """
    sheet_name_found = xlrd.open_workbook(excel_file_path, on_demand=True).sheet_names()
    sheet_name = sheet_name if sheet_name in sheet_name_found else sheet_name_found[0]
    df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
    df.columns = df.columns.str.replace(' ', '_')
    
    # adding dataframe to temporary sql table
    temp_table_name = await id_generator(chars=string.ascii_lowercase+string.ascii_uppercase)
    n_rows = df.to_sql(
        name=temp_table_name,
        con="sqlite:///agent.db",
        if_exists="replace"
    )
    
    # metadata for access
    metadata = {
        "operation": f"The data from the excel_file {excel_file_path} was loaded into a temporary table. Please use the following information to access the data.",
        "table_name": temp_table_name,
        "con": "sqlite:///autogpts/InsightEngineAgent/agent.db",
        "n_rows": n_rows,
        "columns": df.columns.tolist(),
        "dtypes": df.dtypes.to_dict(),
        "shape": df.shape,
    }
    return metadata

@ability(
    name="select_from_table",
    description="""Selects data from a table using SQL and insert into a temporary table. With this you can manipulate data, calculate, aggregate and other operations.
        If a table_name is provided, use that.""",
    parameters=[
        {
            "name": "sql_query",
            "description": "The SQL query to run. All column names must be wrapped in double quotes (\").",
            "type": "string",
            "required": True,
        },
        {
            "name": "connection_string",
            "description": "The connection string to the database.",
            "type": "string",
            "required": False,
        }
    ],
    output_type="dict"
)
async def select_from_table(agent, task_id: str, sql_query: str, connection_string: str = "sqlite:////home/jfeli/AutoGPTIE/autogpts/InsightEngineAgent/agent.db") -> dict:
    """Selects data from a table and insert into a temporary table.

    Args:
    table_name: The name of the table to select from.
    connection_string: The connection string to the database.

    Returns:
    A dictionary containing the temporary table name and other metadata for agent to use.
    """
    # query data from table
    df = pd.read_sql(sql_query, "sqlite:////home/jfeli/AutoGPTIE/autogpts/InsightEngineAgent/agent.db")
    
    # adding dataframe to temporary sql table
    temp_table_name = await id_generator(chars=string.ascii_lowercase+string.ascii_uppercase)
    n_rows = df.to_sql(
        name=temp_table_name,
        con="sqlite:////home/jfeli/AutoGPTIE/autogpts/InsightEngineAgent/agent.db",
        if_exists="replace"
    )
    
    # metadata for access
    metadata = {
        "operation": f"The data retrieved from {sql_query} was loaded into a temporary table. Please use the following information to access the data.",
        "table_name": temp_table_name,
        "con": "sqlite:////home/jfeli/AutoGPTIE/autogpts/InsightEngineAgent/agent.db",
        "n_rows": n_rows,
        "columns": ["'"+col+"'" for col in df.columns],
        "dtypes": df.dtypes.to_dict(),
        "shape": df.shape,
    }
    return metadata

@ability(
    name="pg_to_df_rquery",
    description="Connects to a PostgreSQL local database and runs a query, returning the table as a DataFrame. Use this when asked to query for data only available in PostgreSQL database listed in resources.",
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
async def pg_to_df_rquery(agent, task_id: str, query: str, database: str = "postgres", user: str = "postgres", password: str = "postgres", host: str = "localhost", port: int = 5432):
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

@ability(
    name="build_graph",
    description="Generate data for building a graph. Use when needing to show a graph using CanvasJS (Angular).",
    parameters=[
        {
            "name": "query",
            "type": "string",
            "description": "The query to be executed to fetch data from a table. Remember to format the column names with double quotes (\") and rename them to X and Y according to their graph axes.",
            "required": True,
        }
    ],
    output_type="list"
)
async def build_graph(agent, task_id: str, query: str) -> list:
    """Returns data to be used on a graph visualization with Angular.

    Args:
    query: The query to be executed to fetch data from a table.

    Returns:
    A list containing the data to be used on a graph visualization.
    """
    task = await agent.db.get_task(task_id)
    df = pd.read_sql(query, "sqlite:////home/jfeli/AutoGPTIE/autogpts/InsightEngineAgent/agent.db")
    df = df.astype(str)
    
    return {'data': df.to_json(orient="records"), 'task': task.input}