import json
import os

import requests
from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

"""
docs: https://platform.openai.com/docs/guides/function-calling
"""

# --------------------------------------------------------------
# Define the tool (function) that we want to call
# --------------------------------------------------------------


def get_weather(latitude, longitude):
    """This is a publically available API that returns the weather for a given location."""
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )
    data = response.json()
    return data["current"]


# --------------------------------------------------------------
# Step 1: Call model with get_weather tool defined
# --------------------------------------------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current temperature for provided coordinates in celsius.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required": ["latitude", "longitude"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]

system_prompt = "You are a helpful weather assistant."

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "What's the weather like in Memphis Tennessee today?"},
]

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
)

# --------------------------------------------------------------
# Step 2: Model decides to call function(s)
# --------------------------------------------------------------

completion.model_dump()


"""ChatCompletion(
# When you call completion.model_dump(), it returns something like this:
{
    'id': 'chatcmpl-B3o8J13KlsdmQjyh9HXhp2AUE3kqPAds7',
    'choices': [{
        'finish_reason': 'tool_calls',
        'index': 0,
        'logprobs': None,
        'message': {
            'content': None,
            'refusal': None,
            'role': 'assistant',
            'audio': None,
            'function_call': None,
            'tool_calls': [{
                'id': 'call_oAlOPd0sdin2LqDtuVGsQcFqYuad',
                'function': {
                    'arguments': '{"latitude":35.1495,"longitude":-90.049}',
                    'name': 'get_weather'
                },
                'type': 'function'
            }]
        }
    }],
    'created': 1740247395,
    'model': 'gpt-4o-2024-08-06',
    'object': 'chat.completion',
    'service_tier': 'default',
    'system_fingerprint': 'fp_eb9ddcsde5436a8',
    'usage': {
        'completion_tokens': 25,
        'prompt_tokens': 67,
        'total_tokens': 92,
        'completion_tokens_details': {
            'accepted_prediction_tokens': 0,
            'audio_tokens': 0,
            'reasoning_tokens': 0,
            'rejected_prediction_tokens': 0
        },
        'prompt_tokens_details': {
            'audio_tokens': 0,
            'cached_tokens': 0
        }
    }
}
)"""
# --------------------------------------------------------------
# Step 3: Execute get_weather function
# --------------------------------------------------------------


def call_function(name, args):
    if name == "get_weather":
        return get_weather(**args)


for tool_call in completion.choices[0].message.tool_calls:
    name = tool_call.function.name #<--'name': 'get_weather'
    args = json.loads(tool_call.function.arguments)
    messages.append(completion.choices[0].message)

    result = call_function(name, args)
    messages.append( # working with memory
        {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
    )

# --------------------------------------------------------------
# Step 4: Supply result and call model again
# --------------------------------------------------------------


class WeatherResponse(BaseModel):
    temperature: float = Field(
        description="The current temperature in celsius for the given location."
    )
    response: str = Field(
        description="A natural language response to the user's question."
    )


completion_2 = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=messages,
    tools=tools,
    response_format=WeatherResponse,
)

# --------------------------------------------------------------
# Step 5: Check model response
# --------------------------------------------------------------

final_response = completion_2.choices[0].message.parsed
final_response.temperature
final_response.response

print(final_response)



"""flow of information (Mermaid diagram )

sequenceDiagram
    participant User
    participant OpenAI Client
    participant GPT-4
    participant Weather API
    
    Note over User,Weather API: Step 1: Initial Setup
    User->>OpenAI Client: Ask about weather in Paris
    OpenAI Client->>GPT-4: Send query + tools definition
    
    Note over GPT-4: Step 2: Function Call Decision
    GPT-4-->>OpenAI Client: Decide to call get_weather
    
    Note over OpenAI Client,Weather API: Step 3: Execute Function
    OpenAI Client->>Weather API: Call get_weather(latitude, longitude)
    Weather API-->>OpenAI Client: Return weather data
    
    Note over OpenAI Client,GPT-4: Step 4: Process Weather Data
    OpenAI Client->>GPT-4: Send weather data
    
    Note over GPT-4: Step 5: Final Response
    GPT-4-->>OpenAI Client: Generate structured response
    OpenAI Client-->>User: Return formatted weather info"""