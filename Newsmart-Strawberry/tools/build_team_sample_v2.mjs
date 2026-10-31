import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const sharp = require("C:/Users/cyan/.codex/visualizations/2026/08/10/019fea44-4795-7673-87e6-99e69014ad23/tomato_ppt/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp");

const ROOT = "C:/Users/cyan/.codex/visualizations/2026/08/10/019fea44-4795-7673-87e6-99e69014ad23/tomato_ppt/three-samples";
const W = 1280;
const H = 720;

function esc(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" })[c]);
}

function text(x, y, value, opt = {}) {
  const size = opt.size ?? 20;
  const lines = Array.isArray(value) ? value : [value];
  return `<text x="${x}" y="${y}" font-family="Microsoft YaHei, Noto Sans CJK SC, Arial" font-size="${size}" font-weight="${opt.bold ? 800 : 500}" fill="${opt.color ?? "#F6FFF9"}" text-anchor="${opt.anchor ?? "start"}">${lines.map((line, i) => `<tspan x="${x}" dy="${i ? size * (opt.leading ?? 1.45) : 0}">${esc(line)}</tspan>`).join("")}</text>`;
}

function tag(x, y, width, label, color = "#63F2CA") {
  return `<g><rect x="${x}" y="${y}" width="${width}" height="24" rx="3" fill="${color}" fill-opacity="0.13" stroke="${color}" stroke-opacity="0.75"/><text x="${x + width / 2}" y="${y + 17}" font-family="Microsoft YaHei, Arial" font-size="12" font-weight="700" fill="${color}" text-anchor="middle">${esc(label)}</text></g>`;
}

function indexBadge(x, y, number, color) {
  return `<g><circle cx="${x}" cy="${y}" r="17" fill="${color}" fill-opacity="0.16" stroke="${color}" stroke-width="1.4"/><text x="${x}" y="${y + 5}" font-family="Arial" font-size="13" font-weight="800" fill="${color}" text-anchor="middle">${number}</text></g>`;
}

const navLabels = [
  "\u9879\u76ee\u4ecb\u7ecd",
  "\u603b\u4f53\u601d\u8def",
  "\u6280\u672f\u8981\u70b9",
  "\u7cfb\u7edf\u529f\u80fd",
  "\u9879\u76ee\u521b\u65b0",
  "\u5e94\u7528\u4ef7\u503c",
];

const nav = navLabels.map((label, i) => {
  const active = i === 0;
  return text(120 + i * 166, 47, label, {
    size: 13,
    bold: true,
    color: active ? "#FFFFFF" : "#BDEEDC",
    anchor: "middle",
  });
}).join("");

const svg = `
  ${nav}
  ${text(75, 112, "\u56e2\u961f\u89d2\u8272\u4e0e\u5c97\u4f4d\u5206\u5de5", { size: 29, bold: true })}
  ${text(1160, 111, "TEAM COLLABORATION", { size: 13, bold: true, color: "#78EEC9", anchor: "end" })}

  ${indexBadge(132, 211, "01", "#47E5A9")}
  ${text(166, 216, "\u9879\u76ee\u7ecf\u7406 / \u6eaf\u6e90\u5de5\u7a0b\u5e08", { size: 25, bold: true })}
  ${text(132, 263, ["\u7edf\u7b79\u67b6\u6784\u3001\u8fdb\u5ea6\u4e0e\u73b0\u573a\u4ea4\u4ed8", "\u6784\u5efa\u533a\u5757\u94fe\u5b58\u8bc1\u4e0e\u53ef\u4fe1\u6eaf\u6e90"], { size: 17, color: "#D6F5E8", leading: 1.6 })}
  ${tag(132, 324, 92, "\u9879\u76ee\u7ba1\u7406")}
  ${tag(234, 324, 92, "\u53ef\u4fe1\u6eaf\u6e90")}
  ${tag(336, 324, 92, "\u6210\u679c\u4ea4\u4ed8")}

  ${indexBadge(780, 211, "02", "#FFD46C")}
  ${text(814, 216, "AI\u5e94\u7528\u5de5\u7a0b\u5e08", { size: 25, bold: true, color: "#FFF6D6" })}
  ${text(780, 263, ["\u5efa\u8bbe\u77e5\u8bc6\u5e93\u4e0e RAG \u68c0\u7d22\u94fe\u8def", "\u5b9e\u73b0\u5927\u6a21\u578b\u5206\u6790\u4e0e\u591a\u667a\u80fd\u4f53\u51b3\u7b56"], { size: 17, color: "#F4F1DA", leading: 1.6 })}
  ${tag(780, 324, 78, "RAG", "#FFD46C")}
  ${tag(868, 324, 92, "\u77e5\u8bc6\u5e93", "#FFD46C")}
  ${tag(970, 324, 112, "\u591a\u667a\u80fd\u4f53", "#FFD46C")}

  ${indexBadge(132, 466, "03", "#64E9F0")}
  ${text(166, 471, "\u5d4c\u5165\u5f0f\u5de5\u7a0b\u5e08", { size: 25, bold: true })}
  ${text(132, 518, ["\u4f20\u611f\u5668\u6570\u636e\u91c7\u96c6\u4e0e Modbus \u901a\u4fe1", "MQTT \u4e0a\u4f20\u4e0e\u8bbe\u5907\u8054\u52a8\u63a7\u5236"], { size: 17, color: "#D6F5F1", leading: 1.6 })}
  ${tag(132, 579, 92, "\u4f20\u611f\u91c7\u96c6", "#64E9F0")}
  ${tag(234, 579, 92, "Modbus", "#64E9F0")}
  ${tag(336, 579, 76, "MQTT", "#64E9F0")}

  ${indexBadge(780, 466, "04", "#7BF0C5")}
  ${text(814, 471, "AI\u89c6\u89c9\u5de5\u7a0b\u5e08", { size: 25, bold: true })}
  ${text(780, 518, ["\u5b8c\u6210\u6570\u636e\u96c6\u5904\u7406\u4e0e YOLO \u8bad\u7ec3", "\u8d1f\u8d23\u6a21\u578b\u8bc4\u4f30\u4e0e\u756a\u8304\u6210\u719f\u5ea6\u8bc6\u522b"], { size: 17, color: "#D8F7EB", leading: 1.6 })}
  ${tag(780, 579, 92, "\u6570\u636e\u96c6", "#7BF0C5")}
  ${tag(882, 579, 92, "YOLO", "#7BF0C5")}
  ${tag(984, 579, 92, "\u89c6\u89c9\u8bc6\u522b", "#7BF0C5")}

  ${text(631, 402, "\u534f\u540c", { size: 24, bold: true, anchor: "middle" })}
  ${text(631, 428, "\u95ed\u73af", { size: 24, bold: true, color: "#73F2D0", anchor: "middle" })}
  ${text(631, 670, "\u611f\u77e5  \u00b7  \u8ba4\u77e5  \u00b7  \u51b3\u7b56  \u00b7  \u63a7\u5236  \u00b7  \u6eaf\u6e90", { size: 14, bold: true, color: "#BCEEDC", anchor: "middle" })}
`;

const base = await sharp(path.join(ROOT, "team-v2-base.png"))
  .resize(W, H, { fit: "cover" })
  .png()
  .toBuffer();

await sharp(base)
  .composite([{ input: Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">${svg}</svg>`) }])
  .png()
  .toFile(path.join(ROOT, "\u6837\u56fe1-\u56e2\u961f\u89d2\u8272\u9875-v2.png"));

console.log(path.join(ROOT, "\u6837\u56fe1-\u56e2\u961f\u89d2\u8275-v2.png"));
