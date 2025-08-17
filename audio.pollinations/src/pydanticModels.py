from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union

class APIMessage(BaseModel):
    """Chat message for API (renamed to avoid conflicts)"""
    role: str = Field(..., description="Role: user, assistant, system")
    content: str = Field(..., description="Message content")

class OpenAIRequest(BaseModel):
    """OpenAI-compatible request format"""
    model: str = Field(default="higgs", description="Model name")
    modalities: List[str] = Field(default=["text", "audio"], description="Supported modalities")
    audio: Optional[str] = Field(None, description="Base64 encoded audio or URL for voice cloning")
    messages: List[APIMessage] = Field(..., description="Chat messages")
    seed: Optional[int] = Field(None, description="Random seed")