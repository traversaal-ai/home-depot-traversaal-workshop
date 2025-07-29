#create dataset through ui in project

FOLDER_PATH="normalized_tables" #change it if your csvs are in different tables
PROJECT_ID="<YOUR-PROJECT-ID>"
DATASET_ID="<YOUR-DATASET_ID>"


import os
import pandas as pd
from google.cloud import bigquery
def upload_csvs_to_bigquery(folder_path, project_id, dataset_id):
    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".csv"):
            file_path = os.path.join(folder_path, file_name)
            table_name = os.path.splitext(file_name)[0]  # Use filename (without .csv) as table name
            print(f"Uploading {file_name} to {dataset_id}.{table_name}...")
            # Read CSV into DataFrame
            df = pd.read_csv(file_path)
            if table_name == "action_update":
                if 'DATA_ID' in df.columns:
                    df['DATA_ID'] = pd.to_numeric(df['DATA_ID'], errors='coerce').astype('Int64')
                if 'CUSTOMER_ID' in df.columns:
                    df['CUSTOMER_ID'] = pd.to_numeric(df['CUSTOMER_ID'], errors='coerce').astype('Int64')
                if 'UPDATED_AT' in df.columns:
                    df['UPDATED_AT'] = pd.to_datetime(df['UPDATED_AT'], errors='coerce')
                if 'RESCHEDULED' in df.columns:
                    df['RESCHEDULED'] = pd.to_datetime(df['RESCHEDULED'], errors='coerce')
            table_id = f"{project_id}.{dataset_id}.{table_name}"
            job = client.load_table_from_dataframe(df, table_id)
            job.result()
            print(f"Uploaded {file_name} to {table_id}")

            
            
            
upload_csvs_to_bigquery(
    folder_path=FOLDER_PATH,
    project_id=PROJECT_ID,
    dataset_id=DATASET_ID
)















