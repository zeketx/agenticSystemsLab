import json
import logging
import os
from typing import List, Dict, Any, Optional, Literal
from uuid import uuid4
from pydantic import BaseModel, Field
from openai import OpenAI
from datetime import datetime, timedelta

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
# Define the data models
# --------------------------------------------------------------
class FeedbackRoute(BaseModel):
    """Router LLM call: Determine if feedback is operational or non-operational"""
    feedback_type: Literal["operational", "non_operational"] = Field(
        description="Type of feedback (operational requires action, non_operational does not)"
    )
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    description: str = Field(description="Cleaned description of the feedback")

class FeedbackClassification(BaseModel):
    """First LLM call: Classify operational feedback"""
    raw_text: str
    feedback_category: str  # e.g., Wi-Fi, Ticketing, Scoreboard, Concessions
    overall_sentiment: str  # positive, negative, mixed, neutral
    confidence_score: float
    feedback_source: str  # e.g., fan_survey, X_post, staff_report

class FeedbackDetails(BaseModel):
    """Second LLM call: Extract specific insights from operational feedback"""
    system_or_area: str  # e.g., Arena Wi-Fi, Ticketing Platform
    mentioned_components: List[Dict[str, str]]  # [{"component": "Wi-Fi speed", "sentiment": "negative"}]
    pros: List[str]
    cons: List[str]
    improvement_suggestions: List[str]
    categorize_feedback: List[str]  # e.g., system outage, user experience issue
    key_quotes: List[str]

class JiraTicket(BaseModel):
    """Third LLM call: Model for JIRA ticket"""
    ticket_id: str
    title: str
    description: str
    status: str
    assignee: str  # e.g., IT Lead, Arena Ops Manager
    reporter: str
    priority: str
    due_date: str  # YYYY-MM-DD
    affected_system: str

class FeedbackAnalysis(BaseModel):
    """Third LLM call: Generate actionable insights and JIRA ticket"""
    success: bool = Field(description="Whether the analysis was successful")
    message: str = Field(description="User-friendly response message")
    sentiment_score: Optional[float] = Field(description="Sentiment score from 0.0 to 1.0")
    summary: Optional[str] = Field(description="Summary of the feedback")
    priority_level: Optional[str] = Field(description="Priority: high, medium, low")
    recommended_actions: Optional[List[str]] = Field(description="Actions to address feedback")
    similar_incidents_pattern: Optional[bool] = Field(description="Matches other incidents")
    jira_ticket: Optional[JiraTicket] = Field(description="JIRA ticket details")
    classification: Optional[FeedbackClassification] = Field(description="Feedback classification details")
    details: Optional[FeedbackDetails] = Field(description="Detailed feedback insights")

# --------------------------------------------------------------
# Load feedback data
# --------------------------------------------------------------
def load_feedback_data(file_path: str = "reviewITData.json") -> List[Dict[str, Any]]:
    """Load feedback data from a local JSON file"""
    try:
        with open(file_path, "r") as f:
            feedback = json.load(f)
        return feedback
    except Exception as e:
        logger.error(f"Error loading feedback data: {e}")
        return []

# --------------------------------------------------------------
# Set dynamic due date based on priority
# --------------------------------------------------------------
def set_due_date(priority: str, event_date: str) -> str:
    """Set JIRA ticket due date based on priority"""
    try:
        base_date = datetime.strptime(event_date, "%Y-%m-%d")
        days = {"high": 3, "medium": 7, "low": 14}.get(priority.lower(), 7)
        return (base_date + timedelta(days=days)).strftime("%Y-%m-%d")
    except ValueError:
        # Fallback to 7 days from today if event_date is invalid
        return (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

# --------------------------------------------------------------
# Routing and processing functions
# --------------------------------------------------------------
def route_feedback(feedback_text: str, feedback_source: str) -> FeedbackRoute:
    """Router LLM call to determine if feedback is operational or non-operational"""
    logger.info("Routing feedback")

    prompt = (
        f"Analyze the following text: '{feedback_text}' from source '{feedback_source}'.\n"
        "Determine if it is operational feedback related to IT systems or arena operations (e.g., Wi-Fi, ticketing, scoreboards, concessions) "
        "that requires action, or non-operational feedback (e.g., general comments, non-actionable) that does not.\n"
        "Return a JSON object with:\n"
        "- feedback_type: 'operational' or 'non_operational'.\n"
        "- confidence_score: Confidence in the classification (0.0 to 1.0).\n"
        "- description: A cleaned version of the feedback text."
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Classify feedback as operational or non-operational."},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "feedback_route",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "feedback_type": {"type": "string", "enum": ["operational", "non_operational"]},
                            "confidence_score": {"type": "number"},
                            "description": {"type": "string"},
                        },
                        "required": ["feedback_type", "confidence_score", "description"],
                        "additionalProperties": False,
                    },
                },
            },
        )

        structured_response = completion.choices[0].message.content
        result = FeedbackRoute.model_validate_json(structured_response)
        logger.info(f"Feedback routed as: {result.feedback_type} with confidence: {result.confidence_score}")
        return result

    except Exception as e:
        logger.error(f"Error during feedback routing: {e}", exc_info=True)
        return FeedbackRoute(feedback_type="non_operational", confidence_score=0.0, description=feedback_text)

def validate_operational_feedback(feedback_text: str, feedback_source: str) -> Optional[FeedbackClassification]:
    """Classify operational feedback"""
    logger.info("Classifying operational feedback")

    prompt = (
        f"Analyze the operational feedback: '{feedback_text}' from source '{feedback_source}'.\n"
        "Return a JSON object with:\n"
        "- raw_text: The original text.\n"
        "- feedback_category: The category (e.g., Wi-Fi, Ticketing, Scoreboard, Concessions, or other relevant categories).\n"
        "- overall_sentiment: Sentiment (positive, negative, mixed, neutral).\n"
        "- confidence_score: Confidence in the classification (0.0 to 1.0).\n"
        "- feedback_source: Source of the feedback."
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Classify operational feedback for IT or arena operations."},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "feedback_classification",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "raw_text": {"type": "string"},
                            "feedback_category": {"type": "string"},
                            "overall_sentiment": {"type": "string", "enum": ["positive", "negative", "mixed", "neutral"]},
                            "confidence_score": {"type": "number"},
                            "feedback_source": {"type": "string"},
                        },
                        "required": ["raw_text", "feedback_category", "overall_sentiment", "confidence_score", "feedback_source"],
                        "additionalProperties": False,
                    },
                },
            },
        )

        structured_response = completion.choices[0].message.content
        parsed_response = FeedbackClassification.model_validate_json(structured_response)
        logger.info(f"Feedback classified: {parsed_response.feedback_category}, Sentiment: {parsed_response.overall_sentiment}")
        return parsed_response

    except Exception as e:
        logger.error(f"Error during feedback classification: {e}", exc_info=True)
        return None

def extract_feedback_details(feedback_text: str, classification: FeedbackClassification) -> Optional[FeedbackDetails]:
    """Extract specific insights from operational feedback"""
    logger.info("Extracting feedback details")

    prompt = (
        f"Given the feedback: '{feedback_text}',\n"
        f"classified as {classification.feedback_category} feedback with {classification.overall_sentiment} sentiment,\n"
        "extract the following details in JSON format:\n"
        "- system_or_area: The system or area affected (e.g., Arena Wi-Fi, Ticketing Platform).\n"
        "- mentioned_components: List of components mentioned with their sentiment (e.g., [{'component': 'Wi-Fi speed', 'sentiment': 'negative'}]).\n"
        "- pros: Positive aspects mentioned.\n"
        "- cons: Negative aspects mentioned.\n"
        "- improvement_suggestions: Suggestions for improvement.\n"
        "- categorize_feedback: Categories (e.g., system outage, user experience issue, hardware failure, process improvement, or others as appropriate).\n"
        "- key_quotes: Important excerpts."
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Extract detailed insights from operational feedback."},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "feedback_details",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "system_or_area": {"type": "string"},
                            "mentioned_components": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "component": {"type": "string"},
                                        "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
                                    },
                                    "required": ["component", "sentiment"],
                                    "additionalProperties": False,
                                },
                            },
                            "pros": {"type": "array", "items": {"type": "string"}},
                            "cons": {"type": "array", "items": {"type": "string"}},
                            "improvement_suggestions": {"type": "array", "items": {"type": "string"}},
                            "categorize_feedback": {"type": "array", "items": {"type": "string"}},
                            "key_quotes": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": [
                            "system_or_area",
                            "mentioned_components",
                            "pros",
                            "cons",
                            "improvement_suggestions",
                            "categorize_feedback",
                            "key_quotes",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
        )

        structured_response = completion.choices[0].message.content
        details = FeedbackDetails.model_validate_json(structured_response)
        logger.info(f"Feedback details extracted for: {details.system_or_area}")
        return details

    except Exception as e:
        logger.error(f"Error during feedback details extraction: {e}", exc_info=True)
        return None

def generate_feedback_analysis(
    feedback_text: str, classification: FeedbackClassification, details: FeedbackDetails, event_date: str
) -> FeedbackAnalysis:
    """Generate actionable insights and a JIRA ticket using a sentiment score"""
    logger.info("Generating feedback analysis and JIRA ticket")

    ASSIGNEE_MAPPING = {
        "Wi-Fi": "IT Lead",
        "Ticketing": "IT Lead",
        "Scoreboard": "Arena Ops Manager",
        "Concessions": "Arena Ops Manager",
    }
    assignee = ASSIGNEE_MAPPING.get(classification.feedback_category, "IT Lead")

    prompt = (
        f"Feedback Text: {feedback_text}\n"
        f"Classification: Category '{classification.feedback_category}', Sentiment '{classification.overall_sentiment}', Source '{classification.feedback_source}'.\n"
        f"Detailed Insights: {details.model_dump_json()}\n\n"
        "As an IT or arena operations manager, analyze this operational feedback for an NBA team. Generate actionable insights and a JIRA ticket. "
        "Consider the feedback's urgency, impact on fan experience, operational disruption, and source reliability. "
        "Return a JSON object with:\n"
        "- sentiment_score: A score from 0.0 to 1.0, where 0.0 indicates highly negative/urgent feedback (e.g., system failures, major disruptions) "
        "and 1.0 indicates positive/non-urgent feedback (e.g., general praise).\n"
        "- priority_level: Priority based on the sentiment score and context: 'high' (0.0–0.3, critical issues), "
        "'medium' (0.31–0.6, moderate issues), or 'low' (0.61–1.0, minor or positive feedback).\n"
        "- summary: A brief summary of the feedback.\n"
        "- recommended_actions: List of actions to address the feedback.\n"
        "- similar_incidents_pattern: Boolean indicating if this matches other incidents.\n"
        "- jira_ticket: A JIRA ticket with:\n"
        "  - ticket_id: Unique identifier (e.g., CATEGORY-YYYY-NNN).\n"
        "  - title: Concise title.\n"
        "  - description: Detailed explanation.\n"
        "  - status: 'To Do'.\n"
        "  - assignee: IT Lead or Arena Ops Manager based on category.\n"
        "  - reporter: 'Ops Manager'.\n"
        "  - priority: High, Medium, or Low (match priority_level).\n"
        "  - due_date: YYYY-MM-DD, set based on priority (3 days for high, 7 for medium, 14 for low).\n"
        "  - affected_system: The system affected."
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Generate insights and JIRA ticket for operational feedback."},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "feedback_analysis",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "sentiment_score": {"type": "number"},
                            "priority_level": {"type": "string", "enum": ["high", "medium", "low"]},
                            "summary": {"type": "string"},
                            "recommended_actions": {"type": "array", "items": {"type": "string"}},
                            "similar_incidents_pattern": {"type": "boolean"},
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
                                    "due_date": {"type": "string"},
                                    "affected_system": {"type": "string"},
                                },
                                "required": [
                                    "ticket_id",
                                    "title",
                                    "description",
                                    "status",
                                    "assignee",
                                    "reporter",
                                    "priority",
                                    "due_date",
                                    "affected_system",
                                ],
                                "additionalProperties": False,
                            },
                        },
                        "required": [
                            "sentiment_score",
                            "priority_level",
                            "summary",
                            "recommended_actions",
                            "similar_incidents_pattern",
                            "jira_ticket",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
        )

        structured_response = completion.choices[0].message.content
        analysis_data = json.loads(structured_response)
        # Override due_date using set_due_date for consistency
        analysis_data["jira_ticket"]["due_date"] = set_due_date(analysis_data["priority_level"], event_date)
        analysis_data["jira_ticket"]["assignee"] = assignee
        analysis = FeedbackAnalysis(
            success=True,
            message=f"Processed operational feedback for {classification.feedback_category}",
            sentiment_score=analysis_data["sentiment_score"],
            summary=analysis_data["summary"],
            priority_level=analysis_data["priority_level"],
            recommended_actions=analysis_data["recommended_actions"],
            similar_incidents_pattern=analysis_data["similar_incidents_pattern"],
            jira_ticket=JiraTicket(**analysis_data["jira_ticket"]),
            classification=classification,
            details=details,
        )
        logger.info(f"Feedback analysis generated: {analysis.summary}")
        return analysis

    except Exception as e:
        logger.error(f"Error during feedback analysis: {e}", exc_info=True)
        return FeedbackAnalysis(
            success=False,
            message="Failed to generate feedback analysis",
            sentiment_score=None,
            summary=None,
            priority_level=None,
            recommended_actions=None,
            similar_incidents_pattern=None,
            jira_ticket=None,
            classification=None,
            details=None,
        )

def handle_operational_feedback(feedback: Dict) -> FeedbackAnalysis:
    """Handle operational feedback through classification, details, and analysis"""
    logger.info(f"Processing operational feedback: {feedback['id']}")

    # Step 1: Classify feedback
    classification = validate_operational_feedback(feedback["feedback_text"], feedback["source"])
    if not classification:
        return FeedbackAnalysis(
            success=False,
            message="Feedback classification failed",
            sentiment_score=None,
            summary=None,
            priority_level=None,
            recommended_actions=None,
            similar_incidents_pattern=None,
            jira_ticket=None,
            classification=None,
            details=None,
        )

    # Step 2: Extract details
    details = extract_feedback_details(feedback["feedback_text"], classification)
    if not details:
        return FeedbackAnalysis(
            success=False,
            message="Failed to extract feedback details",
            sentiment_score=None,
            summary=None,
            priority_level=None,
            recommended_actions=None,
            similar_incidents_pattern=None,
            jira_ticket=None,
            classification=classification,
            details=None,
        )

    # Step 3: Generate analysis and JIRA ticket
    return generate_feedback_analysis(feedback["feedback_text"], classification, details, feedback["event_date"])

def handle_non_operational_feedback(feedback: Dict) -> FeedbackAnalysis:
    """Handle non-operational feedback"""
    logger.info(f"Processing non-operational feedback: {feedback['id']}")
    message = "Feedback is non-operational and does not require further action"
    if "loved" in feedback["feedback_text"].lower():
        message += " (positive comment noted)"
    return FeedbackAnalysis(
        success=True,
        message=message,
        sentiment_score=None,
        summary=None,
        priority_level=None,
        recommended_actions=None,
        similar_incidents_pattern=None,
        jira_ticket=None,
        classification=None,
        details=None,
    )

def process_feedback(feedback: Dict) -> FeedbackAnalysis:
    """Main function implementing the routing workflow"""
    logger.info(f"Processing feedback: {feedback['id']}")

    # Route the feedback
    route_result = route_feedback(feedback["feedback_text"], feedback["source"])

    # Check confidence threshold
    if route_result.confidence_score < 0.7:
        logger.warning(f"Low confidence score: {route_result.confidence_score}")
        return FeedbackAnalysis(
            success=False,
            message="Feedback classification confidence too low",
            sentiment_score=None,
            summary=None,
            priority_level=None,
            recommended_actions=None,
            similar_incidents_pattern=None,
            jira_ticket=None,
            classification=None,
            details=None,
        )

    # Route to appropriate handler
    if route_result.feedback_type == "operational":
        return handle_operational_feedback(feedback)
    else:
        return handle_non_operational_feedback(feedback)

# --------------------------------------------------------------
# Run the pipeline
# --------------------------------------------------------------
def run_full_feedback_analysis_pipeline():
    """Run the full feedback analysis pipeline"""
    feedback_list = load_feedback_data()

    for feedback in feedback_list:
        print(f"\nProcessing feedback: {feedback['id']}")
        print(f"Title: {feedback['title']}\n")

        result = process_feedback(feedback)
        print(f"Response: {result.message}")

        if result.success and result.jira_ticket:
            print("Classification:")
            print(f"  Feedback Category: {result.classification.feedback_category}")
            print(f"  Overall Sentiment: {result.classification.overall_sentiment}")
            print(f"  Confidence Score: {result.classification.confidence_score}")
            print(f"  Feedback Source: {result.classification.feedback_source}\n")

            print("Feedback Details:")
            print(f"  System/Area: {result.details.system_or_area}")
            print(f"  Mentioned Components: {result.details.mentioned_components}")
            print(f"  Pros: {result.details.pros}")
            print(f"  Cons: {result.details.cons}")
            print(f"  Improvement Suggestions: {result.details.improvement_suggestions}")
            print(f"  Categorize Feedback: {result.details.categorize_feedback}")
            print(f"  Key Quotes: {result.details.key_quotes}\n")

            print("Feedback Analysis and JIRA Ticket:")
            print(f"  Sentiment Score: {result.sentiment_score}")
            print(f"  Summary: {result.summary}")
            print(f"  Priority Level: {result.priority_level}")
            print(f"  Recommended Actions: {result.recommended_actions}")
            print(f"  Similar Incidents Pattern: {result.similar_incidents_pattern}")
            print("  JIRA Ticket:")
            print(f"    Ticket ID: {result.jira_ticket.ticket_id}")
            print(f"    Title: {result.jira_ticket.title}")
            print(f"    Description: {result.jira_ticket.description}")
            print(f"    Status: {result.jira_ticket.status}")
            print(f"    Assignee: {result.jira_ticket.assignee}")
            print(f"    Reporter: {result.jira_ticket.reporter}")
            print(f"    Priority: {result.jira_ticket.priority}")
            print(f"    Due Date: {result.jira_ticket.due_date}")
            print(f"    Affected System: {result.jira_ticket.affected_system}")

        print("-------------------------------------------")

if __name__ == "__main__":
    run_full_feedback_analysis_pipeline()



""""
Example output

Processing feedback: 001
Title: Wi-Fi Issues in Section 101

2025-05-10 14:44:54 - INFO - Processing feedback: 001
2025-05-10 14:44:54 - INFO - Routing feedback
2025-05-10 14:44:55 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:44:55 - INFO - Feedback routed as: operational with confidence: 0.95
2025-05-10 14:44:55 - INFO - Processing operational feedback: 001
2025-05-10 14:44:55 - INFO - Classifying operational feedback
2025-05-10 14:44:57 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:44:57 - INFO - Feedback classified: Wi-Fi, Sentiment: negative
2025-05-10 14:44:57 - INFO - Extracting feedback details
2025-05-10 14:44:59 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:44:59 - INFO - Feedback details extracted for: Arena Wi-Fi
2025-05-10 14:44:59 - INFO - Generating feedback analysis and JIRA ticket
2025-05-10 14:45:02 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:02 - INFO - Feedback analysis generated: Wi-Fi reliability during the game was poor, impacting app usage for ordering food.
Response: Processed operational feedback for Wi-Fi
Classification:
  Feedback Category: Wi-Fi
  Overall Sentiment: negative
  Confidence Score: 0.95
  Feedback Source: fan_survey

Feedback Details:
  System/Area: Arena Wi-Fi
  Mentioned Components: [{'component': 'Wi-Fi reliability', 'sentiment': 'negative'}]
  Pros: []
  Cons: ['Wi-Fi was spotty', 'Could barely use the app to order food']
  Improvement Suggestions: ['Improve Wi-Fi reliability during events', 'Increase bandwidth for better app usage']
  Categorize Feedback: ['user experience issue']
  Key Quotes: ['Wi-Fi was spotty during the game', 'Could barely use the app to order food']

Feedback Analysis and JIRA Ticket:
  Sentiment Score: 0.2
  Summary: Wi-Fi reliability during the game was poor, impacting app usage for ordering food.
  Priority Level: high
  Recommended Actions: ['Enhance Wi-Fi infrastructure for better connectivity during events', 'Increase overall bandwidth to support user demand for app usage', 'Install additional access points in key areas to mitigate issues']
  Similar Incidents Pattern: True
  JIRA Ticket:
    Ticket ID: WIFI-2025-001
    Title: Improve Wi-Fi Reliability During Events
    Description: Feedback indicates that Wi-Fi was spotty during the game on 2025-05-01, severely affecting fans' ability to use the app for food orders. Immediate actions are needed to enhance Wi-Fi infrastructure and increase bandwidth to prevent future occurrences and ensure a better fan experience.
    Status: To Do
    Assignee: IT Lead
    Reporter: Ops Manager
    Priority: High
    Due Date: 2025-05-04
    Affected System: Arena Wi-Fi
-------------------------------------------

Processing feedback: 002
Title: Scoreboard Glitch

2025-05-10 14:45:02 - INFO - Processing feedback: 002
2025-05-10 14:45:02 - INFO - Routing feedback
2025-05-10 14:45:02 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:02 - INFO - Feedback routed as: operational with confidence: 0.95
2025-05-10 14:45:02 - INFO - Processing operational feedback: 002
2025-05-10 14:45:02 - INFO - Classifying operational feedback
2025-05-10 14:45:04 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:04 - INFO - Feedback classified: Scoreboard, Sentiment: negative
2025-05-10 14:45:04 - INFO - Extracting feedback details
2025-05-10 14:45:06 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:06 - INFO - Feedback details extracted for: Scoreboard
2025-05-10 14:45:06 - INFO - Generating feedback analysis and JIRA ticket
2025-05-10 14:45:09 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:09 - INFO - Feedback analysis generated: Scoreboard malfunction during the third quarter caused confusion among fans.
Response: Processed operational feedback for Scoreboard
Classification:
  Feedback Category: Scoreboard
  Overall Sentiment: negative
  Confidence Score: 0.95
  Feedback Source: staff_report

Feedback Details:
  System/Area: Scoreboard
  Mentioned Components: [{'component': 'Scoreboard performance', 'sentiment': 'negative'}]
  Pros: []
  Cons: ['The scoreboard froze during the third quarter.', 'It was confusing for fans.']
  Improvement Suggestions: []
  Categorize Feedback: ['system outage', 'user experience issue']
  Key Quotes: ['The scoreboard froze during the third quarter.', 'It was confusing for fans.']

Feedback Analysis and JIRA Ticket:
  Sentiment Score: 0.1
  Summary: Scoreboard malfunction during the third quarter caused confusion among fans.
  Priority Level: high
  Recommended Actions: ['Investigate the cause of the scoreboard freezing issue.', 'Enhance the monitoring systems for real-time performance tracking.', 'Create a contingency plan for scoreboard failures.']
  Similar Incidents Pattern: False
  JIRA Ticket:
    Ticket ID: SCOREBOARD-2023-001
    Title: Scoreboard Freezing Issue
    Description: During the third quarter of the game, the scoreboard froze, leading to confusion among fans. This incident needs immediate investigation and resolution to ensure smooth operation in future games.
    Status: To Do
    Assignee: Arena Ops Manager
    Reporter: Ops Manager
    Priority: High
    Due Date: 2025-05-04
    Affected System: Scoreboard
-------------------------------------------

Processing feedback: 003
Title: Ticketing App Crash

2025-05-10 14:45:09 - INFO - Processing feedback: 003
2025-05-10 14:45:09 - INFO - Routing feedback
2025-05-10 14:45:09 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:09 - INFO - Feedback routed as: operational with confidence: 0.95
2025-05-10 14:45:09 - INFO - Processing operational feedback: 003
2025-05-10 14:45:09 - INFO - Classifying operational feedback
2025-05-10 14:45:11 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:11 - INFO - Feedback classified: Ticketing, Sentiment: negative
2025-05-10 14:45:11 - INFO - Extracting feedback details
2025-05-10 14:45:13 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:13 - INFO - Feedback details extracted for: Ticketing Platform
2025-05-10 14:45:13 - INFO - Generating feedback analysis and JIRA ticket
2025-05-10 14:45:16 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:16 - INFO - Feedback analysis generated: The ticketing app crashed during the ticket purchase process, causing significant frustration among users.
Response: Processed operational feedback for Ticketing
Classification:
  Feedback Category: Ticketing
  Overall Sentiment: negative
  Confidence Score: 0.95
  Feedback Source: X_post

Feedback Details:
  System/Area: Ticketing Platform
  Mentioned Components: [{'component': 'Ticket purchase process', 'sentiment': 'negative'}, {'component': 'App stability', 'sentiment': 'negative'}]
  Pros: []
  Cons: ['The ticketing app crashed.', 'Frustration with the experience.']
  Improvement Suggestions: ['Stabilize the app during high traffic periods.', 'Enhance the ticket purchase process to prevent crashes.']
  Categorize Feedback: ['user experience issue', 'system outage']
  Key Quotes: ['The ticketing app crashed when I tried to buy tickets.', 'Very frustrating!']

Feedback Analysis and JIRA Ticket:
  Sentiment Score: 0.1
  Summary: The ticketing app crashed during the ticket purchase process, causing significant frustration among users.
  Priority Level: high
  Recommended Actions: ['Stabilize the app during high traffic periods.', 'Implement fallback mechanisms to improve app resilience.', 'Map out ticketing process for potential points of failure.']
  Similar Incidents Pattern: True
  JIRA Ticket:
    Ticket ID: TICKETING-2023-002
    Title: Ticketing App Crash During Purchase
    Description: The ticketing app crashed when users attempted to buy tickets for the next game. This resulted in a negative user experience noted by several users stating their frustration at not being able to complete their purchases. Immediate investigation and resolution are required to improve stability.
    Status: To Do
    Assignee: IT Lead
    Reporter: Ops Manager
    Priority: High
    Due Date: 2025-05-05
    Affected System: Ticketing Application
-------------------------------------------

Processing feedback: 004
Title: POS System Failure at Concessions

2025-05-10 14:45:16 - INFO - Processing feedback: 004
2025-05-10 14:45:16 - INFO - Routing feedback
2025-05-10 14:45:17 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:17 - INFO - Feedback routed as: operational with confidence: 0.95
2025-05-10 14:45:17 - INFO - Processing operational feedback: 004
2025-05-10 14:45:17 - INFO - Classifying operational feedback
2025-05-10 14:45:18 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:18 - INFO - Feedback classified: Concessions, Sentiment: negative
2025-05-10 14:45:18 - INFO - Extracting feedback details
2025-05-10 14:45:19 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:19 - INFO - Feedback details extracted for: POS system at the main concessions stand
2025-05-10 14:45:19 - INFO - Generating feedback analysis and JIRA ticket
2025-05-10 14:45:22 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:22 - INFO - Feedback analysis generated: The POS system crashed during a critical fan engagement moment, leading to operational chaos.
Response: Processed operational feedback for Concessions
Classification:
  Feedback Category: Concessions
  Overall Sentiment: negative
  Confidence Score: 0.95
  Feedback Source: staff_report

Feedback Details:
  System/Area: POS system at the main concessions stand
  Mentioned Components: [{'component': 'POS system', 'sentiment': 'negative'}]
  Pros: []
  Cons: ['POS system crashed during halftime', 'Caused long lines', 'Cash-only chaos during high-demand period']
  Improvement Suggestions: ['Needs immediate fix before next game']
  Categorize Feedback: ['system outage', 'user experience issue']
  Key Quotes: ['The POS system at the main concessions stand crashed during halftime', 'Needs immediate fix before next game!']

Feedback Analysis and JIRA Ticket:
  Sentiment Score: 0.1
  Summary: The POS system crashed during a critical fan engagement moment, leading to operational chaos.
  Priority Level: high
  Recommended Actions: ['Conduct immediate diagnostics on the POS system.', 'Implement a temporary cash-handling solution for the next game.', 'Schedule system updates and backups before the next event.', 'Plan for additional staff at concessions peak times.']
  Similar Incidents Pattern: True
  JIRA Ticket:
    Ticket ID: CONCESSIONS-2025-001
    Title: Urgent: POS System Crash at Main Concessions Stand
    Description: The POS system at the main concessions stand experienced a failure during halftime on 2025-05-03, causing significant delays and operational chaos. Immediate attention is required to address the root cause and avoid repeat incidents in future games.
    Status: To Do
    Assignee: Arena Ops Manager
    Reporter: Ops Manager
    Priority: High
    Due Date: 2025-05-06
    Affected System: POS system
-------------------------------------------

Processing feedback: 005
Title: General Comment on Arena Atmosphere

2025-05-10 14:45:22 - INFO - Processing feedback: 005
2025-05-10 14:45:22 - INFO - Routing feedback
2025-05-10 14:45:23 - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
2025-05-10 14:45:23 - INFO - Feedback routed as: non_operational with confidence: 0.95
2025-05-10 14:45:23 - INFO - Processing non-operational feedback: 005
Response: Feedback is non-operational and does not require further action (positive comment noted)
"""
