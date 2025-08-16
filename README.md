# FileSyncer

一个通用的文件同步工具，可以从多个网址下载文件并跟踪更新，具有以下特性：

## 功能特性

1. 从多个网址下载文件
2. 比较文件差异和MD5值来检查更新
3. 显示下载进度条
4. 使用颜色区分不同状态
5. 跨平台兼容（Windows/Linux/macOS）
6. 下载完成后等待用户按键退出
7. 同步历史记录功能

## 安装依赖

虽然脚本主要使用Python标准库，但为了获得彩色输出功能，可以安装可选依赖：

```bash
pip install -r requirements.txt
```

或者直接安装colorama库：
```bash
pip install colorama
```

如果没有安装colorama，脚本仍然可以正常工作，只是没有彩色输出。

## 使用方法

1. 确保系统已安装Python 3.x
2. （可选）安装colorama库以获得彩色输出：
   ```
   pip install colorama
   ```
3. 首次运行程序会自动生成 `config.json` 配置文件
4. 编辑 `config.json` 文件，添加需要下载的文件信息
5. 运行脚本：
   - Windows系统：双击 `run_updater.bat` 或运行 `python filesyncer.py`
   - Linux/macOS系统：运行 `./run_updater.sh` 或 `python3 filesyncer.py`

## 状态颜色说明

- **绿色**：文件无变化
- **蓝色**：新文件
- **黄色**：文件已更新
- **红色**：错误信息

## 配置文件说明

`config.json` 文件包含要下载的文件信息：
- `name`：文件名称（用于显示）
- `url`：文件下载地址
- `local_path`：本地保存路径

### 配置文件格式

首次运行程序会自动生成一个简单的配置文件模板：

```json
{
  "files": [
    {
      "name": "示例文件1",
      "url": "https://httpbin.org/uuid",
      "local_path": "files/file1.txt"
    },
    {
      "name": "示例文件2",
      "url": "https://httpbin.org/user-agent",
      "local_path": "files/file2.txt"
    }
  ]
}
```

### 配置项详细说明

- **`name`**: 文件的显示名称，用于在程序输出中标识文件。
- **`url`**: 文件的下载地址，必须是可直接访问的URL。
- **`local_path`**: 文件保存的本地路径。
  - **相对路径**: 如 `"files/file.txt"`，路径是相对于程序运行目录的。
  - **绝对路径**:
    - Windows示例: `"C:/Users/username/Documents/file.txt"`
    - Linux/macOS示例: `"/home/username/file.txt"`

### JSON格式注意事项

- 使用双引号包裹字符串，不要使用单引号
- 路径分隔符推荐使用正斜杠 '/'，即使在Windows上
- 不需要转义普通路径字符
- 如需包含特殊字符，请使用双反斜杠转义

### 添加更多文件

在 `files` 数组中添加更多对象，用逗号分隔。例如：

```json
{
  "files": [
    {
      "name": "Python官网首页",
      "url": "https://www.python.org/",
      "local_path": "downloads/python_homepage.html"
    },
    {
      "name": "另一个文件",
      "url": "https://example.com/file.txt",
      "local_path": "downloads/another_file.txt"
    }
  ]
}
```

## 同步历史记录

脚本会自动记录每次同步的历史信息，保存在 `sync_history.json` 文件中：
- 记录每次同步的时间戳
- 保存每个文件的更新状态
- 保留最近10次同步记录
- 显示上次同步时间和历史记录摘要

## 许可证

本项目采用 MIT 许可证，详情请见 [LICENSE](LICENSE) 文件。