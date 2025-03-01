import json
import os

from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

"""
docs: https://platform.openai.com/docs/guides/function-calling
"""

# --------------------------------------------------------------
# Define the knowledge base retrieval tool
# --------------------------------------------------------------


def search_data(question: str):
    """
    Load the whole knowledge base from the JSON file.
    (This is a mock function for demonstration purposes, we don't search)
    """
    with open("data.json", "r") as f:
        return json.load(f)


# --------------------------------------------------------------
# Step 1: Call model with search_data tool defined
# --------------------------------------------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_data",
            "description": "Get the answer to the user's question from the knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                },
                "required": ["question"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]

system_prompt = "You are a helpful analyst that assists with questions against our data set."

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Can I get into the Grizzlies game with a paper ticket?"},
]

completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
)

# --------------------------------------------------------------
# Step 2: Model decides to call function(s)
# --------------------------------------------------------------

completion.model_dump()
print(completion.model_dump())

# --------------------------------------------------------------
# Step 3: Execute search_data function
# --------------------------------------------------------------


def call_function(name, args):
    if name == "search_data":
        return search_data(**args)

for tool_call in completion.choices[0].message.tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    messages.append(completion.choices[0].message)

    result = call_function(name, args)
    print(result)
    messages.append(
        {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
    )

# --------------------------------------------------------------
# Step 4: Supply result and call model again
# --------------------------------------------------------------


class DataResponse(BaseModel):
    answer: str = Field(description="The answer to the user's question.")
    source: int = Field(description="The record id of the answer.")


completion_2 = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
    response_format=DataResponse,
)

print(completion_2)
# --------------------------------------------------------------
# Step 5: Check model response
# --------------------------------------------------------------

final_response = completion_2.choices[0].message.parsed
final_response.answer
final_response.source

print(final_response)
# --------------------------------------------------------------
# Question that doesn't trigger the tool
# --------------------------------------------------------------

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "What is the weather in Tokyo?"},
]

completion_3 = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
)

completion_3.choices[0].message.content