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

"""
{'id': 'chatcmpl-B67RjQhNHBYcW6dZJvlM0wadfdadadqR7vXh4', 'choices': [
        {'finish_reason': 'tool_calls', 'index': 0, 'logprobs': None, 'message': {'content': None, 'refusal': None, 'role': 'assistant', 'audio': None, 'function_call': None, 'tool_calls': [
                    {'id': 'call_DvNWf6dfdsdcWWq7cdH7f5IX6uzYyq', 'function': {'arguments': '{
                                "question": "Can I get into the Grizzlies game with a paper ticket?"
                            }', 'name': 'search_data'
                        }, 'type': 'function'
                    }
                ]
            }
        }
    ], 'created': 1740798291, 'model': 'gpt-4o-mini-2024-07-18', 'object': 'chat.completion', 'service_tier': 'default', 'system_fingerprint': 'fp_06737a9306', 'usage': {'completion_tokens': 28, 'prompt_tokens': 77, 'total_tokens': 105, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0
        }, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0
        }
    }
}
{'status': 'success', 'timestamp': '2025-02-28T00: 00: 00Z', 'team': 'Memphis Grizzlies', 'season': '2024-25', 'ticketing_policies': [
        {'policy_id': 1, 'title': 'No Refunds or Exchanges', 'description': 'All ticket sales are final. No refunds or exchanges will be issued except in the case of game cancellation without rescheduling.', 'last_updated': '2024-10-01'
        },
        {'policy_id': 2, 'title': 'Mobile Entry Only', 'description': 'Entry to FedExForum requires mobile tickets via the Grizzlies Mobile App or Ticketmaster account. Physical tickets are not accepted.', 'last_updated': '2024-09-15'
        },
        {'policy_id': 3, 'title': 'Child Admission Policy', 'description': "Children under 2 years old may enter free if they sit on an adult's lap. All other children require a ticket.", 'last_updated': '2024-08-20'
        },
        {'policy_id': 4, 'title': 'Resale Restrictions', 'description': 'Tickets may only be resold through official Grizzlies partners (e.g., Ticketmaster). Third-party resales above face value are prohibited.', 'last_updated': '2024-11-01'
        },
        {'policy_id': 5, 'title': 'Game Time Changes', 'description': 'Ticket holders will be notified of any game time changes via email. Original tickets remain valid unless otherwise stated.', 'last_updated': '2024-10-15'
        }
    ]
}
ParsedChatCompletion[DataResponse
](id='chatcmpl-B67RdskK6FebadfadungIxOH9U0wtszeHVrS', choices=[ParsedChoice[DataResponse
    ](finish_reason='stop', index=0, logprobs=None, message=ParsedChatCompletionMessage[DataResponse
    ](content='{
        "answer": "No, you cannot get into the Grizzlies game with a paper ticket. Entry to FedExForum requires mobile tickets via the Grizzlies Mobile App or Ticketmaster account; physical tickets are not accepted.",
        "source": 2
    }', refusal=None, role='assistant', audio=None, function_call=None, tool_calls=None, parsed=DataResponse(answer='No, you cannot get into the Grizzlies game with a paper ticket. Entry to FedExForum requires mobile tickets via the Grizzlies Mobile App or Ticketmaster account; physical tickets are not accepted.', source=2)))
], created=1740798292, model='gpt-4o-mini-2024-07-18', object='chat.completion', service_tier='default', system_fingerprint='fp_06737a9306', usage=CompletionUsage(completion_tokens=55, prompt_tokens=505, total_tokens=560, completion_tokens_details=CompletionTokensDetails(accepted_prediction_tokens=0, audio_tokens=0, reasoning_tokens=0, rejected_prediction_tokens=0), prompt_tokens_details=PromptTokensDetails(audio_tokens=0, cached_tokens=0)))
answer='No, you cannot get into the Grizzlies game with a paper ticket. Entry to FedExForum requires mobile tickets via the Grizzlies Mobile App or Ticketmaster account; physical tickets are not accepted.' source=2
"""

# --------------------------------------------------------------
# Question that doesn't trigger the tool
# --------------------------------------------------------------

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "What is the weather in Memphis Tennessee?"},
]

completion_3 = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
)

completion_3.choices[0].message.content