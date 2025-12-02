const chatDiv = document.getElementById("chat");
const msgInput = document.getElementById("message");
const sendBtn = document.getElementById("send");
const emailInput = document.getElementById("email");
const allergenInput = document.getElementById("allergens");
const orderSummaryDiv = document.getElementById("orderItems");

// Generate or retrieve session ID
const sessionId = localStorage.getItem("session_id") || Math.random().toString(36).slice(2);
localStorage.setItem("session_id", sessionId);

// API URL
const API_URL = "http://localhost:8000";

function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    
    // Check if text contains HTML tags
    if (text.includes('<') && text.includes('>')) {
        // Render as HTML
        div.innerHTML = text;
    } else {
        // Render as plain text
        div.textContent = text;
    }
    
    chatDiv.appendChild(div);
    chatDiv.scrollTop = chatDiv.scrollHeight;
}

function updateOrderSummary(orders, total) {
    if (orders.length === 0) {
        orderSummaryDiv.textContent = "No items yet";
        return;
    }
    
    let html = "";
    orders.forEach(item => {
        const lineTotal = item.price * item.quantity;
        html += `${item.quantity}x ${item.name} - €${lineTotal.toFixed(2)}<br>`;
    });
    html += `<strong>Total: €${total.toFixed(2)}</strong>`;
    orderSummaryDiv.innerHTML = html;
}

async function sendMessage() {
    const text = msgInput.value.trim();
    if (!text) return;
    
    addMessage("user", text);
    msgInput.value = "";
    
    const email = emailInput.value.trim() || null;
    const allergens = allergenInput.value
        .split(",")
        .map(a => a.trim())
        .filter(a => a.length > 0);
    
    const body = {
        session_id: sessionId,
        user_message: text,
        user_email: email,
        user_allergens: allergens.length ? allergens : null
    };
    
    try {
        const res = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        });
        
        const data = await res.json();
        addMessage("assistant", data.assistant_message);
        updateOrderSummary(data.current_order, data.current_total);
    } catch (error) {
        addMessage("assistant", "Sorry, there was an error connecting to the server.");
        console.error(error);
    }
}

sendBtn.onclick = sendMessage;

msgInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        sendMessage();
    }
});

// Initial greeting
addMessage("assistant", "Welcome! I'm your AI restaurant assistant. You can ask about our menu, order food, check for allergens, or make a reservation. How can I help you today?");
