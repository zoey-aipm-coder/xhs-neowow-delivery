# 车辆局部修复

每张场景图均须对照检查。可见车辆细节已正确时记录无需修复；发现轮毂、车标、轮胎文字、灯组、内饰等错误时，修复通过后才能作为合格图交付。此过程归入场景人物替换，外部无需审批每个修复动作。

## 选择方法

优先使用作为生成底图的正确同机位实拍。只恢复错误车辆部件，不覆盖人物、衣服、手、阴影和其他已正确区域。相机角度变化明显、曲面视差、复杂人物遮挡或无清晰正确素材时，不能承诺自动回贴有效；补素材或转设计师，保留未通过状态。

随包 `scripts/repair_local.py` 支持：

- 将已对齐原图直接回贴；或以人工核对的至少四对同平面点估计单应变换，投影真实部件到生成图。
- 使用生成图坐标的灰度遮罩：255 为完整恢复，0 为完全保留，灰色为边缘过渡。可选羽化只向遮罩内部扩展，不改遮罩外区域。
- 输出 PNG、遮罩有效区像素与输入哈希等回执。回读输出并断言遮罩外 RGB 像素不变；这只是技术验证，不代替车辆结构、人物遮挡与自然融合的视觉验收。

不自动检测轮毂、不自动猜遮罩或控制点、不生成 Logo。Agent 先实际查看两图，以原始图像坐标确定错误区域与对应点；在缩略预览上定位须换算回原始坐标。局部修复需要时，在使用者环境的独立 Python 环境安装：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r /path/to/xhs-neowow-delivery/scripts/requirements.txt
```

路径仅为用法示意，按实际 Skill 安装位置替换；Windows 使用 `.venv\Scripts\python.exe`。安装依赖可能需要网络；工具不可用时说明具体问题，不静默用其他付费生图服务代替。

## 同尺寸、已对齐回贴

```bash
python /path/to/xhs-neowow-delivery/scripts/repair_local.py \
  --source correct-original.png --target generated.png \
  --mask repair-mask.png --aligned --feather 3 \
  --output repaired-v2.png
```

## 需要对齐时

点文件包含 `source_points` 与 `target_points` 两个等长数组，至少4对。选择同一真实部件平面上分布良好、不共线的对应点，按同顺序填写，使用原始像素坐标。先核对点，再运行，不用远处背景拟合近处车轮。

```json
{
  "source_points": [[30,30],[130,30],[130,130],[30,130]],
  "target_points": [[32,32],[132,30],[130,132],[31,130]]
}
```

这些数字仅说明结构，不能用于真实图片。执行：

```bash
python /path/to/xhs-neowow-delivery/scripts/repair_local.py \
  --source correct-original.png --target generated.png \
  --mask repair-mask.png --points points.json --feather 3 \
  --output repaired-v2.png
```

## 修复验收

1. 查看对齐后的部件轮廓与透视；错位时调整点／换方法，不靠大范围模糊掩盖。
2. 遮罩只覆盖错误部件，保留原始人物遮挡；边缘轻微内羽化，Logo和轮胎文字核心区域完整取自实拍。
3. 放大逐项核对轮辐、中心标、轮胎文字、卡钳等实际可见内容。核对车身与环境过渡，禁止重影和硬边。
4. 读取脚本回执的外部像素一致结果，人工复查脸、手、服装等正确区域。若输入有 EXIF 旋转，脚本以显示方向归一化后的 RGB 像素为比较基准。
5. 上传修复成品到正式画布／交付位置，重新打开确认。未验收的自动输出不等于可交付。

脚本拒绝覆盖已有文件、透明图像、尺寸错误遮罩、共线／不可靠控制点，以及将源图无效区域投进修复遮罩的情况。只支持单应变换，不宣称处理所有三维车辆或人物遮挡。
