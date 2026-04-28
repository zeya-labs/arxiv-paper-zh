# arxiv-paper-zh

把 arXiv 论文变成**可重新编译的中文 PDF**，而不只是凑合着看的机翻结果。

核心思路很简单：下载 arXiv 的 LaTeX 源码，保留一份原始的 `source/`，复制出 `source-zh/`，只在中文副本里翻译，最后用 `tectonic` 编译出 `paper-zh.pdf`。译文是真正的 `.tex` 源码，随时能校对、改公式、重新编译。

---

## 效果长什么样 👀

左边是 arXiv 原 PDF，右边是从 `source-zh/` 重新编译出来的中文版：

![WorldSplat 原文 PDF 与中文 PDF 对照](docs/assets/example-worldsplat-pdf.png)

标题、摘要、正文都翻成中文；作者、引用、公式、图表结构完整保留。这不是贴在 PDF 上的翻译层，是真的重新编译出来的。

一篇论文做完后目录是这样：

```
papers/WorldSplat/
  paper.pdf       ← arXiv 原 PDF
  paper-zh.pdf    ← 编译出的中文 PDF
  source/         ← arXiv 原始 LaTeX，不动
  source-zh/      ← 中文 LaTeX，所有翻译都在这里
```

---

## 工作流 🔄

![arxiv-paper-zh 工作流示意图](docs/assets/arxiv-paper-zh-workflow.png)

1. 下载 arXiv 源码包 + 原始 PDF
2. 解压到 `source/`，复制一份到 `source-zh/`
3. 通读论文，确认术语、方法名、数据集名
4. 在 `source-zh/` 里逐段翻译可见文本
5. 扫描漏翻段落
6. `tectonic` 编译，输出 `paper-zh.pdf`

不调用翻译 API，不碰 `source/`。

---

## 安装

有两种方式。

**方式一：把 GitHub 链接给 Agent**

如果你的 Agent 支持从 GitHub 安装 Skill，直接把这句话发给它：

```text
请从 https://github.com/zeya-labs/arxiv-paper-zh 安装这个 Codex Skill。
```

Agent 会自己 clone 仓库，并把里面包含 `SKILL.md` 的 `arxiv-paper-zh/` 目录放到本地 skills 目录。

**方式二：手动安装**

```bash
git clone https://github.com/zeya-labs/arxiv-paper-zh.git
cd arxiv-paper-zh

# 把 Skill 装进 Codex
mkdir -p ~/.codex/skills
cp -R arxiv-paper-zh/. ~/.codex/skills/arxiv-paper-zh/
```

本地需要 Python 3.10+、能访问 `arxiv.org`，以及 `tectonic`：

```bash
tectonic --version
```

---

## 用法

对 Agent 说一句就行：

```
帮我把 2509.23402 下载到 ./papers，全文翻译成中文，编译出 paper-zh.pdf。
```


---

## 翻译规则

**翻译**：标题、摘要、正文、章节标题、图注、表头、脚注。

**保留原样**：模型名、数据集名、benchmark 名、公式、代码标识符、citation key、URL、社区已固定的专有名词。

---

## 适不适合用？

✅ 适合：你想认真读一篇论文，希望译文有 `.tex` 源码、能校对和重编译。

❌ 不适合：arXiv 只提供 PDF（没有 LaTeX 源码）；或者你只需要五分钟速览摘要。
