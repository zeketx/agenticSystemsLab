import json
import logging
import os
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from openai import OpenAI
from datetime import datetime, timedelta

# Set up logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4o-mini-2024-07-18"

# Define the data models
class FeedbackRoute(BaseModel):
    feedback_type: Literal["operational", "non_operational"]
    confidence_score: float
    description: str

class FeedbackClassification(BaseModel):
    raw_text: str
    feedback_category: str
    overall_sentiment: str
    confidence_score: float
    feedback_source: str

class FeedbackDetails(BaseModel):
    system_or_area: str
    mentioned_components: List[Dict[str, str]]
    pros: List[str]
    cons: List[str]
    improvement_suggestions: List[str]
    categorize_feedback: List[str]
    key_quotes: List[str]

class JiraTicket(BaseModel):
    ticket_id: str
    title: str
    description: str
    status: str
    assignee: str
    reporter: str
    priority: str
    due_date: str
    affected_system: str

class FeedbackAnalysis(BaseModel):
    success: bool
    message: str
    sentiment_score: Optional[float]
    summary: Optional[str]
    priority_level: Optional[str]
    recommended_actions: Optional[List[str]]
    similar_incidents_pattern: Optional[bool]
    jira_ticket: Optional[JiraTicket]
    classification: Optional[FeedbackClassification]
    details: Optional[FeedbackDetails]
    team: Optional[str]

# Load feedback data
def load_feedback_data(file_path: str = "reviewITData.json") -> List[Dict[str, Any]]:
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading feedback data: {e}")
        return []

# Set dynamic due date based on priority
def set_due_date(priority: str, event_date: str) -> str:
    try:
        base_date = datetime.strptime(event_date, "%Y-%m-%d")
        days = {"high": 3, "medium": 7, "low": 14}.get(priority.lower(), 7)
        return (base_date + timedelta(days=days)).strftime("%Y-%m-%d")
    except ValueError:
        return (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

# Routing and processing functions
def route_feedback(feedback_text: str, feedback_source: str) -> FeedbackRoute:
    logger.info("Routing feedback")
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
    logger.info("Classifying operational feedback")
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
        structured_response = completion.choices[0].message.content
        parsed_response = FeedbackClassification.model_validate_json(structured_response)
        logger.info(f"Feedback classified: {parsed_response.feedback_category}, Sentiment: {parsed_response.overall_sentiment}")
        return parsed_response
    except Exception as e:
        logger.error(f"Error during feedback classification: {e}", exc_info=True)
        return None

def extract_feedback_details(feedback_text: str, classification: FeedbackClassification) -> Optional[FeedbackDetails]:
    logger.info("Extracting feedback details")
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
    logger.info("Generating feedback analysis and JIRA ticket")
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
    default_assignee, default_team = "IT Lead", "IT"
    assignee, team = ASSIGNEE_MAPPING.get(classification.feedback_category, (default_assignee, default_team))
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
        structured_response = completion.choices[0].message.content
        analysis_data = json.loads(structured_response)
        # Enforce ticket ID year
        event_year = event_date[:4]
        ticket_id = analysis_data["jira_ticket"]["ticket_id"]
        if not ticket_id.startswith(f"{classification.feedback_category.upper()}-{event_year}-"):
            ticket_id = f"{classification.feedback_category.upper()}-{event_year}-001"
            analysis_data["jira_ticket"]["ticket_id"] = ticket_id
        # Override due_date
        analysis_data["jira_ticket"]["due_date"] = set_due_date(analysis_data["priority_level"], event_date)
        # Use LLM's assignee and team if provided
        assignee = analysis_data["jira_ticket"].get("assignee", assignee)
        team = analysis_data.get("team", team)
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
            team=None,
        )

def handle_operational_feedback(feedback: Dict) -> FeedbackAnalysis:
    logger.info(f"Processing operational feedback: {feedback['id']}")
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
            team=None,
        )
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
            team=None,
        )
    return generate_feedback_analysis(feedback["feedback_text"], classification, details, feedback["event_date"])

def handle_non_operational_feedback(feedback: Dict) -> FeedbackAnalysis:
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
        team=None,
    )

def process_feedback(feedback: Dict) -> FeedbackAnalysis:
    logger.info(f"Processing feedback: {feedback['id']}")
    route_result = route_feedback(feedback["feedback_text"], feedback["source"])
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
            team=None,
        )
    if route_result.feedback_type == "operational":
        return handle_operational_feedback(feedback)
    else:
        return handle_non_operational_feedback(feedback)

def run_full_feedback_analysis_pipeline():
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
        print("-------------------------------------------")

if __name__ == "__main__":
    run_full_feedback_analysis_pipeline()