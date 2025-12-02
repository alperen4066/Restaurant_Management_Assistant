from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class OrderItem(BaseModel):
    item_id: str
    name: str
    quantity: int
    price: float


class Reservation(BaseModel):
    date: str
    time: str
    people: int
    has_preorder: bool = False


class SessionState(BaseModel):
    history: List[Dict[str, Any]] = []
    current_order: List[OrderItem] = []
    current_total: float = 0.0
    allergens: List[str] = []
    reservation: Optional[Reservation] = None
    mode: str = "chat"
    last_question: Optional[str] = None  # Track context


class ChatRequest(BaseModel):
    session_id: str
    user_message: str
    user_email: Optional[str] = None
    user_allergens: Optional[List[str]] = None


class ChatResponse(BaseModel):
    assistant_message: str
    current_order: List[OrderItem]
    current_total: float
