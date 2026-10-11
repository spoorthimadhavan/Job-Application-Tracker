import { PRESETS } from "../range.js";

export default function Toolbar({ query, onQuery, sort, onSort, range, onRange, memberSince, canDownload = false, onDownload }) {
  const today = new Date().toISOString().slice(0, 10);
  return (
    <div className="tools">
      <label className="field grow">
        <span className="lbl">Search</span>
        <input type="search" placeholder="Company or role" aria-label="Search company or role" value={query} onChange={(e) => onQuery(e.target.value)} />
      </label>
      <label className="field">
        <span className="lbl">Look back</span>
        <select aria-label="Look back" value={range.choice} onChange={(e) => onRange({ ...range, choice: e.target.value })}>
          {PRESETS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.id === "signup" && memberSince ? `Since I signed up (${memberSince})` : p.label}
            </option>
          ))}
        </select>
      </label>
      {range.choice === "custom" && (
        <input type="date" aria-label="From date" max={today} value={range.custom} onChange={(e) => onRange({ ...range, custom: e.target.value })} />
      )}
      <label className="field">
        <span className="lbl">Sort by</span>
        <select aria-label="Sort" value={sort} onChange={(e) => onSort(e.target.value)}>
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="company">Company A to Z</option>
        </select>
      </label>
      <button
        type="button"
        className="download"
        disabled={!canDownload}
        onClick={onDownload}
        title={canDownload ? "Download the list as a CSV file" : "Please wait for the list to be completely loaded"}
      >
        <span aria-hidden="true">⬇ </span>Download CSV
      </button>
      {!canDownload && <span className="hint" role="status">Loading the full list…</span>}
    </div>
  );
}
