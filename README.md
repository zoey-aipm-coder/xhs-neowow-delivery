# 小红书 AI 生图交付 Skill

让 Agent 通过 **Neowow** 完成固定账号人物的小红书图片制作与送审：

**复用账号人物 → 本次换装 → Agent 从图库筛图、人工确认 → 场景人物替换（内部完成车辆修复）→ 保存核验与交付。**

人物身份与账号绑定，日常交付不重新生成人物三视图。服装与场景按任务更换，分开确认。车辆细节检查、实拍局部回贴、修复复查与保存由 Agent 内部完成。

## 安装

### 方式一：让 Codex 从 GitHub 安装（推荐）

将下面这句话发给 Codex：

```text
请安装这个 Skill：https://github.com/zoey-aipm-coder/xhs-neowow-delivery/tree/main/skills/xhs-neowow-delivery
```

Skill 安装器支持从 GitHub 的 Skill 文件夹安装；安装后在下一轮对话使用。实际工具权限仍由你的 Codex 环境决定。

### 方式二：下载安装包

[下载 v1.0.0 安装包](https://github.com/zoey-aipm-coder/xhs-neowow-delivery/releases/download/v1.0.0/xhs-neowow-delivery-v1.0.0.zip) · [发布页面](https://github.com/zoey-aipm-coder/xhs-neowow-delivery/releases/tag/v1.0.0)

解压 ZIP，把其中 `xhs-neowow-delivery` 文件夹放到 `$CODEX_HOME/skills/`；没有设置 `CODEX_HOME` 时放到 `~/.codex/skills/`。Windows 默认对应用户目录下的 `.codex/skills/`。最终应存在：

```text
~/.codex/skills/xhs-neowow-delivery/SKILL.md
```

如果已有同名版本，先备份再由你决定替换，不合并覆盖未知文件。该包是 Skill 文件夹，不是应用程序；安装不会登录账号、自动充值、发图或安装 Python 依赖。

## 使用前准备

- 支持读取 Skill 且具备浏览器操作能力的 Agent，以及你已登录的 Neowow；仅有纯文字聊天无法自动操作网站。
- 账号绑定的确认版人物、人设、车型配置与正确车辆细节参考。
- 本次服装／配饰要求、场景要求、图库入口、图片数量与画幅。
- 可复用画布、审核人、交付期限与明确的生成预算。

Skill 不包含任何客户资产、内部文档／画布入口、账号凭据或生成积分；在自己的授权环境提供素材。无权访问的图库与未登录网站需先由使用者完成接入。

示例：

```text
使用 $xhs-neowow-delivery 完成本次小红书图片交付。
账号与人物资产：使用我提供的账号资料和确认版人物，不重新生成三视图。
本次服装：使用我提供的穿搭参考，先提交换装结果确认。
场景：从我提供的图库筛选车外、车内候选，各提供合格预览与理由让我选。
交付：按确认画幅制作，场景人物替换后完成车辆细节检查和局部修复。
生成前先列本轮张数、预计积分和重试上限，得到授权后执行。
```

## 包含内容

- [Skill 主流程](skills/xhs-neowow-delivery/SKILL.md)
- [场景筛选标准](skills/xhs-neowow-delivery/references/scene-selection.md)
- [Neowow 操作、提示词与费用规则](skills/xhs-neowow-delivery/references/neowow-operation.md)
- [车辆局部修复方法与脚本用法](skills/xhs-neowow-delivery/references/local-repair.md)

局部修复脚本需 Python 3.9+、NumPy、OpenCV 与 Pillow。只在需要修复时按说明在独立环境安装依赖，依赖文件随包提供。脚本支持已对齐素材或人工核对控制点的单应变换，不自动识别部件，不适用于所有视角与复杂遮挡。

## 验证范围

发布前执行 Skill 结构校验、安装包解压与隔离安装验证，以及局部回贴、内羽化、已知位移对齐、遮罩外像素保留、错误输入与禁止覆盖的离线测试。仓库测试可用安装好修复依赖的 Python 执行：

```bash
python -m unittest discover -s tests -v
```

当前版本未重新执行付费在线生图，也未验证批量生产稳定性。安装成功不等于已登录 Neowow、已生成图片或业务审核通过。实际生图需要按本次页面报价取得费用授权；复杂修复仍可能需要补素材或设计师。
