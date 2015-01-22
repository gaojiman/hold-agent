#!/usr/bin/env python
#-*- coding:utf-8 -*-
import win32serviceutil
import win32service
import win32event
import os
import sys
import json
import platform
PLATFORM = platform.system()
import socket
import psutil
import time
import zlib

HOST = 'highwe.net'
PORT = 8302
USER_KEY = None
MAC = None
VERSION = '1.0'
RATE = 5


def getRelease():
    release = ''
    re = osAction("wmic os get caption").decode('GBK')
    if re:
        release = re.split('\n')[1]
    else:
        re = osAction('systeminfo | findstr "os"').decode('GBK')
        release = (((re.split('\n')[0]).split(':'))[1]).lstrip()
    return release


def cpuMon():
    '''cpu'''
    mon_data = {}
    rt = psutil.cpu_times_percent(interval=None, percpu=False)
    mon_data['user'] = float(rt.user)
    mon_data['sys'] = float(rt.system)
    mon_data['idle'] = float(rt.idle)
    mon_data['wa'] = 0
    return mon_data


def memMon():
    mon_data = {}
    rt = psutil.phymem_usage()
    mon_data['total'] = float(rt.total)
    mon_data['available'] = float(rt.available)
    mon_data['used'] = float(rt.used)
    mon_data['free'] = float(rt.free)
    mon_data['percent'] = rt.percent
    return mon_data


def netMon():
    mon_data = {}
    data = psutil.network_io_counters(pernic=False)
    mon_data['send_kb'] = int((data.bytes_sent) / 1024)
    mon_data['receive_kb'] = int((data.bytes_recv) / 1024)
    return mon_data


def diskMon():
    '''磁盘(文件系统)使用率'''
    mon_data = osAction("wmic logicaldisk get caption, filesystem, size, freespace, drivetype")
    if not mon_data:  # 如果主机不能使用wmic命令，则使用psutil模块取
        disk_data = []
        data = psutil.disk_partitions(all=False)
        for i in data:
            rt = {}
            if i.fstype == "NTFS":
                j = psutil.disk_usage(i.mountpoint)
                rt['mounted'] = (i.mountpoint).split('\\')[0]
                rt['disk_type'] = i.fstype
                rt['total'] = float(j.total) / 1024
                rt['capacity'] = j.percent
                rt['used'] = float(j.used) / 1024
                rt['available'] = float(j.free) / 1024
                disk_data.append(rt)
        mon_data = disk_data[:]
    return mon_data


def topMon():
    result = psutil.get_process_list()
    pid_data = []
    for i in result:
        d = {}
        try:
            d['cmd'] = (i.name()).decode('utf-8')
            if d['cmd'] == 'System Idle Process':
                continue
            else:
                d['cpu'] = round(i.cpu_percent(interval=None), 2)
                d['mem'] = round(i.memory_percent(), 2)
                d['pid'] = i.pid
                try:
                    d['user'] = i.username()
                except psutil.error.AccessDenied:
                    d['user'] = 'Adminstrator'
                pid_data.append(d)
        except Exception:
            continue
    return pid_data


def cpuMemTopMon():
    '''主机性能数据CPU, 内存, Top10'''
    return dict(cpu=cpuMon(), top=topMon(), mem=memMon())


def osAction(command):
    p = os.popen(command)
    content = p.read()
    p.close()
    return content


def get_macaddress(host='localhost'):
    import ctypes
    import struct
    # Check for api availability
    try:
        SendARP = ctypes.windll.Iphlpapi.SendARP
    except:
        raise NotImplementedError('Usage only on Windows 2000 and above')

    # Doesn't work with loopbacks, but let's try and help.
    if host == '127.0.0.1' or host.lower() == 'localhost':
        host = socket.gethostname()

    # gethostbyname blocks, so use it wisely.
    try:
        inetaddr = ctypes.windll.wsock32.inet_addr(host)
        if inetaddr in (0, -1):
            raise Exception
    except:
        hostip = socket.gethostbyname(host)
        inetaddr = ctypes.windll.wsock32.inet_addr(hostip)

    buffer = ctypes.c_buffer(6)
    addlen = ctypes.c_ulong(ctypes.sizeof(buffer))
    if SendARP(inetaddr, 0, ctypes.byref(buffer), ctypes.byref(addlen)) != 0:
        raise WindowsError('Retreival of mac address(%s) - failed' % host)

    # Convert binary data into a string.
    macaddr = ''
    for intval in struct.unpack('BBBBBB', buffer):
        if intval > 15:
            replacestr = '0x'
        else:
            replacestr = 'x'
        if macaddr != '':
            macaddr = ':'.join([macaddr, hex(intval).replace(replacestr, '')])
        else:
            macaddr = ''.join([macaddr, hex(intval).replace(replacestr, '')])

    return macaddr.upper()


def getMac():
    global MAC
    MAC = get_macaddress()
    fpath = getPath()
    macpath = fpath + "/mac.conf"
    with open(macpath, 'w') as f:
        data = json.dumps(dict(mac=MAC))
        f.write(data)


def getPath():
    str = os.path.split(os.path.realpath(__file__))
    str = os.path.split(str[0])
    return str[0] + '/'


def socketConnect():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except socket.error:
        error_info = getExpInfo(True)[1]
        # print HOST
        # print error_info
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


def getExpInfo(just_info=False):
    '''得到Exception的异常'''
    import traceback
    if just_info:
        info = sys.exc_info()
        return info[0].__name__ + ':' + str(info[1])
    else:
        return traceback.format_exc()


class AgentService(win32serviceutil.ServiceFramework):
    #服务名
    _svc_name_ = "AgentService"
    #服务显示名称
    _svc_display_name_ = "Agent"
    #服务描述
    _svc_description_ = "A monitor agent for you to hold your computer! "

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.runing = True

    def SvcDoRun(self):
        global RATE
        global MAC
        os = getRelease()
        sock = getConnect()
        fpath = getPath()
        filepath = fpath + "/user.conf"
        with open(filepath, 'r') as f:
            out_data = f.read()
            USER_KEY = json.loads(out_data).get('user_key')
        macpath = fpath + "/mac.conf"
        try:
            with open(macpath, 'r') as f:
                out_data = f.read()
                MAC = json.loads(out_data).get('mac')
        except IOError:
            getMac()
        # print MAC
        additional = dict(user_key=USER_KEY, platform=PLATFORM, mac=MAC, release=os, version=VERSION)
        while True:
            mon_data = dict(top=cpuMemTopMon(), disk=diskMon(), net=netMon(), agent_time=time.time())
            mon_data.update(additional)
            mon_data = json.dumps(mon_data)
            mon_data = zlib.compress(mon_data)
            mon_data += '\u7ed3\u675f'
            try:
                sock.send(mon_data)
            except socket.error:
                #error_info = getExpInfo(True)[1]
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
                #error_info = getExpInfo(True)[0]
                # if error_info[1][0] != 35:
                sock = getConnect()
            time.sleep(RATE)
        # 等待服务被停止
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.runing = False
if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AgentService)
