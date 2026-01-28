# GitHub Copilot Instructions


## Documentation Standards

### Documentation Structure

**Two types of markdown files:**

1. **`README.md`** (Root level only)
   - Contains all deployment commands for the project
   - Quick reference for running deployment scripts
   - Located at: `/README.md`
   - **This is the ONLY markdown file outside `reference-materials/`**

2. **Reference Materials** (`reference-materials/` directory)
   - All other markdown documentation files MUST be created here
   - Contains detailed technical documentation

#### Core Documentation Files

- **`development.md`** - Master architecture and implementation plan. Contains:
  - System architecture overview
  - Data flow diagrams
  - Technology stack decisions
  - Session management strategy
  - stories with check boxes to be completed

#### Component-Specific Documentation Files

When creating new components, create corresponding documentation in `reference-materials/`:
Examples if that be the case:

- **`DYNAMODB_SCHEMA.md`** - DynamoDB table structure, indexes, TTL configuration
- **`API_GATEWAY.md`** - API Gateway endpoints, request/response formats, CORS configuration
- **`MCP_INTEGRATION.md`** - MCP Server integration details, tool calling patterns
- **`DEPLOYMENT.md`** - CloudFormation deployment instructions, environment variables, testing procedures

#### Documentation Update Rules

1. **For new deployment scripts**: Add the command to `README.md` in the "Deployment Commands" section
2. **For new components**: Document it in a dedicated markdown file in `reference-materials/` or update existing ones
   - Note: Not every new feature needs a new file. Some cases might just need an existing md file to be updated or no updates
3. **Update `development.md`** to reference new documentation files if that be the case
4. **Keep `development.md`** as the high-level guide with links to detailed docs

**Example reference in `development.md`:**
```markdown
## DynamoDB Session Storage
See [DYNAMODB_SCHEMA.md](./DYNAMODB_SCHEMA.md) for detailed table structure and schema design.
```

**Example deployment command in `README.md`:**
```markdown
### 1. DynamoDB Session Storage
```bash
cd infra/cloudformation
./deploy-dynamodb.sh dev
```
```

---

## Coding Standards

### Python Lambda Functions (Python 3.12)

#### Logging Standards
```python
import logging

# Always use Python's logging module (NOT print statements)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Log levels:
logger.info("Normal operational messages")
logger.warning("Warning but recoverable issues")
logger.error("Errors that need attention")
logger.debug("Detailed debugging information")
```

#### General Guidelines
- **Language Version**: Python 3.12
- **Logging**: Use `logging` module with structured logs (not `print()`)
- **Configuration Management**: 
  - **Lambda functions**: Retrieve secrets and configuration from AWS Parameter Store (API keys, endpoints, etc.)
  - **Never hardcode sensitive values** in source code
  - **Try to avoid hardcoding any configuration values** in source code which is used accross other areas
- **Error Handling**: Always use try-except blocks with proper error logging
- **Function Design**: Keep Lambda functions short and focused on a single responsibility
- **Code Style**: Follow PEP 8, use type hints where appropriate


---

