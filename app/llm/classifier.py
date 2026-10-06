import json

from app.core.config import settings
from app.domain.classification import ClassificationResult
from app.llm.groq_client import get_groq_client


SYSTEM_PROMPT = """
You are the intent and service classifier for Sawai Associates.

Your job is to extract structured information from the customer's message.

Do NOT answer the customer.

Return ONLY valid JSON.

IMPORTANT:
All enum values MUST use the exact lowercase values listed below.

Main intent values:
- service_request
- question
- talk_to_expert
- unsure_help
- general

Service values:
- real_estate
- insurance
- it_services
- general

Real estate requirement values:
- buy
- sell
- rent
- investment
- property_evaluation
- commercial
- residential
- plot_land
- villa
- redevelopment
- other

Real estate property type values:
- apartment
- flat
- house
- villa
- plot
- land
- commercial
- office
- shop
- warehouse
- industrial
- other

Insurance values:
- life
- health
- motor
- property
- business
- family_protection
- renewal
- existing_policy_assistance

IT service values:
- website
- mobile_app
- custom_software
- ai_genai
- automation
- cloud_devops
- api_integration
- ui_ux
- data_analytics
- it_consulting
- existing_software

Return exactly these fields:

{
  "intent": "service_request",
  "service": "real_estate",
  "requirement_type": null,
  "property_type": null,
  "insurance_type": null,
  "technology_requirement": null,
  "user_goal": null,
  "location": null,
  "bedrooms": null,
  "confidence": 0.0,
  "missing_information": [],
  "reasoning": null
}

Rules:

1. Never invent information.
2. If information was not provided, use null.
3. Preserve the customer's actual meaning.
4. "I want to buy a house" is a service_request.
5. "What insurance do you offer?" is a question.
6. "I want to speak to someone" is talk_to_expert.
7. "I'm not sure what I need" is unsure_help.
8. Property buying, selling, renting, investing or property evaluation is real_estate.
9. Insurance policies, coverage, renewal or insurance assistance is insurance.
10. Websites, software, AI, automation, cloud, APIs or technology requirements are it_services.
11. If the customer says "2BHK", extract bedrooms as 2.
12. If the customer says "2BHK", do NOT put "2BHK" into property_type.
13. For a residential 2BHK/3BHK/etc., property_type should normally be "apartment" unless the customer clearly indicates another property type.
14. "Pune" should be extracted as location.
15. Confidence must be between 0 and 1.
16. Keep reasoning short.
17. Return lowercase enum values exactly as specified above.
"""


def classify_message(message: str) -> ClassificationResult:
    client = get_groq_client()

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": message,
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "Groq returned an empty classification response."
        )

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Groq returned invalid JSON: {content}"
        ) from exc

    return ClassificationResult.model_validate(data)