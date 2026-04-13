import { useState } from 'react';

const API_BASE_URL = 'http://localhost:8000';

function AdminPage({ displayName, username, onLogout }) {
  const [teacherForm, setTeacherForm] = useState({ username: '', name: '', email: '' });
  const [studentForm, setStudentForm] = useState({ username: '', name: '', email: '' });
  const [courseForm, setCourseForm] = useState({ courseCode: '', title: '', credits: '3' });
  const [teacherToDelete, setTeacherToDelete] = useState('');
  const [studentToRemove, setStudentToRemove] = useState('');
  const [courseToDelete, setCourseToDelete] = useState('');
  const [status, setStatus] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const readyAddActions = [
    teacherForm.username.trim() && teacherForm.name.trim(),
    studentForm.username.trim() && studentForm.name.trim(),
    courseForm.courseCode.trim() && courseForm.title.trim(),
  ].filter(Boolean).length;
  const readyRemoveActions = [
    teacherToDelete.trim(),
    studentToRemove.trim(),
    courseToDelete.trim(),
  ].filter(Boolean).length;

  const postRequest = async (path, payload) => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Request failed.');
    }

    return data;
  };

  const runAction = async (label, path, payload) => {
    try {
      setIsLoading(true);
      const data = await postRequest(path, payload);
      const message = data.message || `${label} completed.`;
      setStatus(message);
    } catch (error) {
      setStatus(error.message || `Unable to ${label.toLowerCase()}.`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="dashboard-card">
      <div className="dashboard-header">
        <div>
          <h1>Admin Operations Hub</h1>
          <p className="subtitle">Welcome, {displayName || username}</p>
        </div>
        <button type="button" className="logout-btn" onClick={onLogout}>
          Logout
        </button>
      </div>

      <div className="stat-strip">
        <div className="stat-tile">
          <span>Ready Adds</span>
          <strong>{readyAddActions}</strong>
        </div>
        <div className="stat-tile">
          <span>Ready Removes</span>
          <strong>{readyRemoveActions}</strong>
        </div>
        <div className="stat-tile">
          <span>Total Operations</span>
          <strong>6</strong>
        </div>
        <div className="stat-tile">
          <span>Active Operator</span>
          <strong>{username}</strong>
        </div>
      </div>

      <p className="panel-row-title">Add Operations</p>
      <div className="panel-grid">
        <div className="panel">
          <h3>Add Teacher</h3>
          <input
            type="text"
            value={teacherForm.username}
            onChange={(event) => setTeacherForm((prev) => ({ ...prev, username: event.target.value }))}
            placeholder="Teacher username"
          />
          <input
            type="text"
            value={teacherForm.name}
            onChange={(event) => setTeacherForm((prev) => ({ ...prev, name: event.target.value }))}
            placeholder="Teacher name"
          />
          <input
            type="text"
            value={teacherForm.email}
            onChange={(event) => setTeacherForm((prev) => ({ ...prev, email: event.target.value }))}
            placeholder="Teacher email"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() => runAction('Add teacher', '/api/admin/add-teacher', teacherForm)}
          >
            Add Teacher
          </button>
        </div>

        <div className="panel">
          <h3>Add Student</h3>
          <input
            type="text"
            value={studentForm.username}
            onChange={(event) => setStudentForm((prev) => ({ ...prev, username: event.target.value }))}
            placeholder="Student username"
          />
          <input
            type="text"
            value={studentForm.name}
            onChange={(event) => setStudentForm((prev) => ({ ...prev, name: event.target.value }))}
            placeholder="Student name"
          />
          <input
            type="text"
            value={studentForm.email}
            onChange={(event) => setStudentForm((prev) => ({ ...prev, email: event.target.value }))}
            placeholder="Student email"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() => runAction('Add student', '/api/admin/add-student', studentForm)}
          >
            Add Student
          </button>
        </div>

        <div className="panel">
          <h3>Add Course</h3>
          <input
            type="text"
            value={courseForm.courseCode}
            onChange={(event) => setCourseForm((prev) => ({ ...prev, courseCode: event.target.value }))}
            placeholder="Course code"
          />
          <input
            type="text"
            value={courseForm.title}
            onChange={(event) => setCourseForm((prev) => ({ ...prev, title: event.target.value }))}
            placeholder="Course title"
          />
          <input
            type="number"
            min="1"
            max="8"
            value={courseForm.credits}
            onChange={(event) => setCourseForm((prev) => ({ ...prev, credits: event.target.value }))}
            placeholder="Credits"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() =>
              runAction('Add course', '/api/admin/add-course', {
                course_code: courseForm.courseCode,
                title: courseForm.title,
                credits: Number(courseForm.credits || 3),
              })
            }
          >
            Add Course
          </button>
        </div>
      </div>

      <p className="panel-row-title">Remove Operations</p>
      <div className="panel-grid">
        <div className="panel">
          <h3>Delete Course</h3>
          <input
            type="text"
            value={courseToDelete}
            onChange={(event) => setCourseToDelete(event.target.value)}
            placeholder="Course code"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() =>
              runAction('Delete course', '/api/admin/delete-course', {
                course_code: courseToDelete,
              })
            }
          >
            Delete Course
          </button>
        </div>

        <div className="panel">
          <h3>Delete Teacher</h3>
          <input
            type="text"
            value={teacherToDelete}
            onChange={(event) => setTeacherToDelete(event.target.value)}
            placeholder="Teacher username"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() =>
              runAction('Delete teacher', '/api/admin/delete-teacher', {
                username: teacherToDelete,
              })
            }
          >
            Delete Teacher
          </button>
        </div>

        <div className="panel">
          <h3>Remove Student</h3>
          <input
            type="text"
            value={studentToRemove}
            onChange={(event) => setStudentToRemove(event.target.value)}
            placeholder="Student username"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() =>
              runAction('Remove student', '/api/admin/remove-student', {
                username: studentToRemove,
              })
            }
          >
            Remove Student
          </button>
        </div>
      </div>

      {status && <p className="status-message">{status}</p>}
    </section>
  );
}

export default AdminPage;
