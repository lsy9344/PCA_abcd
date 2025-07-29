#!/usr/bin/env python3
"""
Test script for GitHub MCP Server
"""
import os
import asyncio
from github import Github

async def test_github_connection():
    """Test basic GitHub API connection"""
    print("🔗 Testing GitHub API connection...")
    
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        print("❌ GITHUB_PERSONAL_ACCESS_TOKEN not found")
        return False
    
    try:
        g = Github(token)
        user = g.get_user()
        print(f"✅ GitHub connection successful!")
        print(f"   User: {user.login}")
        print(f"   Name: {user.name or 'Not set'}")
        print(f"   Public repos: {user.public_repos}")
        
        # Test repository access
        repos = list(user.get_repos())[:3]
        print(f"   Sample repositories:")
        for repo in repos:
            print(f"     - {repo.full_name} ({'private' if repo.private else 'public'})")
        
        return True
        
    except Exception as e:
        print(f"❌ GitHub connection failed: {e}")
        return False

async def main():
    print("🚀 GitHub MCP Server Test")
    print("=" * 40)
    
    # Set token (환경변수에서 읽어오거나 직접 설정 필요)
    # os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "your_github_token_here"
    
    if not os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"):
        print("❌ GITHUB_PERSONAL_ACCESS_TOKEN 환경변수가 설정되지 않았습니다.")
        print("   export GITHUB_PERSONAL_ACCESS_TOKEN='your_token_here' 를 실행하세요.")
        return
    
    # Test connection
    success = await test_github_connection()
    
    if success:
        print("\n✅ GitHub MCP Server setup completed successfully!")
        print("\n📋 Available tools:")
        print("   • github_create_issue - Create GitHub issues")
        print("   • github_list_issues - List repository issues")  
        print("   • github_create_pr - Create pull requests")
        print("   • github_list_prs - List pull requests")
        print("   • github_get_repo_info - Get repository information")
        
        print(f"\n🎯 MCP Server ready!")
        print(f"   Server file: /Users/sooyeol/Desktop/Code/PCA_abcd/github_mcp_server.py")
        print(f"   Environment: mcp-servers/github_mcp_env")
        
    else:
        print("\n❌ GitHub MCP Server setup failed!")

if __name__ == "__main__":
    asyncio.run(main())