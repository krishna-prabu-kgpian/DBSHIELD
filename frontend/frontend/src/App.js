import { useState } from 'react';
import './App.css';
import StudentPage from './pages/StudentPage';
import InstructorPage from './pages/InstructorPage';
import AdminPage from './pages/AdminPage';
import iitkgpLogo from './assets/iitkgp-logo.jpeg';

function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loggedInName, setLoggedInName] = useState('');
  const [loggedInUsername, setLoggedInUsername] = useState('');
  const [role, setRole] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus('');

    if (!username.trim() || !password) {
      setStatus('Please enter both username and password.');
      return;
    }

    try {
      setIsSubmitting(true);
      const response = await fetch('http://localhost:8000/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Login request failed.');
      }

      const receivedRole = (data.role || '').toLowerCase();
      if (['student', 'instructor', 'admin'].includes(receivedRole)) {
        setRole(receivedRole);
        setLoggedInName(data.name || '');
        setLoggedInUsername(data.username || username);
        setStatus('');
      } else {
        setStatus('Role missing or unsupported for this user.');
      }
    } catch (error) {
      setStatus(error.message || 'Could not connect to server.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = () => {
    setRole('');
    setLoggedInName('');
    setLoggedInUsername('');
    setPassword('');
    setStatus('You have logged out.');
  };

  if (role) {
    if (role === 'student') {
      return (
        <main className="erp-page erp-page-dashboard">
          <StudentPage
            displayName={loggedInName}
            username={loggedInUsername}
            onLogout={handleLogout}
          />
        </main>
      );
    }

    if (role === 'instructor') {
      return (
        <main className="erp-page erp-page-dashboard">
          <InstructorPage
            displayName={loggedInName}
            username={loggedInUsername}
            onLogout={handleLogout}
          />
        </main>
      );
    }

    if (role === 'admin') {
      return (
        <main className="erp-page erp-page-dashboard">
          <AdminPage
            displayName={loggedInName}
            username={loggedInUsername}
            onLogout={handleLogout}
          />
        </main>
      );
    }

    return (
      <main className="erp-page erp-page-dashboard">
        <section className="login-card">
          <h1>Unsupported Role</h1>
          <p className="subtitle">Role: {role}</p>
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
