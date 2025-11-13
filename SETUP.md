# Setup Guide

## Prerequisites

1. **Python 3.11 or higher**
   ```bash
   python --version
   ```

2. **Google API Key**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Save it for later use

3. **MCP Server**
   - You need a running MCP server accessible via HTTP
   - Use ngrok to expose your local MCP server:
     ```bash
     ngrok http 3000  # Adjust port as needed
     ```
   - Save the ngrok URL (e.g., `https://abc123.ngrok.io`)

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd adk-mcp-code-execution-anthropic/mcp_adk_prototype
```

### 2. Create Virtual Environment

**Using UV (Recommended):**
```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"
```

**Using pip:**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 3. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and update:
```bash
# Replace with your actual ngrok URL
MCP_SERVER_URL=https://your-actual-url.ngrok.io

# Replace with your Google API key
GOOGLE_API_KEY=your_actual_api_key_here
```

### 4. Verify Installation

Run the token comparison example:
```bash
python examples/token_comparison.py
```

You should see output showing ~93% token reduction.

## Running the Demo

**Important:** Make sure your MCP server is running and accessible before running the demo!

```bash
python src/demo.py
```

The demo will:
1. Connect to your MCP server
2. Generate Python wrapper modules
3. Initialize the Google ADK agent
4. Run several demonstration tasks
5. Show token comparison analysis

## Troubleshooting

### Error: "MCP_SERVER_URL environment variable not set"
- Ensure you've created the `.env` file
- Verify the MCP_SERVER_URL is set correctly
- Make sure there are no extra spaces

### Error: Connection refused or timeout
- Check that your MCP server is running
- Verify ngrok is active and the URL is correct
- Test the URL in a browser or with curl:
  ```bash
  curl https://your-url.ngrok.io/mcp/v1/tools/list -X POST -H "Content-Type: application/json" -d '{}'
  ```

### Error: Google API authentication failed
- Verify your GOOGLE_API_KEY is correct
- Check that the API key has access to Gemini models
- Ensure there are no extra quotes or spaces in the .env file

### Import errors
- Make sure you're in the virtual environment
- Reinstall dependencies:
  ```bash
  pip install -e ".[dev]"
  ```

## Next Steps

1. **Explore the code:**
   - `src/mcp_client.py` - MCP protocol client
   - `src/tool_generator.py` - Generates Python wrappers
   - `src/adk_agent.py` - Google ADK agent setup
   - `src/demo.py` - Demonstration script

2. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

3. **Customize for your MCP server:**
   - Modify `tool_generator.py` to handle your specific tool schemas
   - Update agent instructions in `adk_agent.py`
   - Create custom demo scenarios

4. **Deploy to production:**
   - See README.md for GKE deployment instructions
   - Implement proper error handling and monitoring
   - Add authentication and rate limiting

## Support

For issues or questions:
- Check the README.md for detailed documentation
- Review the code comments for implementation details
- Refer to the official Google ADK documentation
