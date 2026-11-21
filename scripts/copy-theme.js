// Copy the shared luxury theme into both static folders after Tailwind build.
const fs = require("fs");

const source = "01-FOUNDATION/assets/orion-theme.css";
const targets = [
  "06-STOREFRONT/themes/default/static/css/orion-theme.css",
  "07-ADMIN/static/css/orion-theme.css",
];

for (const target of targets) {
  fs.mkdirSync(require("path").dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
  console.log(`Copied ${source} -> ${target}`);
}
