# ai-agent-challenge
Coding agent challenge which write custom parsers for Bank statement PDF.
### Demo video:



https://github.com/user-attachments/assets/7208a773-efff-4ece-8e99-9b2e946ef138



### Instructions:

### 1. Clone the repo and open in a code editor

```bash
git clone https://github.com/saitarun47/ai-agent-challenge
cd ai-agent-challenge
```

### 2. Create a virtual environment

```bash
uv venv
```

### 3. Activate the virtual environment

Windows:
```bash
.venv\Scripts\activate
```

Mac/Linux:
```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
uv add -r requirements.txt
```

### 5. Create a file named '.env' and paste your api key there

```bash
GOOGLE_API_KEY="your api key"
```

### 6. Run the agent to generate parser code and validate
```bash
python agent.py --target icici
```
**NOTE:** If the agent produces partial output or fails, simply re-run step 6 again. The agent has built-in retry logic, but a fresh start often resolves temporary issues.

### 7. Run pytest
```bash
pytest
```


### One-paragraph agent diagram:
The agent implements an autonomous plan → analyze → generate → test → self-fix loop using Google Gemini for intelligent parser code generation. It begins by analyzing the input PDF to discover table structures, column patterns, data formats, and extraction challenges, then generates Python parsing code using multiple fallback strategies (pdfplumber table extraction, text pattern matching, and PyPDF2 raw extraction). The generated parser is immediately tested against the sample PDF, with output validated using pandas DataFrame.equals() against expected CSV data. When validation fails, the agent captures detailed error feedback and automatically regenerates improved code for up to 5 attempts (which can be changed in the code), incorporating lessons from previous failures to iteratively refine the parsing logic until it produces accurate PDF parsers that match the exact specification.


