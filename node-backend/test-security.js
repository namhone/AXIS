const http = require('http');

const BASE_URL = process.env.AUTH_TEST_URL || 'http://127.0.0.1:3001/api/auth';

function request(path, options = {}, body = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(BASE_URL + path);
    const headers = { ...(options.headers || {}) };
    const payload = body === null ? null : JSON.stringify(body);
    if (payload) {
      headers['Content-Type'] = 'application/json';
      headers['Content-Length'] = Buffer.byteLength(payload);
    }

    const req = http.request(
      url,
      { method: options.method || 'GET', headers, timeout: 5000 },
      (res) => {
        let data = '';
        res.setEncoding('utf8');
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          let parsed = data;
          try {
            parsed = JSON.parse(data);
          } catch {
            // Giữ nguyên body để báo lỗi chẩn đoán khi server không trả JSON.
          }
          resolve({ status: res.statusCode, headers: res.headers, body: parsed });
        });
      }
    );

    req.on('timeout', () => req.destroy(new Error('Request timed out')));
    req.on('error', reject);
    if (payload) {
      req.write(payload);
    }
    req.end();
  });
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(`FAILED: ${message}`);
  }
}

function cookieValue(setCookieHeader) {
  return setCookieHeader ? setCookieHeader.split(';', 1)[0] : '';
}

async function runSecurityTests() {
  console.log('--------------------------------------------------');
  console.log('BẮT ĐẦU KIỂM THỬ BẢO MẬT AUTH SERVICE');
  console.log('--------------------------------------------------');

  const testEmail = `sec_test_${Date.now()}@example.com`;
  const testPassword = 'Password123!';

  console.log('[1] Registration');
  const registerResponse = await request(
    '/register',
    { method: 'POST' },
    { email: testEmail, password: testPassword }
  );
  assert(registerResponse.status === 201, `register returned ${registerResponse.status}`);

  console.log('[2] Login and cookie flags');
  const loginResponse = await request(
    '/login',
    { method: 'POST' },
    { email: testEmail, password: testPassword }
  );
  const loginCookie = loginResponse.headers['set-cookie']?.[0];
  const accessToken = loginResponse.body?.data?.accessToken;
  assert(loginResponse.status === 200, `login returned ${loginResponse.status}`);
  assert(accessToken, 'access token was not returned');
  assert(loginCookie?.toLowerCase().includes('httponly'), 'refresh cookie is not HttpOnly');
  assert(loginCookie?.toLowerCase().includes('samesite=strict'), 'refresh cookie is not SameSite=Strict');

  const oldCookie = cookieValue(loginCookie);
  console.log('   Access token and secure cookie received');

  console.log('[3] Valid refresh and rotation');
  const refreshResponse = await request('/refresh-token', {
    method: 'POST',
    headers: { Cookie: oldCookie },
  });
  const rawSetCookie = refreshResponse.headers['set-cookie'];
  const rotatedCookie = cookieValue(Array.isArray(rawSetCookie) ? rawSetCookie[0] : rawSetCookie);

  assert(refreshResponse.status === 200, `refresh returned ${refreshResponse.status}`);
  assert(rotatedCookie && rotatedCookie !== oldCookie, 'refresh token was not rotated');

  console.log('[4] Reuse detection');
  const reuseResponse = await request('/refresh-token', {
    method: 'POST',
    headers: { Cookie: oldCookie },
  });
  assert(reuseResponse.status === 403, `reuse returned ${reuseResponse.status}`);
  assert(
    reuseResponse.body?.code === 'TOKEN_REUSE_DETECTED',
    `unexpected reuse code ${reuseResponse.body?.code}`
  );

  console.log('[5] Rate limiting');
  let rateLimited = false;
  for (let index = 1; index <= 12; index += 1) {
    const response = await request(
      '/login',
      { method: 'POST' },
      { email: 'fake@example.com', password: 'wrong-password' }
    );
    if (response.status === 429) {
      rateLimited = true;
      console.log(`   Blocked at request #${index}`);
      break;
    }
  }
  assert(rateLimited, 'login rate limit was not reached');

  console.log('PASS: all security checks completed');
}

runSecurityTests().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
