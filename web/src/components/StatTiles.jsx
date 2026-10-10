import { STATUS, TILE_ORDER } from "../status.js";

export default function StatTiles({ counts, total, active, onPick }) {
  return (
    <div className="stats">
      <button className="stat" aria-pressed={active === "all"} onClick={() => onPick(active)}>
        <b>{total}</b><span>All</span>
      </button>
      {TILE_ORDER.map((k) => (
        <button key={k} className={`stat c-${STATUS[k].color}`} aria-pressed={active === k} onClick={() => onPick(k)}>
          <b>{counts[k] || 0}</b><span>{STATUS[k].tile}</span>
        </button>
      ))}
    </div>
  );
}
