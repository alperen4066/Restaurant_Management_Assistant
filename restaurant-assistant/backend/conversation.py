"""
Advanced conversational AI that understands context and responds naturally.
"""


def get_context_aware_response(user_message: str, state, last_action: str = None) -> str:
    """Generate contextually aware responses."""
    
    text = user_message.lower()
    
    # Restaurant hours
    if any(w in text for w in ["open", "hours", "time", "when", "available"]):
        if "reservation" in text or state.reservation or last_action == "reservation":
            return """We're open every day from **11:00 AM to 10:00 PM**.

For reservations:
• **Lunch**: 11:00 AM - 3:00 PM
• **Dinner**: 5:00 PM - 10:00 PM

What date and time works best for you? (Format: 'Book for [X] people on YYYY-MM-DD at HH:MM')"""
        else:
            return "We're open daily from **11:00 AM to 10:00 PM**. Would you like to make a reservation or see our menu?"
    
    # After order completion
    if last_action == "ordered" and any(w in text for w in ["anything else", "more", "also"]):
        return "Absolutely! Would you like to:\n• Add dessert or drinks?\n• Make a reservation?\n• See the menu again?\n\nJust let me know!"
    
    # Price inquiries
    if any(w in text for w in ["price", "cost", "how much", "expensive"]):
        return "Our dishes range from €5 (drinks) to €32 (premium steak). Most main courses are €15-25. Would you like to see the full menu with prices?"
    
    # Payment/payment methods
    if any(w in text for w in ["payment", "pay", "credit card", "cash"]):
        return "We accept:\n• Credit/Debit cards 💳\n• Cash 💵\n• Mobile payments 📱\n\nYou can pay when you receive your order or at the restaurant. Would you like to proceed with checkout?"
    
    # Delivery
    if "delivery" in text or "deliver" in text:
        return "Yes, we offer delivery! Once you complete your order, we'll send you the bill and delivery details via email. The delivery fee is €3.50 and takes about 30-45 minutes."
    
    # Dietary preferences
    if "gluten free" in text or "gluten-free" in text:
        return "We have several gluten-free options! Check out:\n• Mediterranean Grilled Salmon\n• Vegan Buddha Bowl\n• Quinoa Stuffed Bell Peppers\n\nSay 'show menu' to see all dishes with allergen info."
    
    if "vegetarian" in text:
        return "Great choice! We have delicious vegetarian options:\n• Vegan Buddha Bowl (€17.00)\n• Quinoa Stuffed Bell Peppers (€15.50)\n• Classic Margherita Pizza (€16.50)\n\nAll are marked ✅ on the menu. Would you like to order?"
    
    # Generic fallback
    return None  # Let other handlers deal with it
