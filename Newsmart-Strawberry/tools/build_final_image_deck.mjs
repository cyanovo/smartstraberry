import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { Presentation, PresentationFile } from "@oai/artifact-tool";
import { plans } from "./build_generated_visual_ppt.mjs";

const require = createRequire(import.meta.url);
const sharp = require("./.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp");

const ROOT = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(?:([A-Za-z]:))/, "$1"));
const OUT_DIR = path.join(ROOT, "final-image-slides");
const OUT = path.join(ROOT, "\u756a\u8304\u9879\u76ee-\u7cbe\u54c1\u56fe\u7247\u7248.pptx");
const A = path.join(ROOT, "final-image-assets");
const S = path.join(ROOT, "three-samples");
const PREVIEW = path.join(ROOT, "editable-preview");
const DOC = path.join(ROOT, "docx_media");
const REPO = "D:/work/strawberry/Newsmart-Strawberry/test2/test1-main";
const W = 1280;
const H = 720;

const baseFiles = {
  photo: path.join(A, "photo-evidence.png"),
  triple: path.join(A, "three-point.png"),
  architecture: path.join(A, "architecture.png"),
  results: path.join(A, "results.png"),
  tech: path.join(S, "tech-base.png"),
  section: path.join(S, "section-base.png"),
  team: path.join(S, "team-v2-base.png"),
  cover: path.join(PREVIEW, "slide-01.png"),
  blankCover: path.join(ROOT, "generated-assets", "cover.png"),
  roles: path.join(S, "\u6837\u56fe1-\u56e2\u961f\u89d2\u8272\u9875-v2.png"),
  value: path.join(PREVIEW, "slide-30.png"),
};

const sourceFiles = {
  hero: path.join(REPO, "web/public/images/Tomato/tomato-greenhouse-hero.png"),
  zone: path.join(REPO, "web/public/images/Tomato/tomato-zone-overview.png"),
  stages: path.join(REPO, "web/public/images/Tomato/tomato-growth-stages.png"),
  advisor: path.join(REPO, "web/public/images/Tomato/tomato-ai-advisor.png"),
  curveA: path.join(DOC, "image7.png"),
  curveB: path.join(DOC, "image8.png"),
};

const C = { white: "#F7FFF9", mint: "#C9F8E3", cyan: "#62F3D2", gold: "#FFD76D", muted: "#C5E8D8", dark: "#06251D" };

function esc(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" })[c]);
}

function wrap(value, max = 20) {
  const out = [];
  let line = "";
  let units = 0;
  for (const ch of String(value)) {
    const n = ch.charCodeAt(0) > 255 ? 1 : 0.55;
    if (line && units + n > max) {
      out.push(line);
      line = ch;
      units = n;
    } else {
      line += ch;
      units += n;
    }
  }
  if (line) out.push(line);
  return out;
}

function text(x, y, value, opt = {}) {
  const size = opt.size ?? 20;
  const lines = Array.isArray(value) ? value : [value];
  return `<text x="${x}" y="${y}" font-family="Microsoft YaHei, Noto Sans CJK SC, Arial" font-size="${size}" font-weight="${opt.bold ? 800 : 500}" fill="${opt.color ?? C.white}" text-anchor="${opt.anchor ?? "start"}">${lines.map((line, i) => `<tspan x="${x}" dy="${i ? size * (opt.leading ?? 1.42) : 0}">${esc(line)}</tspan>`).join("")}</text>`;
}

function para(x, y, value, max, opt = {}) {
  return text(x, y, wrap(value, max), opt);
}

function nav(active = 0) {
  const labels = ["\u9879\u76ee\u4ecb\u7ecd", "\u603b\u4f53\u601d\u8def", "\u6280\u672f\u8981\u70b9", "\u7cfb\u7edf\u529f\u80fd", "\u9879\u76ee\u521b\u65b0", "\u5e94\u7528\u4ef7\u503c"];
  return labels.map((label, i) => text(116 + i * 207, 45, label, { size: 13, bold: true, color: i === active ? C.white : "#A8DCC8", anchor: "middle" })).join("");
}

function chrome(plan, index) {
  return `${nav(plan.active ?? 0)}${text(72, 122, plan.title, { size: plan.title.length > 22 ? 27 : 31, bold: true })}${plan.sub ? text(1190, 121, plan.sub, { size: 14, bold: true, color: C.gold, anchor: "end" }) : ""}${text(1210, 690, `${String(index).padStart(2, "0")} / 31`, { size: 12, color: "#9FD8C1", anchor: "end" })}`;
}

function badge(x, y, no, color = C.cyan) {
  return `<circle cx="${x}" cy="${y}" r="18" fill="${color}" fill-opacity=".12" stroke="${color}" stroke-width="1.4"/>${text(x, y + 5, no, { size: 13, bold: true, color, anchor: "middle" })}`;
}

function photo(href, x, y, w, h, id) {
  const inset = 8;
  return `<defs><clipPath id="${id}"><path d="M${x + 22} ${y}H${x + w - 24}L${x + w} ${y + 24}V${y + h - 28}L${x + w - 28} ${y + h}H${x + 20}L${x} ${y + h - 20}V${y + 22}Z"/></clipPath></defs><image href="${href}" x="${x + inset}" y="${y + inset}" width="${w - inset * 2}" height="${h - inset * 2}" preserveAspectRatio="xMidYMid slice" clip-path="url(#${id})"/>`;
}

function titleBody(x, y, titleValue, body, max, opt = {}) {
  return `${text(x, y, titleValue, { size: opt.titleSize ?? 24, bold: true, color: opt.color ?? C.white })}${para(x, y + 46, body, max, { size: opt.bodySize ?? 17, color: C.muted, leading: 1.5 })}`;
}

async function dataUri(file) {
  const buf = await sharp(file).png().toBuffer();
  return `data:image/png;base64,${buf.toString("base64")}`;
}

async function baseUri(file) {
  const buf = await sharp(file).resize(W, H, { fit: "cover" }).png().toBuffer();
  return `data:image/png;base64,${buf.toString("base64")}`;
}

function sectionOverlay(plan, index) {
  return `${text(947, 285, plan.no, { size: 118, bold: true, color: "#6FE0A9", anchor: "middle" })}${text(947, 407, plan.title, { size: 46, bold: true, anchor: "middle" })}${text(947, 456, plan.sub, { size: 18, bold: true, color: C.mint, anchor: "middle" })}<path d="M790 485H1104" stroke="#66E3AF" stroke-width="2"/>${text(1210, 690, `${String(index).padStart(2, "0")} / 31`, { size: 12, color: C.mint, anchor: "end" })}`;
}

function agendaOverlay(plan, index) {
  const items = ["\u9879\u76ee\u4ecb\u7ecd", "\u603b\u4f53\u601d\u8def", "\u6280\u672f\u8981\u70b9", "\u7cfb\u7edf\u529f\u80fd\u5c55\u793a", "\u9879\u76ee\u521b\u65b0", "\u5e94\u7528\u4ef7\u503c"];
  return `${text(760, 128, plan.title, { size: 31, bold: true })}${text(1165, 128, plan.sub, { size: 14, bold: true, color: C.gold, anchor: "end" })}${items.map((item, i) => {
    const x = i % 2 ? 1000 : 760;
    const y = 230 + Math.floor(i / 2) * 126;
    return `${badge(x, y, `0${i + 1}`, i % 2 ? C.gold : C.cyan)}${text(x + 32, y + 7, item, { size: 20, bold: true })}<path d="M${x + 32} ${y + 24}H${x + 185}" stroke="${i % 2 ? C.gold : C.cyan}" stroke-opacity=".55"/>`;
  }).join("")}${text(1210, 690, `${String(index).padStart(2, "0")} / 31`, { size: 12, color: C.mint, anchor: "end" })}`;
}

function tripleOverlay(plan, index) {
  const xs = [98, 496, 864];
  return `${chrome(plan, index)}${plan.titles.map((t, i) => `${badge(xs[i], 210, `0${i + 1}`, i === 2 ? C.gold : C.cyan)}${titleBody(xs[i] + 34, 218, t, plan.bodies[i], 16, { titleSize: 23, bodySize: 17, color: i === 2 ? "#FFF2C6" : C.white })}`).join("")}`;
}

function photoOverlay(plan, index, assets) {
  return `${chrome(plan, index)}${photo(assets[plan.image], 58, 176, 552, 454, `ph-${index}`)}${plan.bullets.map((item, i) => {
    const y = 220 + i * (plan.bullets.length > 3 ? 104 : 126);
    return `${badge(700, y, `0${i + 1}`, i === 1 ? C.gold : C.cyan)}${para(738, y + 7, item, 25, { size: 18, color: C.white, leading: 1.45 })}`;
  }).join("")}`;
}

function flowOverlay(plan, index) {
  const spots = [[222, 345], [490, 345], [788, 345], [1080, 345]];
  let groups;
  if (plan.kind === "architecture") {
    groups = [["\u611f\u77e5\u5c42", "\u4f20\u611f\u5668 \u00b7 \u6444\u50cf\u5934 \u00b7 \u6267\u884c\u5668"], ["\u4f20\u8f93\u5c42", "RS485 \u00b7 Modbus \u00b7 MQTT"], ["\u51b3\u7b56\u5c42", "RAG \u00b7 \u5927\u6a21\u578b \u00b7 \u533a\u5757\u94fe"], ["\u5e94\u7528\u5c42", "\u9a7e\u9a76\u8231 \u00b7 \u7269\u8054\u7f51 \u00b7 \u751f\u957f\u6863\u6848"]];
  } else {
    groups = plan.steps.map((s) => s);
    groups.splice(2, 0, ["\u534f\u540c\u51b3\u7b56", "\u77e5\u8bc6\u3001\u73af\u5883\u4e0e\u89c6\u89c9\u7ed3\u679c\u8054\u5408\u5206\u6790"]);
  }
  return `${chrome(plan, index)}${groups.slice(0, 4).map((g, i) => `${badge(spots[i][0], spots[i][1] - 56, `0${i + 1}`, i === 2 ? C.gold : C.cyan)}${text(spots[i][0], spots[i][1], g[0], { size: 21, bold: true, color: i === 2 ? C.gold : C.white, anchor: "middle" })}${text(spots[i][0], spots[i][1] + 36, wrap(g[1], 12).slice(0, 3), { size: 14, color: C.muted, anchor: "middle", leading: 1.4 })}`).join("")}`;
}

function codeOverlay(plan, index) {
  const code = String(plan.code ?? "").trim().split("\n").slice(0, 15);
  return `${nav(plan.active ?? 2)}${text(68, 112, plan.title, { size: plan.title.length > 21 ? 27 : 31, bold: true })}${text(1188, 111, plan.sub, { size: 14, bold: true, color: C.gold, anchor: "end" })}${plan.bullets.map((item, i) => `${text(116, 208 + i * 102, `0${i + 1}`, { size: 15, bold: true, color: C.gold, anchor: "middle" })}${text(116, 232 + i * 102, wrap(item, 8).slice(0, 2), { size: 13, bold: true, anchor: "middle", leading: 1.35 })}`).join("")}${code.map((line, i) => `<text x="270" y="205" font-family="Cascadia Mono, Consolas, monospace" font-size="14" fill="${line.trim().startsWith("#") ? "#83BFA8" : line.includes("def ") || line.includes("async ") ? C.gold : "#C8F6E0"}"><tspan x="270" dy="${i ? 22 : 0}">${esc(line)}</tspan></text>`).join("")}${text(920, 225, "\u5173\u952e\u94fe\u8def", { size: 23, bold: true })}${text(920, 262, ["\u6570\u636e\u53ef\u8ffd\u8e2a", "\u7ed3\u679c\u53ef\u6821\u9a8c"], { size: 17, color: C.muted, leading: 1.55 })}${text(1030, 575, "\u5b9e\u65f6\u6570\u636e\u6d41", { size: 16, bold: true, anchor: "middle" })}${text(1210, 690, `${String(index).padStart(2, "0")} / 31`, { size: 12, color: C.mint, anchor: "end" })}`;
}

function curveOverlay(plan, index, assets) {
  return `${chrome(plan, index)}${photo(assets.curveA, 58, 190, 410, 375, `c1-${index}`)}${photo(assets.curveB, 490, 190, 410, 375, `c2-${index}`)}${text(1005, 246, "0.23", { size: 34, bold: true, color: C.gold, anchor: "middle" })}${text(1005, 278, "\u521d\u59cb\u6a21\u578b\u51c6\u786e\u7387", { size: 14, color: C.muted, anchor: "middle" })}${text(1005, 404, "0.96", { size: 34, bold: true, color: C.cyan, anchor: "middle" })}${text(1005, 436, "\u6570\u636e\u589e\u5f3a\u540e\u51c6\u786e\u7387", { size: 14, color: C.muted, anchor: "middle" })}${text(1005, 562, "\u663e\u8457\u63d0\u5347", { size: 26, bold: true, color: C.white, anchor: "middle" })}${text(640, 650, "\u65cb\u8f6c\u4e0e\u9971\u548c\u5ea6\u6270\u52a8\u589e\u5f3a\u9c81\u68d2\u6027", { size: 17, bold: true, color: C.gold, anchor: "middle" })}`;
}

function quadOverlay(plan, index) {
  const coords = [[130, 210], [780, 210], [130, 478], [780, 478]];
  return `${chrome(plan, index)}${plan.cards.map((item, i) => `${badge(coords[i][0], coords[i][1], `0${i + 1}`, i === 1 ? C.gold : C.cyan)}${titleBody(coords[i][0] + 34, coords[i][1] + 7, item[0], item[1], 22, { titleSize: 22, bodySize: 16 })}`).join("")}${text(631, 410, "AI", { size: 28, bold: true, color: C.cyan, anchor: "middle" })}`;
}

function sixOverlay(plan, index) {
  const modules = [["\u756a\u8304\u9a7e\u9a76\u8231", "\u6e29\u5ba4\u6574\u4f53\u6001\u52bf"], ["\u667a\u80fd\u7269\u8054\u7f51", "\u4f20\u611f\u5668\u4e0e\u8bbe\u5907\u63a7\u5236"], ["\u751f\u957f\u6863\u6848", "\u9636\u6bb5\u8bb0\u5f55\u4e0e\u517b\u62a4\u5efa\u8bae"], ["\u6210\u719f\u5ea6\u4e2d\u5fc3", "\u62cd\u7167\u68c0\u6d4b\u4e0e\u91c7\u6458\u5efa\u8bae"], ["AI\u65e5\u5fd7", "\u5bf9\u8bdd\u5386\u53f2\u4e0e\u51b3\u7b56\u8ffd\u6eaf"], ["\u540e\u53f0\u7ba1\u7406", "\u57fa\u7840\u6570\u636e\u7ef4\u62a4"]];
  const pos = [[180, 246], [180, 365], [180, 484], [1080, 246], [1080, 365], [1080, 484]];
  return `${chrome(plan, index)}${modules.map((m, i) => `${badge(pos[i][0], pos[i][1], `0${i + 1}`, i % 2 ? C.gold : C.cyan)}${text(pos[i][0] + (i < 3 ? 34 : -34), pos[i][1] + 5, m[0], { size: 18, bold: true, anchor: i < 3 ? "start" : "end" })}${text(pos[i][0] + (i < 3 ? 34 : -34), pos[i][1] + 30, m[1], { size: 13, color: C.muted, anchor: i < 3 ? "start" : "end" })}`).join("")}${text(640, 345, "\u516d\u5927\u6a21\u5757", { size: 27, bold: true, color: C.gold, anchor: "middle" })}${text(640, 381, "\u627f\u8f7d\u5b8c\u6574\u4e1a\u52a1\u6d41\u7a0b", { size: 16, color: C.mint, anchor: "middle" })}`;
}

function resultsOverlay(plan, index, assets) {
  const metrics = [["+20%", "\u9884\u8ba1\u4ea7\u91cf\u63d0\u5347"], ["92%", "\u4f18\u8d28\u679c\u7387"], ["-30%", "\u4eba\u5de5\u6210\u672c"]];
  return `${chrome(plan, index)}${photo(assets.zone, 46, 174, 862, 390, `res-${index}`)}${metrics.map((m, i) => `${text(1042, 224 + i * 166, m[0], { size: 30, bold: true, color: i === 1 ? C.gold : C.cyan, anchor: "middle" })}${text(1042, 256 + i * 166, m[1], { size: 14, color: C.muted, anchor: "middle" })}`).join("")}${text(640, 651, "\u5f62\u6210\u7cfb\u7edf\u539f\u578b\u3001\u6280\u80fd\u6210\u679c\u4e0e\u6301\u7eed\u63a8\u5e7f\u57fa\u7840", { size: 18, bold: true, color: C.gold, anchor: "middle" })}`;
}

async function renderSlide(plan, index, bases, assets) {
  if (plan.kind === "cover") return sharp(baseFiles.cover).resize(W, H, { fit: "cover" }).png().toBuffer();
  if (plan.kind === "roles") return sharp(baseFiles.roles).resize(W, H, { fit: "cover" }).png().toBuffer();
  if (plan.kind === "value") return sharp(baseFiles.value).resize(W, H, { fit: "cover" }).png().toBuffer();

  let baseKey = "triple";
  let overlay = "";
  if (plan.kind === "section") { baseKey = "section"; overlay = sectionOverlay(plan, index); }
  else if (plan.kind === "agenda") { baseKey = "section"; overlay = agendaOverlay(plan, index); }
  else if (plan.kind === "triple") { baseKey = "triple"; overlay = tripleOverlay(plan, index); }
  else if (plan.kind === "photo") { baseKey = "photo"; overlay = photoOverlay(plan, index, assets); }
  else if (plan.kind === "flow" || plan.kind === "architecture") { baseKey = "architecture"; overlay = flowOverlay(plan, index); }
  else if (plan.kind === "code") { baseKey = "tech"; overlay = codeOverlay(plan, index); }
  else if (plan.kind === "curves") { baseKey = "results"; overlay = curveOverlay(plan, index, assets); }
  else if (plan.kind === "quad") { baseKey = "team"; overlay = quadOverlay(plan, index); }
  else if (plan.kind === "six") { baseKey = "architecture"; overlay = sixOverlay(plan, index); }
  else if (plan.kind === "results") { baseKey = "results"; overlay = resultsOverlay(plan, index, assets); }
  else if (plan.kind === "thanks") {
    const cover = bases.blankCover;
    overlay = `<rect width="1280" height="720" fill="#021A14" opacity=".30"/><path d="M250 228H1030L1060 258V470L1030 500H250L220 470V258Z" fill="#04261D" fill-opacity=".72" stroke="${C.cyan}" stroke-width="1.5"/>${text(640, 332, "\u656c\u8bf7\u5404\u4f4d\u4e13\u5bb6\u6307\u5bfc", { size: 52, bold: true, color: C.gold, anchor: "middle" })}${text(640, 398, "\u6167\u773c\u8bc6\u201c\u682a\u201d \u00b7 \u667a\u57f9\u9c9c\u679c", { size: 25, bold: true, color: C.cyan, anchor: "middle" })}`;
    return sharp(Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><image href="${cover}" width="1280" height="720"/>${overlay}</svg>`)).png().toBuffer();
  }

  return sharp(Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><image href="${bases[baseKey]}" width="1280" height="720"/>${overlay}</svg>`)).png().toBuffer();
}

async function main() {
  await fs.rm(OUT_DIR, { recursive: true, force: true });
  await fs.mkdir(OUT_DIR, { recursive: true });
  const bases = {};
  for (const [key, file] of Object.entries(baseFiles)) bases[key] = await baseUri(file);
  const assets = {};
  for (const [key, file] of Object.entries(sourceFiles)) assets[key] = await dataUri(file);

  const files = [];
  for (let i = 0; i < plans.length; i++) {
    const png = await renderSlide(plans[i], i + 1, bases, assets);
    const file = path.join(OUT_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`);
    await fs.writeFile(file, png);
    files.push(file);
  }

  const deck = Presentation.create({ slideSize: { width: W, height: H } });
  for (const file of files) {
    const slide = deck.slides.add();
    const bytes = await fs.readFile(file);
    slide.images.add({
      blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
      contentType: "image/png",
      alt: "\u756a\u8304\u7cbe\u51c6\u751f\u957f\u667a\u63a7\u7cfb\u7edf\u804c\u4e1a\u6280\u80fd\u5927\u8d5b\u6c47\u62a5\u9875\u9762",
      fit: "cover",
      position: { left: 0, top: 0, width: W, height: H },
    });
  }
  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(OUT);
  console.log(JSON.stringify({ out: OUT, slides: files.length, images: OUT_DIR }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
