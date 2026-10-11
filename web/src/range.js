// "Look back" choices: how far back in the mailbox to read, as a YYYY-MM-DD start date.
export const PRESETS = [
  { id: "signup", label: "Since I signed up" },
  { id: "1w", label: "Last week" },
  { id: "2w", label: "Last 2 weeks" },
  { id: "1m", label: "Last month" },
  { id: "3m", label: "Last quarter (3 months)" },
  { id: "6m", label: "Last 6 months" },
  { id: "1y", label: "Last year" },
  { id: "all", label: "All time" },
  { id: "custom", label: "Custom date…" },
];

const iso = (d) => {
  const z = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
  return z.toISOString().slice(0, 10);
};

function daysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return iso(d);
}

function monthsAgo(n) {
  const d = new Date();
  d.setMonth(d.getMonth() - n);
  return iso(d);
}

export function sinceFor(choice, custom, memberSince) {
  switch (choice) {
    case "signup": return memberSince || iso(new Date());
    case "1w": return daysAgo(7);
    case "2w": return daysAgo(14);
    case "1m": return monthsAgo(1);
    case "3m": return monthsAgo(3);
    case "6m": return monthsAgo(6);
    case "1y": return monthsAgo(12);
    case "all": return "2004-01-01";
    case "custom": return custom && custom <= iso(new Date()) ? custom : monthsAgo(6);
    default: return monthsAgo(6);
  }
}

export function loadRange() {
  try {
    const r = JSON.parse(localStorage.getItem("jt-range") || "null");
    if (r && PRESETS.some((p) => p.id === r.choice)) return r;
  } catch { /* storage unavailable */ }
  return { choice: "6m", custom: "" };
}

export function saveRange(r) {
  try { localStorage.setItem("jt-range", JSON.stringify(r)); } catch { /* ignore */ }
}
