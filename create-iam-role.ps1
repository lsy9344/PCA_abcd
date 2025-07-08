# 빠른 IAM 역할 설정
$ACCOUNT_ID = "654654307503"
$ROLE_NAME = "lambda-execution-role"

Write-Host "🔐 Setting up IAM role for Lambda..." -ForegroundColor Green

# 1. 역할이 이미 존재하는지 확인
$roleExists = $false
try {
    $result = aws iam get-role --role-name $ROLE_NAME 2>$null
    if ($LASTEXITCODE -eq 0) {
        $roleExists = $true
        Write-Host "✅ IAM role already exists" -ForegroundColor Green
    }
} catch {
    Write-Host "📝 IAM role doesn't exist, creating..." -ForegroundColor Yellow
}

if (-not $roleExists) {
    # Trust Policy 생성
    $trustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@
    
    # 임시 파일에 저장
    $trustPolicy | Out-File -FilePath "trust-policy.json" -Encoding UTF8
    
    # IAM 역할 생성
    aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://trust-policy.json
    
    # 기본 Lambda 실행 권한 부여
    aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    
    # ECR 접근 권한 부여
    $ecrPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
"@
    
    $ecrPolicy | Out-File -FilePath "ecr-policy.json" -Encoding UTF8
    aws iam put-role-policy --role-name $ROLE_NAME --policy-name "ECRAccessPolicy" --policy-document file://ecr-policy.json
    
    # 정리
    Remove-Item "trust-policy.json" -Force -ErrorAction SilentlyContinue
    Remove-Item "ecr-policy.json" -Force -ErrorAction SilentlyContinue
    
    Write-Host "✅ IAM role created successfully!" -ForegroundColor Green
    Write-Host "⏰ Waiting for IAM propagation..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
}

Write-Host "🔗 Role ARN: arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}" -ForegroundColor Cyan