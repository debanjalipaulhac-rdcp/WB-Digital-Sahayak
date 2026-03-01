from openai import OpenAI  
from .settings import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY,baseurl="https://api.openai.com/v1")  

response = client.responses.create( 

    model="openai.gpt-oss-120b", 
    input=[ 
        {"role": "user", "content": "Write a one-sentence bedtime story about a unicorn."} 
    ] 
)  

print(response.output_text)