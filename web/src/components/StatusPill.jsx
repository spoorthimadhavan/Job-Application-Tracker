import { STATUS } from "../status.js";

export default function StatusPill({ status }) {
  const s = STATUS[status] || STATUS.U;
  return <span className={`pill p-${s.color}`}><i className="dot" aria-hidden="true" />{s.label}</span>;
}
