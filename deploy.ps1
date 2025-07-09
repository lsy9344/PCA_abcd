# Python 3.11 + Playwright + Lambda 컨테이너 배포 스크립트 (수정 버전)

$REGION = "ap-northeast-2"
$ACCOUNT_ID = "654654307503"
$FUNCTION_NAME = "parkingauto_250707"
$IMAGE_NAME = "parking_auto_ecrrepo_2"
$ECR_URL = "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${IMAGE_NAME}"

Write-Host "🚀 Deploying with Python 3.11 (Optimized Multi-Stage Build)" -ForegroundColor Cyan

# 🚨 중요: 멀티아키텍처 매니페스트 방지를 위해 BuildKit 비활성화 (가이드 준수)
$env:DOCKER_BUILDKIT = "0"

Write-Host "`n🧹 Cleaning Docker environment..." -ForegroundColor Yellow
docker system prune -af

# 1단계에서 생성한 Dockerfile을 사용하여 단일 아키텍처로 강제 빌드
Write-Host "`n🔨 Building image from permanent Dockerfile..." -ForegroundColor Yellow
docker build --platform linux/amd64 --no-cache -t $IMAGE_NAME .

# 아키텍처 확인
$arch = docker inspect $IMAGE_NAME --format '{{.Architecture}}'
Write-Host "Image architecture: $arch" -ForegroundColor White
if ($arch -ne "amd64") {
    Write-Host "❌ Wrong architecture detected: $arch" -ForegroundColor Red
    exit 1
}

# ECR 푸시
Write-Host "`n📤 Pushing to ECR..." -ForegroundColor Yellow
docker tag "${IMAGE_NAME}:latest" "${ECR_URL}:latest"
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
docker push "${ECR_URL}:latest"

# Lambda 업데이트
Write-Host "`n🔄 Updating Lambda function..." -ForegroundColor Yellow
aws lambda update-function-code `
    --function-name $FUNCTION_NAME `
    --image-uri "${ECR_URL}:latest" `
    --region $REGION `
    --architectures "x86_64"

# 배포 상태 확인!!
Write-Host "`n⏳ Waiting for deployment..." -ForegroundColor Yellow
# ... (기존 스크립트의 나머지 부분은 그대로 사용)