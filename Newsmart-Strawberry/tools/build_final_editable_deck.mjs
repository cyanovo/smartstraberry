import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { Presentation, PresentationFile } from "@oai/artifact-tool";
import { plans } from "./build_generated_visual_ppt.mjs";

const require = createRequire(import.meta.url);
const sharp = require("./.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp");

const ROOT = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(?:([A-Za-z]:))/, "$1"));
const OUT = path.join(ROOT, "番茄项目-逐字稿对齐可编辑版.pptx");
const PREVIEW = path.join(ROOT, "final-editable-preview");
const W = 1280;
const H = 720;
const REPO = "D:/work/strawberry/Newsmart-Strawberry/test2/test1-main";

const files = {
  cover: path.join(ROOT, "generated-assets", "cover.png"),
  stage: path.join(ROOT, "generated-assets", "clean-stage.png"),
  section: path.join(ROOT, "three-samples", "section-base.png"),
  hero: path.join(REPO, "web/public/images/Tomato/tomato-greenhouse-hero.png"),
  zone: path.join(REPO, "web/public/images/Tomato/tomato-zone-overview.png"),
  stages: path.join(REPO, "web/public/images/Tomato/tomato-growth-stages.png"),
  advisor: path.join(REPO, "web/public/images/Tomato/tomato-ai-advisor.png"),
  curveA: path.join(ROOT, "docx_media", "image7.png"),
  curveB: path.join(ROOT, "docx_media", "image8.png"),
};

const cardFiles = {
  green: path.join(ROOT, "refined-card-assets", "card-green-rail.png"),
  gold: path.join(ROOT, "refined-card-assets", "card-gold-top.png"),
  notch: path.join(ROOT, "refined-card-assets", "card-cyan-notch.png"),
  wave: path.join(ROOT, "refined-card-assets", "card-wave.png"),
  tallGreen: path.join(ROOT, "refined-card-assets", "card-tall-green.png"),
  tallCyan: path.join(ROOT, "refined-card-assets", "card-tall-cyan.png"),
  tallGold: path.join(ROOT, "refined-card-assets", "card-tall-gold.png"),
  title: path.join(ROOT, "refined-card-assets", "title-rail.png"),
  hub: path.join(ROOT, "refined-card-assets", "collaboration-hub.png"),
  code: path.join(ROOT, "refined-card-assets", "code-panel.png"),
  ring: path.join(ROOT, "refined-card-assets", "metric-ring-gold.png"),
  evidence: path.join(ROOT, "refined-card-assets", "evidence-frame.png"),
};

let refined = {};

const C = {
  white: "#F7FFF9",
  mint: "#C9F8E3",
  cyan: "#62F3D2",
  gold: "#FFD76D",
  muted: "#C5E8D8",
  deep: "#07352A",
  green: "#47E5A9",
};

async function png(file) {
  return sharp(file).resize(W, H, { fit: "cover" }).png().toBuffer();
}

async function assetPng(file) {
  return sharp(file).png().toBuffer();
}

function shape(slide, geometry, x, y, w, h, fill = "none", lineFill = "none", lineWidth = 0) {
  return slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
  });
}

function line(slide, x, y, w, h, color, width = 1) {
  if (w < 0) {
    x += w;
    w = Math.abs(w);
  }
  if (h < 0) {
    y += h;
    h = Math.abs(h);
  }
  return shape(slide, "line", x, y, Math.max(w, 0.01), Math.max(h, 0.01), "none", color, width);
}

function text(slide, value, x, y, w, h, opt = {}) {
  const box = shape(slide, "textbox", x, y, w, h);
  box.text = String(value);
  box.text.style = {
    fontFamily: opt.font ?? "Microsoft YaHei",
    fontSize: opt.size ?? 18,
    bold: opt.bold ?? false,
    color: opt.color ?? C.white,
    alignment: opt.align ?? "left",
    verticalAlignment: opt.valign ?? "top",
  };
  return box;
}

function image(slide, bytes, x, y, w, h, alt, fit = "cover") {
  return slide.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png",
    alt,
    fit,
    position: { left: x, top: y, width: w, height: h },
    geometry: "roundRect",
    borderRadius: "rounded-sm",
  });
}

function rawImage(slide, bytes, x, y, w, h, alt) {
  return slide.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png",
    alt,
    fit: "fill",
    position: { left: x, top: y, width: w, height: h },
  });
}

function background(slide, bytes) {
  image(slide, bytes, 0, 0, W, H, "番茄温室科技视觉背景");
}

function badge(slide, x, y, no, color = C.cyan) {
  shape(slide, "ellipse", x - 18, y - 18, 36, 36, C.deep, color, 1.2);
  text(slide, no, x - 18, y - 9, 36, 20, { size: 13, bold: true, color, align: "center" });
}

function tag(slide, x, y, w, label, color = C.cyan) {
  shape(slide, "roundRect", x, y, w, 24, C.deep, color, 1);
  text(slide, label, x + 4, y + 4, w - 8, 16, { size: 12, bold: true, color, align: "center" });
}

function card(slide, x, y, w, h, accent = C.cyan, variant = 0) {
  const horizontal = [refined.green, refined.gold, refined.notch, refined.wave];
  const tall = [refined.tallGreen, refined.tallCyan, refined.tallGold];
  const variants = h / w > 0.78 ? tall : horizontal;
  rawImage(slide, variants[variant % variants.length], x, y, w, h, `独立可编辑的精致卡片背景 ${variant + 1}`);
  return { x, y, w, h };
}

function titleRail(slide, titleValue, subtitle = "") {
  rawImage(slide, refined.title, 42, 82, 1196, 58, "独立可编辑的标题轨道背景");
  text(slide, titleValue, 70, 94, 820, 38, { size: titleValue.length > 22 ? 27 : 31, bold: true });
  if (subtitle) text(slide, subtitle, 900, 101, 288, 24, { size: 14, bold: true, color: C.gold, align: "right" });
}

function nav(slide, active = 0) {
  const labels = ["项目介绍", "总体思路", "技术要点", "系统功能", "项目创新", "应用价值"];
  labels.forEach((label, i) => text(slide, label, 55 + i * 207, 32, 122, 22, {
    size: 13,
    bold: true,
    color: i === active ? C.white : "#A8DCC8",
    align: "center",
  }));
}

function chrome(slide, plan, index) {
  nav(slide, plan.active ?? 0);
  titleRail(slide, plan.title, plan.sub);
  text(slide, `${String(index).padStart(2, "0")} / 31`, 1150, 680, 60, 18, { size: 12, color: "#9FD8C1", align: "right" });
}

function titleBody(slide, x, y, w, titleValue, body, opt = {}) {
  text(slide, titleValue, x, y, w, 36, { size: opt.titleSize ?? 23, bold: true, color: opt.color ?? C.white });
  text(slide, body, x, y + 48, w, opt.bodyHeight ?? 110, { size: opt.bodySize ?? 17, color: C.muted });
}

function addCover(slide, assets) {
  background(slide, assets.cover);
  shape(slide, "rect", 70, 82, 9, 72, "#FF9748");
  text(slide, "番茄温室智能管控平台", 110, 94, 430, 34, { size: 20, bold: true, color: C.mint });
  text(slide, "慧眼识“株”\n智培鲜果", 110, 212, 520, 150, { size: 58, bold: true, color: C.gold });
  text(slide, "番茄精准生长智控系统", 112, 454, 500, 44, { size: 31, bold: true, color: C.cyan });
  text(slide, "职业技能大赛项目汇报", 112, 512, 410, 32, { size: 22 });
  line(slide, 108, 566, 412, 0, "#FF9748", 3);
}

function addRoles(slide, assets, index) {
  background(slide, assets.stage);
  nav(slide, 0);
  titleRail(slide, "团队角色与岗位分工", "TEAM COLLABORATION");
  const roles = [
    [132, 211, "01", "项目经理 / 溯源工程师", "统筹架构、进度与现场交付\n构建区块链存证与可信溯源", ["项目管理", "可信溯源", "成果交付"], C.green],
    [780, 211, "02", "AI应用工程师", "建设知识库与 RAG 检索链路\n实现大模型分析与多智能体决策", ["RAG", "知识库", "多智能体"], C.gold],
    [132, 466, "03", "嵌入式工程师", "传感器数据采集与 Modbus 通信\nMQTT 上传与设备联动控制", ["传感采集", "Modbus", "MQTT"], C.cyan],
    [780, 466, "04", "AI视觉工程师", "完成数据集处理与 YOLO 训练\n负责模型评估与番茄成熟度识别", ["数据集", "YOLO", "视觉识别"], C.green],
  ];
  roles.forEach(([x, y, no, titleValue, body, tags, color]) => {
    card(slide, x - 48, y - 42, 455, 192, color, Number(no));
    badge(slide, x, y, no, color);
    text(slide, titleValue, x + 34, y - 16, 380, 34, { size: 25, bold: true, color: no === "02" ? "#FFF6D6" : C.white });
    text(slide, body, x, y + 34, 410, 64, { size: 17, color: C.muted });
    let tx = x;
    tags.forEach((label, i) => {
      const width = i === 2 && label.length > 4 ? 108 : 92;
      tag(slide, tx, y + 113, width, label, color);
      tx += width + 10;
    });
  });
  line(slide, 535, 300, 65, 65, C.cyan, 1.5);
  line(slide, 745, 300, -75, 65, C.cyan, 1.5);
  line(slide, 535, 520, 65, -68, C.cyan, 1.5);
  line(slide, 745, 520, -75, -68, C.cyan, 1.5);
  rawImage(slide, refined.hub, 550, 330, 170, 170, "独立可编辑的协同闭环圆环背景");
  text(slide, "协同\n闭环", 595, 385, 80, 62, { size: 24, bold: true, color: C.cyan, align: "center" });
  text(slide, "感知 · 认知 · 决策 · 控制 · 溯源", 470, 660, 330, 20, { size: 14, bold: true, color: C.mint, align: "center" });
  text(slide, `${String(index).padStart(2, "0")} / 31`, 1150, 680, 60, 18, { size: 12, color: "#9FD8C1", align: "right" });
}

function addAgenda(slide, plan, assets, index) {
  background(slide, assets.stage);
  nav(slide, 0);
  titleRail(slide, plan.title, plan.sub);
  ["项目介绍", "总体思路", "技术要点", "系统功能展示", "项目创新", "应用价值"].forEach((item, i) => {
    const x = i % 2 ? 665 : 80;
    const y = 180 + Math.floor(i / 2) * 138;
    card(slide, x, y, 535, 102, i % 2 ? C.gold : C.cyan, i);
    badge(slide, x + 50, y + 50, `0${i + 1}`, i % 2 ? C.gold : C.cyan);
    text(slide, item, x + 92, y + 34, 380, 32, { size: 22, bold: true });
  });
  text(slide, `${String(index).padStart(2, "0")} / 31`, 1150, 680, 60, 18, { size: 12, color: "#267754", align: "right" });
}

function addSection(slide, plan, assets, index) {
  background(slide, assets.section);
  text(slide, plan.no, 820, 198, 255, 145, { size: 118, bold: true, color: "#6FE0A9", align: "center" });
  text(slide, plan.title, 760, 355, 375, 58, { size: 46, bold: true, align: "center" });
  text(slide, plan.sub, 750, 421, 395, 30, { size: 18, bold: true, color: C.mint, align: "center" });
  line(slide, 790, 485, 314, 0, "#66E3AF", 2);
  text(slide, `${String(index).padStart(2, "0")} / 31`, 1150, 680, 60, 18, { size: 12, color: "#267754", align: "right" });
}

function addTriple(slide, plan, assets, index) {
  background(slide, assets.stage);
  chrome(slide, plan, index);
  const xs = [98, 496, 864];
  plan.titles.forEach((titleValue, i) => {
    card(slide, xs[i] - 34, 170, i === 1 ? 330 : 350, 430, i === 2 ? C.gold : C.cyan, i);
    badge(slide, xs[i], 210, `0${i + 1}`, i === 2 ? C.gold : C.cyan);
    titleBody(slide, xs[i] + 34, 196, i === 1 ? 300 : 330, titleValue, plan.bodies[i], { color: i === 2 ? "#FFF2C6" : C.white });
  });
}

function addPhoto(slide, plan, assets, index) {
  background(slide, assets.stage);
  chrome(slide, plan, index);
  card(slide, 54, 172, 558, 456, C.cyan, 0);
  image(slide, assets[plan.image], 66, 184, 535, 435, `可替换内容图片：${plan.title}`);
  card(slide, 650, 172, 548, 456, C.green, 2);
  plan.bullets.forEach((item, i) => {
    const y = 220 + i * (plan.bullets.length > 3 ? 104 : 126);
    badge(slide, 700, y, `0${i + 1}`, i === 1 ? C.gold : C.cyan);
    text(slide, item, 738, y - 15, 430, 68, { size: 18 });
  });
}

function addFlow(slide, plan, assets, index) {
  background(slide, assets.stage);
  chrome(slide, plan, index);
  let groups;
  if (plan.kind === "architecture") {
    groups = [["感知层", "传感器 · 摄像头 · 执行器"], ["传输层", "RS485 · Modbus · MQTT"], ["决策层", "RAG · 大模型 · 区块链"], ["应用层", "驾驶舱 · 物联网 · 生长档案"]];
  } else {
    groups = [...plan.steps];
    groups.splice(2, 0, ["协同决策", "知识、环境与视觉结果联合分析"]);
  }
  const spots = [[222, 345], [490, 345], [788, 345], [1080, 345]];
  line(slide, 320, 345, 70, 0, C.cyan, 3);
  line(slide, 590, 345, 92, 0, C.gold, 3);
  line(slide, 888, 345, 92, 0, C.cyan, 3);
  groups.slice(0, 4).forEach((entry, i) => {
    const widths = [235, 235, 250, 235];
    card(slide, spots[i][0] - widths[i] / 2, 220, widths[i], 260, i === 2 ? C.gold : C.cyan, i);
    badge(slide, spots[i][0], spots[i][1] - 56, `0${i + 1}`, i === 2 ? C.gold : C.cyan);
    text(slide, entry[0], spots[i][0] - 100, spots[i][1] - 8, 200, 32, { size: 21, bold: true, color: i === 2 ? C.gold : C.white, align: "center" });
    text(slide, entry[1], spots[i][0] - 108, spots[i][1] + 31, 216, 70, { size: 14, color: C.muted, align: "center" });
  });
}

function addCode(slide, plan, assets, index) {
  background(slide, assets.stage);
  nav(slide, plan.active ?? 2);
  titleRail(slide, plan.title, plan.sub);
  rawImage(slide, refined.code, 220, 166, 650, 430, "独立可编辑的精致代码面板背景");
  plan.bullets.forEach((item, i) => {
    card(slide, 48, 172 + i * 103, 150, 78, i % 2 ? C.cyan : C.gold, i);
    text(slide, `0${i + 1}`, 58, 186 + i * 103, 34, 20, { size: 14, bold: true, color: C.gold, align: "center" });
    text(slide, item, 92, 183 + i * 103, 96, 54, { size: 12, bold: true, align: "center" });
  });
  text(slide, String(plan.code ?? "").trim().split("\n").slice(0, 15).join("\n"), 250, 207, 590, 350, { size: 14, color: "#C8F6E0", font: "Cascadia Mono" });
  card(slide, 900, 172, 300, 168, C.green, 1);
  text(slide, "关键链路", 930, 203, 210, 32, { size: 23, bold: true });
  text(slide, "数据可追踪\n结果可校验", 930, 250, 220, 66, { size: 17, color: C.muted });
  card(slide, 900, 370, 300, 226, C.gold, 2);
  text(slide, "实时数据流", 950, 470, 200, 28, { size: 20, bold: true, color: C.gold, align: "center" });
  text(slide, `${String(index).padStart(2, "0")} / 31`, 1150, 680, 60, 18, { size: 12, color: "#9FD8C1", align: "right" });
}

function addCurves(slide, plan, assets, index) {
  background(slide, assets.stage);
  chrome(slide, plan, index);
  rawImage(slide, refined.evidence, 54, 184, 418, 378, "独立可编辑的曲线证据卡片背景");
  rawImage(slide, refined.evidence, 486, 184, 418, 378, "独立可编辑的曲线证据卡片背景");
  image(slide, assets.curveA, 66, 198, 394, 350, "初始模型评估曲线", "contain");
  image(slide, assets.curveB, 498, 198, 394, 350, "数据增强后评估曲线", "contain");
  line(slide, 1010, 230, 0, 330, C.gold, 1.5);
  [230, 388, 546].forEach((y, i) => rawImage(slide, refined.ring, 956, y - 54, 108, 108, `独立可编辑的指标圆环 ${i + 1}`));
  text(slide, "0.23", 958, 212, 95, 42, { size: 34, bold: true, color: C.gold, align: "center" });
  text(slide, "初始模型准确率", 942, 263, 130, 22, { size: 14, color: C.muted, align: "center" });
  text(slide, "0.96", 958, 370, 95, 42, { size: 34, bold: true, color: C.cyan, align: "center" });
  text(slide, "数据增强后准确率", 930, 421, 155, 22, { size: 14, color: C.muted, align: "center" });
  text(slide, "显著提升", 940, 525, 135, 38, { size: 26, bold: true, align: "center" });
  text(slide, "旋转与饱和度扰动增强鲁棒性", 380, 632, 520, 24, { size: 17, bold: true, color: C.gold, align: "center" });
}

function addQuad(slide, plan, assets, index) {
  background(slide, assets.stage);
  chrome(slide, plan, index);
  const coords = [[130, 210], [780, 210], [130, 478], [780, 478]];
  plan.cards.forEach((entry, i) => {
    card(slide, coords[i][0] - 52, coords[i][1] - 42, 430, 174, i === 1 ? C.gold : C.cyan, i);
    badge(slide, coords[i][0], coords[i][1], `0${i + 1}`, i === 1 ? C.gold : C.cyan);
    titleBody(slide, coords[i][0] + 34, coords[i][1] - 14, 390, entry[0], entry[1], { titleSize: 22, bodySize: 16, bodyHeight: 70 });
  });
  rawImage(slide, refined.hub, 570, 330, 140, 140, "独立可编辑的 AI 中心圆环");
  text(slide, "AI", 609, 383, 62, 36, { size: 28, bold: true, color: C.cyan, align: "center" });
}

function addSix(slide, plan, assets, index) {
  background(slide, assets.stage);
  chrome(slide, plan, index);
  const modules = [["番茄驾驶舱", "温室整体态势"], ["智能物联网", "传感器与设备控制"], ["生长档案", "阶段记录与养护建议"], ["成熟度中心", "拍照检测与采摘建议"], ["AI日志", "对话历史与决策追溯"], ["后台管理", "基础数据维护"]];
  const pos = [[180, 246], [180, 365], [180, 484], [1080, 246], [1080, 365], [1080, 484]];
  line(slide, 420, 270, 170, 80, C.cyan, 1.2);
  line(slide, 420, 390, 170, 0, C.gold, 1.2);
  line(slide, 420, 510, 170, -80, C.cyan, 1.2);
  line(slide, 860, 270, -170, 80, C.gold, 1.2);
  line(slide, 860, 390, -170, 0, C.cyan, 1.2);
  line(slide, 860, 510, -170, -80, C.gold, 1.2);
  modules.forEach((entry, i) => {
    const left = i < 3;
    card(slide, left ? 62 : 876, pos[i][1] - 48, 342, 96, i % 2 ? C.gold : C.cyan, i);
    badge(slide, pos[i][0], pos[i][1], `0${i + 1}`, i % 2 ? C.gold : C.cyan);
    text(slide, entry[0], left ? pos[i][0] + 34 : pos[i][0] - 220, pos[i][1] - 15, 186, 28, { size: 18, bold: true, align: left ? "left" : "right" });
    text(slide, entry[1], left ? pos[i][0] + 34 : pos[i][0] - 220, pos[i][1] + 17, 186, 22, { size: 13, color: C.muted, align: left ? "left" : "right" });
  });
  rawImage(slide, refined.hub, 560, 310, 160, 160, "独立可编辑的六模块中心圆环");
  text(slide, "六大模块", 560, 322, 160, 38, { size: 27, bold: true, color: C.gold, align: "center" });
  text(slide, "承载完整业务流程", 550, 366, 180, 24, { size: 16, color: C.mint, align: "center" });
}

function addResults(slide, plan, assets, index) {
  background(slide, assets.stage);
  chrome(slide, plan, index);
  rawImage(slide, refined.evidence, 44, 174, 865, 392, "独立可编辑的成果证据大卡片背景");
  image(slide, assets.zone, 54, 184, 845, 372, "可替换温室成果图片");
  line(slide, 1042, 220, 0, 340, C.gold, 1.5);
  [["+20%", "产量提升"], ["92%", "优质果率"], ["-30%", "人工成本降低"]].forEach((entry, i) => {
    rawImage(slide, refined.ring, 982, 180 + i * 166, 120, 120, `独立可编辑的成果指标圆环 ${i + 1}`);
    text(slide, entry[0], 990, 196 + i * 166, 104, 42, { size: 30, bold: true, color: i === 1 ? C.gold : C.cyan, align: "center" });
    text(slide, entry[1], 970, 244 + i * 166, 144, 22, { size: 14, color: C.muted, align: "center" });
  });
  text(slide, "形成系统原型、技能成果与持续推广基础", 350, 638, 580, 24, { size: 18, bold: true, color: C.gold, align: "center" });
}

function addValue(slide, plan, assets, index) {
  background(slide, assets.stage);
  chrome(slide, plan, index);
  line(slide, 640, 390, 0, -165, C.gold, 2);
  line(slide, 640, 390, -270, 140, C.cyan, 2);
  line(slide, 640, 390, 270, 140, C.gold, 2);
  rawImage(slide, refined.hub, 505, 255, 270, 270, "独立可编辑的应用价值核心圆环");
  image(slide, assets.stages, 545, 295, 190, 190, "可替换的番茄应用核心图片");
  [["技术", "接入自动采摘机器人", 640, 190], ["产业", "建立可信数字生产档案", 350, 545], ["应用", "迁移至草莓、柑橘等作物", 930, 545]].forEach(([titleValue, body, x, y], i) => {
    rawImage(slide, refined.ring, x - 70, y - 70, 140, 140, `独立可编辑的应用价值圆环 ${i + 1}`);
    text(slide, titleValue, x - 52, y - 16, 104, 32, { size: 21, bold: true, color: C.gold, align: "center" });
    text(slide, body, x - 85, y + 25, 170, 42, { size: 12, color: C.white, align: "center" });
  });
  text(slide, "让每颗番茄拥有可信数字档案", 430, 610, 420, 28, { size: 20, bold: true, color: C.gold, align: "center" });
}

function addThanks(slide, assets) {
  background(slide, assets.cover);
  shape(slide, "roundRect", 220, 228, 840, 272, C.deep, C.cyan, 1.5);
  text(slide, "敬请各位专家指导", 310, 288, 660, 72, { size: 52, bold: true, color: C.gold, align: "center" });
  text(slide, "慧眼识“株” · 智培鲜果", 360, 380, 560, 40, { size: 25, bold: true, color: C.cyan, align: "center" });
}

async function main() {
  await fs.rm(PREVIEW, { recursive: true, force: true });
  await fs.mkdir(PREVIEW, { recursive: true });
  const assets = {};
  refined = {};
  for (const [key, file] of Object.entries(cardFiles)) refined[key] = await assetPng(file);
  for (const [key, file] of Object.entries(files)) {
    if (key === "stage") {
      assets[key] = await sharp(file).resize(W, H, { fit: "cover" }).modulate({ brightness: 1.22, saturation: 0.96 }).png().toBuffer();
    } else {
      assets[key] = key in { hero: 1, zone: 1, stages: 1, advisor: 1, curveA: 1, curveB: 1 } ? await assetPng(file) : await png(file);
    }
  }

  const deckPlans = plans.map((plan) => ({ ...plan }));
  deckPlans[8].title = "用“识土、识图、使谱”建立精准管控闭环";
  [deckPlans[23], deckPlans[24]] = [deckPlans[24], deckPlans[23]];

  const deck = Presentation.create({ slideSize: { width: W, height: H } });
  for (let i = 0; i < deckPlans.length; i++) {
    const plan = deckPlans[i];
    const slide = deck.slides.add();
    if (plan.kind === "cover") addCover(slide, assets);
    else if (plan.kind === "roles") addRoles(slide, assets, i + 1);
    else if (plan.kind === "agenda") addAgenda(slide, plan, assets, i + 1);
    else if (plan.kind === "section") addSection(slide, plan, assets, i + 1);
    else if (plan.kind === "triple") addTriple(slide, plan, assets, i + 1);
    else if (plan.kind === "photo") addPhoto(slide, plan, assets, i + 1);
    else if (plan.kind === "flow" || plan.kind === "architecture") addFlow(slide, plan, assets, i + 1);
    else if (plan.kind === "code") addCode(slide, plan, assets, i + 1);
    else if (plan.kind === "curves") addCurves(slide, plan, assets, i + 1);
    else if (plan.kind === "quad") addQuad(slide, plan, assets, i + 1);
    else if (plan.kind === "six") addSix(slide, plan, assets, i + 1);
    else if (plan.kind === "results") addResults(slide, plan, assets, i + 1);
    else if (plan.kind === "value") addValue(slide, plan, assets, i + 1);
    else if (plan.kind === "thanks") addThanks(slide, assets);
  }

  for (let i = 0; i < deck.slides.items.length; i++) {
    const rendered = await deck.export({ slide: deck.slides.items[i], format: "png", scale: 1 });
    await fs.writeFile(path.join(PREVIEW, `slide-${String(i + 1).padStart(2, "0")}.png`), Buffer.from(await rendered.arrayBuffer()));
  }

  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(OUT);
  console.log(JSON.stringify({ out: OUT, slides: deckPlans.length, preview: PREVIEW }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
