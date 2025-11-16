# Operational Feedback Analysis API

Simple, elegant FastAPI service for AI-powered sentiment analysis and JIRA ticket generation.

## Overview

This API processes operational feedback through a sophisticated 4-stage AI pipeline:

1. **Routing**: Determines if feedback is operational or non-operational
2. **Classification**: Categorizes into domains (Wi-Fi, Mobile App, Ticketing, etc.)
3. **Detail Extraction**: Identifies affected systems and component-level sentiment
4. **Analysis & Ticketing**: Generates actionable insights and JIRA tickets with smart team assignment

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

### Running the API Server

```bash
# Start the FastAPI server
python patterns/prompt_chaining_IT_review.py --api
```

The server will start on `http://0.0.0.0:8000`

### Running in CLI Mode (Original)

```bash
# Process feedback from JSON file
python patterns/prompt_chaining_IT_review.py
```

## API Endpoints

### POST /analyze

Analyzes operational feedback and generates insights with JIRA tickets.

**Request Body:**

```json
{
  "feedback_text": "Wi-Fi was spotty during the game, couldn't load the mobile app",
  "source": "fan_survey",
  "event_date": "2025-11-16",
  "feedback_id": "optional-tracking-id"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Processed operational feedback for Wi-Fi",
  "analysis": {
    "success": true,
    "message": "Processed operational feedback for Wi-Fi",
    "sentiment_score": 0.2,
    "summary": "Fan experienced Wi-Fi connectivity issues affecting mobile app usage",
    "priority_level": "high",
    "recommended_actions": [
      "Improve Wi-Fi stability in arena",
      "Add network monitoring during events"
    ],
    "similar_incidents_pattern": true,
    "team": "IT",
    "jira_ticket": {
      "ticket_id": "WI-FI-2025-001",
      "title": "Arena Wi-Fi Connectivity Issues Affecting App Usage",
      "description": "Fan reported spotty Wi-Fi preventing mobile app access during game...",
      "status": "To Do",
      "assignee": "IT Lead",
      "reporter": "Ops Manager",
      "priority": "High",
      "due_date": "2025-11-19",
      "affected_system": "Arena Wi-Fi"
    },
    "classification": {
      "raw_text": "Wi-Fi was spotty during the game, couldn't load the mobile app",
      "feedback_category": "Wi-Fi",
      "overall_sentiment": "negative",
      "confidence_score": 0.95,
      "feedback_source": "fan_survey"
    },
    "details": {
      "system_or_area": "Arena Wi-Fi",
      "mentioned_components": [
        {"component": "Wi-Fi connectivity", "sentiment": "negative"},
        {"component": "Mobile app", "sentiment": "negative"}
      ],
      "pros": [],
      "cons": ["Spotty Wi-Fi", "Unable to load app"],
      "improvement_suggestions": ["Improve Wi-Fi stability"],
      "categorize_feedback": ["system outage", "connectivity issue"],
      "key_quotes": ["Wi-Fi was spotty", "couldn't load the mobile app"]
    }
  }
}
```

### GET /health

Simple health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "service": "Operational Feedback Analysis API",
  "version": "1.0.0",
  "model": "gpt-4o-mini-2024-07-18"
}
```

## Example Usage

### Using cURL

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_text": "The mobile app crashed when I tried to buy tickets",
    "source": "app_review",
    "event_date": "2025-11-16"
  }'
```

### Using Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/analyze",
    json={
        "feedback_text": "Scoreboard froze during halftime",
        "source": "fan_survey",
        "event_date": "2025-11-16",
    }
)

result = response.json()
print(f"Priority: {result['analysis']['priority_level']}")
print(f"Team: {result['analysis']['team']}")
print(f"Ticket ID: {result['analysis']['jira_ticket']['ticket_id']}")
```

## Team Assignment Logic

The API intelligently routes feedback to appropriate teams:

- **Product Team**: Mobile app issues, ticketing app problems
- **IT**: Wi-Fi, technical infrastructure, system outages
- **Arena Operations**: Scoreboards, concessions, physical arena systems
- **Customer Support**: Fan experience complaints, service issues
- **Facilities**: Physical venue issues (seating, restrooms)
- **Marketing**: Promotional or branding feedback

## Logging

All operations are logged to **stdout** for easy monitoring:

```
2025-11-16 10:30:45 - INFO - API request received for feedback: api-20251116103045
2025-11-16 10:30:45 - INFO - Feedback text: The mobile app crashed when I tried to buy tickets...
2025-11-16 10:30:46 - INFO - Routing feedback
2025-11-16 10:30:47 - INFO - Feedback routed as: operational with confidence: 0.95
2025-11-16 10:30:48 - INFO - Classifying operational feedback
2025-11-16 10:30:49 - INFO - Feedback classified: Mobile App, Sentiment: negative
2025-11-16 10:30:50 - INFO - Analysis completed for feedback: api-20251116103045
```

## Interactive API Documentation

FastAPI automatically generates interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Architecture

```
┌─────────────────┐
│  POST /analyze  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│        4-Stage AI Pipeline              │
├─────────────────────────────────────────┤
│ 1. Route (operational vs non-op)        │
│ 2. Classify (Wi-Fi, App, etc.)          │
│ 3. Extract Details (systems, sentiment) │
│ 4. Generate Analysis & JIRA Ticket      │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ JSON Response   │
│ - Sentiment     │
│ - Priority      │
│ - JIRA Ticket   │
│ - Team Route    │
└─────────────────┘
```

## Notes

- Default event_date is today's date if not provided
- Default source is "api" if not specified
- Sentiment score: 0.0 (critical/urgent) to 1.0 (positive/non-urgent)
- Priority levels automatically calculated from sentiment and context
- Due dates automatically set based on priority (high=3 days, medium=7 days, low=14 days)
