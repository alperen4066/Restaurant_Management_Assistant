document.addEventListener("DOMContentLoaded", () => {
  // -------- Chat + assistant widget --------
  const chatDiv = document.getElementById("chat");
  const msgInput = document.getElementById("message");
  const sendBtn = document.getElementById("send");
  const emailInput = document.getElementById("email");
  const allergenInput = document.getElementById("allergens");
  const orderSummaryDiv = document.getElementById("orderItems");

  const widget = document.getElementById("assistant-widget");
  const toggleBtn = document.getElementById("assistant-toggle");
  const closeBtn = document.getElementById("assistant-close");
  const openHeroBtn = document.getElementById("open-assistant-btn");

  function openAssistant() {
    if (widget) widget.style.display = "grid";
  }

  function closeAssistant() {
    if (widget) widget.style.display = "none";
  }

  if (toggleBtn && widget) {
    toggleBtn.addEventListener("click", () => {
      const isOpen = widget.style.display === "grid";
      isOpen ? closeAssistant() : openAssistant();
    });
  }

  if (closeBtn) closeBtn.addEventListener("click", closeAssistant);
  if (openHeroBtn) openHeroBtn.addEventListener("click", openAssistant);

  // Session id
  const sessionId =
    localStorage.getItem("session_id") || Math.random().toString(36).slice(2);
  localStorage.setItem("session_id", sessionId);

  const API_URL = "http://localhost:8000";

  function addMessage(role, text) {
    if (!chatDiv) return;
    const div = document.createElement("div");
    div.className = `message ${role}`;

    if (text.includes("<") && text.includes(">")) {
      div.innerHTML = text;
    } else {
      div.textContent = text;
    }

    chatDiv.appendChild(div);
    chatDiv.scrollTop = chatDiv.scrollHeight;
  }

  function updateOrderSummary(orders, total) {
    if (!orderSummaryDiv) return;
    if (!orders || orders.length === 0) {
      orderSummaryDiv.textContent = "No items yet";
      return;
    }
    let html = "";
    orders.forEach((item) => {
      const lineTotal = item.price * item.quantity;
      html += `${item.quantity}x ${item.name} - €${lineTotal.toFixed(2)}<br>`;
    });
    html += `<strong>Total: €${total.toFixed(2)}</strong>`;
    orderSummaryDiv.innerHTML = html;
  }

  async function sendMessage() {
    if (!msgInput) return;
    const text = msgInput.value.trim();
    if (!text) return;

    addMessage("user", text);
    msgInput.value = "";

    const email = emailInput ? emailInput.value.trim() || null : null;
    const allergens = allergenInput
      ? allergenInput.value
          .split(",")
          .map((a) => a.trim())
          .filter((a) => a.length > 0)
      : [];

    const body = {
      session_id: sessionId,
      user_message: text,
      user_email: email,
      user_allergens: allergens.length ? allergens : null,
    };

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      addMessage("assistant", data.assistant_message);
      updateOrderSummary(data.current_order, data.current_total);
    } catch (error) {
      addMessage(
        "assistant",
        "Sorry, there was an error connecting to the server."
      );
      console.error(error);
    }
  }

  if (sendBtn && msgInput) {
    sendBtn.onclick = sendMessage;
    msgInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") sendMessage();
    });
  }

  // Initial greeting
  addMessage(
    "assistant",
    "Welcome! I'm your AI restaurant assistant. You can ask about our menu, order food, check for allergens, or make a reservation. How can I help you today?"
  );

  // -------- Testimonials widget --------
  const reviews = [
    {
      text: "From the moment we walked in, everything felt warm and welcoming. The tasting menu was perfectly balanced and the wine pairings were spot on.",
      name: "Sophie D.",
      details: "Anniversary dinner · March 2025",
    },
    {
      text: "Beautiful dining room, attentive but relaxed service and fantastic vegetarian options. Easily one of the best evenings we’ve had in Kortrijk.",
      name: "Jonas V.",
      details: "Local guest · February 2025",
    },
    {
      text: "We booked a table for eight and the team handled every detail flawlessly. The grilled salmon and desserts were unforgettable.",
      name: "Clara M.",
      details: "Group celebration · January 2025",
    },
  ];

  const reviewTextEl = document.getElementById("review-text");
  const reviewNameEl = document.getElementById("review-name");
  const reviewDetailsEl = document.getElementById("review-details");
  const dotEls = document.querySelectorAll(".review-dots .dot");

  let currentReviewIndex = 0;
  let reviewTimer = null;

  function renderReview(index) {
    if (!reviewTextEl || !reviewNameEl || !reviewDetailsEl) return;
    const review = reviews[index];
    reviewTextEl.textContent = `"${review.text}"`;
    reviewNameEl.textContent = review.name;
    reviewDetailsEl.textContent = review.details;
    dotEls.forEach((dot, i) =>
      dot.classList.toggle("active", i === index)
    );
  }

  function nextReview() {
    currentReviewIndex = (currentReviewIndex + 1) % reviews.length;
    renderReview(currentReviewIndex);
  }

  function startReviewRotation() {
    if (reviewTimer) clearInterval(reviewTimer);
    reviewTimer = setInterval(nextReview, 7000);
  }

  if (reviewTextEl && reviewNameEl && reviewDetailsEl && dotEls.length) {
    renderReview(currentReviewIndex);
    startReviewRotation();
    dotEls.forEach((dot) => {
      dot.addEventListener("click", () => {
        const index = Number(dot.dataset.index);
        currentReviewIndex = index;
        renderReview(index);
        startReviewRotation();
      });
    });
  }

  // -------- Mobile navigation (hamburger) --------
  const navToggle = document.getElementById("nav-toggle");
  const navMobile = document.getElementById("nav-mobile");

  if (navToggle && navMobile) {
    navToggle.addEventListener("click", () => {
      const isOpen = navMobile.style.display === "flex";
      navMobile.style.display = isOpen ? "none" : "flex";
    });

    navMobile.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        navMobile.style.display = "none";
      });
    });
  }
});
