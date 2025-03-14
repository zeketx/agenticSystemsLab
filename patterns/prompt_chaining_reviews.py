from pydantic import BaseModel, Field
from openai import OpenAI
import json
from typing import List, Dict, Any
from typing import Optional
import os
import logging
# --------------------------------------------------------------
# Set up logging config
# --------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4o-mini-2024-07-18"
# --------------------------------------------------------------
# Define the data models for each stage
# --------------------------------------------------------------

class ReviewClassification(BaseModel):
    """First LLM call: Determine if text is a review and basic classification"""
    raw_text: str
    is_product_review: bool
    product_category: str
    overall_sentiment: str  # positive, negative, mixed, neutral
    confidence_score: float

class ReviewDetails(BaseModel):
    """Second LLM call: Extract specific insights"""
    product_name: str
    mentioned_features: list[dict]  # [{"feature": "battery life", "sentiment": "positive"}]
    pros: list[str]
    cons: list[str]
    improvement_suggestions: list[str]
    categorize_feedback: list[str] # bug report, feature request, feature enhancement, general feedback
    key_quotes: list[str]  # Quotable sections

class ReviewAnalysis(BaseModel):
    """Third LLM call: Generate actionable insights"""
    summary: str
    priority_level: str  # high, medium, low
    recommended_actions: list[str]
    similar_reviews_pattern: bool  # indicates if this matches other feedback

# --------------------------------------------------------------
# Load the review data from local JSON file
# --------------------------------------------------------------
def load_review_data(file_path: str) -> List[Dict[str, Any]]:
    """Load review data from a local JSON file"""
    with open("reviewData.json", "r") as f:
        reviews = json.load(f)
    return reviews 
# --------------------------------------------------------------
# Define the functions
# --------------------------------------------------------------
def validate_review(review_text: str) -> Optional[ReviewClassification]:
    """
    Determines if a given text is a legitimate product review and provides structured classification.

    Args:
        review_text (str): The review text to analyze.

    Returns:
        ReviewClassification: Structured response object with review analysis.
        None: If the API response is invalid or an error occurs.
    """
    logger.info("Starting review validation analysis")
    
    try:
        # Call OpenAI API with structured output format
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Analyze the text and classify it as a product review or not."},
                {"role": "user", "content": review_text},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "review_classification",
                    "description": "Classifies whether text is a product review and provides sentiment analysis.",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "raw_text": {"type": "string"},
                            "is_product_review": {"type": "boolean"},
                            "product_category": {"type": "string"},
                            "overall_sentiment": {
                                "type": "string",
                                "enum": ["positive", "negative", "mixed", "neutral"]
                            },
                            "confidence_score": {"type": "number"}
                        },
                        "required": ["raw_text", "is_product_review", "product_category", "overall_sentiment", "confidence_score"],
                        "additionalProperties": False
                    }
                }
            }
        )

        # Extract structured response
        structured_response = completion.choices[0].message.content

        if structured_response:
            # Print raw API response for debugging
            print("\n--- DEBUG: Raw API Response ---")
            print(structured_response)
            print("--------------------------------\n")

            # Parse response into ReviewClassification model
            parsed_response = ReviewClassification.model_validate_json(structured_response)

            # Print parsed response in a readable format
            print("\n--- DEBUG: Parsed Response ---")
            print(f"Raw Text: {parsed_response.raw_text}")
            print(f"Is Product Review: {parsed_response.is_product_review}")
            print(f"Product Category: {parsed_response.product_category}")
            print(f"Overall Sentiment: {parsed_response.overall_sentiment}")
            print(f"Confidence Score: {parsed_response.confidence_score}")
            print("--------------------------------\n")

            return parsed_response

    except Exception as e:
        logger.error(f"Error during review validation: {e}", exc_info=True)
    
    return None

# --------------------------------------------------------------
# Step 3: Chain the functions together
# --------------------------------------------------------------

# --------------------------------------------------------------
# Step 4: Test the chain with a valid input
# --------------------------------------------------------------
def test_review_validation():
    # Path to your JSON file
    reviews = load_review_data('reviewData.json')
    
    for review in reviews:
        print(f"\nProcessing review: {review['id']}")
        print(f"Title: {review['title']}")
        
        # Pass the review text to the validation function
        result = validate_review(review['review_text'])
        
        print(f"Is a product review: {result.is_product_review}")
        print(f"Product category: {result.product_category}")
        print(f"Overall sentiment: {result.overall_sentiment}")
        print(f"Confidence score: {result.confidence_score}")
        print("-------------------------------------------")

# Example usage
if __name__ == "__main__":
    test_review_validation()
# --------------------------------------------------------------
# Step 5: Test the chain with an invalid input
# --------------------------------------------------------------

"""
2025-03-11 21:50:18 - INFO - Starting review validation analysis

Processing review: rev_nba_12345
Title: Great live stats, but sometimes delayed
2025-03-11 21:50:21 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-11 21:50:21 - INFO - Starting review validation analysis

--- DEBUG: Raw API Response ---
{"raw_text":"I love being able to track all the live stats during the game. The shot charts, player comparisons, and possession breakdowns are fantastic. The interface is clean and easy to navigate. However, I've noticed the stats sometimes lag behind the actual game by a few plays. It's usually only a few seconds, but it can be frustrating when you're trying to follow along in real-time. Still a great feature overall.","is_product_review":true,"product_category":"sports statistics tracking apps","overall_sentiment":"mixed","confidence_score":0.85}
--------------------------------


--- DEBUG: Parsed Response ---
Raw Text: I love being able to track all the live stats during the game. The shot charts, player comparisons, and possession breakdowns are fantastic. The interface is clean and easy to navigate. However, I've noticed the stats sometimes lag behind the actual game by a few plays. It's usually only a few seconds, but it can be frustrating when you're trying to follow along in real-time. Still a great feature overall.
Is Product Review: True
Product Category: sports statistics tracking apps
Overall Sentiment: mixed
Confidence Score: 0.85
--------------------------------

Is a product review: True
Product category: sports statistics tracking apps
Overall sentiment: mixed
Confidence score: 0.85
-------------------------------------------

Processing review: rev_nba_23456
Title: Disappointed with the app's ticket purchase flow - crashed multiple times
2025-03-11 21:50:22 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-11 21:50:22 - INFO - Starting review validation analysis

--- DEBUG: Raw API Response ---
{"raw_text":"I was excited to buy tickets for the upcoming game through the app. The seat selection and price filtering were good. Unfortunately, the app crashed three times during the checkout process. I had to restart my phone and re-enter my payment information each time. When I finally got through, the seats I originally selected were no longer available. Customer support has not responded to my emails. I'll stick to buying tickets through the website next time.","is_product_review":true,"product_category":"Mobile App","overall_sentiment":"mixed","confidence_score":0.85}
--------------------------------


--- DEBUG: Parsed Response ---
Raw Text: I was excited to buy tickets for the upcoming game through the app. The seat selection and price filtering were good. Unfortunately, the app crashed three times during the checkout process. I had to restart my phone and re-enter my payment information each time. When I finally got through, the seats I originally selected were no longer available. Customer support has not responded to my emails. I'll stick to buying tickets through the website next time.
Is Product Review: True
Product Category: Mobile App
Overall Sentiment: mixed
Confidence Score: 0.85
--------------------------------

Is a product review: True
Product category: Mobile App
Overall sentiment: mixed
Confidence score: 0.85
-------------------------------------------

Processing review: rev_nba_34567
Title: Finally, a reliable source for team news!
2025-03-11 21:50:24 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-11 21:50:24 - INFO - Starting review validation analysis

--- DEBUG: Raw API Response ---
{"raw_text":"I've been looking for an app that gives me real-time updates on my team. The news alerts feature is perfect. I get notified about trades, injuries, and game highlights as soon as they happen. The articles are well-written and the push notifications are timely. The ability to customize the alert settings is a great touch. Highly recommend this feature for any die-hard fan.","is_product_review":true,"product_category":"mobile app","overall_sentiment":"positive","confidence_score":0.95}
--------------------------------


--- DEBUG: Parsed Response ---
Raw Text: I've been looking for an app that gives me real-time updates on my team. The news alerts feature is perfect. I get notified about trades, injuries, and game highlights as soon as they happen. The articles are well-written and the push notifications are timely. The ability to customize the alert settings is a great touch. Highly recommend this feature for any die-hard fan.
Is Product Review: True
Product Category: mobile app
Overall Sentiment: positive
Confidence Score: 0.95
--------------------------------

Is a product review: True
Product category: mobile app
Overall sentiment: positive
Confidence score: 0.95
-------------------------------------------

Processing review: rev_nba_45678
Title: Good highlights but buffering issues
2025-03-11 21:50:26 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-11 21:50:26 - INFO - Starting review validation analysis

--- DEBUG: Raw API Response ---
{"raw_text":"I've been using the highlight feature for a few weeks. The quality of the video is excellent, and I love being able to re-watch key plays. However, I've experienced frequent buffering issues, especially during peak times. Sometimes the videos freeze or skip. I have a fast internet connection, so I don't think it's on my end. If the app developers can improve the streaming performance, this would be a top-notch feature.","is_product_review":true,"product_category":"video streaming app","overall_sentiment":"mixed","confidence_score":0.85}
--------------------------------


--- DEBUG: Parsed Response ---
Raw Text: I've been using the highlight feature for a few weeks. The quality of the video is excellent, and I love being able to re-watch key plays. However, I've experienced frequent buffering issues, especially during peak times. Sometimes the videos freeze or skip. I have a fast internet connection, so I don't think it's on my end. If the app developers can improve the streaming performance, this would be a top-notch feature.
Is Product Review: True
Product Category: video streaming app
Overall Sentiment: mixed
Confidence Score: 0.85
--------------------------------

Is a product review: True
Product category: video streaming app
Overall sentiment: mixed
Confidence score: 0.85
-------------------------------------------

Processing review: rev_nba_56789
Title: Excellent arena map feature - made my game day experience much better!
2025-03-11 21:50:28 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"

--- DEBUG: Raw API Response ---
{"raw_text":"This feature was a game-changer! I used the arena map to find my seats, locate the nearest restrooms, and check out the concession stands. The ability to see menus and order food directly from the app was incredibly convenient. The map was easy to navigate and the directions were accurate. This made my game day experience much more enjoyable. I wish more sports apps had this feature!","is_product_review":true,"product_category":"mobile app","overall_sentiment":"positive","confidence_score":0.95}
--------------------------------


--- DEBUG: Parsed Response ---
Raw Text: This feature was a game-changer! I used the arena map to find my seats, locate the nearest restrooms, and check out the concession stands. The ability to see menus and order food directly from the app was incredibly convenient. The map was easy to navigate and the directions were accurate. This made my game day experience much more enjoyable. I wish more sports apps had this feature!
Is Product Review: True
Product Category: mobile app
Overall Sentiment: positive
Confidence Score: 0.95
--------------------------------

Is a product review: True
Product category: mobile app
Overall sentiment: positive
Confidence score: 0.95
-------------------------------------------

"""