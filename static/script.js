const form = document.getElementById("chat-form");
const questionBox = document.getElementById("question");
const messages = document.getElementById("messages");
const statusBox = document.getElementById("status");
const sendButton = document.getElementById("send");

function addMessage(role, text, data = null) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  const title = document.createElement("strong");
  title.textContent = role === "user" ? "You" : "HR Assistant";
  article.appendChild(title);
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  article.appendChild(paragraph);
  if (data?.escalated) {
    const escalation = document.createElement("div");
    escalation.className = "label escalation";
    escalation.textContent = `Escalation: ${data.escalation_reason || "HR review required"}`;
    article.appendChild(escalation);
  }
  if (data?.sources?.length) {
    const sourceBox = document.createElement("div");
    sourceBox.className = "source";
    const heading = document.createElement("strong");
    heading.textContent = "Retrieved sources";
    sourceBox.appendChild(heading);
    data.sources.forEach((source) => {
      const item = document.createElement("p");
      item.textContent = `${source.filename} · similarity ${source.score}\n${source.excerpt}`;
      sourceBox.appendChild(item);
    });
    article.appendChild(sourceBox);
  }
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionBox.value.trim();
  if (!question) return;
  addMessage("user", question);
  questionBox.value = "";
  sendButton.disabled = true;
  statusBox.textContent = "Retrieving policy text and preparing response…";
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed");
    addMessage("assistant", data.answer, data);
    statusBox.textContent = data.mode === "ollama" ? "Answered using local Ollama." : "No model call made; HR escalation returned.";
  } catch (error) {
    addMessage("assistant", `Could not process the question: ${error.message}`);
    statusBox.textContent = "Check the Flask terminal and Ollama service.";
  } finally {
    sendButton.disabled = false;
    questionBox.focus();
  }
});

document.getElementById("health").addEventListener("click", async () => {
  statusBox.textContent = "Checking local Ollama…";
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    statusBox.textContent = data.ok
      ? `Ollama reachable. Configured model: ${data.model}. Installed models: ${data.installed_models.join(", ") || "none listed"}`
      : `Ollama unavailable: ${data.error || "unknown error"}`;
  } catch (error) {
    statusBox.textContent = `Health check failed: ${error.message}`;
  }
});
