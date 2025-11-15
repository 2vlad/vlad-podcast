# MCP Configuration Guide

This project uses Model Context Protocol (MCP) servers to integrate with various services. This guide explains how to set up MCP for this project.

## Prerequisites

- Node.js and npm installed
- Railway CLI installed and authenticated (`railway login`)
- Vercel CLI installed and authenticated (`vercel login`)

## Setup Instructions

### 1. Copy the MCP Configuration Template

```bash
cp .mcp.json.example .mcp.json
```

### 2. Configure MCP Servers

The `.mcp.json` file contains configuration for several MCP servers:

#### Railway MCP Server
Provides tools for Railway deployment management.

**Authentication:** Uses Railway CLI authentication (run `railway login` first)

**Configuration:**
```json
"railway": {
  "command": "npm",
  "args": ["exec", "@railway/mcp-server"]
}
```

No additional API keys needed - uses Railway CLI credentials.

#### Vercel MCP Server
Provides tools for Vercel deployment management.

**Authentication:** Uses Vercel CLI authentication (run `vercel login` first)

**Configuration:**
```json
"vercel": {
  "command": "npx",
  "args": ["-y", "@vercel/mcp-server"]
}
```

No additional API keys needed - uses Vercel CLI credentials.

#### Task Master AI
Provides AI-powered task management and project planning.

**Configuration:**
Replace placeholder API keys in the `env` section:
```json
"task-master-ai": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "task-master-ai"],
  "env": {
    "ANTHROPIC_API_KEY": "sk-ant-...",
    "PERPLEXITY_API_KEY": "pplx-...",
    // ... other keys as needed
  }
}
```

**Required:** At least one AI provider API key (Anthropic recommended)

#### Supabase MCP Server
Provides tools for Supabase database and backend management.

**Configuration:**
Replace placeholder values in the `env` section:
```json
"supabase": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "supabase-mcp@latest", "supabase-mcp-claude"],
  "env": {
    "SUPABASE_URL": "https://your-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJ...",
    "SUPABASE_SERVICE_ROLE_KEY": "eyJ...",
    "MCP_API_KEY": "your-mcp-api-key"
  }
}
```

**Required:** Supabase project credentials from your Supabase dashboard

### 3. Verify CLI Authentication

Before using Railway and Vercel MCP servers, ensure you're authenticated:

```bash
# Check Railway authentication
railway whoami

# Check Vercel authentication
vercel whoami
```

If not authenticated, run:
```bash
railway login
vercel login
```

### 4. Test MCP Servers

You can test if MCP servers are working by checking available tools in Claude Code:
- Railway tools: `railway___*`
- Vercel tools: `vercel___*`
- Task Master tools: `task-master-ai___*`
- Supabase tools: `supabase___*`

## Troubleshooting

### MCP Server Not Loading

1. **Check Node.js version:** Ensure Node.js 18+ is installed
2. **Check authentication:** Run `railway whoami` and `vercel whoami`
3. **Check API keys:** Verify all required API keys are set in `.mcp.json`
4. **Restart Claude Code:** Exit and restart Claude Code to reload MCP configuration

### Railway/Vercel Commands Not Working

1. **Verify CLI installation:**
   ```bash
   railway --version
   vercel --version
   ```
2. **Re-authenticate:**
   ```bash
   railway login
   vercel login
   ```

### Task Master AI Not Working

Ensure at least one AI provider API key is configured. Anthropic (Claude) is recommended:
- Get API key from https://console.anthropic.com/

### Supabase MCP Not Working

1. Check your Supabase project credentials
2. Ensure the service role key has proper permissions
3. Verify the Supabase URL is correct

## Security Notes

- **Never commit `.mcp.json` to version control** - it's already in `.gitignore`
- API keys in `.mcp.json` are sensitive - keep them secure
- Railway and Vercel MCP use CLI authentication, which is more secure than storing tokens
- Use `.mcp.json.example` as a template for sharing configuration structure

## Available MCP Tools

### Railway MCP
- Check Railway authentication status
- Create new projects
- Deploy services
- Manage environments
- View deployment logs
- List projects and services

### Vercel MCP
- Deploy projects
- Manage deployments
- Configure domains
- View build logs
- List projects
- Manage environment variables

### Task Master AI
- Parse PRD documents into tasks
- Generate task breakdowns
- Analyze project complexity
- Manage task dependencies
- Update task status
- Track implementation progress

### Supabase MCP
- Execute SQL queries
- Manage database tables
- Deploy edge functions
- View project analytics
- Manage authentication
- Configure storage

## More Information

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Railway MCP Server](https://github.com/railwayapp/mcp)
- [Vercel MCP Server](https://github.com/vercel/mcp-server)
- [Task Master AI](https://github.com/taskmaster-ai/mcp-server)
- [Supabase MCP](https://supabase.com/docs/guides/ai/mcp)
