#!/bin/bash

REGION="${AWS_DEFAULT_REGION:-eu-west-1}"
ACCOUNT_ID="000000000000"

TOPIC_NAME="${SNS_TOPIC_NAME:-sns_topic}"
TOPIC_ARN="arn:aws:sns:${AWS_DEFAULT_REGION}:${ACCOUNT_ID}:${TOPIC_NAME}"

# Define filter policies
PRIMARY_FILTER='{"FilterPolicy": "{\"queue_priority\": [\"Primary\"]}"}'
SECONDARY_FILTER='{"FilterPolicy":"{\"queue_priority\": [\"Secondary\"]}"}'

# Create topic
awslocal sns create-topic --name "$TOPIC_NAME" --attributes FifoTopic=true

# Queue and filter pairs
declare -A QUEUE_FILTERS=(
  ["${SQS_PRIMARY_QUEUE_NAME:-primary-queue}"]="$PRIMARY_FILTER"
  ["${SQS_SECONDARY_QUEUE_NAME:-secondary-queue}"]="$SECONDARY_FILTER"
)

for QUEUE_NAME in "${!QUEUE_FILTERS[@]}"; do
  FILTER_POLICY=${QUEUE_FILTERS[$QUEUE_NAME]}
  QUEUE_URL="http://localhost:4566/${ACCOUNT_ID}/${QUEUE_NAME}"

  # Create queue
  awslocal sqs create-queue --queue-name "$QUEUE_NAME"

  # Get queue ARN
  QUEUE_ARN=$(awslocal sqs get-queue-attributes \
    --queue-url "$QUEUE_URL" \
    --attribute-name QueueArn \
    --query "Attributes.QueueArn" \
    --output text)

  # Allow SNS to publish to this SQS queue
  awslocal sqs set-queue-attributes \
    --queue-url "$QUEUE_URL" \
    --attributes '{"Policy": "{\"Version\": \"2012-10-17\",\"Statement\": [{\"Effect\": \"Allow\",\"Principal\": \"*\",\"Action\": \"sqs:SendMessage\",\"Resource\": \"$QUEUE_ARN\",\"Condition\": {\"ArnEquals\": {\"aws:SourceArn\": \"$TOPIC_ARN\"}}}]}"}'

  # Subscribe with filter policy
  awslocal sns subscribe \
    --topic-arn "$TOPIC_ARN" \
    --protocol sqs \
    --notification-endpoint "$QUEUE_ARN" \
    --attributes "$FILTER_POLICY"
done