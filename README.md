### Instructions to run the ai agent:

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
GOOGLE_API_KEY="<your api key>"
```

### 6. Run the agent to generate parser code and validate
```bash
python agent.py --target icici
```

### 7. Run pytest
```bash
pytest
```

