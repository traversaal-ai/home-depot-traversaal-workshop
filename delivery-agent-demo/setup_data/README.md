# BigQuery Data Upload Tool
Upload CSV files to Google BigQuery tables.


## Quick Start
### 1. Update Project ID and upload CSVs in a folder (i.e normalized_tables)
Edit `big_query_data.py` and change:
```python
PROJECT_ID="your-google-cloud-project-id"
DATASET_ID="your-bigquery-dataset-id"
```
### 2. Run
```bash
python big_query_data.py
```
## Files
- `big_query_data.py` - Main script
- `normalized_tables/` - CSV files to upload






