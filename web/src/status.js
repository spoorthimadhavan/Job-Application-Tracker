export const STATUS = {
  S: { label: "Selected", tile: "Selected", color: "sel" },
  R: { label: "Rejected", tile: "Rejected", color: "rej" },
  I: { label: "Rejected after interview", tile: "Rejected after interview", color: "int" },
  N: { label: "Rejected, no response", tile: "Rejected, no response (6–8 weeks)", color: "nor" },
  U: { label: "Under review", tile: "Under review", color: "und" },
  A: { label: "Applied", tile: "Applied (up to 6 weeks)", color: "app" },
  C: { label: "Account created, not applied", tile: "Account created and not applied", color: "wit" },
};

export const TILE_ORDER = ["S", "R", "I", "N", "U", "A", "C"];

export function formatDate(iso) {
  return new Date(iso + "T12:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
