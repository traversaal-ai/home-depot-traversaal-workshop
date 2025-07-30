
# 🛒 MCP Assignment: BigQuery + CSV Upload + Secure Querying with Agents

Welcome to your first hands-on assignment using **MCP Server**, **BigQuery**, and **Gemini Agents**. In this assignment, you'll upload a grocery sales CSV file to BigQuery and use a multi-agent pipeline to query and analyze the data securely.

---

## 📦 Assignment Overview

You will:

1. Upload a new `.csv` file of grocery sales to BigQuery.
2. Replace the existing `walmart_sales.sales` table with your uploaded table.
3. Run secure and explainable SQL queries using a judge → sql → masker agent pipeline via `test_client.py`.

---

## ✅ Steps to Complete

### 1. 🔁 Replace the Dataset/Table in BigQuery

- Open your GCP Console or use the CLI.
- Upload your `.csv` file (e.g., `grocery_sales.csv`) to the BigQuery table.
- Replace the current table `traversaal-research.walmart_sales.sales`.

> 💡 **Hint:** Use the "Create Table" UI in BigQuery and match schema types:  
> `Store: INTEGER`, `Dept: INTEGER`, `Date: DATE`, `Weekly_Sales: FLOAT`, `IsHoliday: BOOLEAN`

---

### 2. ⚙️ Edit the Code (if needed)

- The file `test_client.py` is already set to point to the correct table:
  ```python
  PROJECT_ID = "traversaal-research"
  DATASET_ID = "walmart_sales"
  TABLE_ID = "sales"
  ```

- If you renamed your dataset or table, update the values above.

---

### 3. 🧠 Run the Client Script

```bash
python test_client.py
```

- You’ll be prompted to enter a natural language query.
- The pipeline will follow **three steps**:
  1. **Judge Agent** checks for prompt safety.
  2. **SQL Agent** runs the SQL using MCP Toolset.
  3. **Masking Agent** protects any PII before showing results.

---

### 4. 🧪 Try These Sample Queries

Try entering any of the following:

- `What is the average weekly sales for Dept 1 in Store 1?`
- `Which store had the highest sales during holidays?`
- `Show sales trends over time for Department 5.`

---

## 🧠 Hints & Tips

- 🛡 **Judge Agent** will block unsafe prompts. If your query gets blocked, simplify or rephrase it.
- 🧑‍💻 The SQL Agent is smart — but **be specific** and refer to the column names: `Store`, `Dept`, `Date`, `Weekly_Sales`, `IsHoliday`.
- 🔐 **Masking Agent** will anonymize potentially sensitive info — good for learning privacy best practices.

---

## 🧼 Cleanup (Optional)

If you’d like to delete your uploaded table after the assignment:

```sql
DROP TABLE `traversaal-research.walmart_sales.sales`
```

> ⚠️ Be careful! This will permanently delete the table.

---

## 🚀 Deliverables

Before the end of this session, please complete:

- ✅ Table upload verified in BigQuery
- ✅ Successful query through the agent pipeline
- ✅ Screenshot of terminal output showing masked results

---

Happy querying!  
— Team Traversaal.ai 🧠🚀
s