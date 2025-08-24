import os
from dotenv import load_dotenv
from supabase import create_client, Client
import duckdb
import pandas as pd

load_dotenv()

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY environment variables must be set")

supabase: Client = create_client(url, key)

response = supabase.table('tips').select("*", count="exact").execute()
all_data = response.data
total_rows = response.count

if total_rows is not None and total_rows > len(all_data):
    page = 1
    page_size = 1000  # Default page size in Supabase
    while len(all_data) < total_rows:
        start_index = page * page_size
        end_index = start_index + page_size - 1
        response = supabase.table('tips').select("*").range(start_index, end_index).execute()
        all_data.extend(response.data)
        page += 1

# response.data is a list of dictionaries
# [{'id': 1, 'total_bill': 16.99, 'tip': 1.01, 'sex': 'Female', 'smoker': 'No', 'day': 'Sun', 'time': 'Dinner', 'size': 2}, ...]
tips = pd.DataFrame(all_data)
tips["percent"] = tips.tip / tips.total_bill

duckdb.query("SET allow_community_extensions = false;")
duckdb.register("tips", tips)
