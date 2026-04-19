# PolarOps - 运维控制面板

基于 PySide6 的多服务器远程运维管理桌面应用，支持 MCSManager 和 Squad 游戏服务器的一键部署与管理。

## 功能特性

### 服务器管理
- 多节点服务器列表管理（添加 / 编辑 / 删除 / 导入导出）
- 支持密码和 SSH 密钥两种认证方式
- 实时 SSH 状态检测
- 批量选择与批量操作

### 远程部署
- **MCSManager**：一键安装 Minecraft 服务器管理面板，自动配置公网访问和防火墙
- **Squad 服务器**：一键安装 Squad 游戏服务器，自动配置防火墙规则
- 支持 CentOS 7.6 / 7.9 等主流 Linux 发行版
- 安装过程实时日志输出，进度可视化

### 运维工具
- **远程命令执行**：批量对选定服务器执行自定义命令
- **文件浏览器**：右键节点浏览远程服务器文件系统，支持下载文件
- **一键开放端口**：自定义端口和协议（TCP/UDP），自动配置防火墙（支持 firewalld / ufw / iptables）
- **启动 Squad 实例**：图形化配置并启动 Squad 游戏服务器（Port / QueryPort / BeaconPort / 最大人数 / 固定地图）

### RCON 集成
- 实时查询 Squad 服务器在线人数
- 列表同步显示，一键刷新

### 界面
- 无边框窗口，支持拖动和最小化/关闭
- 深色 / 浅色双主题切换
- 品牌 LOGO 集成

## 技术架构

| 层次 | 技术选型 |
|------|----------|
| UI 框架 | PySide6 (Qt6) |
| 主题 | PyDracula QSS 样式表 |
| SSH 连接 | asyncssh |
| 并发模型 | asyncio + QThread 混合 |
| 配置管理 | JSON 配置文件（原子写入） |

## 目录结构

```
panel/
├── main.py                    # 程序入口
├── config.json                # 服务器和用户配置
├── core/
│   ├── ssh_manager.py         # SSH 连接管理
│   ├── ssh_stream.py          # SSH 流式命令执行
│   ├── status_checker.py      # 批量状态检测
│   ├── deployer.py            # MCSManager/Squad 部署脚本
│   ├── rcon_manager.py        # RCON 协议实现
│   └── config_manager.py      # 配置文件读写
├── ui/
│   ├── login_window.py        # 登录窗口
│   ├── main_window.py         # 主界面
│   ├── draggable.py           # 无边框窗口拖动
│   ├── add_server_dialog.py   # 添加服务器
│   ├── edit_server_dialog.py  # 编辑服务器
│   ├── port_open_dialog.py    # 开放端口
│   ├── file_browser_dialog.py # 文件浏览器
│   └── start_squad_dialog.py  # 启动 Squad 实例
├── threads/
│   ├── command_thread.py      # 命令执行线程
│   └── status_thread.py       # 状态检测线程
└── resources/
    └── style.qss              # QSS 样式表
```

## 安装运行

### 环境要求
- Python 3.10+
- Windows / Linux / macOS

### 安装依赖
```bash
pip install PySide6 asyncssh
```

### 启动
```bash
cd panel
python main.py
```

### 打包为单文件 EXE
```bash
pip install nuitka zstandard
nuitka --standalone --onefile --windows-disable-console ^
  --windows-icon-from-ico=img/透明.png ^
  main.py
```

## 使用说明

### 1. 登录
首次运行使用预设账号登录（在 `config.json` 中配置）

### 2. 添加服务器
点击 **添加服务器** 按钮，填写：
- 节点名称
- IP 地址
- SSH 端口（默认 22）
- 用户名
- 认证方式（密码 / SSH 密钥）
- RCON 信息（用于人数查询）

### 3. 部署服务
勾选目标节点后点击 **安装 MCSManager** 或 **安装 Squad**

### 4. 文件浏览
右键节点 → **浏览文件**，可查看远程目录结构并下载文件

### 5. 启动 Squad
右键节点 → **启动 Squad 实例**，配置端口、人数等参数后启动

### 6. 开放端口
勾选节点 → **开放端口**，输入端口号和协议，自动配置防火墙

### 7. 查看人数
在服务器列表中点击 **刷新人数**，通过 RCON 查询在线玩家

## 注意事项

- 云服务器需先在控制台放行对应安全组/网络 ACL
- Squad 服务器安装约 20-30GB，需要较长时间
- CentOS 7 使用 firewalld，Ubuntu/Debian 使用 ufw，均自动适配
- 配置文件 `config.json` 采用原子写入，防止数据损坏

## License

MIT
