# 本次制包验证记录

日期：2026-10-27。目标 student-2026.10.27-01。以下为老师机实测，不代表学生电脑已经升级成功。

## 已验证

- 两份正式完整ZIP的SHA256与历史发布值一致；从ZIP本体读取基线，而非可变的解压目录。
- 从26日发布代码叠加选定新源码构造独立候选目录。全体候选Python源码 compile 通过。
- 候选后端运行 test_album_delete.py、test_album_images.py、test_disease_care.py：24项通过。临时SQLite/mock，不碰业务库。SQLAlchemy和LangChain弃用警告不影响本次结果。
- MQTT认证专项 unittest：5项通过；视觉项目 unittest：9项通过（含Tk布局、后台任务和图表缓存）。这些测试使用与候选相同的新源码。
- Playwright/Chrome：iot_switches在1440/390、disease_care_suggestions在1440/390、disease_care_smoke在1440/390深浅色，共8组通过，控制接口全被mock拦截，无真实控制指令。
- 改动的4个Vue页面/组件ESLint通过。pnpm现有overrides位置警告仍存在，不影响该测试。
- 制包程序对两个基线分别在内存应用更新并验证目标文件一致；每个base和files文件有真实SHA256。保留worker首次恢复门控和PostgreSQL ROUND numeric修复。
- ZIP生成时检查全部CRC及包内哈希，拒绝越界路径，排除运行数据、虚拟环境、图片、模型、数据集、秘密配置。源码快速检查未发现真实API Key/Wi-Fi密码；MQTT单元测试中的示例网段不是学生连接配置。

## 本机编辑隔离

制包时发现老师 iot_service.py 与 field_analysis_service.py 有未完成课堂编辑（语法错误），本机后端测试曾因此在收集阶段失败。没有改写老师文件。候选使用26日发布版教学方法，再在候选运行上述24项测试通过。其他两份核心教学文件也保留已发布版本。不要将老师工作树未完成源码混入升级包。

首次测试命令误用了不存在的 test_albums.py，修正为 test_album_images.py 后执行上述有效测试；不存在的测试不计为通过。

## 未验证边界

未在学生实体电脑安装；未在空白Windows系统重建环境；未做本次生产构建、完整数据库集成回归、真实图片推理、真实摄像头/GPU短训练、云模型/知识库调用或真实设备开关。浏览器mock验证不能代替硬件验收。LabelImg本次未重新进行桌面标注验收，历史修复验证见更新记录019。

学生Agent必须按UPDATE.md完成本机验收，缺外部条件标记NOT_TESTED/BLOCKED；不得把本报告当作学生测试报告。
