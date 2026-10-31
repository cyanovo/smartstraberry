# -*- coding: utf-8 -*-
import os
import cv2
import numpy as np
import shutil

SOURCE_DIR = "images"
OUTPUT_DIR = "output"
TARGET_SIZE = (400, 400)
SPLIT_GRID = (2, 2)

CATEGORIES = [
    "未成熟草莓",
    "半成熟草莓",
    "成熟草莓",
    "过熟草莓",
    "白草莓",
    "非草莓图片",
]

def create_output_folders(base_dir):
    for category in CATEGORIES:
        folder_path = os.path.join(base_dir, category)
        os.makedirs(folder_path, exist_ok=True)
    print("已创建输出文件夹:", base_dir)

def suofang(img, target_size):
    h, w = img.shape[:2]
    target_w, target_h = target_size
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    scaled_img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return scaled_img, scale

def fenge(img, grid):
    rows, cols = grid
    h, w = img.shape[:2]
    split_h, split_w = h // rows, w // cols
    tiles = []
    for r in range(rows):
        for c in range(cols):
            y1, y2 = r * split_h, (r+1)*split_h
            x1, x2 = c * split_w, (c+1)*split_w
            tiles.append(img[y1:y2, x1:x2])
    return tiles

def get_fruit_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    red1 = cv2.inRange(hsv, (0, 50, 50), (12, 255, 255))
    red2 = cv2.inRange(hsv, (168, 50, 50), (180, 255, 255))
    green = cv2.inRange(hsv, (35, 30, 30), (85, 255, 255))
    white = cv2.inRange(hsv, (0, 0, 180), (180, 35, 255))

    mask = cv2.bitwise_or(red1, red2)
    mask = cv2.bitwise_or(mask, green)
    mask = cv2.bitwise_or(mask, white)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask

def is_strawberry_shape(img, mask):
    """
    根据果实轮廓形状和颜色判断是否为草莓
    草莓：近似三角形/心形，长宽比适中（1.0~1.8），红/绿/白色
    香蕉：长条形，长宽比 > 2.5，黄色
    橙子/芒果：圆形或椭圆，黄色/橙色占比高
    """
    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0:
        return False

    max_cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(max_cnt)
    if area < 500:
        return False

    x, y, w, h = cv2.boundingRect(max_cnt)
    aspect_ratio = max(w, h) / max(min(w, h), 1)

    if aspect_ratio > 2.5:
        return False

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    yellow_mask = cv2.inRange(hsv, (15, 80, 80), (38, 255, 255))
    orange_mask = cv2.inRange(hsv, (10, 100, 100), (25, 255, 255))
    yellow_orange = cv2.bitwise_or(yellow_mask, orange_mask)
    yellow_in_fruit = cv2.bitwise_and(yellow_orange, mask)
    fruit_pixels = np.count_nonzero(mask)
    yellow_ratio = np.count_nonzero(yellow_in_fruit) / max(fruit_pixels, 1)

    if yellow_ratio > 0.30:
        hull = cv2.convexHull(max_cnt)
        hull_area = cv2.contourArea(hull)
        solidity = area / max(hull_area, 1)
        if aspect_ratio < 2.0 and solidity > 0.85:
            return False

    hull = cv2.convexHull(max_cnt)
    hull_area = cv2.contourArea(hull)
    solidity = area / max(hull_area, 1)
    if aspect_ratio < 1.3 and solidity > 0.92:
        return False

    if 1.0 <= aspect_ratio <= 1.8:
        return True

    return True

def classify_by_color(img, mask):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    fruit_pixels = np.count_nonzero(mask)
    if fruit_pixels == 0:
        return 0, 0, 0, "非草莓图片", 0

    red1 = cv2.inRange(hsv, (0, 50, 50), (12, 255, 255))
    red2 = cv2.inRange(hsv, (168, 50, 50), (180, 255, 255))
    red_mask = cv2.bitwise_and(cv2.bitwise_or(red1, red2), mask)

    green_mask = cv2.bitwise_and(cv2.inRange(hsv, (35, 30, 30), (85, 255, 255)), mask)

    white_mask = cv2.bitwise_and(cv2.inRange(hsv, (0, 0, 180), (180, 35, 255)), mask)

    red_ratio = np.count_nonzero(red_mask) / fruit_pixels
    green_ratio = np.count_nonzero(green_mask) / fruit_pixels
    white_ratio = np.count_nonzero(white_mask) / fruit_pixels

    feature_value = red_ratio * 100 + green_ratio * 50 + white_ratio * 30

    if white_ratio > 0.35 and red_ratio < 0.15:
        category = "白草莓"
    elif red_ratio > 0.45:
        category = "成熟草莓"
    elif red_ratio > 0.35:
        category = "过熟草莓"
    elif red_ratio > 0.15 and green_ratio > 0.05:
        category = "半成熟草莓"
    elif red_ratio > 0.15:
        category = "半成熟草莓"
    elif green_ratio > 0.15:
        category = "未成熟草莓"
    else:
        category = "非草莓图片"

    return red_ratio, green_ratio, white_ratio, category, feature_value

def main():
    print("草莓图片分类清洗程序")
    if not os.path.exists(SOURCE_DIR):
        print("源文件夹不存在，请检查！")
        return
    create_output_folders(OUTPUT_DIR)

    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
    image_files = [os.path.join(SOURCE_DIR, f) for f in os.listdir(SOURCE_DIR) if f.lower().endswith(image_extensions)]

    print(f"一共找到{len(image_files)}张图片，开始处理")
    results = []

    for srcpath in image_files:
        filename = os.path.basename(srcpath)
        print("正在处理：", filename)

        try:
            img = cv2.imread(srcpath)
            if img is None:
                print(f"{filename} 图片损坏，读取失败，跳过")
                continue
        except Exception as e:
            print(f"{filename} 读取异常：{str(e)}")
            continue

        h, w = img.shape[:2]
        pixel_area = h * w
        # 生成水果前景掩码
        mask = get_fruit_mask(img)
        # 根据掩码判断这个物体外形是不是草莓
        is_strawberry = is_strawberry_shape(img, mask)

        #等比例缩放
        scaled_img, scale = suofang(img, TARGET_SIZE)
        #分割
        tiles = fenge(scaled_img, SPLIT_GRID)

        # 第三步：根据果实红色占比分类
        red_ratio, green_ratio, white_ratio, category, feature_value = classify_by_color(img, mask)

        # 如果形状判断不是草莓，强制归类为非草莓
        if not is_strawberry:
            category = "非草莓图片"
            feature_value = 0

        # 复制文件到对应文件夹
        dst_folder = os.path.join(OUTPUT_DIR, category)
        dstpath = os.path.join(dst_folder, filename)
        shutil.copy2(srcpath, dstpath)

        results.append({
            "filename": filename,
            "pixel_area": pixel_area,
            "red_ratio": red_ratio,
            "green_ratio": green_ratio,
            "white_ratio": white_ratio,
            "category": category,
            "feature_value": feature_value
        })

    print("\n====================分类结果====================")
    header = "{:<25} {:<12} {:<10} {:<10} {:<10} {:<12} {:<10}".format(
        "文件名", "像素面积", "红色占比", "绿色占比", "白色占比", "分类结果", "特征数值"
    )
    print(header)
    for r in results:
        line = "{:<25} {:<12} {:.4f}     {:.4f}     {:.4f}     {:<12} {:.2f}".format(
            r["filename"], r["pixel_area"],
            r["red_ratio"], r["green_ratio"], r["white_ratio"],
            r["category"], r["feature_value"]
        )
        print(line)
    print("清洗分类全部完成！")

if __name__ == "__main__":
    main()
