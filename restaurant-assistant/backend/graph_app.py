from backend.models import SessionState, Reservation
from backend.agents import (
    add_item_to_order,
    remove_item_from_order,
    set_allergens,
    load_menu
)
from backend.llm import (
    generate_menu_response,
    extract_order_intent_ai,
    extract_allergens_ai,
    generate_smart_response_ai,
    check_allergen_safety_ai,
    recommend_dishes_ai,
    call_ollama,
)
from backend.email_service import send_bill_email, send_reservation_confirmation
import re


def detect_intent(user_message: str, state: SessionState) -> str:
    """Advanced intent detection with context."""
    text = user_message.lower().strip()

    # Clear whole order – BEFORE generic remove
    if any(p in text for p in [
        "delete my order", "delete order", "clear order",
        "remove all", "cancel order", "empty basket", "empty my order"
    ]):
        return "clear_order"

    # Negative order like "i don't want X anymore" → remove
    if any(p in text for p in ["don't want", "dont want", "no longer want", "i dont want"]):
        return "remove"

    # Ingredients questions
    if "ingredient" in text:
        return "ingredients"

    # Reservation status questions
    if any(p in text for p in [
        "do i have a reservation", "do i have reservation",
        "my reservation", "any reservation for me"
    ]):
        return "reservation_status"

    # Exit phrases
    if text in ["no", "nope", "nah", "nothing", "that's all", "nothing else", "no thanks"]:
        return "goodbye"

    # Yes/affirmative
    if text in ["yes", "yeah", "yep", "sure", "ok", "okay", "please", "yes please"]:
        if state.last_question == "need_reservation_details":
            return "reservation_followup"
        return "affirmative"

    # Dish information – avoid "what's the best..." questions
    if (("what is" in text) or ("what's the" in text)) and "best" not in text:
        return "dish_info"

    # Show current order
    if any(phrase in text for phrase in [
        "show order", "show my order", "my order", "current order",
        "what did i order", "what's in my order", "check my order"
    ]):
        return "show_order"

    # Recommendations (with context)
    if any(w in text for w in [
        "recommend", "suggest", "best", "popular",
        "good", "which", "legendary", "favorite", "favourite"
    ]):
        if any(w in text for w in ["drink", "wine", "beer", "beverage", "juice"]):
            return "recommend_drinks"
        if any(phrase in text for phrase in ["for my", "with my", "suit", "pair", "goes with", "match"]):
            return "recommend_pairing"
        return "recommend"

    # Drink-specific queries
    if any(w in text for w in ["drink", "wine", "beer", "beverage", "juice", "water"]) and \
            any(w in text for w in ["have", "any", "do you", "is there", "what"]):
        return "show_drinks"

    # Order with numbers
    if re.search(r'\d+', text) and any(w in text for w in ["want", "order", "add", "get", "wanna"]):
        return "order"

    has_reservation = any(w in text for w in ["book", "reserve", "reservation", "table"])
    has_order = any(w in text for w in ["want", "order", "add", "get", "wanna"])

    # Multi-intent: order + reservation
    if has_reservation and has_order:
        return "order_with_reservation"

    # Menu
    if any(w in text for w in ["menu", "show me", "what do you have", "see menu", "see your menu"]):
        return "show_menu"

    # Bill/checkout
    if any(phrase in text for phrase in [
        "bill", "pay", "checkout", "check out", "finish", "done", "get bill", "invoice"
    ]):
        return "bill"

    # Order
    if has_order or any(phrase in text for phrase in ["i'll have", "give me", "can i", "i would like", "i'd like"]):
        return "order"

    # Remove single item
    if any(w in text for w in ["remove", "delete", "cancel", "take off"]):
        return "remove"

    # Allergen – only if explicit allergy words appear
    if any(w in text for w in ["allergic", "allergy", "allergen"]) \
       or "allergy to" in text or "allergic to" in text:
        return "allergen"

    # Reservation
    if has_reservation:
        return "reservation"

    # Availability query
    if any(phrase in text for phrase in ["available", "when", "which day", "what day", "what time"]):
        if has_reservation or "reservation" in state.last_question:
            return "reservation_info"

    return "chat"


def _ollama_recommendation_answer(user_message: str, state: SessionState, menu) -> str:
    """Use Ollama to answer recommendation/opinion-style questions."""
    order_summary = ""
    if state.current_order:
        items = [f"{i.quantity}x {i.name}" for i in state.current_order]
        order_summary = "Current order: " + ", ".join(items) + "."

    allergens = ""
    if state.allergens:
        allergens = "Customer allergies: " + ", ".join(state.allergens) + "."

    top_dishes = ", ".join([m["name"] for m in menu[:8]])

    system_prompt = (
        "You are a professional, friendly restaurant assistant. "
        "Use only the dishes and prices from the provided menu context. "
        "Never invent new dishes or prices. Answer in 2–3 sentences."
    )

    prompt = (
        f"{allergens} {order_summary}\n\n"
        f"Menu dishes: {top_dishes}.\n\n"
        f"Customer question: {user_message}"
    )

    resp = call_ollama(prompt, system_prompt=system_prompt, max_tokens=180)
    return resp or "Based on your preferences, any of our popular dishes would be a great choice."


def run_turn(state: SessionState, user_message: str, user_email: str = None) -> tuple:
    """Professional conversation handler with full context."""
    intent = detect_intent(user_message, state)
    menu = load_menu()

    context = {
        "order": state.current_order,
        "allergens": state.allergens,
        "total": state.current_total
    }

    print(f"🎯 Intent: {intent}")

    # Handle intents
    if intent == "goodbye":
        answer = "Thank you for visiting! Have a wonderful day! 😊 We look forward to serving you again soon."
        state.history.append({"role": "user", "content": user_message})
        state.history.append({"role": "assistant", "content": answer})
        return state, answer

    elif intent == "affirmative":
        if state.last_question == "offer_drinks":
            answer = show_beverages_menu(menu, state.allergens)
        elif state.last_question == "confirm_order":
            answer = generate_menu_response(menu, state.allergens)
        else:
            answer = "Great! How else can I help you? Would you like to see our menu, place an order, or make a reservation?"
        state.last_question = None

    elif intent == "dish_info":
        order_data = extract_order_intent_ai(user_message, menu)

        if order_data.get("dish"):
            dish_item = next((item for item in menu if item["name"] == order_data["dish"]), None)

            if dish_item:
                safe_note = ""
                if state.allergens:
                    item_allergens = [a.lower() for a in dish_item["allergens"]]
                    matching = [a for a in state.allergens if a.lower() in item_allergens]
                    if matching:
                        safe_note = f"\n\n⚠️ **Warning:** Contains {', '.join(matching)} - NOT safe for you!"
                    else:
                        safe_note = "\n\n✅ **Safe for your allergies!**"

                allergen_list = ", ".join(dish_item["allergens"]) if dish_item["allergens"] else "None"

                answer = f"""**{dish_item['name']}** - €{dish_item['price']:.2f}

📝 {dish_item['description']}

🚨 **Allergens:** {allergen_list}{safe_note}

💬 Would you like to order this dish?"""
            else:
                answer = "I couldn't find that dish on our menu. Would you like to see the full menu?"
        else:
            answer = "Which dish would you like to know about? You can say the dish name or see the full menu."

        state.last_question = None

    elif intent == "show_menu":
        answer = generate_menu_response(menu, state.allergens)
        state.last_question = None

    elif intent == "show_drinks":
        answer = show_beverages_menu(menu, state.allergens)
        state.last_question = None

    elif intent == "recommend":
        safe_text = recommend_dishes_ai(menu, state.allergens, user_message)
        ollama_answer = _ollama_recommendation_answer(
            user_message + " (system suggestion: " + safe_text.replace("\n", " ") + ")",
            state,
            menu,
        )
        answer = ollama_answer
        state.last_question = None

    elif intent == "recommend_drinks":
        drinks_text = show_beverages_menu(menu, state.allergens)
        ollama_answer = _ollama_recommendation_answer(
            user_message + " (available drinks: " + drinks_text.replace("\n", " ") + ")",
            state,
            menu,
        )
        answer = ollama_answer
        state.last_question = "offer_drinks"

    elif intent == "recommend_pairing":
        base = "Recommend a drink that pairs well with the customer's current order."
        ollama_answer = _ollama_recommendation_answer(
            base + " " + user_message,
            state,
            menu,
        )
        answer = ollama_answer
        state.last_question = "offer_drinks"

    elif intent == "order_with_reservation":
        order_data = extract_order_intent_ai(user_message, menu)

        if order_data.get("dish"):
            quantity = order_data.get("quantity", 1)
            state, order_msg = add_item_to_order(state, order_data["dish"], quantity)
            answer = f"""{order_msg}

📅 **Reservation Noted!**

When would you like to dine with us?
Format: 'Book for [X] people on YYYY-MM-DD at HH:MM'

Example: 'Book for 4 people on 2025-12-15 at 19:00'"""
            state.last_question = "need_reservation_details"
        else:
            answer = "I'd love to help with your order and reservation! What would you like to order?"

    elif intent == "order":
        order_data = extract_order_intent_ai(user_message, menu)

        if order_data.get("dish"):
            quantity = order_data.get("quantity", 1)
            state, answer = add_item_to_order(state, order_data["dish"], quantity)

            if any(item.name.startswith("Mediterranean") or item.name.startswith("Truffle")
                   for item in state.current_order):
                if not any("Wine" in item.name or "Juice" in item.name for item in state.current_order):
                    answer += "\n\n🍷 Would you like to add a beverage? (wine, juice, or water)"
                    state.last_question = "offer_drinks"
        else:
            answer = "I couldn't find that dish. Could you try again or see the menu?"

    elif intent == "remove":
        order_data = extract_order_intent_ai(user_message, menu)
        if order_data.get("dish"):
            state, answer = remove_item_from_order(state, order_data["dish"])
        else:
            if len(state.current_order) == 1:
                only_item = state.current_order[0]
                state, answer = remove_item_from_order(state, only_item.name)
            elif state.current_order:
                answer = "Which dish would you like to remove?\n\n" + get_order_summary(state)
            else:
                answer = "Your order is empty."
        state.last_question = None

    elif intent == "clear_order":
        state.current_order = []
        state.current_total = 0.0
        answer = "Your order has been cleared. Would you like to see the menu again or start a new order?"
        state.last_question = None

    elif intent == "ingredients":
        order_data = extract_order_intent_ai(user_message, menu)
        if order_data.get("dish"):
            answer = get_dish_ingredients(menu, order_data["dish"])
        else:
            answer = "Which dish would you like the ingredients for?"
        state.last_question = None

    elif intent == "allergen":
        if any(word in user_message.lower() for word in [
            "i am allergic", "i'm allergic", "allergic to", "i have", "allergy to"
        ]):
            allergens = extract_allergens_ai(user_message)

            if allergens:
                state, answer = set_allergens(state, allergens)
                answer += "\n\n✅ I'll mark safe options when showing the menu.\n\nWould you like to see it now?"
            else:
                answer = "Please tell me which allergens you have.\n\nExample: 'I'm allergic to milk and peanuts'"
        else:
            order_data = extract_order_intent_ai(user_message, menu)

            if order_data.get("dish"):
                dish_item = next((item for item in menu if item["name"] == order_data["dish"]), None)

                if dish_item and state.allergens:
                    answer = check_allergen_safety_ai(
                        dish_item["name"],
                        dish_item.get("allergens", []),
                        state.allergens
                    )
                elif dish_item:
                    allergen_list = ", ".join(dish_item.get("allergens", [])) or "none"
                    answer = f"The listed allergens for {dish_item['name']} are: {allergen_list}."
                else:
                    answer = "I couldn't find that dish."
            else:
                if state.allergens:
                    answer = f"Your allergies: **{', '.join(state.allergens)}**\n\nWhich dish should I check?"
                else:
                    answer = "Please tell me your allergens first."

        state.last_question = None

    elif intent == "reservation_status":
        if state.reservation:
            answer = (
                f"You have a reservation for {state.reservation.people} people "
                f"on {state.reservation.date} at {state.reservation.time}."
            )
            if state.current_order:
                answer += " Your current pre-order is linked to this reservation."
        else:
            answer = "There is no reservation on file yet. Would you like to book a table?"
        state.last_question = None

    elif intent == "reservation" or intent == "reservation_info":
        if "available" in user_message.lower() or "which day" in user_message.lower():
            answer = """📅 **Reservation Information**

We're open **every day**:
• 🌅 Lunch: 11:00 AM - 3:00 PM
• 🌆 Dinner: 5:00 PM - 10:00 PM

To book a table, please provide:
• Date (YYYY-MM-DD)
• Time (HH:MM)
• Number of people

**Example:** 'Book for 4 people on 2025-12-15 at 19:00'"""
            state.last_question = "need_reservation_details"
        else:
            date_match = re.search(r'\d{4}-\d{2}-\d{2}|(\d{1,2})/(\d{1,2})/(\d{4})', user_message)
            time_match = re.search(r'\d{1,2}:\d{2}', user_message)
            people_match = re.search(r'(\d+)\s*people|for (\d+)', user_message.lower())

            if date_match and time_match and people_match:
                if date_match.group(1):  # MM/DD/YYYY format
                    date = f"{date_match.group(3)}-{date_match.group(1).zfill(2)}-{date_match.group(2).zfill(2)}"
                else:
                    date = date_match.group(0)

                time = time_match.group(0)
                people = int(people_match.group(1) or people_match.group(2))

                has_preorder = len(state.current_order) > 0
                state.reservation = Reservation(date=date, time=time, people=people, has_preorder=has_preorder)

                if user_email and has_preorder:
                    send_reservation_confirmation(
                        user_email, {"date": date, "time": time, "people": people}, state.current_order
                    )

                    order_summary = ", ".join([f"{item.quantity}x {item.name}" for item in state.current_order])
                    answer = f"""✅ **Reservation Confirmed!**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 **Date:** {date}
🕐 **Time:** {time}
👥 **Party Size:** {people} people

🍽️ **Pre-Order:**
{order_summary}

📧 Confirmation sent to **{user_email}**

We look forward to serving you! 😊"""
                elif user_email:
                    send_reservation_confirmation(user_email, {"date": date, "time": time, "people": people})
                    answer = f"""✅ **Reservation Confirmed!**

📅 {date} at {time} for {people} people
📧 Confirmation sent to {user_email}

See you soon! 😊"""
                else:
                    answer = f"✅ Reservation noted for {people} people on {date} at {time}.\n\nPlease enter your email above for confirmation."

                state.last_question = None
            else:
                answer = """To book a table, please provide:
• **Date** (YYYY-MM-DD or MM/DD/YYYY)
• **Time** (HH:MM)
• **Number of people**

**Example:** 'Book for 4 people on 2025-12-15 at 19:00'"""
                state.last_question = "need_reservation_details"

    elif intent == "show_order":
        if state.current_order:
            answer = get_order_summary(state)

            if state.reservation:
                answer += (
                    f"\n\n📅 **Reservation:** {state.reservation.people} "
                    f"people on {state.reservation.date} at {state.reservation.time}"
                )

            answer += "\n\n💡 Ready to checkout? Say 'bill' or 'checkout'"
        else:
            answer = "Your order is empty. Would you like to see our menu?"

        state.last_question = None

    elif intent == "bill":
        if not state.current_order:
            answer = "Your order is empty. Would you like to order something delicious?"
        elif not user_email:
            answer = f"{get_order_summary(state)}\n\n📧 **Please enter your email above** to receive your bill."
        else:
            html = generate_bill_html(state)
            email_sent = send_bill_email(user_email, html)

            subtotal = state.current_total
            vat = subtotal * 0.12
            total = subtotal + vat

            if email_sent:
                answer = f"""✅ **Order Complete!**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 **Items:** {len(state.current_order)}
💰 **Subtotal:** €{subtotal:.2f}
📊 **VAT (12%):** €{vat:.2f}
💳 **Total:** €{total:.2f}

📧 Bill sent to **{user_email}**

Thank you! Enjoy your meal! 🍽️✨"""
            else:
                answer = f"⚠️ Bill ready (€{total:.2f}) but email failed. Please check your email address."

        state.last_question = None

    else:  # chat
        if any(w in user_message.lower() for w in ["legendary", "favourite", "favorite", "what do you like"]):
            answer = _ollama_recommendation_answer(user_message, state, menu)
        else:
            answer = generate_smart_response_ai(user_message, context, state.history)

    state.history.append({"role": "user", "content": user_message})
    state.history.append({"role": "assistant", "content": answer})

    return state, answer


def get_dish_ingredients(menu, name: str) -> str:
    item = next((m for m in menu if m["name"].lower() == name.lower()), None)
    if not item:
        return "I couldn't find that dish on the menu."
    ingredients = item.get("ingredients", [])
    if not ingredients:
        return f"We did not list detailed ingredients for {item['name']}, but the description is: {item['description']}."
    return f"The main ingredients in {item['name']} are: {', '.join(ingredients)}."


def show_beverages_menu(menu_items, user_allergens=None):
    """Show drinks menu professionally."""
    drinks = [item for item in menu_items if item["id"].startswith("dr")]

    lines = ["═" * 65]
    lines.append("🍹  **OUR BEVERAGES**")
    lines.append("═" * 65 + "\n")

    for item in drinks:
        safe_marker = ""
        if user_allergens:
            item_allergens = [a.lower() for a in item["allergens"]]
            if not any(ua.lower() in item_allergens for ua in user_allergens):
                safe_marker = "  ✅ **Safe**"

        lines.append(f"┌─ **{item['name']}**{safe_marker}")
        lines.append(f"│  💰 **€{item['price']:.2f}**")
        lines.append(f"│  📝 {item['description']}")
        lines.append("└" + "─" * 63 + "\n")

    lines.append("═" * 65)
    lines.append("💬 **To Order:** Say 'I want [beverage name]' or 'Add 2 wines'")
    lines.append("═" * 65)

    return "\n".join(lines)


def get_order_summary(state: SessionState) -> str:
    """Professional order summary."""
    if not state.current_order:
        return "Your order is empty."

    lines = ["═" * 65]
    lines.append("📋  **YOUR CURRENT ORDER**")
    lines.append("═" * 65 + "\n")

    for item in state.current_order:
        line_total = item.price * item.quantity
        lines.append(f"• **{item.quantity}x {item.name}**")
        lines.append(f"  €{item.price:.2f} each = €{line_total:.2f}\n")

    subtotal = state.current_total
    vat = subtotal * 0.12
    total = subtotal + vat

    lines.append("═" * 65)
    lines.append(f"💰 **Subtotal:** €{subtotal:.2f}")
    lines.append(f"📊 **VAT (12%):** €{vat:.2f}")
    lines.append(f"💳 **TOTAL:** €{total:.2f}")
    lines.append("═" * 65)

    return "\n".join(lines)


def generate_bill_html(state: SessionState) -> str:
    """Professional HTML bill."""
    rows = ""
    for item in state.current_order:
        line_total = item.price * item.quantity
        rows += (
            f"<tr><td>{item.name}</td>"
            f"<td style='text-align:center'>{item.quantity}</td>"
            f"<td style='text-align:right'>€{item.price:.2f}</td>"
            f"<td style='text-align:right'>€{line_total:.2f}</td></tr>"
        )

    subtotal = state.current_total
    vat = subtotal * 0.12
    total = subtotal + vat

    reservation_section = ""
    if state.reservation:
        reservation_section = f"""<div style='background:#e3f2fd;padding:20px;border-radius:8px;margin:20px 0;'>
<h3 style='color:#1976d2;margin:0 0 15px 0;'>📅 Your Reservation</h3>
<p style='margin:8px 0;'><strong>Date:</strong> {state.reservation.date}</p>
<p style='margin:8px 0;'><strong>Time:</strong> {state.reservation.time}</p>
<p style='margin:8px 0;'><strong>Party:</strong> {state.reservation.people} people</p>
</div>"""

    return f"""<!DOCTYPE html><html><head><style>
body{{font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:20px;background:#f5f5f5;}}
.container{{max-width:650px;margin:0 auto;background:white;padding:40px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.1);}}
h2{{color:#667eea;text-align:center;margin-bottom:30px;font-size:28px;}}
table{{width:100%;border-collapse:collapse;margin:25px 0;}}
th{{background:#667eea;color:white;padding:14px;text-align:left;font-weight:600;}}
td{{padding:12px;border-bottom:1px solid #e0e0e0;}}
.totals{{text-align:right;margin-top:25px;}}
.totals p{{margin:10px 0;font-size:17px;}}
.grand-total{{font-size:26px;font-weight:bold;color:#27ae60;margin-top:15px;}}
.footer{{text-align:center;margin-top:35px;color:#666;font-size:15px;}}
</style></head><body><div class='container'>
<h2>🍽️ AI Restaurant - Your Bill</h2>
{reservation_section}
<table><tr><th>Dish</th><th style='text-align:center;'>Qty</th><th style='text-align:right;'>Price</th><th style='text-align:right;'>Total</th></tr>{rows}</table>
<div class='totals'>
<p><strong>Subtotal:</strong> €{subtotal:.2f}</p>
<p><strong>VAT (12%):</strong> €{vat:.2f}</p>
<p class='grand-total'>Total: €{total:.2f}</p>
</div>
<div class='footer'>
<p><strong>Thank you for dining with us!</strong></p>
<p>We hope to see you again soon. 😊</p>
</div>
</div></body></html>"""
