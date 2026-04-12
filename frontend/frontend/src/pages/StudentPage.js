import { useState } from 'react';

const API_BASE_URL = 'http://localhost:8000';

function StudentPage({ displayName, username, onLogout }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [courses, setCourses] = useState([]);
  const [enrollCourseCode, setEnrollCourseCode] = useState('');
  const [deregisterCourseCode, setDeregisterCourseCode] = useState('');
  const [myCourses, setMyCourses] = useState([]);
  const [grades, setGrades] = useState([]);
  const [status, setStatus] = useState('');
  const [isLoading, setIsLoading] = useState(false);

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

  const searchCourses = async () => {
    try {
      setIsLoading(true);
      setStatus('');
      const data = await postRequest('/api/student/search-courses', { query: searchQuery });
      setCourses(data.courses || []);
      if (!data.courses?.length) {
        setStatus('No courses matched your query.');
      }
    } catch (error) {
      setStatus(error.message || 'Unable to search courses.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadMyCourses = async () => {
    try {
      setIsLoading(true);
      setStatus('');
      const data = await postRequest('/api/student/my-courses', {
        student_username: username,
      });
      setMyCourses(data.courses || []);
    } catch (error) {
      setStatus(error.message || 'Unable to load enrolled courses.');
    } finally {
      setIsLoading(false);
    }
  };

  const viewMyGrades = async () => {
    try {
      setIsLoading(true);
      setStatus('');
      const data = await postRequest('/api/student/view-grades', {
        student_username: username,
      });
      setGrades(data.grades || []);
    } catch (error) {
      setStatus(error.message || 'Unable to load grades.');
    } finally {
      setIsLoading(false);
    }
  };

  const enrollCourse = async (overrideCode) => {
    const courseCode = (overrideCode || enrollCourseCode).trim();
    if (!courseCode) {
      setStatus('Enter a course code to enroll.');
      return;
    }

    try {
      setIsLoading(true);
      const data = await postRequest('/api/student/enroll', {
        student_username: username,
        course_code: courseCode,
      });
      setStatus(data.message || 'Enrollment request sent.');
      setEnrollCourseCode(courseCode);
    } catch (error) {
      setStatus(error.message || 'Unable to submit enrollment request.');
    } finally {
      setIsLoading(false);
    }
  };

  const deregisterCourse = async () => {
    const courseCode = deregisterCourseCode.trim();
    if (!courseCode) {
      setStatus('Enter a course code to deregister.');
      return;
    }

    try {
      setIsLoading(true);
      const data = await postRequest('/api/student/deregister', {
        student_username: username,
        course_code: courseCode,
      });
      setStatus(data.message || 'Deregistration request sent.');
    } catch (error) {
      setStatus(error.message || 'Unable to submit deregistration request.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="dashboard-card">
      <div className="dashboard-header">
        <div>
          <h1>Student Workspace</h1>
          <p className="subtitle">Welcome, {displayName || username}</p>
        </div>
        <button type="button" className="logout-btn" onClick={onLogout}>
          Logout
        </button>
      </div>

      <div className="stat-strip">
        <div className="stat-tile">
          <span>Catalog Matches</span>
          <strong>{courses.length}</strong>
        </div>
        <div className="stat-tile">
          <span>Enrolled Courses</span>
          <strong>{myCourses.length}</strong>
        </div>
        <div className="stat-tile">
          <span>Grade Entries</span>
          <strong>{grades.length}</strong>
        </div>
      </div>

      <div className="panel-grid">
        <div className="panel">
          <h3>Search Course Catalog</h3>
          <p className="tiny-note">Search by code or title, then enroll directly.</p>
          <div className="inline-form">
            <input
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="e.g. CS101 or data"
            />
            <button type="button" onClick={searchCourses} disabled={isLoading}>
              Search
            </button>
          </div>
          <ul className="result-list">
            {courses.map((course) => (
              <li key={course.code}>
                <div>
                  <strong>{course.code}</strong> - {course.title}
                  <span className="chip">{course.credits || '-'} credits</span>
                </div>
                <button type="button" onClick={() => enrollCourse(course.code)} disabled={isLoading}>
                  Enroll
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <h3>Enroll in Course</h3>
          <p className="tiny-note">Submit course registration request.</p>
          <input
            type="text"
            value={enrollCourseCode}
            onChange={(event) => setEnrollCourseCode(event.target.value)}
            placeholder="Course code"
          />
          <button type="button" onClick={() => enrollCourse()} disabled={isLoading}>
            Enroll
          </button>
        </div>

        <div className="panel">
          <h3>Deregister from Course</h3>
          <p className="tiny-note">Drop a registered course by course code.</p>
          <input
            type="text"
            value={deregisterCourseCode}
            onChange={(event) => setDeregisterCourseCode(event.target.value)}
            placeholder="Course code"
          />
          <button type="button" onClick={deregisterCourse} disabled={isLoading}>
            Deregister
          </button>
        </div>

        <div className="panel">
          <h3>My Courses</h3>
          <button type="button" onClick={loadMyCourses} disabled={isLoading}>
            Refresh My Courses
          </button>
          <ul className="result-list compact">
            {myCourses.map((course) => (
              <li key={course.code}>
                <strong>{course.code}</strong> - {course.title}
              </li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <h3>View My Grades</h3>
          <button type="button" onClick={viewMyGrades} disabled={isLoading}>
            Load Grades
          </button>
          <ul className="result-list compact">
            {grades.map((gradeItem) => (
              <li key={gradeItem.course}>
                <strong>{gradeItem.course}</strong>: {gradeItem.grade}
                {gradeItem.semester ? <span className="chip">{gradeItem.semester}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {status && <p className="status-message">{status}</p>}
    </section>
  );
}

export default StudentPage;
