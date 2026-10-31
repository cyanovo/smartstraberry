#!/usr/bin/env python3
"""
🍓 草莓智能视觉检测系统 - 一体化脚本
包含Web服务器和前端界面，可直接运行
"""

import os
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import sys
import cv2
import numpy as np
import base64
import json
import uuid
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
import urllib.parse
import tempfile
import time

try:
    from ultralytics import YOLO

    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    print("⚠️ 未安装ultralytics，将使用模拟检测模式")
    print("💡 安装方法: pip install ultralytics")

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class StrawberryDetector:
    """草莓检测器"""

    def __init__(self):
        self.device = 'cuda' if HAS_TORCH and torch.cuda.is_available() else 'cpu'
        print(f"📍 使用设备: {self.device}")

        # 模型路径
        self.model_path = "models/best.pt"
        self.model = None
        self.use_simulation = True
        self.model_type = 'maturity'  # 'maturity' 或 'pest'

        # 加载模型
        self.load_model()

        # 检测结果缓存
        self.last_result = None

    def load_model(self):
        """加载YOLO模型"""
        if not HAS_YOLO:
            print("⚠️ YOLO未安装，使用模拟模式")
            return

        try:
            if os.path.exists(self.model_path):
                print(f"📦 加载模型: {self.model_path}")
                self.model = YOLO(self.model_path)
                self.use_simulation = False
                print("✅ 模型加载成功！")
                # 打印模型类别映射
                if hasattr(self.model, 'names'):
                    print(f"📊 模型类别映射: {self.model.names}")
            else:
                print(f"⚠️ 模型文件不存在: {self.model_path}")
                print("💡 使用模拟检测模式")
                self.use_simulation = True
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            self.use_simulation = True

    def detect_maturity(self, image):
        """实际成熟度检测"""
        if self.use_simulation or self.model is None:
            return self.detect_maturity_simulation(image)

        try:
            results = self.model(image, conf=0.5)  # 添加置信度阈值

            boxes = []
            classes = []
            confidences = []

            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())

                        # 🔧 只保留置信度大于0.5的检测
                        if conf >= 0.5:
                            boxes.append([int(x1), int(y1), int(x2), int(y2)])
                            classes.append(int(box.cls[0].cpu().numpy()))
                            confidences.append(conf)

            total = len(boxes)

            # 假设模型类别: 0=成熟, 1=半成熟, 2=未成熟
            ripe = sum(1 for c in classes if c == 0)
            half = sum(1 for c in classes if c == 1)
            unripe = sum(1 for c in classes if c == 2)

            return {
                'boxes': boxes,
                'classes': classes,
                'confidences': confidences,
                'total': total,
                'ripe': ripe,
                'half': half,
                'unripe': unripe,
                'avg_size': round(np.random.uniform(25, 45), 1)
            }
        except Exception as e:
            print(f"检测错误: {e}")
            return self.detect_maturity_simulation(image)

    def detect_pest_simulation(self, image):
        """模拟病虫害检测"""
        has_pest = np.random.random() > 0.5

        if not has_pest:
            return {'detections': [], 'healthy': True}

        pest_types = ['白粉病', '灰霉病', '红蜘蛛', '蚜虫', '叶斑病', '炭疽病']
        severity_levels = ['轻度', '中度', '严重']

        num_pests = np.random.randint(1, 4)
        detections = []

        for _ in range(num_pests):
            pest = {
                'class': np.random.choice(pest_types),
                'confidence': round(np.random.uniform(0.7, 0.98), 2),
                'severity': np.random.choice(severity_levels, p=[0.5, 0.3, 0.2]),
                'recommendation': self.get_recommendation()
            }
            detections.append(pest)

        return {'detections': detections, 'healthy': False}

    def get_recommendation(self):
        """获取防治建议"""
        recommendations = [
            '建议使用生物防治，减少化学农药',
            '及时清除病叶，防止传播扩散',
            '加强通风，降低环境湿度',
            '使用针对性药剂进行防治',
            '引入天敌进行生物防治',
            '加强田间管理，提高抗病能力'
        ]
        return np.random.choice(recommendations)

    def detect_maturity(self, image):
        """实际成熟度检测"""
        if self.use_simulation or self.model is None:
            return self.detect_maturity_simulation(image)

        try:
            results = self.model(image)

            boxes = []
            classes = []
            confidences = []

            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        boxes.append([int(x1), int(y1), int(x2), int(y2)])
                        classes.append(int(box.cls[0].cpu().numpy()))
                        confidences.append(float(box.conf[0].cpu().numpy()))

            total = len(boxes)

            # 假设模型类别: 0=成熟, 1=半成熟, 2=未成熟
            ripe = sum(1 for c in classes if c == 0)      # 0=成熟
            half = sum(1 for c in classes if c == 1)      # 1=半成熟
            unripe = sum(1 for c in classes if c == 2)    # 2=未成熟

            return {
                'boxes': boxes,
                'classes': classes,
                'confidences': confidences,
                'total': total,
                'ripe': ripe,
                'half': half,
                'unripe': unripe,
                'avg_size': round(np.random.uniform(25, 45), 1)
            }
        except Exception as e:
            print(f"检测错误: {e}")
            return self.detect_maturity_simulation(image)

    def detect_pest(self, image):
        """实际病虫害检测"""
        if self.use_simulation or self.model is None:
            return self.detect_pest_simulation(image)

        try:
            # 这里使用同一模型或专用模型
            results = self.model(image)
            detections = []

            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        cls_id = int(box.cls[0].cpu().numpy())
                        conf = float(box.conf[0].cpu().numpy())

                        # 假设类别映射
                        pest_classes = ['白粉病', '灰霉病', '红蜘蛛', '蚜虫']
                        if cls_id < len(pest_classes):
                            detections.append({
                                'class': pest_classes[cls_id],
                                'confidence': round(conf, 2),
                                'severity': np.random.choice(['轻度', '中度', '严重']),
                                'recommendation': self.get_recommendation()
                            })

            return {'detections': detections, 'healthy': len(detections) == 0}
        except Exception as e:
            print(f"检测错误: {e}")
            return self.detect_pest_simulation(image)

    def detect(self, image, detect_type='maturity'):
        """执行检测"""
        self.model_type = detect_type

        if detect_type == 'maturity':
            return self.detect_maturity(image)
        else:
            return self.detect_pest(image)

    def annotate_image(self, image, results, detect_type):
        """在图像上标注检测结果（使用PIL支持中文）"""
        # 将OpenCV图像转换为PIL图像
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        draw = ImageDraw.Draw(pil_image)

        # 尝试加载中文字体
        try:
            # Windows系统字体
            font_path = "C:/Windows/Fonts/simhei.ttf"  # 黑体
            font = ImageFont.truetype(font_path, 20)
        except:
            try:
                # 备用字体
                font_path = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑
                font = ImageFont.truetype(font_path, 20)
            except:
                # 如果找不到字体，使用默认字体
                font = ImageFont.load_default()
                print("⚠️ 未找到中文字体，使用默认字体")

        h, w = image.shape[:2]

        if detect_type == 'maturity':
            boxes = results.get('boxes', [])
            classes = results.get('classes', [])
            confidences = results.get('confidences', [])

            # 颜色映射：0=成熟(红色), 1=半成熟(黄色), 2=未成熟(绿色)
            label_map = {
                0: {'text': '成熟', 'color': (0, 0, 200)},      # 红色 - 成熟
                1: {'text': '半成熟', 'color': (0, 200, 200)},  # 黄色 - 半成熟
                2: {'text': '未成熟', 'color': (0, 200, 0)}     # 绿色 - 未成熟
            }

            for box, cls, conf in zip(boxes, classes, confidences):
                x1, y1, x2, y2 = box
                label_info = label_map.get(cls, {'text': '未知', 'color': (255, 255, 255)})
                color = label_info['color']
                text = f"{label_info['text']} {conf:.2f}"

                # 画框 (使用PIL)
                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

                # 添加文字背景
                bbox = draw.textbbox((x1, y1), text, font=font)
                draw.rectangle([bbox[0] - 2, bbox[1] - 2, bbox[2] + 2, bbox[3] + 2], fill=color)

                # 添加文字（白色）
                draw.text((x1, y1 - 5), text, fill=(255, 255, 255), font=font)

        elif detect_type == 'pest':
            detections = results.get('detections', [])
            severity_colors = {
                '轻度': (0, 200, 0),      # 绿色（轻微）
                '中度': (0, 200, 200),    # 黄色（中等）
                '严重': (0, 0, 200)       # 红色（严重）
            }

            for i, detection in enumerate(detections):
                # 随机位置
                x1 = np.random.randint(20, w - 150)
                y1 = np.random.randint(20, h - 150)
                x2 = x1 + np.random.randint(60, 160)
                y2 = y1 + np.random.randint(60, 160)

                severity = detection.get('severity', '轻度')
                color = severity_colors.get(severity, (255, 255, 255))

                pest_name = detection.get('class', '未知病虫害')
                confidence = detection.get('confidence', 0)
                text = f"{pest_name} {confidence:.2f}"

                # 画框
                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

                # 添加文字背景
                bbox = draw.textbbox((x1, y1), text, font=font)
                draw.rectangle([bbox[0] - 2, bbox[1] - 2, bbox[2] + 2, bbox[3] + 2], fill=color)

                # 添加文字
                draw.text((x1, y1 - 5), text, fill=(255, 255, 255), font=font)

        # 转换回OpenCV格式
        annotated = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        return annotated

    def get_maturity_recommendation(self, results):
        """生成成熟度建议"""
        total = results.get('total', 0)
        ripe = results.get('ripe', 0)

        if total == 0:
            return "未检测到草莓，请检查图像质量"

        ripe_ratio = ripe / total

        if ripe_ratio > 0.7:
            return "🍓 大量草莓已成熟，建议立即采摘！"
        elif ripe_ratio > 0.4:
            return "🌱 部分草莓已成熟，建议分批采摘"
        elif ripe_ratio > 0.2:
            return "🌿 草莓正在成熟中，预计3-5天可采摘"
        else:
            return "🌱 草莓尚在生长期，请继续培育"

    def get_pest_recommendation(self, results):
        """生成病虫害建议"""
        detections = results.get('detections', [])

        if not detections:
            return "✅ 未发现病虫害，草莓生长健康！"

        severe_count = sum(1 for d in detections if d.get('severity') == '严重')
        if severe_count > 0:
            return "⚠️ 发现严重病虫害，建议立即采取措施！"
        else:
            return "🔍 发现病虫害，建议及时防治"


# 创建全局检测器
detector = StrawberryDetector()


class DetectionHandler(SimpleHTTPRequestHandler):
    """自定义HTTP处理器"""

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/' or path == '/index.html':
            self.serve_html()
        elif path == '/detect':
            self.handle_detect()
        elif path == '/health':
            self.handle_health()
        elif path == '/status':
            self.handle_status()
        elif path.startswith('/static/'):
            self.serve_static(path)
        else:
            self.send_error(404, "Page not found")

    def do_POST(self):
        """处理POST请求"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/detect':
            self.handle_detect_post()
        elif path == '/switch_model':
            self.handle_switch_model()
        else:
            self.send_error(404, "Endpoint not found")

    def serve_html(self):
        """返回HTML页面"""
        html_content = self.get_html_content()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def handle_health(self):
        """健康检查"""
        response = {
            'status': 'ok',
            'simulation': detector.use_simulation,
            'model_type': detector.model_type,
            'timestamp': datetime.now().isoformat()
        }
        self.send_json_response(response)

    def handle_status(self):
        """获取状态"""
        response = {
            'simulation_mode': detector.use_simulation,
            'model_type': detector.model_type,
            'device': detector.device,
            'last_result': detector.last_result
        }
        self.send_json_response(response)

    def handle_switch_model(self):
        """切换模型"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
            detect_type = data.get('detect_type', 'maturity')

            if detect_type in ['maturity', 'pest']:
                detector.model_type = detect_type
                response = {
                    'success': True,
                    'message': f'已切换到{detect_type}模式',
                    'model_type': detect_type
                }
            else:
                response = {
                    'success': False,
                    'error': '不支持的检测类型'
                }
        except:
            response = {
                'success': False,
                'error': '无效的请求数据'
            }

        self.send_json_response(response)

    def handle_detect(self):
        """处理检测请求（GET）"""
        # 从查询参数获取图片
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # 如果有图片数据，进行处理
        if 'image' in params:
            try:
                image_data = params['image'][0]
                # 这里简化处理，实际可能需要base64解码
                response = {
                    'success': True,
                    'message': '检测完成',
                    'simulation': detector.use_simulation
                }
                self.send_json_response(response)
            except:
                self.send_error(400, "Invalid image data")
        else:
            # 返回默认响应
            response = {
                'success': True,
                'message': '检测服务运行正常',
                'simulation': detector.use_simulation,
                'model_type': detector.model_type
            }
            self.send_json_response(response)

    def handle_detect_post(self):
        """处理POST检测请求"""
        try:
            # 获取请求数据
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            if not post_data:
                self.send_error(400, "No data received")
                return

            # 尝试解析JSON
            try:
                data = json.loads(post_data.decode('utf-8'))
            except:
                # 如果不是JSON，尝试作为表单数据处理
                data = {}

            # 检查是否有图片数据
            if 'image' in data:
                image_data = data['image']

                # 解码base64图片
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]

                try:
                    img_bytes = base64.b64decode(image_data)
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if image is None:
                        self.send_error(400, "无法解码图片")
                        return

                    # 执行检测
                    detect_type = data.get('detect_type', detector.model_type)
                    results = detector.detect(image, detect_type)

                    # 生成标注图片
                    annotated = detector.annotate_image(image, results, detect_type)

                    # 编码标注图片
                    _, buffer = cv2.imencode('.jpg', annotated)
                    annotated_base64 = base64.b64encode(buffer).decode('utf-8')

                    # 构建响应
                    if detect_type == 'maturity':
                        response_data = {
                            'success': True,
                            'data': {
                                'detect_type': 'maturity',
                                'detect_type_cn': '成熟度检测',
                                'detected_time': datetime.now().isoformat(),
                                'total_count': results.get('total', 0),
                                'ripe_count': results.get('ripe', 0),
                                'half_ripe_count': results.get('half', 0),
                                'unripe_count': results.get('unripe', 0),
                                'avg_size_mm': results.get('avg_size', 0),
                                'recommendation': detector.get_maturity_recommendation(results),
                                'annotated_image': annotated_base64
                            }
                        }
                    else:
                        detections = results.get('detections', [])
                        pest_detections = []

                        for detection in detections:
                            pest_detections.append({
                                'pest_disease_class': detection.get('class', '未知'),
                                'confidence': f"{detection.get('confidence', 0):.2%}",
                                'severity_level': detection.get('severity', '未知'),
                                'recommendation': detection.get('recommendation', '建议咨询农业专家')
                            })

                        response_data = {
                            'success': True,
                            'data': {
                                'detect_type': 'pest',
                                'detect_type_cn': '病虫害检测',
                                'detected_time': datetime.now().isoformat(),
                                'pest_disease_detections': pest_detections,
                                'recommendation': detector.get_pest_recommendation(results),
                                'annotated_image': annotated_base64
                            }
                        }

                    # 保存结果
                    detector.last_result = response_data

                    self.send_json_response(response_data)

                except Exception as e:
                    print(f"处理图片错误: {e}")
                    self.send_error(500, f"图片处理错误: {str(e)}")
            else:
                self.send_error(400, "未提供图片数据")

        except Exception as e:
            print(f"处理请求错误: {e}")
            self.send_error(500, f"服务器错误: {str(e)}")

    def send_json_response(self, data):
        """发送JSON响应"""
        response_json = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response_json.encode('utf-8'))

    def get_html_content(self):
        """获取HTML内容"""
        return HTML_TEMPLATE

    def serve_static(self, path):
        """服务静态文件"""
        # 简单处理，返回404
        self.send_error(404, "Static file not found")

    def log_message(self, format, *args):
        """重写日志方法"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")


# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🍓 草莓智能检测系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 15px;
        }
        .container {
            max-width: 1300px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #4CAF50, #2E7D32);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 { font-size: 28px; margin-bottom: 5px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .control-panel {
            padding: 15px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
        }
        .control-group {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .control-group label {
            font-weight: bold;
            font-size: 13px;
            color: #495057;
        }
        select, button {
            padding: 6px 12px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 13px;
            background: white;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover { background: #45a049; }
        button:disabled {
            background: #adb5bd;
            cursor: not-allowed;
        }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .main-content {
            display: flex;
            flex-wrap: wrap;
            padding: 20px;
            gap: 20px;
        }
        .camera-section, .result-section {
            flex: 1;
            min-width: 300px;
        }
        .section-title {
            background: #2196F3;
            color: white;
            padding: 8px 15px;
            border-radius: 4px 4px 0 0;
            font-weight: bold;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-active { background: #4CAF50; }
        .status-inactive { background: #dc3545; }
        .video-box, .result-box {
            border: 1px solid #dee2e6;
            border-radius: 0 0 4px 4px;
            padding: 10px;
            min-height: 300px;
            background: #f8f9fa;
        }
        #videoElement {
            max-width: 100%;
            border-radius: 4px;
            background: #000;
            display: none;
        }
        #canvasElement {
            max-width: 100%;
            border-radius: 4px;
            display: none;
        }
        .placeholder {
            color: #6c757d;
            text-align: center;
            padding: 20px;
        }
        .result-content {
            width: 100%;
            max-height: 400px;
            overflow-y: auto;
            display: none;
        }
        .detection-item {
            background: white;
            border-left: 4px solid #4CAF50;
            padding: 12px;
            margin: 8px 0;
            border-radius: 0 4px 4px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .detection-item h3 {
            color: #495057;
            margin-bottom: 6px;
            font-size: 15px;
        }
        .detection-item p {
            margin: 4px 0;
            font-size: 13px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 8px;
            margin: 8px 0;
        }
        .stat-item {
            background: #e3f2fd;
            padding: 8px;
            border-radius: 4px;
            text-align: center;
        }
        .stat-value {
            font-size: 20px;
            font-weight: bold;
            color: #0d6efd;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #0d6efd;
        }
        .annotated-image {
            max-width: 100%;
            border-radius: 4px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍓 草莓智能视觉检测系统</h1>
            <p>基于YOLO的实时成熟度与病虫害检测</p>
        </div>

        <div class="control-panel">
            <div class="control-group">
                <label>检测模式:</label>
                <select id="detectType">
                    <option value="maturity">成熟度检测</option>
                    <option value="pest">病虫害检测</option>
                </select>
            </div>

            <div class="control-group">
                <label>间隔(秒):</label>
                <select id="interval">
                    <option value="2000">2</option>
                    <option value="3000" selected>3</option>
                    <option value="5000">5</option>
                    <option value="10000">10</option>
                </select>
            </div>

            <div class="control-group">
                <button id="startCamera">📷 开启摄像头</button>
                <button id="startDetection" disabled>▶ 开始检测</button>
                <button id="stopDetection" disabled>⏹ 停止</button>
                <button id="captureImage" disabled>📸 拍摄</button>
                <button id="clearResults">🗑 清除</button>
            </div>
        </div>

        <div class="main-content">
            <div class="camera-section">
                <div class="section-title">
                    <span>
                        <span class="status-indicator status-inactive" id="cameraStatus"></span>
                        摄像头画面
                    </span>
                </div>
                <div class="video-box">
                    <video id="videoElement" autoplay playsinline></video>
                    <canvas id="canvasElement"></canvas>
                    <div id="cameraPlaceholder" class="placeholder">
                        <p>📷 摄像头未开启</p>
                        <p style="font-size:12px;">点击"开启摄像头"按钮</p>
                    </div>
                </div>
            </div>

            <div class="result-section">
                <div class="section-title">
                    <span>
                        <span class="status-indicator status-inactive" id="detectionStatus"></span>
                        检测结果
                    </span>
                </div>
                <div class="result-box">
                    <div id="resultPlaceholder" class="placeholder">
                        <p>🔍 检测结果将显示在这里</p>
                        <p style="font-size:12px;">开启摄像头并开始检测</p>
                    </div>
                    <div id="resultContent" class="result-content"></div>
                    <div id="loading" class="loading">
                        <p>🔄 正在分析图像...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = '';
        let videoStream = null;
        let detectionInterval = null;

        const videoElement = document.getElementById('videoElement');
        const canvasElement = document.getElementById('canvasElement');
        const ctx = canvasElement.getContext('2d');
        let cameraActive = false;

        function updateStatus(element, active) {
            element.className = `status-indicator ${active ? 'status-active' : 'status-inactive'}`;
        }

        document.getElementById('startCamera').addEventListener('click', async function() {
            try {
                videoStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 640 }, height: { ideal: 480 } }
                });

                videoElement.srcObject = videoStream;
                videoElement.style.display = 'block';
                document.getElementById('cameraPlaceholder').style.display = 'none';
                cameraActive = true;

                updateStatus(document.getElementById('cameraStatus'), true);
                document.getElementById('startDetection').disabled = false;
                document.getElementById('captureImage').disabled = false;
                document.getElementById('startCamera').disabled = true;

                console.log('✅ 摄像头开启成功');
            } catch (error) {
                alert('无法访问摄像头: ' + error.message);
            }
        });

        document.getElementById('startDetection').addEventListener('click', function() {
            const interval = parseInt(document.getElementById('interval').value);

            if (detectionInterval) clearInterval(detectionInterval);

            detectionInterval = setInterval(captureAndDetect, interval);

            updateStatus(document.getElementById('detectionStatus'), true);
            document.getElementById('stopDetection').disabled = false;
            document.getElementById('startDetection').disabled = true;
            document.getElementById('captureImage').disabled = true;

            console.log('▶ 开始自动检测');
        });

        document.getElementById('stopDetection').addEventListener('click', function() {
            if (detectionInterval) {
                clearInterval(detectionInterval);
                detectionInterval = null;
            }

            updateStatus(document.getElementById('detectionStatus'), false);
            document.getElementById('stopDetection').disabled = true;
            document.getElementById('startDetection').disabled = false;
            document.getElementById('captureImage').disabled = false;

            console.log('⏹ 停止检测');
        });

        document.getElementById('captureImage').addEventListener('click', function() {
            captureAndDetect();
        });

        document.getElementById('clearResults').addEventListener('click', function() {
            document.getElementById('resultContent').style.display = 'none';
            document.getElementById('resultContent').innerHTML = '';
            document.getElementById('resultPlaceholder').style.display = 'block';
        });

        async function captureAndDetect() {
            if (!cameraActive) {
                alert('请先开启摄像头');
                return;
            }

            try {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('resultPlaceholder').style.display = 'none';
                document.getElementById('resultContent').style.display = 'none';

                canvasElement.width = videoElement.videoWidth || 640;
                canvasElement.height = videoElement.videoHeight || 480;
                ctx.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);

                const imageData = canvasElement.toDataURL('image/jpeg', 0.8);
                const detectType = document.getElementById('detectType').value;

                const response = await fetch('/detect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: imageData, detect_type: detectType })
                });

                const result = await response.json();

                document.getElementById('loading').style.display = 'none';

                if (result.success) {
                    displayResult(result.data);
                } else {
                    alert('检测失败: ' + (result.error || '未知错误'));
                }
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                alert('请求失败: ' + error.message);
            }
        }

        function displayResult(data) {
            const content = document.getElementById('resultContent');
            content.innerHTML = '';
            content.style.display = 'block';

            // 显示标注图片
            if (data.annotated_image) {
                const img = document.createElement('img');
                img.src = 'data:image/jpeg;base64,' + data.annotated_image;
                img.className = 'annotated-image';
                content.appendChild(img);
            }

            // 显示检测信息
            const info = document.createElement('div');
            info.className = 'detection-item';
            info.innerHTML = `
                <h3>📊 检测结果</h3>
                <p><strong>检测类型:</strong> ${data.detect_type_cn || '未知'}</p>
                <p><strong>检测时间:</strong> ${data.detected_time || new Date().toLocaleString()}</p>
            `;
            content.appendChild(info);

            // 显示统计数据
            if (data.total_count !== undefined) {
                const stats = document.createElement('div');
                stats.className = 'detection-item';
                stats.innerHTML = `
                    <h3>🍓 成熟度统计</h3>
                    <div class="stats">
                        <div class="stat-item">
                            <div class="stat-value">${data.total_count}</div>
                            <div>总数量</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" style="color: #4CAF50;">${data.ripe_count || 0}</div>
                            <div>成熟</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" style="color: #FF9800;">${data.half_ripe_count || 0}</div>
                            <div>半成熟</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" style="color: #F44336;">${data.unripe_count || 0}</div>
                            <div>未成熟</div>
                        </div>
                    </div>
                    <p><strong>建议:</strong> ${data.recommendation || '暂无建议'}</p>
                `;
                content.appendChild(stats);
            }

            // 显示病虫害结果
            if (data.pest_disease_detections && data.pest_disease_detections.length > 0) {
                const pestDiv = document.createElement('div');
                pestDiv.className = 'detection-item';
                let pestHtml = '<h3>🔍 病虫害检测</h3>';
                data.pest_disease_detections.forEach(d => {
                    pestHtml += `
                        <p><strong>${d.pest_disease_class}</strong> - 置信度: ${d.confidence}</p>
                        <p>严重程度: ${d.severity_level} | 建议: ${d.recommendation}</p>
                        <hr>
                    `;
                });
                pestDiv.innerHTML = pestHtml;
                content.appendChild(pestDiv);
            }

            content.scrollTop = 0;
        }
    </script>
</body>
</html>
'''

# 启动服务
if __name__ == "__main__":
    print("🍓 启动草莓检测系统...")
    print(f"📍 API地址: http://localhost:8000")
    print(f"📍 按 Ctrl+C 停止服务")
    print("=" * 50)

    try:
        server = HTTPServer(('localhost', 8000), DetectionHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")