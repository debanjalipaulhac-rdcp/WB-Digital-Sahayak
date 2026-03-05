import boto3
import json
from src.config.settings import settings
from botocore.exceptions import ClientError

# Initialize the client
client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
)

model_id = "amazon.nova-micro-v1:0"
user_message = "Describe the purpose of a 'hello world' program in one line."

# The Converse API expects this specific structure
conversation = [
    {
        "role": "user",
        "content": [{"text": user_message}],
    }
]

try:
    # Use converse_stream if you want real-time output, 
    # or just converse for a single response.
    response = client.converse(
        modelId=model_id,
        messages=conversation,
        system=[{"text": "You are a helpful assistant."}],
        inferenceConfig={
            "maxTokens": 512, 
            "temperature": 0.5, 
            "topP": 0.9
        }
    )

    # Clean extraction of the text
    output_text = response['output']['message']['content'][0]['text']
    print(f" {output_text}")

except ClientError as e:
    print(f"AWS Error: {e.response['Error']['Message']}")
except Exception as e:
    print(f"Unexpected Error: {e}")