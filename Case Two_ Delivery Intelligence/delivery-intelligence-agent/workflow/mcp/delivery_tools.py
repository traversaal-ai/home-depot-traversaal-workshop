from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters, StdioConnectionParams

delivery_tools = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='python',
            args=["workflow/mcp/tools_server.py"]  # Adjust relative path if needed
        ),
        timeout=15,
    )
)

