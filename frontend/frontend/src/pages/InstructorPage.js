import { useState } from 'react';

function InstructorPage({ displayName, username, onLogout }) {
  const [studentUsername, setStudentUsername] = useState('');
  const [courseCode, setCourseCode] = useState('');
  const [grade, setGrade] = useState('');
  const [assignmentTitle, setAssignmentTitle] = useState('');
  const [status, setStatus] = useState('');

  const callEndpoint = async (url, payload) => {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    setStatus(data.message || 'Action completed.');
  };

  return (
    <section className="dashboard-card">
      <div className="dashboard-header">
        <h1>Instructor Page</h1>
        <button type="button" className="logout-btn" onClick={onLogout}>
          Logout
        </button>
      </div>
      <p className="subtitle">Welcome, {displayName || username}</p>

      <div className="panel-grid">
        <div className="panel">
          <h3>Admit Student</h3>
          <input
            type="text"
            value={studentUsername}
            onChange={(event) => setStudentUsername(event.target.value)}
            placeholder="Student username"
          />
          <input
            type="text"
            value={courseCode}
            onChange={(event) => setCourseCode(event.target.value)}
            placeholder="Course code"
          />
          <button
            type="button"
            onClick={() =>
              callEndpoint('http://localhost:8000/api/instructor/admit-student', {
                student_username: studentUsername,
                course_code: courseCode,
              })
            }
          >
            Admit
          </button>
        </div>

        <div className="panel">
          <h3>Assign Grade</h3>
          <input
            type="text"
            value={studentUsername}
            onChange={(event) => setStudentUsername(event.target.value)}
            placeholder="Student username"
          />
          <input
            type="text"
            value={courseCode}
            onChange={(event) => setCourseCode(event.target.value)}
            placeholder="Course code"
          />
          <input
            type="text"
            value={grade}
            onChange={(event) => setGrade(event.target.value)}
            placeholder="Grade (e.g. A)"
          />
          <button
            type="button"
            onClick={() =>
              callEndpoint('http://localhost:8000/api/instructor/assign-grade', {
                student_username: studentUsername,
                course_code: courseCode,
                grade,
              })
            }
          >
            Assign
          </button>
        </div>

        <div className="panel">
          <h3>Create Assignment</h3>
          <input
            type="text"
            value={courseCode}
            onChange={(event) => setCourseCode(event.target.value)}
            placeholder="Course code"
          />
          <input
            type="text"
            value={assignmentTitle}
            onChange={(event) => setAssignmentTitle(event.target.value)}
            placeholder="Assignment title"
          />
          <button
            type="button"
            onClick={() =>
              callEndpoint('http://localhost:8000/api/instructor/create-assignment', {
                course_code: courseCode,
                title: assignmentTitle,
              })
            }
          >
            Create
          </button>
        </div>
      </div>

      {status && <p className="status-message">{status}</p>}
    </section>
  );
}

export default InstructorPage;
