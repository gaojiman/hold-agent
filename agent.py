#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import socket
import time
import json
import zlib
import platform
PLATFORM = platform.system()


HOST = 'highwe.net'
PORT = 8302
USERKEY = None
VERSION = '1.0'
RATE = 5


def getHoldHost():
    '''
    发布时候要删除
    '''
    hold_host = os.environ.get('HOLDHOST')
    if hold_host is None:
        return HOST
    return hold_host
HOST = getHoldHost()


def setZH():
    if 'zh_CN' in osAction("echo $LANG")[0]:
        pass
    else:
        # 设置中文环境
        osAction('''export PS1='[PEXPECT]\$ '; export LANG=C''')


def shellFn():
    cmd = '''
        prep ()
        {
                echo "$1" | sed -e 's/^ *//g' -e 's/ *$//g' | sed -n '1 p'
        }
        num ()
        {
            case $1 in
                 ''|*[!0-9\.]*) echo 0 ;;
                 *) echo $1 ;;
            esac
        }
    '''
    return cmd


def getRelease():
    '''
    操作系统信息
    '''
    release = ''
    if PLATFORM == 'Linux':
        release = osAction("cat /etc/issue | head -n 1")
        # 截取前三个信息即可
        release = release.split('\n')[0]
        release = ' '.join(release.split()[0:3])
    elif PLATFORM == 'Darwin':
        release = osAction("/usr/bin/uname")
    return release


def getExpInfo(just_info=False):
    '''得到Exception的异常'''
    import traceback
    if just_info:
        info = sys.exc_info()
        return (info, info[0].__name__ + ':' + str(info[1]))
    else:
        return traceback.format_exc()


def osAction(command):
    '''
    代码运行
    '''
    try:
        p = os.popen(command)
        content = p.read()
        p.close()
    except Exception:
        content = 'djoin_error:' + getExpInfo(True)[1]
    return content


def macAddress(mac_cmd="ifconfig | grep -o -E '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}'"):
    mac = osAction(mac_cmd)
    mac = mac.split('\n')[0]
    return mac


def getUniqueID():
    mac = macAddress()
    if not mac:
        time.sleep(20)
        mac = macAddress()
    if not mac:
        mac = macAddress("hostid")
    return mac


def socketConnect():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except socket.error:
        error_info = getExpInfo(True)[1]
        sock = None
    return sock


def getConnect():
    sock = None
    while True:
        sock = socketConnect()
        if sock:
            sock.setblocking(0)
            return sock
        time.sleep(5)


def swapMon():
    '''
    swap page in/out
    '''
    swap = None
    if PLATFORM == 'Linux':
        cmd_fn = shellFn()
        cmd = ''' %s
        swap_total=$(prep $(num "$(cat /proc/meminfo | grep ^SwapTotal: | awk '{ print $2 }')"))
        swap_free=$(prep $(num "$(cat /proc/meminfo | grep ^SwapFree: | awk '{ print $2 }')"))
        swap_usage=$(($swap_total-$swap_free))
        echo $swap_usage
        ''' % cmd_fn
        swap = osAction(cmd)
    else:
        pass
    return swap


def networkMon():
    '''
    networkIO
    '''
    net = None
    if PLATFORM == 'Linux':
        cmd_fn = shellFn()
        net = '''%s
        nic=$(prep "$(ip route get 8.8.8.8 | grep dev | awk -F'dev' '{ print $2 }' | awk '{ print $1 }')")

        if [ -z $nic ]
        then
            nic=$(prep "$(ip link show | grep 'eth[0-9]' | awk '{ print $2 }' | tr -d ':')")
        fi

        if [ -d /sys/class/net/$nic/statistics ]
        then
            rx=$(prep $(num "$(cat /sys/class/net/$nic/statistics/rx_bytes)"))
            tx=$(prep $(num "$(cat /sys/class/net/$nic/statistics/tx_bytes)"))
        else
            rx=$(prep $(num "$(ip -s link show $nic | grep '[0-9]*' | grep -v '[A-Za-z]' | awk '{ print $1 }' | sed -n '1 p')"))
            tx=$(prep $(num "$(ip -s link show $nic | grep '[0-9]*' | grep -v '[A-Za-z]' | awk '{ print $1 }' | sed -n '2 p')"))
        fi
        echo $rx $tx
        ''' % cmd_fn
        net = osAction(net)
    elif PLATFORM == 'Darwin':
        net_cmd = '''/usr/sbin/netstat -ib |grep en | awk '{print $1" "$7" "$10}'
        '''
        net = osAction(net_cmd)
    else:
        pass
    return net


def diskMon():
    '''
    磁盘使用率监控
    '''
    disk = None
    if PLATFORM == 'Linux':
        disk = osAction("df -TPk")
    elif PLATFORM == 'Darwin':
        disk = osAction("/bin/df -lk")
    else:
        pass
    return disk


def topMon():
    import re
    '''
    使用top采到的信息
    '''
    top = None
    if PLATFORM == 'Linux':
        top = osAction("COLUMNS=512 top -c -n2 -b")
        split_re = re.compile(r"\ntop")
        top = "top" + split_re.split(top)[1]
    elif PLATFORM == 'Darwin':
        # mac主机
        top = osAction("/usr/bin/top -o mem -stats pid,user,cpu,mem,command -l2")
        split_re = re.compile(r"\nProcesses:")
        top = "Processes:" + split_re.split(top)[1]
    else:
        pass
    return top


def send():
    global RATE
    mac = getUniqueID()
    release = getRelease()
    sock = getConnect()
    additional = dict(user_key=USERKEY, platform=PLATFORM, mac=mac, release=release, version=VERSION)
    while True:
        mon_data = dict(top=topMon(), disk=diskMon(), swap=swapMon(), net=networkMon(), agent_time=time.time())
        mon_data.update(additional)
        mon_data = json.dumps(mon_data)
        # 数据压缩
        mon_data = zlib.compress(mon_data)
        mon_data += '\u7ed3\u675f'
        try:
            sock.send(mon_data)
        except socket.error:
            error_info = getExpInfo(True)[1]
            sock = getConnect()
        try:
            data = sock.recv(1024)
            data = data.replace("\"", "")
            instructions = data.split(",")
            for instruction in instructions:
                if instruction.find("rate") > -1:
                    strs = instruction.split("=")
                    rate_d = int(strs[1])
                    RATE = rate_d
        except socket.error:
            error_info = getExpInfo(True)[0]
            if error_info[1][0] != 35:
                sock = getConnect()
        time.sleep(RATE)


def exitsKill():
    # 一台主机上的同user_key进程只允许启动一个
    exits_cmd = ''' pid=$(ps aux | grep "agent.py %s" | grep -v  grep |  awk '{print $2}' | head -2)
    echo $pid
    ''' % USERKEY
    out = osAction(exits_cmd)
    out = out.split(' ')
    out = [int(item) for item in out]
    if len(out) == 2:
        pid = min(out)
        # kill掉已有的进程
        kill_cmd = "kill %s" % pid
        osAction(kill_cmd)


def main():
    exitsKill()
    send()


if __name__ == '__main__':
    # 设置中文环境
    setZH()
    param = sys.argv
    if len(param) >= 2:
        USERKEY = param[1]
        main()
    else:
        print "按照 python agent.py USERKEY >> agent.log &  方式启动,USERKEY为您在监控系统中的用户密钥"
