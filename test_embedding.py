import os
from openai import OpenAI
client = OpenAI(
    api_key=os.environ.get("ARK_API_KEY", "ark-你的火山方舟APIKey"),
    base_url="https://ark.cn-beijing.volces.com/api/v3",
)
print("----- embeddings request -----")
resp = client.embeddings.create(
    model="doubao-embedding-text-240715",
    input=["花椰菜又称菜花、花菜，是一种常见的蔬菜。"],
    encoding_format="float"
)
print(resp)
