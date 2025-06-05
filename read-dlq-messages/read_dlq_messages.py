"""python sqs_dlq_reader.py --dlq-name=\"my-dead-letter-queue\""""

import boto3
import json
import os
import time
import argparse
from botocore.exceptions import ClientError

def list_queues(sqs_client):
    """List all SQS queues in the account and region for debugging."""
    try:
        response = sqs_client.list_queues()
        queues = response.get('QueueUrls', [])
        if queues:
            print("Available queues in this region:")
            for queue_url in queues:
                print(f" - {queue_url}")
        else:
            print("No queues found in this region.")
        return queues
    except ClientError as e:
        print(f"Error listing queues: {e}")
        return []

def read_dlq_messages(dlq_name, region_name=None):
    try:
        # Use environment variable for region if not provided
        if not region_name:
            region_name = os.getenv('AWS_REGION', 'us-west-2')  # Default to us-west-2 if not set
        print(f"Using AWS region: {region_name}")

        # Initialize SQS client with specified region
        sqs_client = boto3.client('sqs', region_name=region_name)
        sqs_resource = boto3.resource('sqs', region_name=region_name)

        # Validate queue existence
        try:
            queue_url = sqs_client.get_queue_url(QueueName=dlq_name)['QueueUrl']
            print(f"Connected to DLQ: {dlq_name} ({queue_url})")
        except ClientError as e:
            if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                print(f"Error: Queue '{dlq_name}' does not exist in region '{region_name}'.")
                print("Listing available queues for debugging:")
                list_queues(sqs_client)
                return
            raise

        # Get the DLQ
        dlq = sqs_resource.Queue(queue_url)

        # Get approximate number of messages
        no_of_messages = dlq.attributes['ApproximateNumberOfMessages']
        print(f"Initial number of messages in DLQ: {no_of_messages}")

        # Process messages while there are any in the DLQ
        while int(no_of_messages) > 0:
            # Receive up to 10 messages at a time
            messages = dlq.receive_messages(
                MaxNumberOfMessages=10,
                WaitTimeSeconds=1  # Short polling for simplicity
            )

            if not messages:
                print("No messages received in this batch, checking again...")
                time.sleep(1)  # Avoid rapid empty polling
                no_of_messages = dlq.attributes['ApproximateNumberOfMessages']
                continue

            # Process each message
            for message in messages:
                try:
                    # Parse the message body as JSON
                    body = json.loads(message.body)
                    
                    # Check if eventType in MessageAttributes is 'policy-header-record.created'
                    event_type = body.get('MessageAttributes', {}).get('eventType', {}).get('Value')

                    # Parse the Message field as JSON to get the id
                    message_content = json.loads(body.get('Message', '{}'))
                    message_id = message_content.get('id')
                    if not message_id:
                        print(f"Skipping message ID: {message.message_id} (no id found in Message)")
                        continue

                    # Output the entire message body
                    print(f"Message ID: {message.message_id}")
                    print(json.dumps(message_content, indent=2))

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON for message ID: {message.message_id}: {e}")
                    continue
                except Exception as e:
                    print(f"Error processing message ID: {message.message_id}: {e}")
                    continue  # Skip to next message on error

            # Update message count
            no_of_messages = dlq.attributes['ApproximateNumberOfMessages']
            print(f"Remaining messages in DLQ: {no_of_messages}")

        print("DLQ is empty or no more messages to process.")

    except ClientError as e:
        print(f"AWS ClientError: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Read messages from an AWS SQS Dead Letter Queue")
    parser.add_argument("--dlq-name", required=True, help="Name of the SQS Dead Letter Queue")
    args = parser.parse_args()

    # Call the function with the provided DLQ name
    read_dlq_messages(args.dlq_name)
