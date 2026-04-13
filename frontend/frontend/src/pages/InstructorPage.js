import { useState } from 'react';
import { postJson } from '../api';

function InstructorPage({ authToken, displayName, username, onAuthFailure, onLogout }) {
  const [admitForm, setAdmitForm] = useState({ studentUsername: '', courseCode: '' });
  const [removeForm, setRemoveForm] = useState({ studentUsername: '', courseCode: '' });
  const [gradingForm, setGradingForm] = useState({ studentUsername: '', courseCode: '', grade: '' });
  const [courseForm, setCourseForm] = useState({ courseCode: '', title: '', credits: '3' });
  const [materialForm, setMaterialForm] = useState({ courseCode: '', title: '', resourceLink: '' });
  const [assignmentForm, setAssignmentForm] = useState({ courseCode: '', title: '' });
  const [status, setStatus] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activityLog, setActivityLog] = useState([]);
  const readyActions = [
    courseForm.courseCode.trim() && courseForm.title.trim(),
    admitForm.studentUsername.trim() && admitForm.courseCode.trim(),
    removeForm.studentUsername.trim() && removeForm.courseCode.trim(),
    gradingForm.studentUsername.trim() && gradingForm.courseCode.trim() && gradingForm.grade.trim(),
    materialForm.courseCode.trim() && materialForm.title.trim() && materialForm.resourceLink.trim(),
    assignmentForm.courseCode.trim() && assignmentForm.title.trim(),
  ].filter(Boolean).length;
  const lastActionLabel = activityLog[0] ? activityLog[0].split(':')[0] : 'None';

  const postRequest = async (path, payload) => {
    try {
      return await postJson(path, payload, authToken);
    } catch (error) {
      if (error.status === 401) {
        onAuthFailure?.('Your session expired or is invalid. Please sign in again.');
        throw error;
      }

      throw error;
    }
  };

  const runAction = async (label, path, payload) => {
    try {
      setIsLoading(true);
      const data = await postRequest(path, payload);
      const message = data.message || `${label} completed.`;
      setStatus(message);
      setActivityLog((prev) => [`${label}: ${message}`, ...prev].slice(0, 8));
    } catch (error) {
      if (error.status !== 401) {
        setStatus(error.message || `Unable to ${label.toLowerCase()}.`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="dashboard-card">
      <div className="dashboard-header">
        <div>
          <h1>Instructor Control Center</h1>
          <p className="subtitle">Welcome, {displayName || username}</p>
        </div>
        <button type="button" className="logout-btn" onClick={onLogout}>
          Logout
        </button>
      </div>

      <div className="stat-strip">
        <div className="stat-tile">
          <span>Recent Actions</span>
          <strong>{activityLog.length}</strong>
        </div>
        <div className="stat-tile">
          <span>Ready Actions</span>
          <strong>{readyActions}</strong>
        </div>
        <div className="stat-tile">
          <span>Last Action</span>
          <strong>{lastActionLabel}</strong>
        </div>
        <div className="stat-tile">
          <span>Managed By</span>
          <strong>{username}</strong>
        </div>
      </div>

      <div className="panel-grid">
        <div className="panel">
          <h3>Create Course</h3>
          <p className="tiny-note">Create a new course shell for this semester.</p>
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
              runAction('Create course', '/api/instructor/create-course', {
                creator_username: username,
                course_code: courseForm.courseCode,
                title: courseForm.title,
                credits: Number(courseForm.credits || 3),
              })
            }
          >
            Create Course
          </button>
        </div>

        <div className="panel">
          <h3>Admit Student</h3>
          <input
            type="text"
            value={admitForm.studentUsername}
            onChange={(event) => setAdmitForm((prev) => ({ ...prev, studentUsername: event.target.value }))}
            placeholder="Student username"
          />
          <input
            type="text"
            value={admitForm.courseCode}
            onChange={(event) => setAdmitForm((prev) => ({ ...prev, courseCode: event.target.value }))}
            placeholder="Course code"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() =>
              runAction('Admit student', '/api/instructor/admit-student', {
                student_username: admitForm.studentUsername,
                course_code: admitForm.courseCode,
              })
            }
          >
            Admit
          </button>
        </div>

        <div className="panel">
          <h3>Remove Student</h3>
          <input
            type="text"
            value={removeForm.studentUsername}
            onChange={(event) => setRemoveForm((prev) => ({ ...prev, studentUsername: event.target.value }))}
            placeholder="Student username"
          />
          <input
            type="text"
            value={removeForm.courseCode}
            onChange={(event) => setRemoveForm((prev) => ({ ...prev, courseCode: event.target.value }))}
            placeholder="Course code"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() =>
              runAction('Remove student', '/api/instructor/remove-student', {
                student_username: removeForm.studentUsername,
                course_code: removeForm.courseCode,
              })
            }
          >
            Remove
          </button>
        </div>

        <div className="panel">
          <h3>Assign Grade</h3>
          <input
            type="text"
            value={gradingForm.studentUsername}
            onChange={(event) => setGradingForm((prev) => ({ ...prev, studentUsername: event.target.value }))}
            placeholder="Student username"
          />
          <input
            type="text"
            value={gradingForm.courseCode}
            onChange={(event) => setGradingForm((prev) => ({ ...prev, courseCode: event.target.value }))}
            placeholder="Course code"
          />
          <input
            type="text"
            value={gradingForm.grade}
            onChange={(event) => setGradingForm((prev) => ({ ...prev, grade: event.target.value }))}
            placeholder="Grade (e.g. A)"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() =>
              runAction('Assign grade', '/api/instructor/assign-grade', {
                student_username: gradingForm.studentUsername,
                course_code: gradingForm.courseCode,
                grade: gradingForm.grade,
              })
            }
          >
            Assign
          </button>
        </div>

        <div className="panel">
          <h3>Add Course Material</h3>
          <input
            type="text"
            value={materialForm.courseCode}
            onChange={(event) => setMaterialForm((prev) => ({ ...prev, courseCode: event.target.value }))}
            placeholder="Course code"
          />
          <input
            type="text"
            value={materialForm.title}
            onChange={(event) => setMaterialForm((prev) => ({ ...prev, title: event.target.value }))}
            placeholder="Material title"
          />
          <input
            type="text"
            value={materialForm.resourceLink}
            onChange={(event) => setMaterialForm((prev) => ({ ...prev, resourceLink: event.target.value }))}
            placeholder="Resource link"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() =>
              runAction('Add material', '/api/instructor/add-material', {
                course_code: materialForm.courseCode,
                title: materialForm.title,
                resource_link: materialForm.resourceLink,
              })
            }
          >
            Add Material
          </button>
        </div>

        <div className="panel">
          <h3>Create Assignment</h3>
          <input
            type="text"
            value={assignmentForm.courseCode}
            onChange={(event) => setAssignmentForm((prev) => ({ ...prev, courseCode: event.target.value }))}
            placeholder="Course code"
          />
          <input
            type="text"
            value={assignmentForm.title}
            onChange={(event) => setAssignmentForm((prev) => ({ ...prev, title: event.target.value }))}
            placeholder="Assignment title"
          />
          <button
            type="button"
            disabled={isLoading}
            onClick={() =>
              runAction('Create assignment', '/api/instructor/create-assignment', {
                course_code: assignmentForm.courseCode,
                title: assignmentForm.title,
              })
            }
          >
            Create
          </button>
        </div>

        <div className="panel panel-activity">
          <h3>Recent Activity</h3>
          <ul className="result-list compact">
            {activityLog.map((item, index) => (
              <li key={`${item}-${index}`}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      {status && <p className="status-message">{status}</p>}
    </section>
  );
}

export default InstructorPage;
