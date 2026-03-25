import { useState } from 'react';

function AdminPage({ displayName, username, onLogout }) {
  const [action, setAction] = useState('');
  const [status, setStatus] = useState('');

  const runAdminAction = async () => {
    if (!action.trim()) {
      setStatus('Enter an admin action.');
      return;
    }

    const response = await fetch('http://localhost:8000/api/admin/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: action }),
    });

    const data = await response.json();
    setStatus(data.message || 'Admin action executed.');
  };

  return (
    <section className="dashboard-card">
      <div className="dashboard-header">
        <h1>Admin Page</h1>
        <button type="button" className="logout-btn" onClick={onLogout}>
          Logout
        </button>
      </div>
      <p className="subtitle">Welcome, {displayName || username}</p>

      <div className="panel-grid">
        <div className="panel">
          <h3>Admin Controls (Demo)</h3>
          <p className="tiny-note">Admin can do anything in this demo placeholder.</p>
          <input
            type="text"
            value={action}
            onChange={(event) => setAction(event.target.value)}
            placeholder="Describe admin action"
          />
          <button type="button" onClick={runAdminAction}>
            Run Action
          </button>
        </div>

        <div className="panel">
          <h3>Quick Ops</h3>
          <ul>
            <li>Manage users</li>
            <li>Review course catalog</li>
            <li>Override role permissions</li>
          </ul>
        </div>
      </div>

      {status && <p className="status-message">{status}</p>}
    </section>
  );
}

export default AdminPage;
