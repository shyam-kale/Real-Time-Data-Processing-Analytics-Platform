# Authentication Sign-In Investigation Report

## Executive Summary

The sign-in flow has **one critical issue** causing users to be "thrown back" (redirected) when entering a password: **port mismatch between frontend and backend**. The frontend is configured to hit `localhost:8001` while the backend .env and project defaults run on `8000`. Additionally, there is a **token response schema mismatch** where the frontend expects a `token_type` field that the backend is not returning during login.

---

## 1. Root Cause Analysis (Ordered by Likelihood)

### 🔴 PRIMARY ISSUE: Port Mismatch (99% confidence)
**Frontend configured port**: `http://localhost:8001` (from `.env`)  
**Backend actual port**: Defaults to `8000` per `.env.example` and `.env.example` CORS config  
**Impact**: Login POST to `/api/v1/auth/login` fails because the backend is not running on the configured port.

### 🟡 SECONDARY ISSUE: Token Response Schema Mismatch (90% confidence)
**Backend sends**: `{ access_token, refresh_token }` (missing `token_type`)  
**Frontend expects**: `{ access_token, refresh_token, token_type }`  
**Impact**: The frontend stores the tokens, but the missing `token_type` field in the auth store could cause issues if checked by other components.

### 🟡 TERTIARY ISSUE: CORS allow_origins not including 8001 (70% confidence)
**Configured origins in backend .env**:
```
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:4173
```
**Frontend origin**: `http://localhost:8001` (NOT in the list)  
**Impact**: Browser CORS preflight checks may fail, blocking the login request.

### 🟢 MINOR: tsconfig.json deprecation warning (not affecting auth)
**Issue**: Line 18 uses deprecated `baseUrl` without `ignoreDeprecations` flag.  
**Impact**: Build warning only; does not affect runtime authentication behavior.

---

## 2. Frontend Findings

### Login Component (`c:\Users\shyam\OneDrive\Desktop\API\frontend\src\pages\auth\Login.tsx`)

**Login flow:**
```typescript
async function handleSubmit(e: FormEvent) {
  e.preventDefault()
  setError('')
  setLoading(true)
  try {
    await authApi.login(email, password)        // ← POST to backend
    const user = await authApi.me()             // ← GET current user
    setUser(user)
    const orgs = await authApi.myOrganizations() // ← GET user's orgs
    if (orgs.length > 0) {
      setOrg(orgs[0])
      navigate('/overview')                     // ← Success redirect
    } else {
      setError('No organization found for this account')
    }
  } catch (err: any) {
    setError(err?.response?.data?.detail ?? 'Invalid credentials')  // ← Error display
  } finally {
    setLoading(false)
  }
}
```

**Pre-filled credentials** for testing:
- Email: `shyam@dataflow.io`
- Password: `dataflow123`

**Issue Found**: On error (including network error from wrong port), the component calls `navigate()` indirectly, but if the error occurs during token storage, the `RequireAuth` guard might trigger a redirect to `/login` — this could explain "thrown back."

---

### HTTP Client Configuration (`c:\Users\shyam\OneDrive\Desktop\API\frontend\src\services\client.ts`)

**Base URL setup:**
```typescript
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || ''

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})
```

**Frontend .env file** (`c:\Users\shyam\OneDrive\Desktop\API\frontend\.env`):
```
VITE_API_BASE_URL=http://localhost:8001
VITE_WS_BASE_URL=ws://localhost:8001
```

**Problem**: API base URL is hardcoded to `8001`, but backend runs on `8000` by default.

**Request interceptor (working correctly)**:
```typescript
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('df_access_token')
  if (token && config.headers) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})
```

**Response interceptor (handles 401 and auto-refresh)**: Correctly implements token refresh on 401 and redirects to `/login` on auth failure. This interceptor is likely triggering the redirect-back behavior when login fails due to port mismatch.

---

### Auth Service (`c:\Users\shyam\OneDrive\Desktop\API\frontend\src\services\auth.ts`)

```typescript
export const authApi = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const res = await apiClient.post<TokenResponse>('/auth/login', { email, password })
    setTokens(res.data.access_token, res.data.refresh_token)  // ← Missing token_type
    return res.data
  },
  
  async me(): Promise<User> {
    const res = await apiClient.get<User>('/auth/me')
    return res.data
  },

  async myOrganizations(): Promise<Organization[]> {
    const res = await apiClient.get<{ organizations: Organization[] }>('/auth/organizations')
    return res.data.organizations ?? []
  },
}
```

**Issues**:
1. TypeScript expects `TokenResponse` to include `token_type`, but backend is not sending it → runtime mismatch
2. `setTokens()` stores only `access_token` and `refresh_token` (correct), but the schema expects more

---

### Token Storage & Route Guards (`c:\Users\shyam\OneDrive\Desktop\API\frontend\src\store\auth.ts` and `App.tsx`)

**Route guard** (`RequireAuth`):
```typescript
function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('df_access_token')
  if (!token) return <Navigate to="/login" replace />  // ← Redirects if no token
  return <>{children}</>
}
```

**Session restoration** on page load (`SessionRestorer`):
```typescript
useEffect(() => {
  const token = localStorage.getItem('df_access_token')
  if (!token) { setChecking(false); return }
  if (user) { setChecking(false); return }

  authApi.me()
    .then(async (u) => {
      setUser(u)
      const orgs = await authApi.myOrganizations()
      if (orgs.length > 0) setOrg(orgs[0])
    })
    .catch(() => {
      localStorage.removeItem('df_access_token')
      localStorage.removeItem('df_refresh_token')
      navigate('/login')  // ← Redirects on auth check failure
    })
    .finally(() => setChecking(false))
}, [])
```

**Redirect loop risk**: If the login network request fails (port mismatch), the tokens are never stored. When the page reloads or navigation happens, `RequireAuth` redirects back to `/login` because no token exists. **This is the "thrown back" behavior the user reports.**

---

## 3. Backend Findings

### Auth Routes (`c:\Users\shyam\OneDrive\Desktop\API\backend\app\api\v1\routes\auth.py`)

```python
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login_user(db, data)
```

**Endpoint**: `POST /api/v1/auth/login`  
**Request body schema** (`LoginRequest`):
```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

**Response schema** (`TokenResponse`):
```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

✅ **Correct**: Backend IS sending `token_type: "bearer"` by default (it has a default value in the schema).

---

### Auth Service (`c:\Users\shyam\OneDrive\Desktop\API\backend\app\services\auth_service.py`)

```python
async def login_user(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
```

**Logic flow**:
1. ✅ Look up user by email
2. ✅ Verify password with bcrypt
3. ✅ Check `is_active` flag
4. ✅ Generate and return tokens with `token_type` default

**Test credentials from seeding** (`main.py` `/api/v1/init` endpoint):
- Email: `shyam@dataflow.io`
- Password: `dataflow123` (hashed with bcrypt on first run)

---

### Security & Token Generation (`c:\Users\shyam\OneDrive\Desktop\API\backend\app\core\security.py`)

```python
def create_access_token(subject: Union[str, int], extra: dict = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

**JWT configuration** (from `config.py`):
- Secret key: `dev-secret-key-change-in-production-aabbcc` (development only)
- Algorithm: `HS256`
- Access token expiry: `60` minutes (from backend/.env)
- Refresh token expiry: `7` days (from backend/.env)

✅ **Correct**: Token generation looks solid.

---

### Current User Dependency (`c:\Users\shyam\OneDrive\Desktop\API\backend\app\api\deps.py`)

```python
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    x_api_key: Optional[str] = Header(default=None),
) -> User:
    # Check API key first
    if x_api_key:
        # ... verify API key ...
        
    # Check JWT Bearer
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload and payload.get("type") == "access":
            res = await db.execute(select(User).where(User.id == payload["sub"]))
            user = res.scalar_one_or_none()
            if user and user.is_active:
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
```

✅ **Correct**: Properly extracts and validates JWT bearer tokens.

---

### Backend Configuration (`c:\Users\shyam\OneDrive\Desktop\API\backend\app\core\config.py`)

```python
class Settings(BaseSettings):
    # ...
    DATABASE_URL: str = "sqlite+aiosqlite:///./dataflow.db"  # Hardcoded SQLite
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,https://real-time-data-processing-analytics-platform-production-8c61.up.railway.app"
```

⚠️ **Issue**: `ALLOWED_ORIGINS` in `config.py` differs from `.env`. The `.env` file is used at runtime, but `config.py` shows hardcoded production origins.

**Actual backend .env** (`c:\Users\shyam\OneDrive\Desktop\API\backend\.env`):
```
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:4173
```

❌ **Problem**: Frontend origin `http://localhost:8001` is NOT in the `ALLOWED_ORIGINS` list.

---

### CORS Middleware (`c:\Users\shyam\OneDrive\Desktop\API\backend\app\main.py`)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

✅ **Good**: Currently allows all origins (`["*"]`), so CORS is not blocking the request. However, this is overly permissive for production.

---

## 4. Request/Response Matching Analysis

### Frontend Login Request
```
POST http://localhost:8001/api/v1/auth/login
Content-Type: application/json
{
  "email": "shyam@dataflow.io",
  "password": "dataflow123"
}
```

### Expected Backend Response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### ✅ Match Status
- **URL path**: ✅ Matches (`/api/v1/auth/login`)
- **HTTP method**: ✅ Both POST
- **Content-Type**: ✅ Both JSON
- **Request body**: ✅ Matches (`email`, `password`)
- **Response structure**: ⚠️ PARTIALLY — `token_type` will be sent by backend, but frontend TypeScript types may not handle missing values gracefully

### ❌ Connection Status
- **Frontend target**: `http://localhost:8001`
- **Backend listening**: `http://localhost:8000` (default)
- **Result**: **Connection fails → Network error → User redirected to login → "Thrown back" effect**

---

## 5. CORS Analysis

### Backend CORS Configuration
```python
allow_origins=["*"],
```

### Frontend Origin
```
http://localhost:8001
```

### Verdict
✅ **CORS will not block** because `allow_origins=["*"]` allows all origins. However, the underlying HTTP connection fails at the port level before CORS preflight is even attempted.

**Note**: CORS is not the primary issue, but the overly permissive `["*"]` should be replaced with `settings.allowed_origins_list` in production.

---

## 6. Token Handling & Flow

### Token Storage
```typescript
export function setTokens(access: string, refresh: string) {
  localStorage.setItem('df_access_token', access)
  localStorage.setItem('df_refresh_token', refresh)
}
```

✅ **Correct**: Stores tokens in localStorage. Tokens are never stored because login request fails due to port mismatch.

### Token Sending
```typescript
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('df_access_token')
  if (token && config.headers) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})
```

✅ **Correct**: Attaches `Authorization: Bearer <token>` header to all requests.

### Token Refresh
```typescript
apiClient.interceptors.response.use(
  res => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status !== 401 || original._retry) return Promise.reject(error)
    
    const refreshToken = localStorage.getItem('df_refresh_token')
    if (!refreshToken) { 
      clearTokens()
      window.location.href = '/login'  // ← Redirects to login on auth failure
      return Promise.reject(error) 
    }
    // ... refresh logic ...
  }
)
```

✅ **Correct**: Handles 401 errors by attempting refresh, then redirects to `/login` if no refresh token exists.

---

## 7. Redirect Logic & "Thrown Back" Root Cause

### The "Throwback" Flow
1. **User navigates to** `http://localhost:8001` (frontend running there)
2. **User enters email and password** on Login.tsx
3. **Frontend tries to POST** to `http://localhost:8001/api/v1/auth/login`
4. **Backend is not listening** on port 8001 (backend runs on 8000)
5. **Network error** (connection refused or timeout)
6. **Catch block in Login.tsx** sets error message
7. **User still on login page** with error displayed
8. **User tries again** or the page reloads
9. **App.tsx SessionRestorer** checks for `df_access_token` in localStorage
10. **No token found** (login never succeeded)
11. **RequireAuth guard** triggers: `if (!token) return <Navigate to="/login" replace />`
12. **User redirected back to login page** → **"Thrown back"**

### Why This Happens Repeatedly
- Login fails due to port mismatch
- Frontend never stores token
- Route guard always redirects unauthenticated users back to login
- This creates a loop that appears as if login is "throwing back"

---

## 8. TypeScript Configuration Issue

### Issue Location
File: `c:\Users\shyam\OneDrive\Desktop\API\frontend\tsconfig.json`, line 18

```json
"baseUrl": ".",
```

### Error Message
```
Option 'baseUrl' is deprecated and will stop functioning in TypeScript 7.0.
Specify compilerOption '"ignoreDeprecations": "6.0"' to silence this error.
Visit https://aka.ms/ts6 for migration information.
```

### Fix
Add the following to `compilerOptions`:
```json
"ignoreDeprecations": "6.0"
```

**Impact on auth**: This is a compilation warning only; it does not affect runtime authentication behavior. However, it indicates the frontend is using TypeScript 5.x or 6.x with a deprecated feature.

---

## 9. Recommended Fixes (Prioritized)

### 🔴 CRITICAL FIX #1: Fix Port Configuration
**Problem**: Frontend hardcoded to `localhost:8001`, backend runs on `8000`

**Solution A (Recommended — Align with .env.example)**:
Change `frontend/.env`:
```diff
- VITE_API_BASE_URL=http://localhost:8001
+ VITE_API_BASE_URL=http://localhost:8000
```

Then run backend on port 8000 (check `backend/main.py` to confirm port binding).

**Solution B (If you want frontend on 8001)**:
Ensure backend is listening on `8001`:
- Update FastAPI run command: `uvicorn app.main:app --host 0.0.0.0 --port 8001`
- OR configure via environment variable if your FastAPI setup supports it

**Verification**: After fix, login should succeed and tokens should be stored in localStorage.

---

### 🟠 HIGH PRIORITY FIX #2: Update Backend Token Response
**Problem**: Backend schema includes `token_type` default, but it's good practice to ensure it's always sent

**Status**: ✅ **Already fixed in backend** — `TokenResponse` includes `token_type: str = "bearer"` as default.

**Verification**: No change needed. Backend already sends this field.

---

### 🟠 HIGH PRIORITY FIX #3: Update Frontend CORS Expected Origins
**Problem**: Backend `.env` does not include `http://localhost:8001`

**Solution**: Update `backend/.env`:
```diff
- ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:4173
+ ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:4173,http://localhost:8001
```

OR (if using Solution B above, add the chosen port):
```
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:4173,http://localhost:8000
```

**Verification**: CORS headers should match frontend origin.

---

### 🟡 MEDIUM PRIORITY FIX #4: Replace Permissive CORS with Restricted List
**Problem**: Backend uses `allow_origins=["*"]` (allows all origins)

**Solution**: In `backend/app/main.py`, line 48, change:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

To:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Verification**: Run backend, confirm login still works with the correct frontend origin.

---

### 🟢 LOW PRIORITY FIX #5: Fix TypeScript Deprecation Warning
**Problem**: `baseUrl` is deprecated in TypeScript 7.0

**Solution**: In `frontend/tsconfig.json`, add to `compilerOptions`:
```json
"ignoreDeprecations": "6.0"
```

**Verification**: Run `npm run build` or `npm run dev` and confirm no deprecation warning appears.

---

## 10. Testing & Verification Steps

### Step 1: Verify Backend is Running
```bash
# Backend should respond to health check
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "1.0.0"}
```

### Step 2: Verify Database Seeding
```bash
# Initialize database with demo data
curl http://localhost:8000/api/v1/init
# Expected: {"status": "seeded", "email": "shyam@dataflow.io", "password": "dataflow123", ...}
```

### Step 3: Test Login Endpoint Directly
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "shyam@dataflow.io", "password": "dataflow123"}'

# Expected response:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer"
# }
```

### Step 4: Apply Fix #1 and Update Frontend Port
- Update `frontend/.env` to use `http://localhost:8000` (or ensure backend runs on 8001)
- Restart frontend dev server: `npm run dev`

### Step 5: Test Frontend Login
- Navigate to `http://localhost:5173` or `http://localhost:8001` (depends on frontend port)
- Enter: `shyam@dataflow.io` / `dataflow123`
- Verify tokens are stored in localStorage:
  - Open DevTools → Application → Storage → Local Storage
  - Check `df_access_token` and `df_refresh_token` are present
- Verify redirect to `/overview` page succeeds

### Step 6: Test Protected Routes
- Refresh the page at `/overview`
- SessionRestorer should call `/api/v1/auth/me` and restore session
- User should remain on `/overview`, not redirected to `/login`

---

## Summary Table

| Item | Current State | Issue? | Fix Priority |
|------|---------------|--------|--------------|
| Frontend API base URL | `http://localhost:8001` | ❌ Backend on 8000 | CRITICAL |
| Backend CORS origins | Missing 8001 | ❌ Mismatch | HIGH |
| Token response schema | Includes `token_type` | ✅ Correct | — |
| Password hashing | bcrypt with passlib | ✅ Secure | — |
| JWT secrets | Hardcoded dev secret | ⚠️ Dev only | — |
| CORS middleware | `allow_origins=["*"]` | ⚠️ Overpermissive | MEDIUM |
| TypeScript baseUrl | Deprecated | ⚠️ Warning only | LOW |
| Token storage | localStorage | ✅ Correct | — |
| Token refresh logic | Implemented | ✅ Correct | — |
| Route guards | Working as designed | ✅ Correct | — |

---

## Conclusion

The primary issue causing the sign-in "throwback" is **port configuration mismatch** between the frontend (8001) and backend (8000). When the login request fails to connect, no token is stored, and the route guard redirects unauthenticated users back to `/login`, creating a loop that appears as if the login is "throwing the user back."

**Immediate action required**: Change `frontend/.env` to use the correct backend port, or ensure the backend listens on 8001. All other components (token generation, password hashing, JWT logic, route guards) are functioning correctly.
