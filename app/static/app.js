"use strict";

const $ = (selector) => document.querySelector(selector);
const form = $("#plan-form");
const workspace = $("#workspace");
const emptyState = $("#empty-state");
const reviewPanel = $("#review-panel");
const finalBanner = $("#final-banner");
const toast = $("#toast");
let currentPlanId = localStorage.getItem("atlasPlanId");
let pollTimer = null;
let mode = "demo";

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined && text !== null) item.textContent = String(text);
  return item;
}

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 5500);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  let body;
  try { body = await response.json(); } catch { body = {}; }
  if (!response.ok) {
    const detail = body.detail;
    const message = Array.isArray(detail) ? detail.map(item => item.msg).join("; ") : (detail || `Request failed (${response.status})`);
    throw new Error(message);
  }
  return body;
}

function readableDate(value) {
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function money(value, currency = "USD") {
  try { return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(value || 0); }
  catch { return `${currency} ${Math.round(value || 0)}`; }
}

function safeSource(url, label = "Source ↗") {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (!["http:", "https:"].includes(parsed.protocol)) return null;
    const link = node("a", "source-link", label);
    link.href = parsed.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    return link;
  } catch { return null; }
}

function block(title, lines) {
  const section = node("div", "research-block");
  section.append(node("h4", "", title));
  const list = node("ul");
  for (const line of lines) list.append(node("li", "", line));
  section.append(list);
  return section;
}

function renderResearch(research) {
  const host = $("#research");
  host.replaceChildren();
  host.hidden = !research;
  if (!research) return;
  host.append(node("h3", "section-title", "A little local context"));
  const grid = node("div", "research-grid");
  const attractions = node("div", "research-block");
  attractions.append(node("h4", "", "Places & experiences"));
  if (research.attractions?.length) {
    const list = node("ul");
    for (const place of research.attractions.slice(0, 6)) {
      const entry = node("li", "", place.name + (place.area ? ` · ${place.area}` : ""));
      const source = safeSource(place.source_url);
      if (source) { entry.append(" ", source); }
      list.append(entry);
    }
    attractions.append(list);
  } else attractions.append(node("p", "", "No specific places were found."));
  grid.append(attractions);
  const weather = node("div", "research-block");
  weather.append(node("h4", "", "Weather"));
  if (research.weather?.daily?.length) {
    for (const day of research.weather.daily.slice(0, 5)) {
      weather.append(node("p", "", `${readableDate(day.date)} · ${day.low_c ?? "?"}–${day.high_c ?? "?"}°C · ${day.precipitation_probability ?? "?"}% rain chance`));
    }
  }
  weather.append(node("p", "", research.weather?.note || "Check the forecast closer to departure."));
  grid.append(weather);
  if (research.local_tips?.length) grid.append(block("Local tips", research.local_tips));
  if (research.transportation?.length) grid.append(block("Getting around", research.transportation));
  if (research.safety?.length) grid.append(block("Safety", research.safety));
  host.append(grid);
}

function timelineRow(time, title, description, source) {
  const row = node("div", "timeline-row");
  row.append(node("span", "timeline-time", time));
  const content = node("div", "timeline-content");
  content.append(node("strong", "", title));
  if (description) content.append(node("p", "", description));
  const link = safeSource(source);
  if (link) content.append(link);
  row.append(content);
  return row;
}

function renderItinerary(itinerary) {
  const host = $("#itinerary");
  host.replaceChildren();
  host.hidden = !itinerary;
  if (!itinerary) return;
  host.append(node("h3", "section-title", "Day by day"));
  const currency = itinerary.trip_summary?.currency || itinerary.budget_breakdown?.currency || $("#currency").value;
  const selector = $("#modify-day");
  selector.replaceChildren();
  for (const day of itinerary.days || []) {
    const card = node("article", "day-card");
    const head = node("div", "day-head");
    const title = node("div");
    title.append(node("span", "day-index", `DAY ${String(day.day).padStart(2, "0")}`));
    title.append(node("h4", "", day.theme));
    title.append(node("span", "day-date", readableDate(day.date)));
    head.append(title, node("span", "day-cost", `${money(day.estimated_cost, currency)} est.`));
    card.append(head);
    const events = [
      ...(day.activities || []).map(item => ({ time: item.start_time, title: item.name, description: item.description, source: item.source_url })),
      ...(day.meals || []).map(item => ({ time: item.time, title: item.suggestion, description: "Meal", source: item.source_url })),
    ].sort((a, b) => a.time.localeCompare(b.time));
    for (const item of events) card.append(timelineRow(item.time, item.title, item.description, item.source));
    if (day.notes?.length) {
      const notes = node("ul", "day-notes");
      for (const note of day.notes) notes.append(node("li", "", note));
      card.append(notes);
    }
    host.append(card);
    const option = node("option", "", `Day ${day.day} · ${readableDate(day.date)}`);
    option.value = String(day.day);
    selector.append(option);
  }
  const budget = node("div", "budget-total");
  budget.append(node("span", "", "Estimated trip total"));
  budget.append(node("strong", "", money(itinerary.budget_breakdown?.estimated_total, currency)));
  host.append(budget);
}

function describeStatus(status) {
  const descriptions = {
    researching: "Looking for ideas and putting your trip together. This may take a minute.",
    planning: "Research is in. Building a day-by-day itinerary now.",
    revising: "Applying your feedback to the itinerary.",
    awaiting_review: "Your draft is ready. Review it and choose what happens next.",
    finalized: "Approved and ready to use.",
    failed: "Planning stopped before a draft was ready. Check the service logs and try again.",
  };
  return descriptions[status] || "Preparing your plan.";
}

function draw(plan) {
  workspace.hidden = false;
  emptyState.hidden = true;
  $("#workspace-title").textContent = plan.research?.destination || $("#destination").value || "Your itinerary";
  $("#plan-id").textContent = `Plan ${plan.plan_id.slice(0, 8)}`;
  $("#status-pill").textContent = plan.status.replaceAll("_", " ");
  $("#status-pill").className = `status-pill ${plan.status}`;
  $("#status-description").textContent = plan.error || describeStatus(plan.status);
  const modeNote = $("#mode-note");
  modeNote.hidden = mode !== "demo";
  modeNote.textContent = "Demo mode uses sample activities and estimates. Add API keys to switch to live research and AI planning.";
  renderResearch(plan.research);
  renderItinerary(plan.draft_itinerary);
  reviewPanel.hidden = !plan.requires_review;
  finalBanner.hidden = plan.status !== "finalized";
}

async function loadPlan(planId) {
  window.clearTimeout(pollTimer);
  try {
    const plan = await api(`/plan/${encodeURIComponent(planId)}`);
    draw(plan);
    if (plan.status === "finalized") {
      const final = await api(`/plan/${encodeURIComponent(planId)}/final`);
      renderItinerary(final);
    }
    if (["researching", "planning", "revising"].includes(plan.status)) {
      pollTimer = window.setTimeout(() => loadPlan(planId), 1600);
    }
  } catch (error) {
    if (error.message === "Plan not found") {
      localStorage.removeItem("atlasPlanId");
      currentPlanId = null;
    }
    showToast(error.message);
  }
}

function setReviewBusy(value) {
  for (const selector of ["#approve-button", "#reject-button", "#modify-button"]) $(selector).disabled = value;
}

async function sendReview(payload) {
  if (!currentPlanId) return;
  setReviewBusy(true);
  try {
    const plan = await api(`/plan/${encodeURIComponent(currentPlanId)}/review`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    draw(plan);
    if (plan.status === "finalized") {
      const final = await api(`/plan/${encodeURIComponent(currentPlanId)}/final`);
      renderItinerary(final);
    }
    $("#reject-feedback").value = "";
    $("#modify-request").value = "";
    workspace.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showToast(error.message);
    await loadPlan(currentPlanId);
  } finally { setReviewBusy(false); }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fields = new FormData(form);
  const interests = String(fields.get("interests") || "").split(",").map(item => item.trim()).filter(Boolean);
  const payload = {
    destination: String(fields.get("destination") || "").trim(),
    start_date: fields.get("start_date"), end_date: fields.get("end_date"),
    budget_min: Number(fields.get("budget_min")), budget_max: Number(fields.get("budget_max")),
    currency: fields.get("currency"), travelers: Number(fields.get("travelers")), interests,
  };
  if (payload.end_date < payload.start_date) return showToast("End date must be on or after the start date.");
  if (payload.budget_max < payload.budget_min) return showToast("Maximum budget must be at least the minimum.");
  if (!interests.length) return showToast("Add at least one interest.");
  $("#create-button").disabled = true;
  try {
    const created = await api("/plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    currentPlanId = created.plan_id;
    localStorage.setItem("atlasPlanId", currentPlanId);
    await loadPlan(currentPlanId);
    workspace.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) { showToast(error.message); }
  finally { $("#create-button").disabled = false; }
});

$("#approve-button").addEventListener("click", () => sendReview({ action: "approve" }));
$("#reject-button").addEventListener("click", () => {
  const feedback = $("#reject-feedback").value.trim();
  if (!feedback) return showToast("Describe what you want changed in the full draft.");
  sendReview({ action: "reject", feedback });
});
$("#modify-button").addEventListener("click", () => {
  const request = $("#modify-request").value.trim();
  if (!request) return showToast("Describe the change for this day.");
  sendReview({ action: "modify", modifications: { day: Number($("#modify-day").value), request } });
});
$("#new-trip").addEventListener("click", () => {
  window.clearTimeout(pollTimer);
  currentPlanId = null;
  localStorage.removeItem("atlasPlanId");
  workspace.hidden = true;
  emptyState.hidden = false;
  $("#plan-form").scrollIntoView({ behavior: "smooth", block: "start" });
});

function setDefaultDates() {
  const start = new Date();
  start.setDate(start.getDate() + 30);
  const end = new Date(start);
  end.setDate(end.getDate() + 4);
  const asLocalDate = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  $("#start-date").value = asLocalDate(start);
  $("#end-date").value = asLocalDate(end);
}

async function boot() {
  setDefaultDates();
  try {
    const config = await api("/config");
    mode = config.mode;
    const badge = $("#mode-badge");
    badge.textContent = mode === "demo" ? "Demo mode · sample data" : "Live planning";
    badge.classList.toggle("live", mode === "live");
  } catch { $("#mode-badge").textContent = "Planner mode unavailable"; }
  if (currentPlanId) await loadPlan(currentPlanId);
}

boot();
