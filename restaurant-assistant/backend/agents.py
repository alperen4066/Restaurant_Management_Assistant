from typing import List, Tuple
from backend.models import SessionState, OrderItem, Reservation
from backend.rag import load_menu, get_retriever
import re


# Load menu data
MENU = load_menu()
RETRIEVER = get_retriever()


def find_menu_item_by_name(name: str):
    """Find menu item by partial name match."""
    name_lower = name.lower()
    for item in MENU:
        if name_lower in item["name"].lower():
            return item
    return None


def add_item_to_order(state: SessionState, dish_name: str, quantity: int = 1) -> Tuple[SessionState, str]:
    """Add item to the current order."""
    item_data = find_menu_item_by_name(dish_name)
    
    if not item_data:
        return state, f"Sorry, I could not find a dish matching '{dish_name}'. Please check the menu."
    
    # Check if item already in order
    existing = next((i for i in state.current_order if i.item_id == item_data["id"]), None)
    
    if existing:
        existing.quantity += quantity
    else:
        state.current_order.append(
            OrderItem(
                item_id=item_data["id"],
                name=item_data["name"],
                quantity=quantity,
                price=item_data["price"],
            )
        )
    
    # Recalculate total
    state.current_total = sum(i.price * i.quantity for i in state.current_order)
    
    return state, f"Added {quantity} x {item_data['name']} to your order. Current total is €{state.current_total:.2f}."


def remove_item_from_order(state: SessionState, dish_name: str) -> Tuple[SessionState, str]:
    """Remove item from the current order."""
    item_data = find_menu_item_by_name(dish_name)
    
    if not item_data:
        return state, f"Sorry, I could not find '{dish_name}' in the menu."
    
    # Find and remove item
    state.current_order = [i for i in state.current_order if i.item_id != item_data["id"]]
    
    # Recalculate total
    state.current_total = sum(i.price * i.quantity for i in state.current_order)
    
    return state, f"Removed {item_data['name']} from your order. Current total is €{state.current_total:.2f}."


def set_allergens(state: SessionState, allergens: List[str]) -> Tuple[SessionState, str]:
    """Set user allergens."""
    state.allergens = [a.lower().strip() for a in allergens]
    return state, f"Got it. I will check all dishes for: {', '.join(state.allergens)}."


def check_dish_allergens(dish_name: str, allergens: List[str]) -> str:
    """Check if a dish is safe for user allergens."""
    item = find_menu_item_by_name(dish_name)
    
    if not item:
        return f"I could not find a dish named '{dish_name}'."
    
    dish_allergens = [a.lower() for a in item["allergens"]]
    user_allergens_lower = [a.lower() for a in allergens]
    
    risky = [a for a in user_allergens_lower if a in dish_allergens]
    
    if risky:
        return f"⚠️ Warning: {item['name']} contains {', '.join(risky)}. This dish is NOT safe for you."
    else:
        return f"✅ {item['name']} does not contain your listed allergens. However, please always confirm with staff about cross-contamination."


def make_reservation(state: SessionState, date: str, time: str, people: int) -> Tuple[SessionState, str]:
    """Make a reservation."""
    state.reservation = Reservation(date=date, time=time, people=people)
    return state, f"Reservation confirmed for {people} people on {date} at {time}."


def answer_with_rag(question: str, user_allergens: List[str]) -> str:
    """Answer questions using RAG over menu and FAQ."""
    docs = RETRIEVER.invoke(question)
    
    if not docs:
        return "I'm sorry, I couldn't find relevant information. Please ask about our menu, allergens, or policies."
    
    # Build context from retrieved documents
    context_parts = []
    for doc in docs:
        context_parts.append(doc.page_content)
    
    context = "\n".join(context_parts)
    
    # Simple response (in production, you'd use LLM here with Ollama)
    response = f"Based on our menu and policies:\n\n{context[:500]}"
    
    # Add allergen warning if relevant
    if user_allergens and any("allergen" in doc.page_content.lower() for doc in docs):
        response += f"\n\n⚠️ Note: You have indicated allergies to {', '.join(user_allergens)}. Please always inform staff when ordering."
    
    return response


def get_order_summary(state: SessionState) -> str:
    """Get formatted order summary."""
    if not state.current_order:
        return "Your order is currently empty."
    
    lines = ["Your current order:"]
    for item in state.current_order:
        line_total = item.price * item.quantity
        lines.append(f"  • {item.quantity}x {item.name} - €{line_total:.2f}")
    
    lines.append(f"\nSubtotal: €{state.current_total:.2f}")
    vat = state.current_total * 0.12
    total = state.current_total + vat
    lines.append(f"VAT (12%): €{vat:.2f}")
    lines.append(f"Total: €{total:.2f}")
    
    return "\n".join(lines)
