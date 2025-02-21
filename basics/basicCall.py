import os

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You're a helpful assistant."},
        {
            "role": "user",
            "content": "Write me a short story about a robot who wants to be human.",
        },
    ],
)

response = completion.choices[0].message.content
print(response)