# Running Both Backends with One Frontend

## Overview

You now have a **backend selector** in the frontend that lets you toggle between vulnerable (8001) and secure (8002) backends with one click. 

```
Frontend (Port 3000)
    ├─ Talks to Vulnerable Backend (Port 8001) ❌
    └─ Or Secure Backend (Port 8002) ✅
```

---

## Quick Setup (3 Steps)

### Step 1: Terminal 1 - Run Vulnerable Backend
```bash
cd "Authorization Bypass"
python3 -m uvicorn app_vulnerable:app --host 0.0.0.0 --port 8001 --reload
```

### Step 2: Terminal 2 - Run Secure Backend
```bash
cd "Authorization Bypass"
python3 -m uvicorn app_secure:app --host 0.0.0.0 --port 8002 --reload
```

### Step 3: Terminal 3 - Run Frontend
```bash
cd frontend/frontend
npm install  # First time only
npm start
```

**Frontend opens at:** http://localhost:3000

---

## Demo: Switch Between Backends

### On Login Page:

You'll see two buttons in the top-right:

```
❌ Vulnerable (8001)    ✓ Secure (8002)
```

**Click to toggle** which backend the frontend uses.

---

## Scenario 1: Show the Vulnerability

1. **Click** "❌ Vulnerable (8001)"
2. **Login** as: `student_user` / `password`
3. **You'll see a STUDENT dashboard**
4. **Try to call instructor endpoints** (should work - VULNERABLE!)
5. **Observe the attack succeeds**

---

## Scenario 2: Show the Fix

1. **Logout** (button in dashboard)
2. **Click** "✓ Secure (8002)"
3. **Login** again as: `student_user` / `password`
4. **Try the same attacks** (should be BLOCKED - SECURE!)
5. **Observe 403 Forbidden errors**

---

## Complete Testing Flow (5 minutes)

### Part 1: Vulnerable (3 min)
```
1. Switch to "❌ Vulnerable (8001)"
2. Login: student1 / pass1
3. As student, try to:
   - View another student's grades ✓ WORKS (BAD)
   - Assign yourself an 'A' ✓ WORKS (BAD)
   - Call admin endpoint ✓ WORKS (BAD)
4. Take screenshots of working attacks
```

### Part 2: Secure (2 min)
```
1. Switch to "✓ Secure (8002)"
2. Login again: student1 / pass1
3. Try the same attacks
   - View another student's grades → 403 BLOCKED ✓
   - Assign yourself grade → 403 BLOCKED ✓
   - Call admin endpoint → 403 BLOCKED ✓
4. Compare results
```

---

## Backend Selection UI

The selector appears on:
- **Login page:** Top-right corner (select before logging in)
- **Dashboard pages:** Small badge in top-right showing current backend

### Color Coding:
- **Red `❌ VULNERABLE`** = Port 8001 (no authorization)
- **Green `✓ SECURE`** = Port 8002 (with authorization)

---

## Testing with Different Roles

### Test Scenarios:

**1. Student accessing instructor endpoint:**
```
Login: student1 / pass1
Try: Assign grades to another student
Vulnerable: SUCCESS ❌
Secure: 403 FORBIDDEN ✓
```

**2. Student accessing admin endpoint:**
```
Login: student1 / pass1
Try: Execute admin action
Vulnerable: SUCCESS ❌
Secure: 403 FORBIDDEN ✓
```

**3. Legitimate admin action:**
```
Login: admin / admin123
Try: Execute admin action
Vulnerable: SUCCESS ✓
Secure: SUCCESS ✓
```

---

## Test Credentials

```
Admin:
  Username: admin
  Password: admin123

Student 1:
  Username: student1
  Password: pass1

Student 2:
  Username: student2
  Password: pass2
```

(These are the same credentials from your original database)

---

## How It Works (Technical)

The frontend was updated with:

1. **State management:**
   ```javascript
   const [backendVersion, setBackendVersion] = useState('secure');
   ```

2. **Backend URL selector:**
   ```javascript
   const getBackendUrl = () => {
     return backendVersion === 'vulnerable' 
       ? 'http://localhost:8001' 
       : 'http://localhost:8002';
   };
   ```

3. **Dynamic API calls:**
   ```javascript
   const backendUrl = getBackendUrl();
   const response = await fetch(`${backendUrl}/api/login`, {...});
   ```

4. **Child components receive backend:**
   ```javascript
   <StudentPage
     backendUrl={getBackendUrl()}
     {...props}
   />
   ```

---

## For Presentations

### Live Demo Script:

```
"I have three terminals:
• Terminal 1: Vulnerable backend on 8001
• Terminal 2: Secure backend on 8002
• Terminal 3: Frontend on 3000

I can toggle between them in real-time without reloading anything.
Let me show you the difference..."
```

### Steps:
1. Open frontend in browser
2. Show red button "Vulnerable (8001)" at top
3. Login as student
4. Show student accessing instructor endpoint (WORKS)
5. Logout, click "Secure (8002)" button (turns green)
6. Login as student again
7. Show same endpoint BLOCKED with 403

---

## Troubleshooting

**Issue:** "Cannot connect to backend"
- Make sure both backends are running on 8001 and 8002
- Check terminals to see if any crashed

**Issue:** "Button not showing"
- Refresh the page (Ctrl+R)
- Clear browser cache

**Issue:** "Getting different errors than expected"
- Make sure you're on the right backend (check color of button)
- Logout and login again
- Check backend terminals for detailed error messages

**Issue:** "Still getting 200 OK on vulnerable"
- Make sure you're actually on port 8001 (red button selected)
- Check the badge at top-right of page

---

## File Changes Made

Only one file was modified:

**[frontend/frontend/src/App.js](frontend/frontend/src/App.js)**

Changes:
1. Added `backendVersion` state (line ~8)
2. Added `getBackendUrl()` function
3. Updated login to use dynamic backend URL
4. Added backend selector buttons on login page
5. Added backend badge badges on role pages
6. Pass `backendUrl` prop to child components

---

## Next Steps

### Option 1: Automated Demo
- Use curl commands on backend
- Show test results
- Use frontend to verify

### Option 2: Interactive Demo
- Have audience suggest students to test
- Have them suggest endpoints to attack
- Switch backends in real-time

### Option 3: Comparison View
- Open two browser windows (F12 dev tools open)
- One pointing to 8001, one to 8002
- Perform same action side-by-side

---

## Advanced: Run Frontends on Different Ports

If you want TWO separate frontend instances:

```bash
# Terminal 3a: Frontend for vulnerable (port 3001)
PORT=3001 npm start

# Terminal 3b: Frontend for secure (port 3000)
PORT=3000 npm start
```

Then open both in browser:
- http://localhost:3000 (always connects to 8002 secure)
- http://localhost:3001 (always connects to 8001 vulnerable)

But single frontend with toggle is cleaner for demos!

---

## Summary

✅ Both backends running simultaneously (8001 + 8002)  
✅ One frontend that switches between them (3000)  
✅ Instant toggle in browser (top-right button)  
✅ Color coding shows which backend is active  
✅ Perfect for side-by-side vulnerability demonstrations  

Ready to impress your audience! 🎯
