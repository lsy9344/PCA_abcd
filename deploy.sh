#!/bin/bash
set -e

REGION="ap-northeast-2"
ACCOUNT_ID="654654307503"
FUNCTION_NAME="parkingauto_250707"
IMAGE_NAME="parking_auto_ecrrepo_2"
ECR_URL="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME"

export DOCKER_BUILDKIT=0
docker system prune -af
docker build --platform linux/amd64 --no-cache -t $IMAGE_NAME .

docker tag $IMAGE_NAME:latest $ECR_URL:latest
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
docker push $ECR_URL:latest

manifest=$(aws ecr batch-get-image --repository-name $IMAGE_NAME --image-ids imageTag=latest --query 'images[].imageManifest' --output text --region $REGION)
if [[ $manifest == *"manifest.list.v2"* ]]; then
    echo "❌ Multi-arch manifest detected! Lambda 배포 불가"
    exit 1
fi

aws lambda update-function-code --function-name $FUNCTION_NAME --image-uri $ECR_URL:latest --region $REGION --architectures "x86_64"
echo "✅ Lambda 컨테이너 배포 완료"