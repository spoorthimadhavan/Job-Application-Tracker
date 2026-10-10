const DEMO = Boolean(import.meta.env.VITE_DEMO);

export default function Login({ googleConfigured, failed }) {
  return (
    <main className="login">
      <h1>Job Application Tracker</h1>
      <p className="muted">
        Sign in with Google. The app reads your job emails (LinkedIn, Indeed, StepStone and company career systems) and keeps one list of every
        application and its status.
      </p>
      {failed && <p className="banner">Sign-in did not complete. Please try again.</p>}
      {DEMO ? (
        <button className="btn" onClick={() => location.reload()}>Open the demo again</button>
      ) : googleConfigured ? (
        <a className="btn" href="/api/auth/login">Sign in with Google</a>
      ) : (
        <p className="banner">Google sign-in is not set up on this server yet. Add the Google keys (see the README) or try the demo.</p>
      )}
      {!DEMO && <a className="btn ghost" href="/api/auth/demo">Try the demo</a>}
      <p className="fine">Read-only access to Gmail. Nothing is stored on the server: your session lives in an encrypted cookie.</p>
    </main>
  );
}
