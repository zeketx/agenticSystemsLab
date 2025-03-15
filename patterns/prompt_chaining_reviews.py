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

class JiraTicket(BaseModel):
    """Third LLM call: model for JIRA ticket"""
    ticket_id: str
    title: str
    description: str
    status: str
    assignee: str
    reporter: str
    priority: str
    due_date: str  # Expected in YYYY-MM-DD format

class ReviewAnalysis(BaseModel):
    """Third LLM call: Generate actionable insights and include a nested JIRA ticket"""
    summary: str
    priority_level: str  # high, medium, low
    recommended_actions: List[str]
    similar_reviews_pattern: bool
    jira_ticket: JiraTicket

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

def extract_review_details(review_text: str, classification: ReviewClassification) -> Optional[ReviewDetails]:
    """
    Extracts specific insights from the review text using details from the initial classification.
    
    Args:
        review_text (str): The original review text.
        classification (ReviewClassification): The structured output from the first LLM call.
    
    Returns:
        ReviewDetails: Structured insights extracted from the review.
        None: If the API response is invalid or an error occurs.
    """
    logger.info("Starting review details extraction")
    
    # Construct a prompt that includes context from the classification result
    prompt = (
        f"Given the following review text: '{review_text}', "
        f"and knowing that it is classified as a product review in the category '{classification.product_category}' "
        f"with an overall sentiment of '{classification.overall_sentiment}', "
        "extract the following details in a structured JSON format: "
        "- product_name: The name of the product being reviewed. "
        "- mentioned_features: A list of features mentioned along with their sentiment (e.g., battery life, positive). "
        "- pros: List the positive aspects mentioned. "
        "- cons: List the negative aspects mentioned. "
        "- improvement_suggestions: Any suggestions for improvement. "
        "- categorize_feedback: Categories like bug report, feature request, feature enhancement, general feedback. "
        "- key_quotes: Important excerpts from the review."
    )
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Extract detailed insights from a product review."},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "review_details",
                    "description": "Extracts detailed insights from a product review.",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string"},
                            "mentioned_features": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "feature": {"type": "string"},
                                        "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]}
                                    },
                                    "required": ["feature", "sentiment"],
                                    "additionalProperties": False
                                }
                            },
                            "pros": {"type": "array", "items": {"type": "string"}},
                            "cons": {"type": "array", "items": {"type": "string"}},
                            "improvement_suggestions": {"type": "array", "items": {"type": "string"}},
                            "categorize_feedback": {"type": "array", "items": {"type": "string"}},
                            "key_quotes": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["product_name", "mentioned_features", "pros", "cons", "improvement_suggestions", "categorize_feedback", "key_quotes"],
                        "additionalProperties": False
                    }
                }
            }
        )
        
        structured_response = completion.choices[0].message.content
        
        if structured_response:
            # Optionally print for debugging:
            print("\n--- DEBUG: Raw Details API Response ---")
            print(structured_response)
            print("----------------------------------------\n")
            
            details = ReviewDetails.model_validate_json(structured_response)
            print(details)
            print("\n--- DEBUG: Parsed Review Details ---")
            print(details.model_dump_json(indent=4))
            print("-------------------------------------\n")
            
            return details
        
    except Exception as e:
        logger.error(f"Error during review details extraction: {e}", exc_info=True)
    
    return None

def generate_review_analysis(
    review_text: str,
    classification: ReviewClassification,
    details: ReviewDetails
) -> Optional[ReviewAnalysis]:
    """
    Uses review text, classification, and detailed insights to generate actionable analysis.
    This includes a summary, recommended actions, and a JIRA ticket for the review.
    
    Args:
        review_text (str): The original review text.
        classification (ReviewClassification): Output from the first LLM call.
        details (ReviewDetails): Output from the second LLM call.
    
    Returns:
        ReviewAnalysis: Structured actionable insights including a nested JIRA ticket.
        None: If an error occurs.
    """
    logger.info("Starting review analysis for actionable insights and JIRA ticket generation.")
    
    # Construct a detailed prompt using information from the classification and details
    prompt = (
        f"Review Text: {review_text}\n"
        f"Classification: The review is classified under product category '{classification.product_category}' "
        f"with an overall sentiment of '{classification.overall_sentiment}'.\n"
        f"Detailed Insights: {details.model_dump_json()}\n\n"
        "As a product manager, generate actionable insights for this review. Your response must include:\n"
        "1. A summary of the review.\n"
        "2. A priority level (high, medium, or low) that reflects if the review indicates a need for a new feature, "
        "a bug fix, or a rethinking of the existing feature.\n"
        "3. A list of recommended actions to address the review feedback.\n"
        "4. An indication if this review matches patterns from other similar reviews (true or false).\n"
        "5. A JIRA ticket creation with the following fields:\n"
        "   - Ticket ID: a unique identifier\n"
        "   - Title: a concise and descriptive title for the issue\n"
        "   - Description: a detailed explanation of the issue including context and reproduction steps if applicable\n"
        "   - Status: the current state (e.g., 'To Do')\n"
        "   - Assignee: assign to either an engineering manager, product manager, or a member of the product team\n"
        "   - Reporter: assume the reporter is 'Product Manager'\n"
        "   - Priority: determine the urgency (e.g., 'High' if a bug fix is needed, 'Medium' for a feature request, etc.)\n"
        "   - Due Date: a suggested due date in YYYY-MM-DD format\n\n"
        "Return a valid JSON object with exactly these keys: summary, priority_level, recommended_actions, "
        "similar_reviews_pattern, and jira_ticket (which itself must have ticket_id, title, description, status, "
        "assignee, reporter, priority, due_date)."
    )
    
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Generate actionable insights and a JIRA ticket from a product review."},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "review_analysis",
                    "description": "Generates actionable insights including a JIRA ticket.",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string"},
                            "priority_level": {"type": "string", "enum": ["high", "medium", "low"]},
                            "recommended_actions": {"type": "array", "items": {"type": "string"}},
                            "similar_reviews_pattern": {"type": "boolean"},
                            "jira_ticket": {
                                "type": "object",
                                "properties": {
                                    "ticket_id": {"type": "string"},
                                    "title": {"type": "string"},
                                    "description": {"type": "string"},
                                    "status": {"type": "string"},
                                    "assignee": {"type": "string"},
                                    "reporter": {"type": "string"},
                                    "priority": {"type": "string"},
                                    "due_date": {"type": "string"}
                                },
                                "required": ["ticket_id", "title", "description", "status", "assignee", "reporter", "priority", "due_date"],
                                "additionalProperties": False
                            }
                        },
                        "required": ["summary", "priority_level", "recommended_actions", "similar_reviews_pattern", "jira_ticket"],
                        "additionalProperties": False
                    }
                }
            }
        )
        
        structured_response = completion.choices[0].message.content
        if structured_response:
            print("\n--- DEBUG: Raw API Response (Review Analysis) ---")
            print(structured_response)
            print("--------------------------------------------------\n")
            
            # Parse the response into the ReviewAnalysis model
            analysis = ReviewAnalysis.model_validate_json(structured_response)
            
            print("\n--- DEBUG: Parsed Review Analysis ---")
            print(analysis.model_dump_json(indent=4))
            print("--------------------------------------------------\n")
            
            return analysis
        
    except Exception as e:
        logger.error(f"Error during review analysis generation: {e}", exc_info=True)
    
    return None

# --------------------------------------------------------------
# Chain the functions together
# --------------------------------------------------------------
def run_full_review_analysis_pipeline():
    """
    Runs the full review analysis pipeline:
      1. Validates and classifies the review.
      2. Extracts detailed insights if the text is confirmed as a product review.
      3. Generates actionable insights along with a JIRA ticket.
    """
    reviews = load_review_data("reviewData.json")
    
    for review in reviews:
        print(f"\nProcessing review: {review['id']}")
        print(f"Title: {review['title']}\n")
        
        # Step 1: Validate and classify the review.
        classification = validate_review(review["review_text"])
        if not classification:
            print("Review classification failed.")
            print("-------------------------------------------")
            continue
        
        print("Classification:")
        print(f"  Is Product Review: {classification.is_product_review}")
        print(f"  Product Category: {classification.product_category}")
        print(f"  Overall Sentiment: {classification.overall_sentiment}")
        print(f"  Confidence Score: {classification.confidence_score}\n")
        
        # Gate check: Only proceed if it is a product review.
        if not classification.is_product_review:
            print("The text is not a product review; skipping further analysis.")
            print("-------------------------------------------")
            continue
        
        # Step 2: Extract detailed insights from the review.
        details = extract_review_details(review["review_text"], classification)
        if not details:
            print("Failed to extract review details.")
            print("-------------------------------------------")
            continue
        
        print("Review Details:")
        print(f"  Product Name: {details.product_name}")
        print(f"  Mentioned Features: {details.mentioned_features}")
        print(f"  Pros: {details.pros}")
        print(f"  Cons: {details.cons}")
        print(f"  Improvement Suggestions: {details.improvement_suggestions}")
        print(f"  Categorize Feedback: {details.categorize_feedback}")
        print(f"  Key Quotes: {details.key_quotes}\n")
        
        # Step 3: Generate actionable insights and create a JIRA ticket.
        analysis = generate_review_analysis(review["review_text"], classification, details)
        if analysis:
            print("Review Analysis and JIRA Ticket:")
            print(f"  Summary: {analysis.summary}")
            print(f"  Priority Level: {analysis.priority_level}")
            print(f"  Recommended Actions: {analysis.recommended_actions}")
            print(f"  Similar Reviews Pattern: {analysis.similar_reviews_pattern}")
            print("  JIRA Ticket:")
            print(f"    Ticket ID: {analysis.jira_ticket.ticket_id}")
            print(f"    Title: {analysis.jira_ticket.title}")
            print(f"    Description: {analysis.jira_ticket.description}")
            print(f"    Status: {analysis.jira_ticket.status}")
            print(f"    Assignee: {analysis.jira_ticket.assignee}")
            print(f"    Reporter: {analysis.jira_ticket.reporter}")
            print(f"    Priority: {analysis.jira_ticket.priority}")
            print(f"    Due Date: {analysis.jira_ticket.due_date}\n")
        else:
            print("Failed to generate review analysis.")
        
        print("-------------------------------------------")


if __name__ == "__main__":
    run_full_review_analysis_pipeline()


"""
# --------------------------------------------------------------
#  RESPONSES Example
# --------------------------------------------------------------
2025-03-15 16:33:52 - INFO - Starting review validation analysis

Processing review: rev_nba_12345
Title: Great live stats, but sometimes delayed

2025-03-15 16:33:55 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:33:55 - INFO - Starting review details extraction

--- DEBUG: Raw API Response ---
{"raw_text":"I love being able to track all the live stats during the game. The shot charts, player comparisons, and possession breakdowns are fantastic. The interface is clean and easy to navigate. However, I've noticed the stats sometimes lag behind the actual game by a few plays. It's usually only a few seconds, but it can be frustrating when you're trying to follow along in real-time. Still a great feature overall.","is_product_review":true,"product_category":"sports analytics application","overall_sentiment":"mixed","confidence_score":0.85}
--------------------------------


--- DEBUG: Parsed Response ---
Raw Text: I love being able to track all the live stats during the game. The shot charts, player comparisons, and possession breakdowns are fantastic. The interface is clean and easy to navigate. However, I've noticed the stats sometimes lag behind the actual game by a few plays. It's usually only a few seconds, but it can be frustrating when you're trying to follow along in real-time. Still a great feature overall.
Is Product Review: True
Product Category: sports analytics application
Overall Sentiment: mixed
Confidence Score: 0.85
--------------------------------

Classification:
  Is Product Review: True
  Product Category: sports analytics application
  Overall Sentiment: mixed
  Confidence Score: 0.85

2025-03-15 16:33:57 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:33:57 - INFO - Starting review analysis for actionable insights and JIRA ticket generation.

--- DEBUG: Raw Details API Response ---
{"product_name":"sports analytics application","mentioned_features":[{"feature":"live stats tracking","sentiment":"positive"},{"feature":"shot charts","sentiment":"positive"},{"feature":"player comparisons","sentiment":"positive"},{"feature":"possession breakdowns","sentiment":"positive"},{"feature":"interface","sentiment":"positive"},{"feature":"stats lag","sentiment":"negative"}],"pros":["Ability to track live stats","Fantastic shot charts","Comparisons between players","Detailed possession breakdowns","Clean and easy-to-navigate interface"],"cons":["Stats sometimes lag behind actual game","Lag can be frustrating when following along in real-time"],"improvement_suggestions":["Reduce the lag in stats updates"],"categorize_feedback":["bug report","general feedback"],"key_quotes":["I love being able to track all the live stats during the game.","The shot charts, player comparisons, and possession breakdowns are fantastic.","The interface is clean and easy to navigate.","I've noticed the stats sometimes lag behind the actual game by a few plays."]}
----------------------------------------

product_name='sports analytics application' mentioned_features=[{'feature': 'live stats tracking', 'sentiment': 'positive'}, {'feature': 'shot charts', 'sentiment': 'positive'}, {'feature': 'player comparisons', 'sentiment': 'positive'}, {'feature': 'possession breakdowns', 'sentiment': 'positive'}, {'feature': 'interface', 'sentiment': 'positive'}, {'feature': 'stats lag', 'sentiment': 'negative'}] pros=['Ability to track live stats', 'Fantastic shot charts', 'Comparisons between players', 'Detailed possession breakdowns', 'Clean and easy-to-navigate interface'] cons=['Stats sometimes lag behind actual game', 'Lag can be frustrating when following along in real-time'] improvement_suggestions=['Reduce the lag in stats updates'] categorize_feedback=['bug report', 'general feedback'] key_quotes=['I love being able to track all the live stats during the game.', 'The shot charts, player comparisons, and possession breakdowns are fantastic.', 'The interface is clean and easy to navigate.', "I've noticed the stats sometimes lag behind the actual game by a few plays."]

--- DEBUG: Parsed Review Details ---
{
    "product_name": "sports analytics application",
    "mentioned_features": [
        {
            "feature": "live stats tracking",
            "sentiment": "positive"
        },
        {
            "feature": "shot charts",
            "sentiment": "positive"
        },
        {
            "feature": "player comparisons",
            "sentiment": "positive"
        },
        {
            "feature": "possession breakdowns",
            "sentiment": "positive"
        },
        {
            "feature": "interface",
            "sentiment": "positive"
        },
        {
            "feature": "stats lag",
            "sentiment": "negative"
        }
    ],
    "pros": [
        "Ability to track live stats",
        "Fantastic shot charts",
        "Comparisons between players",
        "Detailed possession breakdowns",
        "Clean and easy-to-navigate interface"
    ],
    "cons": [
        "Stats sometimes lag behind actual game",
        "Lag can be frustrating when following along in real-time"
    ],
    "improvement_suggestions": [
        "Reduce the lag in stats updates"
    ],
    "categorize_feedback": [
        "bug report",
        "general feedback"
    ],
    "key_quotes": [
        "I love being able to track all the live stats during the game.",
        "The shot charts, player comparisons, and possession breakdowns are fantastic.",
        "The interface is clean and easy to navigate.",
        "I've noticed the stats sometimes lag behind the actual game by a few plays."
    ]
}
-------------------------------------

Review Details:
  Product Name: sports analytics application
  Mentioned Features: [{'feature': 'live stats tracking', 'sentiment': 'positive'}, {'feature': 'shot charts', 'sentiment': 'positive'}, {'feature': 'player comparisons', 'sentiment': 'positive'}, {'feature': 'possession breakdowns', 'sentiment': 'positive'}, {'feature': 'interface', 'sentiment': 'positive'}, {'feature': 'stats lag', 'sentiment': 'negative'}]
  Pros: ['Ability to track live stats', 'Fantastic shot charts', 'Comparisons between players', 'Detailed possession breakdowns', 'Clean and easy-to-navigate interface']
  Cons: ['Stats sometimes lag behind actual game', 'Lag can be frustrating when following along in real-time']
  Improvement Suggestions: ['Reduce the lag in stats updates']
  Categorize Feedback: ['bug report', 'general feedback']
  Key Quotes: ['I love being able to track all the live stats during the game.', 'The shot charts, player comparisons, and possession breakdowns are fantastic.', 'The interface is clean and easy to navigate.', "I've noticed the stats sometimes lag behind the actual game by a few plays."]

2025-03-15 16:34:00 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:34:00 - INFO - Starting review validation analysis

--- DEBUG: Raw API Response (Review Analysis) ---
{"summary":"The reviewer appreciates the ability to track live stats, along with the quality of visual features like shot charts and player comparisons. They also praise the clean interface. However, they report an issue with a lag in the stats updates during the game, which can be frustrating when trying to follow along in real-time.","priority_level":"high","recommended_actions":["Investigate and resolve the lag in live stats updates","Enhance data syncing capabilities for real-time accuracy"],"similar_reviews_pattern":true,"jira_ticket":{"ticket_id":"SP-12345","title":"Lag in Live Stats Updates","description":"Users are experiencing a lag in the live stats tracking functionality of the sports analytics application. The stats can lag behind actual gameplay by a few plays, which impacts real-time use. Investigate the cause of this delay and look for optimization opportunities to ensure that live stats are updated without noticeable lag.","status":"To Do","assignee":"Engineering Manager","reporter":"Product Manager","priority":"High","due_date":"2023-11-15"}}
--------------------------------------------------


--- DEBUG: Parsed Review Analysis ---
{
    "summary": "The reviewer appreciates the ability to track live stats, along with the quality of visual features like shot charts and player comparisons. They also praise the clean interface. However, they report an issue with a lag in the stats updates during the game, which can be frustrating when trying to follow along in real-time.",
    "priority_level": "high",
    "recommended_actions": [
        "Investigate and resolve the lag in live stats updates",
        "Enhance data syncing capabilities for real-time accuracy"
    ],
    "similar_reviews_pattern": true,
    "jira_ticket": {
        "ticket_id": "SP-12345",
        "title": "Lag in Live Stats Updates",
        "description": "Users are experiencing a lag in the live stats tracking functionality of the sports analytics application. The stats can lag behind actual gameplay by a few plays, which impacts real-time use. Investigate the cause of this delay and look for optimization opportunities to ensure that live stats are updated without noticeable lag.",
        "status": "To Do",
        "assignee": "Engineering Manager",
        "reporter": "Product Manager",
        "priority": "High",
        "due_date": "2023-11-15"
    }
}
--------------------------------------------------

Review Analysis and JIRA Ticket:
  Summary: The reviewer appreciates the ability to track live stats, along with the quality of visual features like shot charts and player comparisons. They also praise the clean interface. However, they report an issue with a lag in the stats updates during the game, which can be frustrating when trying to follow along in real-time.
  Priority Level: high
  Recommended Actions: ['Investigate and resolve the lag in live stats updates', 'Enhance data syncing capabilities for real-time accuracy']
  Similar Reviews Pattern: True
  JIRA Ticket:
    Ticket ID: SP-12345
    Title: Lag in Live Stats Updates
    Description: Users are experiencing a lag in the live stats tracking functionality of the sports analytics application. The stats can lag behind actual gameplay by a few plays, which impacts real-time use. Investigate the cause of this delay and look for optimization opportunities to ensure that live stats are updated without noticeable lag.
    Status: To Do
    Assignee: Engineering Manager
    Reporter: Product Manager
    Priority: High
    Due Date: 2023-11-15

-------------------------------------------

Processing review: rev_nba_23456
Title: Disappointed with the app's ticket purchase flow - crashed multiple times

2025-03-15 16:34:02 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:34:02 - INFO - Starting review details extraction

--- DEBUG: Raw API Response ---
{"raw_text":"I was excited to buy tickets for the upcoming game through the app. The seat selection and price filtering were good. Unfortunately, the app crashed three times during the checkout process. I had to restart my phone and re-enter my payment information each time. When I finally got through, the seats I originally selected were no longer available. Customer support has not responded to my emails. I'll stick to buying tickets through the website next time.","is_product_review":true,"product_category":"mobile application","overall_sentiment":"negative","confidence_score":0.95}
--------------------------------


--- DEBUG: Parsed Response ---
Raw Text: I was excited to buy tickets for the upcoming game through the app. The seat selection and price filtering were good. Unfortunately, the app crashed three times during the checkout process. I had to restart my phone and re-enter my payment information each time. When I finally got through, the seats I originally selected were no longer available. Customer support has not responded to my emails. I'll stick to buying tickets through the website next time.
Is Product Review: True
Product Category: mobile application
Overall Sentiment: negative
Confidence Score: 0.95
--------------------------------

Classification:
  Is Product Review: True
  Product Category: mobile application
  Overall Sentiment: negative
  Confidence Score: 0.95

2025-03-15 16:34:05 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:34:05 - INFO - Starting review analysis for actionable insights and JIRA ticket generation.

--- DEBUG: Raw Details API Response ---
{"product_name":"Ticket Purchase App","mentioned_features":[{"feature":"seat selection","sentiment":"positive"},{"feature":"price filtering","sentiment":"positive"},{"feature":"app crashing","sentiment":"negative"},{"feature":"customer support response","sentiment":"negative"}],"pros":["Good seat selection","Good price filtering"],"cons":["App crashed three times during checkout","Had to restart phone and re-enter payment information each time","Seats were no longer available after crash","No response from customer support"],"improvement_suggestions":["Fix app stability to prevent crashing","Improve customer support response times"],"categorize_feedback":["bug report","general feedback"],"key_quotes":["The app crashed three times during the checkout process.","Customer support has not responded to my emails."]}
----------------------------------------

product_name='Ticket Purchase App' mentioned_features=[{'feature': 'seat selection', 'sentiment': 'positive'}, {'feature': 'price filtering', 'sentiment': 'positive'}, {'feature': 'app crashing', 'sentiment': 'negative'}, {'feature': 'customer support response', 'sentiment': 'negative'}] pros=['Good seat selection', 'Good price filtering'] cons=['App crashed three times during checkout', 'Had to restart phone and re-enter payment information each time', 'Seats were no longer available after crash', 'No response from customer support'] improvement_suggestions=['Fix app stability to prevent crashing', 'Improve customer support response times'] categorize_feedback=['bug report', 'general feedback'] key_quotes=['The app crashed three times during the checkout process.', 'Customer support has not responded to my emails.']

--- DEBUG: Parsed Review Details ---
{
    "product_name": "Ticket Purchase App",
    "mentioned_features": [
        {
            "feature": "seat selection",
            "sentiment": "positive"
        },
        {
            "feature": "price filtering",
            "sentiment": "positive"
        },
        {
            "feature": "app crashing",
            "sentiment": "negative"
        },
        {
            "feature": "customer support response",
            "sentiment": "negative"
        }
    ],
    "pros": [
        "Good seat selection",
        "Good price filtering"
    ],
    "cons": [
        "App crashed three times during checkout",
        "Had to restart phone and re-enter payment information each time",
        "Seats were no longer available after crash",
        "No response from customer support"
    ],
    "improvement_suggestions": [
        "Fix app stability to prevent crashing",
        "Improve customer support response times"
    ],
    "categorize_feedback": [
        "bug report",
        "general feedback"
    ],
    "key_quotes": [
        "The app crashed three times during the checkout process.",
        "Customer support has not responded to my emails."
    ]
}
-------------------------------------

Review Details:
  Product Name: Ticket Purchase App
  Mentioned Features: [{'feature': 'seat selection', 'sentiment': 'positive'}, {'feature': 'price filtering', 'sentiment': 'positive'}, {'feature': 'app crashing', 'sentiment': 'negative'}, {'feature': 'customer support response', 'sentiment': 'negative'}]
  Pros: ['Good seat selection', 'Good price filtering']
  Cons: ['App crashed three times during checkout', 'Had to restart phone and re-enter payment information each time', 'Seats were no longer available after crash', 'No response from customer support']
  Improvement Suggestions: ['Fix app stability to prevent crashing', 'Improve customer support response times']
  Categorize Feedback: ['bug report', 'general feedback']
  Key Quotes: ['The app crashed three times during the checkout process.', 'Customer support has not responded to my emails.']

2025-03-15 16:34:07 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:34:07 - INFO - Starting review validation analysis

--- DEBUG: Raw API Response (Review Analysis) ---
{"summary":"The review highlights issues with app stability during the ticket checkout process and a lack of response from customer support, making the user resort to purchasing tickets via the website instead.","priority_level":"high","recommended_actions":["Fix app stability to prevent crashing during checkout","Enhance customer support response times to inquiries"],"similar_reviews_pattern":true,"jira_ticket":{"ticket_id":"TICKET-1234","title":"App Crashing During Checkout Process","description":"Users are experiencing multiple crashes during the checkout process. This has led to the loss of seat selections and requires users to re-enter payment information. Additionally, there are reports of customer support being unresponsive to inquiries. Please investigate the app's stability during checkout and improve customer support follow-up procedures.","status":"To Do","assignee":"Engineering Manager","reporter":"Product Manager","priority":"High","due_date":"2023-11-30"}}
--------------------------------------------------


--- DEBUG: Parsed Review Analysis ---
{
    "summary": "The review highlights issues with app stability during the ticket checkout process and a lack of response from customer support, making the user resort to purchasing tickets via the website instead.",
    "priority_level": "high",
    "recommended_actions": [
        "Fix app stability to prevent crashing during checkout",
        "Enhance customer support response times to inquiries"
    ],
    "similar_reviews_pattern": true,
    "jira_ticket": {
        "ticket_id": "TICKET-1234",
        "title": "App Crashing During Checkout Process",
        "description": "Users are experiencing multiple crashes during the checkout process. This has led to the loss of seat selections and requires users to re-enter payment information. Additionally, there are reports of customer support being unresponsive to inquiries. Please investigate the app's stability during checkout and improve customer support follow-up procedures.",
        "status": "To Do",
        "assignee": "Engineering Manager",
        "reporter": "Product Manager",
        "priority": "High",
        "due_date": "2023-11-30"
    }
}
--------------------------------------------------

Review Analysis and JIRA Ticket:
  Summary: The review highlights issues with app stability during the ticket checkout process and a lack of response from customer support, making the user resort to purchasing tickets via the website instead.
  Priority Level: high
  Recommended Actions: ['Fix app stability to prevent crashing during checkout', 'Enhance customer support response times to inquiries']
  Similar Reviews Pattern: True
  JIRA Ticket:
    Ticket ID: TICKET-1234
    Title: App Crashing During Checkout Process
    Description: Users are experiencing multiple crashes during the checkout process. This has led to the loss of seat selections and requires users to re-enter payment information. Additionally, there are reports of customer support being unresponsive to inquiries. Please investigate the app's stability during checkout and improve customer support follow-up procedures.
    Status: To Do
    Assignee: Engineering Manager
    Reporter: Product Manager
    Priority: High
    Due Date: 2023-11-30

-------------------------------------------

Processing review: rev_nba_22334
Title: Amazing Game!

2025-03-15 16:34:08 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:34:08 - INFO - Starting review validation analysis

--- DEBUG: Raw API Response ---
{"raw_text":"Just saw the game last night! What a thriller! That last-second shot was incredible! #GoGrizz #NBALive","is_product_review":false,"overall_sentiment":"positive","confidence_score":0.95,"product_category":""}
--------------------------------


--- DEBUG: Parsed Response ---
Raw Text: Just saw the game last night! What a thriller! That last-second shot was incredible! #GoGrizz #NBALive
Is Product Review: False
Product Category: 
Overall Sentiment: positive
Confidence Score: 0.95
--------------------------------

Classification:
  Is Product Review: False
  Product Category: 
  Overall Sentiment: positive
  Confidence Score: 0.95

The text is not a product review; skipping further analysis.
-------------------------------------------

Processing review: rev_nba_45678
Title: Highlighst are acting weird

2025-03-15 16:34:10 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:34:10 - INFO - Starting review details extraction

--- DEBUG: Raw API Response ---
{"raw_text":"Highlights for some reason take a while to load, do not automatically move onto next video. Sometimes restarting the app helps but not always consistent.","is_product_review":true,"product_category":"app/software","overall_sentiment":"negative","confidence_score":0.8}
--------------------------------


--- DEBUG: Parsed Response ---
Raw Text: Highlights for some reason take a while to load, do not automatically move onto next video. Sometimes restarting the app helps but not always consistent.
Is Product Review: True
Product Category: app/software
Overall Sentiment: negative
Confidence Score: 0.8
--------------------------------

Classification:
  Is Product Review: True
  Product Category: app/software
  Overall Sentiment: negative
  Confidence Score: 0.8

2025-03-15 16:34:12 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:34:14 - INFO - Starting review analysis for actionable insights and JIRA ticket generation.

--- DEBUG: Raw Details API Response ---
{"product_name":"Unnamed Video App","mentioned_features":[{"feature":"loading time for highlights","sentiment":"negative"},{"feature":"automatic transition to next video","sentiment":"negative"}],"pros":[],"cons":["Highlights take a while to load","Do not automatically move onto the next video","Inconsistent performance of restarting the app"],"improvement_suggestions":["Improve the loading time for highlights","Enable automatic transitions to the next video","Make the app restart process more reliable"],"categorize_feedback":["bug report","general feedback"],"key_quotes":["Highlights for some reason take a while to load","do not automatically move onto next video","Sometimes restarting the app helps but not always consistent"]}
----------------------------------------

product_name='Unnamed Video App' mentioned_features=[{'feature': 'loading time for highlights', 'sentiment': 'negative'}, {'feature': 'automatic transition to next video', 'sentiment': 'negative'}] pros=[] cons=['Highlights take a while to load', 'Do not automatically move onto the next video', 'Inconsistent performance of restarting the app'] improvement_suggestions=['Improve the loading time for highlights', 'Enable automatic transitions to the next video', 'Make the app restart process more reliable'] categorize_feedback=['bug report', 'general feedback'] key_quotes=['Highlights for some reason take a while to load', 'do not automatically move onto next video', 'Sometimes restarting the app helps but not always consistent']

--- DEBUG: Parsed Review Details ---
{
    "product_name": "Unnamed Video App",
    "mentioned_features": [
        {
            "feature": "loading time for highlights",
            "sentiment": "negative"
        },
        {
            "feature": "automatic transition to next video",
            "sentiment": "negative"
        }
    ],
    "pros": [],
    "cons": [
        "Highlights take a while to load",
        "Do not automatically move onto the next video",
        "Inconsistent performance of restarting the app"
    ],
    "improvement_suggestions": [
        "Improve the loading time for highlights",
        "Enable automatic transitions to the next video",
        "Make the app restart process more reliable"
    ],
    "categorize_feedback": [
        "bug report",
        "general feedback"
    ],
    "key_quotes": [
        "Highlights for some reason take a while to load",
        "do not automatically move onto next video",
        "Sometimes restarting the app helps but not always consistent"
    ]
}
-------------------------------------

Review Details:
  Product Name: Unnamed Video App
  Mentioned Features: [{'feature': 'loading time for highlights', 'sentiment': 'negative'}, {'feature': 'automatic transition to next video', 'sentiment': 'negative'}]
  Pros: []
  Cons: ['Highlights take a while to load', 'Do not automatically move onto the next video', 'Inconsistent performance of restarting the app']
  Improvement Suggestions: ['Improve the loading time for highlights', 'Enable automatic transitions to the next video', 'Make the app restart process more reliable']
  Categorize Feedback: ['bug report', 'general feedback']
  Key Quotes: ['Highlights for some reason take a while to load', 'do not automatically move onto next video', 'Sometimes restarting the app helps but not always consistent']

2025-03-15 16:34:16 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:34:16 - INFO - Starting review validation analysis

--- DEBUG: Raw API Response (Review Analysis) ---
{"summary":"The review highlights issues with loading times for highlights and the lack of automatic transitions to the next video, leading to an inconsistent user experience.","priority_level":"high","recommended_actions":["Improve the loading time for highlights","Enable automatic transitions to the next video","Make the app restart process more reliable"],"similar_reviews_pattern":true,"jira_ticket":{"ticket_id":"APP-1023","title":"Improve loading times and add automatic video transition","description":"Users have reported that highlights take a long time to load and the app does not automatically move to the next video. Furthermore, restarting the app only sometimes resolves these issues, indicating inconsistent performance. This requires urgent attention to enhance user experience.","status":"To Do","assignee":"Engineering Lead","reporter":"Product Manager","priority":"High","due_date":"2023-12-01"}}
--------------------------------------------------


--- DEBUG: Parsed Review Analysis ---
{
    "summary": "The review highlights issues with loading times for highlights and the lack of automatic transitions to the next video, leading to an inconsistent user experience.",
    "priority_level": "high",
    "recommended_actions": [
        "Improve the loading time for highlights",
        "Enable automatic transitions to the next video",
        "Make the app restart process more reliable"
    ],
    "similar_reviews_pattern": true,
    "jira_ticket": {
        "ticket_id": "APP-1023",
        "title": "Improve loading times and add automatic video transition",
        "description": "Users have reported that highlights take a long time to load and the app does not automatically move to the next video. Furthermore, restarting the app only sometimes resolves these issues, indicating inconsistent performance. This requires urgent attention to enhance user experience.",
        "status": "To Do",
        "assignee": "Engineering Lead",
        "reporter": "Product Manager",
        "priority": "High",
        "due_date": "2023-12-01"
    }
}
--------------------------------------------------

Review Analysis and JIRA Ticket:
  Summary: The review highlights issues with loading times for highlights and the lack of automatic transitions to the next video, leading to an inconsistent user experience.
  Priority Level: high
  Recommended Actions: ['Improve the loading time for highlights', 'Enable automatic transitions to the next video', 'Make the app restart process more reliable']
  Similar Reviews Pattern: True
  JIRA Ticket:
    Ticket ID: APP-1023
    Title: Improve loading times and add automatic video transition
    Description: Users have reported that highlights take a long time to load and the app does not automatically move to the next video. Furthermore, restarting the app only sometimes resolves these issues, indicating inconsistent performance. This requires urgent attention to enhance user experience.
    Status: To Do
    Assignee: Engineering Lead
    Reporter: Product Manager
    Priority: High
    Due Date: 2023-12-01

-------------------------------------------

Processing review: rev_nba_56789
Title: Excellent arena map feature - made my game day experience much better!

2025-03-15 16:34:19 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:34:19 - INFO - Starting review details extraction

--- DEBUG: Raw API Response ---
{"raw_text":"This feature was a game-changer! I used the arena map to find my seats, locate the nearest restrooms, and check out the concession stands. The ability to see menus and order food directly from the app was incredibly convenient. The map was easy to navigate and the directions were accurate. This made my game day experience much more enjoyable. I wish more sports apps had this feature!","is_product_review":true,"product_category":"mobile application","overall_sentiment":"positive","confidence_score":0.95}
--------------------------------


--- DEBUG: Parsed Response ---
Raw Text: This feature was a game-changer! I used the arena map to find my seats, locate the nearest restrooms, and check out the concession stands. The ability to see menus and order food directly from the app was incredibly convenient. The map was easy to navigate and the directions were accurate. This made my game day experience much more enjoyable. I wish more sports apps had this feature!
Is Product Review: True
Product Category: mobile application
Overall Sentiment: positive
Confidence Score: 0.95
--------------------------------

Classification:
  Is Product Review: True
  Product Category: mobile application
  Overall Sentiment: positive
  Confidence Score: 0.95

2025-03-15 16:34:21 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-03-15 16:34:21 - INFO - Starting review analysis for actionable insights and JIRA ticket generation.

--- DEBUG: Raw Details API Response ---
{"product_name":"Sports Event Mobile App","mentioned_features":[{"feature":"arena map","sentiment":"positive"},{"feature":"seat locator","sentiment":"positive"},{"feature":"nearest restrooms locator","sentiment":"positive"},{"feature":"concession stands","sentiment":"positive"},{"feature":"menus and food ordering","sentiment":"positive"},{"feature":"navigation","sentiment":"positive"},{"feature":"directions accuracy","sentiment":"positive"}],"pros":["Game-changing feature","Convenient food ordering","Easy to navigate map","Accurate directions","Enhanced game day experience"],"cons":[],"improvement_suggestions":["More sports apps should have this feature"],"categorize_feedback":["general feedback","feature enhancement"],"key_quotes":["This feature was a game-changer!","The ability to see menus and order food directly from the app was incredibly convenient.","This made my game day experience much more enjoyable."]}
----------------------------------------

product_name='Sports Event Mobile App' mentioned_features=[{'feature': 'arena map', 'sentiment': 'positive'}, {'feature': 'seat locator', 'sentiment': 'positive'}, {'feature': 'nearest restrooms locator', 'sentiment': 'positive'}, {'feature': 'concession stands', 'sentiment': 'positive'}, {'feature': 'menus and food ordering', 'sentiment': 'positive'}, {'feature': 'navigation', 'sentiment': 'positive'}, {'feature': 'directions accuracy', 'sentiment': 'positive'}] pros=['Game-changing feature', 'Convenient food ordering', 'Easy to navigate map', 'Accurate directions', 'Enhanced game day experience'] cons=[] improvement_suggestions=['More sports apps should have this feature'] categorize_feedback=['general feedback', 'feature enhancement'] key_quotes=['This feature was a game-changer!', 'The ability to see menus and order food directly from the app was incredibly convenient.', 'This made my game day experience much more enjoyable.']

--- DEBUG: Parsed Review Details ---
{
    "product_name": "Sports Event Mobile App",
    "mentioned_features": [
        {
            "feature": "arena map",
            "sentiment": "positive"
        },
        {
            "feature": "seat locator",
            "sentiment": "positive"
        },
        {
            "feature": "nearest restrooms locator",
            "sentiment": "positive"
        },
        {
            "feature": "concession stands",
            "sentiment": "positive"
        },
        {
            "feature": "menus and food ordering",
            "sentiment": "positive"
        },
        {
            "feature": "navigation",
            "sentiment": "positive"
        },
        {
            "feature": "directions accuracy",
            "sentiment": "positive"
        }
    ],
    "pros": [
        "Game-changing feature",
        "Convenient food ordering",
        "Easy to navigate map",
        "Accurate directions",
        "Enhanced game day experience"
    ],
    "cons": [],
    "improvement_suggestions": [
        "More sports apps should have this feature"
    ],
    "categorize_feedback": [
        "general feedback",
        "feature enhancement"
    ],
    "key_quotes": [
        "This feature was a game-changer!",
        "The ability to see menus and order food directly from the app was incredibly convenient.",
        "This made my game day experience much more enjoyable."
    ]
}
-------------------------------------

Review Details:
  Product Name: Sports Event Mobile App
  Mentioned Features: [{'feature': 'arena map', 'sentiment': 'positive'}, {'feature': 'seat locator', 'sentiment': 'positive'}, {'feature': 'nearest restrooms locator', 'sentiment': 'positive'}, {'feature': 'concession stands', 'sentiment': 'positive'}, {'feature': 'menus and food ordering', 'sentiment': 'positive'}, {'feature': 'navigation', 'sentiment': 'positive'}, {'feature': 'directions accuracy', 'sentiment': 'positive'}]
  Pros: ['Game-changing feature', 'Convenient food ordering', 'Easy to navigate map', 'Accurate directions', 'Enhanced game day experience']
  Cons: []
  Improvement Suggestions: ['More sports apps should have this feature']
  Categorize Feedback: ['general feedback', 'feature enhancement']
  Key Quotes: ['This feature was a game-changer!', 'The ability to see menus and order food directly from the app was incredibly convenient.', 'This made my game day experience much more enjoyable.']

2025-03-15 16:34:24 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"

--- DEBUG: Raw API Response (Review Analysis) ---
{"summary":"The review highlights the effectiveness and convenience of the arena map feature within the Sports Event Mobile App. The user praises its ability to help navigate the venue, find restrooms, and order food directly from the app, which significantly enhanced their game day experience.","priority_level":"low","recommended_actions":["Consider promoting this feature more prominently within the app and in marketing materials.","Explore partnerships with other sports apps to share this feature or standardized navigation options."],"similar_reviews_pattern":false,"jira_ticket":{"ticket_id":"PM-2378","title":"Enhance Visibility of Arena Map Feature in Marketing","description":"The arena map feature has received positive feedback from users as a game changer for navigating sports events. To leverage this, we should consider enhancing the visibility of this feature in our marketing efforts and possibly partnering with other sports apps to expand its reach. No bugs or immediate fixes are necessary, but further exploration of feature promotion is recommended.","status":"To Do","assignee":"Marketing Team Lead","reporter":"Product Manager","priority":"Low","due_date":"2024-01-15"}}
--------------------------------------------------


--- DEBUG: Parsed Review Analysis ---
{
    "summary": "The review highlights the effectiveness and convenience of the arena map feature within the Sports Event Mobile App. The user praises its ability to help navigate the venue, find restrooms, and order food directly from the app, which significantly enhanced their game day experience.",
    "priority_level": "low",
    "recommended_actions": [
        "Consider promoting this feature more prominently within the app and in marketing materials.",
        "Explore partnerships with other sports apps to share this feature or standardized navigation options."
    ],
    "similar_reviews_pattern": false,
    "jira_ticket": {
        "ticket_id": "PM-2378",
        "title": "Enhance Visibility of Arena Map Feature in Marketing",
        "description": "The arena map feature has received positive feedback from users as a game changer for navigating sports events. To leverage this, we should consider enhancing the visibility of this feature in our marketing efforts and possibly partnering with other sports apps to expand its reach. No bugs or immediate fixes are necessary, but further exploration of feature promotion is recommended.",
        "status": "To Do",
        "assignee": "Marketing Team Lead",
        "reporter": "Product Manager",
        "priority": "Low",
        "due_date": "2024-01-15"
    }
}
--------------------------------------------------

Review Analysis and JIRA Ticket:
  Summary: The review highlights the effectiveness and convenience of the arena map feature within the Sports Event Mobile App. The user praises its ability to help navigate the venue, find restrooms, and order food directly from the app, which significantly enhanced their game day experience.
  Priority Level: low
  Recommended Actions: ['Consider promoting this feature more prominently within the app and in marketing materials.', 'Explore partnerships with other sports apps to share this feature or standardized navigation options.']
  Similar Reviews Pattern: False
  JIRA Ticket:
    Ticket ID: PM-2378
    Title: Enhance Visibility of Arena Map Feature in Marketing
    Description: The arena map feature has received positive feedback from users as a game changer for navigating sports events. To leverage this, we should consider enhancing the visibility of this feature in our marketing efforts and possibly partnering with other sports apps to expand its reach. No bugs or immediate fixes are necessary, but further exploration of feature promotion is recommended.
    Status: To Do
    Assignee: Marketing Team Lead
    Reporter: Product Manager
    Priority: Low
    Due Date: 2024-01-15

-------------------------------------------

"""