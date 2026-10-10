export const apps = [
  { id: "1", company: "Wide World", role: "Platform Engineer", status: "S", date: "2026-10-07", note: "Interview or next-step invite.", check: true, source: "email", events: [{ status: "S", date: "2026-10-07", subject: "Interview invitation", message_id: "m1", source: "email" }] },
  { id: "2", company: "Contoso", role: "Frontend Developer", status: "R", date: "2026-09-20", note: "LinkedIn rejection email.", check: false, source: "linkedin", events: [{ status: "R", date: "2026-09-20", subject: "Your application to Frontend Developer at Contoso", message_id: "m2", source: "linkedin" }] },
  { id: "3", company: "Northwind Labs", role: "LinkedIn application", status: "A", date: "2026-10-05", note: "LinkedIn.", check: false, source: "linkedin", events: [{ status: "A", date: "2026-10-05", subject: "sent", message_id: "m3", source: "linkedin" }] },
  { id: "4", company: "Tailspin Toys", role: "LinkedIn application", status: "N", date: "2026-08-01", note: "No response after more than 6 weeks.", check: false, source: "linkedin", events: [{ status: "N", date: "2026-08-01", subject: "sent", message_id: "m4", source: "linkedin" }] },
];

export const counts = { S: 1, R: 1, A: 1, N: 1 };
