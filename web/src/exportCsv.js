const esc = (v) => `"${String(v ?? "").replace(/"/g, '""').replace(/\s+/g, " ")}"`;

/** One line per application: what the tracker decided and which mails led to it, so it can be checked row by row. */
export function toCsv(apps) {
  const head = ["date", "company", "role", "status", "sender", "mails (newest first: date status subject)"];
  const lines = apps.map((a) =>
    [a.date, a.company, a.role, a.status, a.sender, (a.events || []).map((e) => `${e.date} ${e.status} ${e.subject}`).join(" || ")].map(esc).join(",")
  );
  return [head.map(esc).join(","), ...lines].join("\n");
}

export function downloadCsv(apps) {
  const url = URL.createObjectURL(new Blob([toCsv(apps)], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "applications.csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
