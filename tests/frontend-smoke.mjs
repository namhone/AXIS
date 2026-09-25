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
