import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";
import vm from "node:vm";

const root = resolve(import.meta.dirname, "..");

async function read(relativePath) {
  return readFile(resolve(root, relativePath), "utf8");
}

test("CV editor exposes language selection and AI action", async () => {
  const html = await read("pages/cv-builder-editor.html");
  const script = await read("js/cv-builder-editor.js");

  assert.match(html, /data-cv-language/);
  assert.match(html, /data-action="normalize"/);
  assert.match(script, /\/ai\/cv/);
  assert.match(script, /translate/);
});

test("career library exposes pagination and stable detail links", async () => {
  const html = await read("pages/careers.html");

  assert.match(html, /id="careerPagination"/);
  assert.match(html, /data-page-action="previous"/);
  assert.match(html, /career-detail\.html\?code=/);
  for (let index = 1; index <= 24; index += 1) {
    assert.match(html, new RegExp(`N${String(index).padStart(2, "0")}:`));
  }
});

test("RIASEC layout includes responsive controls", async () => {
  const html = await read("pages/riasec.html");
  const css = await read("css/global.css");

  assert.match(html, /riasec-assessment-layout/);
  assert.match(html, /id="submitRiasec"/);
  assert.match(css, /\.riasec-group-switcher \{ display: grid/);
  assert.match(css, /\.riasec-option \{ display: grid; min-width: 0/);
});

test("RIASEC assessment samples 60 questions and renders structured AI evaluation", async () => {
  const html = await read("pages/riasec.html");
  const script = await read("js/riasec.js");
  assert.match(html, /10 câu, với 2 câu cho mỗi khía cạnh/);
  assert.match(html, /id="riasecAiOverall"/);
  assert.match(html, /id="riasecAiDirection"/);
  assert.match(html, /id="riasecAiSummary"/);
  assert.match(script, /var QUESTIONS_PER_ASPECT = 2;/);
  assert.match(script, /var QUESTIONS_PER_GROUP = QUESTIONS_PER_ASPECT \* ASPECTS_PER_GROUP;/);
  assert.ok(script.includes("apiRequest('/ai/riasec-evaluation'"));
  assert.ok(script.includes("apiRequest('/assessments/run'"));
  assert.ok(!script.includes("apiRequest('/learning/assessments/run'"));
  assert.match(script, /aspect_scores:/);
  assert.match(script, /result\.aspects\[code\]\[aspect\]\.converted/);
});

test("dashboard renders the backend ranking and surfaces evaluation failures", async () => {
  const dashboard = await read("js/dashboard.js");

  assert.match(dashboard, /render\(response\.results\)/);
  assert.match(dashboard, /result\.match_score/);
  assert.match(dashboard, /result\.gap_risk/);
  assert.match(dashboard, /Không thể tính kết quả từ máy chủ AXIS/);
});

test("desktop navigation converts mouse-wheel movement to horizontal scrolling", async () => {
  const script = await read("js/components.js");

  assert.match(script, /setupHorizontalWheelScroll/);
  assert.match(script, /nav\.scrollLeft \+= verticalDelta/);
  assert.match(script, /passive: false/);
});

test("profile exposes private document management", async () => {
  const html = await read("pages/profile.html");

  assert.match(html, /id="documentUpload"/);
  assert.match(html, /id="documentsList"/);
  assert.match(html, /listDocuments/);
  assert.match(html, /deleteDocument/);
});

test("development page shows ranked career matches and careers saved to the roadmap", async () => {
  const html = await read("pages/development.html");
  const css = await read("css/global.css");

  assert.match(html, /id="careerGoalsCurrent" class="info-grid current-goals-grid career-focus-grid"/);
  assert.match(html, /id="careerSelectedGoals"/);
  assert.match(html, /href="careers\.html"/);
  assert.match(html, /renderCareerFocus/);
  assert.doesNotMatch(html, /careerFocusCustom|persistCareerFocus|career-focus\/career-focus/);
  assert.match(html, /focus\.recommended/);
  assert.match(html, /focus\.selected/);
  assert.doesNotMatch(html, /<h3>Python<\/h3>/);
  assert.doesNotMatch(html, /<h3>Tiếng Anh<\/h3>/);
  assert.match(css, /\.career-focus-grid/);
  assert.match(html, /Chưa có nhiệm vụ\. Hãy tạo lộ trình để bắt đầu/);
  assert.doesNotMatch(html, /Python: biến và kiểu dữ liệu|C\+\+: cú pháp nền tảng/);
  assert.match(html, /function renderRoadmapSteps\(steps\)/);
  assert.match(css, /roadmap-item > \.roadmap-task-list > \.roadmap-task-card/);
  assert.match(css, /grid-template-columns: minmax\(0, 1fr\) !important/);
});

test("development progress and assessment use persisted evaluation history", async () => {
  const development = await read("pages/development.html");
  const assessment = await read("pages/assessment.html");

  assert.match(development, /id="developmentProgressChart"/);
  assert.match(development, /apiRequest\('\/assessments'\)/);
  assert.match(development, /drawDevelopmentProgress/);
  assert.match(assessment, /id="runAssessment"/);
  assert.match(assessment, /apiRequest\('\/assessments\/run'/);
  assert.match(assessment, /id="assessmentActionStatus"/);
  assert.match(assessment, /Đã chạy đánh giá và lưu mốc tiến bộ/);
});

test("shared shell is semantic and every page exposes basic SEO metadata", async () => {
  const header = await read("components/header.html");
  const footer = await read("components/footer.html");
  assert.match(header, /^<header class="site-header"/);
  assert.match(header, /<nav class="header-nav"/);
  assert.match(header, /data-path="pages\/calendar\.html"/);
  assert.match(footer, /^<footer class="site-footer-content"/);
  assert.match(footer, /for="contactEmail"/);

  const pages = ["index.html", ...["about", "assessment", "calendar", "career-detail", "careers", "cv-builder-editor", "dashboard", "development", "guide", "profile", "riasec"].map((name) => `pages/${name}.html`)];
  for (const page of pages) {
    const html = await read(page);
    assert.match(html, /<title>[^<]+<\/title>/, page);
    assert.match(html, /<meta name="description"/, page);
    assert.match(html, /<meta property="og:title"/, page);
  }
});

test("page scripts defer parsing and PDF generation loads only on request", async () => {
  const assessment = await read("pages/assessment.html");
  const profile = await read("pages/profile.html");
  const pdfLoader = await read("js/pdf-loader.js");
  const css = await read("css/global.css");
  assert.match(assessment, /js\/pdf-loader\.js[^>]+defer/);
  assert.match(profile, /js\/pdf-loader\.js[^>]+defer/);
  assert.doesNotMatch(assessment, /<script[^>]+jspdf\.umd\.min\.js/);
  assert.doesNotMatch(profile, /<script[^>]+jspdf\.umd\.min\.js/);
  assert.match(pdfLoader, /script\.integrity = integrity/);
  assert.match(pdfLoader, /window\.jspdf\.jsPDF/);
  assert.match(assessment, /await window\.AxisPdf\.load\(\)/);
  assert.match(profile, /await window\.AxisPdf\.load\(\)/);
  assert.match(css, /@media \(max-width: 320px\)/);
  assert.match(css, /@view-transition/);
});

test("shared component loaders are deferred on every HTML page", async () => {
  const pages = ["index.html", ...["about", "assessment", "calendar", "career-detail", "careers", "cv-builder-editor", "dashboard", "development", "guide", "profile", "riasec"].map((name) => `pages/${name}.html`)];

  for (const page of pages) {
    const html = await read(page);
    const head = html.match(/<head\b[^>]*>([\s\S]*?)<\/head>/i)?.[1] ?? "";
    const componentLoader = head.match(/<script\b[^>]*src=["'][^"']*components\.js[^"']*["'][^>]*>/i)?.[0];
    assert.ok(componentLoader, `${page} is missing the shared component loader`);
    assert.match(componentLoader, /\bdefer\b/i, `${page} loads shared components as a parser-blocking script`);
  }
});

test("every page loads Inter directly instead of through a CSS import waterfall", async () => {
  const pages = ["index.html", ...["about", "assessment", "calendar", "career-detail", "careers", "cv-builder-editor", "dashboard", "development", "guide", "profile", "riasec"].map((name) => `pages/${name}.html`)];
  const css = await read("css/global.css");

  assert.doesNotMatch(css, /@import\s+url\([^)]*fonts\.googleapis\.com/i);
  for (const page of pages) {
    const html = await read(page);
    assert.match(html, /rel=["']preconnect["'][^>]+fonts\.googleapis\.com/i, `${page} should preconnect to Google Fonts`);
    assert.match(html, /rel=["']stylesheet["'][^>]+fonts\.googleapis\.com/i, `${page} should load Inter directly`);
  }
});

test("PDF loader downloads the library once on demand and retries failures", async () => {
  const source = await read("js/pdf-loader.js");
  const scripts = [];
  const context = {
    window: {
      setTimeout: () => 1,
      clearTimeout: () => {},
    },
    document: {
      createElement: () => ({
        remove() {},
      }),
      head: {
        appendChild(script) {
          scripts.push(script);
        },
      },
    },
  };
  vm.runInNewContext(source, context);

  const firstLoad = context.window.AxisPdf.load();
  const secondLoad = context.window.AxisPdf.load();
  assert.equal(firstLoad, secondLoad);
  assert.equal(scripts.length, 1);
  assert.equal(scripts[0].integrity, "sha384-JcnsjUPPylna1s1fvi1u12X5qjY5OL56iySh75FdtrwhO/SWXgMjoVqcKyIIWOLk");

  scripts[0].onerror();
  await assert.rejects(firstLoad, /Unable to load PDF library/);
  context.window.AxisPdf.load();
  assert.equal(scripts.length, 2);
});

test("registration validates required identity fields before requesting the API", async () => {
  const auth = await read("js/auth.js");

  assert.match(auth, /nameField\.required = signUp/);
  assert.match(auth, /Vui lòng nhập họ và tên/);
  assert.match(auth, /Mật khẩu phải có ít nhất 8 ký tự/);
  assert.match(auth, /Không thể kết nối máy chủ/);
  assert.match(auth, /Email này đã được đăng ký/);
  assert.match(auth, /Thông tin đăng ký chưa hợp lệ/);
});

test("CV list fields create editable rows and remove empty rows", async () => {
  const editor = await read("js/cv-builder-editor.js");

  assert.match(editor, /list\.dataset\.cvListPath/);
  assert.match(editor, /insertNewListItem/);
  assert.match(editor, /removeEmptyListItem/);
  assert.match(editor, /syncListFromDom/);
  assert.match(editor, /node\.dataset\.cvMode === 'list-item'/);
});

test("CV renders labeled academic scores and avoids invented resume details", async () => {
  const editor = await read("js/cv-builder-editor.js");
  const css = await read("css/cv-builder-editor.css");

  assert.match(editor, /KẾT QUẢ HỌC TẬP/);
  assert.match(editor, /GPA lớp /);
  assert.match(editor, /Điểm tuyển sinh/);
  assert.match(editor, /formatScore/);
  assert.match(editor, /appendAcademicScores\(wrapper, entry\)/);
  assert.match(editor, /model\.data\.education\.academicScores = extractProfile\(profileFromAxis\(\)\)\.education\.academicScores/);
  assert.match(editor, /nextModel\.data = mergeAiEditableSection\(nextModel\.data, aiPayload \|\| \{\}\)/);
  assert.match(editor, /model\.data = mergeAiEditableSection\(currentCvData\(\), data\)/);
  assert.doesNotMatch(editor, /2021 – 2025|2024 – PRESENT|REFERENCES/);
  assert.doesNotMatch(editor, /dotIndex < 4|i < 4/);
  assert.match(css, /\.cv-academic-score__value[^}]*font-size: 14px[^}]*font-weight: 900/s);
});

test("CV A4 preview scales to the available mobile width", async () => {
  const editor = await read("js/cv-builder-editor.js");

  assert.match(editor, /var availableWidth = Math\.max\(0, scroll\.clientWidth - 16\)/);
  assert.match(editor, /Math\.min\(1, availableWidth \/ pageWidth\)/);
  assert.doesNotMatch(editor, /Math\.max\(scale,\s*0\.56\)/);
});

test("decimal score fields preserve in-progress comma and period input", async () => {
  const app = await read("js/app.js");
  const profile = await read("pages/profile.html");
  const css = await read("css/global.css");

  assert.match(app, /function sanitizeDecimalInput/);
  assert.match(app, /isDecimalScoreField\(key, field\)/);
  assert.match(app, /: sanitizeDecimalInput\(field\.value\)/);
  assert.match(app, /document\.addEventListener\('input', handleProfileFieldEvent\)/);
  assert.match(app, /key === 'certificateScore' && field\.tagName !== 'SELECT'/);
  assert.match(profile, /id="certificateScore" type="text" inputmode="decimal"/);
  assert.match(profile, /certificateScore\.outerHTML = '<input id="certificateScore" type="text" inputmode="decimal"/);
  assert.match(profile, /certificateScore\.type = 'text'/);
  assert.match(css, /subject-score-row input\[data-profile-field\^="score"\][^{]*\{[^}]*font-weight: 700/s);
});

test("certificate scores enforce each certificate's range and allowed increments", async () => {
  const certificatesSource = await read("js/certificates.js");
  const profile = await read("pages/profile.html");
  const app = await read("js/app.js");
  const context = { window: {} };
  vm.runInNewContext(certificatesSource, context);
  const rules = context.window.AxisCertificates;

  assert.equal(rules.sanitizeScoreInput("IELTS", "6,3"), "6,");
  assert.equal(rules.sanitizeScoreInput("IELTS", "6.5"), "6.5");
  assert.equal(rules.formatScore("IELTS", "6,5"), "6.5");
  assert.equal(rules.validateScore("IELTS", "6.5"), "");
  assert.match(rules.validateScore("IELTS", "6.3"), /bước 0\.5/);
  assert.equal(rules.sanitizeScoreInput("TOEIC", "785,5"), "785");
  assert.equal(rules.validateScore("TOEIC", "785"), "");
  assert.match(rules.validateScore("TOEIC", "783"), /bước 5/);
  assert.match(rules.validateScore("SAT", "1599"), /bước 10/);
  assert.match(rules.validateScore("IELTS", "9.5"), /khoảng 0–9/);
  assert.match(profile, /dataset\.certificateType = type/);
  assert.match(profile, /certificateScore\.reportValidity\(\)/);
  assert.match(profile, /certificateName\.addEventListener\('change', function \(\) \{\s*certificateScore\.value = ''/);
  assert.match(app, /sanitizeScoreInput\(certificateType, field\.value\)/);
});

test("CV editor auto-saves local drafts and supports the save shortcut", async () => {
  const editor = await read("js/cv-builder-editor.js");
  const html = await read("pages/cv-builder-editor.html");

  assert.match(editor, /function scheduleLocalDraftSave/);
  assert.match(editor, /localStorage\.setItem\(draftStorageKey\(\)/);
  assert.match(editor, /'axis_cv_draft:' \+ user\.id/);
  assert.match(editor, /'axis_cv_draft:guest'/);
  assert.match(editor, /event\.key\.toLowerCase\(\) === 's'/);
  assert.match(html, /tự lưu trên thiết bị/);
});

test("profile personal interests, personality, and skills share a responsive full-width row", async () => {
  const profile = await read("pages/profile.html");
  const css = await read("css/global.css");

  assert.match(profile, /for="profile-interests"[\s\S]*data-profile-field="interests"/);
  assert.match(profile, /for="profile-personality"[\s\S]*data-profile-field="personality"/);
  assert.match(profile, /for="profile-skills"[\s\S]*data-profile-field="skills"/);
  assert.match(profile, /class="field profile-core-skills"[\s\S]*data-profile-field="skills"/);
  assert.match(css, /\.profile-workspace \.profile-core-details \.profile-core-fields \{\s*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(css, /\.profile-core-fields > \.profile-core-skills \{\s*grid-column: 1 \/ -1/s);
  assert.doesNotMatch(css, /@media \(max-width: 520px\)[\s\S]*\.profile-core-fields \{\s*grid-template-columns: minmax\(0, 1fr\)/);
});

test("CV list rows discard blanks and move focus when deleting an empty row", async () => {
  const editor = await read("js/cv-builder-editor.js");

  assert.match(editor, /event\.key === 'Backspace'/);
  assert.match(editor, /isCaretAtStart\(node\)/);
  assert.match(editor, /removeEmptyListItem\(node, true\)/);
  assert.match(editor, /node\.addEventListener\('blur'/);
  assert.match(editor, /focusListItemAtEnd\(previousItem\)/);
  assert.match(editor, /event\.isComposing \|\| event\.keyCode === 229/);
});

test("CV AI runs only on demand and requires changed content after successful normalization", async () => {
  const editor = await read("js/cv-builder-editor.js");
  const html = await read("pages/cv-builder-editor.html");
  const aiRoute = await read("backend/app/api/routes/ai.py");

  assert.match(html, /Chỉ gửi nội dung CV có thể chỉnh sửa lên AI khi bạn chủ động nhấn nút/);
  assert.match(editor, /contentFingerprint\(currentCvData\(\)\)/);
  assert.match(editor, /key\.replace\(\/\^data\\\.\/, ''\)/);
  assert.match(editor, /Boolean\(lastNormalizedFingerprint && fingerprint === lastNormalizedFingerprint\)/);
  assert.match(editor, /if \(operation === 'normalize'\) \{\s*return Promise\.reject/);
  assert.doesNotMatch(editor, /axis:profile-hydrated', function \(\) \{ runPipeline\(\)/);
  assert.doesNotMatch(editor, /axis:auth-state', function \(event\) \{\s*if \(event\.detail && event\.detail\.signedIn\) runPipeline/);
  assert.match(aiRoute, /_cv_ai_limiter = LockoutRateLimiter\(limit=5, window_seconds=600, lockout_seconds=600\)/);
  assert.match(aiRoute, /__:\s*None = Depends\(enforce_cv_ai_rate_limit\)/);
});
