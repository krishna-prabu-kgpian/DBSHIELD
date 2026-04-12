import { useState } from 'react';
import './App.css';
import StudentPage from './pages/StudentPage';
import InstructorPage from './pages/InstructorPage';
import AdminPage from './pages/AdminPage';

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
      <section className="login-card">
        <h1>Student ERP Login</h1>
        <p className="subtitle">Sign in to continue to your dashboard.</p>

        <form onSubmit={handleSubmit} className="login-form">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="e.g. 22CS10001"
            autoComplete="username"
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter password"
            autoComplete="current-password"
          />

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        {status && <p className="status-message">{status}</p>}
      </section>
    </main>
  );
}

export default App;
