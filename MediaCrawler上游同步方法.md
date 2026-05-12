# MediaCrawler 上游同步方法

当前本地仓库结构是：

- 外层仓库：`/Users/zed/all code/D 互影/media-crawler`
- 上游项目目录：`/Users/zed/all code/D 互影/media-crawler/MediaCrawler`
- 原始上游仓库：`https://github.com/NanmiCoder/MediaCrawler.git`

因为 `MediaCrawler` 现在只是外层仓库里的一个普通子目录，不再保留原来的 `.git` 历史，所以不能直接在当前目录执行：

```bash
git pull upstream main
git merge upstream/main
```

这样会把“上游仓库根目录”错误地合并到“当前仓库根目录”，目录层级会乱掉。

正确做法是：先把上游仓库拉到临时目录，再把代码同步到当前的 `MediaCrawler/` 子目录。

## 一次性同步命令

```bash
cd /tmp
rm -rf MediaCrawler-upstream
git clone --depth=1 https://github.com/NanmiCoder/MediaCrawler.git MediaCrawler-upstream
```

```bash
rsync -av --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'browser_data' \
  --exclude 'data' \
  /tmp/MediaCrawler-upstream/ \
  "/Users/zed/all code/D 互影/media-crawler/MediaCrawler/"
```

同步完成后，回到你自己的外层仓库检查变更：

```bash
cd "/Users/zed/all code/D 互影/media-crawler"
git status
git diff --stat
```

确认没问题后提交：

```bash
git add MediaCrawler
git commit -m "sync MediaCrawler from upstream"
```

## 使用现有脚本同步

仓库根目录已经有脚本：

```bash
/Users/zed/all code/D 互影/media-crawler/sync_mediacrawler.sh
```

最常用命令：

```bash
cd "/Users/zed/all code/D 互影/media-crawler"
bash ./sync_mediacrawler.sh
```

如果脚本因为本地未提交改动而中止，但你确认要继续：

```bash
bash ./sync_mediacrawler.sh --force
```

如果要严格镜像上游，把上游已删除文件也同步删除：

```bash
bash ./sync_mediacrawler.sh --delete --force
```

同步后一样要检查并提交：

```bash
git status
git add MediaCrawler
git commit -m "sync MediaCrawler from upstream"
```

## 如何查看上游最近更新

如果外层仓库已经加了上游 remote：

```bash
cd "/Users/zed/all code/D 互影/media-crawler"
git fetch upstream
git log upstream/main --oneline --decorate -20
```

注意：这里的 `upstream/main` 只能用来看更新内容，不能直接合并。

## 常见问题

### 1. 为什么不能直接 `git pull upstream main`

因为上游仓库的根目录内容，对应的是你当前仓库里的 `MediaCrawler/` 子目录，不是当前仓库根目录。

### 2. 为什么要排除 `.git`

因为你要保留的是你自己的外层仓库历史，而不是把上游仓库的 Git 元数据覆盖进来。

### 3. 为什么通常排除 `browser_data` 和 `data`

这两个目录一般是你本地运行产生的数据和浏览器状态，不属于上游源码。

### 4. 同步完后 `git diff` 很大正常吗

正常。上游改动会和你本地定制修改叠加。先看：

```bash
git diff --stat
```

再决定是否需要手动保留你本地改动。
