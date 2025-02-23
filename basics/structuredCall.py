import os

from openai import OpenAI
from pydantic import BaseModel

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# --------------------------------------------------------------
# Step 1: Define the response format in a Pydantic model
# --------------------------------------------------------------


class ticketEvent(BaseModel):
    name: str
    date: str
    numberOfTickets: int
    locationOfTickets: str
    participants: list[str]


# --------------------------------------------------------------
# Step 2: Call the model
# --------------------------------------------------------------

completion = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Extract the event information."},
        {
            "role": "user",
            "content": "I want three tickets to the next Memphsi Grizzlies game vs the Lakers on Christmass day. I would like floor seats.",
        },
    ],
    response_format=ticketEvent, # <-- Use this class
)

# --------------------------------------------------------------
# Step 3: Parse the response
# --------------------------------------------------------------

event = completion.choices[0].message.parsed
event.name
event.date
event.participants
event.numberOfTickets
event.locationOfTickets

print(event)


""" output:
name='Memphis Grizzlies vs Los Angeles Lakers' 
date='2023-12-25' 
numberOfTickets=3 
locationOfTickets='Floor seats' 
participants=['Memphis Grizzlies', 'Los Angeles Lakers']
"""