# Expected Output Examples

This document shows expected outputs for the Operational Feedback Analysis API in both modes.

---

## 1. API Server Mode Startup

```bash
$ python patterns/prompt_chaining_IT_review.py --api
```

**Expected stdout:**

```
2025-11-16 10:30:00 - INFO - Starting in API server mode...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
2025-11-16 10:30:01 - INFO - ================================================================================
2025-11-16 10:30:01 - INFO - Operational Feedback Analysis API - Starting Up
2025-11-16 10:30:01 - INFO - ================================================================================
2025-11-16 10:30:01 - INFO - OpenAI Model: gpt-4o-mini-2024-07-18
2025-11-16 10:30:01 - INFO - API Key Configured: Yes
2025-11-16 10:30:01 - INFO - Ready to process feedback requests
2025-11-16 10:30:01 - INFO - ================================================================================
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 2. API Request Processing (Operational Feedback)

### Request:
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_text": "Wi-Fi was spotty during the game, couldn'\''t load the mobile app to order food",
    "source": "fan_survey",
    "event_date": "2025-11-16",
    "feedback_id": "survey-001"
  }'
```

### Expected stdout logs:
```
INFO:     127.0.0.1:54321 - "POST /analyze HTTP/1.1" 200 OK
2025-11-16 10:35:12 - INFO - API request received for feedback: survey-001
2025-11-16 10:35:12 - INFO - Feedback text: Wi-Fi was spotty during the game, couldn't load the mobile app to order food...
2025-11-16 10:35:12 - INFO - Processing feedback: survey-001
2025-11-16 10:35:12 - INFO - Routing feedback
2025-11-16 10:35:14 - INFO - Feedback routed as: operational with confidence: 0.95
2025-11-16 10:35:14 - INFO - Processing operational feedback: survey-001
2025-11-16 10:35:14 - INFO - Classifying operational feedback
2025-11-16 10:35:16 - INFO - Feedback classified: Wi-Fi, Sentiment: negative
2025-11-16 10:35:16 - INFO - Extracting feedback details
2025-11-16 10:35:18 - INFO - Feedback details extracted for: Arena Wi-Fi
2025-11-16 10:35:18 - INFO - Generating feedback analysis and JIRA ticket
2025-11-16 10:35:21 - INFO - Feedback analysis generated: Fan experienced Wi-Fi connectivity issues preventing mobile app usage during game
2025-11-16 10:35:21 - INFO - Analysis completed for feedback: survey-001
2025-11-16 10:35:21 - INFO - Result: Processed operational feedback for Wi-Fi
```

### Expected JSON response:
```json
{
  "success": true,
  "message": "Processed operational feedback for Wi-Fi",
  "analysis": {
    "success": true,
    "message": "Processed operational feedback for Wi-Fi",
    "sentiment_score": 0.2,
    "summary": "Fan experienced Wi-Fi connectivity issues preventing mobile app usage during game",
    "priority_level": "high",
    "recommended_actions": [
      "Improve Wi-Fi coverage and stability in arena",
      "Implement real-time network monitoring during events",
      "Add Wi-Fi troubleshooting support at guest services"
    ],
    "similar_incidents_pattern": true,
    "team": "IT",
    "jira_ticket": {
      "ticket_id": "WI-FI-2025-001",
      "title": "Arena Wi-Fi Connectivity Issues Affecting Mobile App Usage",
      "description": "Fan reported spotty Wi-Fi during game preventing mobile app access for food ordering. This is a high-priority issue affecting fan experience and revenue. Root cause identified as Wi-Fi infrastructure. Immediate attention required to prevent recurring issues.",
      "status": "To Do",
      "assignee": "IT Lead",
      "reporter": "Ops Manager",
      "priority": "High",
      "due_date": "2025-11-19",
      "affected_system": "Arena Wi-Fi"
    },
    "classification": {
      "raw_text": "Wi-Fi was spotty during the game, couldn't load the mobile app to order food",
      "feedback_category": "Wi-Fi",
      "overall_sentiment": "negative",
      "confidence_score": 0.95,
      "feedback_source": "fan_survey"
    },
    "details": {
      "system_or_area": "Arena Wi-Fi",
      "mentioned_components": [
        {
          "component": "Wi-Fi connectivity",
          "sentiment": "negative"
        },
        {
          "component": "Mobile app",
          "sentiment": "negative"
        },
        {
          "component": "Food ordering",
          "sentiment": "negative"
        }
      ],
      "pros": [],
      "cons": [
        "Spotty Wi-Fi connection",
        "Unable to load mobile app",
        "Could not order food"
      ],
      "improvement_suggestions": [
        "Improve Wi-Fi stability and coverage",
        "Implement network redundancy",
        "Add offline mode to mobile app"
      ],
      "categorize_feedback": [
        "system outage",
        "connectivity issue",
        "fan experience",
        "revenue impact"
      ],
      "key_quotes": [
        "Wi-Fi was spotty during the game",
        "couldn't load the mobile app to order food"
      ]
    }
  }
}
```

---

## 3. API Request Processing (Non-Operational Feedback)

### Request:
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_text": "Loved the halftime show! Great entertainment!",
    "source": "social_media"
  }'
```

### Expected stdout logs:
```
INFO:     127.0.0.1:54322 - "POST /analyze HTTP/1.1" 200 OK
2025-11-16 10:40:05 - INFO - API request received for feedback: api-20251116104005
2025-11-16 10:40:05 - INFO - Feedback text: Loved the halftime show! Great entertainment!...
2025-11-16 10:40:05 - INFO - Processing feedback: api-20251116104005
2025-11-16 10:40:05 - INFO - Routing feedback
2025-11-16 10:40:07 - INFO - Feedback routed as: non_operational with confidence: 0.92
2025-11-16 10:40:07 - INFO - Processing non-operational feedback: api-20251116104005
2025-11-16 10:40:07 - INFO - Analysis completed for feedback: api-20251116104005
2025-11-16 10:40:07 - INFO - Result: Feedback is non-operational and does not require further action (positive comment noted)
```

### Expected JSON response:
```json
{
  "success": true,
  "message": "Feedback is non-operational and does not require further action (positive comment noted)",
  "analysis": {
    "success": true,
    "message": "Feedback is non-operational and does not require further action (positive comment noted)",
    "sentiment_score": null,
    "summary": null,
    "priority_level": null,
    "recommended_actions": null,
    "similar_incidents_pattern": null,
    "jira_ticket": null,
    "classification": null,
    "details": null,
    "team": null
  }
}
```

---

## 4. Health Check Endpoint

### Request:
```bash
curl http://localhost:8000/health
```

### Expected stdout logs:
```
INFO:     127.0.0.1:54323 - "GET /health HTTP/1.1" 200 OK
2025-11-16 10:42:15 - INFO - Health check requested
```

### Expected JSON response:
```json
{
  "status": "healthy",
  "service": "Operational Feedback Analysis API",
  "version": "1.0.0",
  "model": "gpt-4o-mini-2024-07-18"
}
```

---

## 5. Error Handling (Low Confidence)

### Request:
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_text": "asdfghjkl",
    "source": "unknown"
  }'
```

### Expected stdout logs:
```
INFO:     127.0.0.1:54324 - "POST /analyze HTTP/1.1" 200 OK
2025-11-16 10:45:30 - INFO - API request received for feedback: api-20251116104530
2025-11-16 10:45:30 - INFO - Feedback text: asdfghjkl...
2025-11-16 10:45:30 - INFO - Processing feedback: api-20251116104530
2025-11-16 10:45:30 - INFO - Routing feedback
2025-11-16 10:45:32 - INFO - Feedback routed as: non_operational with confidence: 0.45
2025-11-16 10:45:32 - WARNING - Low confidence score: 0.45
2025-11-16 10:45:32 - INFO - Analysis completed for feedback: api-20251116104530
2025-11-16 10:45:32 - INFO - Result: Feedback classification confidence too low
```

### Expected JSON response:
```json
{
  "success": false,
  "message": "Feedback classification confidence too low",
  "analysis": null
}
```

---

## 6. CLI Mode (Original Behavior)

### Request:
```bash
python patterns/prompt_chaining_IT_review.py
```

### Expected stdout:
```
2025-11-16 10:50:00 - INFO - Starting in CLI mode...
2025-11-16 10:50:00 - INFO - Processing feedback: fb-001
2025-11-16 10:50:00 - INFO - Routing feedback
2025-11-16 10:50:02 - INFO - Feedback routed as: operational with confidence: 0.93
2025-11-16 10:50:02 - INFO - Processing operational feedback: fb-001
2025-11-16 10:50:02 - INFO - Classifying operational feedback
2025-11-16 10:50:04 - INFO - Feedback classified: Mobile App, Sentiment: negative
2025-11-16 10:50:04 - INFO - Extracting feedback details
2025-11-16 10:50:06 - INFO - Feedback details extracted for: Ticketing App
2025-11-16 10:50:06 - INFO - Generating feedback analysis and JIRA ticket
2025-11-16 10:50:09 - INFO - Feedback analysis generated: Mobile app crash during ticket purchase flow causing customer frustration

Processing feedback: fb-001
Title: App Crash During Purchase

Response: Processed operational feedback for Mobile App
Classification:
  Feedback Category: Mobile App
  Overall Sentiment: negative
  Confidence Score: 0.93
  Feedback Source: app_review

Feedback Details:
  System/Area: Ticketing App
  Mentioned Components: [{'component': 'Ticket purchase flow', 'sentiment': 'negative'}, {'component': 'App stability', 'sentiment': 'negative'}]
  Pros: []
  Cons: ['App crashed during checkout', 'Lost ticket selection']
  Improvement Suggestions: ['Fix app crash during purchase flow', 'Implement session recovery', 'Add crash reporting']
  Categorize Feedback: ['app crash', 'purchase flow', 'user experience']
  Key Quotes: ['app crashed when buying tickets']

Feedback Analysis and JIRA Ticket:
  Sentiment Score: 0.15
  Summary: Mobile app crash during ticket purchase flow causing customer frustration
  Priority Level: high
  Assigned Team: Product Team
  Recommended Actions: ['Fix critical app stability issues in purchase flow', 'Implement comprehensive crash analytics', 'Add session state recovery']
  Similar Incidents Pattern: True
  JIRA Ticket:
    Ticket ID: MOBILE APP-2025-001
    Title: Critical: App Crashes During Ticket Purchase
    Description: User reported app crash during ticket purchase checkout. High-priority revenue-impacting issue requiring immediate fix. Product Team to investigate crash logs and implement stability improvements.
    Status: To Do
    Assignee: Product Manager
    Reporter: Ops Manager
    Priority: High
    Due Date: 2025-11-19
    Affected System: Ticketing App
-------------------------------------------

[continues for each feedback entry in reviewITData.json...]
```

---

## Key Logging Features

✅ **All logs to stdout** - Easy monitoring and container-friendly
✅ **Timestamp on every log** - Precise tracking
✅ **Request tracking** - Each request gets unique ID
✅ **Pipeline stage logging** - Visibility into 4-stage process
✅ **Error logging with stack traces** - Full debugging context
✅ **Startup banner** - Clear service initialization
✅ **Health check logging** - Monitor endpoint usage
✅ **Warning for low confidence** - Quality control alerts

The logging is comprehensive, clean, and perfect for production monitoring! 🚀
