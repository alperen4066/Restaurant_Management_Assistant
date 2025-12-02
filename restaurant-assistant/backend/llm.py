import requests
import json
from typing import Optional, List, Dict
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3:mini"


def call_ollama(prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 200) -> str:
    """Call Ollama with optimized settings."""
    
    if system_prompt:
        full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
    else:
        full_prompt = prompt
    
    payload = {
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.8,
            "num_predict": max_tokens,
            "num_ctx": 3072,
            "top_p": 0.9,
        }
    }
    
    try:
        print(f"🤖 Calling Ollama...")
        response = requests.post(OLLAMA_URL, json=payload, timeout=25)
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", "").strip()
            print(f"✅ Response: {len(answer)} chars")
            return answer
        else:
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def generate_menu_response(menu_items: List[Dict], user_allergens: List[str] = None) -> str:
    categories = {
        "🍝 Main Courses": [],
        "🥗 Vegetarian & Vegan": [],
        "🍰 Desserts": [],
        "🍹 Beverages": []
    }

    for item in menu_items:
        if item["id"].startswith("m"):
            categories["🍝 Main Courses"].append(item)
        elif item["id"].startswith("v"):
            categories["🥗 Vegetarian & Vegan"].append(item)
        elif item["id"].startswith("dr"):
            categories["🍹 Beverages"].append(item)    
        elif item["id"].startswith("d"):
            categories["🍰 Desserts"].append(item)
        

    parts: list[str] = []
    parts.append("🍽️ <b>OUR RESTAURANT MENU</b><br>")

    if user_allergens:
        parts.append(f"⚠️ <b>Your Allergies:</b> {', '.join(user_allergens)}<br><br>")

    for category, items in categories.items():
        if not items:
            continue

        parts.append(f"{category}:<br>")  # category header

        for idx, item in enumerate(items, start=1):
            item_allergens = item.get("allergens", [])
            allergen_text = ", ".join(item_allergens) if item_allergens else "none"

            safe_marker = ""
            if user_allergens:
                lower = [a.lower() for a in item_allergens]
                matching = [a for a in user_allergens if a.lower() in lower]
                if matching:
                    safe_marker = f" ⚠️ Contains: {', '.join(matching)}"
                else:
                    safe_marker = " ✅ Safe for you"

            parts.append(
                f"{idx}. <b>{item['name']}</b>{safe_marker}<br>"
                f"&nbsp;&nbsp;💰 €{item['price']:.2f}<br>"
                f"&nbsp;&nbsp;📝 {item['description']}<br>"
                f"&nbsp;&nbsp;🚨 Allergens: {allergen_text}<br><br>"
            )

    parts.append("💬 To order: say 'I want [dish name]' or 'Add 2 [dish name]'")

    return "".join(parts)


def extract_order_intent_ai(user_message: str, menu_items: List[Dict]) -> Dict:
    """Smart order extraction with fuzzy matching."""
    
    text = user_message.lower()
    
    # Extract quantity
    quantity = 1
    qty_match = re.search(r'(\d+)\s*(x|pieces?|orders?|glass|glasses)?', text)
    if qty_match:
        quantity = int(qty_match.group(1))
    
    # Clean text
    clean_text = text
    for word in ["add", "order", "want", "get", "i'll have", "i want", "give me", "wanna", "i'd like", "please", "for me"]:
        clean_text = clean_text.replace(word, " ")
    clean_text = re.sub(r'\d+\s*(x|pieces?|orders?|glass|glasses)?', '', clean_text).strip()
    
    # Exact and fuzzy matching
    best_match = None
    best_score = 0
    
    for item in menu_items:
        item_name_lower = item["name"].lower()
        
        # Exact match
        if clean_text == item_name_lower:
            return {"dish": item["name"], "quantity": quantity}
        
        # Contains match
        if clean_text in item_name_lower or item_name_lower in clean_text:
            score = max(len(clean_text), len(item_name_lower))
            if score > best_score:
                best_score = score
                best_match = item["name"]
        
        # Word overlap
        item_words = set([w for w in item_name_lower.split() if len(w) > 3])
        text_words = set([w for w in clean_text.split() if len(w) > 3])
        common = item_words & text_words
        
        if common and len(common) > 0:
            score = len(common) * 20
            if score > best_score:
                best_score = score
                best_match = item["name"]
    
    return {"dish": best_match, "quantity": quantity}


def extract_allergens_ai(user_message: str) -> List[str]:
    """Extract allergens from user message."""
    
    text = user_message.lower()
    common = ["milk", "dairy", "eggs", "fish", "shellfish", "nuts", "peanuts", "wheat", "gluten", "soy", "sesame", "sulfites"]
    
    found = set()
    for allergen in common:
        if allergen in text:
            found.add(allergen)
            if allergen == "dairy":
                found.add("milk")
    
    return list(found)


def recommend_dishes_ai(menu_items: List[Dict], user_allergens: List[str] = None, user_preference: str = "") -> str:
    """Smart recommendations based on context."""
    
    text = user_preference.lower()
    
    # Filter safe dishes
    safe_dishes = []
    for item in menu_items:
        if user_allergens:
            item_allergens = [a.lower() for a in item["allergens"]]
            if not any(ua.lower() in item_allergens for ua in user_allergens):
                safe_dishes.append(item)
        else:
            safe_dishes.append(item)
    
    # Context-based recommendations
    if any(w in text for w in ["vegetarian", "vegan", "plant"]):
        recs = [item for item in safe_dishes if item["id"].startswith("v")][:3]
        category_emoji = "🥗"
        title = "**Vegetarian & Vegan Recommendations**"
    elif any(w in text for w in ["dessert", "sweet", "cake", "chocolate"]):
        recs = [item for item in safe_dishes if item["id"].startswith("d")][:3]
        category_emoji = "🍰"
        title = "**Dessert Recommendations**"
    elif any(w in text for w in ["drink", "beverage", "wine", "beer", "juice"]):
        recs = [item for item in safe_dishes if item["id"].startswith("dr")][:3]
        category_emoji = "🍹"
        title = "**Beverage Recommendations**"
    else:
        # Popular main dishes
        popular_ids = ["m3", "m1", "v1"]
        recs = [item for item in safe_dishes if item["id"] in popular_ids][:3]
        category_emoji = "✨"
        title = "**Most Popular Dishes**"
    
    if not recs:
        recs = safe_dishes[:3]
    
    lines = [category_emoji + " " + title + "\n"]
    
    for idx, item in enumerate(recs, 1):
        safe_note = ""
        if user_allergens:
            safe_note = " ✅"
        
        lines.append(f"**{idx}. {item['name']}** - €{item['price']:.2f}{safe_note}")
        lines.append(f"   _{item['description']}_\n")
    
    lines.append("💬 Would you like to order any of these?")
    
    return "\n".join(lines)


def generate_smart_response_ai(user_message: str, context: Dict, conversation_history: List = None) -> str:
    """Context-aware conversation with memory."""
    
    text = user_message.lower()
    
    # Build conversation context
    history_text = ""
    if conversation_history and len(conversation_history) > 0:
        recent = conversation_history[-4:]  # Last 2 exchanges
        history_text = "\nRecent conversation:\n"
        for msg in recent:
            role = msg.get("role", "")
            content = msg.get("content", "")[:100]
            history_text += f"{role}: {content}\n"
    
    # Quick pattern responses
    if any(w in text for w in ["hello", "hi", "hey"]):
        return "Hello! 👋 Welcome to our restaurant. Would you like to see our menu or place an order?"
    
    if "help" in text and len(text) < 10:
        return """I can help with:
• 🍽️ **Show menu** - See all our dishes
• 🛒 **Order food** - Add items to your order
• ⚠️ **Check allergens** - Food safety information
• 📅 **Make reservations** - Book a table
• 💰 **Get bill** - Checkout and pay

What would you like?"""
    
    if "thank" in text:
        return "You're very welcome! 😊 Anything else I can help with?"
    
    # Build AI context
    order_info = ""
    if context.get('order') and len(context['order']) > 0:
        items = [f"{item.quantity}x {item.name}" for item in context['order']]
        order_info = f"Current order: {', '.join(items)} (€{context.get('total', 0):.2f}). "
    
    allergen_info = ""
    if context.get('allergens'):
        allergen_info = f"Customer allergies: {', '.join(context['allergens'])}. "
    
    # Use AI for complex queries
    system_prompt = f"""You are a professional restaurant assistant. Be warm, helpful, and concise (2-3 sentences).

Context: {order_info}{allergen_info}
{history_text}

Guidelines:
- Answer the customer's question directly
- Suggest relevant next steps
- Be enthusiastic about our food
- Prioritize allergen safety"""
    
    ai_response = call_ollama(user_message, system_prompt, 180)
    
    if ai_response and len(ai_response) > 20:
        # Clean up response
        ai_response = ai_response.replace("Customer said:", "").replace("User:", "").strip()
        return ai_response
    
    # Fallback
    return "I'm here to help! Would you like to see the menu, order food, or make a reservation?"


def check_allergen_safety_ai(dish_name: str, dish_allergens: List[str], user_allergens: List[str]) -> str:
    """Professional allergen safety check."""
    
    dish_a = [a.lower() for a in dish_allergens]
    user_a = [a.lower() for a in user_allergens]
    
    dangerous = [a for a in user_a if a in dish_a]
    
    if dangerous:
        return f"""⚠️  **ALLERGEN WARNING**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**{dish_name}** contains allergens that you're sensitive to:
🚨 **{', '.join(dangerous).upper()}**

❌ **This dish is NOT SAFE for you.**

Please choose another option from our menu."""
    else:
        return f"""✅  **SAFE FOR YOUR ALLERGIES**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**{dish_name}** does not contain:
{', '.join(user_allergens)}

💚 **This dish should be safe for you.**

However, please always inform our staff about your allergies to prevent cross-contamination."""
