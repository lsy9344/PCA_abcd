# GitHub MCP Server Setup Guide

## ✅ 설치 완료

GitHub MCP 서버가 성공적으로 설치되어 로컬에서 사용할 수 있습니다.

## 📁 파일 위치

- **MCP 서버**: `/Users/sooyeol/Desktop/Code/PCA_abcd/github_mcp_server.py`
- **가상환경**: `/Users/sooyeol/Desktop/Code/PCA_abcd/mcp-servers/github_mcp_env/`
- **테스트 스크립트**: `/Users/sooyeol/Desktop/Code/PCA_abcd/test_github_mcp.py`

## 🔐 인증 정보

- **GitHub Token**: `[REDACTED - 환경변수로 설정 필요]`
- **GitHub User**: `lsy9344`
- **Public Repositories**: 5개

## 🛠 사용 가능한 도구

### 1. `github_create_issue`
GitHub 이슈를 생성합니다.

```json
{
  "repo": "owner/repository-name",
  "title": "Issue title",
  "body": "Issue description",
  "labels": ["bug", "urgent"]  // optional
}
```

### 2. `github_list_issues`
저장소의 이슈 목록을 조회합니다.

```json
{
  "repo": "owner/repository-name",
  "state": "open",  // "open", "closed", "all"
  "limit": 10       // optional, default: 10
}
```

### 3. `github_create_pr`
풀 리퀘스트를 생성합니다.

```json
{
  "repo": "owner/repository-name",
  "title": "PR title",
  "body": "PR description",
  "head": "feature-branch",
  "base": "main"  // optional, default: "main"
}
```

### 4. `github_list_prs`
저장소의 풀 리퀘스트 목록을 조회합니다.

```json
{
  "repo": "owner/repository-name",
  "state": "open",  // "open", "closed", "all"
  "limit": 10       // optional, default: 10
}
```

### 5. `github_get_repo_info`
저장소 정보를 조회합니다.

```json
{
  "repo": "owner/repository-name"
}
```

## 🚀 서버 실행 방법

```bash
# 환경변수 설정
export GITHUB_PERSONAL_ACCESS_TOKEN="your_github_token_here"

# 가상환경 활성화
source mcp-servers/github_mcp_env/bin/activate

# MCP 서버 실행
python github_mcp_server.py
```

## 🧪 테스트 실행

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="your_github_token_here"
source mcp-servers/github_mcp_env/bin/activate
python test_github_mcp.py
```

## 📋 설치된 패키지

- `mcp` - Model Context Protocol 라이브러리
- `PyGithub` - GitHub API 클라이언트
- `pydantic` - 데이터 검증
- `requests` - HTTP 클라이언트
- 기타 의존성 패키지들

## 🔧 문제 해결

1. **Token 인증 실패**
   - 환경변수 `GITHUB_PERSONAL_ACCESS_TOKEN`이 설정되어 있는지 확인
   - 토큰에 필요한 권한(repo, issues, pull_requests)이 있는지 확인

2. **가상환경 활성화 실패**
   - 가상환경 경로가 올바른지 확인: `mcp-servers/github_mcp_env/bin/activate`

3. **의존성 설치 문제**
   - 가상환경에서 다시 설치: `pip install mcp pydantic requests PyGithub`

## ✨ 사용 예시

### 이슈 생성
```python
# MCP 클라이언트에서 호출
await call_tool("github_create_issue", {
    "repo": "lsy9344/PCA",
    "title": "새로운 기능 요청",
    "body": "C 매장 자동화 기능을 추가해주세요",
    "labels": ["enhancement", "automation"]
})
```

### 저장소 정보 조회
```python
await call_tool("github_get_repo_info", {
    "repo": "lsy9344/PCA"
})
```

GitHub MCP 서버가 성공적으로 설치되었습니다! 🎉