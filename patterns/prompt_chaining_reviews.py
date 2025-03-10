from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from openai import OpenAI
import os
import logging

# --------------------------------------------------------------
# Step 1: Define the data models for each stage
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
    inferred_rating: float  # 1-5 scale
    key_quotes: list[str]  # Quotable sections

class ReviewAnalysis(BaseModel):
    """Third LLM call: Generate actionable insights"""
    summary: str
    priority_level: str  # high, medium, low
    recommended_actions: list[str]
    similar_reviews_pattern: bool  # indicates if this matches other feedback