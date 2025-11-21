# Copyright 2025 CNOE
# SPDX-License-Identifier: Apache-2.0

import logging
import uuid
import asyncpg

from collections.abc import AsyncIterable
from typing import Any, Literal, Dict

from pydantic import BaseModel
from dotenv import load_dotenv
from strands.models.litellm import LiteLLMModel
from strands import Agent, tool
import os

from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from context_vars import get_access_token
logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.environ.get('OPENAI_API_KEY').strip()
db_url_value = os.environ.get('postgres_url').strip()

"""
           1. which user has done most sales share their names with total amount
           2. list top 5 total sales of each user in descending order . share usernames and customer names for each user and date of sale in mm-dd-yyyy format. If user has multiple customers , split by different rows
           3. list all customers and their contact info
           4. show me largest sale happened in 2025
           5. show me largest sale happened in 2024
           6. show me largest sale happened in 2024. If identified, show me customer name, user name,  amount and date
           7. show me smallest sale . If identified, show me customer name, user name,  amount and date
           8. show me a table view of sales done by Ivy and Eve in 2024
           9. what are the top 2 sales. share usernames and customer names for each user and date of sale
           10. what are the lowest sales in year 2024. share usernames and customer names for each user and date of sale
           11. top 5 customers with total number of sales with total sale amount more than 3700
           12. top 5 customers with total number of sales
           """


class DBAgent:

    def __init__(self):
        print(":::::::api_key::::", api_key)
        self.model = LiteLLMModel(
            client_args={
                "api_key": api_key,
                # "api_base": None,
                "base_url": None,
                #  "use_litellm_proxy": False,
            },
            # **model_config
            model_id="openai/gpt-4o",
            params={
                # "max_tokens": 500,
                "temperature": 0.75,
            }
        )
        self.agent = None
        self._initialized = False
        self.agent_cache: dict[str, Agent] = {}

        print("::::::::::::::::::initializing agent")

    def format_table(self, rows):
        """
        Formats query results as a table string.

        Args:
            rows: List of dicts representing query results

        Returns:
            str: Formatted table as string
        """
        if not rows:
            return "No results."

        headers = list(rows[0].keys())
        widths = [max(len(str(h)), *(len(str(r.get(h, "")))
                      for r in rows)) for h in headers]

        # Create header
        header_line = " | ".join(str(h).ljust(w)
                                 for h, w in zip(headers, widths))
        sep_line = "-+-".join("-" * w for w in widths)

        # Create rows
        table_lines = [header_line, sep_line]
        for r in rows:
            row_line = " | ".join(str(r.get(h, "")).ljust(w)
                                  for h, w in zip(headers, widths))
            table_lines.append(row_line)

        return "\n".join(table_lines)

    async def run_sql_query(self, sql_query):
        """
        Executes a SQL query from agent output.

        Args:
            sql_query : Should be valid sql query.

        Returns:
            list: Query results as a list of dicts.
        """
       # db_url = "postgresql://admin:admin@localhost:5432/ai"
        db_url = db_url_value
        conn = await asyncpg.connect(db_url)
        try:
            print(f"sql_query: before running::: {sql_query}")
            params = []
            rows = await conn.fetch(sql_query, *params)
            # Convert asyncpg Record objects to dicts
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    async def generate_sql_query(self, user_query: str) -> str:
        """
        Generates a valid SQL query for a given user prompt.

        Args:
            user_query (str): The user prompt or query in natural language

        Returns:
            str: Returns a SQL query for executing in PostgreSQL
        """
        prompt = """
        You are a PostgreSQL specialized agent.

        Your tasks:
        - When given a question about the data, generate a SQL query that can be executed in PostgreSQL.
        - Always specify the table(s) the query should be run on.
        - Extract the following information and return ONLY valid plain sql query without any extra text or quotes or single quotes. Do not prefix with sql like ```sql. Do not add sql code fencing. I take this query and run using asyncpg python library.


        RULES:
        - Retrieve only the JSON object, no explanatory text
        - If query is not generated, use null for strings/arrays
        - Use valid table names for the FROM/JOIN clauses
        - Use valid SQL syntax for PostgreSQL
        - For analytical questions (e.g., totals, maximums, rankings, or involving multiple tables), use SQL aggregation functions and JOINs as needed.
        - For questions involving multiple users or multiple sales or multiple customers, use a single query with the IN operator to match all relevant userids and maps all users corrects when joining.
        - Always try to answer with a single query when possible.
        - For questions involving "most", "highest", "top", or "for which customer", use the appropriate aggregation and join clauses.
        - Always output the SQL query as a string
        - sometimes user gives firstname , lastname and customer name in lower case , in sql query include to match case insensitive
        - For questions that require grouping results by user and including related details (such as customer names and sale dates), use aggregation functions like SUM for totals and array_agg for collecting related values (e.g., customer names, sale dates) per user.
        - The output should be one row per user, with total sales, a list of customer names, and a list of sale dates for that user.
        - Always order the results by total sales in descending order unless otherwise specified.
        - Use array_agg(DISTINCT ...) for customer names to avoid duplicates.
        - Ensure the query is compatible with PostgreSQL and can be executed as-is.
        - please use documentation if anytime you are confused and you need help with generating complex and optimized using this url https://neon.com/postgresql/tutorial and use http_request tool
        - If the user does not specify a threshold for "weak sales", you may calculate a threshold such as the 25th percentile or the minimum sales amount, and use that in the query. Mention this in your summary.

        Below are the PostgreSQL table schemas:

        users table:
            userid SERIAL PRIMARY KEY,
            firstname TEXT,
            lastname TEXT,
            emailid TEXT,
            gender TEXT

        address table:
            addressid SERIAL PRIMARY KEY,
            userid INT REFERENCES users(userid),
            street TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            country TEXT

        customers table:
            customerid SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            address TEXT

        sales table:
            saleid SERIAL PRIMARY KEY,
            userid INT REFERENCES users(userid),
            customerid INT REFERENCES customers(customerid),
            date DATE,
            amount NUMERIC

        Example record for users: (1, 'Alice', 'Smith', 'alice.smith@example.com', 'Female')
        Example record for address: (1, '123 Main St', 'New York', 'NY', '10001', 'USA')
        Example record for customers: ('Acme Corp', 'contact@acmecorp.com', '555-1001', '100 Acme Way, New York, NY')
        Example record for sales: (1, 1, 101, '2024-01-05', 250.00)
        """
        agent = Agent(model=self.model, callback_handler=None,
                      system_prompt=prompt, tools=[])
        full_response = ""
        agent_stream = agent.stream_async(user_query)
        async for event in agent_stream:
            if "data" in event:
                chunk = event["data"]
                full_response += chunk
            elif 'result' in event:
                result = event['result']
                if hasattr(result, 'metrics') and result.metrics:
                    if hasattr(result.metrics, 'accumulated_usage') and result.metrics.accumulated_usage:
                        total_tokens = result.metrics.accumulated_usage.get(
                            'totalTokens', 0)
        print(f"\n{total_tokens}")
        print(f"SQL query from agent::: {full_response} \n\n {total_tokens}")
        return full_response, total_tokens

    async def stream(
        self, query: str, context_id: str | None = None
    ) -> AsyncIterable[dict[str, Any]]:
        logger.debug(
            f"Starting stream with query: {query} and context_id: {context_id}")
        arguments = {'user_query': query}
        yield {
            'is_task_complete': False,
            'require_user_input': False,
            'content': f"Executing tool: generate_sql_query with arguments {arguments}",
        }
        sql_query, total_tokens = await self.generate_sql_query(query)
        token_message = f"Total Tokens Consumed: {total_tokens}"
        print("agent generated sql query:::", sql_query)
        response_to_user = f"Here is the sql query I am going to use get the results... \n\n{sql_query}\n\n{token_message}"
        yield {
            'is_task_complete': False,
            'require_user_input': False,
            'content': response_to_user,
        }

        # Execute the SQL query and get results
        try:
            query_results = await self.run_sql_query(sql_query)
            formatted_table = self.format_table(query_results)
            print("============Task completed=======")
            yield {
                'is_task_complete': True,
                'require_user_input': False,
                'content': formatted_table,
            }
        except Exception as e:
            full_response = f"Error executing query: {str(e)}"
            print("============Task completed=======")
            yield {
                'is_task_complete': True,
                'require_user_input': False,
                'content': full_response,
            }
