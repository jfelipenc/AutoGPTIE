# 🤖 Insight Engine

**Insight Engine** is an autonomous agent that can provide your business with data based on your needs right **now**!

- 🔎 **Querying and extracting** - Our agent can query your local data, from Excel files to databases.
- ⚒️ **Manipulate and change** - Insight Engine can calculate new metrics, adapting your graphs to your needs.
- 👀 **Visualizing** - The agent provides real-time data in easy-to-edit graphs.


---

![Alt text](<Captura de tela 2023-10-25 211146-1.png>)

---

## Executing

Our agent is following the Agent Protocol and is backed by Auto GPT. To start it, simply run the command below:

```bash
./run agent start InsightEngineAgent
```

## Capabilities

The agent can currently extract data from an Excel file or Postgres database. We're working to add new data sources to it and also improving some other abilities.

The agent currently is able to create temporary databases that store the extracted data and use its metadata as a way to share output between steps.

## Next steps

We're working on a Angular frontend that links the agent's final output with the graphing framework (CanvasJS). This feature is expected to be launched on a separate repository. 

To-do list:
- Delete temporary tables after task execution or on failure
- Add ability to retrieve data from any SQL database
- Add ability to retrieve data from CSVs and other common file types (Parquet, etc...)
- Add frontend integration
- Allow the user to save files through Data Connections page

Stay tuned!