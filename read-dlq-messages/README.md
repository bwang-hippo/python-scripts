## read_dlq_message.py

### Overview
`read_dlq_message.py` is a Python script that processes messages from an AWS SQS Dead Letter Queue (DLQ). It extracts the `id` field from the `Message` attribute of each SQS message and prints the `Message` content in a pretty-printed JSON format. The script is designed for debugging or extracting specific data from a DLQ in the Hippo Insurance AWS environment.

### Features
- **Reads Messages in Batches**: Fetches up to 10 messages at a time from the specified DLQ using short polling (`WaitTimeSeconds=1`).
- **Extracts IDs**: Parses the `Message` field of each SQS message to extract the `id` and writes it to `messages.json` in the format `'<id>',\n`.
- **Pretty-Prints Message Content**: Outputs the `Message` field (parsed as JSON) for each message, aiding in debugging or inspection.
- **Error Handling**: Skips messages with invalid JSON or missing `id` fields, logging errors for traceability.
- **Queue Validation**: Checks for the existence of the specified DLQ and lists available queues if it doesn’t exist.

### Why Check for Messages in Each Batch?
The script checks if messages are received in each batch (`if not messages`) because AWS SQS is a distributed system. The `receive_messages` call may return no messages due to:
- **Eventual Consistency**: Messages may not be immediately available due to replication delays across SQS servers.
- **Short Polling**: With a 1-second wait time, responses may be empty even if messages exist, necessitating retries.
This check prevents premature termination when messages are temporarily unavailable, with a 1-second pause to avoid rapid API calls.

### Does It Guarantee Processing All Messages?
The script does **not** guarantee that all DLQ messages are processed due to:
- **Distributed Nature**: SQS’s `ApproximateNumberOfMessages` is an estimate and may not reflect the exact message count due to eventual consistency.
- **No Message Deletion**: Messages are not deleted after processing, so they remain in the queue and could be reprocessed or missed if processed by other consumers.
- **Short Polling**: The 1-second polling may miss messages temporarily unavailable on distributed servers.
- **Error Skipping**: Messages with parsing errors are skipped without retries.
To improve completeness, consider adding message deletion (`message.delete()`) and long polling (`WaitTimeSeconds=20`). However, absolute guarantees are challenging due to SQS’s distributed architecture.

### Prerequisites
- **Python**: Version 3.6 or higher.
- **Dependencies**: Install required packages:
  ```bash
  pip install boto3
  ```
- **AWS Credentials**: Configure AWS credentials via `~/.aws/credentials`, environment variables, or an IAM role with SQS read permissions.
- **AWS Region**: Defaults to `us-west-2` if not set via the `AWS_REGION` environment variable.

### Usage
Run the script with the `--dlq-name` argument to specify the DLQ:

```bash
python read_dlq_message.py --dlq-name="my-dead-letter-queue"
```

### Example Output
For an SQS message with the body:
```json
{
  "Type": "Notification",
  "MessageId": "0eb3cc14-af08-5e4e-ba96-acbcc7a69c3d",
  "Message": "{\"eventType\":\"policy-header-record.created\",\"id\":\"5c8ab6cd-0b24-495c-ad7e-1074cc74cf4f\"}",
  ...
}
```

The script outputs:
```
Message ID: 0eb3cc14-af08-5e4e-ba96-acbcc7a69c3d
{
  "eventType": "policy-header-record.created",
  "id": "5c8ab6cd-0b24-495c-ad7e-1074cc74cf4f"
}
```