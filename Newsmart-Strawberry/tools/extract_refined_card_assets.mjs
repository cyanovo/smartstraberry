import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const sharp = require("./.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp");

const ROOT = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(?:([A-Za-z]:))/, "$1"));
const OUT = path.join(ROOT, "refined-card-assets");
const TEAM = path.join(ROOT, "three-samples", "team-v2-base.png");
const TECH = path.join(ROOT, "three-samples", "tech-base.png");
const RESULTS = path.join(ROOT, "final-image-assets", "results.png");
const THREE = path.join(ROOT, "final-image-assets", "three-point.png");

async function normalized(file) {
  return sharp(file).resize(1280, 720, { fit: "cover" }).png().toBuffer();
}

async function extract(source, name, box, maskPath) {
  const crop = await sharp(source).extract(box).png().toBuffer();
  const mask = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${box.width}" height="${box.height}"><path d="${maskPath}" fill="#fff"/></svg>`);
  await sharp(crop).composite([{ input: mask, blend: "dest-in" }]).png().toFile(path.join(OUT, name));
}

async function main() {
  await fs.rm(OUT, { recursive: true, force: true });
  await fs.mkdir(OUT, { recursive: true });
  const team = await normalized(TEAM);
  const tech = await normalized(TECH);
  const results = await normalized(RESULTS);
  const three = await normalized(THREE);

  await extract(team, "card-green-rail.png", { left: 82, top: 168, width: 460, height: 214 }, "M18 0 H438 L460 22 V192 L438 214 H18 L0 196 V18 Z");
  await extract(team, "card-gold-top.png", { left: 738, top: 168, width: 458, height: 214 }, "M22 0 H438 L458 20 V194 L438 214 H22 L0 194 V20 Z");
  await extract(team, "card-cyan-notch.png", { left: 82, top: 428, width: 410, height: 208 }, "M20 0 H360 L402 42 V82 L380 102 V164 L360 208 H20 L0 188 V20 Z");
  await extract(team, "card-wave.png", { left: 750, top: 428, width: 444, height: 210 }, "M20 0 H424 L444 20 V190 L424 210 H20 L0 190 V20 Z");
  await extract(three, "card-tall-green.png", { left: 48, top: 156, width: 398, height: 466 }, "M24 0 H374 L398 24 V442 L374 466 H24 L0 442 V24 Z");
  await extract(three, "card-tall-cyan.png", { left: 460, top: 156, width: 360, height: 466 }, "M24 0 H336 L360 24 V442 L336 466 H24 L0 442 V24 Z");
  await extract(three, "card-tall-gold.png", { left: 838, top: 156, width: 394, height: 466 }, "M24 0 H370 L394 24 V442 L370 466 H24 L0 442 V24 Z");
  await extract(team, "title-rail.png", { left: 58, top: 78, width: 1148, height: 56 }, "M18 0 H1128 L1148 18 V38 L1128 56 H18 L0 38 V18 Z");
  await extract(team, "collaboration-hub.png", { left: 548, top: 332, width: 170, height: 170 }, "M85 0 A85 85 0 1 1 84.9 0 Z");

  await extract(tech, "code-panel.png", { left: 220, top: 128, width: 612, height: 505 }, "M24 0 H554 L612 58 V447 L554 505 H24 L0 481 V24 Z");

  await extract(results, "metric-ring-gold.png", { left: 952, top: 116, width: 170, height: 170 }, "M85 0 A85 85 0 1 1 84.9 0 Z");
  await extract(results, "evidence-frame.png", { left: 42, top: 162, width: 870, height: 410 }, "M28 0 H834 L870 36 V378 L836 410 H28 L0 382 V28 Z");

  console.log(OUT);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
