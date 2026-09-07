import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

def create_embedding(text: str):
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )

    return response.data[0].embedding
