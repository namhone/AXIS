const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const output = path.join(root, 'dist');
const directories = ['assets', 'components', 'css', 'cv-builder', 'js', 'pages'];
const files = ['index.html', 'cauhoi.txt', 'sitemap.xml'];

fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(output, { recursive: true });
for (const name of directories) fs.cpSync(path.join(root, name), path.join(output, name), { recursive: true });
for (const name of files) fs.copyFileSync(path.join(root, name), path.join(output, name));

const privatePath = /(^|\/)(backend|demo|node-backend|data|screenshots)(\/|$)|(^|\/)\.env(?:$|\.)|(^|\/)api\.md$|\.(xlsx|xlsm|csv|sqlite|db)$/i;
function checkOutput(directory, relative = '') {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const name = relative ? `${relative}/${entry.name}` : entry.name;
    if (privatePath.test(name)) throw new Error(`Private path included in Vercel static output: ${name}`);
    if (entry.isDirectory()) checkOutput(path.join(directory, entry.name), name);
  }
}

checkOutput(output);
