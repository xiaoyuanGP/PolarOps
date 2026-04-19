import asyncio
import logging
from typing import Optional, Callable
from core.ssh_stream import SSHStream

logger = logging.getLogger(__name__)

MCSMANAGER_CMD = r'''set -euo pipefail
echo "=== MCSManager 安装开始 ==="

# 检测操作系统版本
if [ -f /etc/os-release ]; then
    OS_NAME=$(. /etc/os-release && echo "$ID")
    OS_VERSION=$(. /etc/os-release && echo "$VERSION_ID")
    echo "检测到系统: $OS_NAME $OS_VERSION"
else
    echo "⚠ 无法检测操作系统版本"
fi

# 检查并安装必要工具
if ! command -v curl >/dev/null 2>&1; then
    echo "安装 curl..."
    if command -v yum >/dev/null 2>&1; then
        # CentOS 7 需要确保 yum 源可用
        yum makecache fast 2>/dev/null || true
        yum install -y curl
    elif command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y curl
    fi
fi

if ! command -v wget >/dev/null 2>&1; then
    echo "安装 wget..."
    if command -v yum >/dev/null 2>&1; then
        yum makecache fast 2>/dev/null || true
        yum install -y wget
    elif command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y wget
    fi
fi

# CentOS 7 特别处理：安装基础依赖
if command -v yum >/dev/null 2>&1; then
    echo "安装系统基础依赖..."
    yum makecache fast 2>/dev/null || true
    yum install -y epel-release 2>/dev/null || true
    yum install -y tar gzip which systemd || true
fi

echo "开始下载并执行 MCSManager 安装脚本..."
sudo su -c "wget -qO- https://script.mcsmanager.com/setup_cn.sh | bash"
echo "MCSManager 安装脚本执行完成"

# 验证安装结果
if [ -d /opt/mcsmanager ]; then
    echo "✓ MCSManager 安装目录存在: /opt/mcsmanager"
    ls -la /opt/mcsmanager/ 2>/dev/null || true
else
    echo "✗ 警告: MCSManager 安装目录不存在，安装可能失败"
    exit 1
fi

# 检查 Node.js 是否可用
if command -v node >/dev/null 2>&1; then
    echo "✓ Node.js 可用: $(node --version)"
else
    echo "✗ Node.js 未找到，尝试修复..."
    if [ -f /opt/mcsmanager/node/bin/node ]; then
        echo "使用 MCSManager 自带的 Node.js"
        sudo ln -sf /opt/mcsmanager/node/bin/node /usr/bin/node
        sudo ln -sf /opt/mcsmanager/node/bin/npm /usr/bin/npm || true
        echo "✓ Node.js 已链接: $(node --version)"
    else
        echo "✗ 未找到 Node.js，安装失败"
        exit 1
    fi
fi

# 检查 systemd 服务是否存在
if systemctl list-unit-files 2>/dev/null | grep -q "mcsm-web"; then
    echo "✓ systemd 服务已注册"
else
    echo "⚠ systemd 服务未注册，将手动创建..."

    sudo tee /etc/systemd/system/mcsm-daemon.service > /dev/null << 'DAEMON_EOF'
[Unit]
Description=MCSManager Daemon
After=network.target

[Service]
WorkingDirectory=/opt/mcsmanager/daemon
ExecStart=/opt/mcsmanager/node/bin/node app.js
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/mcsmanager/node/bin"
User=root
Restart=on-failure

[Install]
WantedBy=multi-user.target
DAEMON_EOF

    sudo tee /etc/systemd/system/mcsm-web.service > /dev/null << 'WEB_EOF'
[Unit]
Description=MCSManager Web
After=network.target mcsm-daemon.service

[Service]
WorkingDirectory=/opt/mcsmanager/web
ExecStart=/opt/mcsmanager/node/bin/node app.js
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/mcsmanager/node/bin"
User=root
Restart=on-failure

[Install]
WantedBy=multi-user.target
WEB_EOF

    sudo systemctl daemon-reload
    echo "✓ systemd 服务文件已创建"
fi

# 检查是否有 install.sh 并执行
if [ -f /opt/mcsmanager/install.sh ]; then
    echo "执行依赖安装..."
    cd /opt/mcsmanager
    sudo bash install.sh
    echo "✓ 依赖安装完成"
fi
'''

MCSMANAGER_POST_CONFIG = r'''set -euo pipefail
echo "=== 配置 MCSManager 公网访问 ==="

if [ -f /opt/mcsmanager/daemon/data/Setting.json ]; then
    echo "修改监听地址为 0.0.0.0..."
    sudo sed -i 's/"ip":[[:space:]]*".*"/"ip": "0.0.0.0"/g' /opt/mcsmanager/daemon/data/Setting.json || true
    echo "✓ 已配置监听地址"
else
    echo "⚠ Setting.json 不存在，跳过监听地址配置"
fi

sudo systemctl stop mcsm-web.service 2>/dev/null || true
sudo systemctl stop mcsm-daemon.service 2>/dev/null || true
sleep 1

echo "启动 MCSManager 服务..."
sudo systemctl daemon-reload
sudo systemctl enable mcsm-daemon.service 2>/dev/null || true
sudo systemctl enable mcsm-web.service 2>/dev/null || true
sudo systemctl start mcsm-daemon.service 2>/dev/null || true
sleep 2
sudo systemctl start mcsm-web.service 2>/dev/null || true
sleep 3

if systemctl is-active mcsm-daemon.service >/dev/null 2>&1; then
    echo "✓ mcsm-daemon 服务运行正常"
else
    echo "✗ mcsm-daemon 服务启动失败"
    echo "尝试手动启动..."
    sudo pkill -f "mcsm-daemon" 2>/dev/null || true
    sudo pkill -f "daemon/app.js" 2>/dev/null || true
    sleep 1
    cd /opt/mcsmanager/daemon 2>/dev/null || exit 1
    sudo nohup /opt/mcsmanager/node/bin/node app.js >/dev/null 2>&1 &
    echo "已手动启动 daemon"
fi

if systemctl is-active mcsm-web.service >/dev/null 2>&1; then
    echo "✓ mcsm-web 服务运行正常"
else
    echo "✗ mcsm-web 服务启动失败"
    echo "尝试手动启动..."
    sudo pkill -f "mcsm-web" 2>/dev/null || true
    sudo pkill -f "web/app.js" 2>/dev/null || true
    sleep 1
    cd /opt/mcsmanager/web 2>/dev/null || exit 1
    sudo nohup /opt/mcsmanager/node/bin/node app.js >/dev/null 2>&1 &
    echo "已手动启动 web"
fi

echo "配置防火墙放行 MCSManager 端口..."

if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active firewalld >/dev/null 2>&1; then
    echo "[firewalld] 放行端口..."
    sudo firewall-cmd --permanent --add-port=23333/tcp
    sudo firewall-cmd --permanent --add-port=24444/tcp
    sudo firewall-cmd --reload
    echo "✓ firewalld 已放行 23333/tcp 24444/tcp"
elif command -v ufw >/dev/null 2>&1; then
    echo "[ufw] 放行端口..."
    sudo ufw allow 23333/tcp || true
    sudo ufw allow 24444/tcp || true
    sudo ufw reload || true
    echo "✓ ufw 已放行 23333/tcp 24444/tcp"
elif command -v iptables >/dev/null 2>&1; then
    echo "[iptables] 放行端口..."
    sudo iptables -C INPUT -p tcp --dport 23333 -j ACCEPT 2>/dev/null || sudo iptables -A INPUT -p tcp --dport 23333 -j ACCEPT
    sudo iptables -C INPUT -p tcp --dport 24444 -j ACCEPT 2>/dev/null || sudo iptables -A INPUT -p tcp --dport 24444 -j ACCEPT
    sudo mkdir -p /etc/iptables 2>/dev/null || true
    command -v iptables-save >/dev/null 2>&1 && sudo iptables-save | sudo tee /etc/iptables/rules.v4 >/dev/null 2>&1 || true
    echo "✓ iptables 已放行 23333/tcp 24444/tcp"
else
    echo "⚠ 未检测到防火墙，跳过端口放行"
fi

sleep 2
LISTEN_ADDR=$(ss -tlnp 2>/dev/null | grep -E ':(23333|24444)' | head -1 || true)
if [ -n "$LISTEN_ADDR" ]; then
    echo "✓ 服务已启动并监听: $LISTEN_ADDR"
else
    echo "✗ 警告: 服务可能未正确启动"
    echo "请手动检查: journalctl -u mcsm-web.service -n 50 --no-pager"
    echo "或查看日志: journalctl -u mcsm-daemon.service -n 50 --no-pager"
fi

echo "MCSManager 公网访问配置完成"
'''

SQUAD_POST_CONFIG = r'''set -euo pipefail
echo "=== 配置 Squad 服务器 ==="

SQUAD_DIR=""
if [ -d /data/SquadGame ]; then
    SQUAD_DIR="/data"
elif [ -d /data/squadserver ]; then
    SQUAD_DIR="/data"
elif [ -d /home/squadserver ]; then
    SQUAD_DIR="/home/squadserver"
elif [ -d /root/squadserver ]; then
    SQUAD_DIR="/root/squadserver"
elif [ -d /home/steam/squadserver ]; then
    SQUAD_DIR="/home/steam/squadserver"
elif [ -d /opt/squad ]; then
    SQUAD_DIR="/opt/squad"
elif [ -d /opt/squadserver ]; then
    SQUAD_DIR="/opt/squadserver"
elif [ -d "$(pwd)/squadserver" ]; then
    SQUAD_DIR="$(pwd)/squadserver"
elif [ -d "$(pwd)/SquadGame" ]; then
    SQUAD_DIR="$(pwd)"
else
    FOUND_DIR=$(find / -maxdepth 4 -type d -name "SquadGame" 2>/dev/null | head -1 || true)
    if [ -n "$FOUND_DIR" ]; then
        SQUAD_DIR="$(dirname "$FOUND_DIR")"
    fi
fi

if [ -n "$SQUAD_DIR" ]; then
    echo "✓ 找到 Squad 安装目录: $SQUAD_DIR"
    ls -la "$SQUAD_DIR/" 2>/dev/null || true
else
    echo "✗ 未找到 Squad 安装目录，请检查安装是否成功"
    exit 1
fi

echo "配置防火墙放行 Squad 端口..."
echo "放行端口: 7787(tcp/udp), 27165(tcp/udp), 15000(udp)"

if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active firewalld >/dev/null 2>&1; then
    echo "[firewalld] 放行端口..."
    sudo firewall-cmd --permanent --add-port=7787/tcp
    sudo firewall-cmd --permanent --add-port=7787/udp
    sudo firewall-cmd --permanent --add-port=27165/tcp
    sudo firewall-cmd --permanent --add-port=27165/udp
    sudo firewall-cmd --permanent --add-port=15000/udp
    sudo firewall-cmd --reload
    echo "✓ firewalld 已放行 Squad 端口 (7787, 27165, 15000)"
elif command -v ufw >/dev/null 2>&1; then
    echo "[ufw] 放行端口..."
    sudo ufw allow 7787/tcp || true
    sudo ufw allow 7787/udp || true
    sudo ufw allow 27165/tcp || true
    sudo ufw allow 27165/udp || true
    sudo ufw allow 15000/udp || true
    sudo ufw reload || true
    echo "✓ ufw 已放行 Squad 端口 (7787, 27165, 15000)"
elif command -v iptables >/dev/null 2>&1; then
    echo "[iptables] 放行端口..."
    sudo iptables -C INPUT -p tcp --dport 7787 -j ACCEPT 2>/dev/null || sudo iptables -A INPUT -p tcp --dport 7787 -j ACCEPT
    sudo iptables -C INPUT -p udp --dport 7787 -j ACCEPT 2>/dev/null || sudo iptables -A INPUT -p udp --dport 7787 -j ACCEPT
    sudo iptables -C INPUT -p tcp --dport 27165 -j ACCEPT 2>/dev/null || sudo iptables -A INPUT -p tcp --dport 27165 -j ACCEPT
    sudo iptables -C INPUT -p udp --dport 27165 -j ACCEPT 2>/dev/null || sudo iptables -A INPUT -p udp --dport 27165 -j ACCEPT
    sudo iptables -C INPUT -p udp --dport 15000 -j ACCEPT 2>/dev/null || sudo iptables -A INPUT -p udp --dport 15000 -j ACCEPT
    sudo mkdir -p /etc/iptables 2>/dev/null || true
    command -v iptables-save >/dev/null 2>&1 && sudo iptables-save | sudo tee /etc/iptables/rules.v4 >/dev/null 2>&1 || true
    echo "✓ iptables 已放行 Squad 端口 (7787, 27165, 15000)"
else
    echo "⚠ 未检测到防火墙，跳过端口放行"
fi

echo "Squad 服务器配置完成"
'''

SQUAD_CMD = r'''set -euo pipefail
echo "=== Squad 服务器安装开始 ==="

# 检测操作系统版本
if [ -f /etc/os-release ]; then
    OS_NAME=$(. /etc/os-release && echo "$ID")
    OS_VERSION=$(. /etc/os-release && echo "$VERSION_ID")
    echo "检测到系统: $OS_NAME $OS_VERSION"
else
    echo "⚠ 无法检测操作系统版本"
fi

# 检查并安装必要工具
if ! command -v curl >/dev/null 2>&1; then
    echo "安装 curl..."
    if command -v yum >/dev/null 2>&1; then
        yum makecache fast 2>/dev/null || true
        yum install -y curl
    elif command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y curl
    fi
fi

if ! command -v screen >/dev/null 2>&1; then
    echo "安装 screen..."
    if command -v yum >/dev/null 2>&1; then
        yum makecache fast 2>/dev/null || true
        yum install -y screen
    elif command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y screen
    fi
fi

# CentOS 7 特别处理
if command -v yum >/dev/null 2>&1; then
    echo "检测 CentOS 7 环境，安装基础依赖..."
    yum makecache fast 2>/dev/null || true
    # 安装 EPEL 源（可能已安装）
    yum install -y epel-release 2>/dev/null || true
    # 安装 32 位兼容库
    yum install -y glibc.i686 libstdc++.i686 2>/dev/null || true
    yum install -y ncurses-libs.i686 2>/dev/null || true
fi

# 安装 SteamCMD 依赖
echo "安装 SteamCMD 依赖..."
if command -v yum >/dev/null 2>&1; then
    yum install -y glibc.i686 libstdc++.i686 ncurses-libs.i686 2>/dev/null || true
elif command -v apt-get >/dev/null 2>&1; then
    dpkg --add-architecture i386 || true
    apt-get update
    apt-get install -y lib32gcc-s1 lib32stdc++6 libc6-i386 || \
    apt-get install -y lib32gcc1 lib32stdc++6 libc6-i386
fi

# 创建目录
sudo mkdir -p /data
sudo mkdir -p /home/steam/steamcmd

# 下载并解压 SteamCMD
if [ ! -f /home/steam/steamcmd/steamcmd.sh ]; then
    echo "下载 SteamCMD..."
    curl -fsSL https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz -o /tmp/steamcmd.tar.gz
    sudo tar -xzf /tmp/steamcmd.tar.gz -C /home/steam/steamcmd/
    rm -f /tmp/steamcmd.tar.gz
    echo "SteamCMD 安装完成"
fi

sudo chmod +x /home/steam/steamcmd/steamcmd.sh

echo "测试 SteamCMD 是否可运行..."
/home/steam/steamcmd/steamcmd.sh +quit

echo "开始下载 Squad 服务器文件 (这可能需要较长时间，请耐心等待)..."

# 前台执行，避免"后台刚启动就结束但外层看不出来"的问题
/home/steam/steamcmd/steamcmd.sh \
    +force_install_dir /data \
    +login anonymous \
    +app_update 403240 validate \
    +quit

echo "检查安装结果..."
if [ -d /data/SquadGame ]; then
    echo "✓ Squad 安装成功，目录存在: /data/SquadGame"
    ls -la /data | head -50 || true
else
    echo "✗ Squad 安装可能失败，未找到 /data/SquadGame"
    exit 1
fi
''' + "\n" + SQUAD_POST_CONFIG


class Deployer:
    def __init__(self):
        self._streams = {}

    async def deploy_mcsmanager(
        self,
        host: str,
        port: int,
        user: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        output_callback: Optional[Callable] = None
    ):
        if output_callback is None:
            output_callback = lambda h, m: print(f"[{h}] {m}")

        output_callback(host, "开始安装 MCSManager...")
        stream = SSHStream(
            host=host,
            port=port,
            user=user,
            password=password,
            key_path=key_path
        )

        try:
            await stream.execute_streaming(MCSMANAGER_CMD, output_callback)
            output_callback(host, "=" * 50)
            output_callback(host, "MCSManager 安装完成！")
            output_callback(host, f"HTTP面板地址: http://{host}:23333")
            output_callback(host, "请在浏览器中打开上述地址")
            output_callback(host, "=" * 50)

            stream2 = SSHStream(
                host=host,
                port=port,
                user=user,
                password=password,
                key_path=key_path
            )
            await stream2.execute_streaming(MCSMANAGER_POST_CONFIG, output_callback)

        except Exception as exc:
            output_callback(host, f"MCSManager 安装失败: {str(exc)}")
            raise

    async def deploy_squad(
        self,
        host: str,
        port: int,
        user: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        output_callback: Optional[Callable] = None
    ):
        if output_callback is None:
            output_callback = lambda h, m: print(f"[{h}] {m}")

        output_callback(host, "开始安装 Squad 服务器...")
        stream = SSHStream(
            host=host,
            port=port,
            user=user,
            password=password,
            key_path=key_path
        )

        try:
            await stream.execute_streaming(SQUAD_CMD, output_callback)
            output_callback(host, "=" * 50)
            output_callback(host, "Squad 安装完成")
            output_callback(host, f"游戏服务器地址: {host}:27015")
            output_callback(host, "=" * 50)

        except Exception as exc:
            output_callback(host, f"Squad 安装失败: {str(exc)}")
            raise

    async def deploy_batch(
        self,
        servers: list,
        deploy_type: str,
        output_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None
    ):
        if output_callback is None:
            output_callback = lambda h, m: print(f"[{h}] {m}")
        if progress_callback is None:
            progress_callback = lambda c, t: None

        total = len(servers)
        completed = 0

        async def _deploy_one(server):
            nonlocal completed
            try:
                if deploy_type == "mcsmanager":
                    await self.deploy_mcsmanager(
                        host=server["ip"],
                        port=server.get("port", 22),
                        user=server["user"],
                        password=server.get("password") if server.get("auth_type") == "password" else None,
                        key_path=server.get("key_path") if server.get("auth_type") == "key" else None,
                        output_callback=output_callback
                    )
                elif deploy_type == "squad":
                    await self.deploy_squad(
                        host=server["ip"],
                        port=server.get("port", 22),
                        user=server["user"],
                        password=server.get("password") if server.get("auth_type") == "password" else None,
                        key_path=server.get("key_path") if server.get("auth_type") == "key" else None,
                        output_callback=output_callback
                    )
                else:
                    output_callback(server["ip"], f"未知部署类型: {deploy_type}")
            except Exception as exc:
                output_callback(server["ip"], f"部署失败: {str(exc)}")
            finally:
                completed += 1
                progress_callback(completed, total)

        tasks = [_deploy_one(s) for s in servers]
        await asyncio.gather(*tasks, return_exceptions=True)