// Ensure built CSS ends with a newline so pre-commit's `end-of-file-fixer`
// does not create a diff between generated and committed assets in CI.
const fs = require("fs");

const targets = [
  "06-STOREFRONT/themes/default/static/css/tailwind.css",
  "07-ADMIN/static/css/tailwind.css",
];

for (const file of targets) {
  const content = fs.readFileSync(file, "utf8");
  if (!content.endsWith("\n")) fs.writeFileSync(file, content + "\n", "utf8");
}
