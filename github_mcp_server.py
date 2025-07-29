#!/usr/bin/env python3
"""
GitHub MCP Server
Provides GitHub integration through Model Context Protocol
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
)
from github import Github
from github.Repository import Repository
from github.GithubException import GithubException


class GitHubMCPServer:
    def __init__(self):
        self.server = Server("github-mcp")
        self.github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        
        if not self.github_token:
            raise ValueError("GITHUB_PERSONAL_ACCESS_TOKEN environment variable is required")
        
        self.github = Github(self.github_token)
        
        # Register tools
        self._register_tools()
        
    def _register_tools(self):
        """Register available GitHub tools"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="github_create_issue",
                    description="Create a new GitHub issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string", "description": "Repository name (owner/repo)"},
                            "title": {"type": "string", "description": "Issue title"},
                            "body": {"type": "string", "description": "Issue body"},
                            "labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Labels to add to the issue"
                            }
                        },
                        "required": ["repo", "title", "body"]
                    }
                ),
                Tool(
                    name="github_list_issues",
                    description="List GitHub issues for a repository",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string", "description": "Repository name (owner/repo)"},
                            "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                            "limit": {"type": "integer", "description": "Maximum number of issues to return", "default": 10}
                        },
                        "required": ["repo"]
                    }
                ),
                Tool(
                    name="github_create_pr",
                    description="Create a new GitHub pull request",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string", "description": "Repository name (owner/repo)"},
                            "title": {"type": "string", "description": "PR title"},
                            "body": {"type": "string", "description": "PR body"},
                            "head": {"type": "string", "description": "Branch to merge from"},
                            "base": {"type": "string", "description": "Branch to merge into", "default": "main"}
                        },
                        "required": ["repo", "title", "body", "head"]
                    }
                ),
                Tool(
                    name="github_list_prs",
                    description="List GitHub pull requests for a repository",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string", "description": "Repository name (owner/repo)"},
                            "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                            "limit": {"type": "integer", "description": "Maximum number of PRs to return", "default": 10}
                        },
                        "required": ["repo"]
                    }
                ),
                Tool(
                    name="github_get_repo_info",
                    description="Get repository information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string", "description": "Repository name (owner/repo)"}
                        },
                        "required": ["repo"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "github_create_issue":
                    return await self._create_issue(arguments)
                elif name == "github_list_issues":
                    return await self._list_issues(arguments)
                elif name == "github_create_pr":
                    return await self._create_pr(arguments)
                elif name == "github_list_prs":
                    return await self._list_prs(arguments)
                elif name == "github_get_repo_info":
                    return await self._get_repo_info(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
            except Exception as e:
                return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
    
    async def _create_issue(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create a GitHub issue"""
        repo_name = args["repo"]
        title = args["title"]
        body = args["body"]
        labels = args.get("labels", [])
        
        try:
            repo = self.github.get_repo(repo_name)
            issue = repo.create_issue(title=title, body=body, labels=labels)
            
            result = {
                "success": True,
                "issue_number": issue.number,
                "issue_url": issue.html_url,
                "title": issue.title
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except GithubException as e:
            return [TextContent(type="text", text=f"GitHub API error: {e.data}")]
    
    async def _list_issues(self, args: Dict[str, Any]) -> List[TextContent]:
        """List GitHub issues"""
        repo_name = args["repo"]
        state = args.get("state", "open")
        limit = args.get("limit", 10)
        
        try:
            repo = self.github.get_repo(repo_name)
            issues = repo.get_issues(state=state)
            
            issue_list = []
            for i, issue in enumerate(issues):
                if i >= limit:
                    break
                    
                issue_list.append({
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "url": issue.html_url,
                    "created_at": issue.created_at.isoformat(),
                    "user": issue.user.login if issue.user else None
                })
            
            result = {
                "repository": repo_name,
                "total_found": len(issue_list),
                "issues": issue_list
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except GithubException as e:
            return [TextContent(type="text", text=f"GitHub API error: {e.data}")]
    
    async def _create_pr(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create a GitHub pull request"""
        repo_name = args["repo"]
        title = args["title"]
        body = args["body"]
        head = args["head"]
        base = args.get("base", "main")
        
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.create_pull(title=title, body=body, head=head, base=base)
            
            result = {
                "success": True,
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "title": pr.title,
                "head": pr.head.ref,
                "base": pr.base.ref
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except GithubException as e:
            return [TextContent(type="text", text=f"GitHub API error: {e.data}")]
    
    async def _list_prs(self, args: Dict[str, Any]) -> List[TextContent]:
        """List GitHub pull requests"""
        repo_name = args["repo"]
        state = args.get("state", "open")
        limit = args.get("limit", 10)
        
        try:
            repo = self.github.get_repo(repo_name)
            prs = repo.get_pulls(state=state)
            
            pr_list = []
            for i, pr in enumerate(prs):
                if i >= limit:
                    break
                    
                pr_list.append({
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "url": pr.html_url,
                    "head": pr.head.ref,
                    "base": pr.base.ref,
                    "created_at": pr.created_at.isoformat(),
                    "user": pr.user.login if pr.user else None
                })
            
            result = {
                "repository": repo_name,
                "total_found": len(pr_list),
                "pull_requests": pr_list
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except GithubException as e:
            return [TextContent(type="text", text=f"GitHub API error: {e.data}")]
    
    async def _get_repo_info(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get repository information"""
        repo_name = args["repo"]
        
        try:
            repo = self.github.get_repo(repo_name)
            
            result = {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "url": repo.html_url,
                "clone_url": repo.clone_url,
                "default_branch": repo.default_branch,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "language": repo.language,
                "private": repo.private,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except GithubException as e:
            return [TextContent(type="text", text=f"GitHub API error: {e.data}")]


async def main():
    # Set GitHub token from environment
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not github_token:
        print("Error: GITHUB_PERSONAL_ACCESS_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    # Create and run the server
    server_instance = GitHubMCPServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream, write_stream, 
            init_options=server_instance.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())