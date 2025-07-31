from google.cloud import bigquery
from google.cloud.exceptions import Conflict

# Configuration IDs
PROJECT_ID = "" # ADD YOUR PROJECT
LOCATION_ID = "us-central1"
DATASET_ID = "home_depot_policy_data"
ACTION_TABLE_ID = "action_table"
ANCHOR_TABLE_ID = "anchor_table"
CUSTOMER_TABLE_ID = "customer_table"
ORDER_TABLE_ID = "order_table"
ITEM_TABLE_ID = "item_table"

# CSV files mapping
CSV_FILES = {
    ANCHOR_TABLE_ID: "data/anchor_table.csv",
    CUSTOMER_TABLE_ID: "data/customer_table.csv",
    ORDER_TABLE_ID: "data/order_table.csv",
    ITEM_TABLE_ID: "data/item_table.csv"
}

def create_all_tables():
    """Create BigQuery dataset and all tables with CSV data."""
    
    client = bigquery.Client(project=PROJECT_ID)
    
    try:
        # Create dataset
        dataset_ref = client.dataset(DATASET_ID)
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = LOCATION_ID
        
        try:
            client.create_dataset(dataset, timeout=30)
            print(f"✅ Created dataset: {PROJECT_ID}.{DATASET_ID}")
        except Conflict:
            print(f"ℹ️  Dataset exists: {PROJECT_ID}.{DATASET_ID}")
        
        # Define schemas - FIXED date format issue
        schemas = {
            ACTION_TABLE_ID: [
                bigquery.SchemaField("customer_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("order_number", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("query", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("action_type", "STRING", mode="NULLABLE"),
            ],
            ANCHOR_TABLE_ID: [
                bigquery.SchemaField("sku_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("sku_name", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("sku_price", "FLOAT", mode="NULLABLE"),
                bigquery.SchemaField("recommended_sku_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("recommended_sku_name", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("recommended_price", "FLOAT", mode="NULLABLE"),
            ],
            CUSTOMER_TABLE_ID: [
                bigquery.SchemaField("customer_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("name", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("phone", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("email", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("address", "STRING", mode="NULLABLE"),
            ],
            ORDER_TABLE_ID: [
                bigquery.SchemaField("customer_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("customer_name", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("order_number", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("order_date", "STRING", mode="NULLABLE"),  # CHANGED FROM DATE TO STRING
                bigquery.SchemaField("quantity", "INTEGER", mode="NULLABLE"),
                bigquery.SchemaField("total_sale", "FLOAT", mode="NULLABLE"),
                bigquery.SchemaField("sku_price", "FLOAT", mode="NULLABLE"),
                bigquery.SchemaField("sku_name", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("sku_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("delivery_type", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("pickup_person", "STRING", mode="NULLABLE"),
            ],
            ITEM_TABLE_ID: [
                bigquery.SchemaField("sku_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("sku_name", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("sku_price", "FLOAT", mode="NULLABLE"),
                bigquery.SchemaField("sku_description", "STRING", mode="NULLABLE"),
            ]
        }
        
        # Create all tables
        for table_id, schema in schemas.items():
            table_ref = dataset_ref.table(table_id)
            table = bigquery.Table(table_ref, schema=schema)
            
            try:
                client.create_table(table, timeout=30)
                print(f"✅ Created table: {PROJECT_ID}.{DATASET_ID}.{table_id}")
            except Conflict:
                print(f"ℹ️  Table exists: {PROJECT_ID}.{DATASET_ID}.{table_id}")
                if table_id in CSV_FILES:
                    client.query(f"DELETE FROM `{PROJECT_ID}.{DATASET_ID}.{table_id}` WHERE TRUE").result()
                    print(f"🗑️  Cleared existing data in {table_id}")
        
        # Load CSV data
        for table_id, csv_path in CSV_FILES.items():
            job_config = bigquery.LoadJobConfig(
                schema=schemas[table_id],
                skip_leading_rows=1,
                source_format=bigquery.SourceFormat.CSV,
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            )
            
            table_ref = dataset_ref.table(table_id)
            
            with open(csv_path, "rb") as source_file:
                load_job = client.load_table_from_file(source_file, table_ref, job_config=job_config)
            
            load_job.result()
            
            table = client.get_table(table_ref)
            print(f"✅ Loaded {table.num_rows} rows into {table_id}")
        
        print("🎉 All tables setup completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_all_tables()