import { useState } from 'react';

function StudentPage({ displayName, username, onLogout }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState('');
  const [grades, setGrades] = useState([]);
  const [status, setStatus] = useState('');

  const searchCourses = async () => {
    setStatus('');
    const response = await fetch('http://localhost:8000/api/student/search-courses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: searchQuery }),
    });
    const data = await response.json();
    setCourses(data.courses || []);
    if (!data.courses?.length) {
      setStatus('No courses found.');
    }
  };

  const viewMyGrades = async () => {
    setStatus('');
    const response = await fetch('http://localhost:8000/api/student/view-grades', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_username: username }),
    });
    const data = await response.json();
    setGrades(data.grades || []);
  };

  const enrollCourse = async () => {
    if (!selectedCourse.trim()) {
      setStatus('Enter a course code to enroll.');
      return;
    }

    const response = await fetch('http://localhost:8000/api/student/enroll', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_username: username,
        course_code: selectedCourse,
      }),
    });
    const data = await response.json();
    setStatus(data.message || 'Enrollment request sent.');
  };

  return (
    <section className="dashboard-card">
      <div className="dashboard-header">
        <h1>Student Page</h1>
        <button type="button" className="logout-btn" onClick={onLogout}>
          Logout
        </button>
      </div>
      <p className="subtitle">Welcome, {displayName || username}</p>

      <div className="panel-grid">
        <div className="panel">
          <h3>Search Courses</h3>
          <input
            type="text"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="e.g. CS101"
          />
          <button type="button" onClick={searchCourses}>
            Search
          </button>
          <ul>
            {courses.map((course) => (
              <li key={course.code}>{course.code} - {course.title}</li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <h3>Enroll in Course</h3>
          <input
            type="text"
            value={selectedCourse}
            onChange={(event) => setSelectedCourse(event.target.value)}
            placeholder="Course code"
          />
          <button type="button" onClick={enrollCourse}>
            Enroll
          </button>
        </div>

        <div className="panel">
          <h3>View My Grades</h3>
          <button type="button" onClick={viewMyGrades}>
            Load Grades
          </button>
          <ul>
            {grades.map((gradeItem) => (
              <li key={gradeItem.course}>{gradeItem.course}: {gradeItem.grade}</li>
            ))}
          </ul>
        </div>
      </div>

      {status && <p className="status-message">{status}</p>}
    </section>
  );
}

export default StudentPage;
