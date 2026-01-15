# Agent Protocols (v0.3.0)

## 📡 The Radio Protocol
All communication occurs via the `mission_log.md` file using the following format:
```
### [TIMESTAMP] [Sender -> Recipient] [TYPE] Content
```
* **REQ:** Request (Command)
* **ACK:** Acknowledgment (Success/Failure response)
* **LOG:** General logging

## 🤖 LocalSmith Skills
The **LocalSmith** agent (`tools/lib/toolsmith_local.py`) understands the following natural language commands:

### 1. Backup Files
Creates a copy of a file in `.ddd/` with a `.bak` extension.
> **Command:** `backup <filename>`
>
> **Example:** `backup config.json`

### 2. Update Configuration
Edits JSON keys in `.ddd/config.json`. Handles quote stripping automatically.
> **Command:** `set <key> to <value>`
>
> **Example:** `set verification_command to: echo 'All Systems Go'`

### 3. Create Filters (Python/Text)
Writes code or text to `.ddd/filters/`. Supports Markdown code blocks.
> **Command:** `create filter <name> with content: <content>`
>
> **Example:**
> `create filter ignore.py with content: `
> ``` python
> def filter(lines): return []
> ```

### 4. Run Verification
Executes the shell command currently stored in `.ddd/config.json` ("verification_command") inside the container.
> **Command:** `run verification`
