#<img src="images/logo-black.png"  width="40px"> hold-agent 
* 个轻量的主机观察者,帮你轻松掌控主机并揪出不安分进程
* 无需配置，一行命令，即刻开始使用
* 简单点击回溯历史，揪出可疑进程
* 采集器代码开源，安全放心

#文件说明
* agent-install.sh 主机观察者安装和开机启动脚本
* agent-uninstall.sh 主机观察者卸载脚本
* agent.py 主机观察者程序,为了让您放心, 我们将这个 python 写的小程序开源了

#如何使用
* `USER_KEY` 您在[HOLD](http://highwe.net/profile#user)上注册用户的密钥
* 开机启动,需要使用`sudo`权限运行
```sudo agent-install.sh  USER_KEY```
* 源码启动
```python agent.py USER_KEY```

#查看主机性能
通过访问[HOLD](http://highwe.net/hostList) 来查看您的主机性能信息。
