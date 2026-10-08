from enum import Enum


class ServiceType(str, Enum):
    REAL_ESTATE = "real_estate"
    INSURANCE = "insurance"
    IT_SERVICES = "it_services"
    GENERAL = "general"


class MainIntent(str, Enum):
    SERVICE_REQUEST = "service_request"
    QUESTION = "question"
    TALK_TO_EXPERT = "talk_to_expert"
    UNSURE_HELP = "unsure_help"
    GENERAL = "general"


class RequirementType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    RENT = "rent"
    INVESTMENT = "investment"
    PROPERTY_EVALUATION = "property_evaluation"
    COMMERCIAL = "commercial"
    RESIDENTIAL = "residential"
    PLOT_LAND = "plot_land"
    VILLA = "villa"
    REDEVELOPMENT = "redevelopment"
    OTHER = "other"


class PropertyType(str, Enum):
    APARTMENT = "apartment"
    FLAT = "flat"
    HOUSE = "house"
    VILLA = "villa"
    PLOT = "plot"
    LAND = "land"
    COMMERCIAL = "commercial"
    OFFICE = "office"
    SHOP = "shop"
    WAREHOUSE = "warehouse"
    INDUSTRIAL = "industrial"
    OTHER = "other"


class InsuranceType(str, Enum):
    LIFE = "life"
    HEALTH = "health"
    MOTOR = "motor"
    PROPERTY = "property"
    BUSINESS = "business"
    FAMILY_PROTECTION = "family_protection"
    RENEWAL = "renewal"
    EXISTING_POLICY_ASSISTANCE = "existing_policy_assistance"


class ITServiceType(str, Enum):
    WEBSITE = "website"
    MOBILE_APP = "mobile_app"
    CUSTOM_SOFTWARE = "custom_software"
    AI_GENAI = "ai_genai"
    AUTOMATION = "automation"
    CLOUD_DEVOPS = "cloud_devops"
    API_INTEGRATION = "api_integration"
    UI_UX = "ui_ux"
    DATA_ANALYTICS = "data_analytics"
    IT_CONSULTING = "it_consulting"
    EXISTING_SOFTWARE = "existing_software"


class AIGenAIType(str, Enum):
    AI_CHATBOT = "ai_chatbot"
    CUSTOMER_SUPPORT_AI = "customer_support_ai"
    RAG_KNOWLEDGE_ASSISTANT = "rag_knowledge_assistant"
    AI_AUTOMATION = "ai_automation"
    AGENTIC_AI = "agentic_ai"
    RECOMMENDATION_SYSTEM = "recommendation_system"


class TimelineType(str, Enum):
    IMMEDIATE = "immediate"
    WITHIN_1_MONTH = "within_1_month"
    ONE_TO_THREE_MONTHS = "one_to_three_months"
    THREE_TO_SIX_MONTHS = "three_to_six_months"
    SIX_PLUS_MONTHS = "six_plus_months"
    EXPLORING = "exploring"
    NOT_SURE = "not_sure"


class FinancingRequirement(str, Enum):
    YES = "yes"
    NO = "no"
    NOT_SURE = "not_sure"


class ContactPreference(str, Enum):
    PHONE = "phone"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    CALL = "call"
    NO_PREFERENCE = "no_preference"


class LeadPriority(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"

    # Keep this for compatibility with existing development data.
    IN_PROGRESS = "in_progress"

    PROPOSAL_SHARED = "proposal_shared"
    FOLLOW_UP = "follow_up"

    CONVERTED = "converted"

    # Keep CLOSED for compatibility.
    CLOSED = "closed"

    CLOSED_LOST = "closed_lost"


class TeamType(str, Enum):
    REAL_ESTATE = "real_estate_team"
    INSURANCE = "insurance_team"
    IT = "it_team"
    GENERAL = "business_customer_support"


class ConversationMode(str, Enum):
    MAIN_MENU = "main_menu"
    GENERAL_CHAT = "general_chat"
    QUALIFICATION = "qualification"
    EXPERT_REQUEST = "expert_request"
    SUMMARY = "summary"
    COMPLETED = "completed"