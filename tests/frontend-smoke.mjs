import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

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

test("development page renders real goals and keeps roadmap card structure consistent", async () => {
  const html = await read("pages/development.html");
  const css = await read("css/global.css");

  assert.match(html, /id="careerGoalsCurrent" class="info-grid current-goals-grid"/);
  assert.match(html, /currentGoals\.map/);
  assert.match(html, /current-goals-empty/);
  assert.doesNotMatch(html, /<h3>Python<\/h3>/);
  assert.doesNotMatch(html, /<h3>Tiếng Anh<\/h3>/);
  assert.match(html, /roadmap-task-card is-completed/);
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

test("heavy PDF scripts are deferred and narrow viewports have a fallback", async () => {
  const assessment = await read("pages/assessment.html");
  const profile = await read("pages/profile.html");
  const css = await read("css/global.css");
  assert.match(assessment, /jspdf\.umd\.min\.js[^>]+defer/);
  assert.match(profile, /jspdf\.umd\.min\.js[^>]+defer/);
  assert.match(css, /@media \(max-width: 320px\)/);
  assert.match(css, /@view-transition/);
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
  assert.match(app, /profile\[key\] = sanitizeDecimalInput\(field\.value\)/);
  assert.match(app, /document\.addEventListener\('input', handleProfileFieldEvent\)/);
  assert.match(app, /key === 'certificateScore' && field\.tagName !== 'SELECT'/);
  assert.match(profile, /id="certificateScore" type="text" inputmode="decimal"/);
  assert.match(profile, /certificateScore\.outerHTML = '<input id="certificateScore" type="text" inputmode="decimal"/);
  assert.match(profile, /certificateScore\.type = 'text'/);
  assert.match(css, /subject-score-row input\[data-profile-field\^="score"\][^{]*\{[^}]*font-weight: 700/s);
});
