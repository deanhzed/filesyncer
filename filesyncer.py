#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import hashlib
import urllib.request
from urllib.parse import urlparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import difflib
from typing import Dict, List, Tuple
import platform
from datetime import datetime

try:
    from colorama import init, Fore, Style
    init()  # 初始化colorama
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    # 如果没有colorama，创建伪类以保持兼容性
    class Fore:
        GREEN = ''
        RED = ''
        YELLOW = ''
        BLUE = ''
        MAGENTA = ''
        CYAN = ''
        RESET = ''
    
    class Style:
        BRIGHT = ''
        RESET_ALL = ''

def load_config(config_file: str = "config.json") -> List[Dict]:
    """加载文件配置"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 如果包含files键，返回files部分
            if isinstance(data, dict) and "files" in data:
                return data["files"]
            # 如果是数组格式（旧格式），直接返回
            elif isinstance(data, list):
                return data
            else:
                raise ValueError("配置文件格式不正确")
    except FileNotFoundError:
        print_colored(f"配置文件 {config_file} 未找到，使用默认配置", Fore.YELLOW)
        default_files = [
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
        
        # 生成简单的配置文件模板
        config_template = {
            "files": default_files
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_template, f, ensure_ascii=False, indent=2)
            print_colored(f"已创建默认配置文件 {config_file}", Fore.GREEN)
        except Exception as e:
            print_colored(f"创建配置文件失败: {str(e)}", Fore.RED)
        
        return default_files
    except json.JSONDecodeError as e:
        print_colored(f"配置文件 {config_file} 格式错误: {str(e)}", Fore.RED)
        return []

def save_config(config_data: Dict, config_file: str = "config.json") -> bool:
    """保存配置文件（仅包含文件列表）"""
    try:
        # 只保存files部分
        data_to_save = {"files": config_data.get("files", [])}
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        print(f"配置文件保存成功: {config_file}")  # 调试信息
        return True
    except Exception as e:
        print_colored(f"保存配置文件失败: {str(e)}", Fore.RED)
        return False

def load_sync_history(config_file: str = "config.json") -> Dict:
    """从配置文件加载同步历史记录"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 如果包含history键，返回整个数据
            if isinstance(data, dict) and "history" in data:
                return data
            else:
                return {"files": data if isinstance(data, list) else [], "history": []}
    except (FileNotFoundError, json.JSONDecodeError):
        return {"files": [], "history": []}

def save_sync_history(history_data: Dict, config_file: str = "config.json") -> bool:
    """将同步历史记录保存到配置文件"""
    try:
        # 读取现有配置
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                # 如果是旧格式（直接是数组），转换为新格式
                if isinstance(config_data, list):
                    config_data = {
                        "files": config_data,
                        "history": history_data.get("history", [])
                    }
                elif isinstance(config_data, dict):
                    config_data["history"] = history_data.get("history", [])
        except (FileNotFoundError, json.JSONDecodeError):
            config_data = {
                "files": [],
                "history": history_data.get("history", [])
            }
        
        result = save_config_with_history(config_data, config_file)
        print(f"保存历史记录结果: {result}")  # 调试信息
        return result
    except Exception as e:
        print_colored(f"保存历史记录失败: {str(e)}", Fore.RED)
        return False

def load_sync_history(history_file: str = "sync_history.json") -> Dict:
    """加载同步历史记录"""
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 如果历史文件不存在，创建一个空的历史记录
        history = {"history": []}
        save_sync_history(history, history_file)
        return history
    except json.JSONDecodeError as e:
        print_colored(f"历史记录文件 {history_file} 格式错误: {str(e)}", Fore.RED)
        return {"history": []}

def save_sync_history(history: Dict, history_file: str = "sync_history.json") -> bool:
    """保存同步历史记录"""
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print_colored(f"保存历史记录失败: {str(e)}", Fore.RED)
        return False
download_progress = {}  # 存储下载进度
lock = threading.Lock()  # 用于线程安全

def print_colored(text: str, color: str = '', style: str = '') -> None:
    """带颜色的打印函数"""
    try:
        if HAS_COLORAMA:
            print(f"{style}{color}{text}{Style.RESET_ALL}")
        else:
            print(text)
    except UnicodeEncodeError:
        # 处理Windows命令行可能不支持某些Unicode字符的问题
        if HAS_COLORAMA:
            print(f"{style}{color}{text.encode('gbk', errors='ignore').decode('gbk')}{Style.RESET_ALL}")
        else:
            print(text.encode('gbk', errors='ignore').decode('gbk'))

def calculate_md5(file_path: str) -> str:
    """计算文件的MD5值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return ""

def download_file(url: str, local_path: str, file_name: str) -> Tuple[bool, str]:
    """下载文件并显示进度条"""
    try:
        # 创建目录（如果不存在）
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # 打开URL
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # 初始化进度
            with lock:
                download_progress[file_name] = {
                    "total": total_size,
                    "downloaded": 0,
                    "finished": False
                }
            
            # 写入文件
            with open(local_path, 'wb') as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # 更新进度
                    with lock:
                        download_progress[file_name]["downloaded"] = downloaded
        
        # 标记为完成
        with lock:
            download_progress[file_name]["finished"] = True
            
        return True, "下载成功"
    except Exception as e:
        with lock:
            if file_name in download_progress:
                download_progress[file_name]["finished"] = True
        return False, f"下载失败: {str(e)}"

def show_progress() -> None:
    """显示下载进度"""
    while True:
        with lock:
            # 检查是否所有下载都已完成
            all_finished = all(info["finished"] for info in download_progress.values())
            
            # 清屏（兼容多平台）
            if platform.system() == "Windows":
                os.system("cls")
            else:
                os.system("clear")
            
            # 显示每个文件的进度
            for file_name, info in download_progress.items():
                if info["total"] > 0:
                    percent = min(100, int((info["downloaded"] / info["total"]) * 100))
                else:
                    percent = 100 if info["finished"] else 0
                
                # 绘制进度条
                bar_length = 40
                filled_length = int(bar_length * percent // 100)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                
                status = "完成" if info["finished"] else "下载中"
                print_colored(f"{file_name}: |{bar}| {percent}% {status}", Fore.CYAN)
                if info["total"] > 0:
                    print(f"  已下载: {info['downloaded']}/{info['total']} 字节")
                print()
        
        if all_finished:
            break
        
        # 短暂休眠以减少CPU使用
        import time
        time.sleep(0.5)

def compare_files(old_file: str, new_content: bytes) -> Tuple[bool, List[str]]:
    """比较文件差异"""
    try:
        with open(old_file, 'rb') as f:
            old_content = f.read()
        
        if old_content == new_content:
            return False, []  # 没有变化
        
        # 转换为字符串进行行比较
        old_lines = old_content.decode('utf-8', errors='ignore').splitlines(keepends=True)
        new_lines = new_content.decode('utf-8', errors='ignore').splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            old_lines, 
            new_lines, 
            fromfile=f'a/{os.path.basename(old_file)}',
            tofile=f'b/{os.path.basename(old_file)}'
        ))
        
        return True, diff  # 有变化
    except FileNotFoundError:
        return True, ["文件是新的"]  # 新文件
    except Exception as e:
        return False, [f"比较文件时出错: {str(e)}"]

def update_file(file_info: Dict) -> Dict:
    """更新单个文件"""
    name = file_info["name"]
    url = file_info["url"]
    local_path = file_info["local_path"]
    
    result = {
        "name": name,
        "status": "unknown",
        "message": "",
        "diff": []
    }
    
    try:
        # 计算本地文件的MD5
        local_md5 = calculate_md5(local_path)
        
        # 下载新文件内容到内存
        with urllib.request.urlopen(url) as response:
            new_content = response.read()
            new_md5 = hashlib.md5(new_content).hexdigest()
        
        # 比较MD5
        if local_md5 == new_md5:
            result["status"] = "unchanged"
            result["message"] = "文件无变化"
        else:
            # 比较详细差异
            has_diff, diff_lines = compare_files(local_path, new_content)
            result["diff"] = diff_lines
            
            if not local_md5:
                result["status"] = "new"
                result["message"] = f"新文件 (MD5: {new_md5})"
            else:
                result["status"] = "updated"
                result["message"] = f"文件已更新 (旧MD5: {local_md5}, 新MD5: {new_md5})"
            
            # 保存新文件
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                f.write(new_content)
                
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"更新失败: {str(e)}"
    
    return result

def print_update_result(result: Dict) -> None:
    """打印更新结果"""
    name = result["name"]
    status = result["status"]
    message = result["message"]
    
    if status == "unchanged":
        print_colored(f"✓ {name}: {message}", Fore.GREEN)
    elif status == "new":
        print_colored(f"+ {name}: {message}", Fore.BLUE)
    elif status == "updated":
        print_colored(f"↑ {name}: {message}", Fore.YELLOW)
        # 显示差异（如果有）
        if result["diff"]:
            print("  差异预览:")
            for line in result["diff"][:10]:  # 只显示前10行
                if line.startswith('+'):
                    print_colored(f"    {line.rstrip()}", Fore.GREEN)
                elif line.startswith('-'):
                    print_colored(f"    {line.rstrip()}", Fore.RED)
                elif line.startswith('@'):
                    print_colored(f"    {line.rstrip()}", Fore.MAGENTA)
                else:
                    print(f"    {line.rstrip()}")
            if len(result["diff"]) > 10:
                print_colored(f"    ... 还有{len(result["diff"]) - 10}行差异", Fore.CYAN)
    elif status == "error":
        print_colored(f"✗ {name}: {message}", Fore.RED)

def main() -> None:
    """主函数"""
    print_colored("FileSyncer", Fore.CYAN, Style.BRIGHT)
    print("=" * 50)
    
    # 加载配置
    files_config = load_config()
    
    if not files_config:
        print_colored("没有找到有效的文件配置", Fore.RED)
        return
    
    # 从独立的历史文件加载同步历史
    sync_data = load_sync_history("sync_history.json")
    
    # 显示上次同步时间
    if sync_data["history"]:
        last_sync = sync_data["history"][-1]
        print_colored(f"上次同步时间: {last_sync['timestamp']}", Fore.CYAN)
    else:
        print_colored("这是首次同步", Fore.CYAN)
    
    print()
    
    # 记录本次同步开始时间
    start_time = datetime.now()
    sync_record = {
        "timestamp": start_time.isoformat(),
        "files": []
    }
    
    # 使用线程池下载所有文件
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有下载任务
        future_to_file = {
            executor.submit(update_file, file_info): file_info 
            for file_info in files_config
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_file):
            file_info = future_to_file[future]
            try:
                result = future.result()
                print_update_result(result)
                # 添加到同步记录
                sync_record["files"].append(result)
            except Exception as e:
                print_colored(f"✗ {file_info['name']}: 处理时发生异常: {str(e)}", Fore.RED)
    
    # 将同步记录添加到历史中
    sync_data["history"].append(sync_record)
    # 只保留最近10次记录
    if len(sync_data["history"]) > 10:
        sync_data["history"] = sync_data["history"][-10:]
    
    # 保存同步记录到独立的历史文件
    save_sync_history(sync_data, "sync_history.json")
    
    # 显示本次同步统计
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print("=" * 50)
    print_colored(f"同步完成! 耗时: {duration:.2f}秒", Fore.GREEN, Style.BRIGHT)
    
    # 显示历史记录摘要
    print("\n最近同步记录:")
    for i, record in enumerate(sync_data["history"][-5:]):  # 显示最近5次
        status_counts = {"unchanged": 0, "new": 0, "updated": 0, "error": 0}
        for file in record["files"]:
            status_counts[file["status"]] += 1
        
        print(f"  {record['timestamp'][:19]} - 新增:{status_counts['new']} 更新:{status_counts['updated']} 无变化:{status_counts['unchanged']} 错误:{status_counts['error']}")

def wait_for_exit() -> None:
    """等待用户按键后退出"""
    print()
    if platform.system() == "Windows":
        os.system("pause")  # Windows专用
    else:
        input("按回车键退出...")  # 跨平台方案

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n操作被用户取消", Fore.YELLOW)
    except Exception as e:
        print_colored(f"程序发生未预期的错误: {str(e)}", Fore.RED)
    finally:
        wait_for_exit()