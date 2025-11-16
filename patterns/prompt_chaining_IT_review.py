import json
import logging
import os
import sys
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from openai import OpenAI
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# -----------------------------------------------------------
# Configure logging for tracking script execution
# All logs output to stdout for visibility in both CLI and API modes
# -----------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client with API key from environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4o-mini-2024-07-18"  # Specify the LLM model for feedback analysis

# -----------------------------------------------------------
# Define the data models for each stage of feedback processing
# -----------------------------------------------------------
class FeedbackRoute(BaseModel):
    feedback_type: Literal["operational", "non_operational"]  # Type of feedback (actionable or not)
    confidence_score: float  # Confidence in classification (0.0 to 1.0)
    description: str  # Cleaned version of feedback text

class FeedbackClassification(BaseModel):
    raw_text: str  # Original feedback text
    feedback_category: str  # Primary category (e.g., Wi-Fi, Mobile App)
    overall_sentiment: str  # Sentiment (positive, negative, mixed, neutral)
    confidence_score: float  # Confidence in classification (0.0 to 1.0)
    feedback_source: str  # Source of feedback (e.g., fan_survey, X_post)

class FeedbackDetails(BaseModel):
    system_or_area: str  # Primary affected system (e.g., Arena Wi-Fi)
    mentioned_components: List[Dict[str, str]]  # Components and their sentiments
    pros: List[str]  # Positive aspects mentioned
    cons: List[str]  # Negative aspects mentioned
    improvement_suggestions: List[str]  # Suggested actions (explicit or inferred)
    categorize_feedback: List[str]  # Feedback categories (e.g., system outage)
    key_quotes: List[str]  # Important excerpts from feedback

class JiraTicket(BaseModel):
    ticket_id: str  # Unique ticket identifier (e.g., WI-FI-2025-001)
    title: str  # Concise ticket title
    description: str  # Detailed ticket explanation
    status: str  # Ticket status (e.g., To Do)
    assignee: str  # Assigned role (e.g., Product Manager)
    reporter: str  # Reporter of the ticket (e.g., Ops Manager)
    priority: str  # Priority level (High, Medium, Low)
    due_date: str  # Due date in YYYY-MM-DD format
    affected_system: str  # Affected system (e.g., Ticketing App)

class FeedbackAnalysis(BaseModel):
    success: bool  # Whether processing was successful
    message: str  # Processing result message
    sentiment_score: Optional[float]  # Sentiment score (0.0 to 1.0)
    summary: Optional[str]  # Brief feedback summary
    priority_level: Optional[str]  # Priority level (high, medium, low)
    recommended_actions: Optional[List[str]]  # Actions to address feedback
    similar_incidents_pattern: Optional[bool]  # Indicates recurring issues
    jira_ticket: Optional[JiraTicket]  # Generated JIRA ticket
    classification: Optional[FeedbackClassification]  # Feedback classification
    details: Optional[FeedbackDetails]  # Detailed feedback insights
    team: Optional[str]  # Assigned team (e.g., Product Team)

# -----------------------------------------------------------
# API Request/Response Models
# Simple, clean models for HTTP communication
# -----------------------------------------------------------
class FeedbackRequest(BaseModel):
    """Request model for analyzing feedback via API"""
    feedback_text: str  # The feedback text to analyze
    source: str = "api"  # Source of the feedback (defaults to 'api')
    event_date: str = datetime.now().strftime("%Y-%m-%d")  # Event date (defaults to today)
    feedback_id: Optional[str] = None  # Optional identifier for tracking

class FeedbackResponse(BaseModel):
    """Response model returning analysis results"""
    success: bool  # Whether analysis succeeded
    message: str  # Human-readable status message
    analysis: Optional[FeedbackAnalysis] = None  # Full analysis details if successful

# -----------------------------------------------------------
# Initialize FastAPI application
# Clean, elegant API for sentiment analysis
# -----------------------------------------------------------
app = FastAPI(
    title="Operational Feedback Analysis API",
    description="AI-powered sentiment analysis and JIRA ticket generation for operational feedback",
    version="1.0.0",
)

# -----------------------------------------------------------
# Load feedback data from JSON file
# -----------------------------------------------------------
def load_feedback_data(file_path: str = "reviewITData.json") -> List[Dict[str, Any]]:
    """
    Loads feedback data from a JSON file into a list of dictionaries.

    Args:
        file_path (str): Path to the JSON file (default: reviewITData.json).

    Returns:
        List[Dict[str, Any]]: List of feedback entries, or empty list if loading fails.
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)  # Read and parse JSON file
    except Exception as e:
        logger.error(f"Error loading feedback data: {e}")  # Log any errors
        return []  # Return empty list on failure

# -----------------------------------------------------------
# Calculate due date based on priority and event date
# -----------------------------------------------------------
def set_due_date(priority: str, event_date: str) -> str:
    """
    Sets a due date for a JIRA ticket based on priority and event date.

    Args:
        priority (str): Priority level (high, medium, low).
        event_date (str): Event date in YYYY-MM-DD format.

    Returns:
        str: Due date in YYYY-MM-DD format.
    """
    try:
        base_date = datetime.strptime(event_date, "%Y-%m-%d")  # Parse event date
        # Map priority to days: high=3, medium=7, low=14, default=7
        days = {"high": 3, "medium": 7, "low": 14}.get(priority.lower(), 7)
        return (base_date + timedelta(days=days)).strftime("%Y-%m-%d")  # Calculate and format due date
    except ValueError:
        # Fallback to current date + 7 days if date parsing fails
        return (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

# -----------------------------------------------------------
# Route feedback to operational or non-operational categories
# -----------------------------------------------------------
def route_feedback(feedback_text: str, feedback_source: str) -> FeedbackRoute:
    """
    Determines if feedback is operational (actionable) or non-operational (non-actionable).

    Args:
        feedback_text (str): The feedback text to analyze.
        feedback_source (str): Source of the feedback (e.g., fan_survey).

    Returns:
        FeedbackRoute: Structured classification of feedback type, confidence, and description.
    """
    logger.info("Routing feedback")
    # Define prompt for LLM to classify feedback
    prompt = (
        f"Analyze the following text: '{feedback_text}' from source '{feedback_source}'.\n"
        "Determine if it is operational feedback related to IT systems, arena operations, mobile apps, or other actionable areas "
        "(e.g., Wi-Fi, ticketing, scoreboards, concessions, app usability) that requires action, or non-operational feedback "
        "(e.g., general comments, non-actionable) that does not.\n"
        "Return a JSON object with:\n"
        "- feedback_type: 'operational' or 'non_operational'.\n"
        "- confidence_score: Confidence in the classification (0.0 to 1.0).\n"
        "- description: A cleaned version of the feedback text."
    )
    try:
        # Call OpenAI API to classify feedback
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
        structured_response = completion.choices[0].message.content  # Extract LLM response
        result = FeedbackRoute.model_validate_json(structured_response)  # Validate and parse response
        logger.info(f"Feedback routed as: {result.feedback_type} with confidence: {result.confidence_score}")
        return result
    except Exception as e:
        logger.error(f"Error during feedback routing: {e}", exc_info=True)  # Log errors with stack trace
        # Return default non-operational classification on failure
        return FeedbackRoute(feedback_type="non_operational", confidence_score=0.0, description=feedback_text)

# -----------------------------------------------------------
# Classify operational feedback into categories and sentiment
# -----------------------------------------------------------
def validate_operational_feedback(feedback_text: str, feedback_source: str) -> Optional[FeedbackClassification]:
    """
    Classifies operational feedback into a category and determines its sentiment.

    Args:
        feedback_text (str): The feedback text to classify.
        feedback_source (str): Source of the feedback (e.g., fan_survey).

    Returns:
        Optional[FeedbackClassification]: Structured classification, or None if classification fails.
    """
    logger.info("Classifying operational feedback")
    # Define prompt for LLM to categorize and analyze sentiment
    prompt = (
        f"Analyze the operational feedback: '{feedback_text}' from source '{feedback_source}'.\n"
        "Return a JSON object with:\n"
        "- raw_text: The original text.\n"
        "- feedback_category: A single primary category (e.g., Wi-Fi, Mobile App, Ticketing, Scoreboard, Concessions, Fan Experience, Facilities, Marketing). Choose the root cause, e.g., Wi-Fi for connectivity issues impacting apps.\n"
        "- overall_sentiment: Sentiment (positive, negative, mixed, neutral).\n"
        "- confidence_score: Confidence in the classification (0.0 to 1.0).\n"
        "- feedback_source: Source of the feedback.\n"
        "Examples:\n"
        "- Feedback: 'Wi-Fi was spotty, couldn’t use the app' → feedback_category: Wi-Fi\n"
        "- Feedback: 'App crashed during ticket purchase' → feedback_category: Mobile App\n"
    )
    try:
        # Call OpenAI API to classify feedback
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Classify operational feedback for IT, product, arena operations, or other areas."},
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
        structured_response = completion.choices[0].message.content  # Extract LLM response
        parsed_response = FeedbackClassification.model_validate_json(structured_response)  # Validate and parse response
        logger.info(f"Feedback classified: {parsed_response.feedback_category}, Sentiment: {parsed_response.overall_sentiment}")
        return parsed_response
    except Exception as e:
        logger.error(f"Error during feedback classification: {e}", exc_info=True)  # Log errors with stack trace
        return None  # Return None on failure

# -----------------------------------------------------------
# Extract detailed insights from operational feedback
# -----------------------------------------------------------
def extract_feedback_details(feedback_text: str, classification: FeedbackClassification) -> Optional[FeedbackDetails]:
    """
    Extracts detailed insights from operational feedback, including affected systems and suggestions.

    Args:
        feedback_text (str): The feedback text to analyze.
        classification (FeedbackClassification): The feedback's classification.

    Returns:
        Optional[FeedbackDetails]: Structured details, or None if extraction fails.
    """
    logger.info("Extracting feedback details")
    # Define prompt for LLM to extract detailed insights
    prompt = (
        f"Given the feedback: '{feedback_text}',\n"
        f"classified as {classification.feedback_category} feedback with {classification.overall_sentiment} sentiment,\n"
        "extract the following details in JSON format:\n"
        "- system_or_area: The primary system or area affected (e.g., Arena Wi-Fi, Ticketing App). Choose the root cause, e.g., Wi-Fi for connectivity issues impacting apps.\n"
        "- mentioned_components: List of components mentioned with their sentiment (e.g., [{'component': 'App usability', 'sentiment': 'negative'}]).\n"
        "- pros: Positive aspects mentioned.\n"
        "- cons: Negative aspects mentioned.\n"
        "- improvement_suggestions: Suggestions for improvement, including inferred actions if not explicitly stated (e.g., 'fix system' for crashes, 'test hardware' for freezes).\n"
        "- categorize_feedback: Categories (e.g., system outage, app usability issue, hardware failure, fan experience).\n"
        "- key_quotes: Important excerpts.\n"
        "Examples:\n"
        "- Feedback: 'Wi-Fi was spotty, couldn’t use the app' → system_or_area: Arena Wi-Fi, improvement_suggestions: ['Improve Wi-Fi stability']\n"
        "- Feedback: 'Scoreboard froze' → improvement_suggestions: ['Test scoreboard hardware', 'Ensure backup display']\n"
        "- Feedback: 'App crashed' → improvement_suggestions: ['Fix app stability', 'Enhance testing']\n"
    )
    try:
        # Call OpenAI API to extract details
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
        structured_response = completion.choices[0].message.content  # Extract LLM response
        details = FeedbackDetails.model_validate_json(structured_response)  # Validate and parse response
        logger.info(f"Feedback details extracted for: {details.system_or_area}")
        return details
    except Exception as e:
        logger.error(f"Error during feedback details extraction: {e}", exc_info=True)  # Log errors with stack trace
        return None  # Return None on failure

# -----------------------------------------------------------
# Generate analysis and JIRA ticket for operational feedback
# -----------------------------------------------------------
def generate_feedback_analysis(
    feedback_text: str, classification: FeedbackClassification, details: FeedbackDetails, event_date: str
) -> FeedbackAnalysis:
    """
    Generates actionable insights and a JIRA ticket for operational feedback.

    Args:
        feedback_text (str): The feedback text to analyze.
        classification (FeedbackClassification): The feedback's classification.
        details (FeedbackDetails): Detailed insights from the feedback.
        event_date (str): Event date in YYYY-MM-DD format.

    Returns:
        FeedbackAnalysis: Structured analysis with insights and JIRA ticket.
    """
    logger.info("Generating feedback analysis and JIRA ticket")
    # Define mapping of categories to assignees and teams
    ASSIGNEE_MAPPING = {
        "Wi-Fi": ("IT Lead", "IT"),
        "Mobile App": ("Product Manager", "Product Team"),
        "Ticketing": ("Product Manager", "Product Team"),
        "Scoreboard": ("Arena Ops Manager", "Arena Operations"),
        "Concessions": ("Arena Ops Manager", "Arena Operations"),
        "Fan Experience": ("Customer Support Lead", "Customer Support"),
        "Facilities": ("Facilities Manager", "Facilities"),
        "Marketing": ("Marketing Lead", "Marketing"),
    }
    default_assignee, default_team = "IT Lead", "IT"  # Default assignee and team
    # Get assignee and team based on category, or use defaults
    assignee, team = ASSIGNEE_MAPPING.get(classification.feedback_category, (default_assignee, default_team))
    # Define prompt for LLM to generate analysis and ticket
    prompt = (
        f"Feedback Text: {feedback_text}\n"
        f"Classification: Category '{classification.feedback_category}', Sentiment '{classification.overall_sentiment}', Source '{classification.feedback_source}'.\n"
        f"Detailed Insights: {details.model_dump_json()}\n\n"
        "As an organizational router for an NBA team, analyze this operational feedback to generate actionable insights and a JIRA ticket. "
        "Determine the most appropriate team and role to handle the feedback based on the affected system, required expertise, and impact. "
        "Consider the following teams and roles:\n"
        "- Product Team (Product Manager): For mobile app issues (e.g., crashes, usability, feature requests).\n"
        "- IT (IT Lead): For technical infrastructure (e.g., Wi-Fi, system outages).\n"
        "- Arena Operations (Arena Ops Manager): For physical arena systems (e.g., concessions, scoreboards).\n"
        "- Customer Support (Customer Support Lead): For fan experience complaints or service issues.\n"
        "- Facilities (Facilities Manager): For physical venue issues (e.g., seating, restrooms).\n"
        "- Marketing (Marketing Lead): For promotional or branding feedback.\n"
        "Evaluate urgency, impact on fan experience, operational disruption, and source reliability. "
        "Return a JSON object with:\n"
        "- sentiment_score: A score from 0.0 to 1.0, where 0.0 indicates highly negative/urgent feedback (e.g., system failures, major disruptions) "
        "and 1.0 indicates positive/non-urgent feedback (e.g., general praise).\n"
        "- priority_level: Priority based on the sentiment score and context: 'high' (0.0–0.3, critical issues), "
        "'medium' (0.31–0.6, moderate issues), or 'low' (0.61–1.0, minor or positive feedback).\n"
        "- summary: A brief summary of the feedback.\n"
        "- recommended_actions: List of actions to address the feedback.\n"
        "- similar_incidents_pattern: Boolean indicating if this matches other incidents.\n"
        "- team: The assigned team (e.g., Product Team, IT, Arena Operations).\n"
        "- jira_ticket: A JIRA ticket with:\n"
        "  - ticket_id: Unique identifier (e.g., CATEGORY-YYYY-NNN, where YYYY is the event year).\n"
        "  - title: Concise title.\n"
        "  - description: Detailed explanation.\n"
        "  - status: 'To Do'.\n"
        "  - assignee: Specific role (e.g., Product Manager, IT Lead, Arena Ops Manager).\n"
        "  - reporter: 'Ops Manager'.\n"
        "  - priority: High, Medium, or Low (match priority_level).\n"
        "  - due_date: YYYY-MM-DD, set based on priority (3 days for high, 7 for medium, 14 for low).\n"
        "  - affected_system: The system affected.\n"
        "Examples:\n"
        "- Feedback: 'Ticketing app crashed' → team: Product Team, assignee: Product Manager, priority: high, sentiment_score: 0.1.\n"
        "- Feedback: 'Wi-Fi was spotty' → team: IT, assignee: IT Lead, priority: high, sentiment_score: 0.2.\n"
        "- Feedback: 'Scoreboard froze, confusing fans' → team: Arena Operations, assignee: Arena Ops Manager, priority: medium, sentiment_score: 0.4.\n"
        "- Feedback: 'Seats were uncomfortable' → team: Facilities, assignee: Facilities Manager, priority: medium, sentiment_score: 0.5.\n"
        "- Feedback: 'Loved the halftime show' → non-operational, no ticket."
    )
    try:
        # Call OpenAI API to generate analysis and ticket
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Generate insights and JIRA ticket for operational feedback, routing to the appropriate team."},
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
                            "team": {"type": "string"},
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
                            "team",
                            "jira_ticket",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
        )
        structured_response = completion.choices[0].message.content  # Extract LLM response
        analysis_data = json.loads(structured_response)  # Parse JSON response
        # Enforce ticket ID year based on event date
        event_year = event_date[:4]
        ticket_id = analysis_data["jira_ticket"]["ticket_id"]
        if not ticket_id.startswith(f"{classification.feedback_category.upper()}-{event_year}-"):
            ticket_id = f"{classification.feedback_category.upper()}-{event_year}-001"
            analysis_data["jira_ticket"]["ticket_id"] = ticket_id
        # Override due_date using set_due_date function
        analysis_data["jira_ticket"]["due_date"] = set_due_date(analysis_data["priority_level"], event_date)
        # Use LLM's assignee and team if provided, else use defaults
        assignee = analysis_data["jira_ticket"].get("assignee", assignee)
        team = analysis_data.get("team", team)
        # Create FeedbackAnalysis object with processed data
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
            team=team,
        )
        logger.info(f"Feedback analysis generated: {analysis.summary}")
        return analysis
    except Exception as e:
        logger.error(f"Error during feedback analysis: {e}", exc_info=True)  # Log errors with stack trace
        # Return failed analysis on error
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
            team=None,
        )

# -----------------------------------------------------------
# Process operational feedback through classification and analysis
# -----------------------------------------------------------
def handle_operational_feedback(feedback: Dict) -> FeedbackAnalysis:
    """
    Handles operational feedback by classifying, extracting details, and generating analysis.

    Args:
        feedback (Dict): Feedback entry with id, feedback_text, source, and event_date.

    Returns:
        FeedbackAnalysis: Structured analysis, or failed result if processing fails.
    """
    logger.info(f"Processing operational feedback: {feedback['id']}")
    # Classify feedback
    classification = validate_operational_feedback(feedback["feedback_text"], feedback["source"])
    if not classification:
        # Return failed analysis if classification fails
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
            team=None,
        )
    # Extract detailed insights
    details = extract_feedback_details(feedback["feedback_text"], classification)
    if not details:
        # Return failed analysis if detail extraction fails
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
            team=None,
        )
    # Generate analysis and JIRA ticket
    return generate_feedback_analysis(feedback["feedback_text"], classification, details, feedback["event_date"])

# -----------------------------------------------------------
# Handle non-operational feedback
# -----------------------------------------------------------
def handle_non_operational_feedback(feedback: Dict) -> FeedbackAnalysis:
    """
    Processes non-operational feedback, marking it as non-actionable.

    Args:
        feedback (Dict): Feedback entry with id and feedback_text.

    Returns:
        FeedbackAnalysis: Result indicating no further action needed.
    """
    logger.info(f"Processing non-operational feedback: {feedback['id']}")
    message = "Feedback is non-operational and does not require further action"
    if "loved" in feedback["feedback_text"].lower():
        message += " (positive comment noted)"  # Note positive feedback
    # Return non-actionable result
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
        team=None,
    )

# -----------------------------------------------------------
# Main feedback processing logic
# -----------------------------------------------------------
def process_feedback(feedback: Dict) -> FeedbackAnalysis:
    """
    Routes feedback to operational or non-operational processing based on classification.

    Args:
        feedback (Dict): Feedback entry with id, feedback_text, and source.

    Returns:
        FeedbackAnalysis: Processed feedback result.
    """
    logger.info(f"Processing feedback: {feedback['id']}")
    # Route feedback to determine type
    route_result = route_feedback(feedback["feedback_text"], feedback["source"])
    if route_result.confidence_score < 0.7:
        logger.warning(f"Low confidence score: {route_result.confidence_score}")  # Warn on low confidence
        # Return failed analysis for low confidence
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
            team=None,
        )
    # Process based on feedback type
    if route_result.feedback_type == "operational":
        return handle_operational_feedback(feedback)
    else:
        return handle_non_operational_feedback(feedback)

# -----------------------------------------------------------
# Run the full feedback analysis pipeline
# -----------------------------------------------------------
def run_full_feedback_analysis_pipeline():
    """
    Loads and processes all feedback entries, printing detailed results.

    Args:
        None

    Returns:
        None
    """
    feedback_list = load_feedback_data()  # Load feedback from JSON file
    for feedback in feedback_list:
        print(f"\nProcessing feedback: {feedback['id']}")  # Print feedback ID
        print(f"Title: {feedback['title']}\n")  # Print feedback title
        result = process_feedback(feedback)  # Process feedback
        print(f"Response: {result.message}")  # Print processing result
        if result.success and result.jira_ticket:
            # Print classification details
            print("Classification:")
            print(f"  Feedback Category: {result.classification.feedback_category}")
            print(f"  Overall Sentiment: {result.classification.overall_sentiment}")
            print(f"  Confidence Score: {result.classification.confidence_score}")
            print(f"  Feedback Source: {result.classification.feedback_source}\n")
            # Print feedback details
            print("Feedback Details:")
            print(f"  System/Area: {result.details.system_or_area}")
            print(f"  Mentioned Components: {result.details.mentioned_components}")
            print(f"  Pros: {result.details.pros}")
            print(f"  Cons: {result.details.cons}")
            print(f"  Improvement Suggestions: {result.details.improvement_suggestions}")
            print(f"  Categorize Feedback: {result.details.categorize_feedback}")
            print(f"  Key Quotes: {result.details.key_quotes}\n")
            # Print analysis and JIRA ticket
            print("Feedback Analysis and JIRA Ticket:")
            print(f"  Sentiment Score: {result.sentiment_score}")
            print(f"  Summary: {result.summary}")
            print(f"  Priority Level: {result.priority_level}")
            print(f"  Assigned Team: {result.team}")
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
        print("-------------------------------------------")  # Print separator

# -----------------------------------------------------------
# FastAPI Endpoints
# Simple, elegant API interface for feedback analysis
# -----------------------------------------------------------

@app.post("/analyze", response_model=FeedbackResponse)
async def analyze_feedback(request: FeedbackRequest):
    """
    Analyzes operational feedback and generates actionable insights with JIRA tickets.

    This endpoint routes feedback through our 4-stage AI pipeline:
    1. Routing: Determines if feedback is operational or non-operational
    2. Classification: Categorizes into domains (Wi-Fi, Mobile App, etc.)
    3. Detail Extraction: Identifies affected systems and sentiment
    4. Analysis & Ticketing: Generates insights and JIRA tickets with team assignment

    Args:
        request: FeedbackRequest with feedback_text, source, event_date, and optional feedback_id

    Returns:
        FeedbackResponse with success status, message, and full analysis results
    """
    try:
        # Log incoming request
        feedback_id = request.feedback_id or f"api-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"API request received for feedback: {feedback_id}")
        logger.info(f"Feedback text: {request.feedback_text[:100]}...")  # Log first 100 chars

        # Prepare feedback object for processing
        feedback = {
            "id": feedback_id,
            "feedback_text": request.feedback_text,
            "source": request.source,
            "event_date": request.event_date,
            "title": f"API Feedback - {feedback_id}",
        }

        # Process feedback through the AI pipeline
        analysis_result = process_feedback(feedback)

        # Log completion
        logger.info(f"Analysis completed for feedback: {feedback_id}")
        logger.info(f"Result: {analysis_result.message}")

        # Return structured response
        return FeedbackResponse(
            success=analysis_result.success,
            message=analysis_result.message,
            analysis=analysis_result if analysis_result.success else None,
        )

    except Exception as e:
        # Log error and return failure response
        logger.error(f"Error processing feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process feedback: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Simple health check endpoint to verify the API is running.

    Returns:
        JSON response with status and service information
    """
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "service": "Operational Feedback Analysis API",
        "version": "1.0.0",
        "model": model,
    }

@app.on_event("startup")
async def startup_event():
    """
    Runs when the FastAPI application starts.
    Logs startup information to stdout.
    """
    logger.info("=" * 80)
    logger.info("Operational Feedback Analysis API - Starting Up")
    logger.info("=" * 80)
    logger.info(f"OpenAI Model: {model}")
    logger.info(f"API Key Configured: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    logger.info("Ready to process feedback requests")
    logger.info("=" * 80)

# -----------------------------------------------------------
# Entry point for script execution
# Supports both CLI mode and API server mode
# -----------------------------------------------------------
if __name__ == "__main__":
    import sys

    # Check if we should run in API mode or CLI mode
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        # Run as API server
        logger.info("Starting in API server mode...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
        )
    else:
        # Run as CLI script (original behavior)
        logger.info("Starting in CLI mode...")
        run_full_feedback_analysis_pipeline()  # Run the feedback analysis pipeline