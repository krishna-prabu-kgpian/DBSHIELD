import { useState } from 'react';
import './App.css';
import StudentPage from './pages/StudentPage';
import InstructorPage from './pages/InstructorPage';
import AdminPage from './pages/AdminPage';
import iitkgpLogo from './assets/iitkgp-logo.jpeg';
import { postJson } from './api';

const SESSION_STORAGE_KEY = 'dbshield.session';
const EMPTY_SESSION = {
  token: '',
  username: '',
  role: '',
  name: '',
};

const readStoredSession = () => {
  if (typeof window === 'undefined') {
    return EMPTY_SESSION;
  }

  try {
    const rawSession = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (!rawSession) {
      return EMPTY_SESSION;
    }

    const parsedSession = JSON.parse(rawSession);
    const role = typeof parsedSession.role === 'string' ? parsedSession.role.toLowerCase() : '';

    return {
      token: typeof parsedSession.token === 'string' ? parsedSession.token : '',
      username: typeof parsedSession.username === 'string' ? parsedSession.username : '',
      role: ['student', 'instructor', 'admin'].includes(role) ? role : '',
      name: typeof parsedSession.name === 'string' ? parsedSession.name : '',
    };
  } catch {
    return EMPTY_SESSION;
  }
};

const writeStoredSession = (session) => {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
};

const clearStoredSession = () => {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.removeItem(SESSION_STORAGE_KEY);
};

function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [session, setSession] = useState(readStoredSession);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus('');

    const trimmedUsername = username.trim();

    if (!trimmedUsername || !password) {
      setStatus('Please enter both username and password.');
      return;
    }

    try {
      setIsSubmitting(true);
      const data = await postJson('/api/login', {
        username: trimmedUsername,
        password,
      });

      const receivedRole = (data.role || '').toLowerCase();
      const receivedToken = typeof data.token === 'string' ? data.token.trim() : '';

      if (!receivedToken) {
        throw new Error('Login succeeded, but no session token was returned.');
      }

      if (!['student', 'instructor', 'admin'].includes(receivedRole)) {
        setStatus('Role missing or unsupported for this user.');
        return;
      }

      const nextSession = {
        token: receivedToken,
        username: data.username || trimmedUsername,
        role: receivedRole,
        name: data.name || '',
      };

      setSession(nextSession);
      writeStoredSession(nextSession);
      setStatus('');
    } catch (error) {
      setStatus(error.message || 'Could not connect to server.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = (messageOrEvent = 'You have logged out.') => {
    const message = typeof messageOrEvent === 'string' ? messageOrEvent : 'You have logged out.';
    setSession(EMPTY_SESSION);
    clearStoredSession();
    setPassword('');
    setStatus(message);
  };

  if (session.token && session.role) {
    if (session.role === 'student') {
      return (
        <main className="erp-page erp-page-dashboard">
          <StudentPage
            authToken={session.token}
            displayName={session.name}
            username={session.username}
            onAuthFailure={handleLogout}
            onLogout={handleLogout}
          />
        </main>
      );
    }

    if (session.role === 'instructor') {
      return (
        <main className="erp-page erp-page-dashboard">
          <InstructorPage
            authToken={session.token}
            displayName={session.name}
            username={session.username}
            onAuthFailure={handleLogout}
            onLogout={handleLogout}
          />
        </main>
      );
    }

    if (session.role === 'admin') {
      return (
        <main className="erp-page erp-page-dashboard">
          <AdminPage
            authToken={session.token}
            displayName={session.name}
            username={session.username}
            onAuthFailure={handleLogout}
            onLogout={handleLogout}
          />
        </main>
      );
    }

    return (
      <main className="erp-page erp-page-dashboard">
        <section className="login-card">
          <h1>Unsupported Role</h1>
          <p className="subtitle">Role: {session.role}</p>
          <button type="button" className="logout-btn" onClick={handleLogout}>Logout</button>
        </section>
      </main>
    );
  }

  return (
    <main className="erp-page erp-page-login">
      <section className="erp-login-shell">
        <header className="erp-brand-banner">
          <div className="erp-brand-mark" aria-hidden="true">
            <img src={iitkgpLogo} alt="IIT Kharagpur" className="erp-brand-logo" />
          </div>
          <div className="erp-brand-copy">
            <h1 className="erp-brand-title">Indian Institute of Technology Kharagpur</h1>
            <p className="erp-brand-subtitle">Enterprise Resource Planning</p>
          </div>
        </header>

        <section className="login-card">
          <nav className="erp-login-tabs" aria-label="Authentication options">
            <button type="button" className="tab-item tab-item-active">Sign In</button>
          </nav>

          <div className="erp-login-content">
            <p className="subtitle">Please enter your credentials for signing in to the ERP portal.</p>

            <form onSubmit={handleSubmit} className="login-form">
              <label htmlFor="username">Stakeholder Code / Login Id</label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Stakeholder code / login id"
                autoComplete="username"
              />

              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Password"
                autoComplete="current-password"
              />

              <button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            {status && <p className="status-message">{status}</p>}
          </div>
        </section>
      </section>
    </main>
  );
}

export default App;
